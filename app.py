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
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #f0f4f3;
        color: #1a2e2a;
    }

    /* ── Header ── */
    .main-header {
        background: #1a3a34;
        padding: 2.5rem 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #2d5a50;
    }
    .main-header h1 { color: #7dd3c0; font-size: 2.6rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .main-header p  { color: #a8c5be; font-size: 1rem; margin-top: 0.5rem; margin-bottom: 0; }

    /* ── Breadcrumb ── */
    .breadcrumb {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.75rem 1.25rem; background: #e4edeb;
        border-radius: 10px; margin-bottom: 1.5rem;
        font-size: 0.875rem; border: 1px solid #c8dbd7;
    }
    .bc-step        { color: #7a9e97; font-weight: 500; }
    .bc-step.active { color: #1a6b5a; font-weight: 700; }
    .bc-step.done   { color: #2d8c72; font-weight: 500; }
    .bc-arrow       { color: #b0ccc7; font-size: 0.75rem; }

    /* ── Location banners ── */
    .location-ok {
        background: #f0faf7; border: 1px solid #a8d5c8;
        border-left: 4px solid #2d8c72; border-radius: 10px;
        padding: 0.9rem 1.2rem; margin: 0.75rem 0;
        font-size: 0.88rem; color: #1a3a34;
    }
    .location-ok .loc-label {
        color: #1a6b5a; font-weight: 700;
        font-size: 0.76rem; text-transform: uppercase;
        letter-spacing: 0.5px; display: block; margin-bottom: 0.2rem;
    }
    .location-err {
        background: #fef3e2; border: 1px solid #f5c842;
        border-left: 4px solid #f5a623; border-radius: 10px;
        padding: 0.9rem 1.2rem; margin: 0.75rem 0;
        font-size: 0.88rem; color: #6b4c00;
    }

    /* ── Strengths banner ── */
    .strengths-banner {
        background: #f0faf7; border: 1px solid #a8d5c8;
        border-left: 4px solid #2d8c72; border-radius: 10px;
        padding: 1.2rem 1.5rem; margin-bottom: 1.5rem;
        color: #1a3a34; font-size: 0.93rem; line-height: 1.7;
    }
    .strengths-banner strong { color: #1a6b5a; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.6px; }

    /* ── Role cards ── */
    .role-card {
        background: #ffffff; border: 1.5px solid #c8dbd7;
        border-radius: 12px; padding: 1.2rem 1.5rem;
        margin-top: 0.4rem; margin-bottom: 0.8rem;
        transition: border-color 0.2s ease;
    }
    .role-card-selected { border-color: #2d8c72 !important; background: #f0faf7 !important; }
    .role-category-badge {
        display: inline-block; padding: 0.2rem 0.7rem;
        border-radius: 20px; font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.6px; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .cat-obvious { background: #dff0eb; color: #1a6b5a; }
    .cat-stretch { background: #e8e4f7; color: #5a3da8; }
    .cat-hidden  { background: #fef3e2; color: #9a6000; }
    .role-title  { color: #1a2e2a; font-size: 1rem; font-weight: 700; margin-bottom: 0.3rem; }
    .role-reason { color: #4a6b64; font-size: 0.88rem; line-height: 1.5; }
    .role-salary { color: #2d8c72; font-size: 0.82rem; font-weight: 600; margin-top: 0.4rem; }

    /* ── Job cards ── */
    .job-card {
        background: #ffffff; border: 1px solid #c8dbd7;
        border-radius: 14px; padding: 1.5rem; margin-bottom: 1rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .job-card:hover { border-color: #2d8c72; box-shadow: 0 4px 20px rgba(45,140,114,0.1); }
    .job-title       { color: #1a3a34; font-size: 1.1rem; font-weight: 700; margin-bottom: 0.3rem; }
    .job-meta        { color: #5a7b74; font-size: 0.85rem; margin-bottom: 0.8rem; }
    .job-description { color: #3a5a54; font-size: 0.9rem; line-height: 1.6; }

    .score-badge  { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 20px; font-weight: 700; font-size: 0.85rem; margin-bottom: 0.8rem; }
    .score-high   { background: #dff0eb; color: #1a6b5a; }
    .score-medium { background: #fef3e2; color: #9a6000; }
    .score-low    { background: #fde8e8; color: #9a2020; }
    .salary-badge { background: #e4edeb; color: #2d6b5a; padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.78rem; font-weight: 600; margin-left: 0.5rem; }

    /* ── Analysis box ── */
    .analysis-box {
        background: #f5fbf9; border-left: 4px solid #2d8c72;
        border-radius: 0 10px 10px 0; padding: 1.5rem;
        color: #1a3a34; font-size: 0.93rem; line-height: 1.9; margin-top: 0.5rem;
    }

    /* ── Sidebar ── */
    .step-indicator {
        display: flex; align-items: center; gap: 0.8rem;
        padding: 0.7rem 1rem; border-radius: 8px;
        margin-bottom: 0.5rem; font-size: 0.875rem; font-weight: 600;
    }
    .step-complete { background: #dff0eb; color: #1a6b5a; }
    .step-pending  { background: #eef3f2; color: #8aada7; }
    .stat-card   { background: #ffffff; border: 1px solid #c8dbd7; border-radius: 10px; padding: 1rem; text-align: center; margin-bottom: 0.5rem; }
    .stat-number { font-size: 1.8rem; font-weight: 800; color: #2d8c72; }
    .stat-label  { font-size: 0.78rem; color: #6a9b94; margin-top: 0.2rem; }

    /* ── Empty state ── */
    .empty-state       { text-align: center; padding: 3rem 1rem; color: #7a9e97; font-size: 1rem; }
    .empty-state .icon { font-size: 3rem; margin-bottom: 1rem; }

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
        # Location
        "location_filter":   None,   # LocationFilter | None
        "postcode_input":    "",     # raw text in the input box
        "location_status":   "",     # "ok" | "error" | ""
        "location_message":  "",     # human-readable message
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
    "results":      "💼 Job Results",
}


def go_to(stage: str) -> None:
    st.session_state.app_stage = stage
    st.rerun()


def go_back() -> None:
    idx = STAGES.index(st.session_state.app_stage)
    if idx > 0:
        go_to(STAGES[idx - 1])


def render_breadcrumb() -> None:
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
        back_label = f"← {STAGE_LABELS[STAGES[current_index - 1]]}"
        if st.button(back_label, key="breadcrumb_back"):
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
    """Geocode postcode and store result in session state."""
    with st.spinner("📍 Looking up postcode..."):
        loc = geocode_postcode(postcode)

    if loc:
        st.session_state.location_filter  = loc
        st.session_state.location_status  = "ok"
        st.session_state.location_message = (
            f"Filtering jobs near **{loc.display}** "
            f"within **{loc.radius_km} km**"
        )
        logger.info(f"Postcode resolved: {loc}")
    else:
        st.session_state.location_filter  = None
        st.session_state.location_status  = "error"
        st.session_state.location_message = (
            f"Could not find postcode **{postcode.strip().upper()}**. "
            "Check the postcode and try again, or leave blank to search nationwide."
        )


def _apply_ip_location() -> None:
    """Detect location from IP and store result in session state."""
    with st.spinner("🌐 Detecting your location..."):
        loc = detect_location_from_ip()

    if loc:
        st.session_state.location_filter  = loc
        st.session_state.location_status  = "ok"
        st.session_state.location_message = (
            f"Location detected as **{loc.display}** *(approximate)* — "
            f"within **{loc.radius_km} km**"
        )
        logger.info(f"IP location detected: {loc}")
    else:
        st.session_state.location_filter  = None
        st.session_state.location_status  = "error"
        st.session_state.location_message = (
            "Could not detect your location automatically. "
            "Enter a postcode manually, or leave blank to search nationwide."
        )


def _clear_location() -> None:
    """Remove any active location filter from session state."""
    st.session_state.location_filter  = None
    st.session_state.location_status  = ""
    st.session_state.location_message = ""
    st.session_state.postcode_input   = ""


# ─────────────────────────────────────────────
# LOCATION UI
# ─────────────────────────────────────────────

def render_location_section() -> None:
    """
    Render the location filtering panel inside the role selection screen.

    Provides:
      - UK postcode input + Apply button  (uses postcodes.io)
      - "Use my location" button          (uses ip-api.com as fallback)
      - Radius slider when a location is active
      - Clear button to remove any filter
      - Status banner (success or error)
    """
    st.markdown("#### 📍 Location Filter *(optional)*")
    st.caption(
        "Narrow results to jobs near you. Leave blank to search nationwide. "
        "Remote jobs from Remotive are always included regardless."
    )

    col_input, col_apply, col_ip, col_clear = st.columns([3, 1.1, 1.8, 1])

    with col_input:
        postcode_val = st.text_input(
            "UK postcode",
            value=st.session_state.postcode_input,
            placeholder="e.g. M1 1AE  or  SW1A 2AA",
            label_visibility="collapsed",
            key="postcode_text_input",
        )
        st.session_state.postcode_input = postcode_val

    with col_apply:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Apply", use_container_width=True, key="btn_apply_postcode"):
            if postcode_val.strip():
                _apply_postcode(postcode_val)
            else:
                _clear_location()

    with col_ip:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "🌐 Use my location",
            use_container_width=True,
            key="btn_ip_location",
            help="Approximate detection based on your internet connection.",
        ):
            _apply_ip_location()

    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✕ Clear", use_container_width=True, key="btn_clear_location"):
            _clear_location()

    # ── Radius slider — only visible when a location is active ──
    loc: LocationFilter | None = st.session_state.get("location_filter")
    if loc and st.session_state.location_status == "ok":
        radius_col, _ = st.columns([2, 3])
        with radius_col:
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

    # ── Status banner ──
    status  = st.session_state.get("location_status", "")
    message = st.session_state.get("location_message", "")

    if status == "ok" and message:
        st.markdown(
            f'<div class="location-ok">'
            f'<span class="loc-label">📍 Active Location Filter</span>'
            f'{message}'
            f'</div>',
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

        # Show active location
        loc: LocationFilter | None = st.session_state.get("location_filter")
        if loc:
            st.markdown(f"📍 **Location:** {loc.display}")
            st.markdown(f"*Radius: {loc.radius_km} km*")
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
                st.markdown(f'<div class="stat-card"><div class="stat-number">{len(scores)}</div><div class="stat-label">Jobs Found</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-card"><div class="stat-number">{strong}</div><div class="stat-label">Strong Matches</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-card"><div class="stat-number">{max(scores)}%</div><div class="stat-label">Top Score</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-card"><div class="stat-number">{round(sum(scores)/len(scores), 1)}%</div><div class="stat-label">Avg Score</div></div>', unsafe_allow_html=True)

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
            <p>Upload your CV · Discover your ideal roles · Find live matching jobs · Get AI insights</p>
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SCREEN 1 — UPLOAD
# ─────────────────────────────────────────────

def render_upload_stage() -> None:
    """Screen 1: Upload CV, extract text, auto-generate role suggestions."""
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
                Drop your CV above to get started.<br><br>
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
    """Screen 2: Display AI-suggested roles, location filter, and search options."""
    st.markdown("### 💡 Roles You're Suited For")

    if st.session_state.strengths_summary:
        st.markdown(f"""
            <div class="strengths-banner">
                <strong>🔑 Your Profile</strong><br>
                {st.session_state.strengths_summary}
            </div>
        """, unsafe_allow_html=True)

    st.markdown(
        "Select the roles you'd like to explore — "
        "we'll find live jobs and rank them against your CV."
    )

    # ── Role cards ──
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
        cols = st.columns(2)

        for idx, role in enumerate(cat_roles):
            with cols[idx % 2]:
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

    # ── Location filter ──
    render_location_section()

    # ── Search options ──
    if not selected:
        st.info("☝️ Select at least one role above to continue.")
        return

    st.success(f"✅ {len(selected)} role(s) selected: {', '.join(selected)}")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.session_state.search_country = st.selectbox(
            "Country",
            options=["gb", "us", "au", "ca"],
            format_func=lambda x: {
                "gb": "🇬🇧 UK", "us": "🇺🇸 USA",
                "au": "🇦🇺 Australia", "ca": "🇨🇦 Canada",
            }[x],
            index=["gb", "us", "au", "ca"].index(st.session_state.search_country),
        )
    with col2:
        st.session_state.results_per_role = st.selectbox(
            "Jobs per role",
            options=[3, 5, 10],
            index=[3, 5, 10].index(st.session_state.results_per_role),
        )
    with col3:
        st.session_state.include_remote = st.checkbox(
            "Include remote",
            value=st.session_state.include_remote,
            help="Include remote jobs from Remotive (location filter does not apply to these).",
        )
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Find My Jobs", use_container_width=True, type="primary"):
            _run_job_search(selected)


def _run_job_search(selected_roles: list[str]) -> None:
    """
    Fetch, score, and store jobs for all selected roles then navigate to results.

    Passes the active LocationFilter (if any) through to fetch_jobs so that
    Adzuna and Reed results are geographically filtered.

    Args:
        selected_roles: List of role title strings chosen by the user
    """
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
        st.warning("No jobs found. Try selecting different roles, changing country, or widening your search radius.")
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
    Render a single scored job card with collapsible AI analysis.

    Args:
        job:   Scored job dictionary
        index: Position index used for unique widget keys
    """
    score       = job.get("match_score", 0)
    score_class = get_score_class(score)
    score_label = get_score_label(score)
    salary      = format_salary(job)
    description = job.get("description", "")
    preview     = description[:300] + ("..." if len(description) > 300 else "")
    source      = job.get("source", "")

    source_colours = {
        "Adzuna":   "#2d8c72",
        "Reed":     "#0072c6",
        "Remotive": "#00b894",
    }
    source_colour = source_colours.get(source, "#7a9e97")

    st.markdown(f"""
        <div class="job-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div class="job-title">{job.get("title", "Unknown Role")}</div>
                <span style="background:{source_colour}18;color:{source_colour};
                    padding:0.2rem 0.7rem;border-radius:20px;
                    font-size:0.73rem;font-weight:700;">{source}</span>
            </div>
            <div class="job-meta">
                🏢 {job.get("company", "Unknown")} &nbsp;|&nbsp;
                📍 {job.get("location", "Unknown")} &nbsp;|&nbsp;
                📅 {job.get("created", "")}
                <span class="salary-badge">💷 {salary}</span>
            </div>
            <span class="score-badge {score_class}">{score}% — {score_label}</span>
            <div class="job-description">{preview}</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("🔗 View Job", job.get("url", "#"), use_container_width=True)
    with col2:
        toggle_key = f"show_analysis_{index}"
        btn_label  = "🤖 Hide Analysis" if st.session_state.get(toggle_key) else "🤖 AI Analysis"
        if st.button(btn_label, key=f"toggle_{index}", use_container_width=True):
            st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
            st.rerun()
    with col3:
        st.button(
            "✉️ Cover Letter",
            key=f"cover_{index}",
            use_container_width=True,
            disabled=True,
            help="Coming soon",
        )

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

            if st.button("📋 Copy Analysis", key=f"copy_{index}"):
                st.code(st.session_state[analysis_key], language=None)

    st.markdown("---")


def render_results_stage() -> None:
    """Screen 3: Display all scored job results with filters and inline analysis."""
    loc: LocationFilter | None = st.session_state.get("location_filter")

    header_suffix = f" near **{loc.display}**" if loc else ""
    st.markdown(f"### 💼 Your Live Job Matches{header_suffix}")
    st.markdown(
        f"Found **{len(st.session_state.scored_jobs)} jobs** across "
        f"**{len(st.session_state.selected_roles)} role(s)**, ranked by CV match score."
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        min_score = st.slider("Minimum match score", 0, 100, 0, step=5)
    with col2:
        sort_order = st.selectbox("Sort by", ["Match Score", "Salary"])
    with col3:
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