import streamlit as st
from src.models import CandidateProfile, JobDescription
from src.models.enums import SkillLevel


def render_profile(candidate: CandidateProfile, jd: JobDescription) -> None:
    """
    Render the parsed candidate profile section.

    Displays:
    - Candidate identity (name, email, links)
    - Skills with level badges
    - Work experience entries
    - Education
    - AI-generated summary

    Args:
        candidate: Parsed CandidateProfile from the pipeline.
        jd:        Parsed JobDescription (used to highlight matching skills).
    """
    st.markdown('<div class="section-header">Candidate Profile</div>', unsafe_allow_html=True)

    # --- Identity card ---
    _render_identity(candidate)

    # --- Summary ---
    if candidate.summary:
        st.markdown(f"""
        <div class="info-card" style="border-left: 3px solid #3b82f6;">
            <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                        text-transform: uppercase; color: #64748b; margin-bottom: 0.5rem;">
                AI Summary
            </div>
            <div style="color: #334155; line-height: 1.6; font-size: 0.95rem;">
                {candidate.summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Skills ---
    _render_skills(candidate, jd)

    # --- Experience ---
    _render_experience(candidate)

    # --- Education ---
    _render_education(candidate)


# ------------------------------------------------------------------
# Private renderers
# ------------------------------------------------------------------

def _render_identity(candidate: CandidateProfile) -> None:
    """Render name, email, LinkedIn, GitHub, and experience years."""

    # Build links row
    links = []
    if candidate.linkedin_url:
        links.append(f'<a href="{candidate.linkedin_url}" target="_blank" '
                     f'style="color: #3b82f6; text-decoration: none; font-size: 0.85rem;">'
                     f'🔗 LinkedIn</a>')
    if candidate.github_url:
        links.append(f'<a href="{candidate.github_url}" target="_blank" '
                     f'style="color: #3b82f6; text-decoration: none; font-size: 0.85rem;">'
                     f'🐙 GitHub</a>')

    links_html = " &nbsp;·&nbsp; ".join(links) if links else ""

    exp_years = (
        f'<span style="background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; '
        f'padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600;">'
        f'{candidate.total_experience_years:.1f} yrs exp</span>'
        if candidate.total_experience_years
        else ""
    )

    email_html = (
        f'<span style="color: #64748b; font-size: 0.85rem;">✉ {candidate.email}</span>'
        if candidate.email
        else ""
    )

    st.markdown(f"""
    <div class="info-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-size: 1.3rem; font-weight: 600;
                            color: #0f172a; margin-bottom: 0.3rem;">
                    {candidate.full_name}
                </div>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
                    {email_html}
                    {links_html}
                </div>
            </div>
            <div>{exp_years}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_skills(candidate: CandidateProfile, jd: JobDescription) -> None:
    """
    Render skills as colour-coded pills.
    Skills that match JD requirements are highlighted in blue.
    Others are shown in grey.
    """
    if not candidate.skills:
        return

    # Build set of JD skill names for highlighting
    jd_skill_names = {
        s.name.lower().strip()
        for s in (jd.required_skills + jd.preferred_skills)
    }

    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin: 1rem 0 0.5rem 0;">
        Skills
    </div>
    """, unsafe_allow_html=True)

    pills_html = ""
    for skill in candidate.skills:
        is_match = skill.name.lower().strip() in jd_skill_names
        level_badge = _skill_level_badge(skill.level)

        if is_match:
            pills_html += (
                f'<span style="display: inline-flex; align-items: center; gap: 0.3rem; '
                f'background: #eff6ff; color: #1e40af; border: 1px solid #93c5fd; '
                f'padding: 0.25rem 0.75rem; border-radius: 999px; '
                f'font-size: 0.8rem; font-weight: 500; margin: 0.2rem;">'
                f'{skill.name}{level_badge}</span>'
            )
        else:
            pills_html += (
                f'<span style="display: inline-flex; align-items: center; gap: 0.3rem; '
                f'background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; '
                f'padding: 0.25rem 0.75rem; border-radius: 999px; '
                f'font-size: 0.8rem; font-weight: 500; margin: 0.2rem;">'
                f'{skill.name}{level_badge}</span>'
            )

    st.markdown(
        f'<div style="line-height: 2.2;">{pills_html}</div>',
        unsafe_allow_html=True,
    )

    # Legend
    st.markdown("""
    <div style="margin-top: 0.5rem; font-size: 0.72rem; color: #94a3b8;">
        <span style="color: #1e40af;">■</span> Matches JD requirement &nbsp;
        <span style="color: #94a3b8;">■</span> Other skills
    </div>
    """, unsafe_allow_html=True)


def _render_experience(candidate: CandidateProfile) -> None:
    """Render work experience as expandable entries."""
    if not candidate.experience:
        return

    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin: 1rem 0 0.5rem 0;">
        Experience
    </div>
    """, unsafe_allow_html=True)

    for exp in candidate.experience:
        duration_str = (
            f"{exp.duration_months} months"
            if exp.duration_months
            else "Duration unknown"
        )

        with st.expander(f"**{exp.role}** — {exp.company}  ·  {duration_str}"):

            if exp.description:
                st.markdown(
                    f'<div style="color: #475569; font-size: 0.9rem; '
                    f'line-height: 1.6; margin-bottom: 0.75rem;">'
                    f'{exp.description}</div>',
                    unsafe_allow_html=True,
                )

            if exp.achievements:
                st.markdown(
                    '<div style="font-size: 0.72rem; font-weight: 600; '
                    'letter-spacing: 0.1em; text-transform: uppercase; '
                    'color: #64748b; margin-bottom: 0.4rem;">Achievements</div>',
                    unsafe_allow_html=True,
                )
                for ach in exp.achievements:
                    st.markdown(
                        f'<div style="color: #166534; font-size: 0.88rem; '
                        f'padding: 0.25rem 0; padding-left: 1rem; '
                        f'border-left: 2px solid #86efac; margin-bottom: 0.3rem;">'
                        f'✦ {ach}</div>',
                        unsafe_allow_html=True,
                    )

            if exp.keywords:
                keywords_html = " ".join(
                    f'<span style="background: #f1f5f9; color: #475569; '
                    f'border: 1px solid #e2e8f0; padding: 0.15rem 0.5rem; '
                    f'border-radius: 4px; font-size: 0.75rem; '
                    f'font-family: monospace;">{kw}</span>'
                    for kw in exp.keywords
                )
                st.markdown(
                    f'<div style="margin-top: 0.5rem;">{keywords_html}</div>',
                    unsafe_allow_html=True,
                )


def _render_education(candidate: CandidateProfile) -> None:
    """Render education entries compactly."""
    if not candidate.education:
        return

    st.markdown("""
    <div style="font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
                text-transform: uppercase; color: #64748b;
                margin: 1rem 0 0.5rem 0;">
        Education
    </div>
    """, unsafe_allow_html=True)

    for edu in candidate.education:
        degree_str = " ".join(filter(None, [edu.degree, edu.field]))
        year_str = str(edu.year) if edu.year else ""

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between;
                    align-items: center; padding: 0.6rem 0;
                    border-bottom: 1px solid #f1f5f9;">
            <div>
                <span style="font-weight: 500; color: #0f172a;
                             font-size: 0.9rem;">{edu.institution}</span>
                {f'<span style="color: #64748b; font-size: 0.85rem;"> · {degree_str}</span>'
                 if degree_str else ''}
            </div>
            <span style="color: #94a3b8; font-size: 0.82rem;">{year_str}</span>
        </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _skill_level_badge(level: SkillLevel) -> str:
    """Return a small inline HTML badge for a skill level."""
    badges = {
        SkillLevel.ADVANCED:     '<span style="font-size: 0.65rem; '
                                 'background: #dcfce7; color: #166534; '
                                 'padding: 0.1rem 0.35rem; border-radius: 3px; '
                                 'margin-left: 0.2rem;">adv</span>',
        SkillLevel.INTERMEDIATE: '<span style="font-size: 0.65rem; '
                                 'background: #fef9c3; color: #854d0e; '
                                 'padding: 0.1rem 0.35rem; border-radius: 3px; '
                                 'margin-left: 0.2rem;">mid</span>',
        SkillLevel.BEGINNER:     '<span style="font-size: 0.65rem; '
                                 'background: #fee2e2; color: #991b1b; '
                                 'padding: 0.1rem 0.35rem; border-radius: 3px; '
                                 'margin-left: 0.2rem;">jun</span>',
        SkillLevel.UNKNOWN:      '',
    }
    return badges.get(level, "")