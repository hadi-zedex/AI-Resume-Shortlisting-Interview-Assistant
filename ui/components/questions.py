import streamlit as st
from ui.utils import st_html
from src.models import InterviewPlan, InterviewQuestion
from src.models.enums import Tier


def render_questions(plan: InterviewPlan) -> None:
    """
    Render the interview plan section.

    Displays:
    - Interviewer briefing
    - Recommended duration + tier
    - 5–8 tailored questions with rationale, difficulty, and follow-ups
    - Red flags and green flags

    Args:
        plan: InterviewPlan from the QuestionGenerator.
    """
    st_html(
        '<div class="section-header">Interview Plan</div>',
    )

    # --- Briefing card ---
    _render_briefing(plan)

    st_html("<br>")

    # --- Questions ---
    st_html("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin-bottom: 0.75rem;">
        Questions
    </div>
    """)

    for i, question in enumerate(plan.questions, start=1):
        _render_question_card(question, i)

    st_html("<br>")

    # --- Red flags + green flags ---
    left, right = st.columns(2, gap="medium")

    with left:
        _render_flags(
            flags=plan.red_flags,
            label="Red Flags",
            bg="#fef2f2",
            border="#fca5a5",
            text="#991b1b",
            icon="🚩",
        )

    with right:
        _render_flags(
            flags=plan.green_flags,
            label="Green Flags",
            bg="#f0fdf4",
            border="#86efac",
            text="#166534",
            icon="✅",
        )


# ------------------------------------------------------------------
# Private renderers
# ------------------------------------------------------------------

def _render_briefing(plan: InterviewPlan) -> None:
    """
    Render the interviewer briefing card.
    Includes tier badge, duration, and the briefing text.
    """
    tier_colors = _tier_badge_colors(plan.tier)
    duration = plan.recommended_duration_minutes

    st_html(f"""
    <div style="
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        border-left: 4px solid {tier_colors['accent']};
    ">
        <!-- Header row -->
        <div style="display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 1rem;
                    flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.72rem; font-weight: 600;
                        letter-spacing: 0.15em; text-transform: uppercase;
                        color: #94a3b8;">
                Interviewer Briefing
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
                <!-- Tier pill -->
                <span style="
                    background: {tier_colors['bg']};
                    color: {tier_colors['text']};
                    border: 1px solid {tier_colors['border']};
                    padding: 0.2rem 0.75rem;
                    border-radius: 999px;
                    font-size: 0.75rem;
                    font-weight: 700;
                    font-family: 'IBM Plex Mono', monospace;
                ">Tier {plan.tier.value}</span>
                <!-- Duration pill -->
                <span style="
                    background: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    padding: 0.2rem 0.75rem;
                    border-radius: 999px;
                    font-size: 0.75rem;
                    font-weight: 500;
                ">⏱ {duration} min</span>
            </div>
        </div>

        <!-- Briefing text -->
        <div style="
            font-size: 0.95rem;
            color: #e2e8f0;
            line-height: 1.7;
            font-style: italic;
        ">{plan.interviewer_briefing}</div>

        <!-- Candidate + role -->
        <div style="
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #1e293b;
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        ">
            <div>
                <span style="font-size: 0.7rem; color: #64748b;
                             text-transform: uppercase; letter-spacing: 0.1em;">
                    Candidate
                </span>
                <div style="font-size: 0.9rem; color: #f1f5f9;
                            font-weight: 500; margin-top: 0.1rem;">
                    {plan.candidate_name}
                </div>
            </div>
            <div>
                <span style="font-size: 0.7rem; color: #64748b;
                             text-transform: uppercase; letter-spacing: 0.1em;">
                    Role
                </span>
                <div style="font-size: 0.9rem; color: #f1f5f9;
                            font-weight: 500; margin-top: 0.1rem;">
                    {plan.jd_title}
                </div>
            </div>
            <div>
                <span style="font-size: 0.7rem; color: #64748b;
                             text-transform: uppercase; letter-spacing: 0.1em;">
                    Questions
                </span>
                <div style="font-size: 0.9rem; color: #f1f5f9;
                            font-weight: 500; margin-top: 0.1rem;">
                    {len(plan.questions)}
                </div>
            </div>
        </div>
    </div>
    """)


def _render_question_card(question: InterviewQuestion, index: int) -> None:
    """
    Render a single interview question card.

    Shows:
    - Question number + dimension tag + difficulty tag
    - The question text
    - Rationale (always visible)
    - Follow-up (expandable if present)

    Args:
        question: InterviewQuestion instance.
        index:    1-based question number.
    """
    dim_style = _dimension_style(question.dimension)
    diff_style = _difficulty_style(question.difficulty)
    accent = dim_style["accent"]

    st_html(f"""
    <div style="
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 3px solid {accent};
        border-radius: 0 10px 10px 0;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.75rem;
    ">
        <!-- Header row: number + tags -->
        <div style="display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 0.75rem;
                    flex-wrap: wrap; gap: 0.4rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <!-- Question number -->
                <span style="
                    font-size: 0.72rem;
                    font-weight: 700;
                    font-family: 'IBM Plex Mono', monospace;
                    color: #94a3b8;
                ">Q{index:02d}</span>

                <!-- Dimension tag -->
                <span style="
                    background: {dim_style['bg']};
                    color: {dim_style['text']};
                    border: 1px solid {dim_style['border']};
                    padding: 0.15rem 0.6rem;
                    border-radius: 4px;
                    font-size: 0.68rem;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                ">{dim_style['label']}</span>
            </div>

            <!-- Difficulty tag -->
            <span style="
                background: {diff_style['bg']};
                color: {diff_style['text']};
                border: 1px solid {diff_style['border']};
                padding: 0.15rem 0.6rem;
                border-radius: 4px;
                font-size: 0.68rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            ">{question.difficulty.upper()}</span>
        </div>

        <!-- Question text -->
        <div style="
            font-size: 0.97rem;
            font-weight: 500;
            color: #0f172a;
            line-height: 1.55;
            margin-bottom: 0.75rem;
        ">{question.question}</div>

        <!-- Rationale -->
        <div style="
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 0.6rem 0.9rem;
            font-size: 0.82rem;
            color: #475569;
            line-height: 1.5;
        ">
            <span style="font-weight: 600; color: #64748b;">Why: </span>
            {question.rationale}
        </div>
    </div>
    """)

    # Follow-up — shown as expandable below the card
    if question.follow_up:
        with st.expander(f"↳  Follow-up for Q{index:02d}", expanded=False):
            st_html(f"""
            <div style="
                background: #f5f3ff;
                border: 1px solid #c4b5fd;
                border-radius: 8px;
                padding: 0.75rem 1rem;
                font-size: 0.88rem;
                color: #4c1d95;
                line-height: 1.55;
            ">
                <span style="font-weight: 600;">Follow-up: </span>
                {question.follow_up}
            </div>
            """)


def _render_flags(
    flags: list[str],
    label: str,
    bg: str,
    border: str,
    text: str,
    icon: str,
) -> None:
    """
    Render a list of red or green flags.

    Args:
        flags:  List of flag strings.
        label:  Section label e.g. "Red Flags".
        bg:     Background colour for flag cards.
        border: Border colour for flag cards.
        text:   Text colour for flag cards.
        icon:   Emoji icon prefix.
    """
    st_html(f"""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin-bottom: 0.6rem;">
        {icon} {label}
    </div>
    """)

    if not flags:
        st_html(
            '<div style="color: #94a3b8; font-size: 0.85rem;">'
            'None identified.</div>',
        )
        return

    for flag in flags:
        st_html(f"""
        <div style="
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            font-size: 0.85rem;
            color: {text};
            line-height: 1.5;
            margin-bottom: 0.4rem;
        ">{flag}</div>
        """)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _tier_badge_colors(tier: Tier) -> dict[str, str]:
    """Return colour tokens for a tier badge on a dark background."""
    return {
        Tier.A: {
            "accent": "#4ade80",
            "bg":     "#dcfce7",
            "text":   "#166534",
            "border": "#86efac",
        },
        Tier.B: {
            "accent": "#fbbf24",
            "bg":     "#fef9c3",
            "text":   "#854d0e",
            "border": "#fde047",
        },
        Tier.C: {
            "accent": "#f87171",
            "bg":     "#fee2e2",
            "text":   "#991b1b",
            "border": "#fca5a5",
        },
    }[tier]


def _dimension_style(dimension: str) -> dict[str, str]:
    """Return style tokens for a question dimension tag."""
    styles = {
        "technical_depth": {
            "label":  "Technical Depth",
            "bg":     "#dbeafe",
            "text":   "#1e40af",
            "border": "#93c5fd",
            "accent": "#3b82f6",
        },
        "skill_gap": {
            "label":  "Skill Gap",
            "bg":     "#fee2e2",
            "text":   "#991b1b",
            "border": "#fca5a5",
            "accent": "#ef4444",
        },
        "ownership": {
            "label":  "Ownership",
            "bg":     "#ede9fe",
            "text":   "#5b21b6",
            "border": "#c4b5fd",
            "accent": "#8b5cf6",
        },
        "achievement": {
            "label":  "Achievement",
            "bg":     "#dcfce7",
            "text":   "#166534",
            "border": "#86efac",
            "accent": "#10b981",
        },
    }
    return styles.get(dimension, {
        "label":  dimension.replace("_", " ").title(),
        "bg":     "#f1f5f9",
        "text":   "#475569",
        "border": "#e2e8f0",
        "accent": "#94a3b8",
    })


def _difficulty_style(difficulty: str) -> dict[str, str]:
    """Return style tokens for a difficulty tag."""
    styles = {
        "easy": {
            "bg":     "#f0fdf4",
            "text":   "#15803d",
            "border": "#86efac",
        },
        "medium": {
            "bg":     "#fffbeb",
            "text":   "#b45309",
            "border": "#fcd34d",
        },
        "hard": {
            "bg":     "#fef2f2",
            "text":   "#b91c1c",
            "border": "#fca5a5",
        },
    }
    return styles.get(difficulty.lower(), {
        "bg":     "#f1f5f9",
        "text":   "#475569",
        "border": "#e2e8f0",
    })