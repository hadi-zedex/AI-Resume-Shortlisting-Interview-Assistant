from src.models import CandidateProfile, JobDescription, DimensionScore, SkillMatchDetail
from src.models.enums import ScoreDimension, MatchType
from src.llm.client import llm_client
from src.llm.prompts.semantic_similarity import (
    SEMANTIC_SIMILARITY_SYSTEM,
    build_semantic_similarity_prompt,
)


class SemanticSimilarityScorer:
    """
    Scores the candidate based on functional equivalence between
    their skills and the JD requirements.

    Handles cases where the candidate has a different but interchangeable
    technology (e.g. RabbitMQ instead of Kafka, GCP instead of AWS).

    Uses Claude to reason about technology equivalence.
    Only evaluates skills that were NOT already matched by ExactMatchScorer
    to avoid double-counting.
    """

    def score(
        self,
        candidate: CandidateProfile,
        jd: JobDescription,
        exact_match_details: list[SkillMatchDetail] | None = None,
    ) -> tuple[DimensionScore, list[SkillMatchDetail]]:
        """
        Compute the semantic similarity score.

        Args:
            candidate:            Parsed candidate profile.
            jd:                   Parsed job description.
            exact_match_details:  SkillMatchDetail list from ExactMatchScorer.
                                  Used to skip already-matched skills.

        Returns:
            Tuple of:
                - DimensionScore with score + explanation + evidence
                - list[SkillMatchDetail] for unmatched JD skills
        """
        # Collect all JD skills
        all_jd_skills = jd.required_skills + jd.preferred_skills

        # Skip skills already exactly matched
        unmatched_jd_skills = self._filter_unmatched(
            all_jd_skills, exact_match_details
        )

        # If everything was already matched exactly, semantic score is perfect
        if not unmatched_jd_skills:
            return self._perfect_score(), []

        # Collect candidate skill names
        candidate_skill_names = self._extract_candidate_skills(candidate)

        # If candidate has no skills at all
        if not candidate_skill_names:
            return self._zero_score("No skills found in candidate profile."), []

        # Build and send prompt
        jd_skill_names = [s.name for s in unmatched_jd_skills]
        prompt = build_semantic_similarity_prompt(
            jd_skills=jd_skill_names,
            candidate_skills=list(candidate_skill_names),
            domain=jd.domain,
        )

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=SEMANTIC_SIMILARITY_SYSTEM,
        )

        return self._parse_response(raw_json, unmatched_jd_skills)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_unmatched(
        jd_skills: list,
        exact_match_details: list[SkillMatchDetail] | None,
    ) -> list:
        """
        Remove JD skills that were already matched exactly.
        Prevents double-counting a skill in both exact and semantic scores.

        Args:
            jd_skills:            All JD skills (required + preferred).
            exact_match_details:  Results from ExactMatchScorer.

        Returns:
            List of JD skills that still need semantic evaluation.
        """
        if not exact_match_details:
            return jd_skills

        exactly_matched_names = {
            detail.jd_skill.lower().strip()
            for detail in exact_match_details
            if detail.match_type == MatchType.EXACT
        }

        return [
            skill for skill in jd_skills
            if skill.name.lower().strip() not in exactly_matched_names
        ]

    @staticmethod
    def _extract_candidate_skills(candidate: CandidateProfile) -> set[str]:
        """
        Build a set of all candidate skill names including
        top-level skills and per-experience keywords.
        """
        skills = set()

        for skill in candidate.skills:
            if skill.name:
                skills.add(skill.name.strip())

        for exp in candidate.experience:
            for keyword in exp.keywords:
                if keyword:
                    skills.add(keyword.strip())

        return skills

    def _parse_response(
        self,
        raw_json: dict,
        unmatched_jd_skills: list,
    ) -> tuple[DimensionScore, list[SkillMatchDetail]]:
        """
        Parse Claude's response into a DimensionScore and SkillMatchDetail list.

        Args:
            raw_json:             Parsed dict from Claude's JSON response.
            unmatched_jd_skills:  The JD skills that were evaluated.

        Returns:
            Tuple of DimensionScore and list[SkillMatchDetail].
        """
        matches_data = raw_json.get("matches", [])
        overall_summary = raw_json.get("overall_summary", "")

        skill_details = []
        per_skill_scores = []
        evidence = []

        mandatory_names = {
            s.name.lower().strip()
            for s in unmatched_jd_skills
            if s.is_mandatory
        }

        for match in matches_data:
            if not isinstance(match, dict):
                continue

            jd_skill = match.get("jd_skill", "")
            candidate_skill = match.get("candidate_skill")
            match_type_raw = match.get("match_type", "none")
            skill_score = match.get("score_0_to_100", 0)
            explanation = match.get("explanation", "")

            # Map Claude's string to MatchType enum safely
            match_type = self._parse_match_type(match_type_raw)

            skill_details.append(SkillMatchDetail(
                jd_skill=jd_skill,
                candidate_skill=candidate_skill,
                match_type=match_type,
                explanation=explanation,
            ))

            # Mandatory skills carry more weight in the average
            is_mandatory = jd_skill.lower().strip() in mandatory_names
            weight = 1.5 if is_mandatory else 1.0
            per_skill_scores.append((skill_score * weight, weight))

            # Collect evidence for non-zero matches
            if skill_score > 0 and candidate_skill:
                evidence.append(
                    f"{jd_skill} → {candidate_skill} "
                    f"({match_type.value}): {explanation}"
                )

        # Weighted average across all evaluated skills
        overall_score = self._weighted_average(per_skill_scores)

        dimension_score = DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=round(overall_score, 2),
            explanation=overall_summary or self._fallback_explanation(skill_details),
            evidence=evidence,
        )

        return dimension_score, skill_details

    @staticmethod
    def _parse_match_type(raw: str) -> MatchType:
        """
        Safely parse Claude's match_type string into a MatchType enum.
        Defaults to NONE if unrecognised.
        """
        mapping = {
            "exact": MatchType.EXACT,
            "semantic": MatchType.SEMANTIC,
            "partial": MatchType.PARTIAL,
            "none": MatchType.NONE,
        }
        return mapping.get(raw.lower().strip(), MatchType.NONE)

    @staticmethod
    def _weighted_average(scores: list[tuple[float, float]]) -> float:
        """
        Compute a weighted average from a list of (score * weight, weight) tuples.

        Args:
            scores: List of (weighted_score, weight) pairs.

        Returns:
            Weighted average clamped between 0.0 and 100.0.
        """
        if not scores:
            return 0.0

        total_weighted = sum(ws for ws, _ in scores)
        total_weight = sum(w for _, w in scores)

        if total_weight == 0:
            return 0.0

        return min(100.0, max(0.0, total_weighted / total_weight))

    @staticmethod
    def _fallback_explanation(details: list[SkillMatchDetail]) -> str:
        """
        Build a basic explanation if Claude's overall_summary is empty.
        """
        semantic = sum(1 for d in details if d.match_type == MatchType.SEMANTIC)
        partial = sum(1 for d in details if d.match_type == MatchType.PARTIAL)
        none = sum(1 for d in details if d.match_type == MatchType.NONE)

        return (
            f"{semantic} semantic match(es), "
            f"{partial} partial match(es), "
            f"{none} unmatched skill(s)."
        )

    @staticmethod
    def _perfect_score() -> DimensionScore:
        """Return a perfect score when all skills were already exactly matched."""
        return DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=100.0,
            explanation="All JD skills were already matched exactly. "
                        "No semantic evaluation needed.",
            evidence=[],
        )

    @staticmethod
    def _zero_score(reason: str) -> DimensionScore:
        """Return a zero score with a reason."""
        return DimensionScore(
            dimension=ScoreDimension.SEMANTIC_SIMILARITY,
            score=0.0,
            explanation=reason,
            evidence=[],
        )


# Singleton
semantic_similarity_scorer = SemanticSimilarityScorer()