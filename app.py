import streamlit as st
import pandas as pd
import pdfplumber
import json
import re
import io

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="CosRA Pro v3.0", page_icon="🧴", layout="wide")

# 2. 규제 DB 로드 함수 (regulations.json 파일을 읽어옴)
@st.cache_data(ttl=60)
def load_db():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"데이터 파일(regulations.json)을 찾을 수 없거나 형식이 잘못되었습니다: {e}")
        return {}

db_all = load_db()

# 3. 텍스트 표준화 함수 (대소문자, 공백, 하이픈 무시)
def clean_text(text):
    if text is None or pd.isna(text) or str(text).lower() == 'nan':
        return ""
    return str(text).upper().replace("-", "").replace(" ", "").strip()

# 4. 핵심 분석 로직 (원료명, CAS, 농도 3중 체크)
def check_ingredient(inci, cas, conc, region_data):
    search_inci = clean_text(inci)
    search_cas = clean_text(cas)
    
    # (1) 금지 성분 체크 (이름 또는 CAS 번호가 하나라도 일치하면 차단)
    prohibited_list = region_data.get("prohibited", [])
    for p in prohibited_list:
        p_name = clean_text(p.get("name", ""))
        p_cas = clean_text(p.get("cas", ""))
        
        # 이름 매칭 또는 CAS 번호 매칭 확인
        name_match = (p_name != "" and p_name in search_inci)
        cas_match = (p_cas != "" and p_cas == search_cas)
        
        if name_match or cas_match:
            return {"label": "❌ 사용금지", "color": "red"}
            
    # (2) 제한 성분 체크 (농도 확인)
    rest = region_data.get("restricted", {})
    # CAS번호로 먼저 찾고, 없으면 이름으로 찾음
    matched_rule = rest.get(search_cas) or rest.get(search_inci)
    
    if matched_rule:
        limit = matched_rule.get("max", 100)
        try:
            # 농도 텍스트에서 숫자와 소수점만 추출 (예: "1.2%" -> 1.2)
            pure_conc = float(re.sub(r'[^0-9.]', '', str(conc)))
            if pure_conc > limit:
                return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
        except:
            pass
        return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
        
    return {"label": "✅ 안전/확인불가", "color": "blue"}

# 5. 메인 UI 구성
st.title("CosRA Pro 🧴 (Professional RA System)")
st.markdown("### 원료명 + CAS No. + 농도 교차 분석 시스템")
st.info("출처: EU CosIng, UK OPSS, FDA MoCRA, MHLW Japan, GSO 1943 (2026 Updated)")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    if db_all:
        all_regions = list(db_all.keys())
        selected_regions = st.multiselect("분석 대상 국가 선택", all_regions, default=all_regions)
    else:
        st.warning("regulations.json 파일이 필요합니다.")
        
    uploaded_file = st.file_uploader("분석할 파일 업로드 (PDF, Excel, CSV)", type=["pdf", "xlsx", "csv"])
    run_btn = st.button("🚀 분석 시작", use_container_width=True)

# 6. 파일 처리 및 결과 출력
if run_btn and uploaded_file and db_all:
    df = None
    # 파일 타입별 읽기 로직
    if uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            all_rows = []
            for page in pdf.pages:
                table = page.extract_table()
                if table: all_rows.extend(table)
            if all_rows:
                df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if df is not None:
        # 데이터 정리 (빈 행 제거 등)
        df = df.dropna(how='all').reset_index(drop=True)
        cols = [str(c).upper().strip() for c in df.columns]
        
        # 컬럼 자동 매칭 (제목이 조금 달라도 찾아냄)
        idx_name = next((i for i, c in enumerate(cols) if any(k in c for k in ["INCI", "원료", "NAME", "INGREDIENT"])), None)
        idx_cas = next((i for i, c in enumerate(cols) if any(k in c for k in ["CAS"])), None)
        idx_conc = next((i for i, c in enumerate(cols) if any(k in c for k in ["CONC", "농도", "CONTENT", "%", "함량"])), None)

        if idx_name is not None:
            final_results = []
            for _, row in df.iterrows():
                name_val = row.iloc[idx_name]
                cas_val = row.iloc[idx_cas] if idx_cas is not None else ""
                conc_val = row.iloc[idx_conc] if idx_conc is not None else 0
                
                res_row = {"원료명": name_val, "CAS No.": cas_val, "농도": conc_val}
                
                # 선택한 국가별로 규제 체크
                for reg_id in selected_regions:
                    region_info = db_all[reg_id]
                    check_res = check_ingredient(name_val, cas_val, conc_val, region_info)
                    res_row[region_info['name']] = check_res['label']
                
                final_results.append(res_row)
            
            # 최종 결과 테이블 출력
            st.success(f"총 {len(final_results)}개의 성분 분석이 완료되었습니다.")
            st.dataframe(pd.DataFrame(final_results), use_container_width=True)
        else:
            st.error("파일에서 '원료명(INCI)' 컬럼을 찾을 수 없습니다. 엑셀 첫 줄의 제목을 확인해주세요.")
    else:
        st.error("파일을 읽는 데 실패했습니다.")
