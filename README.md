# 진짜약 · JinzzaYak

약품을 검색하고 포장지 사진에서 읽은 제조사·주성분을 CSV 데이터와 비교하는 Streamlit 앱입니다.

## 실행

Python 3.12 기준:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저에서 http://localhost:8501에 접속합니다. 최초 실행 시 한국어·영어 OCR 모델을 다운로드합니다.

- `app.py`: 검색, 사진 OCR, 비교 결과, 북마크·기록
- `drugs.csv`: 팀 제공 약품 데이터
- `requirements.txt`: 실행 의존성

OCR: [EasyOCR](https://github.com/JaidedAI/EasyOCR) · 표기 비교: [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)

기록은 브라우저 세션 동안 유지됩니다. 결과는 포장지 글자 비교이며 정품 인증·실제 성분 검사·복용 판단이 아닙니다.
