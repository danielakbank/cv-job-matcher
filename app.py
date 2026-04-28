import streamlit as st
import logging
from utils.cv_parser import extract_cv_text
from utils.job_fetcher import (
    fetch_jobs,
    geocode_postcode,
    detect_location_from_ip,
    LocationFilter,
)
from utils.scorer import score_jobs
from utils.analyzer import analyse_match
from utils.job_suggester import suggest_job_roles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="CV Job Matcher",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",  # collapsed by default on mobile
)

# ─────────────────────────────────────────────
# CUSTOM CSS — mobile first
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Base ── */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #f0f4f3;
        color: #1a2e2a;
    }

    /* ── Constrain max width on desktop, full width on mobile ── */
    .block-container {
        max-width: 860px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }

    /* ── Header ── */
    .main-header {
        background: #1a3a34;
        padding: 1.8rem 1.2rem;
        border-radius: 14px;
        text-align: center;
        margin-bottom: 1.5rem;
        border: 1px solid #2d5a50;
    }
    .main-header h1 {
        color: #7dd3c0;
        font-size: clamp(1.6rem, 5vw, 2.4rem);
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    .main-header p {
        color: #a8c5be;
        font-size: clamp(0.82rem, 2.5vw, 0.95rem);
        margin-top: 0.5rem;
        margin-bottom: 0;
        line-height: 1.5;
    }

    /* ── Breadcrumb ── */
    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.6rem 1rem;
        background: #e4edeb;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        font-size: clamp(0.72rem, 2.5vw, 0.85rem);
        border: 1px solid #c8dbd7;
        flex-wrap: wrap;
    }
    .bc-step        { color: #7a9e97; font-weight: 500; white-space: nowrap; }
    .bc-step.active { color: #1a6b5a; font-weight: 700; }
    .bc-step.done   { color: #2d8c72; font-weight: 500; }
    .bc-arrow       { color: #b0ccc7; font-size: 0.7rem; }

    /* ── Location banners ── */
    .location-ok {
        background: #f0faf7;
        border: 1px solid #a8d5c8;
        border-left: 4px solid #2d8c72;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin: 0.75rem 0;
        font-size: 0.88rem;
        color: #1a3a34;
        line-height: 1.5;
    }
    .location-ok .loc-label {
        color: #1a6b5a;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: block;
        margin-bottom: 0.3rem;
    }
    .location-err {
        background: #fef3e2;
        border: 1px solid #f5c842;
        border-left: 4px solid #f5a623;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin: 0.75rem 0;
        font-size: 0.88rem;
        color: #6b4c00;
        line-height: 1.5;
    }

    /* ── Strengths banner ── */
    .strengths-banner {
        background: #f0faf7;
        border: 1px solid #a8d5c8;
        border-left: 4px solid #2d8c72;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
        color: #1a3a34;
        font-size: clamp(0.82rem, 2.5vw, 0.93rem);
        line-height: 1.7;
    }
    .strengths-banner strong {
        color: #1a6b5a;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    /* ── Role cards — full width on mobile ── */
    .role-card {
        background: #ffffff;
        border: 1.5px solid #c8dbd7;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-top: 0.3rem;
        margin-bottom: 0.7rem;
        transition: border-color 0.2s ease;
    }
    .role-card-selected {
        border-color: #2d8c72 !important;
        background: #f0faf7 !important;
    }
    .role-category-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 20px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }
    .cat-obvious { background: #dff0eb; color: #1a6b5a; }
    .cat-stretch { background: #e8e4f7; color: #5a3da8; }
    .cat-hidden  { background: #fef3e2; color: #9a6000; }
    .role-title  { color: #1a2e2a; font-size: clamp(0.88rem, 2.8vw, 1rem); font-weight: 700; margin-bottom: 0.3rem; line-height: 1.3; }
    .role-reason { color: #4a6b64; font-size: clamp(0.78rem, 2.4vw, 0.88rem); line-height: 1.5; }
    .role-salary { color: #2d8c72; font-size: 0.8rem; font-weight: 600; margin-top: 0.4rem; }

    /* ── Job cards ── */
    .job-card {
        background: #ffffff;
        border: 1px solid #c8dbd7;
        border-radius: 14px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .job-card:hover {
        border-color: #2d8c72;
        box-shadow: 0 4px 16px rgba(45,140,114,0.1);
    }
    .job-title {
        color: #1a3a34;
        font-size: clamp(0.92rem, 3vw, 1.05rem);
        font-weight: 700;
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }
    .job-meta {
        color: #5a7b74;
        font-size: clamp(0.75rem, 2.3vw, 0.83rem);
        margin-bottom: 0.7rem;
        line-height: 1.6;
    }
    .job-description {
        color: #3a5a54;
        font-size: clamp(0.8rem, 2.5vw, 0.88rem);
        line-height: 1.6;
    }
    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: clamp(0.75rem, 2.3vw, 0.83rem);
        margin-bottom: 0.7rem;
    }
    .score-high   { background: #dff0eb; color: #1a6b5a; }
    .score-medium { background: #fef3e2; color: #9a6000; }
    .score-low    { background: #fde8e8; color: #9a2020; }
    .salary-badge {
        background: #e4edeb;
        color: #2d6b5a;
        padding: 0.15rem 0.6rem;
        border-radius: 20px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-left: 0.3rem;
        white-space: nowrap;
    }

    /* ── Analysis box ── */
    .analysis-box {
        background: #f5fbf9;
        border-left: 4px solid #2d8c72;
        border-radius: 0 10px 10px 0;
        padding: 1.2rem;
        color: #1a3a34;
        font-size: clamp(0.82rem, 2.5vw, 0.93rem);
        line-height: 1.9;
        margin-top: 0.5rem;
    }

    /* ── Sidebar ── */
    .step-indicator {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.6rem 0.9rem;
        border-radius: 8px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .step-complete { background: #dff0eb; color: #1a6b5a; }
    .step-pending  { background: #eef3f2; color: #8aada7; }
    .stat-card   { background: #ffffff; border: 1px solid #c8dbd7; border-radius: 10px; padding: 0.8rem; text-align: center; margin-bottom: 0.5rem; }
    .stat-number { font-size: 1.6rem; font-weight: 800; color: #2d8c72; }
    .stat-label  { font-size: 0.75rem; color: #6a9b94; margin-top: 0.2rem; }

    /* ── Empty state ── */
    .empty-state       { text-align: center; padding: 2rem 1rem; color: #7a9e97; font-size: 0.95rem; }
    .empty-state .icon { font-size: 2.5rem; margin-bottom: 0.8rem; }

    /* ── Mobile button tweaks ── */
    .stButton > button {
        font-size: clamp(0.78rem, 2.5vw, 0.9rem) !important;
        padding: 0.5rem 0.8rem !important;
        border-radius: 8px !important;
        min-height: 2.4rem !important;
    }

    /* ── Mobile: stack columns on narrow screens ── */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .main-header {
            padding: 1.2rem 0.8rem;
            border-radius: 10px;
        }
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

def initialise_session_state() -> None:
    """Initialise all session state variables on first run."""
    defaults: dict = {
        "cv_text":           None,
        "parsed_roles":      [],
        "strengths_summary": "",
        "selected_roles":    [],
        "scored_jobs":       [],
        "app_stage":         "upload",
        "search_country":    "gb",
        "results_per_role":  5,
        "include_remote":    True,
        "location_filter":   None,
        "postcode_input":    "",
        "location_status":   "",
        "location_message":  "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialise_session_state()


# ─────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────

STAGES = ["upload", "select_roles", "results"]
STAGE_LABELS = {
    "upload":       "📄 Upload CV",
    "select_roles": "💡 Pick Roles",
    "results":      "💼 Jobs",
}


def go_to(stage: str) -> None:
    st.session_state.app_stage = stage
    st.rerun()


def go_back() -> None:
    idx = STAGES.index(st.session_state.app_stage)
    if idx > 0:
        go_to(STAGES[idx - 1])


def render_breadcrumb() -> None:
    """Render compact breadcrumb — stays readable on small screens."""
    current       = st.session_state.app_stage
    current_index = STAGES.index(current) if current in STAGES else len(STAGES)
    parts         = []

    for i, stage in enumerate(STAGES):
        label = STAGE_LABELS[stage]
        if i < current_index:
            parts.append(f'<span class="bc-step done">{label}</span>')
        elif i == current_index:
            parts.append(f'<span class="bc-step active">{label}</span>')
        else:
            parts.append(f'<span class="bc-step">{label}</span>')

    separator = '<span class="bc-arrow"> › </span>'
    st.markdown(
        f'<div class="breadcrumb">{separator.join(parts)}</div>',
        unsafe_allow_html=True,
    )

    if current_index > 0 and current in STAGES:
        if st.button(
            f"← Back",
            key="breadcrumb_back",
            use_container_width=False,
        ):
            go_back()


# ─────────────────────────────────────────────
# PURE HELPERS
# ─────────────────────────────────────────────

def get_score_class(score: float) -> str:
    if score >= 70: return "score-high"
    if score >= 45: return "score-medium"
    return "score-low"


def get_score_label(score: float) -> str:
    if score >= 70: return "Strong Match"
    if score >= 45: return "Partial Match"
    return "Weak Match"


def format_salary(job: dict) -> str:
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo and hi: return f"£{int(lo):,} – £{int(hi):,}"
    if lo:        return f"From £{int(lo):,}"
    if hi:        return f"Up to £{int(hi):,}"
    return "Salary not listed"


# ─────────────────────────────────────────────
# LOCATION HELPERS
# ─────────────────────────────────────────────

def _apply_postcode(postcode: str) -> None:
    with st.spinner("📍 Looking up postcode..."):
        loc = geocode_postcode(postcode)
    if loc:
        st.session_state.location_filter  = loc
        st.session_state.location_status  = "ok"
        st.session_state.location_message = (
            f"Filtering jobs near **{loc.display}** within **{loc.radius_km} km**"
        )
    else:
        st.session_state.location_filter  = None
        st.session_state.location_status  = "error"
        st.session_state.location_message = (
            f"Could not find **{postcode.strip().upper()}**. "
            "Check the postcode or leave blank for nationwide."
        )


def _apply_ip_location() -> None:
    with st.spinner("🌐 Detecting your location..."):
        loc = detect_location_from_ip()
    if loc:
        st.session_state.location_filter  = loc
        st.session_state.location_status  = "ok"
        st.session_state.location_message = (
            f"Location detected as **{loc.display}** *(approximate)* "
            f"within **{loc.radius_km} km**"
        )
    else:
        st.session_state.location_filter  = None
        st.session_state.location_status  = "error"
        st.session_state.location_message = (
            "Could not detect your location. "
            "Enter a postcode manually or leave blank for nationwide."
        )


def _clear_location() -> None:
    st.session_state.location_filter  = None
    st.session_state.location_status  = ""
    st.session_state.location_message = ""
    st.session_state.postcode_input   = ""


# ─────────────────────────────────────────────
# LOCATION UI — mobile optimised
# ─────────────────────────────────────────────

def render_location_section() -> None:
    """
    Location filter panel — single column layout for mobile,
    with postcode input stacked above action buttons.
    """
    st.markdown("#### 📍 Location *(optional)*")
    st.caption(
        "Enter a UK postcode to find nearby jobs, or leave blank to search nationwide. "
        "Remote jobs are always included."
    )

    # Postcode input — full width for easy mobile tapping
    postcode_val = st.text_input(
        "UK postcode",
        value=st.session_state.postcode_input,
        placeholder="e.g. M1 1AE",
        label_visibility="collapsed",
        key="postcode_text_input",
    )
    st.session_state.postcode_input = postcode_val

    # Buttons on one row — 3 equal columns
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Apply", use_container_width=True, key="btn_apply_postcode"):
            if postcode_val.strip():
                _apply_postcode(postcode_val)
            else:
                _clear_location()
            st.rerun()
    with col2:
        if st.button(
            "🌐 My Location",
            use_container_width=True,
            key="btn_ip_location",
            help="Approximate — based on your internet connection.",
        ):
            _apply_ip_location()
            st.rerun()
    with col3:
        if st.button("✕ Clear", use_container_width=True, key="btn_clear_location"):
            _clear_location()
            st.rerun()

    # Radius slider — full width when active
    loc: LocationFilter | None = st.session_state.get("location_filter")
    if loc and st.session_state.location_status == "ok":
        new_radius = st.slider(
            "Search radius (km)",
            min_value=5,
            max_value=150,
            value=loc.radius_km,
            step=5,
            key="radius_slider",
            help="Applies to Adzuna and Reed. Remote jobs ignore this.",
        )
        if new_radius != loc.radius_km:
            loc.radius_km = new_radius
            st.session_state.location_filter = loc

    # Status banner
    status  = st.session_state.get("location_status", "")
    message = st.session_state.get("location_message", "")

    if status == "ok" and message:
        st.markdown(
            f'<div class="location-ok">'
            f'<span class="loc-label">📍 Active Location Filter</span>'
            f'{message}</div>',
            unsafe_allow_html=True,
        )
    elif status == "error" and message:
        st.markdown(
            f'<div class="location-err">⚠️ {message}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🎯 CV Job Matcher")
        st.markdown("*AI-powered career guidance*")
        st.markdown("---")

        loc: LocationFilter | None = st.session_state.get("location_filter")
        if loc:
            st.markdown(f"📍 **{loc.display}** · {loc.radius_km} km")
            st.markdown("---")

        st.markdown("### Progress")
        steps = [
            ("📄 Upload CV",  st.session_state.cv_text is not None),
            ("💡 Pick Roles", len(st.session_state.selected_roles) > 0),
            ("💼 View Jobs",  len(st.session_state.scored_jobs) > 0),
        ]
        for label, complete in steps:
            css  = "step-complete" if complete else "step-pending"
            icon = "✅" if complete else "⏳"
            st.markdown(
                f'<div class="step-indicator {css}">{icon} {label}</div>',
                unsafe_allow_html=True,
            )

        if st.session_state.scored_jobs:
            st.markdown("---")
            st.markdown("### Results")
            scores = [j["match_score"] for j in st.session_state.scored_jobs]
            strong = sum(1 for s in scores if s >= 70)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="stat-card"><div class="stat-number">{len(scores)}</div><div class="stat-label">Jobs</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-card"><div class="stat-number">{strong}</div><div class="stat-label">Strong</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-card"><div class="stat-number">{max(scores)}%</div><div class="stat-label">Top Score</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-card"><div class="stat-number">{round(sum(scores)/len(scores),1)}%</div><div class="stat-label">Avg Score</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

def render_header() -> None:
    st.markdown("""
        <div class="main-header">
            <h1>🎯 CV Job Matcher</h1>
            <p>Upload your CV · Discover roles · Find live jobs · Get AI insights</p>
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SCREEN 1 — UPLOAD
# ─────────────────────────────────────────────

def render_upload_stage() -> None:
    st.markdown("### 📄 Upload Your CV")

    uploaded_file = st.file_uploader(
        "Upload your CV (PDF or Word .docx)",
        type=["pdf", "docx"],
        help="Processed in memory only — never stored or shared.",
    )

    if not uploaded_file:
        st.markdown("""
            <div class="empty-state">
                <div class="icon">📂</div>
                Upload your CV to get started.<br><br>
                We'll identify every role you're suited for<br>
                and let you choose which ones to explore.
            </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner("📖 Reading your CV..."):
        try:
            cv_text = extract_cv_text(uploaded_file)
        except ValueError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error("Could not read your CV. Please check the file and try again.")
            logger.error(f"CV extraction error: {e}")
            return

    if not cv_text:
        st.error("No text could be extracted. Ensure your CV is not a scanned image.")
        return

    st.session_state.cv_text = cv_text
    st.success(f"✅ CV uploaded — {len(cv_text.split()):,} words extracted.")

    with st.spinner("🤖 Analysing your CV and identifying matching roles..."):
        try:
            roles, summary = suggest_job_roles(cv_text)
            st.session_state.parsed_roles      = roles
            st.session_state.strengths_summary = summary
            logger.info(f"Parsed {len(roles)} roles successfully.")
        except (ValueError, RuntimeError) as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"Role analysis failed: {e}")
            logger.error(f"Role suggestion error: {e}")
            return

    go_to("select_roles")


# ─────────────────────────────────────────────
# SCREEN 2 — ROLE SELECTION
# ─────────────────────────────────────────────

def render_role_selection_stage() -> None:
    st.markdown("### 💡 Roles You're Suited For")

    if st.session_state.strengths_summary:
        st.markdown(f"""
            <div class="strengths-banner">
                <strong>🔑 Your Profile</strong><br>
                {st.session_state.strengths_summary}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("Select roles to explore — we'll find live jobs and rank them against your CV.")

    roles      = st.session_state.parsed_roles
    categories: dict[str, list[dict]] = {}
    for role in roles:
        categories.setdefault(role["category"], []).append(role)

    category_config = {
        "Obvious Match": ("cat-obvious", "🎯 Obvious Matches", "Roles you're already fully qualified for"),
        "Stretch Role":  ("cat-stretch", "🚀 Stretch Roles",   "Roles within reach with minor upskilling"),
        "Hidden Gem":    ("cat-hidden",  "💎 Hidden Gems",      "Surprising roles your background suits well"),
    }

    selected = list(st.session_state.selected_roles)

    for cat_key, (css_class, cat_label, cat_desc) in category_config.items():
        cat_roles = categories.get(cat_key, [])
        if not cat_roles:
            continue

        st.markdown(f"#### {cat_label}")
        st.caption(cat_desc)

        # Single column on mobile, two columns on desktop
        num_cols = 1 if len(cat_roles) == 1 else 2
        cols     = st.columns(num_cols)

        for idx, role in enumerate(cat_roles):
            with cols[idx % num_cols]:
                checked = st.checkbox(
                    label=role["title"],
                    value=role["title"] in selected,
                    key=f"role_{cat_key}_{idx}",
                )
                st.markdown(f"""
                    <div class="role-card {'role-card-selected' if checked else ''}">
                        <span class="role-category-badge {css_class}">{cat_key}</span>
                        <div class="role-title">{role["title"]}</div>
                        <div class="role-reason">{role["reason"]}</div>
                        <div class="role-salary">💷 {role["salary"]}</div>
                    </div>
                """, unsafe_allow_html=True)

                if checked and role["title"] not in selected:
                    selected.append(role["title"])
                elif not checked and role["title"] in selected:
                    selected.remove(role["title"])

    st.session_state.selected_roles = selected
    st.markdown("---")

    # Location filter
    render_location_section()

    if not selected:
        st.info("☝️ Select at least one role above to continue.")
        return

    st.success(f"✅ {len(selected)} role(s) selected: {', '.join(selected)}")

    # Search options — stacked on mobile
    st.markdown("#### ⚙️ Search Options")

    country = st.selectbox(
        "Country",
        options=["gb", "us", "au", "ca"],
        format_func=lambda x: {
            "gb": "🇬🇧 UK", "us": "🇺🇸 USA",
            "au": "🇦🇺 Australia", "ca": "🇨🇦 Canada",
        }[x],
        index=["gb", "us", "au", "ca"].index(st.session_state.search_country),
    )
    st.session_state.search_country = country

    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state.results_per_role = st.selectbox(
            "Jobs per role",
            options=[3, 5, 10],
            index=[3, 5, 10].index(st.session_state.results_per_role),
        )
    with col_b:
        st.session_state.include_remote = st.checkbox(
            "Include remote jobs",
            value=st.session_state.include_remote,
            help="Adds remote listings from Remotive.",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Full-width CTA button — easy to tap on mobile
    if st.button(
        "🔍 Find My Jobs",
        use_container_width=True,
        type="primary",
        key="find_jobs_btn",
    ):
        _run_job_search(selected)


def _run_job_search(selected_roles: list[str]) -> None:
    location: LocationFilter | None = st.session_state.get("location_filter")
    all_jobs: list[dict]            = []
    progress = st.progress(0, text="Searching live jobs...")

    for i, role_title in enumerate(selected_roles):
        progress.progress(
            int((i / len(selected_roles)) * 80),
            text=f"Searching: {role_title}...",
        )
        try:
            jobs = fetch_jobs(
                keywords         = role_title,
                country          = st.session_state.search_country,
                results_per_page = st.session_state.results_per_role,
                include_remote   = st.session_state.include_remote,
                location         = location,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.warning(f"Job fetch failed for '{role_title}': {e}")

    if not all_jobs:
        st.warning("No jobs found. Try different roles, a wider radius, or a different country.")
        progress.empty()
        return

    progress.progress(85, text="Scoring jobs against your CV...")

    try:
        scored = score_jobs(st.session_state.cv_text, all_jobs)
        st.session_state.scored_jobs = scored
    except Exception as e:
        st.error("Scoring failed. Please try again.")
        logger.error(f"Scoring error: {e}")
        progress.empty()
        return

    progress.progress(100, text="Done!")
    go_to("results")


# ─────────────────────────────────────────────
# SCREEN 3 — JOB RESULTS
# ─────────────────────────────────────────────

def render_job_card(job: dict, index: int) -> None:
    """
    Render a single scored job card — mobile friendly layout.
    Buttons stacked vertically on narrow screens via full width.
    """
    score       = job.get("match_score", 0)
    score_class = get_score_class(score)
    score_label = get_score_label(score)
    salary      = format_salary(job)
    description = job.get("description", "")
    preview     = description[:250] + ("..." if len(description) > 250 else "")
    source      = job.get("source", "")
    title       = job.get("title",    "Unknown Role")
    company     = job.get("company",  "Unknown")
    location    = job.get("location", "Unknown")
    created     = job.get("created",  "")

    source_colours = {
        "Adzuna":   "#2d8c72",
        "Reed":     "#0072c6",
        "Remotive": "#00b894",
    }
    source_colour = source_colours.get(source, "#7a9e97")

    score_colours = {"score-high": "#1a6b5a", "score-medium": "#9a6000", "score-low": "#9a2020"}
    score_bgs     = {"score-high": "#dff0eb", "score-medium": "#fef3e2", "score-low": "#fde8e8"}
    s_colour      = score_colours.get(score_class, "#1a6b5a")
    s_bg          = score_bgs.get(score_class, "#dff0eb")

    # Card rendered with inline styles — immune to special chars in job data
    st.markdown(f"""
        <div class="job-card">
            <div style="display:flex;justify-content:space-between;
                align-items:flex-start;gap:0.5rem;margin-bottom:0.3rem;">
                <div class="job-title" style="flex:1;">{title}</div>
                <span style="background:{source_colour}18;color:{source_colour};
                    padding:0.15rem 0.6rem;border-radius:20px;
                    font-size:0.7rem;font-weight:700;white-space:nowrap;">{source}</span>
            </div>
            <div class="job-meta">
                🏢 {company}<br>
                📍 {location} &nbsp;·&nbsp; 📅 {created}
                <span class="salary-badge">💷 {salary}</span>
            </div>
            <span style="background:{s_bg};color:{s_colour};padding:0.25rem 0.8rem;
                border-radius:20px;font-weight:700;font-size:0.8rem;
                display:inline-block;margin-bottom:0.7rem;">
                {score}% — {score_label}
            </span>
            <div class="job-description">{preview}</div>
        </div>
    """, unsafe_allow_html=True)

    # Buttons — 3 equal columns, full width for tap targets
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("🔗 View Job", job.get("url", "#"), use_container_width=True)
    with col2:
        toggle_key = f"show_analysis_{index}"
        btn_label  = "✕ Close" if st.session_state.get(toggle_key) else "🤖 Analysis"
        if st.button(btn_label, key=f"toggle_{index}", use_container_width=True):
            st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
            st.rerun()
    with col3:
        st.button(
            "✉️ Letter",
            key=f"cover_{index}",
            use_container_width=True,
            disabled=True,
            help="Coming soon",
        )

    # Inline analysis panel
    if st.session_state.get(f"show_analysis_{index}", False):
        analysis_key = f"analysis_cache_{index}"

        if analysis_key not in st.session_state:
            with st.spinner("Analysing with Groq AI..."):
                try:
                    result = analyse_match(st.session_state.cv_text, job)
                    st.session_state[analysis_key] = result
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    st.session_state[f"show_analysis_{index}"] = False
                    st.rerun()

        if analysis_key in st.session_state:
            st.markdown(f"""
                <div class="analysis-box">
                    {st.session_state[analysis_key].replace(chr(10), "<br>")}
                </div>
            """, unsafe_allow_html=True)
            if st.button("📋 Copy", key=f"copy_{index}", use_container_width=True):
                st.code(st.session_state[analysis_key], language=None)

    st.markdown("---")


def render_results_stage() -> None:
    loc: LocationFilter | None = st.session_state.get("location_filter")
    header_suffix = f" near **{loc.display}**" if loc else ""

    st.markdown(f"### 💼 Your Job Matches{header_suffix}")
    st.markdown(
        f"**{len(st.session_state.scored_jobs)} jobs** across "
        f"**{len(st.session_state.selected_roles)} role(s)**, ranked by CV match."
    )

    # Filters — stacked on mobile
    min_score   = st.slider("Min match score", 0, 100, 0, step=5)
    sort_order  = st.selectbox("Sort by", ["Match Score", "Salary"])
    role_filter = st.selectbox(
        "Filter by role",
        ["All Roles"] + st.session_state.selected_roles,
    )

    filtered = [j for j in st.session_state.scored_jobs if j["match_score"] >= min_score]

    if role_filter != "All Roles":
        filtered = [
            j for j in filtered
            if role_filter.lower() in j.get("title", "").lower()
        ]

    if sort_order == "Salary":
        filtered.sort(key=lambda x: x.get("salary_max") or 0, reverse=True)

    if not filtered:
        st.info("No jobs match your filters. Try lowering the minimum score.")
        return

    st.markdown(f"Showing **{len(filtered)}** jobs.")
    st.markdown("---")

    for i, job in enumerate(filtered):
        render_job_card(job, i)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    render_sidebar()
    render_header()
    render_breadcrumb()

    stage = st.session_state.app_stage

    if stage == "upload":
        render_upload_stage()
    elif stage == "select_roles":
        render_role_selection_stage()
    elif stage == "results":
        render_results_stage()


if __name__ == "__main__":
    main()