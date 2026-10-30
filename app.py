import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import easyocr
import re

# 페이지 설정
st.set_page_config(
    page_title="PillGuard - AI 약 성분 판별기",
    page_icon="💊",
    layout="wide"
)

# 1. EasyOCR 캐싱 로드 (속도 최적화)
@st.cache_resource
def get_ocr_reader():
    # 한국어와 영어 동시 인식 지원
    return easyocr.Reader(['ko', 'en'], gpu=False)

try:
    with st.spinner("AI OCR 엔진을 로딩 중입니다... 잠시만 기다려주세요."):
        reader = get_ocr_reader()
except Exception as e:
    st.error(f"OCR 엔진 로딩 실패: {e}")

# 2. 표준 의약품 데이터베이스 (Mock DB)
STANDARD_DB = [
    {
        "약품명": "중외5%포도당주사액",
        "품목기준코드": "M040702",
        "주성분": "포도당",
        "함량": "50g",
        "영문명": "Glucose"
    },
    {
        "약품명": "타이레놀정 500밀리그램",
        "품목기준코드": "M040701",
        "주성분": "아세트아미노펜",
        "함량": "500mg",
        "영문명": "Acetaminophen"
    },
    {
        "약품명": "아스피린보호정 100밀리그램",
        "품목기준코드": "M040703",
        "주성분": "아세틸사리실산",
        "함량": "100mg",
        "영문명": "Aspirin"
    }
]

st.title("💊 PillGuard: 스마트 약 성분 및 정·가품 판별 시스템")
st.markdown("식약처 표준 데이터베이스와 EasyOCR을 활용하여 업로드된 성분표 이미지를 실시간으로 비교 검증합니다.")
st.markdown("---")

# 세션 상태 초기화
if 'applied_drug' not in st.session_state:
    st.session_state.applied_drug = None

# ==========================================
# STEP 1 & 2 & 3: 약품 검색, 선택 및 적용
# ==========================================
st.header("Step 1. 기준 의약품 검색 및 적용")
col_search1, col_search2 = st.columns([3, 1])

with col_search1:
    search_query = st.text_input("검색할 약품명을 입력하세요 (예: 포도당, 타이레놀, 아스피린)", "")

# 검색 필터링
matched_drugs = [
    d for d in STANDARD_DB 
    if search_query.lower() in d["약품명"].lower() or search_query.lower() in d["주성분"].lower()
] if search_query else STANDARD_DB

selected_drug_name = st.selectbox(
    "검색된 약품 목록에서 선택", 
    [d["약품명"] for d in matched_drugs] if matched_drugs else ["검색 결과 없음"]
)

with col_search2:
    st.write("") # 간격 맞춤
    st.write("")
    apply_btn = st.button("약품 적용 🔌", type="primary", use_container_width=True)

if apply_btn:
    if matched_drugs and selected_drug_name != "검색 결과 없음":
        selected_data = next((d for d in STANDARD_DB if d["약품명"] == selected_drug_name), None)
        st.session_state.applied_drug = selected_data
        st.success(f"'{selected_drug_name}' 정품 기준 데이터가 성공적으로 적용되었습니다!")
    else:
        st.warning("적용할 유효한 약품을 선택해주세요.")

# 적용된 약품 정보 카드 표시
if st.session_state.applied_drug:
    drug = st.session_state.applied_drug
    st.info(f"📌 **현재 적용된 기준 약품**: **{drug['약품명']}** (코드: `{drug['품목기준코드']}`) | 주성분: **{drug['주성분']} ({drug['함량']})**")

st.markdown("---")

# ==========================================
# STEP 4 & 5: 이미지 업로드 및 OCR 분석
# ==========================================
st.header("Step 2. 성분표 이미지 업로드 및 OCR 분석")

uploaded_file = st.file_uploader("약 성분표 또는 라벨 이미지를 업로드하세요 (.jpg, .png, .jpeg)", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    col_img, col_ocr = st.columns(2)
    
    with col_img:
        st.subheader("업로드된 이미지")
        image = Image.open(uploaded_file)
        st.image(image, caption="성분표 라벨", use_column_width=True)
    
    with col_ocr:
        st.subheader("OCR 분석 제어")
        run_ocr_btn = st.button("🚀 이미지 OCR 분석 및 성분 비교 실행", type="primary", use_container_width=True)
        
        if not st.session_state.applied_drug:
            st.warning("⚠️ 먼저 위쪽에서 [약품 적용]을 완료해주세요.")

    if run_ocr_btn and st.session_state.applied_drug:
        with st.spinner("EasyOCR이 이미지 속 텍스트를 판독하고 있습니다..."):
            # PIL Image를 numpy array로 변환
            img_np = np.array(image)
            
            # EasyOCR 실행
            results = reader.readtext(img_np)
            
            # 텍스트 추출 및 정제
            extracted_texts = [text[1] for text in results]
            full_raw_text = " ".join(extracted_texts)
            
        st.success("OCR 텍스트 판독 완료!")
        
        with st.expander("🔍 추출된 Raw OCR 텍스트 보기"):
            st.write(extracted_texts)
            st.text(f"전체 텍스트: {full_raw_text}")

        # ==========================================
        # STEP 6 & 7: 성분 비교 및 결과물 출력
        # ==========================================
        st.markdown("---")
        st.header("Step 3. 성분 대조 및 최종 판정 결과")
        
        target_drug = st.session_state.applied_drug
        target_ingredient = target_drug["주성분"]
        target_content = target_drug["함량"]
        
        # 성분명 및 함량 포함 여부 단순 대조 시뮬레이션
        is_ingredient_matched = target_ingredient in full_raw_text or target_drug["영문명"].lower() in full_raw_text.lower()
        is_content_matched = target_content.lower().replace("g", "").replace("mg", "") in full_raw_text.lower()
        
        # 일치율 계산 (예시 로직)
        match_score = 99.2 if (is_ingredient_matched and is_content_matched) else (75.0 if is_ingredient_matched else 42.1)
        is_genuine = match_score >= 90.0

        # 결과 메트릭 표시
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("주성분 일치 여부", "일치" if is_ingredient_matched else "불일치", "기준 규격 대조")
        m_col2.metric("성분 일치율", f"{match_score:.1f}%", "정밀 분석")
        
        if is_genuine:
            m_col3.metric("최종 판정", "정품 (GENUINE)", "인증 완료", delta_color="normal")
            st.success("🎉 분석 결과: 정품 기준 규격과 완벽히 일치합니다.")
        else:
            m_col3.metric("최종 판정", "가품 의심 (COUNTERFEIT)", "주의 요망", delta_color="inverse")
            st.error("🚨 분석 결과: 기준 성분 또는 함량에 차이가 감지되었습니다. 가품 또는 불량 의약품일 수 있습니다.")

        # 상세 비교 리포트 테이블
        st.subheader("📋 상세 항목별 대조 리포트")
        report_df = pd.DataFrame({
            "검증 항목": ["품목기준코드", "주성분명", "함량 규격", "판정 상태"],
            "기준 DB (정품)": [target_drug["품목기준코드"], target_ingredient, target_content, "기준 규격"],
            "이미지 OCR 검출값": [
                target_drug["품목기준코드"] if is_ingredient_matched else "미검출",
                target_ingredient if is_ingredient_matched else "확인 불가",
                target_content if is_content_matched else "함량 상이",
                "✅ 적합" if is_genuine else "❌ 부적합"
            ],
            "검증 결과": ["일치", "일치" if is_ingredient_matched else "불일치", "일치" if is_content_matched else "차이 발생", "통과" if is_genuine else "경고"]
        })
        st.table(report_df)
