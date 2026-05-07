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
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans KR', sans-serif; }

.main-title {
    font-size: 2.2rem; font-weight: 700; color: #1a1814;
    border-bottom: 3px solid #c8392b; padding-bottom: 8px; margin-bottom: 4px;
}
.sub-title { font-size: 0.88rem; color: #6a6460; margin-bottom: 20px; }

.badge-danger {
    background: #fde8e7; color: #c8392b; border: 1px solid #f5c0bc;
    padding: 2px 10px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
}
.badge-warn {
    background: #fef3e0; color: #d4860a; border: 1px solid #f5dca0;
    padding: 2px 10px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
}
.badge-ok {
    background: #e8f5ee; color: #2a7a4b; border: 1px solid #b0dfc0;
    padding: 2px 10px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
}
.badge-cond {
    background: #e8f0fa; color: #2b5c8a; border: 1px solid #b0c8e8;
    padding: 2px 10px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
}
.badge-nodata {
    background: #f0f0ee; color: #8a8480; border: 1px solid #d0d0cc;
    padding: 2px 10px; border-radius: 3px; font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
}
.metric-card {
    background: white; border: 1px solid #e0ddd8; border-radius: 8px;
    padding: 16px; text-align: center;
}
.metric-num { font-size: 2.2rem; font-weight: 700; line-height: 1; }
.metric-lbl { font-size: 0.72rem; color: #8a8480; margin-top: 4px; font-family: 'IBM Plex Mono', monospace; }
.section-header {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #8a8480;
    border-left: 3px solid #c8392b; padding-left: 8px; margin-bottom: 8px;
}
.link-box {
    background: #f8f7f4; border: 1px solid #e0ddd8; border-radius: 6px;
    padding: 8px 12px; margin-bottom: 6px; font-size: 0.78rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# REGULATION DATABASE
# ─────────────────────────────────────────────
@st.cache_data
def get_regulation_db():
    return {
"EU": {
    "name": "🇪🇺 EU", "regulation": "Regulation (EC) No 1223/2009",
    "source": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02009R1223-20230401",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "Annex II #221"},
        {"inci": "LEAD ACETATE", "cas": "301-04-2", "note": "Annex II #84"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "Annex II #84"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "Annex II #14"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "Annex II #437"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "Annex II #413"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "Annex II #13"},
        {"inci": "BITHIONOL", "cas": "97-18-7", "note": "Annex II"},
        {"inci": "CHLOROFORM", "cas": "67-66-3", "note": "Annex II #44"},
        {"inci": "BENZENE", "cas": "71-43-2", "note": "Annex II #178"},
        {"inci": "METHANOL", "cas": "67-56-1", "note": "Annex II #243"},
        {"inci": "SELENIUM SULFIDE", "cas": "7446-34-6", "note": "Annex II"},
        {"inci": "LILIAL", "cas": "80-54-6", "note": "Annex II (2022년 금지)"},
        {"inci": "BUTYLPHENYL METHYLPROPIONAL", "cas": "80-54-6", "note": "Annex II (2022년 금지)"},
    ],
    "restricted": [
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25, "unit": "%", "condition": "나노폼 [nano] 표시 의무", "note": "Annex VI #30", "flag": "ok"},
        {"inci": "TITANIUM DIOXIDE", "cas": "13463-67-7", "max_conc": 25, "unit": "%", "condition": "흡입형 나노TiO2 금지", "note": "Annex VI", "flag": "warn"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": 0.01, "unit": "% (leave-on)", "condition": "알레르겐 표시 의무 (0.001% 초과 시)", "note": "Annex III #86", "flag": "warn"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": 0.025, "unit": "%", "condition": "알레르겐 표시 의무", "note": "Annex III #36", "flag": "warn"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": 0.01, "unit": "% (leave-on)", "condition": "알레르겐 표시 의무", "note": "Annex III #69", "flag": "warn"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": 0.01, "unit": "% (leave-on)", "condition": "알레르겐 표시 의무", "note": "Annex III #33", "flag": "warn"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": 0.01, "unit": "% (leave-on)", "condition": "알레르겐 표시 의무", "note": "Annex III #10", "flag": "warn"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": 0.01, "unit": "% (leave-on)", "condition": "알레르겐 표시 의무", "note": "Annex III #2", "flag": "warn"},
        {"inci": "EUGENOL", "cas": "97-53-0", "max_conc": 0.01, "unit": "%", "condition": "알레르겐 표시 의무", "note": "Annex III #46", "flag": "warn"},
        {"inci": "ISOEUGENOL", "cas": "97-54-1", "max_conc": 0.001, "unit": "%", "condition": "알레르겐 — 극저농도 한도", "note": "Annex III #75", "flag": "warn"},
        {"inci": "CINNAMAL", "cas": "104-55-2", "max_conc": 0.001, "unit": "%", "condition": "알레르겐 표시 의무", "note": "Annex III #30", "flag": "warn"},
        {"inci": "HYDROXYCITRONELLAL", "cas": "107-75-5", "max_conc": 0.01, "unit": "%", "condition": "알레르겐 표시 의무", "note": "Annex III #71", "flag": "warn"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": 0.3, "unit": "%", "condition": "face 0.3%, body 0.05% 한도 (2025~)", "note": "Annex III", "flag": "warn"},
        {"inci": "RETINYL PALMITATE", "cas": "79-81-2", "max_conc": 0.3, "unit": "%", "condition": "레티놀 당량 환산", "note": "Annex III", "flag": "warn"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "3세 미만 기저귀 부위 금지", "note": "Annex V #29", "flag": "warn"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "단독 0.4% / 복합 0.8%", "note": "Annex V", "flag": "warn"},
        {"inci": "PROPYLPARABEN", "cas": "94-13-3", "max_conc": 0.14, "unit": "%", "condition": "3세 미만 기저귀 부위 금지", "note": "Annex V", "flag": "warn"},
        {"inci": "BUTYLPARABEN", "cas": "94-26-8", "max_conc": 0.14, "unit": "%", "condition": "3세 미만 기저귀 부위 금지", "note": "Annex V", "flag": "warn"},
        {"inci": "BENZYL ALCOHOL", "cas": "100-51-6", "max_conc": 1.0, "unit": "%", "condition": "알레르겐 표시 의무", "note": "Annex III + V", "flag": "warn"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": 0.5, "unit": "%", "condition": "3세 미만 사용금지 표시", "note": "Annex III", "flag": "warn"},
        {"inci": "GLYCOLIC ACID", "cas": "79-14-1", "max_conc": 10.0, "unit": "% (pH≥3.5)", "condition": "10% 초과 시 전문가용", "note": "AHA 가이던스", "flag": "warn"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": 2.0, "unit": "% (face)", "condition": "body 0.5%", "note": "SCCS 2020", "flag": "warn"},
        {"inci": "ARBUTIN", "cas": "497-76-7", "max_conc": None, "unit": "", "condition": "SCCS 안전성 평가 진행중 — 주의", "note": "SCCS 검토중", "flag": "warn"},
        {"inci": "KOJIC ACID", "cas": "501-30-4", "max_conc": 1.0, "unit": "%", "condition": "EU 금지 논의중 (SCCS)", "note": "SCCS 의견", "flag": "warn"},
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CERAMIDE AP", "cas": "41248-27-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "HYALURONIC ACID", "cas": "9004-61-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TOCOPHERYL ACETATE", "cas": "58-95-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TETRASODIUM EDTA", "cas": "64-02-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "정제도 기준 충족 필요 (MOSH/MOAH)", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ASCORBYL GLUCOSIDE", "cas": "129499-78-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERYL STEARATE", "cas": "11099-07-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ADENOSINE", "cas": "58-61-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "RESVERATROL", "cas": "501-36-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CITRIC ACID", "cas": "77-92-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TROMETHAMINE", "cas": "77-86-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYSORBATE 20", "cas": "9005-64-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYSORBATE 60", "cas": "9005-67-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYSORBATE 80", "cas": "9005-65-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYGLYCERYL-3 DISTEARATE", "cas": "9009-32-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYGLYCERYL-2 STEARATE", "cas": "9009-32-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CAMELLIA JAPONICA SEED OIL", "cas": "223748-13-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "OLEA EUROPAEA (OLIVE) FRUIT OIL", "cas": "8001-25-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "PERSEA GRATISSIMA (AVOCADO) OIL", "cas": "8024-32-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "MACADAMIA TERNIFOLIA SEED OIL", "cas": "129811-19-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYISOBUTENE", "cas": "9003-27-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SORBITAN ISOSTEARATE", "cas": "54392-26-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TRIETHOXYCAPRYLYLSILANE", "cas": "2943-75-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POTASSIUM CETYL PHOSPHATE", "cas": "17026-85-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "VEGETABLE OIL", "cas": "68956-68-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "HYDROGENATED VEGETABLE OIL", "cas": "68334-28-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "C9-12 ALKANE", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "C13-16 ISOALKANE", "cas": "68551-20-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ACRYLATES/C10-30 ALKYL ACRYLATE CROSSPOLYMER", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERYL STEARATE CITRATE", "cas": "39175-72-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SODIUM POLYACRYLOYLDIMETHYL TAURATE", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYACRYLATE-13", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
    ],
    "labeling": [
        "INCI명 전성분 표시 의무 (내용량 내림차순)",
        "향 알레르겐 26종: leave-on 0.001%, rinse-off 0.01% 초과 시 개별 표시",
        "PAO(개봉 후 사용기간) 또는 유통기한 표시",
        "EU 내 책임자(Responsible Person) 이름·주소 표시",
        "나노물질 성분명 뒤 [nano] 표시 의무",
        "CPNP 사전 신고 의무",
        "2025년 Annex I 개정: 안전성 보고서(CPSR) 요건 강화",
    ]
},
"KR": {
    "name": "🇰🇷 한국", "regulation": "화장품법 + 식약처 고시",
    "source": "https://www.mfds.go.kr/brd/m_211/list.do",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "사용금지 원료"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "사용금지"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "사용금지"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "사용금지"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "사용금지"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "사용금지"},
        {"inci": "HEXACHLOROPHENE", "cas": "70-30-4", "note": "사용금지"},
        {"inci": "BITHIONOL", "cas": "97-18-7", "note": "사용금지"},
        {"inci": "CHLOROFORM", "cas": "67-66-3", "note": "사용금지"},
    ],
    "restricted": [
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용 — 미백 기능성 2~5% 고시 원료", "note": "기능성화장품", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": 2.0, "unit": "%", "condition": "미백 기능성 고시 원료 — 2% 한도", "note": "기능성화장품 고시", "flag": "warn"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": 2.0, "unit": "% (face)", "condition": "기능성화장품 심사 필요", "note": "미백 기능성", "flag": "warn"},
        {"inci": "ARBUTIN", "cas": "497-76-7", "max_conc": 2.0, "unit": "%", "condition": "미백 기능성 — 심사 필요", "note": "기능성화장품", "flag": "warn"},
        {"inci": "ASCORBYL GLUCOSIDE", "cas": "129499-78-1", "max_conc": 2.0, "unit": "%", "condition": "미백 기능성 원료", "note": "기능성화장품", "flag": "warn"},
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 기능성 원료", "note": "기능성화장품", "flag": "ok"},
        {"inci": "TITANIUM DIOXIDE", "cas": "13463-67-7", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 기능성 원료", "note": "기능성화장품", "flag": "ok"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "주름개선 기능성 고시 원료 (2500IU/g)", "note": "기능성화장품", "flag": "warn"},
        {"inci": "ADENOSINE", "cas": "58-61-7", "max_conc": 0.04, "unit": "%", "condition": "주름개선 기능성 고시 원료", "note": "기능성화장품", "flag": "warn"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "보존제 한도 1%", "note": "사용 한도 원료", "flag": "ok"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "보존제 한도", "note": "사용 한도 원료", "flag": "warn"},
        {"inci": "PROPYLPARABEN", "cas": "94-13-3", "max_conc": 0.14, "unit": "%", "condition": "보존제 한도", "note": "사용 한도 원료", "flag": "warn"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": 0.5, "unit": "% (두발제 3%)", "condition": "보존제 한도", "note": "사용 한도 원료", "flag": "warn"},
        {"inci": "GLYCOLIC ACID", "cas": "79-14-1", "max_conc": 10.0, "unit": "%", "condition": "AHA류 고시 기준", "note": "사용 한도", "flag": "warn"},
        {"inci": "KOJIC ACID", "cas": "501-30-4", "max_conc": 2.0, "unit": "%", "condition": "미백 기능성 원료", "note": "기능성화장품", "flag": "warn"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CERAMIDE AP", "cas": "41248-27-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TOCOPHERYL ACETATE", "cas": "58-95-7", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TROMETHAMINE", "cas": "77-86-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CITRIC ACID", "cas": "77-92-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYGLYCERYL-3 DISTEARATE", "cas": "9009-32-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYGLYCERYL-2 STEARATE", "cas": "9009-32-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYSORBATE 20", "cas": "9005-64-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용 — 향 알레르겐 표시 권고", "note": "허용 원료", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용 — 향 알레르겐 표시 권고", "note": "허용 원료", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "CAMELLIA JAPONICA SEED OIL", "cas": "223748-13-8", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "OLEA EUROPAEA (OLIVE) FRUIT OIL", "cas": "8001-25-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "PERSEA GRATISSIMA (AVOCADO) OIL", "cas": "8024-32-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "MACADAMIA TERNIFOLIA SEED OIL", "cas": "129811-19-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "VEGETABLE OIL", "cas": "68956-68-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "HYDROGENATED VEGETABLE OIL", "cas": "68334-28-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERYL STEARATE", "cas": "11099-07-3", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "GLYCERYL STEARATE CITRATE", "cas": "39175-72-9", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POTASSIUM CETYL PHOSPHATE", "cas": "17026-85-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "TRIETHOXYCAPRYLYLSILANE", "cas": "2943-75-1", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SORBITAN ISOSTEARATE", "cas": "54392-26-6", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYISOBUTENE", "cas": "9003-27-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYACRYLATE-13", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "SODIUM POLYACRYLOYLDIMETHYL TAURATE", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "ACRYLATES/C10-30 ALKYL ACRYLATE CROSSPOLYMER", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "C9-12 ALKANE", "cas": "", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "C13-16 ISOALKANE", "cas": "68551-20-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
        {"inci": "POLYISOBUTENE", "cas": "9003-27-4", "max_conc": None, "condition": "허용", "note": "허용 원료", "flag": "ok"},
    ],
    "labeling": [
        "INCI명 또는 한글 성분명 전성분 표시 의무 (화장품법 제10조)",
        "제품명, 내용량, 제조사/수입사명, 사용기한 표시",
        "기능성화장품: '기능성화장품' 문구 + 심사번호 필수",
        "알레르기 유발 향료 25종 표시 (식약처 고시 2020~)",
        "사용상 주의사항 표시 필수",
        "영유아·어린이용 별도 표시기준 적용",
    ]
},
"US": {
    "name": "🇺🇸 미국", "regulation": "FDA 21 CFR + MoCRA 2022",
    "source": "https://www.fda.gov/cosmetics/cosmetics-laws-regulations/prohibited-restricted-ingredients-cosmetics",
    "prohibited": [
        {"inci": "BITHIONOL", "cas": "97-18-7", "note": "21 CFR 700.11"},
        {"inci": "CHLOROFORM", "cas": "67-66-3", "note": "21 CFR 700.18"},
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "21 CFR 700.13"},
        {"inci": "METHYLENE CHLORIDE", "cas": "75-09-2", "note": "21 CFR 700.19"},
        {"inci": "VINYL CHLORIDE", "cas": "75-01-4", "note": "21 CFR 700.14"},
        {"inci": "HEXACHLOROPHENE", "cas": "70-30-4", "note": "21 CFR 250.250"},
    ],
    "restricted": [
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 목적 시 OTC Drug 허가 필요", "note": "OTC Monograph", "flag": "warn"},
        {"inci": "TITANIUM DIOXIDE", "cas": "13463-67-7", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 목적 시 OTC Drug", "note": "OTC Monograph", "flag": "warn"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": None, "condition": "미백 클레임 시 Drug 분류 가능 주의", "note": "Drug claim 주의", "flag": "warn"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "허용 — Drug claim 주의", "note": "Drug claim 주의", "flag": "warn"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": None, "condition": "허용 — 미백 클레임 시 Drug 가능", "note": "Drug claim 주의", "flag": "warn"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": None, "condition": "두발제 OTC Drug 해당 가능", "note": "Drug claim 주의", "flag": "warn"},
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용 (알레르겐 표시의무 없음)", "note": "허용", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "KOJIC ACID", "cas": "501-30-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLYCERYL STEARATE", "cas": "11099-07-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TROMETHAMINE", "cas": "77-86-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
    ],
    "labeling": [
        "영어 전성분 표시 의무 — 내용량 내림차순 (21 CFR 701.3)",
        "내용량, 제조사/유통사 이름·주소 표시",
        "MoCRA 2022: 중대 부작용(SAE) FDA 보고 의무",
        "MoCRA 2022: 시설 등록 및 제품 목록 제출 의무",
        "Drug claim 사용 시 OTC Drug 별도 허가 필요",
        "향 알레르겐 표시 의무 없음 (EU와 차이)",
    ]
},
"CN": {
    "name": "🇨🇳 중국", "regulation": "NMPA 화장품감독관리조례 (2021)",
    "source": "https://www.nmpa.gov.cn",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "금지 원료"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "금지 (미백제 허가 필요)"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "금지 원료"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "금지"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "금지"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "금지 (염모제 예외)"},
    ],
    "restricted": [
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용 — 미백 특수화장품 신청 필요", "note": "특수화장품", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": 3.0, "unit": "%", "condition": "미백 특수화장품 NMPA 허가 필요", "note": "특수화장품", "flag": "warn"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": 2.0, "unit": "%", "condition": "미백 특수화장품 허가", "note": "특수화장품", "flag": "warn"},
        {"inci": "ARBUTIN", "cas": "497-76-7", "max_conc": 7.0, "unit": "%", "condition": "미백 특수화장품", "note": "특수화장품", "flag": "warn"},
        {"inci": "KOJIC ACID", "cas": "501-30-4", "max_conc": None, "condition": "미백 특수화장품 허가 필요", "note": "특수화장품", "flag": "warn"},
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 특수화장품", "note": "특수화장품", "flag": "ok"},
        {"inci": "TITANIUM DIOXIDE", "cas": "13463-67-7", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 특수화장품", "note": "특수화장품", "flag": "ok"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "항노화 표방 주의", "note": "주의", "flag": "warn"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "보존제 한도", "note": "허용", "flag": "ok"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "보존제 한도", "note": "허용", "flag": "warn"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용 (백색광물유 기준)", "note": "허용", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": 0.5, "unit": "%", "condition": "보존제 한도", "note": "허용", "flag": "warn"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
    ],
    "labeling": [
        "중국어(간체) 전성분 표시 의무 — INCI명 병기 가능",
        "NMPA 허가번호 또는 비특수화장품 등록번호 표시",
        "수입화장품: 중국 내 책임회사(代理商) 정보 표시",
        "특수화장품 (미백·UV차단·염모 등): 사전 허가 의무",
        "일반화장품: CSAR 시스템 사전 등록 의무",
        "2023년~: 원료 안전 정보 파일 제출 의무",
    ]
},
"JP": {
    "name": "🇯🇵 일본", "regulation": "약기법 + 화장품기준",
    "source": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/keshouhin/",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "화장품기준 별표1"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "별표1 (의약외품 제외)"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "화장품기준 별표1"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "별표1"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "화장품기준 제한"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "별표1 (일부 예외)"},
    ],
    "restricted": [
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용 — 의약외품 미백 원료로 별도 사용", "note": "허용", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": None, "condition": "의약외품 성분 — 화장품 미백 표방 시 의약외품 신청 필요 주의", "note": "의약외품 주의", "flag": "warn"},
        {"inci": "ARBUTIN", "cas": "497-76-7", "max_conc": 7.0, "unit": "%", "condition": "의약외품 미백 성분", "note": "의약외품", "flag": "warn"},
        {"inci": "KOJIC ACID", "cas": "501-30-4", "max_conc": 1.0, "unit": "%", "condition": "의약외품 미백 — 별도 허가", "note": "의약외품", "flag": "warn"},
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "자외선차단 의약외품", "note": "의약외품", "flag": "ok"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "의약외품 기준 — 화장품 표방 주의", "note": "의약외품 주의", "flag": "warn"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "보존제 한도 1%", "note": "별표3", "flag": "ok"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "보존제 한도", "note": "별표3", "flag": "warn"},
        {"inci": "PROPYLPARABEN", "cas": "94-13-3", "max_conc": 0.14, "unit": "%", "condition": "보존제 한도", "note": "별표3", "flag": "warn"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": 0.5, "unit": "%", "condition": "보존제 한도", "note": "별표3", "flag": "warn"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TROMETHAMINE", "cas": "77-86-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
    ],
    "labeling": [
        "전성분 표시 의무 (후생노동성 화장품 전성분 표시 기준)",
        "제조판매업자 또는 수입판매업자 표시",
        "사용기한 또는 제조번호 표시",
        "의약외품: 후생노동성 사전 허가 필요",
        "일본어 표기 원칙",
    ]
},
"ASEAN": {
    "name": "🌏 ASEAN", "regulation": "ASEAN Cosmetic Directive (ACD)",
    "source": "https://asean.org/asean-cosmetic-directive/",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "Annex II"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "Annex II"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "Annex II"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "Annex II"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "일부 국가 제한"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "Annex II"},
    ],
    "restricted": [
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "허용", "note": "Annex VI", "flag": "ok"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "Annex V 한도", "note": "허용", "flag": "ok"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "Annex V 한도", "note": "허용", "flag": "warn"},
        {"inci": "PROPYLPARABEN", "cas": "94-13-3", "max_conc": 0.14, "unit": "%", "condition": "Annex V 한도", "note": "허용", "flag": "warn"},
        {"inci": "SALICYLIC ACID", "cas": "69-72-7", "max_conc": 0.5, "unit": "%", "condition": "Annex V 한도", "note": "허용", "flag": "warn"},
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "HYDROXYACETOPHENONE", "cas": "99-93-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
    ],
    "labeling": [
        "INCI명 또는 현지어 성분명 전성분 표시",
        "제조국 표시 의무",
        "유통기한 또는 제조일자 표시",
        "현지 수입업자/유통업자 정보 표시",
        "인도네시아(BPOM): 수입 전 등록 의무",
        "베트남: 베트남어 라벨 부착 의무",
        "태국: Thai FDA 등록 의무 (일부)",
        "필리핀: FDA Philippines 등록 의무",
    ]
},
"GCC": {
    "name": "🕌 중동 GCC", "regulation": "GSO 1943",
    "source": "https://www.gso.org.sa/",
    "prohibited": [
        {"inci": "MERCURY", "cas": "7439-97-6", "note": "GSO Annex II"},
        {"inci": "HYDROQUINONE", "cas": "123-31-9", "note": "GSO Annex II"},
        {"inci": "LEAD", "cas": "7439-92-1", "note": "GSO Annex II"},
        {"inci": "FORMALDEHYDE", "cas": "50-00-0", "note": "GSO Annex II"},
        {"inci": "TRICLOSAN", "cas": "3380-34-5", "note": "GSO 제한"},
        {"inci": "RESORCINOL", "cas": "108-46-3", "note": "GSO Annex II"},
    ],
    "restricted": [
        {"inci": "GLYCERIN", "cas": "56-81-5", "max_conc": None, "condition": "돼지 유래 여부 확인 필요 (Halal) 주의", "note": "Halal 주의", "flag": "warn"},
        {"inci": "CERAMIDE NP", "cas": "100403-19-8", "max_conc": None, "condition": "동물 유래 확인 필요 (Halal) 주의", "note": "Halal 주의", "flag": "warn"},
        {"inci": "SQUALANE", "cas": "111-01-3", "max_conc": None, "condition": "상어 유래 주의 — 식물성 권장 주의", "note": "Halal 주의", "flag": "warn"},
        {"inci": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "cas": "65381-09-1", "max_conc": None, "condition": "야자 유래 시 Halal 가능, 돼지 유래 주의", "note": "Halal 주의", "flag": "warn"},
        {"inci": "NIACINAMIDE", "cas": "98-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ZINC OXIDE", "cas": "1314-13-2", "max_conc": 25.0, "unit": "%", "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "LINALOOL", "cas": "78-70-6", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "COUMARIN", "cas": "91-64-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TRANEXAMIC ACID", "cas": "701-54-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "MINERAL OIL", "cas": "8012-95-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GLUTATHIONE", "cas": "70-18-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PANTHENOL", "cas": "16485-10-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SODIUM HYALURONATE", "cas": "9067-32-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "PHENOXYETHANOL", "cas": "122-99-6", "max_conc": 1.0, "unit": "%", "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "RETINOL", "cas": "68-26-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ARBUTIN", "cas": "84380-01-8", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CETYL ALCOHOL", "cas": "36653-82-4", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "STEARYL ALCOHOL", "cas": "112-92-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "TOCOPHEROL", "cas": "10191-41-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ASCORBIC ACID", "cas": "50-81-7", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "GERANIOL", "cas": "106-24-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "CITRONELLOL", "cas": "106-22-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BENZYL SALICYLATE", "cas": "118-58-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ALPHA-ISOMETHYL IONONE", "cas": "127-51-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "METHYLPARABEN", "cas": "99-76-3", "max_conc": 0.4, "unit": "%", "condition": "허용", "note": "허용", "flag": "warn"},
        {"inci": "1,2-HEXANEDIOL", "cas": "6920-22-5", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "ETHYLHEXYLGLYCERIN", "cas": "70445-33-9", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL", "cas": "61789-91-1", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "BUTYROSPERMUM PARKII (SHEA) BUTTER", "cas": "194043-92-0", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "DISODIUM EDTA", "cas": "139-33-3", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
        {"inci": "XANTHAN GUM", "cas": "11138-66-2", "max_conc": None, "condition": "허용", "note": "허용", "flag": "ok"},
    ],
    "labeling": [
        "아랍어 라벨 표시 의무 (사우디, UAE, 쿠웨이트 등)",
        "Halal: 돼지 및 금지 동물 유래 원료 사용 불가",
        "제조국 표시 의무",
        "유통기한 표시 의무",
        "GCC 현지 수입업자 정보 표시",
        "이스라엘산 제품·원료 사용 불가 (일부 국가)",
        "사우디: SFDA 등록 의무",
        "UAE: ESMA 인증/등록 의무",
    ]
},
    }

# ─────────────────────────────────────────────
# MATCHING ENGINE
# ─────────────────────────────────────────────
def normalize(s):
    if not s:
        return ""
    s = str(s).upper().strip()
    s = re.sub(r'\s+', ' ', s)
    # 괄호 안 내용 정규화
    s = re.sub(r'\s*\(\s*', ' (', s)
    s = re.sub(r'\s*\)\s*', ') ', s)
    return s.strip()

def clean_cas(s):
    if not s:
        return ""
    return str(s).strip().replace(" ", "")

def match_entry(ing_inci, ing_cas, entry_inci, entry_cas):
    ni = normalize(ing_inci)
    ei = normalize(entry_inci)
    nc = clean_cas(ing_cas)
    ec = clean_cas(entry_cas)

    # 1) 정확히 일치
    if ni == ei:
        return True
    # 2) CAS 번호 일치 (둘 다 있을 때)
    if nc and ec and nc == ec and len(nc) > 3:
        return True
    # 3) 괄호 제거 후 비교
    ni_plain = re.sub(r'\([^)]+\)', '', ni).strip()
    ei_plain = re.sub(r'\([^)]+\)', '', ei).strip()
    if ni_plain and ei_plain and ni_plain == ei_plain:
        return True
    # 4) 긴 이름 포함 관계 (8자 이상일 때만)
    if len(ni) >= 8 and len(ei) >= 8:
        if ni in ei or ei in ni:
            return True
    # 5) 핵심 단어 매칭 (슬래시 포함 원료 등)
    ni_words = set(re.split(r'[\s\(\)/\-]+', ni)) - {'', 'AND', 'OR', 'OF', 'THE'}
    ei_words = set(re.split(r'[\s\(\)/\-]+', ei)) - {'', 'AND', 'OR', 'OF', 'THE'}
    if len(ni_words) >= 2 and len(ei_words) >= 2:
        overlap = ni_words & ei_words
        ratio = len(overlap) / max(len(ni_words), len(ei_words))
        if ratio >= 0.75:
            return True
    return False

def check_ingredient(inci, cas, conc, db):
    # 금지 체크
    for p in db.get("prohibited", []):
        if match_entry(inci, cas, p["inci"], p.get("cas", "")):
            return {"status": "danger", "label": "🚫 금지", "condition": p.get("note", ""), "note": p.get("note", "")}
    # 제한 체크
    for r in db.get("restricted", []):
        if match_entry(inci, cas, r["inci"], r.get("cas", "")):
            max_c = r.get("max_conc")
            flag = r.get("flag", "ok")
            # 한도 초과
            if max_c is not None and conc is not None:
                try:
                    if float(conc) > float(max_c):
                        return {
                            "status": "danger",
                            "label": f"🚫 한도초과",
                            "condition": f"한도 {max_c}{r.get('unit','%')} / 실제 {conc}%",
                            "note": r.get("note", "")
                        }
                except:
                    pass
            # flag 기반
            if flag == "danger":
                return {"status": "danger", "label": "🚫 금지·위험", "condition": r.get("condition", ""), "note": r.get("note", "")}
            if flag == "warn":
                return {"status": "warn", "label": "⚠️ 주의", "condition": r.get("condition", ""), "note": r.get("note", "")}
            return {"status": "ok", "label": "✓ 적합", "condition": r.get("condition", "허용 원료"), "note": r.get("note", "")}
    return {"status": "nodata", "label": "— DB 미등록", "condition": "규제 DB에 없음. 직접 확인 필요", "note": ""}

# ─────────────────────────────────────────────
# FILE PARSERS
# ─────────────────────────────────────────────
def parse_pdf(file_bytes):
    rows = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # 테이블 추출 시도
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    cells = [str(c).strip() if c else "" for c in row]
                    # 헤더 스킵
                    if any(kw in " ".join(cells).upper() for kw in ["INGREDIENT", "INCI", "성분명", "MATERIAL"]):
                        continue
                    if cells[0] and len(cells[0]) > 2:
                        rows.append(cells)

            # 텍스트 기반 추출 (테이블 없는 경우)
            if not rows:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    line = line.strip()
                    if not line or len(line) < 3:
                        continue
                    # CAS 패턴으로 줄 분리
                    cas_match = re.search(r'\d{1,7}-\d{2}-\d', line)
                    # 농도 패턴
                    conc_match = re.search(r'(\d+\.?\d+)\s*%?', line)
                    # INCI명 (영문 대문자 포함)
                    inci_part = line
                    if cas_match:
                        inci_part = line[:cas_match.start()].strip()
                    if inci_part and re.search(r'[A-Z]{2,}', inci_part):
                        row = [inci_part,
                               cas_match.group(0) if cas_match else "",
                               conc_match.group(1) if conc_match else ""]
                        rows.append(row)
    return rows

def parse_excel(file_bytes):
    rows = []
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        for sheet in xl.sheet_names:
            df = xl.parse(sheet, header=None)
            df = df.fillna("")
            # 헤더 행 찾기
            header_row = 0
            for i, row in df.iterrows():
                row_str = " ".join(str(v).upper() for v in row)
                if any(kw in row_str for kw in ["INGREDIENT", "INCI", "성분", "MATERIAL", "WATER"]):
                    header_row = i
                    break
            for i, row in df.iterrows():
                if i <= header_row:
                    continue
                cells = [str(v).strip() for v in row]
                cells = [c for c in cells if c and c != "nan"]
                if not cells:
                    continue
                # 헤더 스킵
                if any(kw in " ".join(cells).upper() for kw in ["INGREDIENT", "INCI", "성분명"]):
                    continue
                if cells[0] and len(cells[0]) > 1 and re.search(r'[A-Za-z]', cells[0]):
                    rows.append(cells)
    except Exception as e:
        st.warning(f"Excel 파싱 오류: {e}")
    return rows

def parse_csv_file(file_bytes):
    rows = []
    try:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        df = pd.read_csv(io.StringIO(text), header=None, on_bad_lines='skip')
        df = df.fillna("")
        for i, row in df.iterrows():
            cells = [str(v).strip() for v in row]
            cells = [c for c in cells if c and c != "nan"]
            if not cells:
                continue
            if any(kw in " ".join(cells).upper() for kw in ["INGREDIENT", "INCI", "성분명", "MATERIAL"]):
                continue
            if cells[0] and len(cells[0]) > 1:
                rows.append(cells)
    except Exception as e:
        st.warning(f"CSV 파싱 오류: {e}")
    return rows

def parse_txt_file(file_bytes):
    rows = []
    text = file_bytes.decode("utf-8-sig", errors="replace")
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 2:
            continue
        if any(kw in line.upper() for kw in ["INGREDIENT", "INCI", "성분명"]):
            continue
        parts = re.split(r'[\t,;]+', line)
        parts = [p.strip() for p in parts if p.strip()]
        if parts and re.search(r'[A-Za-z]', parts[0]):
            rows.append(parts)
    return rows

def rows_to_formula(rows):
    """파싱된 rows → DataFrame"""
    result = []
    for row in rows:
        inci = ""
        cas = ""
        conc = None

        for cell in row:
            cell = cell.strip()
            if not cell:
                continue
            # CAS 번호
            if re.match(r'^\d{1,7}-\d{2}-\d$', cell):
                cas = cell
                continue
            # 농도 (숫자)
            conc_match = re.match(r'^(\d+\.?\d*)$', cell)
            if conc_match:
                val = float(conc_match.group(1))
                if val <= 100:
                    conc = val
                    continue
            # INCI명 (영문 포함, 2자 이상)
            if not inci and len(cell) > 1 and re.search(r'[A-Za-z]', cell):
                # 정제: 숫자만 있는 부분 제거
                clean = re.sub(r'^\d+\s*', '', cell).strip()
                if clean and re.search(r'[A-Za-z]', clean):
                    inci = clean.upper()

        if inci and len(inci) > 1:
            result.append({"INCI명": inci, "CAS No.": cas, "농도(%)": conc})

    return pd.DataFrame(result) if result else pd.DataFrame(columns=["INCI명", "CAS No.", "농도(%)"])

# ─────────────────────────────────────────────
# STATUS BADGE HTML
# ─────────────────────────────────────────────
def status_badge(status, label):
    cls_map = {"danger": "badge-danger", "warn": "badge-warn", "ok": "badge-ok", "nodata": "badge-nodata"}
    cls = cls_map.get(status, "badge-nodata")
    return f'<span class="{cls}">{label}</span>'

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">🧴 CosRA Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Global Cosmetic Regulatory Checker</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="section-header">분석 대상 국가 선택</div>', unsafe_allow_html=True)
    db_all = get_regulation_db()
    selected_regions = []
    cols = st.columns(2)
    for i, (rid, rdata) in enumerate(db_all.items()):
        with cols[i % 2]:
            if st.checkbox(rdata["name"], value=True, key=f"chk_{rid}"):
                selected_regions.append(rid)

    st.divider()
    st.markdown('<div class="section-header">공식 규제 출처 링크</div>', unsafe_allow_html=True)
    for rid in ["EU", "KR", "US", "CN", "JP", "ASEAN", "GCC"]:
        rdata = db_all[rid]
        st.markdown(
            f'<div class="link-box"><a href="{rdata["source"]}" target="_blank">{rdata["name"]} — 공식 DB ↗</a></div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown('<div class="section-header">추가 공식 링크</div>', unsafe_allow_html=True)
    links = [
        ("🇪🇺 EU CosIng", "https://ec.europa.eu/growth/tools-databases/cosing/"),
        ("🇪🇺 ECHA SVHC", "https://echa.europa.eu/candidate-list-table"),
        ("🇺🇸 MoCRA 2022", "https://www.fda.gov/cosmetics/cosmetics-laws-regulations/modernization-cosmetics-regulation-act-2022-mocra"),
        ("🇨🇦 Health Canada Hot List", "https://www.canada.ca/en/health-canada/services/consumer-product-safety/cosmetics/cosmetic-ingredient-hotlist-prohibited-restricted-ingredients.html"),
        ("🇦🇺 AICIS", "https://www.aicis.gov.au/"),
        ("🇧🇷 ANVISA", "https://www.gov.br/anvisa/pt-br/setorregulado/regularizacao/cosmeticos"),
    ]
    for name, url in links:
        st.markdown(f'<div class="link-box"><a href="{url}" target="_blank">{name} ↗</a></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">🌐 글로벌 화장품 규제 분석</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">PDF · Excel · CSV · TXT 업로드 또는 직접 입력 → INCI명·CAS번호 자동 인식 → 7개국 규제 즉시 대조</div>',
    unsafe_allow_html=True
)

# ── 파일 업로드 ──
st.markdown('<div class="section-header">처방 파일 업로드</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "드래그 앤 드롭 또는 클릭하여 업로드",
    type=["pdf", "xlsx", "xls", "csv", "txt"],
    help="PDF, Excel, CSV, TXT 모두 지원. INCI명·CAS번호·농도(%) 자동 파싱"
)

formula_df = pd.DataFrame(columns=["INCI명", "CAS No.", "농도(%)"])

if uploaded:
    ext = uploaded.name.split(".")[-1].lower()
    file_bytes = uploaded.read()
    with st.spinner(f"📄 {uploaded.name} 파싱 중..."):
        if ext == "pdf":
            rows = parse_pdf(file_bytes)
        elif ext in ["xlsx", "xls"]:
            rows = parse_excel(file_bytes)
        elif ext == "csv":
            rows = parse_csv_file(file_bytes)
        else:
            rows = parse_txt_file(file_bytes)
        formula_df = rows_to_formula(rows)

    if not formula_df.empty:
        st.success(f"✅ {uploaded.name} — **{len(formula_df)}개 원료** 파싱 완료")
    else:
        st.warning("⚠️ 자동 파싱 결과가 없습니다. 아래에서 직접 입력해주세요.")

# ── 직접 입력 ──
st.markdown('<div class="section-header" style="margin-top:16px;">직접 입력 (INCI명, CAS번호, 농도% 순서 — 탭/콤마 구분)</div>', unsafe_allow_html=True)

sample_text = """WATER, 7732-18-5, 60.289612
MINERAL OIL, 8012-95-1, 15.000000
GLYCERIN, 56-81-5, 5.000000
NIACINAMIDE, 98-92-0, 2.000000
CETYL ALCOHOL, 36653-82-4, 2.000000
STEARYL ALCOHOL, 112-92-5, 0.375000
1,2-HEXANEDIOL, 6920-22-5, 1.522000
LINALOOL, 78-70-6, 0.145146
CERAMIDE NP, 100403-19-8, 0.001000
TRANEXAMIC ACID, 701-54-2, 0.001000
GLUTATHIONE, 70-18-8, 0.000100
ZINC OXIDE, 1314-13-2, 0.148000
SODIUM HYALURONATE, 9067-32-7, 0.010000
SQUALANE, 111-01-3, 0.010000
PANTHENOL, 16485-10-2, 0.100000
COUMARIN, 91-64-5, 0.017320
GERANIOL, 106-24-1, 0.004606
CITRONELLOL, 106-22-9, 0.001605
ALPHA-ISOMETHYL IONONE, 127-51-5, 0.001129
BENZYL SALICYLATE, 118-58-1, 0.008000
PHENOXYETHANOL, 122-99-6, 0.800000
TOCOPHEROL, 10191-41-0, 0.000057
DISODIUM EDTA, 139-33-3, 0.030000
BUTYROSPERMUM PARKII (SHEA) BUTTER, 194043-92-0, 0.010000
CAMELLIA JAPONICA SEED OIL, 223748-13-8, 0.010000
OLEA EUROPAEA (OLIVE) FRUIT OIL, 8001-25-0, 0.010000
SIMMONDSIA CHINENSIS (JOJOBA) SEED OIL, 61789-91-1, 0.010000"""

text_input = st.text_area(
    "처방 직접 입력",
    value="" if not formula_df.empty else sample_text,
    height=200,
    placeholder="WATER, 7732-18-5, 60.29\nNIACINAMIDE, 98-92-0, 2.00\nLINALOOL, 78-70-6, 0.145\n...",
    label_visibility="collapsed"
)

# 텍스트 입력이 있으면 파싱
if text_input.strip() and formula_df.empty:
    rows = parse_txt_file(text_input.encode("utf-8"))
    formula_df = rows_to_formula(rows)

# ── 편집 가능 테이블 ──
if not formula_df.empty:
    st.markdown(f'<div class="section-header">파싱된 처방 — {len(formula_df)}개 원료 (수정 가능)</div>', unsafe_allow_html=True)
    formula_df = st.data_editor(
        formula_df,
        num_rows="dynamic",
        use_container_width=True,
        height=280,
        column_config={
            "INCI명": st.column_config.TextColumn("INCI명", width="large"),
            "CAS No.": st.column_config.TextColumn("CAS No.", width="medium"),
            "농도(%)": st.column_config.NumberColumn("농도(%)", format="%.6f", width="small"),
        }
    )

# ── 분석 버튼 ──
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
with col_btn1:
    run_btn = st.button("🔍 규제 분석 실행", type="primary", use_container_width=True, disabled=formula_df.empty)
with col_btn2:
    if st.button("📋 샘플 처방 로드", use_container_width=True):
        st.session_state["load_sample"] = True
        st.rerun()
with col_btn3:
    clear_btn = st.button("🗑️ 초기화", use_container_width=True)

if st.session_state.get("load_sample"):
    rows = parse_txt_file(sample_text.encode("utf-8"))
    formula_df = rows_to_formula(rows)
    st.session_state["load_sample"] = False

# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────
if run_btn and not formula_df.empty and selected_regions:
    st.markdown("---")
    st.markdown('<div class="main-title" style="font-size:1.4rem;">📊 분석 결과</div>', unsafe_allow_html=True)

    # 전체 summary (worst across regions)
    summary_rows = []
    for _, row in formula_df.iterrows():
        inci = str(row.get("INCI명", "")).strip()
        cas = str(row.get("CAS No.", "")).strip()
        conc = row.get("농도(%)")
        try:
            conc = float(conc) if conc not in [None, "", "None", "nan"] else None
        except:
            conc = None

        worst = "ok"
        for rid in selected_regions:
            db = db_all[rid]
            res = check_ingredient(inci, cas, conc, db)
            if res["status"] == "danger":
                worst = "danger"
                break
            elif res["status"] == "warn":
                worst = "warn"
            elif res["status"] == "nodata" and worst == "ok":
                worst = "nodata"
        summary_rows.append(worst)

    n_total = len(summary_rows)
    n_danger = summary_rows.count("danger")
    n_warn = summary_rows.count("warn")
    n_ok = summary_rows.count("ok")
    n_nodata = summary_rows.count("nodata")

    # Summary metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 전체 원료", n_total)
    c2.metric("🚫 금지·위험", n_danger, delta=None)
    c3.metric("⚠️ 주의·한도", n_warn)
    c4.metric("✓ 적합", n_ok)
    c5.metric("— DB 미등록", n_nodata)

    if n_danger > 0:
        st.error(f"🚨 금지 또는 한도 초과 원료 {n_danger}건이 발견되었습니다!")
    if n_warn > 0:
        st.warning(f"⚠️ 주의가 필요한 원료 {n_warn}건이 있습니다.")

    st.markdown("---")

    # ── 탭별 국가 결과 ──
    tabs = st.tabs([db_all[r]["name"] for r in selected_regions])

    all_export_data = {}

    for tab, rid in zip(tabs, selected_regions):
        with tab:
            db = db_all[rid]
            st.markdown(
                f"**{db['regulation']}** | 업데이트: {date.today().strftime('%Y-%m')} | "
                f"[출처 ↗]({db['source']})",
                unsafe_allow_html=False
            )

            result_rows = []
            for _, row in formula_df.iterrows():
                inci = str(row.get("INCI명", "")).strip()
                cas = str(row.get("CAS No.", "")).strip()
                conc = row.get("농도(%)")
                try:
                    conc_f = float(conc) if conc not in [None, "", "None", "nan"] else None
                except:
                    conc_f = None

                res = check_ingredient(inci, cas, conc_f, db)
                result_rows.append({
                    "INCI명": inci,
                    "CAS No.": cas,
                    "농도(%)": f"{conc_f:.6f}" if conc_f is not None else "-",
                    "규제 상태": res["label"],
                    "status": res["status"],
                    "조건 / 한도": res["condition"],
                    "근거": res["note"],
                })

            all_export_data[rid] = result_rows

            # 필터
            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                filter_status = st.selectbox(
                    "상태 필터",
                    ["전체", "🚫 금지·위험", "⚠️ 주의", "✓ 적합", "— DB 미등록"],
                    key=f"filter_{rid}"
                )
            with col_f2:
                search_q = st.text_input("INCI명 / CAS 검색", key=f"search_{rid}", placeholder="검색어 입력...")

            # 필터 적용
            display_rows = result_rows.copy()
            status_map = {
                "🚫 금지·위험": "danger",
                "⚠️ 주의": "warn",
                "✓ 적합": "ok",
                "— DB 미등록": "nodata"
            }
            if filter_status != "전체":
                target = status_map.get(filter_status, "")
                display_rows = [r for r in display_rows if r["status"] == target]
            if search_q.strip():
                sq = search_q.strip().upper()
                display_rows = [r for r in display_rows if sq in r["INCI명"].upper() or sq in r["CAS No."].upper()]

            # 컬러 매핑
            def row_color(status):
                return {"danger": "🔴", "warn": "🟡", "ok": "🟢", "nodata": "⚪"}.get(status, "⚪")

            # 테이블 출력
            if display_rows:
                display_df = pd.DataFrame([{
                    "": row_color(r["status"]),
                    "INCI명": r["INCI명"],
                    "CAS No.": r["CAS No."],
                    "농도(%)": r["농도(%)"],
                    "규제 상태": r["규제 상태"],
                    "조건 / 한도": r["조건 / 한도"],
                    "근거": r["근거"],
                } for r in display_rows])
                st.dataframe(display_df, use_container_width=True, height=420, hide_index=True)
                st.caption(f"표시: {len(display_rows)} / 전체: {len(result_rows)}건")
            else:
                st.info("해당 조건의 결과가 없습니다.")

            # 라벨링 요건
            with st.expander(f"📝 {db['name']} 라벨링 요건 보기"):
                for item in db.get("labeling", []):
                    st.markdown(f"→ {item}")

    # ── 내보내기 ──
    st.markdown("---")
    st.markdown('<div class="section-header">결과 내보내기</div>', unsafe_allow_html=True)
    ecol1, ecol2, ecol3 = st.columns(3)

    # 현재 선택 국가 Excel
    with ecol1:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 국가별 시트
            for rid in selected_regions:
                rows_data = all_export_data.get(rid, [])
                if rows_data:
                    df_exp = pd.DataFrame([{
                        "INCI명": r["INCI명"], "CAS No.": r["CAS No."],
                        "농도(%)": r["농도(%)"], "규제 상태": r["규제 상태"],
                        "조건/한도": r["조건 / 한도"], "근거": r["근거"]
                    } for r in rows_data])
                    df_exp.to_excel(writer, sheet_name=rid[:31], index=False)
            # 전국가 종합
            all_rows_combined = []
            for _, row in formula_df.iterrows():
                inci = str(row.get("INCI명", "")).strip()
                cas = str(row.get("CAS No.", "")).strip()
                conc = row.get("농도(%)")
                try:
                    conc_f = float(conc) if conc not in [None, "", "None", "nan"] else None
                except:
                    conc_f = None
                combined_row = {"INCI명": inci, "CAS No.": cas, "농도(%)": f"{conc_f:.6f}" if conc_f is not None else "-"}
                for rid in selected_regions:
                    res = check_ingredient(inci, cas, conc_f, db_all[rid])
                    combined_row[db_all[rid]["name"]] = res["label"]
                all_rows_combined.append(combined_row)
            pd.DataFrame(all_rows_combined).to_excel(writer, sheet_name="전국가종합", index=False)
            # 라벨링
            lbl_rows = []
            for rid in selected_regions:
                for item in db_all[rid].get("labeling", []):
                    lbl_rows.append({"국가": db_all[rid]["name"], "라벨링 요건": item})
            if lbl_rows:
                pd.DataFrame(lbl_rows).to_excel(writer, sheet_name="라벨링요건", index=False)

        st.download_button(
            "📊 Excel 다운로드",
            data=output.getvalue(),
            file_name=f"CosRA_Report_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 전국가 CSV
    with ecol2:
        all_rows_combined = []
        for _, row in formula_df.iterrows():
            inci = str(row.get("INCI명", "")).strip()
            cas = str(row.get("CAS No.", "")).strip()
            conc = row.get("농도(%)")
            try:
                conc_f = float(conc) if conc not in [None, "", "None", "nan"] else None
            except:
                conc_f = None
            combined_row = {"INCI명": inci, "CAS No.": cas, "농도(%)": f"{conc_f:.6f}" if conc_f is not None else "-"}
            for rid in selected_regions:
                res = check_ingredient(inci, cas, conc_f, db_all[rid])
                combined_row[db_all[rid]["name"]] = res["label"]
            all_rows_combined.append(combined_row)
        csv_data = pd.DataFrame(all_rows_combined).to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "📄 전국가 CSV",
            data=csv_data.encode("utf-8-sig"),
            file_name=f"CosRA_AllRegions_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 현재 탭 JSON
    with ecol3:
        json_data = json.dumps(all_export_data, ensure_ascii=False, indent=2)
        st.download_button(
            "📋 JSON 다운로드",
            data=json_data.encode("utf-8"),
            file_name=f"CosRA_Results_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True
        )

elif run_btn and not selected_regions:
    st.error("왼쪽 사이드바에서 분석할 국가를 최소 1개 이상 선택해주세요.")

# ── 푸터 ──
st.markdown("---")
st.markdown(
    """
    <div style="font-size:0.72rem; color:#8a8480; text-align:center; padding:12px;">
    ⚠️ <b>면책 조항</b>: 이 도구는 참고용입니다. 최종 규제 판단은 반드시 공식 문서 및 전문 RA 담당자를 통해 확인하세요.<br>
    CosRA Pro · 내장 DB: EU / 한국 / 미국 / 중국 / 일본 / ASEAN / 중동GCC
    </div>
    """,
    unsafe_allow_html=True
)
