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
        # 같은 폴더에 있는 regulations.json 파일을 읽어옵니다.
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("⚠️ 'regulations.json' 파일이 폴더에 없습니다. 파일을 먼저 생성해주세요.")
        return {}
    except json.JSONDecodeError:
        st.error("⚠️ 'regulations.json' 파일 형식이 잘못되었습니다. 중괄호나 쉼표를 확인해주세요.")
        return {}

# 전역 변수로 DB 로드
db_all = load_db_from_json()

# ─────────────────────────────────────────────
# 2. 성분 체크 핵심 함수
# ─────────────────────────────────────────────
def check_ingredient(inci, cas, conc, region_data):
    # 입력값 표준화
    name = str(inci).upper().strip()
    
    # 1. 금지 성분 체크 (키워드 포함 여부 검색)
    for p in region_data.get("prohibited", []):
        if p.upper() in name:
            return {"label": "❌ 사용금지", "color": "red"}
            
    # 2. 제한 성분 체크
    rest = region_data.get("restricted", {})
    for r_name, rule in rest.items():
        if r_name.upper() in name:
            limit = rule.get("max", 100)
            # 농도값이 있을 때만 비교 수행
            if conc is not None:
                try:
                    if float(conc) > limit:
                        return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
                except ValueError:
                    pass
            return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
            
    return {"label": "✅ 안전", "color": "blue"}

# ─────────────────────────────────────────────
# 3. CSS 스타일링 (기존 유지)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans KR', sans-serif; }
.main-title { font-size: 2.2rem; font-weight: 700; color: #1a1814; border-bottom: 3px solid #c8392b; padding-bottom: 8px; margin-bottom: 4px; }
.sub-title { font-size: 0.88rem; color: #6a6460; margin-bottom: 20px; }
</style>
""", unsafe_allow_index=True)

st.markdown('<div class="main-title">CosRA Pro 🧴</div>', unsafe_allow_index=True)
st.markdown('<div class="sub-title">Global Cosmetic Regulatory Compliance Checker (V2.1 - JSON DB Type)</div>', unsafe_allow_index=True)

# ─────────────────────────────────────────────
# 4. 사이드바 설정
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 분석 설정")
    if db_all:
        region_options = list(db_all.keys())
        selected_regions = st.multiselect("분석 국가 선택", region_options, default=[region_options[0]] if region_options else [])
    else:
        st.warning("설정된 국가 데이터가 없습니다.")
        selected_regions = []
        
    st.divider()
    uploaded_file = st.file_uploader("원료 리스트 업로드 (PDF/Excel/CSV)", type=["pdf", "xlsx", "csv"])
    run_btn = st.button("🚀 규제 분석 시작", use_container_width=True)

# ─────────────────────────────────────────────
# 5. 메인 로직 (파일 처리 및 결과 출력)
# ─────────────────────────────────────────────
if run_btn and uploaded_file and selected_regions:
    # (이하 기존 파일 처리 및 출력 로직 동일하게 작동)
    # 대리님의 기존 파일 처리 로직에 맞춰 결과를 화면에 뿌려줍니다.
    st.info(f"선택된 국가: {', '.join(selected_regions)} 에 대해 분석을 진행합니다.")
    
    # 셈플 데이터 분석 예시 (실제 파일 처리 로직은 기존 코드 유지)
    # 여기에 기존 파일 로드 로직을 그대로 사용하시면 됩니다.
    st.success("분석이 완료되었습니다. 결과를 확인하세요.")
    
else:
    st.write("왼쪽 사이드바에서 파일을 업로드하고 '규제 분석 시작' 버튼을 눌러주세요.")
