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
# 1. JSON 파일을 읽어오는 함수 (기존 get_regulation_db 대체)
@st.cache_data
def load_db_from_json():
    try:
        with open('regulations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("폴더에 'regulations.json' 파일이 없습니다. 파일을 생성해 주세요.")
        return {}

# 2. 전역 변수로 DB 로드
db_all = load_db_from_json()

# 3. 성분 체크 함수 (기존 로직보다 더 정확하게 수정)
def check_ingredient(inci, cas, conc, region_data):
    # 입력값 표준화 (대문자, 공백제거)
    name = str(inci).upper().strip()
    cas_val = str(cas).strip() if cas else ""
    
    # 금지 성분 체크 (키워드 포함 여부 검색)
    for p in region_data.get("prohibited", []):
        if p.upper() in name:
            return {"label": "❌ 사용금지", "color": "red"}
            
    # 제한 성분 체크
    rest = region_data.get("restricted", {})
    for r_name, rule in rest.items():
        if r_name.upper() in name:
            limit = rule.get("max", 100)
            if conc and float(conc) > limit:
                return {"label": f"⚠️ 한도초과 ({limit}%)", "color": "orange"}
            return {"label": f"✅ 준수 ({limit}%)", "color": "green"}
            
    return {"label": "✅ 안전", "color": "blue"}
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
