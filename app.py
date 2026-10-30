import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import easyocr
import re

st.set_page_config(
    page_title="PillGuard - AI 약 성분 판별기",
    page_icon="💊",
    layout="wide"
)

# 1. EasyOCR 캐싱 로드
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

try:
    with st.spinner("AI OCR 엔진을 로딩 중입니다... 잠시만 기다려주세요."):
        reader = get_ocr_reader()
except Exception as e:
    st.error(f"OCR 엔진 로딩 실패: {e}")

# 2. drug.csv 파일 로드 (캐싱 적용)
@st.cache_data
def load_drug_data():
    try:
        # 파일 인코딩에 따라 utf-8 또는 cp949(euc-kr) 지정 필요할 수 있음
        df = pd.read_csv('drug.csv', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv('drug.csv', encoding='cp949')
    return df

try:
    df_drugs = load_drug_data()
except Exception as e:
    st.error(f"drug.csv 파일을 읽어오는 데 실패했습니다. 파일명을 확인해주세요. 에러: {e}")
    st.stop()

st.title("💊 PillGuard: 스마트 약 성분 및 정·가품 판별 시스템")
st.markdown("식약처 표준 데이터셋과 EasyOCR을 활용하여 업로드된 성분표 이미지를 실시간으로 비교 검증합니다.")
st.markdown("---")

# 세션 상태 초기화
if 'applied_drug' not in st.session_state:
    st.session_state.applied_drug = None

# ==========================================
# STEP 1 & 2 & 3: 약품 검색, 선택 및 적용
# ==========================================
st.header("Step 1. 기준 의약품 검색 및 적용")

# CSV 파일의 컬럼명에 맞춰 수정 필요 (예: '약품명', '주성분' 등 컬럼 이름 확인)
# 사용자 CSV 구조에 맞춰 아래 컬럼명을 변경해 주세요.
col_name_key = "약품명"       # CSV 안의 약품명 컬럼 이름
ingredient_key = "주성분"     # CSV 안의 주성분 컬럼 이름
code_key = "품목기준코드"     # CSV 안의 품목기준코드 컬럼 이름
content_key = "함량"          # CSV 안의 함량 컬럼 이름
eng_key = "영문명"            # CSV 안의 영문명 컬럼 이름 (없으면 생략 가능)

col_search1, col_search2 = st.columns([3, 1])

with col_search1:
    search_query = st.text_input("검색할 약품명을 입력하세요 (예: 포도당, 타이레놀)", "")

# CSV 데이터에서 검색 필터링
if search_query:
    matched_df = df_drugs[
        df_drugs[col_name_key].astype(str).str.contains(search_query, case=False, na=False) | 
        df_drugs[ingredient_key].astype(str).str.contains(search_query, case=False, na=False)
    ]
else:
    matched_df = df_drugs

drug_names = matched_df[col_name_key].tolist() if not matched_df.empty else ["검색 결과 없음"]

selected_drug_name = st.selectbox("검색된 약품 목록에서 선택", drug_names)

with col_search2:
    st.write("") 
    st.write("")
    apply_btn = st.button("약품 적용 🔌", type="primary", use_container_width=True)

if apply_btn:
    if not matched_df.empty and selected_drug_name != "검색 결과 없음":
        # 선택된 행의 데이터 추출
        selected_row = matched_df[matched_df[col_name_key] == selected_drug_name].iloc[0]
        
        st.session_state.applied_drug = {
            "약품명": str(selected_row[col_name_key]),
            "품목기준코드": str(selected_row[code_key]),
            "주성분": str(selected_row[ingredient_key]),
            "함량": str(selected_row[content_key]),
            "영문명": str(selected_row.get(eng_key, ""))
        }
        st.success(f"'{selected_drug_name}' 정품 기준 데이터가 성공적으로 적용되었습니다!")
    else:
        st.warning("적용할 유효한 약품을 선택해주세요.")

# 적용된 약품 정보 카드 표시
if st.session_state.applied_drug:
    drug = st.session_state.applied_drug
    st.info(f"📌 **현재 적용된 기준 약품**: **{drug['약품명']}** (코드: `{drug['품목기준코드']}`) | 주성분: **{drug['주성분']} ({drug['함량']})**")
