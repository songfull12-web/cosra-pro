import streamlit as st
import pandas as pd
import pdfplumber
import json
import re
import io

# 1. 페이지 설정
st.set_page_config(page_title="CosRA Pro v3.2", page_icon="🧴", layout="wide")

# 2. 규제 DB 로드 함수
@st.cache_data(ttl=60)
def load_db():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"데이터 파일(regulations.json) 로드 실패: {e}")
        return {}

db_all = load_db()

# 3. 텍스트 표준화 함수 (데이터 타입 에러 방지)
def clean_text(text):
    if text is None or pd.isna(text):
        return ""
    # 리스트나 시리즈 형태일 경우 첫 번째 요소만 사용하거나 문자열로 합침
    if isinstance(text, (list, pd.Series)):
        text = " ".join(map(str, text))
    return str(text).upper().replace("-", "").replace(" ", "").strip()

# 4. 분석 로직
def check_ingredient(inci, cas, conc, region_data):
    search_inci = clean_text(inci)
    search_cas = clean_text(cas)
    
    if not search_inci and not search_cas:
        return {"label": "-", "color": "white"}
    
    # (1) 금지 성분 체크
    prohibited_list = region_data.get("prohibited", [])
    for p in prohibited_list:
        if isinstance(p, dict):
            p_name = clean_text(p.get("name", ""))
            p_cas = clean_text(p.get("cas", ""))
            if (p_name != "" and p_name in search_inci) or (p_cas != "" and p_cas == search_cas):
                return {"label": "❌ 사용금지", "color": "red"}
            
    # (2) 제한 성분 체크
    rest = region_data.get("restricted", {})
    matched_rule = rest.get(search_cas) or rest.get(search_inci)
    
    if matched_rule:
        limit = matched_rule.get("max", 100)
        try:
            pure_conc = float(re.sub(r'[^0-9.]', '', str(conc)))
            if pure_conc > limit:
                return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
        except:
            pass
        return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
        
    return {"label": "✅ 안전/확인불가", "color": "blue"}

# 5. 메인 UI
st.title("CosRA Pro 🧴 (Professional RA System)")
st.info("지원 국가: EU, UK, USA, JPN, GCC | 분석 기준: INCI, CAS No., 농도")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    if db_all:
        selected_regions = st.multiselect("분석 대상 국가", list(db_all.keys()), default=list(db_all.keys()))
    uploaded_file = st.file_uploader("파일 업로드 (Excel, PDF, CSV)", type=["xlsx", "pdf", "csv"])
    run_btn = st.button("🚀 분석 시작", use_container_width=True)

# 6. 파일 읽기 및 전처리
if run_btn and uploaded_file and db_all:
    df = None
    try:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table: all_rows.extend(table)
                if all_rows:
                    df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
        
        elif uploaded_file.name.endswith(".xlsx"):
            # 엑셀의 모든 행을 일단 읽어옴
            df_raw = pd.read_excel(uploaded_file, header=None)
            
            # 헤더 위치 찾기 로직 강화
            header_row_idx = 0
            for i, row in df_raw.iterrows():
                # 행 전체를 하나의 문자열로 합쳐서 키워드 검색
                row_str = " ".join(row.fillna("").astype(str).upper())
                if any(k in row_str for k in ["INCI", "원료", "NAME", "INGREDIENT"]):
                    header_row_idx = i
                    break
            
            # 찾은 헤더를 기준으로 데이터 다시 읽기
            df = pd.read_excel(uploaded_file, skiprows=header_row_idx)
            
        else:
            df = pd.read_csv(uploaded_file)

        if df is not None:
            # 모든 컬럼명을 안전하게 문자열로 변환 후 대문자 처리
            df.columns = [str(c).upper().strip() for c in df.columns]
            df = df.dropna(how='all').reset_index(drop=True)
            
            # 인덱스 매칭
            idx_name = next((i for i, c in enumerate(df.columns) if any(k in c for k in ["INCI", "원료", "NAME", "INGREDIENT"])), None)
            idx_cas = next((i for i, c in enumerate(df.columns) if any(k in c for k in ["CAS"])), None)
            idx_conc = next((i for i, c in enumerate(df.columns) if any(k in c for k in ["CONC", "농도", "CONTENT", "%", "함량"])), None)

            if idx_name is not None:
                final_results = []
                for _, row in df.iterrows():
                    name_val = row.iloc[idx_name]
                    cas_val = row.iloc[idx_cas] if idx_cas is not None else ""
                    conc_val = row.iloc[idx_conc] if idx_conc is not None else 0
                    
                    if pd.isna(name_val) and pd.isna(cas_val): continue
                    
                    res_row = {"원료명": name_val, "CAS No.": cas_val, "농도": conc_val}
                    for reg_id in selected_regions:
                        region_info = db_all[reg_id]
                        check_res = check_ingredient(name_val, cas_val, conc_val, region_info)
                        res_row[region_info['name']] = check_res['label']
                    
                    final_results.append(res_row)
                
                st.success(f"분석 완료! (총 {len(final_results)}건)")
                st.dataframe(pd.DataFrame(final_results), use_container_width=True)
            else:
                st.error("파일에서 '원료명(INCI)' 컬럼을 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"파일 처리 중 에러 발생: {e}")
