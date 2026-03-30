import streamlit as st
from src.models import ScoringResult, DimensionScore
from src.models.enums import ScoreDimension, MatchType


def render_scores(scoring: ScoringResult) -> None:
    """
    Render the scoring section.

    Displays:
    - Overall score prominently
    - 4 dimension scores as cards with progress bars
    - Explanation and evidence per dimension
    - Skill match breakdown table

    Args:
        scoring: ScoringResult from the ScoringEngine.
    """
    st.markdown(
        '<div class="section-header">Scoring Results</div>',
        unsafe_allow_html=True,
    )

    # --- Overall score + strengths/gaps side by side ---
    left, right = st.columns([1, 1.8], gap="medium")

    with left:
        _render_overall_score(scoring)

    with right:
        _render_strengths_gaps(scoring)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 4 Dimension score cards ---
    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin-bottom: 0.75rem;">
        Dimension Breakdown
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        _render_dimension_card(scoring.exact_match, "#3b82f6")
        _render_dimension_card(scoring.achievement, "#10b981")

    with col2:
        _render_dimension_card(scoring.semantic_similarity, "#8b5cf6")
        _render_dimension_card(scoring.ownership, "#f59e0b")

    # --- Skill match breakdown ---
    if scoring.skill_matches:
        _render_skill_matches(scoring)


# ------------------------------------------------------------------
# Private renderers
# ------------------------------------------------------------------

def _render_overall_score(scoring: ScoringResult) -> None:
    """Render the overall score in a prominent dark card."""
    score = scoring.overall_score
    color = _score_color(score)

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0f172a, #1e3a5f);
        border-radius: 12px;
        padding: 1.75rem;
        text-align: center;
        height: 100%;
        min-height: 160px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    ">
        <div style="
            font-size: 3.8rem;
            font-weight: 700;
            font-family: 'IBM Plex Mono', monospace;
            color: {color};
            line-height: 1;
        ">{score:.1f}</div>
        <div style="
            font-size: 0.72rem;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #94a3b8;
            margin-top: 0.5rem;
        ">Overall Score</div>
        <div style="
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 0.3rem;
        ">out of 100</div>
    </div>
    """, unsafe_allow_html=True)


def _render_strengths_gaps(scoring: ScoringResult) -> None:
    """Render strengths and gaps in two compact columns."""
    s_col, g_col = st.columns(2, gap="small")

    with s_col:
        st.markdown("""
        <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                    text-transform: uppercase; color: #166534;
                    margin-bottom: 0.5rem;">
            ✦ Strengths
        </div>
        """, unsafe_allow_html=True)

        if scoring.strengths:
            for strength in scoring.strengths:
                st.markdown(f"""
                <div style="
                    background: #f0fdf4;
                    border: 1px solid #86efac;
                    border-radius: 6px;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.82rem;
                    color: #166534;
                    margin-bottom: 0.4rem;
                    line-height: 1.4;
                ">{strength}</div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="color: #94a3b8; font-size: 0.82rem;">'
                'None identified.</div>',
                unsafe_allow_html=True,
            )

    with g_col:
        st.markdown("""
        <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                    text-transform: uppercase; color: #991b1b;
                    margin-bottom: 0.5rem;">
            ✦ Gaps
        </div>
        """, unsafe_allow_html=True)

        if scoring.gaps:
            for gap in scoring.gaps:
                st.markdown(f"""
                <div style="
                    background: #fef2f2;
                    border: 1px solid #fca5a5;
                    border-radius: 6px;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.82rem;
                    color: #991b1b;
                    margin-bottom: 0.4rem;
                    line-height: 1.4;
                ">{gap}</div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="color: #94a3b8; font-size: 0.82rem;">'
                'None identified.</div>',
                unsafe_allow_html=True,
            )


def _render_dimension_card(
    dim_score: DimensionScore,
    accent_color: str,
) -> None:
    """
    Render a single dimension score card with:
    - Score value + progress bar
    - Explanation
    - Expandable evidence list

    Args:
        dim_score:     DimensionScore from the scorer.
        accent_color:  Hex colour for the progress bar and accent.
    """
    label = _dimension_label(dim_score.dimension)
    score = dim_score.score
    bar_width = int(score)

    st.markdown(f"""
    <div class="score-card">
        <div style="display: flex; justify-content: space-between;
                    align-items: flex-start; margin-bottom: 0.6rem;">
            <div class="score-label">{label}</div>
            <div style="
                font-size: 1.6rem;
                font-weight: 700;
                font-family: 'IBM Plex Mono', monospace;
                color: {accent_color};
                line-height: 1;
            ">{score:.0f}</div>
        </div>

        <!-- Progress bar -->
        <div style="
            background: #f1f5f9;
            border-radius: 999px;
            height: 6px;
            margin-bottom: 0.75rem;
            overflow: hidden;
        ">
            <div style="
                background: {accent_color};
                width: {bar_width}%;
                height: 100%;
                border-radius: 999px;
                transition: width 0.3s ease;
            "></div>
        </div>

        <!-- Explanation -->
        <div style="
            font-size: 0.85rem;
            color: #475569;
            line-height: 1.5;
        ">{dim_score.explanation}</div>
    </div>
    """, unsafe_allow_html=True)

    # Evidence — expandable
    if dim_score.evidence:
        with st.expander(f"View evidence ({len(dim_score.evidence)})", expanded=False):
            for item in dim_score.evidence:
                # Colour code by tag
                if item.startswith("[STRONG]"):
                    bg, fg, border = "#f0fdf4", "#166534", "#86efac"
                elif item.startswith("[MODERATE]"):
                    bg, fg, border = "#fffbeb", "#92400e", "#fcd34d"
                elif item.startswith("[WEAK]"):
                    bg, fg, border = "#fef2f2", "#991b1b", "#fca5a5"
                else:
                    bg, fg, border = "#f8fafc", "#475569", "#e2e8f0"

                st.markdown(f"""
                <div style="
                    background: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                    padding: 0.4rem 0.75rem;
                    font-size: 0.8rem;
                    color: {fg};
                    margin-bottom: 0.3rem;
                    line-height: 1.4;
                    font-family: 'IBM Plex Mono', monospace;
                ">{item}</div>
                """, unsafe_allow_html=True)


def _render_skill_matches(scoring: ScoringResult) -> None:
    """
    Render the skill match breakdown as a styled table.
    Groups by match type with colour coding per row.
    """
    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin: 1.25rem 0 0.75rem 0;">
        Skill Match Breakdown
    </div>
    """, unsafe_allow_html=True)

    # Header row
    st.markdown("""
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 2fr;
                gap: 0.5rem; padding: 0.4rem 0.75rem;
                background: #f8fafc; border-radius: 6px;
                margin-bottom: 0.3rem;">
        <div style="font-size: 0.7rem; font-weight: 600; color: #64748b;
                    text-transform: uppercase; letter-spacing: 0.08em;">JD Skill</div>
        <div style="font-size: 0.7rem; font-weight: 600; color: #64748b;
                    text-transform: uppercase; letter-spacing: 0.08em;">Candidate Skill</div>
        <div style="font-size: 0.7rem; font-weight: 600; color: #64748b;
                    text-transform: uppercase; letter-spacing: 0.08em;">Match Type</div>
        <div style="font-size: 0.7rem; font-weight: 600; color: #64748b;
                    text-transform: uppercase; letter-spacing: 0.08em;">Explanation</div>
    </div>
    """, unsafe_allow_html=True)

    # Sort: exact first, then semantic, partial, none
    order = {
        MatchType.EXACT: 0,
        MatchType.SEMANTIC: 1,
        MatchType.PARTIAL: 2,
        MatchType.NONE: 3,
    }
    sorted_matches = sorted(
        scoring.skill_matches,
        key=lambda m: order.get(m.match_type, 4),
    )

    for match in sorted_matches:
        bg, badge_bg, badge_fg, badge_border = _match_type_colors(match.match_type)
        candidate_skill = match.candidate_skill or "—"
        explanation = match.explanation or "—"
        match_label = match.match_type.value.upper()

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 2fr;
                    gap: 0.5rem; padding: 0.5rem 0.75rem;
                    background: {bg}; border-radius: 6px;
                    margin-bottom: 0.25rem; align-items: start;">
            <div style="font-size: 0.82rem; font-weight: 500;
                        color: #0f172a;">{match.jd_skill}</div>
            <div style="font-size: 0.82rem;
                        color: #334155;">{candidate_skill}</div>
            <div>
                <span style="
                    background: {badge_bg};
                    color: {badge_fg};
                    border: 1px solid {badge_border};
                    padding: 0.15rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    letter-spacing: 0.06em;
                ">{match_label}</span>
            </div>
            <div style="font-size: 0.8rem; color: #64748b;
                        line-height: 1.4;">{explanation}</div>
        </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _dimension_label(dimension: ScoreDimension) -> str:
    """Map ScoreDimension enum to a human-readable label."""
    return {
        ScoreDimension.EXACT_MATCH:         "Exact Match",
        ScoreDimension.SEMANTIC_SIMILARITY:  "Semantic Similarity",
        ScoreDimension.ACHIEVEMENT:          "Achievement Quality",
        ScoreDimension.OWNERSHIP:            "Ownership Signals",
    }.get(dimension, dimension.value.replace("_", " ").title())


def _score_color(score: float) -> str:
    """Return a hex colour based on score value."""
    if score >= 80:
        return "#4ade80"    # Green
    elif score >= 55:
        return "#fbbf24"    # Amber
    else:
        return "#f87171"    # Red


def _match_type_colors(match_type: MatchType) -> tuple[str, str, str, str]:
    """
    Return (row_bg, badge_bg, badge_fg, badge_border)
    for a given MatchType.
    """
    return {
        MatchType.EXACT:    ("#f0fdf4", "#dcfce7", "#166534", "#86efac"),
        MatchType.SEMANTIC: ("#f5f3ff", "#ede9fe", "#5b21b6", "#c4b5fd"),
        MatchType.PARTIAL:  ("#fffbeb", "#fef9c3", "#854d0e", "#fde047"),
        MatchType.NONE:     ("#fef2f2", "#fee2e2", "#991b1b", "#fca5a5"),
    }.get(match_type, ("#f8fafc", "#f1f5f9", "#475569", "#e2e8f0"))