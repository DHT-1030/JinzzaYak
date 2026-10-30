import base64
import contextlib
import html
import io
import logging
import os
import re
import warnings
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from rapidfuzz import process, fuzz

warnings.filterwarnings("ignore")
logging.getLogger("easyocr").setLevel(logging.ERROR)

st.set_page_config(
    page_title="진짜약 (Jinzzayak)",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ss = st.session_state
esc = html.escape
MAX_FILES = 6


CSS = """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css");

:root{
  --red:#E5383B; --red-d:#C92A2D; --green:#12A150;
  --ink:#191F28; --sub:#4E5968; --mute:#8B95A1;
  --line:#E5E8EB; --bg:#F2F4F6; --soft:#F9FAFB;
}
html, body, .stApp, p, div, label, input, textarea, button, table, td, th {
  font-family:"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,system-ui,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  letter-spacing:-0.01em;
}


header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], #MainMenu, footer, .stDeployButton,
[data-testid="InputInstructions"], [data-testid="stElementToolbar"] { display:none !important; }


.stApp { background:#E9ECEF; }
.block-container, [data-testid="stMainBlockContainer"]{
  max-width:440px !important; padding:0 20px 100px !important;
  background:#fff; min-height:100dvh;
}
@media (max-width:480px){ .stApp{ background:#fff; } }
[data-testid="stVerticalBlock"]{ gap:0.6rem; }


[data-testid="stHorizontalBlock"]{ flex-wrap:nowrap !important; gap:8px !important; }
[data-testid="stColumn"], [data-testid="column"]{ min-width:0 !important; }


.stButton, .stFormSubmitButton{ width:100%; }
.stButton > button, .stFormSubmitButton > button{
  width:100%; min-height:50px; border-radius:12px;
  font-size:16px; font-weight:600; color:var(--ink);
  background:#fff; border:1px solid var(--line); box-shadow:none;
  transition:background .15s, transform .05s;
}
.stButton > button:hover, .stButton > button:focus:not(:active){ color:var(--ink); border-color:#D1D6DB; }
.stButton > button:active, .stFormSubmitButton > button:active{ transform:scale(.985); }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"]{
  background:var(--red) !important; color:#fff !important; border:none !important;
}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover{
  background:var(--red-d) !important; color:#fff !important;
}


[data-testid="stForm"]{
    border: none !important;
    padding: 0 !important;
}


.st-key-searchrow [data-testid="stHorizontalBlock"]{
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}


.stTextInput {
    width: 100% !important;
}
.stTextInput [data-baseweb="input"]{
    height: 46px !important;
    border: 1.5px solid var(--line) !important;
    border-radius: 12px !important;
    background: #fff !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
}
.stTextInput [data-baseweb="input"]:focus-within{
    border-color: var(--ink) !important;
}
.stTextInput input{
    font-size: 15px !important;
    color: var(--ink) !important;
    padding: 0 14px !important;
    background: transparent !important;
    border: none !important;
    outline: none !important;
}
.stTextInput input::placeholder{ color: #B0B8C1 !important; }


.st-key-searchrow .stFormSubmitButton {
    width: auto !important;
}
.st-key-searchrow .stFormSubmitButton > button{
    width: 65px !important;
    min-height: 35px !important;
    height: 46px !important;
    border-radius: 12px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    background: var(--red) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.st-key-searchrow .stFormSubmitButton > button:hover{
    background: var(--red-d) !important;
}


.st-key-topbar{ position:sticky; top:0; z-index:50; background:#fff; padding:10px 0 6px; }
.st-key-topbar .stButton{ width:auto; }
.st-key-topbar .stButton > button{
  width:auto; min-height:44px; padding:0 6px 0 0; gap:8px;
  border:none !important; background:transparent !important; justify-content:flex-start;
}
.st-key-topbar button > div{ align-items:center; gap:8px; }
.st-key-topbar [data-testid="stIconMaterial"]{ font-size:26px; color:var(--ink); }
.st-key-topbar button p{ font-size:21px; font-weight:800; color:var(--ink); letter-spacing:-0.03em; line-height:1; margin:0; }
.st-key-tb_back button p{ font-size:18px; font-weight:700; }


.sec{ display:flex; justify-content:space-between; align-items:baseline; margin:12px 0 0; }
.sec b{ font-size:15px; font-weight:700; color:var(--ink); }
.sec small{ font-size:12px; color:var(--mute); }
.sec.up{ margin:14px 0 10px; }
.empty{ color:var(--mute); font-size:14px; line-height:1.6; padding:14px 2px; }
.notice{
  background:var(--soft); border:1px solid var(--line); border-radius:14px;
  padding:22px 18px; text-align:center; color:var(--sub); font-size:15px; line-height:1.6;
}
.notice b{ color:var(--ink); display:block; font-size:16px; margin-bottom:4px; }
.err{ background:#FFF1F1; color:var(--red-d); border-radius:12px; padding:12px 14px; font-size:14px; }


[data-testid="stButtonGroup"] button{ border-radius:999px !important; font-size:14px; }
.st-key-hist_clear .stButton > button{
  min-height:28px; border:none; background:transparent; color:var(--mute);
  font-size:13px; font-weight:500; justify-content:flex-end; padding:0;
}


.st-key-reslist{
    background: var(--bg);
    border-radius: 14px;
    padding: 4px 10px;
    margin-top: 18px;
    height: auto !important;
    max-height: 330px !important;
    overflow-y: auto !important;
}
.st-key-favlist{
    background: var(--bg);
    border-radius: 14px;
    padding: 4px 10px;
    margin-top: 18px;
    height: auto !important;
    max-height: 330px !important;
    overflow-y: auto !important;
}
[class*="st-key-row_"], [class*="st-key-hrow_"]{ border-bottom:1px solid #E1E4E8; }
[class*="st-key-row_"]:last-child, [class*="st-key-hrow_"]:last-child{ border-bottom:none; }
[class*="st-key-res_"] .stButton > button, [class*="st-key-open_"] .stButton > button{
  background:transparent; border:none; min-height:48px; padding:0 4px;
  justify-content:flex-start; font-size:15px; font-weight:500;
}
[class*="st-key-res_"] button > div, [class*="st-key-open_"] button > div{ justify-content:flex-start; width:100%; }
[class*="st-key-res_"] button p, [class*="st-key-open_"] button p{
  text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
[class*="st-key-bm_"] .stButton > button{
  background:transparent; border:none; min-height:44px; width:44px; padding:0;
}
[class*="st-key-bm_"] [data-testid="stIconMaterial"]{ font-size:22px; color:#B0B8C1; }
[class*="st-key-bmcon_"] [data-testid="stIconMaterial"]{ color:var(--red) !important; }


.applied{ background:var(--soft); border:1px solid var(--line); border-radius:14px; padding:12px 14px; }
.applied .tag{ display:inline-block; font-size:11px; font-weight:700; color:var(--red);
  background:#FFECEC; border-radius:6px; padding:2px 7px; margin-bottom:5px; }
.applied .nm{ font-size:16px; font-weight:700; color:var(--ink); line-height:1.4; }
.applied .meta{ font-size:12.5px; color:var(--mute); margin-top:2px; line-height:1.5; }


[class*="st-key-upwrap"]{ margin-top:4px; }
.st-key-upwrap{ margin-top:12px; }
[class*="st-key-upwrap"] [data-testid="stFileUploaderDropzone"]{
  position:relative; min-height:60px; border:1.5px dashed #CDD2D8; background:var(--bg);
  border-radius:14px; display:flex; align-items:center; justify-content:center; padding:0;
}
.st-key-upwrap_empty [data-testid="stFileUploaderDropzone"]{ min-height:110px; }
[class*="st-key-upwrap"] [data-testid="stFileUploaderDropzoneInstructions"]{ display:none; }
[class*="st-key-upwrap"] [data-testid="stFileUploaderDropzone"] button{
  position:absolute; inset:0; width:100%; height:100%; opacity:0; z-index:2; cursor:pointer;
}
[class*="st-key-upwrap"] [data-testid="stFileUploaderDropzone"]::after{
  content:"+ 사진 추가"; font-size:15px; font-weight:600; color:var(--mute); pointer-events:none;
}
[class*="st-key-upwrap"] [data-testid="stFileUploaderFile"],
[class*="st-key-upwrap"] [data-testid="stFileUploaderPagination"]{ display:none; }


[class*="st-key-chip_"]{ position:relative; gap:0 !important; }
.chip img{ width:100%; aspect-ratio:1; object-fit:cover; display:block;
  border-radius:10px; border:1px solid var(--line); background:var(--bg); }
.chip .n{ font-size:11px; font-weight:600; color:var(--ink); margin-top:4px; line-height:1.2;
  letter-spacing:-0.02em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chip .s{ font-size:10px; color:var(--mute); line-height:1.2; margin-top:1px; letter-spacing:-0.01em; }
[class*="st-key-rm_"]{ position:absolute !important; top:4px; right:4px; width:auto !important; z-index:5; }
[class*="st-key-rm_"] .stButton{ width:auto; }
[class*="st-key-rm_"] .stButton > button{
  width:22px; height:22px; min-height:22px; padding:0; border-radius:50%;
  background:rgba(25,31,40,.72) !important; border:none !important;
}
[class*="st-key-rm_"] [data-testid="stIconMaterial"]{ font-size:14px; color:#fff; }


.st-key-btn_compare{ margin-top:6px; }
.st-key-btn_compare, .st-key-btn_compare .stButton{ width:100% !important; display:flex; justify-content:center; }
.st-key-btn_compare .stButton > button{
  width:86% !important; min-width:220px; white-space:nowrap;
  border:1.5px solid var(--red) !important; color:var(--red) !important; background:#fff;
}
.st-key-btn_compare button p{ white-space:nowrap; }


.analyzing{ min-height:calc(100dvh - 40px); display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center; }
.scanbox{ position:relative; width:200px; height:200px; border-radius:22px; overflow:hidden;
  background:var(--bg); box-shadow:0 8px 28px rgba(0,0,0,.08); }
.scanbox img{ width:100%; height:100%; object-fit:cover; }
.scanbox::after{ content:""; position:absolute; left:0; right:0; height:3px; background:var(--red);
  box-shadow:0 0 14px var(--red); animation:scan 1.8s ease-in-out infinite; }
@keyframes scan{ 0%{top:0} 50%{top:calc(100% - 3px)} 100%{top:0} }
.an-t{ font-size:18px; font-weight:700; color:var(--ink); margin-top:26px; white-space:nowrap; }
.dots b{ font-weight:700; opacity:0; animation-duration:1.6s; animation-iteration-count:infinite; }
.dots b:nth-child(1){ animation-name:d1; }
.dots b:nth-child(2){ animation-name:d2; }
.dots b:nth-child(3){ animation-name:d3; }
@keyframes d1{ 0%,10%{opacity:0} 15%,100%{opacity:1} }
@keyframes d2{ 0%,40%{opacity:0} 45%,100%{opacity:1} }
@keyframes d3{ 0%,70%{opacity:0} 75%,100%{opacity:1} }
.an-s{ color:var(--mute); font-size:13px; margin-top:6px; line-height:1.6; }


.r-title{ font-size:25px; font-weight:800; color:var(--ink); letter-spacing:-0.035em; margin:6px 0 4px; }
.r-drug{ color:var(--mute); font-size:14px; margin-bottom:6px; }
.r-item{ padding:18px 0; border-bottom:1px solid var(--line); }
.r-item:last-child{ border-bottom:none; }
.r-label{ display:block; font-size:13px; color:var(--mute); font-weight:500; margin-bottom:4px; }
.r-value{ font-size:30px; font-weight:800; letter-spacing:-0.03em; line-height:1.25; }
.r-value.sm{ font-size:24px; }
.ok{ color:var(--green); } .bad{ color:var(--red); }
.bar{ height:6px; background:var(--bg); border-radius:99px; margin-top:10px; overflow:hidden; }
.bar i{ display:block; height:100%; border-radius:99px; }
[class*="st-key-light_"] .stButton > button{
  background:var(--bg) !important; border:none !important; color:var(--sub) !important; font-weight:500;
}


.rpt-h{ font-size:22px; font-weight:800; color:var(--ink); letter-spacing:-0.03em; margin:4px 0 12px; }
.rpt{ width:100%; border-collapse:separate; border-spacing:0; border:1px solid var(--line);
  border-radius:12px; overflow:hidden; font-size:13px; table-layout:fixed; }
.rpt th{ background:var(--soft); color:var(--mute); font-weight:500; text-align:left; padding:10px 8px; font-size:12px; }
.rpt td{ padding:11px 8px; border-top:1px solid var(--line); color:var(--ink); word-break:break-all; vertical-align:top; }
.rpt td.k{ color:var(--sub); }
.rpt .pct{ display:block; font-size:11px; color:var(--mute); margin-top:2px; }
.fine{ font-size:12px; color:var(--mute); line-height:1.6; margin-top:6px; }


.st-key-drawer{ animation:fadein .2s ease-out; }
@keyframes fadein{ from{ opacity:0; margin-left:-16px } to{ opacity:1; margin-left:0 } }
.st-key-drawer [class*="st-key-dr_"] .stButton > button{
  border:none; background:transparent; justify-content:flex-start; font-size:17px; font-weight:700;
  min-height:56px; padding:0 4px; border-bottom:1px solid var(--line); border-radius:0;
}
.st-key-drawer [class*="st-key-dr_"] button > div{ justify-content:flex-start; gap:10px; }
.st-key-drawer [class*="st-key-dr_"] [data-testid="stIconMaterial"]{ font-size:22px; color:var(--sub); }


.st-key-drawer_bottom{
  position:fixed; bottom:0; left:50%; transform:translateX(-50%); width:100%; max-width:440px;
  background:#fff; border-top:1px solid var(--line);
  padding:6px 20px calc(6px + env(safe-area-inset-bottom)); z-index:100;
}
.st-key-drawer_bottom .stButton > button{
  border:none; background:transparent; font-size:15px; font-weight:600; color:var(--sub); min-height:52px; padding:0;
}
.st-key-db_my .stButton > button, .st-key-db_my button > div{ justify-content:flex-start; }
.st-key-db_set .stButton > button, .st-key-db_set button > div{ justify-content:flex-end; }


.set-sec{ font-size:13px; color:var(--mute); font-weight:600; margin:18px 0 2px; }
.stToggle label p{ font-size:15px; color:var(--ink); }


.st-key-btn_report,
[class*="st-key-light_"] {
    display: flex !important;
    justify-content: flex-end !important;
    width: 100% !important;
}

.st-key-btn_report .stButton,
[class*="st-key-light_"] .stButton {
    display: flex !important;
    justify-content: flex-end !important;
    width: 100% !important;
}

.st-key-btn_report .stButton > button,
[class*="st-key-light_"] .stButton > button {
    margin-left: auto !important;
    margin-right: 0 !important;
    width: 240px !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


MAX_SIDE = 2000
MAG_RATIO = 1.0


@st.cache_resource(show_spinner=False)
def load_reader():

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import torch
        import easyocr
        torch.set_num_threads(4)
        model_dir = os.getenv("JINZZAYAK_OCR_MODELS", str(Path(__file__).parent / ".cache" / "easyocr"))
        return easyocr.Reader(["ko", "en"], gpu=False, verbose=False, model_storage_directory=model_dir)


def _preprocess(pil_img):
    pil_img = ImageOps.exif_transpose(pil_img)
    img = np.array(pil_img.convert("RGB"))
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_AREA)
    return img


@st.cache_data(show_spinner=False)
def run_ocr_bytes(img_bytes, min_conf=0.3):

    pil_img = Image.open(io.BytesIO(img_bytes))
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        results = load_reader().readtext(_preprocess(pil_img), detail=1, mag_ratio=MAG_RATIO)
    return [text for _, text, conf in results if conf >= min_conf]


STRICT = 90
LOOSE = 70
INGR_PASS = 75
INGR_RATIO = 0.5
MAKER_REQUIRED = False

COLUMN_MAP = {"Product Name": "약품명", "Active Ingredient": "주성분", "Manufacturer": "제조사"}


def norm(s):
    s = re.sub(r"\(주\)|㈜|주식회사", "", str(s))
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s).lower()


def make_key(name):
    return norm(re.sub(r"\(.*?\)", "", str(name)))


def match_score(target, texts, full):

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


@st.cache_data(show_spinner=False)
def load_db(path="drugs.csv"):
    path = Path(__file__).resolve().parent / path
    df = None
    for enc in ["utf-8-sig", "cp949"]:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc).fillna("")
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        raise ValueError("drugs.csv 인코딩을 읽을 수 없습니다.")
    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMN_MAP)
    df = df[["약품명", "주성분", "제조사"]]
    df = df.groupby(["약품명", "제조사"], as_index=False)["주성분"].agg(merge_ingr)
    df["검색키"] = df["약품명"].map(make_key)
    df = df[df["검색키"].str.len() >= 2].reset_index(drop=True)
    return df


def search_names(query, db, limit=5):

    q = make_key(query)
    if not q:
        return []
    res = process.extract(q, db["검색키"].tolist(), scorer=fuzz.WRatio,
                          limit=limit, score_cutoff=70)
    return [(i, db.at[i, "약품명"], db.at[i, "제조사"]) for _, _, i in res]


def find_other_company(full, db, expected):

    exp = norm(expected)
    for c in db["제조사"].unique():
        n = norm(c)
        if len(n) >= 4 and n != exp and n in full:
            return c
    return None


def verify(texts, db, idx):

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
                "message": f"사진에서 등록 제조사와 다른 '{other}' 표기를 찾았어요. 제조사·판매사 표시를 다시 확인해 주세요. 위조 여부를 뜻하지 않습니다."}
    if ingr_ratio < INGR_RATIO:
        return {"status": "warning", "detail": detail,
                "message": "등록된 주성분 이름을 충분히 읽지 못했어요. 성분 표시 전체를 선명하게 다시 찍어주세요. 실제 성분 누락을 뜻하지 않습니다."}
    if MAKER_REQUIRED and not maker_ok:
        return {"status": "warning", "detail": detail,
                "message": "제조사 표기를 확인하지 못했어요. 제조사가 적힌 부분을 가까이서 선명하게 다시 찍어주세요."}
    if maker_ok:
        msg = "제조사와 주성분 이름에 유사한 표기를 찾았어요. 원문을 확인해 주세요. 사진만으로 정품 여부나 실제 내용물을 확인할 수 없습니다."
    else:
        msg = "등록된 주성분 이름에 유사한 표기를 찾았어요. 제조사 표기는 확인되지 않았습니다. 정품 인증이나 복용 가능 판정이 아닙니다."
    return {"status": "genuine", "detail": detail, "message": msg}


def search_drugs(keyword, db):

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


with st.spinner("AI 엔진 준비 중..."):
    load_reader()

try:
    db = load_db()
except Exception as e:
    st.markdown('<div class="err">drugs.csv 파일을 불러오지 못했습니다.<br>' + esc(str(e)) + "</div>",
                unsafe_allow_html=True)
    st.stop()

FOOTER = ("© 2026 Jinzzayak · 로컬 테스트. 저장소 제공 CSV와 포장지 글자를 비교합니다. "
          "데이터 출처·갱신일은 검증 전이며, 결과는 정품 인증이나 복용 판단이 아닙니다.")

VERDICT = {
    "genuine": ("유사 표기 검출 (MATCH)", "ok"),
    "fake": ("제조사 표기 확인 필요", "warn"),
    "warning": ("확인 필요 (CHECK)", "warn"),
    "error": ("인식 실패 (RETRY)", "warn"),
}
WARN_STYLE = ' style="color:#FF9500"'


_DEFAULTS = {
    "page": "home", "prev": "home", "results": None, "total": 0,
    "applied": None, "files": [], "up_n": 0, "hist_n": 0,
    "history": [], "bookmarks": [], "analyses": [], "result": None, "err": "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in ss:
        ss[_k] = list(_v) if isinstance(_v, list) else _v


def to_rec(idx):
    idx = int(idx)
    return {"idx": idx, "name": db.at[idx, "약품명"], "maker": db.at[idx, "제조사"],
            "ingr": db.at[idx, "주성분"]}


def go(page):
    ss.page = page


def toggle_menu():
    if ss.page == "menu":
        ss.page = ss.prev
    else:
        ss.prev = ss.page
        ss.page = "menu"


def reset_home():
    ss.applied, ss.results, ss.files, ss.err, ss.result = None, None, [], "", None
    ss.q = ""
    ss.page = "home"


def retry_photos():
    ss.files, ss.err = [], ""
    ss.page = "home"


def clear_list(name):
    ss[name] = []


def do_search(query=None):
    if query is not None:
        ss.q = query
    q = str(ss.get("q", "")).strip()
    if not q:
        st.toast("약품명을 입력해주세요")
        return
    if ss.applied and q == ss.applied["name"]:
        st.toast("이미 적용된 약품입니다")
        return
    ss.applied, ss.files, ss.err = None, [], ""
    ss.history = ([q] + [h for h in ss.history if h != q])[:8]
    matched = search_drugs(q, db)
    ss.total = len(matched)
    ss.results = [to_rec(i) for i in matched.head(10).index]


def on_pick_history():
    val = ss.get("hist_" + str(ss.hist_n))
    ss.hist_n += 1
    if val:
        do_search(val)


def apply_drug(rec):
    ss.applied = rec
    ss.q = rec["name"]
    ss.results, ss.files, ss.err = None, [], ""
    ss.page = "home"


def is_bookmarked(rec):
    return any(b["idx"] == rec["idx"] for b in ss.bookmarks)


def toggle_bookmark(rec):
    if is_bookmarked(rec):
        ss.bookmarks = [b for b in ss.bookmarks if b["idx"] != rec["idx"]]
        st.toast("즐겨찾기에서 삭제했습니다")
    else:
        ss.bookmarks = ss.bookmarks + [rec]
        st.toast("즐겨찾기에 추가했습니다")


def make_thumb(data, size=320):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


def fmt_size(n):
    return "%.1f KB" % (n / 1024)


def on_upload():
    new = ss.get("uploader_" + str(ss.up_n)) or []
    have = {(f["name"], f["size"]) for f in ss.files}
    files = list(ss.files)
    for uf in new:
        if len(files) >= MAX_FILES:
            st.toast("사진은 최대 %d장까지 올릴 수 있습니다" % MAX_FILES)
            break
        data = uf.getvalue()
        if (uf.name, len(data)) in have:
            continue
        try:
            thumb = make_thumb(data)
        except Exception:
            st.toast(uf.name + " 파일을 열 수 없습니다")
            continue
        files.append({"name": uf.name, "size": len(data), "data": data, "thumb": thumb})
    ss.files = files
    ss.up_n += 1


def remove_file(i):
    ss.files = [f for j, f in enumerate(ss.files) if j != i]


def start_compare():
    if not ss.files:
        st.toast("포장지 사진을 먼저 올려주세요")
        return
    ss.err = ""
    ss.page = "analyzing"


def open_result(r):
    ss.result = r
    ss.page = "result"


def topbar(title=None, back=None):
    with st.container(key="topbar"):
        if back:
            st.button(title or "", icon=":material/arrow_back:", key="tb_back", on_click=go, args=(back,))
        else:
            st.button(title or "진짜약", icon=":material/menu:", key="tb_menu", on_click=toggle_menu)


def drug_row(rec, i, prefix):
    on = is_bookmarked(rec)
    with st.container(key="row_%s%d" % (prefix, i)):
        c1, c2 = st.columns([7, 1], vertical_alignment="center")
        with c1:
            st.button("%s  ·  %s" % (rec["name"], rec["maker"]), key="res_%s%d" % (prefix, i),
                      on_click=apply_drug, args=(rec,))
        with c2:
            with st.container(key="bmc%s_%s%d" % ("on" if on else "", prefix, i)):
                st.button("", icon=":material/bookmark:" if on else ":material/bookmark_border:",
                          key="bm_%s%d" % (prefix, i), on_click=toggle_bookmark, args=(rec,))


def verdict_span(status, size_cls="r-value sm"):
    text, cls = VERDICT[status]
    if cls == "warn":
        return '<span class="%s"%s>%s</span>' % (size_cls, WARN_STYLE, text)
    return '<span class="%s %s">%s</span>' % (size_cls, cls, text)


def page_home():
    topbar()

    applied = ss.applied
    with st.container(key="searchrow"):
        with st.form("search_form", border=False):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            with c1:
                st.text_input("약품명", key="q", placeholder="약품명 또는 성분명을 입력하세요",
                              label_visibility="collapsed")
            with c2:
                st.form_submit_button("적용됨" if applied else "검색", type="primary", on_click=do_search)

    if ss.err:
        st.markdown('<div class="err">' + esc(ss.err) + "</div>", unsafe_allow_html=True)


    if applied:
        st.markdown(
            '<div class="applied"><span class="tag">적용되었습니다</span>'
            '<div class="nm">' + esc(applied["name"]) + "</div>"
            '<div class="meta">제조사 ' + esc(applied["maker"] or "-")
            + "<br>주성분 " + esc(applied["ingr"] or "-") + "</div></div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.button("★ 북마크 취소" if is_bookmarked(applied) else "☆ 북마크", key="sel_bm",
                      on_click=toggle_bookmark, args=(applied,))
        with c2:
            st.button("다시 검색", key="sel_reset", on_click=reset_home)

        st.markdown(
            '<div class="sec up"><b>이미지를 업로드 하세요</b>'
            "<small>.jpg .png .jpeg · 최대 %d장</small></div>"
            '<div class="fine">제조사와 \'원료약품 및 분량\'이 적힌 칸을 글자가 가로로 보이게, '
            "가까이서 찍으면 정확해요. 여러 장 올릴 수 있어요.</div>" % MAX_FILES,
            unsafe_allow_html=True,
        )

        files = ss.files
        per_row = 4
        for start in range(0, len(files), per_row):
            cols = st.columns(per_row)
            for j, col in enumerate(cols):
                idx = start + j
                if idx >= len(files):
                    continue
                f = files[idx]
                with col:
                    with st.container(key="chip_%d" % idx):
                        st.markdown(
                            '<div class="chip"><img src="data:image/jpeg;base64,' + f["thumb"] + '"/>'
                            '<div class="n">' + esc(f["name"]) + "</div>"
                            '<div class="s">' + fmt_size(f["size"]) + "</div></div>",
                            unsafe_allow_html=True,
                        )
                        st.button("", icon=":material/close:", key="rm_%d" % idx,
                                  on_click=remove_file, args=(idx,))

        if len(files) < MAX_FILES:
            with st.container(key="upwrap" if files else "upwrap_empty"):
                st.file_uploader("포장지 사진", type=["jpg", "jpeg", "png"], accept_multiple_files=True,
                                 key="uploader_" + str(ss.up_n), on_change=on_upload,
                                 label_visibility="collapsed")

        st.button("성분 비교 및 판정 시작", key="btn_compare", on_click=start_compare)


    elif ss.results is not None:
        if not ss.results:
            st.markdown(
                '<div class="notice"><b>등록된 CSV에서 약품을 찾지 못했어요.</b>'
                "다른 검색어로 찾아보세요. 검색 결과가 없다는 것이 미허가 제품을 뜻하지는 않습니다.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="sec"><b>검색된 약품 목록</b><small>총 %d건</small></div>' % ss.total,
                unsafe_allow_html=True,
            )
            with st.container(border=False, key="reslist"):
                for i, rec in enumerate(ss.results):
                    drug_row(rec, i, "")


    else:
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            st.markdown('<div class="sec"><b>검색 기록</b></div>', unsafe_allow_html=True)
        with c2:
            if ss.history:
                st.button("전체 삭제", key="hist_clear", on_click=clear_list, args=("history",))
        if ss.history:
            st.pills("검색 기록", ss.history, selection_mode="single", key="hist_" + str(ss.hist_n),
                     on_change=on_pick_history, label_visibility="collapsed")
        else:
            st.markdown('<div class="empty">검색할 약품명을 입력하고 검색 버튼을 눌러주세요.</div>',
                        unsafe_allow_html=True)

    st.markdown('<div class="fine">' + FOOTER + "</div>", unsafe_allow_html=True)


def page_analyzing():
    if not ss.files or not ss.applied:
        ss.page = "home"
        st.rerun()

    f = ss.files[0]
    extra = " 외 %d장" % (len(ss.files) - 1) if len(ss.files) > 1 else ""
    st.markdown(
        '<div class="analyzing">'
        '<div class="scanbox"><img src="data:image/jpeg;base64,' + f["thumb"] + '"/></div>'
        '<div class="an-t">이미지 분석 중입니다<span class="dots"><b>.</b><b>.</b><b>.</b></span></div>'
        '<div class="an-s">' + esc(ss.applied["name"]) + extra
        + "<br>처음 실행할 때는 시간이 조금 더 걸려요</div></div>",
        unsafe_allow_html=True,
    )

    result, error = None, ""
    try:
        idx = ss.applied["idx"]
        texts = []
        for file in ss.files:
            texts += run_ocr_bytes(file["data"])
        res = verify(texts, db, idx)

        full = norm(" ".join(texts))
        ingrs = [x.strip() for x in str(db.iloc[idx]["주성분"]).split(",") if x.strip()]
        hits = [(ing, match_score(ing, texts, full) >= INGR_PASS) for ing in ingrs]
        n_hit = sum(h for _, h in hits)
        result = {
            "drug": ss.applied, "texts": texts,
            "status": res["status"], "message": res["message"], "detail": res.get("detail", {}),
            "hits": hits, "n_hit": n_hit, "n_ingr": len(ingrs),
            "ratio": n_hit / len(ingrs) if ingrs else 0,
            "time": datetime.now().strftime("%m.%d %H:%M"),
        }
    except Exception as e:
        error = "이미지 분석에 실패했습니다. 다른 사진으로 다시 시도해주세요. (%s)" % e

    if error:
        ss.err = error
        ss.page = "home"
    else:
        ss.result = result
        ss.analyses = ([result] + ss.analyses)[:30]
        ss.page = "result"
    st.rerun()


def page_result():
    r = ss.result
    if not r:
        ss.page = "home"
        st.rerun()
    topbar(back="home")

    ratio = r["ratio"]
    ingr_ok = ratio >= INGR_RATIO
    ing_cls = "ok" if ingr_ok else "bad"
    bar_color = "var(--green)" if ingr_ok else "var(--red)"
    msg_cls = "notice" if r["status"] == "genuine" else "err"

    st.markdown(
        '<div class="r-title">성분표 글자 비교 결과</div>'
        '<div class="r-drug">' + esc(r["drug"]["name"]) + "  ·  " + esc(r["drug"]["maker"]) + "</div>"
        '<div class="r-item"><span class="r-label">주성분 이름 검출</span>'
        '<span class="r-value ' + ing_cls + '">' + ("유사 표기 검출" if ingr_ok else "재촬영 필요") + "</span></div>"
        '<div class="r-item"><span class="r-label">성분명 검출률 (%d/%d개)</span>' % (r["n_hit"], r["n_ingr"])
        + '<span class="r-value ' + ing_cls + '">%.0f%%</span>' % (ratio * 100)
        + '<div class="bar"><i style="width:%.0f%%;background:%s"></i></div></div>' % (ratio * 100, bar_color)
        + '<div class="r-item"><span class="r-label">표기 비교 상태</span>' + verdict_span(r["status"]) + "</div>"
        + '<div class="' + msg_cls + '">' + esc(r["message"]) + "</div>",
        unsafe_allow_html=True,
    )

    st.button("상세 항목별 대조 리포트 확인하기", type="primary", key="btn_report", on_click=go, args=("report",))
    st.button("다른 사진으로 다시 분석", key="light_retry", on_click=retry_photos)
    st.button("메인화면으로 돌아가기", key="light_home1", on_click=reset_home)


def page_report():
    r = ss.result
    if not r:
        ss.page = "home"
        st.rerun()
    topbar(back="result")
    d = r["drug"]

    def tag(ok, yes="일치", no="불일치"):
        return '<span class="%s">%s</span>' % ("ok" if ok else "bad", yes if ok else no)

    maker_status = r["detail"].get("제조사 확인", "사진에서 찾지 못함")
    if maker_status.startswith("확인됨"):
        maker_ocr, maker_res = "검출", tag(True)
    elif maker_status.startswith("다른"):
        maker_ocr, maker_res = esc(maker_status), tag(False)
    else:
        maker_ocr, maker_res = "미검출", "확인 불가"

    rows = [("제품명", esc(d["name"]), "사용자 선택", tag(True, "확인")),
            ("제조사", esc(d["maker"] or "-"), maker_ocr, maker_res)]
    for ing, hit in r["hits"]:
        rows.append(("주성분", esc(ing), "검출" if hit else "미검출", tag(hit)))

    body = "".join(
        '<tr><td class="k">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % row for row in rows
    )
    st.markdown(
        '<div class="rpt-h">상세 항목별 대조 리포트</div>'
        '<table class="rpt"><colgroup><col style="width:22%"><col style="width:28%">'
        '<col style="width:32%"><col style="width:18%"></colgroup>'
        "<thead><tr><th>비교 항목</th><th>등록 CSV</th><th>이미지 OCR 검출값</th><th>비교 결과</th></tr></thead>"
        "<tbody>" + body + "</tbody></table>"
        '<div class="fine">' + FOOTER + "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("사진에서 인식된 글자 보기"):
        if r["texts"]:
            st.markdown("<br>".join(esc(t) for t in r["texts"]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">인식된 글자가 없습니다.</div>', unsafe_allow_html=True)

    st.button("메인화면으로 돌아가기", key="light_home2", on_click=reset_home)


def page_menu():
    with st.container(key="drawer"):
        topbar()
        st.button("약품 성분 검색/판별", icon=":material/search:", key="dr_home", on_click=go, args=("home",))
        label = "즐겨찾기" + ("  %d" % len(ss.bookmarks) if ss.bookmarks else "")
        st.button(label, icon=":material/bookmark:", key="dr_fav", on_click=go, args=("favorites",))

    with st.container(key="drawer_bottom"):
        c1, c2 = st.columns(2)
        with c1:
            st.button("마이메뉴", key="db_my", on_click=go, args=("mymenu",))
        with c2:
            st.button("설정", key="db_set", on_click=go, args=("settings",))


def page_favorites():
    topbar("즐겨찾기", back="menu")
    if not ss.bookmarks:
        st.markdown('<div class="empty">북마크된 약품이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="sec"><b>즐겨찾기한 약품 %d</b><small>눌러서 바로 사진 대조</small></div>'
            % len(ss.bookmarks),
            unsafe_allow_html=True,
        )
        with st.container(key="favlist"):
            for i, b in enumerate(ss.bookmarks):
                drug_row(b, i, "f")


def page_mymenu():
    topbar("마이메뉴", back="home")
    st.markdown('<div class="sec"><b>최근 판별 이력</b></div>', unsafe_allow_html=True)
    if not ss.analyses:
        st.markdown('<div class="empty">아직 판별한 이력이 없습니다.</div>', unsafe_allow_html=True)
    for i, r in enumerate(ss.analyses):
        with st.container(key="hrow_%d" % i):
            st.button("%s  ·  %s  ·  %s" % (r["drug"]["name"], VERDICT[r["status"]][0], r["time"]),
                      key="open_%d" % i, on_click=open_result, args=(r,))


def page_settings():
    topbar("설정", back="home")
    st.markdown('<div class="set-sec">데이터</div>', unsafe_allow_html=True)
    st.button("검색 기록 삭제", key="clr_h", on_click=clear_list, args=("history",))
    st.button("즐겨찾기 비우기", key="clr_b", on_click=clear_list, args=("bookmarks",))
    st.button("판별 이력 삭제", key="clr_a", on_click=clear_list, args=("analyses",))
    st.markdown('<div class="set-sec">앱 정보</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="fine">진짜약 (Jinzzayak) v1.0.0<br>등록 약품 %s건 · 저장소 제공 CSV (출처 검증 전)<br>'
        "기록과 즐겨찾기는 이 브라우저 세션 동안만 유지됩니다.</div>" % format(len(db), ","),
        unsafe_allow_html=True,
    )


PAGES = {
    "home": page_home, "analyzing": page_analyzing, "result": page_result, "report": page_report,
    "menu": page_menu, "favorites": page_favorites, "mymenu": page_mymenu, "settings": page_settings,
}
PAGES.get(ss.page, page_home)()
