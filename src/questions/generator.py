from src.models import (
    CandidateProfile,
    TierClassification,
    InterviewPlan,
    InterviewQuestion,
)
from src.models.enums import Tier, ScoreDimension
from src.llm.client import llm_client
from src.llm.prompts.generate_questions import (
    GENERATE_QUESTIONS_SYSTEM,
    build_generate_questions_prompt,
    format_experience_for_questions,
    format_skill_match_summary,
)


class QuestionGenerator:
    """
    Generates a tailored interview plan for a candidate based on
    their TierClassification and CandidateProfile.

    Uses Claude to produce 5–8 specific, actionable interview questions
    with rationale, difficulty, and follow-up probes for each.

    Input:  TierClassification + CandidateProfile
    Output: InterviewPlan
    """

    def generate(
        self,
        classification: TierClassification,
        candidate: CandidateProfile,
    ) -> InterviewPlan:
        """
        Generate a complete interview plan for a candidate.

        Args:
            classification: TierClassification from TierClassifier.
            candidate:      Parsed CandidateProfile.

        Returns:
            Fully populated InterviewPlan.
        """
        print(
            f"[QuestionGenerator] Generating interview plan for "
            f"'{candidate.full_name}' (Tier {classification.tier.value})..."
        )

        # --- Prepare context for the prompt ---
        experience_summary = format_experience_for_questions(
            candidate.experience
        )

        skill_match_summary = format_skill_match_summary(
            classification.scoring_result.skill_matches
        )

        dimension_scores = self._extract_dimension_scores(classification)

        # --- Build and send prompt ---
        prompt = build_generate_questions_prompt(
            candidate_name=candidate.full_name,
            jd_title=classification.scoring_result.jd_title,
            tier=classification.tier,
            overall_score=classification.overall_score,
            strengths=classification.scoring_result.strengths,
            gaps=classification.scoring_result.gaps,
            focus_areas=classification.focus_areas,
            experience_summary=experience_summary,
            skill_match_summary=skill_match_summary,
            dimension_scores=dimension_scores,
        )

        raw_json = llm_client.complete_json(
            prompt=prompt,
            system=GENERATE_QUESTIONS_SYSTEM,
        )

        return self._parse_response(
            raw_json=raw_json,
            candidate=candidate,
            classification=classification,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_dimension_scores(
        classification: TierClassification,
    ) -> dict[str, float]:
        """
        Extract dimension scores from TierClassification into a
        plain dict keyed by dimension name string.
        Used to build the prompt — avoids passing Pydantic enums to the formatter.

        Args:
            classification: TierClassification from TierClassifier.

        Returns:
            Dict mapping dimension name → score float.
        """
        scoring = classification.scoring_result
        return {
            ScoreDimension.EXACT_MATCH.value:        scoring.exact_match.score,
            ScoreDimension.SEMANTIC_SIMILARITY.value: scoring.semantic_similarity.score,
            ScoreDimension.ACHIEVEMENT.value:         scoring.achievement.score,
            ScoreDimension.OWNERSHIP.value:           scoring.ownership.score,
        }

    def _parse_response(
        self,
        raw_json: dict,
        candidate: CandidateProfile,
        classification: TierClassification,
    ) -> InterviewPlan:
        """
        Parse Claude's JSON response into a validated InterviewPlan.

        Args:
            raw_json:       Parsed dict from Claude's response.
            candidate:      Candidate profile for context fields.
            classification: TierClassification for tier and title.

        Returns:
            Validated InterviewPlan instance.

        Raises:
            ValueError: If the response cannot be parsed into a valid plan.
        """
        try:
            questions = self._parse_questions(raw_json.get("questions", []))

            # Enforce minimum question count
            if len(questions) < 5:
                raise ValueError(
                    f"Claude returned only {len(questions)} questions. "
                    f"Minimum required is 5."
                )

            # Cap at 8 questions
            questions = questions[:8]

            duration = self._parse_duration(
                raw_json.get("recommended_duration_minutes", 45)
            )

            return InterviewPlan(
                candidate_name=candidate.full_name,
                jd_title=classification.scoring_result.jd_title,
                tier=classification.tier,
                interviewer_briefing=raw_json.get(
                    "interviewer_briefing",
                    self._fallback_briefing(candidate, classification),
                ),
                questions=questions,
                red_flags=self._parse_string_list(raw_json.get("red_flags", [])),
                green_flags=self._parse_string_list(raw_json.get("green_flags", [])),
                recommended_duration_minutes=duration,
            )

        except ValueError:
            raise

        except Exception as e:
            raise ValueError(
                f"[QuestionGenerator] Failed to parse Claude response "
                f"for '{candidate.full_name}'.\n"
                f"Error: {e}\n"
                f"Raw JSON keys: {list(raw_json.keys())}"
            ) from e

    @staticmethod
    def _parse_questions(questions_data: list) -> list[InterviewQuestion]:
        """
        Parse the questions list from Claude's response.
        Skips malformed entries rather than crashing.

        Args:
            questions_data: Raw list of question dicts from Claude.

        Returns:
            List of validated InterviewQuestion instances.
        """
        VALID_DIMENSIONS = {
            "technical_depth",
            "skill_gap",
            "ownership",
            "achievement",
        }
        VALID_DIFFICULTIES = {"easy", "medium", "hard"}

        questions = []
        for item in questions_data:
            if not isinstance(item, dict):
                continue

            try:
                # Sanitise dimension
                dimension = item.get("dimension", "technical_depth").lower().strip()
                if dimension not in VALID_DIMENSIONS:
                    dimension = "technical_depth"

                # Sanitise difficulty
                difficulty = item.get("difficulty", "medium").lower().strip()
                if difficulty not in VALID_DIFFICULTIES:
                    difficulty = "medium"

                question_text = item.get("question", "").strip()
                if not question_text:
                    continue                         # Skip empty questions

                questions.append(InterviewQuestion(
                    question=question_text,
                    rationale=item.get("rationale", "").strip(),
                    dimension=dimension,
                    difficulty=difficulty,
                    follow_up=item.get("follow_up") or None,
                ))

            except Exception:
                continue                             # Skip malformed entries

        return questions

    @staticmethod
    def _parse_duration(raw_duration) -> int:
        """
        Parse and validate the recommended interview duration.
        Snaps to nearest valid slot: 30, 45, or 60 minutes.

        Args:
            raw_duration: Raw value from Claude's response.

        Returns:
            Integer duration in minutes (30, 45, or 60).
        """
        valid_durations = [30, 45, 60]

        try:
            duration = int(raw_duration)
        except (TypeError, ValueError):
            return 45                               # Sensible default

        # Snap to nearest valid duration
        return min(valid_durations, key=lambda v: abs(v - duration))

    @staticmethod
    def _parse_string_list(raw_list: list) -> list[str]:
        """
        Parse a list of strings from Claude's response.
        Filters out non-strings and empty entries.

        Args:
            raw_list: Raw list from Claude.

        Returns:
            Clean list of non-empty strings.
        """
        return [
            item.strip()
            for item in raw_list
            if isinstance(item, str) and item.strip()
        ]

    @staticmethod
    def _fallback_briefing(
        candidate: CandidateProfile,
        classification: TierClassification,
    ) -> str:
        """
        Generate a minimal fallback briefing if Claude omits it.

        Args:
            candidate:      Candidate profile.
            classification: TierClassification with tier and score.

        Returns:
            Basic briefing string.
        """
        tier_descriptions = {
            Tier.A: "a strong",
            Tier.B: "a moderate",
            Tier.C: "a weak",
        }
        description = tier_descriptions.get(classification.tier, "a")

        return (
            f"{candidate.full_name} is {description} match for the role "
            f"with an overall score of {classification.overall_score:.1f}/100. "
            f"Review the focus areas and questions below before the interview."
        )


# Singleton
question_generator = QuestionGenerator()