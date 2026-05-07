import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import json
from datetime import date

st.set_page_config(
    page_title="CosRA Pro — Global Cosmetic Regulatory Checker",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# 1. 데이터 로드 로직 (JSON 파일 연동)
# ─────────────────────────────────────────────
@st.cache_data
def load_db_from_json():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

db_all = load_db_from_json()

# ─────────────────────────────────────────────
# 2. 성분 체크 핵심 함수
# ─────────────────────────────────────────────
def check_ingredient(inci, cas, conc, region_data):
    name = str(inci).upper().strip()
    
    # 금지 성분 체크
    for p in region_data.get("prohibited", []):
        if p.upper() in name:
            return {"label": "❌ 사용금지", "color": "red"}
            
    # 제한 성분 체크
    rest = region_data.get("restricted", {})
    for r_name, rule in rest.items():
        if r_name.upper() in name:
            limit = rule.get("max", 100)
            if conc is not None:
                try:
                    if float(conc) > limit:
                        return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
                except: pass
            return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
            
    return {"label": "✅ 안전", "color": "blue"}

# ─────────────────────────────────────────────
# 3. CSS 스타일링
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans KR', sans-serif; }
.main-title { font-size: 2.2rem; font-weight: 700; color: #1a1814; border-bottom: 3px solid #c8392b; padding-bottom: 8px; }
.badge { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
</style>
""", unsafe_allow_index=True)

st.markdown('<div class="main-title">CosRA Pro 🧴</div>', unsafe_allow_index=True)
st.write("Global Cosmetic Regulatory Compliance Checker (V2.1)")

# ─────────────────────────────────────────────
# 4. 사이드바 및 파일 로드
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    if not db_all:
        st.error("regulations.json 파일을 찾을 수 없습니다.")
        st.stop()
        
    region_options = list(db_all.keys())
    selected_regions = st.multiselect("분석 국가 선택", region_options, default=[region_options[0]])
    
    uploaded_file = st.file_uploader("원료 리스트 업로드", type=["pdf", "xlsx", "csv"])
    run_btn = st.button("🚀 분석 시작", use_container_width=True)

# ─────────────────────────────────────────────
# 5. 메인 로직
# ─────────────────────────────────────────────
if run_btn and uploaded_file:
    # 데이터 읽기 로직
    df = None
    if uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            rows = []
            for page in pdf.pages:
                table = page.extract_table()
                if table: rows.extend(table)
            if rows: df = pd.DataFrame(rows[1:], columns=rows[0])
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if df is not None:
        st.subheader("📋 분석 결과")
        
        # 결과 계산
        results = []
        for _, row in df.iterrows():
            inci = row.get("INCI") or row.get("Ingredient") or row.get("원료명") or ""
            cas = row.get("CAS") or ""
            conc = row.get("Content") or row.get("농도") or 0
            
            res_row = {"원료명": inci, "CAS": cas, "농도": conc}
            for region in selected_regions:
                check_res = check_ingredient(inci, cas, conc, db_all[region])
                res_row[db_all[region]['name']] = check_res['label']
            results.append(res_row)
        
        # 결과 출력
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        
        # 다운로드 버튼
        csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📊 결과 다운로드 (CSV)", data=csv, file_name="analysis_result.csv", mime="text/csv")
    else:
        st.error("파일에서 데이터를 읽을 수 없습니다. 형식을 확인해주세요.")

elif not uploaded_file and run_btn:
    st.warning("파일을 먼저 업로드해주세요.")
