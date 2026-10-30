import io
import re
import cv2
import numpy as np
import pandas as pd
import streamlit as st
import easyocr
from PIL import Image, ImageOps
from rapidfuzz import process, fuzz

st.set_page_config(page_title="진짜약 (Jinzzayak)", page_icon="💊", layout="centered")

# =====================================================================
# 1. OCR (사진 → 글자)
# =====================================================================
MAX_SIDE = 2000   # 사진 최대 크기 (클수록 작은 글씨를 잘 읽지만 느려짐)
MAG_RATIO = 1.0   # 확대 비율

@st.cache_resource
def load_reader():
    return easyocr.Reader(["ko", "en"], gpu=False)

def _preprocess(pil_img):
    pil_img = ImageOps.exif_transpose(pil_img)        # 휴대폰 사진 회전 정보 반영
    img = np.array(pil_img.convert("RGB"))
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_AREA)
    return img

@st.cache_data(show_spinner=False)
def run_ocr_bytes(img_bytes, min_conf=0.3):
    """사진 → 인식된 글자 리스트 (같은 사진은 한 번만 읽음)"""
    pil_img = Image.open(io.BytesIO(img_bytes))
    results = load_reader().readtext(_preprocess(pil_img), detail=1, mag_ratio=MAG_RATIO)
    return [text for _, text, conf in results if conf >= min_conf]

# =====================================================================
# 2. 판별 (사진 글자 ↔ 식약처 허가정보)
# =====================================================================
STRICT = 90        # 제조사 점수가 이 이상이어야 '확인됨'
LOOSE = 70         # 제조사 점수가 이 미만이면 '불일치'
INGR_PASS = 75     # 성분 하나가 '있다'고 인정할 점수
INGR_RATIO = 0.5   # 성분 중 이 비율 이상 확인되어야 통과
MAKER_REQUIRED = False   # True면 제조사를 못 읽었을 때도 '확인 필요'

COLUMN_MAP = {"Product Name": "약품명", "Active Ingredient": "주성분", "Manufacturer": "제조사"}

def norm(s):
    s = re.sub(r"\(주\)|㈜|주식회사", "", str(s))
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()

def make_key(name):
    return norm(re.sub(r"\(.*?\)", "", str(name)))

def match_score(target, texts, full):
    """OCR 오타를 고려해서 target이 사진 속 글자에 있는지 점수(0~100)"""
    t = norm(target)
    if not t:
        return 0
    line_scores = [fuzz.ratio(t, norm(x)) for x in texts if norm(x)]
    return max(line_scores + [fuzz.partial_ratio(t, full)])

def merge_ingr(series):
    parts = []
    for v in series:
        parts += [p.strip() for p in str(v).split(",") if p.strip()]
    return ", ".join(dict.fromkeys(parts))

@st.cache_data
def load_db(path="drugs.csv"):
    for enc in ["utf-8-sig", "cp949"]:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc).fillna("")
            break
        except UnicodeDecodeError:
            continue
    df = df.rename(columns=COLUMN_MAP)
    df = df[["약품명", "주성분", "제조사"]]
    df = df.groupby(["약품명", "제조사"], as_index=False)["주성분"].agg(merge_ingr)
    df["검색키"] = df["약품명"].map(make_key)
    df = df[df["검색키"].str.len() >= 2].reset_index(drop=True)
    return df

def search_names(query, db, limit=5):
    """오타가 있어도 비슷한 약 이름 찾기"""
    q = make_key(query)
    if not q:
        return []
    res = process.extract(q, db["검색키"].tolist(), scorer=fuzz.WRatio,
                          limit=limit, score_cutoff=70)
    return [(i, db.at[i, "약품명"], db.at[i, "제조사"]) for _, _, i in res]

def find_other_company(full, db, expected):
    """포장지에 '허가 제조사가 아닌' 다른 제약사 이름이 적혀 있는지"""
    exp = norm(expected)
    for c in db["제조사"].unique():
        n = norm(c)
        if len(n) >= 4 and n != exp and n in full:
            return c
    return None

def verify(texts, db, idx):
    """사용자가 고른 약(idx)과 사진 속 글자(texts)를 비교"""
    full = norm(" ".join(texts))
    if len(full) < 2:
        return {"status": "error",
                "message": "사진에서 글자를 인식하지 못했어요. 더 밝고 선명한 사진을 올려주세요."}

    row = db.iloc[idx]
    entp_score = match_score(row["제조사"], texts, full)
    maker_ok = entp_score >= STRICT
    other = None if maker_ok else find_other_company(full, db, row["제조사"])

    ingrs = [i.strip() for i in str(row["주성분"]).split(",") if i.strip()]
    hit = sum(match_score(i, texts, full) >= INGR_PASS for i in ingrs)
    ingr_ratio = hit / len(ingrs) if ingrs else 0

    if maker_ok:
        maker_status = "확인됨"
    elif other and entp_score < LOOSE:
        maker_status = f"다른 제조사 발견 ({other})"
    else:
        maker_status = "사진에서 찾지 못함"
    detail = {"제조사 확인": maker_status}

    if other and entp_score < LOOSE:
        return {"status": "fake", "detail": detail,
                "message": f"포장지에 허가 제조사가 아닌 '{other}'이(가) 적혀 있어요. 위조 의심!"}
    if ingr_ratio < INGR_RATIO:
        return {"status": "warning", "detail": detail,
                "message": "주성분 표기가 허가정보와 일치하지 않아요. 성분이 적힌 부분을 가까이서 다시 찍어주세요."}
    if MAKER_REQUIRED and not maker_ok:
        return {"status": "warning", "detail": detail,
                "message": "제조사 표기를 확인하지 못했어요. 제조사가 적힌 부분을 가까이서 선명하게 다시 찍어주세요."}
    if maker_ok:
        msg = "제조사와 주성분이 식약처 허가정보와 일치해요. 정품일 가능성이 높아요."
    else:
        msg = "주성분이 식약처 허가정보와 일치해요. (제조사 표기는 사진에서 확인되지 않았어요)"
    return {"status": "genuine", "detail": detail, "message": msg}

def search_drugs(keyword, db):
    """약품명 또는 성분명으로 검색 (이름이 앞부분부터 맞는 약을 먼저)"""
    q = norm(keyword)
    if not q:
        return db.iloc[0:0]
    by_name = db["검색키"].str.contains(q, regex=False)
    by_ingr = db["주성분"].map(norm).str.contains(q, regex=False)
    res = db[by_name | by_ingr]
    if res.empty:
        idxs = [i for i, _, _ in search_names(keyword, db, limit=10)]
        res = db.loc[idxs]
    order = (~res["검색키"].str.startswith(q)).astype(int)
    return res.assign(_o=order).sort_values("_o").drop(columns="_o")

# =====================================================================
# 3. 화면 (진짜약 디자인)
# =====================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #f5f6fa;
        max-width: 480px;
        margin: 0 auto;
    }
    .stButton>button {
        background-color: #FF3B30;
        color: white;
        border-radius: 8px;
        width: 100%;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #d93228;
        color: white;
    }
    input {
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

with st.spinner("AI 엔진 준비 중..."):
    load_reader()
db = load_db()

defaults = {"menu": "메인", "selected_idx": None, "search_keyword": "",
            "bookmarks": [], "analysis_done": False, "ocr_texts": [], "result": None}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_search():
    st.session_state.selected_idx = None
    st.session_state.search_keyword = ""
    st.session_state.analysis_done = False
    st.session_state.result = None

def toggle_bookmark(name):
    if name in st.session_state.bookmarks:
        st.session_state.bookmarks.remove(name)
    else:
        st.session_state.bookmarks.append(name)

# ---------- 사이드바 ----------
with st.sidebar:
    st.title("메뉴")
    if st.button("🏠 약품 성분 검색/판별", use_container_width=True):
        st.session_state.menu = "메인"
        st.session_state.analysis_done = False
        st.rerun()
    if st.button("⭐ 즐겨찾기 (북마크)", use_container_width=True):
        st.session_state.menu = "즐겨찾기"
        st.rerun()
    if st.button("👤 마이메뉴", use_container_width=True):
        st.session_state.menu = "마이메뉴"
        st.rerun()
    if st.button("⚙️ 설정", use_container_width=True):
        st.session_state.menu = "설정"
        st.rerun()

# ---------- 즐겨찾기 / 마이메뉴 / 설정 ----------
if st.session_state.menu != "메인":
    st.markdown(f"### {st.session_state.menu}")
    st.markdown("---")
    if st.session_state.menu == "즐겨찾기":
        if st.session_state.bookmarks:
            for b in st.session_state.bookmarks:
                st.info(f"⭐ {b}")
        else:
            st.write("북마크된 약품이 없습니다.")
    elif st.session_state.menu == "마이메뉴":
        st.write("사용자 계정 정보 및 최근 판별 이력 관리 화면입니다.")
    elif st.session_state.menu == "설정":
        st.write("앱 환경 설정 및 버전 정보 (v1.0.0)")
    if st.button("메인으로 돌아가기"):
        st.session_state.menu = "메인"
        st.rerun()
    st.stop()

# ---------- 메인 ----------
col_top1, col_top2 = st.columns([1, 5])
with col_top1:
    st.markdown("### ☰")
with col_top2:
    st.markdown("### **진짜약**")
st.markdown("---")

col_search, col_btn = st.columns([3, 1])
with col_search:
    search_query = st.text_input("약품 검색", placeholder="약품명 또는 성분명을 입력하세요",
                                 label_visibility="collapsed", key="search_input")
with col_btn:
    search_clicked = st.button("검색")

if search_clicked:
    st.session_state.search_keyword = search_query
    st.session_state.selected_idx = None
    st.session_state.analysis_done = False

# [상태 A] 검색 · 선택 전
if st.session_state.selected_idx is None:
    kw = st.session_state.search_keyword.strip()
    if kw:
        matched = search_drugs(kw, db)
        if not matched.empty:
            st.markdown(f"**검색된 약품 목록** (총 {len(matched)}건)")
            with st.container(border=True):
                for idx, row in matched.head(10).iterrows():
                    d_name = row["약품명"]
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        if st.button(f"{d_name}  ·  {row['제조사']}", key=f"drug_{idx}",
                                     use_container_width=True):
                            st.session_state.selected_idx = int(idx)
                            st.rerun()
                    with c2:
                        is_bm = d_name in st.session_state.bookmarks
                        if st.button("⭐" if is_bm else "☆", key=f"bm_{idx}"):
                            toggle_bookmark(d_name)
                            st.rerun()
        else:
            st.error("🚨 식약처 허가 DB에서 일치하는 약품을 찾을 수 없어요. "
                     "약품명을 다시 확인하거나, 미허가 제품일 수 있어요.")
    else:
        st.info("💡 검색할 약품명을 입력하고 검색 버튼을 눌러주세요.")

# [상태 B·C] 약품 선택 후
else:
    idx = st.session_state.selected_idx
    row = db.iloc[idx]
    d_name = row["약품명"]
    is_bm = d_name in st.session_state.bookmarks

    col_sel1, col_sel2, col_sel3 = st.columns([3, 1, 1])
    with col_sel1:
        st.success(f"✔️ **{d_name}** (적용됨)")
    with col_sel2:
        if st.button("⭐ 북마크" if not is_bm else "★ 취소"):
            toggle_bookmark(d_name)
            st.rerun()
    with col_sel3:
        if st.button("다시 검색"):
            reset_search()
            st.rerun()
    st.caption(f"제조사: {row['제조사']}  |  주성분: {row['주성분']}")
    st.markdown("---")

    # [상태 B] 이미지 업로드
    if not st.session_state.analysis_done:
        st.markdown("#### 이미지를 업로드 하세요")
        st.caption("📌 제조사와 '원료약품 및 분량'이 적힌 칸을 글자가 가로로 보이게, "
                   "가까이서 찍으면 정확해요. 여러 장 올릴 수 있어요.")
        files = st.file_uploader("포장지 사진", type=["jpg", "png", "jpeg"],
                                 accept_multiple_files=True, label_visibility="collapsed")
        if files:
            with st.container(border=True):
                for f in files:
                    col_f1, col_f2 = st.columns([1, 4])
                    with col_f1:
                        st.image(Image.open(f), width=60)
                    with col_f2:
                        st.markdown(f"**파일명:** {f.name}")
                        st.caption(f"크기: {f.size / 1024:.1f} KB")

            if st.button("🚀 성분 비교 및 판정 시작", use_container_width=True):
                texts = []
                bar = st.progress(0, text="이미지 분석 중입니다...")
                for i, f in enumerate(files):
                    texts += run_ocr_bytes(f.getvalue())
                    bar.progress((i + 1) / len(files),
                                 text=f"이미지 분석 중... ({i + 1}/{len(files)})")
                st.session_state.ocr_texts = texts
                st.session_state.result = verify(texts, db, idx)
                st.session_state.analysis_done = True
                st.rerun()

    # [상태 C] 분석 결과
    else:
        result = st.session_state.result
        texts = st.session_state.ocr_texts
        full = norm(" ".join(texts))
        status = result["status"]
        detail = result.get("detail", {})

        ingrs = [x.strip() for x in str(row["주성분"]).split(",") if x.strip()]
        hits = {ing: match_score(ing, texts, full) >= INGR_PASS for ing in ingrs}
        n_hit = sum(hits.values())
        ratio = n_hit / len(ingrs) if ingrs else 0

        st.markdown("### **성분 대조 및 최종 판정 결과**")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.caption("주성분 일치 여부")
            if ratio >= INGR_RATIO:
                st.markdown("<h3 style='color: #34C759;'>일치</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color: #FF3B30;'>불일치</h3>", unsafe_allow_html=True)
        with col_r2:
            st.caption("성분 일치율")
            st.markdown(f"<h3>{ratio * 100:.0f}% <span style='font-size:15px;color:#8e8e93;'>"
                        f"({n_hit}/{len(ingrs)}개)</span></h3>", unsafe_allow_html=True)

        VERDICT = {
            "genuine": ("정품 (GENUINE)", "#34C759"),
            "fake":    ("가품 의심 (COUNTERFEIT)", "#FF3B30"),
            "warning": ("확인 필요 (CHECK)", "#FF9500"),
            "error":   ("인식 실패 (RETRY)", "#FF9500"),
        }
        v_text, v_color = VERDICT[status]
        st.caption("최종 판정")
        st.markdown(f"<h2 style='color: {v_color};'>{v_text}</h2>", unsafe_allow_html=True)
        if status == "genuine":
            st.success("🎉 " + result["message"])
        elif status == "fake":
            st.error("🚨 " + result["message"])
        else:
            st.warning("⚠️ " + result["message"])

        st.markdown("#### **상세 항목별 대조 리포트**")
        maker_status = detail.get("제조사 확인", "사진에서 찾지 못함")
        if maker_status.startswith("확인됨"):
            maker_ocr, maker_res = "검출", "✅ 일치"
        elif maker_status.startswith("다른"):
            maker_ocr, maker_res = maker_status, "❌ 불일치"
        else:
            maker_ocr, maker_res = "미검출", "➖ 확인 불가"

        rows = [["제품명", d_name, "사용자 선택", "✅ 확인"],
                ["제조사", row["제조사"], maker_ocr, maker_res]]
        for ing in ingrs:
            rows.append(["주성분", ing, "검출" if hits[ing] else "미검출",
                         "✅ 일치" if hits[ing] else "❌ 불일치"])
        st.table(pd.DataFrame(rows, columns=["검증 항목", "기준 DB (정품)",
                                             "이미지 OCR 검출값", "검증 결과"]))

        with st.expander("🔍 사진에서 인식된 글자 보기"):
            st.write(texts)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("다른 사진으로 다시 분석", use_container_width=True):
                st.session_state.analysis_done = False
                st.rerun()
        with col_b2:
            if st.button("메인화면으로 돌아가기", use_container_width=True):
                reset_search()
                st.rerun()

st.markdown("---")
st.caption("© 2026 Jinzzayak. 포장지 표기를 식약처 허가정보와 대조한 참고용 결과이며, "
           "복용 전 최종 확인은 약사와 상담하세요.")
