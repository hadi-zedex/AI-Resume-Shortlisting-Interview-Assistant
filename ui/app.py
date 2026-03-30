import streamlit as st
import sys
from pathlib import Path

# Make sure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import run_pipeline, PipelineResult

# ------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Resume Shortlister",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------------
# Custom CSS
# ------------------------------------------------------------------
st.markdown("""
<style>
    /* Global */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }

    /* Page header */
    .page-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        border-left: 4px solid #3b82f6;
    }
    .page-header h1 {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0 0 0.3rem 0;
        font-family: 'IBM Plex Mono', monospace;
    }
    .page-header p {
        color: #94a3b8;
        margin: 0;
        font-size: 0.95rem;
    }

    /* Section headers */
    .section-header {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #64748b;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #e2e8f0;
    }

    /* Tier badges */
    .tier-badge-a {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        border: 1px solid #86efac;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .tier-badge-b {
        display: inline-block;
        background: #fef9c3;
        color: #854d0e;
        border: 1px solid #fde047;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .tier-badge-c {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
    }

    /* Info cards */
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }

    /* Score card */
    .score-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .score-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 0.4rem;
    }
    .score-value {
        font-size: 2rem;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
        color: #0f172a;
        line-height: 1;
        margin-bottom: 0.5rem;
    }

    /* Question card */
    .question-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 3px solid #3b82f6;
        border-radius: 0 10px 10px 0;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .question-text {
        font-size: 1rem;
        font-weight: 500;
        color: #0f172a;
        margin-bottom: 0.75rem;
        line-height: 1.5;
    }
    .question-meta {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
    }
    .tag {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
    }
    .tag-ownership    { background: #ede9fe; color: #5b21b6; }
    .tag-achievement  { background: #dcfce7; color: #166534; }
    .tag-technical    { background: #dbeafe; color: #1e40af; }
    .tag-skill-gap    { background: #fee2e2; color: #991b1b; }
    .tag-easy         { background: #f0fdf4; color: #15803d; border: 1px solid #86efac; }
    .tag-medium       { background: #fffbeb; color: #b45309; border: 1px solid #fcd34d; }
    .tag-hard         { background: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; }

    /* Skill pills */
    .skill-pill {
        display: inline-block;
        background: #eff6ff;
        color: #1e40af;
        border: 1px solid #bfdbfe;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 500;
        margin: 0.15rem;
    }

    /* Overall score ring area */
    .overall-score-box {
        background: linear-gradient(135deg, #0f172a, #1e3a5f);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        color: white;
    }
    .overall-score-number {
        font-size: 3.5rem;
        font-weight: 700;
        font-family: 'IBM Plex Mono', monospace;
        line-height: 1;
    }
    .overall-score-label {
        font-size: 0.8rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #94a3b8;
        margin-top: 0.4rem;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 1.5rem 0;
    }

    /* Expander tweaks */
    .streamlit-expanderHeader {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Session state initialisation
# ------------------------------------------------------------------
if "result" not in st.session_state:
    st.session_state.result = None
if "error" not in st.session_state:
    st.session_state.error = None
if "running" not in st.session_state:
    st.session_state.running = False


# ------------------------------------------------------------------
# Page header
# ------------------------------------------------------------------
st.markdown("""
<div class="page-header">
    <h1>🎯 Resume Shortlister</h1>
    <p>AI-powered candidate screening — parse, score, classify, and generate interview plans in seconds.</p>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Layout — two columns: input (left) | results (right)
# ------------------------------------------------------------------
input_col, results_col = st.columns([1, 1.6], gap="large")


# ------------------------------------------------------------------
# LEFT COLUMN — Inputs
# ------------------------------------------------------------------
with input_col:
    st.markdown('<div class="section-header">Resume PDF</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        label="Upload resume",
        type=["pdf"],
        help="Text-based PDFs only. Scanned image PDFs are not supported.",
        label_visibility="collapsed",
    )

    if uploaded_file:
        st.success(f"✓ {uploaded_file.name}  ({uploaded_file.size / 1024:.1f} KB)")

    st.markdown('<div class="section-header">Job Description</div>', unsafe_allow_html=True)
    jd_text = st.text_area(
        label="Paste job description",
        placeholder="Paste the full job description here — requirements, responsibilities, and preferred skills...",
        height=280,
        label_visibility="collapsed",
    )

    char_count = len(jd_text.strip())
    if char_count > 0:
        st.caption(f"{char_count:,} characters")

    st.markdown("<br>", unsafe_allow_html=True)

    run_button = st.button(
        label="▶  Run Screening Pipeline",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running,
    )

    # Clear results button — only show if results exist
    if st.session_state.result:
        if st.button("✕  Clear Results", use_container_width=True):
            st.session_state.result = None
            st.session_state.error = None
            st.rerun()


# ------------------------------------------------------------------
# Pipeline execution
# ------------------------------------------------------------------
if run_button:
    # Input validation
    if not uploaded_file:
        st.session_state.error = "Please upload a resume PDF."
    elif not jd_text.strip():
        st.session_state.error = "Please paste a job description."
    elif len(jd_text.strip()) < 100:
        st.session_state.error = "Job description seems too short. Please paste the full JD."
    else:
        st.session_state.error = None
        st.session_state.running = True

        with results_col:
            with st.spinner("Running pipeline — this takes 20–40 seconds..."):
                try:
                    pdf_bytes = uploaded_file.read()
                    result = run_pipeline(
                        pdf_bytes=pdf_bytes,
                        jd_text=jd_text.strip(),
                    )
                    st.session_state.result = result
                    st.session_state.error = None
                except Exception as e:
                    st.session_state.error = str(e)
                    st.session_state.result = None
                finally:
                    st.session_state.running = False

        st.rerun()


# ------------------------------------------------------------------
# Error display
# ------------------------------------------------------------------
if st.session_state.error:
    with input_col:
        st.error(f"⚠️ {st.session_state.error}")


# ------------------------------------------------------------------
# RIGHT COLUMN — Results
# ------------------------------------------------------------------
with results_col:
    result: PipelineResult | None = st.session_state.result

    if result is None:
        # Empty state
        st.markdown("""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 400px;
            color: #94a3b8;
            text-align: center;
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📋</div>
            <div style="font-size: 1rem; font-weight: 500;">Results will appear here</div>
            <div style="font-size: 0.85rem; margin-top: 0.4rem;">
                Upload a resume and paste a job description to get started.
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # Import and render each component
        from ui.components.profile import render_profile
        from ui.components.scores import render_scores
        from ui.components.tier import render_tier
        from ui.components.questions import render_questions

        render_profile(result.candidate, result.jd)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_scores(result.scoring)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_tier(result.classification)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_questions(result.interview_plan)