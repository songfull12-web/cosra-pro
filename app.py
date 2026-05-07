import streamlit as st
import pandas as pd
import pdfplumber
import json
import re
import io

# 1. 페이지 설정
st.set_page_config(page_title="CosRA Pro v3.3", page_icon="🧴", layout="wide")

# 2. 규제 DB 로드
@st.cache_data(ttl=60)
def load_db():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"데이터 파일 로드 실패: {e}")
        return {}

db_all = load_db()

# 3. 텍스트 표준화 (에러 방지용)
def clean_text(text):
    if text is None or pd.isna(text): return ""
    return str(text).upper().replace("-", "").replace(" ", "").strip()

# 4. 분석 로직
def check_ingredient(inci, cas, conc, region_data):
    search_inci = clean_text(inci)
    search_cas = clean_text(cas)
    if not search_inci and not search_cas: return {"label": "-", "color": "white"}
    
    # (1) 금지 체크
    prohibited = region_data.get("prohibited", [])
    for p in prohibited:
        if isinstance(p, dict):
            p_n, p_c = clean_text(p.get("name")), clean_text(p.get("cas"))
            if (p_n and p_n in search_inci) or (p_c and p_c == search_cas):
                return {"label": "❌ 사용금지", "color": "red"}
    
    # (2) 제한 체크
    rest = region_data.get("restricted", {})
    matched = rest.get(search_cas) or rest.get(search_inci)
    if matched:
        limit = matched.get("max", 100)
        try:
            val = float(re.sub(r'[^0-9.]', '', str(conc)))
            if val > limit: return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
        except: pass
        return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
    return {"label": "✅ 안전/확인불가", "color": "blue"}

# 5. UI
st.title("CosRA Pro 🧴 (Excel 판독 강화판)")

with st.sidebar:
    st.header("⚙️ 설정")
    sel_regions = st.multiselect("국가 선택", list(db_all.keys()), default=list(db_all.keys()))
    up_file = st.file_uploader("엑셀/PDF 업로드", type=["xlsx", "pdf", "csv"])
    run_btn = st.button("🚀 분석 시작")

# 6. 파일 읽기 핵심 로직
if run_btn and up_file and db_all:
    df = None
    try:
        if up_file.name.endswith(".pdf"):
            with pdfplumber.open(up_file) as pdf:
                rows = []
                for p in pdf.pages:
                    tbl = p.extract_table()
                    if tbl: rows.extend(tbl)
                if rows: df = pd.DataFrame(rows[1:], columns=rows[0])
        
        elif up_file.name.endswith(".xlsx"):
            # 엑셀 시트 전체를 읽어서 헤더 위치 검색
            tmp_df = pd.read_excel(up_file, header=None, engine='openpyxl')
            header_idx = 0
            for i, r in tmp_df.iterrows():
                r_str = " ".join(r.fillna("").astype(str).upper())
                if any(k in r_str for k in ["INCI", "원료", "NAME", "CAS"]):
                    header_idx = i
                    break
            # 실제 데이터 로드
            up_file.seek(0)
            df = pd.read_excel(up_file, skiprows=header_idx, engine='openpyxl')
        
        else:
            df = pd.read_csv(up_file)

        if df is not None:
            df.columns = [str(c).upper().strip() for c in df.columns]
            df = df.dropna(how='all').reset_index(drop=True)
            
            i_n = next((i for i, c in enumerate(df.columns) if any(k in c for k in ["INCI", "원료", "NAME"])), None)
            i_ca = next((i for i, c in enumerate(df.columns) if "CAS" in c), None)
            i_co = next((i for i, c in enumerate(df.columns) if any(k in c for k in ["CONC", "농도", "CONTENT", "%"])), None)

            if i_n is not None:
                res = []
                for _, r in df.iterrows():
                    n, ca, co = r.iloc[i_n], r.iloc[i_ca] if i_ca is not None else "", r.iloc[i_co] if i_co is not None else 0
                    if pd.isna(n) and not ca: continue
                    row_data = {"원료명": n, "CAS": ca, "농도": co}
                    for rid in sel_regions:
                        c = check_ingredient(n, ca, co, db_all[rid])
                        row_data[db_all[rid]['name']] = c['label']
                    res.append(row_data)
                st.success(f"총 {len(res)}건 분석 완료")
                st.dataframe(pd.DataFrame(res), use_container_width=True)
            else:
                st.error("컬럼명을 찾을 수 없습니다. (INCI, 원료명 등 확인 필요)")
    except Exception as e:
        st.error(f"에러 발생: {e}")
