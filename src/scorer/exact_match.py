from src.models import CandidateProfile, JobDescription, DimensionScore, SkillMatchDetail
from src.models.enums import ScoreDimension, MatchType


class ExactMatchScorer:
    """
    Scores the candidate based on literal keyword overlap
    between their skills and the JD requirements.

    No LLM involved — pure Python set operations.
    Fast, deterministic, and fully explainable.
    """

    def score(
        self,
        candidate: CandidateProfile,
        jd: JobDescription,
    ) -> tuple[DimensionScore, list[SkillMatchDetail]]:
        """
        Compute the exact match score.

        Mandatory skills carry more weight than preferred skills.
        Each matched mandatory skill contributes more to the score
        than a matched preferred skill.

        Args:
            candidate: Parsed candidate profile.
            jd:        Parsed job description.

        Returns:
            Tuple of:
                - DimensionScore with score + explanation + evidence
                - list[SkillMatchDetail] one entry per JD skill
        """
        candidate_skill_names = self._extract_candidate_skills(candidate)

        mandatory_skills = [s for s in jd.required_skills if s.is_mandatory]
        preferred_skills = [s for s in jd.preferred_skills if not s.is_mandatory]

        mandatory_matches, mandatory_details = self._match_skills(
            jd_skills=mandatory_skills,
            candidate_skills=candidate_skill_names,
        )
        preferred_matches, preferred_details = self._match_skills(
            jd_skills=preferred_skills,
            candidate_skills=candidate_skill_names,
        )

        score = self._compute_score(
            mandatory_skills=mandatory_skills,
            mandatory_matches=mandatory_matches,
            preferred_skills=preferred_skills,
            preferred_matches=preferred_matches,
        )

        all_details = mandatory_details + preferred_details
        explanation = self._build_explanation(
            mandatory_skills=mandatory_skills,
            mandatory_matches=mandatory_matches,
            preferred_skills=preferred_skills,
            preferred_matches=preferred_matches,
        )
        evidence = self._build_evidence(mandatory_details, preferred_details)

        dimension_score = DimensionScore(
            dimension=ScoreDimension.EXACT_MATCH,
            score=round(score, 2),
            explanation=explanation,
            evidence=evidence,
        )

        return dimension_score, all_details

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_candidate_skills(candidate: CandidateProfile) -> set[str]:
        """
        Build a normalised set of all skill names from the candidate profile.
        Includes both top-level skills and per-experience keywords.

        Normalisation: lowercase + strip whitespace.
        This handles "Python" == "python" == " Python ".
        """
        skills = set()

        # Top-level skills list
        for skill in candidate.skills:
            if skill.name:
                skills.add(skill.name.lower().strip())

        # Per-experience keywords
        for exp in candidate.experience:
            for keyword in exp.keywords:
                if keyword:
                    skills.add(keyword.lower().strip())

        return skills

    @staticmethod
    def _normalize(skill_name: str) -> str:
        """Lowercase and strip a skill name for comparison."""
        return skill_name.lower().strip()

    def _match_skills(
        self,
        jd_skills: list,
        candidate_skills: set[str],
    ) -> tuple[list, list[SkillMatchDetail]]:
        """
        Match a list of JD skills against candidate skills.
        Returns matched skills and SkillMatchDetail records.

        A match is considered exact if the normalised JD skill name
        is present in the normalised candidate skill set.

        Args:
            jd_skills:        List of RequiredSkill from JD.
            candidate_skills: Normalised set of candidate skill names.

        Returns:
            Tuple of:
                - List of matched RequiredSkill objects
                - List of SkillMatchDetail for all skills
        """
        matched = []
        details = []

        for jd_skill in jd_skills:
            normalized_jd = self._normalize(jd_skill.name)
            is_matched = normalized_jd in candidate_skills

            if is_matched:
                matched.append(jd_skill)
                details.append(SkillMatchDetail(
                    jd_skill=jd_skill.name,
                    candidate_skill=jd_skill.name,        # Same name — exact match
                    match_type=MatchType.EXACT,
                    explanation=f"'{jd_skill.name}' found directly in candidate's skill set.",
                ))
            else:
                details.append(SkillMatchDetail(
                    jd_skill=jd_skill.name,
                    candidate_skill=None,
                    match_type=MatchType.NONE,
                    explanation=f"'{jd_skill.name}' not found in candidate's skill set.",
                ))

        return matched, details

    @staticmethod
    def _compute_score(
        mandatory_skills: list,
        mandatory_matches: list,
        preferred_skills: list,
        preferred_matches: list,
    ) -> float:
        """
        Compute weighted exact match score.

        Weighting:
            - Mandatory skills account for 80% of the score
            - Preferred skills account for 20% of the score

        If no mandatory skills exist in the JD, the full score
        is based on preferred skills alone.

        Args:
            mandatory_skills:  All mandatory JD skills.
            mandatory_matches: Mandatory skills matched exactly.
            preferred_skills:  All preferred JD skills.
            preferred_matches: Preferred skills matched exactly.

        Returns:
            Float score between 0.0 and 100.0.
        """
        mandatory_score = 0.0
        preferred_score = 0.0

        if mandatory_skills:
            mandatory_score = (
                len(mandatory_matches) / len(mandatory_skills)
            ) * 100

        if preferred_skills:
            preferred_score = (
                len(preferred_matches) / len(preferred_skills)
            ) * 100

        # If JD has both mandatory and preferred skills
        if mandatory_skills and preferred_skills:
            return (mandatory_score * 0.80) + (preferred_score * 0.20)

        # If only mandatory skills
        if mandatory_skills:
            return mandatory_score

        # If only preferred skills (unusual but handled)
        return preferred_score

    @staticmethod
    def _build_explanation(
        mandatory_skills: list,
        mandatory_matches: list,
        preferred_skills: list,
        preferred_matches: list,
    ) -> str:
        """
        Build a human-readable explanation of the exact match score.
        """
        parts = []

        if mandatory_skills:
            parts.append(
                f"Matched {len(mandatory_matches)}/{len(mandatory_skills)} "
                f"mandatory skills."
            )

        if preferred_skills:
            parts.append(
                f"Matched {len(preferred_matches)}/{len(preferred_skills)} "
                f"preferred skills."
            )

        if not mandatory_skills and not preferred_skills:
            return "No skills found in the job description to match against."

        missed_mandatory = [
            s.name for s in mandatory_skills
            if s not in mandatory_matches
        ]
        if missed_mandatory:
            parts.append(
                f"Missing mandatory skills: {', '.join(missed_mandatory)}."
            )

        return " ".join(parts)

    @staticmethod
    def _build_evidence(
        mandatory_details: list[SkillMatchDetail],
        preferred_details: list[SkillMatchDetail],
    ) -> list[str]:
        """
        Build evidence list from matched skill details.
        Only includes matched skills as positive evidence.
        """
        evidence = []

        for detail in mandatory_details + preferred_details:
            if detail.match_type == MatchType.EXACT:
                evidence.append(
                    f"[Mandatory] {detail.jd_skill} — exact match found."
                    if detail in mandatory_details
                    else f"[Preferred] {detail.jd_skill} — exact match found."
                )

        return evidence


# Singleton
exact_match_scorer = ExactMatchScorer()