import streamlit as st
import pandas as pd
import pdfplumber
import io
import json
from datetime import date

# 1. 페이지 설정
st.set_page_config(page_title="CosRA Pro", page_icon="🧴", layout="wide")

# 2. JSON 데이터 로드 함수
@st.cache_data
def load_db():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"데이터 파일을 읽을 수 없습니다: {e}")
        return {}

db_all = load_db()

# 3. 성분 체크 로직
def check_ingredient(inci, cas, conc, region_data):
    name = str(inci).upper().strip()
    for p in region_data.get("prohibited", []):
        if p.upper() in name:
            return {"label": "❌ 사용금지", "color": "red"}
    rest = region_data.get("restricted", {})
    for r_name, rule in rest.items():
        if r_name.upper() in name:
            limit = rule.get("max", 100)
            try:
                if float(conc) > limit:
                    return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
            except: pass
            return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
    return {"label": "✅ 안전", "color": "blue"}

# 4. UI 구성
st.title("CosRA Pro 🧴")
st.write("중동/아세안/유럽 규제 통합 분석기")

with st.sidebar:
    st.header("⚙️ 설정")
    if db_all:
        selected_regions = st.multiselect("분석 국가 선택", list(db_all.keys()), default=list(db_all.keys())[:1])
    uploaded_file = st.file_uploader("파일 업로드 (PDF, Excel)", type=["pdf", "xlsx", "csv"])
    run_btn = st.button("🚀 분석 시작", use_container_width=True)

# 5. 실행 로직
if run_btn and uploaded_file and db_all:
    # 파일 읽기
    if uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            rows = []
            for page in pdf.pages:
                table = page.extract_table()
                if table: rows.extend(table)
            df = pd.DataFrame(rows[1:], columns=rows[0]) if rows else None
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if df is not None:
        results = []
        for _, row in df.iterrows():
            # 컬럼명이 다를 경우를 대비해 유연하게 매칭
            inci = row.get("INCI") or row.get("원료명") or row.get("Ingredient") or ""
            conc = row.get("Content") or row.get("농도") or 0
            
            res_row = {"원료명": inci, "농도": conc}
            for region in selected_regions:
                check = check_ingredient(inci, "", conc, db_all[region])
                res_row[db_all[region]['name']] = check['label']
            results.append(res_row)
        
        st.success("분석 완료!")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.error("파일에서 데이터를 추출하지 못했습니다.")
