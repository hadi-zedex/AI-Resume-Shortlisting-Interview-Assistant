import streamlit as st
from ui.utils import st_html
from src.models import TierClassification
from src.models.enums import Tier


def render_tier(classification: TierClassification) -> None:
    """
    Render the tier classification section.

    Displays:
    - Tier badge with colour coding
    - Overall score
    - Decision label and recommended action
    - Reasoning paragraph
    - Focus areas for the interviewer

    Args:
        classification: TierClassification from the TierClassifier.
    """
    st_html(
        '<div class="section-header">Tier Classification</div>',
    )

    # --- Top row: tier badge + decision ---
    _render_tier_header(classification)

    st_html("<br>")

    # --- Two columns: reasoning | focus areas ---
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        _render_reasoning(classification)

    with right:
        _render_focus_areas(classification)


# ------------------------------------------------------------------
# Private renderers
# ------------------------------------------------------------------

def _render_tier_header(classification: TierClassification) -> None:
    """
    Render the prominent tier badge row with score,
    decision label, and recommended action.
    """
    tier = classification.tier
    colors = _tier_colors(tier)

    st_html(f"""
    <div style="
        background: {colors['bg']};
        border: 1px solid {colors['border']};
        border-radius: 12px;
        padding: 1.5rem 2rem;
        display: flex;
        align-items: center;
        gap: 2rem;
        flex-wrap: wrap;
    ">
        <!-- Tier badge -->
        <div style="
            background: {colors['badge_bg']};
            border: 2px solid {colors['badge_border']};
            border-radius: 12px;
            width: 72px;
            height: 72px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        ">
            <div style="
                font-size: 0.6rem;
                font-weight: 700;
                letter-spacing: 0.15em;
                text-transform: uppercase;
                color: {colors['text_muted']};
            ">TIER</div>
            <div style="
                font-size: 2rem;
                font-weight: 800;
                font-family: 'IBM Plex Mono', monospace;
                color: {colors['text']};
                line-height: 1;
            ">{tier.value}</div>
        </div>

        <!-- Decision info -->
        <div style="flex: 1; min-width: 200px;">
            <div style="
                font-size: 1.15rem;
                font-weight: 600;
                color: {colors['text']};
                margin-bottom: 0.3rem;
            ">{classification.decision_label}</div>
            <div style="
                font-size: 0.85rem;
                color: {colors['text_muted']};
                margin-bottom: 0.5rem;
            ">{classification.recommended_action}</div>
            <div style="
                display: inline-block;
                background: {colors['badge_bg']};
                border: 1px solid {colors['badge_border']};
                color: {colors['text']};
                font-family: 'IBM Plex Mono', monospace;
                font-size: 0.85rem;
                font-weight: 600;
                padding: 0.25rem 0.75rem;
                border-radius: 999px;
            ">Score: {classification.overall_score:.1f} / 100</div>
        </div>

        <!-- Threshold info -->
        <div style="
            text-align: right;
            font-size: 0.75rem;
            color: {colors['text_muted']};
            min-width: 120px;
        ">
            <div style="margin-bottom: 0.2rem;">
                Tier A ≥ {classification.thresholds_used.tier_a_min:.0f}
            </div>
            <div style="margin-bottom: 0.2rem;">
                Tier B ≥ {classification.thresholds_used.tier_b_min:.0f}
            </div>
            <div>
                Tier C &lt; {classification.thresholds_used.tier_b_min:.0f}
            </div>
        </div>
    </div>
    """)


def _render_reasoning(classification: TierClassification) -> None:
    """Render the classifier's reasoning paragraph."""
    st_html("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin-bottom: 0.6rem;">
        Reasoning
    </div>
    """)

    st_html(f"""
    <div style="
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        font-size: 0.9rem;
        color: #334155;
        line-height: 1.7;
    ">{classification.reasoning}</div>
    """)

    # --- Dimension score mini summary ---
    st_html("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin: 1rem 0 0.6rem 0;">
        Score Breakdown
    </div>
    """)

    scoring = classification.scoring_result
    dimensions = [
        ("Exact Match",        scoring.exact_match.score,        "#3b82f6"),
        ("Semantic",           scoring.semantic_similarity.score, "#8b5cf6"),
        ("Achievement",        scoring.achievement.score,         "#10b981"),
        ("Ownership",          scoring.ownership.score,           "#f59e0b"),
    ]

    for label, score, color in dimensions:
        bar_width = int(score)
        st_html(f"""
        <div style="margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between;
                        align-items: center; margin-bottom: 0.2rem;">
                <span style="font-size: 0.8rem; color: #475569;">{label}</span>
                <span style="font-size: 0.8rem; font-weight: 600;
                             font-family: 'IBM Plex Mono', monospace;
                             color: {color};">{score:.0f}</span>
            </div>
            <div style="background: #f1f5f9; border-radius: 999px;
                        height: 5px; overflow: hidden;">
                <div style="background: {color}; width: {bar_width}%;
                            height: 100%; border-radius: 999px;"></div>
            </div>
        </div>
        """)


def _render_focus_areas(classification: TierClassification) -> None:
    """
    Render the interviewer focus areas as a numbered checklist.
    Each item is colour-coded based on its content type.
    """
    st_html("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin-bottom: 0.6rem;">
        Interviewer Focus Areas
    </div>
    """)

    if not classification.focus_areas:
        st_html(
            '<div style="color: #94a3b8; font-size: 0.85rem;">'
            'No specific focus areas identified.</div>',
        )
        return

    for i, area in enumerate(classification.focus_areas, start=1):
        # Detect type of focus area for colour coding
        bg, border, icon = _focus_area_style(area)

        st_html(f"""
        <div style="
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 0.65rem 1rem;
            margin-bottom: 0.4rem;
            display: flex;
            gap: 0.75rem;
            align-items: flex-start;
        ">
            <span style="
                font-size: 0.7rem;
                font-weight: 700;
                font-family: 'IBM Plex Mono', monospace;
                color: #94a3b8;
                padding-top: 0.1rem;
                flex-shrink: 0;
            ">{i:02d}</span>
            <span style="font-size: 0.85rem; color: #334155;
                         line-height: 1.5;">{icon} {area}</span>
        </div>
        """)

    # Thresholds footnote
    st_html(f"""
    <div style="
        margin-top: 1rem;
        font-size: 0.72rem;
        color: #94a3b8;
        padding: 0.5rem 0.75rem;
        background: #f8fafc;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
    ">
        Thresholds used — A: ≥{classification.thresholds_used.tier_a_min:.0f} &nbsp;|&nbsp;
        B: ≥{classification.thresholds_used.tier_b_min:.0f} &nbsp;|&nbsp;
        C: &lt;{classification.thresholds_used.tier_b_min:.0f}
    </div>
    """)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _tier_colors(tier: Tier) -> dict[str, str]:
    """
    Return a colour palette dict for a given tier.
    Used to theme the entire tier header card.
    """
    palettes = {
        Tier.A: {
            "bg":           "#f0fdf4",
            "border":       "#86efac",
            "badge_bg":     "#dcfce7",
            "badge_border": "#4ade80",
            "text":         "#166534",
            "text_muted":   "#16a34a",
        },
        Tier.B: {
            "bg":           "#fffbeb",
            "border":       "#fde047",
            "badge_bg":     "#fef9c3",
            "badge_border": "#fbbf24",
            "text":         "#854d0e",
            "text_muted":   "#b45309",
        },
        Tier.C: {
            "bg":           "#fef2f2",
            "border":       "#fca5a5",
            "badge_bg":     "#fee2e2",
            "badge_border": "#f87171",
            "text":         "#991b1b",
            "text_muted":   "#dc2626",
        },
    }
    return palettes[tier]


def _focus_area_style(area: str) -> tuple[str, str, str]:
    """
    Return (bg, border, icon) for a focus area string
    based on keyword detection.
    """
    area_lower = area.lower()

    if any(w in area_lower for w in ["verify", "claimed", "confirm"]):
        return "#fffbeb", "#fde047", "🔍"

    if any(w in area_lower for w in ["probe", "depth", "assess"]):
        return "#f5f3ff", "#c4b5fd", "🎯"

    if any(w in area_lower for w in ["missing", "gap", "lacks", "absent"]):
        return "#fef2f2", "#fca5a5", "⚠️"

    if any(w in area_lower for w in ["ownership", "leadership", "decision"]):
        return "#eff6ff", "#bfdbfe", "🏛️"

    if any(w in area_lower for w in ["system design", "architecture", "design"]):
        return "#f0fdf4", "#86efac", "🏗️"

    if any(w in area_lower for w in ["culture", "team", "fit"]):
        return "#fdf4ff", "#e9d5ff", "🤝"

    if any(w in area_lower for w in ["screen", "assessment", "take-home"]):
        return "#f8fafc", "#e2e8f0", "📋"

    # Default
    return "#f8fafc", "#e2e8f0", "→"