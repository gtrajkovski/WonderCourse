"""Standards validator service for content validation.

Validates generated content against the active ContentStandardsProfile,
returning structured violations that can be displayed or auto-fixed.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from src.core.models import ContentStandardsProfile


# v1.2.0: CTA validation patterns (Coursera v3.0)
# These regex patterns detect activity previews and next-activity references
CTA_FORBIDDEN_PATTERNS = [
    # Pattern: "next you'll" or "next, you'll"
    (re.compile(r'\bnext\b[,\s]*\byou\'?ll\b', re.IGNORECASE),
     "References to 'next you'll...' preview upcoming activities"),
    # Pattern: "in the next" followed by content type
    (re.compile(r'\bin the next\s+(?:video|reading|quiz|module|lesson|activity|section)\b', re.IGNORECASE),
     "References 'in the next [content]' previewing upcoming activities"),
    # Pattern: "upcoming" content
    (re.compile(r'\bupcoming\s+(?:video|reading|quiz|module|lesson|activity|section|assessment)\b', re.IGNORECASE),
     "References 'upcoming' content"),
    # Pattern: "following" activity reference
    (re.compile(r'\b(?:the\s+)?following\s+(?:video|reading|quiz|activity|exercise)\b', re.IGNORECASE),
     "References 'following' content"),
    # Pattern: "work through" a content type (preview)
    (re.compile(r'\bwork\s+through\s+a\s+(?:reading|quiz|lab|exercise)\b', re.IGNORECASE),
     "Previews 'work through a [content]'"),
    # Pattern: "take a quiz/assessment"
    (re.compile(r'\b(?:take|complete)\s+(?:a|the)\s+(?:quiz|assessment|test)\b', re.IGNORECASE),
     "Previews taking an assessment"),
]


class ViolationSeverity(Enum):
    """Severity levels for standards violations."""
    ERROR = "error"      # Must fix before publishing
    WARNING = "warning"  # Should fix, but not blocking
    INFO = "info"        # Suggestion for improvement


@dataclass
class StandardsViolation:
    """A single standards violation."""
    field: str              # Which field has the violation
    rule: str               # Human-readable rule description
    expected: str           # What the standard requires
    actual: str             # What was found
    severity: ViolationSeverity = ViolationSeverity.WARNING
    auto_fixable: bool = False  # Can this be automatically corrected?
    fix_suggestion: Optional[str] = None  # Suggested fix if auto_fixable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "field": self.field,
            "rule": self.rule,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity.value,
            "auto_fixable": self.auto_fixable,
            "fix_suggestion": self.fix_suggestion,
        }


class StandardsValidator:
    """Validates content against ContentStandardsProfile standards.

    Each content type has specific validation rules based on the
    active standards profile.
    """

    def __init__(self, standards: ContentStandardsProfile):
        self.standards = standards

    def validate(self, item_type: str, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate content against standards.

        Args:
            item_type: One of: video, reading, quiz, practice_quiz, hol,
                      coach, lab, discussion, assignment, project, rubric
            content: The content dictionary to validate

        Returns:
            List of StandardsViolation objects (empty if valid)
        """
        validators = {
            "video": self._validate_video,
            "reading": self._validate_reading,
            "quiz": self._validate_quiz,
            "practice_quiz": self._validate_practice_quiz,
            "hol": self._validate_hol,
            "coach": self._validate_coach,
            "lab": self._validate_lab,
            "discussion": self._validate_discussion,
            "assignment": self._validate_assignment,
            "project": self._validate_project,
            "rubric": self._validate_rubric,
        }

        validator = validators.get(item_type)
        if validator is None:
            return []

        return validator(content)

    def _validate_video(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate video script against standards."""
        violations = []
        s = self.standards

        # Check duration
        duration = content.get("estimated_duration_min", 0)
        if duration > s.video_max_duration_min:
            violations.append(StandardsViolation(
                field="estimated_duration_min",
                rule="Maximum video duration",
                expected=f"<= {s.video_max_duration_min} minutes",
                actual=f"{duration} minutes",
                severity=ViolationSeverity.ERROR,
                auto_fixable=False,
            ))

        # Check ideal duration range
        if duration < s.video_ideal_min_duration or duration > s.video_ideal_max_duration:
            violations.append(StandardsViolation(
                field="estimated_duration_min",
                rule="Ideal video duration range",
                expected=f"{s.video_ideal_min_duration}-{s.video_ideal_max_duration} minutes",
                actual=f"{duration} minutes",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        # Check structure if required
        if s.video_structure_required and s.video_structure:
            sections = content.get("sections", [])
            section_names = [sec.get("section_name", "").lower() for sec in sections]

            for required_section in s.video_structure:
                if required_section.lower() not in section_names:
                    violations.append(StandardsViolation(
                        field="sections",
                        rule="Required video structure",
                        expected=f"Section '{required_section}' required",
                        actual=f"Missing '{required_section}' section",
                        severity=ViolationSeverity.ERROR,
                        auto_fixable=False,
                    ))

        # Check word count against WPM
        script_text = content.get("full_script", "")
        word_count = len(script_text.split()) if script_text else 0
        expected_max_words = s.video_max_duration_min * s.video_wpm

        if word_count > expected_max_words:
            violations.append(StandardsViolation(
                field="full_script",
                rule="Video word count (based on speaking rate)",
                expected=f"<= {expected_max_words} words ({s.video_wpm} WPM × {s.video_max_duration_min} min)",
                actual=f"{word_count} words",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        # v1.2.0: CTA validation (Coursera v3.0)
        cta_section = None
        sections = content.get("sections", [])
        for sec in sections:
            if sec.get("section_name", "").lower() == "cta":
                cta_section = sec
                break

        if cta_section:
            cta_text = cta_section.get("script_text", "")

            # Check CTA word count
            cta_word_count = len(cta_text.split()) if cta_text else 0
            if cta_word_count > s.video_cta_max_words:
                violations.append(StandardsViolation(
                    field="sections.cta",
                    rule="CTA maximum word count",
                    expected=f"<= {s.video_cta_max_words} words (~15 seconds)",
                    actual=f"{cta_word_count} words",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                    fix_suggestion="Shorten CTA to under 35 words for impact"
                ))

            # Check for forbidden activity preview phrases
            if s.video_cta_forbid_activity_previews and cta_text:
                cta_lower = cta_text.lower()

                # Check simple phrase matches from standards profile
                for phrase in s.video_cta_forbidden_phrases:
                    if phrase.lower() in cta_lower:
                        violations.append(StandardsViolation(
                            field="sections.cta",
                            rule="No activity previews in CTA",
                            expected="CTA should not preview upcoming activities",
                            actual=f"Found forbidden phrase: '{phrase}'",
                            severity=ViolationSeverity.WARNING,
                            auto_fixable=False,
                            fix_suggestion=f"Remove reference to '{phrase}' - CTAs should motivate without spoiling what's next"
                        ))

                # Check regex pattern matches (v1.2.0: Coursera v3.0)
                for pattern, description in CTA_FORBIDDEN_PATTERNS:
                    match = pattern.search(cta_text)
                    if match:
                        violations.append(StandardsViolation(
                            field="sections.cta",
                            rule="No activity previews in CTA",
                            expected="CTA should not preview upcoming activities",
                            actual=f"{description}: '{match.group()}'",
                            severity=ViolationSeverity.WARNING,
                            auto_fixable=False,
                            fix_suggestion="CTAs should motivate learners without revealing what's next - focus on the value they'll gain"
                        ))

        # v1.2.1: Video section timing validation
        if s.video_section_timing_enabled:
            sections = content.get("sections", [])
            for sec in sections:
                section_name = sec.get("section_name", "").lower()
                if section_name in s.video_section_word_counts:
                    limits = s.video_section_word_counts[section_name]
                    script_text = sec.get("script_text", "")
                    word_count = len(script_text.split()) if script_text else 0

                    min_words = limits.get("min", 0)
                    max_words = limits.get("max", 9999)

                    if word_count < min_words:
                        violations.append(StandardsViolation(
                            field=f"sections.{section_name}",
                            rule=f"Minimum word count for {section_name.upper()} section",
                            expected=f">= {min_words} words",
                            actual=f"{word_count} words",
                            severity=ViolationSeverity.INFO,
                            auto_fixable=False,
                            fix_suggestion=f"Expand the {section_name} section to at least {min_words} words"
                        ))
                    elif word_count > max_words:
                        violations.append(StandardsViolation(
                            field=f"sections.{section_name}",
                            rule=f"Maximum word count for {section_name.upper()} section",
                            expected=f"<= {max_words} words",
                            actual=f"{word_count} words",
                            severity=ViolationSeverity.WARNING,
                            auto_fixable=False,
                            fix_suggestion=f"Trim the {section_name} section to under {max_words} words"
                        ))

        # v1.3.0: Visual cue validation
        if s.video_visual_cue_enabled:
            # Find the Content section for visual cue validation
            content_section = None
            sections = content.get("sections", [])
            for sec in sections:
                if sec.get("section_name", "").lower() == "content":
                    content_section = sec
                    break

            if content_section:
                script_text = content_section.get("script_text", "")
                if script_text:
                    # Calculate expected visual cues based on word count and speaking rate
                    word_count = len(script_text.split())
                    wpm = s.video_wpm  # Default 150 WPM
                    duration_seconds = (word_count / wpm) * 60
                    expected_cues = max(1, int(duration_seconds / s.video_visual_cue_interval_seconds))

                    # Count actual visual cues using pattern
                    cue_pattern = re.compile(s.video_visual_cue_pattern, re.IGNORECASE)
                    actual_cues = len(cue_pattern.findall(script_text))

                    if actual_cues < expected_cues:
                        violations.append(StandardsViolation(
                            field="sections.content",
                            rule="Visual cues in content section",
                            expected=f">= {expected_cues} visual cues (one every ~{s.video_visual_cue_interval_seconds}s)",
                            actual=f"{actual_cues} visual cues found",
                            severity=ViolationSeverity.INFO,
                            auto_fixable=False,
                            fix_suggestion="Add visual cues like [Talking head: explanation] or [B-roll: example footage]"
                        ))

        return violations

    def _validate_reading(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate reading content against standards."""
        violations = []
        s = self.standards

        # Check word count
        body = content.get("body", "")
        word_count = len(body.split()) if body else 0

        if word_count > s.reading_max_words:
            violations.append(StandardsViolation(
                field="body",
                rule="Maximum reading word count",
                expected=f"<= {s.reading_max_words} words",
                actual=f"{word_count} words",
                severity=ViolationSeverity.ERROR,
                auto_fixable=False,
            ))

        # Check references
        references = content.get("references", [])
        ref_count = len(references)

        if s.reading_reference_format.lower() != "none":
            if ref_count < s.reading_min_references:
                violations.append(StandardsViolation(
                    field="references",
                    rule="Minimum references required",
                    expected=f">= {s.reading_min_references} references",
                    actual=f"{ref_count} references",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                ))

            if ref_count > s.reading_max_references:
                violations.append(StandardsViolation(
                    field="references",
                    rule="Maximum references allowed",
                    expected=f"<= {s.reading_max_references} references",
                    actual=f"{ref_count} references",
                    severity=ViolationSeverity.INFO,
                    auto_fixable=False,
                ))

        # Check optional readings
        optional = content.get("optional_readings", [])
        if len(optional) > s.reading_max_optional:
            violations.append(StandardsViolation(
                field="optional_readings",
                rule="Maximum optional readings",
                expected=f"<= {s.reading_max_optional}",
                actual=f"{len(optional)}",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        # v1.2.1: Reading attribution validation
        if s.reading_require_attribution:
            body = content.get("body", "")
            key_takeaways = content.get("key_takeaways", [])
            attribution = content.get("attribution", "")

            # Check if attribution exists
            if not attribution:
                # Also check if it's embedded in the body after Key Takeaways
                has_attribution_in_body = False
                if body:
                    # Look for common attribution markers
                    attribution_markers = ["author's original work", "developed with the assistance of", "based on professional experience"]
                    body_lower = body.lower()
                    has_attribution_in_body = any(marker in body_lower for marker in attribution_markers)

                if not has_attribution_in_body:
                    violations.append(StandardsViolation(
                        field="attribution",
                        rule="Author attribution required",
                        expected="Attribution statement after Key Takeaways",
                        actual="No attribution found",
                        severity=ViolationSeverity.WARNING,
                        auto_fixable=True,
                        fix_suggestion=f"Add attribution using template: {s.reading_attribution_template}"
                    ))

        # v1.2.1: Reference link paywall validation
        if s.reading_require_free_links:
            references = content.get("references", [])
            for i, ref in enumerate(references):
                url = ref.get("url", "") or ref.get("link", "") or ""
                if url:
                    url_lower = url.lower()
                    for domain in s.reading_paywall_domains:
                        if domain.lower() in url_lower:
                            violations.append(StandardsViolation(
                                field=f"references[{i}]",
                                rule="No paywall links in references",
                                expected="All reference links must be freely accessible",
                                actual=f"Link contains paywall domain: {domain}",
                                severity=ViolationSeverity.WARNING,
                                auto_fixable=False,
                                fix_suggestion=f"Replace with a freely accessible source or remove the link"
                            ))
                            break  # Only report one domain match per reference

        return violations

    def _validate_quiz(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate quiz content against standards."""
        violations = []
        s = self.standards

        questions = content.get("questions", [])

        for i, q in enumerate(questions):
            options = q.get("options", [])

            # Check options count
            if len(options) != s.quiz_options_per_question:
                violations.append(StandardsViolation(
                    field=f"questions[{i}].options",
                    rule="Options per question",
                    expected=f"{s.quiz_options_per_question} options",
                    actual=f"{len(options)} options",
                    severity=ViolationSeverity.ERROR,
                    auto_fixable=False,
                ))

            # Check per-option feedback if required
            if s.quiz_require_per_option_feedback:
                for j, opt in enumerate(options):
                    if not opt.get("feedback"):
                        violations.append(StandardsViolation(
                            field=f"questions[{i}].options[{j}].feedback",
                            rule="Per-option feedback required",
                            expected="Feedback text present",
                            actual="No feedback provided",
                            severity=ViolationSeverity.WARNING,
                            auto_fixable=False,
                        ))

        # Check answer distribution if required (v1.2.0: added minimum check)
        if s.quiz_require_balanced_distribution and questions:
            answer_counts = {}
            answer_sequence = []
            for q in questions:
                correct = q.get("correct_answer", "")
                answer_counts[correct] = answer_counts.get(correct, 0) + 1
                answer_sequence.append(correct)

            total = len(questions)

            # Only check distribution with 4+ questions
            if total >= 4:
                max_allowed_pct = s.quiz_max_distribution_skew_percent
                min_allowed_pct = s.quiz_min_distribution_percent
                max_allowed = (max_allowed_pct / 100) * total
                min_allowed = (min_allowed_pct / 100) * total

                for letter, count in answer_counts.items():
                    pct = 100 * count / total

                    # Check maximum distribution (WARNING)
                    if count > max_allowed:
                        violations.append(StandardsViolation(
                            field="questions",
                            rule="Balanced answer distribution (maximum)",
                            expected=f"No answer > {max_allowed_pct}% of total",
                            actual=f"Answer '{letter}' is {count}/{total} ({pct:.0f}%)",
                            severity=ViolationSeverity.WARNING,
                            auto_fixable=False,
                        ))

                    # Check minimum distribution (INFO - v1.2.0)
                    if count < min_allowed:
                        violations.append(StandardsViolation(
                            field="questions",
                            rule="Balanced answer distribution (minimum)",
                            expected=f"Each answer should be >= {min_allowed_pct}% of total",
                            actual=f"Answer '{letter}' is {count}/{total} ({pct:.0f}%)",
                            severity=ViolationSeverity.INFO,
                            auto_fixable=False,
                        ))

            # v1.2.0: Check for predictable patterns
            if total >= 4:
                pattern_violation = self._check_answer_pattern(answer_sequence)
                if pattern_violation:
                    violations.append(pattern_violation)

        # v1.2.0: Check option length consistency and correct answer position
        for i, q in enumerate(questions):
            options = q.get("options", [])
            correct_answer = q.get("correct_answer", "")

            if len(options) >= 2:
                # Check option length variance
                option_lengths = []
                correct_option_text = None

                for opt in options:
                    text = opt.get("text", "") if isinstance(opt, dict) else str(opt)
                    option_lengths.append(len(text))
                    opt_label = opt.get("label", "") if isinstance(opt, dict) else ""
                    if opt_label == correct_answer:
                        correct_option_text = text

                if option_lengths:
                    avg_length = sum(option_lengths) / len(option_lengths)
                    max_len = max(option_lengths)
                    min_len = min(option_lengths)

                    # Flag if options vary too much (>50% difference from average)
                    if max_len > 0 and (max_len - min_len) / max_len > 0.5:
                        violations.append(StandardsViolation(
                            field=f"questions[{i}].options",
                            rule="Option length consistency",
                            expected="Options should be similar in length (within 50%)",
                            actual=f"Lengths vary from {min_len} to {max_len} characters",
                            severity=ViolationSeverity.INFO,
                            auto_fixable=False,
                            fix_suggestion="Balance option lengths to avoid giving away the answer"
                        ))

                    # Check if correct answer is longest or shortest
                    if correct_option_text:
                        correct_len = len(correct_option_text)
                        if correct_len == max_len and max_len > min_len + 10:
                            violations.append(StandardsViolation(
                                field=f"questions[{i}]",
                                rule="Correct answer should not be longest option",
                                expected="Correct answer length should be similar to distractors",
                                actual=f"Correct answer ({correct_len} chars) is the longest option",
                                severity=ViolationSeverity.WARNING,
                                auto_fixable=False,
                                fix_suggestion="Shorten correct answer or expand distractors"
                            ))
                        elif correct_len == min_len and max_len > min_len + 10:
                            violations.append(StandardsViolation(
                                field=f"questions[{i}]",
                                rule="Correct answer should not be shortest option",
                                expected="Correct answer length should be similar to distractors",
                                actual=f"Correct answer ({correct_len} chars) is the shortest option",
                                severity=ViolationSeverity.INFO,
                                auto_fixable=False,
                                fix_suggestion="Expand correct answer or shorten distractors"
                            ))

        return violations

    def _check_answer_pattern(self, sequence: list) -> StandardsViolation:
        """Check for predictable answer patterns.

        Args:
            sequence: List of correct answer letters.

        Returns:
            StandardsViolation if pattern detected, None otherwise.
        """
        if len(sequence) < 4:
            return None

        # Check for repeating patterns like A,B,C,D,A,B,C,D
        for pattern_len in [2, 3, 4]:
            if len(sequence) >= pattern_len * 2:
                pattern = sequence[:pattern_len]
                is_repeating = True

                for i in range(pattern_len, len(sequence)):
                    if sequence[i] != pattern[i % pattern_len]:
                        is_repeating = False
                        break

                if is_repeating:
                    return StandardsViolation(
                        field="questions",
                        rule="No predictable answer patterns",
                        expected="Answer sequence should appear random",
                        actual=f"Detected repeating pattern: {','.join(pattern)}",
                        severity=ViolationSeverity.WARNING,
                        auto_fixable=False,
                        fix_suggestion="Randomize correct answer positions"
                    )

        # Check for runs (same answer 3+ times in a row)
        for i in range(len(sequence) - 2):
            if sequence[i] == sequence[i+1] == sequence[i+2]:
                return StandardsViolation(
                    field="questions",
                    rule="No answer runs",
                    expected="Avoid same answer 3+ times consecutively",
                    actual=f"Answer '{sequence[i]}' appears 3+ times in a row",
                    severity=ViolationSeverity.INFO,
                    auto_fixable=False,
                    fix_suggestion="Vary answer positions to avoid runs"
                )

        return None

    def _validate_practice_quiz(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate practice quiz content against standards."""
        # Start with regular quiz validation
        violations = self._validate_quiz(content)
        s = self.standards

        questions = content.get("questions", [])

        for i, q in enumerate(questions):
            # Check hints if required
            if s.practice_quiz_require_hints:
                if not q.get("hint"):
                    violations.append(StandardsViolation(
                        field=f"questions[{i}].hint",
                        rule="Hints required for practice quiz",
                        expected="Hint text present",
                        actual="No hint provided",
                        severity=ViolationSeverity.WARNING,
                        auto_fixable=False,
                    ))

            # Check explanations if required
            if s.practice_quiz_require_explanations:
                if not q.get("explanation"):
                    violations.append(StandardsViolation(
                        field=f"questions[{i}].explanation",
                        rule="Explanations required for practice quiz",
                        expected="Explanation text present",
                        actual="No explanation provided",
                        severity=ViolationSeverity.WARNING,
                        auto_fixable=False,
                    ))

        return violations

    def _validate_hol(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate Hands-On Lab content against standards."""
        violations = []
        s = self.standards

        # Check rubric criteria count
        rubric = content.get("rubric", {})
        criteria = rubric.get("criteria", [])

        if len(criteria) != s.hol_rubric_criteria_count:
            violations.append(StandardsViolation(
                field="rubric.criteria",
                rule="HOL rubric criteria count",
                expected=f"Exactly {s.hol_rubric_criteria_count} criteria",
                actual=f"{len(criteria)} criteria",
                severity=ViolationSeverity.ERROR,
                auto_fixable=False,
            ))

        # Check total points
        total_points = sum(c.get("points", 0) for c in criteria)
        if total_points != s.hol_rubric_total_points:
            violations.append(StandardsViolation(
                field="rubric.criteria",
                rule="HOL rubric total points",
                expected=f"{s.hol_rubric_total_points} total points",
                actual=f"{total_points} total points",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        # Check word count
        response = content.get("sample_response", "")
        word_count = len(response.split()) if response else 0

        if word_count > s.hol_max_word_count:
            violations.append(StandardsViolation(
                field="sample_response",
                rule="Maximum HOL response word count",
                expected=f"<= {s.hol_max_word_count} words",
                actual=f"{word_count} words",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        return violations

    def _validate_coach(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate coach dialogue content against standards."""
        violations = []
        s = self.standards

        # Check scenario if required
        if s.coach_require_scenario:
            if not content.get("scenario"):
                violations.append(StandardsViolation(
                    field="scenario",
                    rule="Scenario required for coach dialogue",
                    expected="Scenario text present",
                    actual="No scenario provided",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                ))

        # Check example responses if required
        if s.coach_require_example_responses:
            examples = content.get("example_responses", [])
            expected_levels = set(s.coach_evaluation_levels)
            actual_levels = set(ex.get("level", "") for ex in examples)

            missing = expected_levels - actual_levels
            if missing:
                violations.append(StandardsViolation(
                    field="example_responses",
                    rule="Example responses for all evaluation levels",
                    expected=f"Examples for: {', '.join(expected_levels)}",
                    actual=f"Missing: {', '.join(missing)}",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                ))

        return violations

    def _validate_lab(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate lab content against standards."""
        violations = []
        s = self.standards

        # Check exercises count
        exercises = content.get("exercises", [])

        if len(exercises) < s.lab_min_exercises:
            violations.append(StandardsViolation(
                field="exercises",
                rule="Minimum lab exercises",
                expected=f">= {s.lab_min_exercises} exercises",
                actual=f"{len(exercises)} exercises",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(exercises) > s.lab_max_exercises:
            violations.append(StandardsViolation(
                field="exercises",
                rule="Maximum lab exercises",
                expected=f"<= {s.lab_max_exercises} exercises",
                actual=f"{len(exercises)} exercises",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        # Check setup steps if required
        if s.lab_require_setup_steps:
            if not content.get("setup_steps"):
                violations.append(StandardsViolation(
                    field="setup_steps",
                    rule="Setup steps required for lab",
                    expected="Setup steps present",
                    actual="No setup steps provided",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                ))

        return violations

    def _validate_discussion(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate discussion content against standards."""
        violations = []
        s = self.standards

        # Check facilitation questions
        questions = content.get("facilitation_questions", [])

        if len(questions) < s.discussion_min_facilitation_questions:
            violations.append(StandardsViolation(
                field="facilitation_questions",
                rule="Minimum facilitation questions",
                expected=f">= {s.discussion_min_facilitation_questions} questions",
                actual=f"{len(questions)} questions",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(questions) > s.discussion_max_facilitation_questions:
            violations.append(StandardsViolation(
                field="facilitation_questions",
                rule="Maximum facilitation questions",
                expected=f"<= {s.discussion_max_facilitation_questions} questions",
                actual=f"{len(questions)} questions",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        # Check engagement hooks if required
        if s.discussion_require_engagement_hooks:
            if not content.get("engagement_hooks"):
                violations.append(StandardsViolation(
                    field="engagement_hooks",
                    rule="Engagement hooks required",
                    expected="Engagement hooks present",
                    actual="No engagement hooks provided",
                    severity=ViolationSeverity.WARNING,
                    auto_fixable=False,
                ))

        return violations

    def _validate_assignment(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate assignment content against standards."""
        violations = []
        s = self.standards

        # Check deliverables count
        deliverables = content.get("deliverables", [])

        if len(deliverables) < s.assignment_min_deliverables:
            violations.append(StandardsViolation(
                field="deliverables",
                rule="Minimum assignment deliverables",
                expected=f">= {s.assignment_min_deliverables} deliverables",
                actual=f"{len(deliverables)} deliverables",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(deliverables) > s.assignment_max_deliverables:
            violations.append(StandardsViolation(
                field="deliverables",
                rule="Maximum assignment deliverables",
                expected=f"<= {s.assignment_max_deliverables} deliverables",
                actual=f"{len(deliverables)} deliverables",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        # Check grading criteria count
        criteria = content.get("grading_criteria", [])

        if len(criteria) < s.assignment_min_grading_criteria:
            violations.append(StandardsViolation(
                field="grading_criteria",
                rule="Minimum grading criteria",
                expected=f">= {s.assignment_min_grading_criteria} criteria",
                actual=f"{len(criteria)} criteria",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(criteria) > s.assignment_max_grading_criteria:
            violations.append(StandardsViolation(
                field="grading_criteria",
                rule="Maximum grading criteria",
                expected=f"<= {s.assignment_max_grading_criteria} criteria",
                actual=f"{len(criteria)} criteria",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        return violations

    def _validate_project(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate project milestone content against standards."""
        violations = []
        s = self.standards

        # Check milestone type
        milestone_type = content.get("milestone_type", "")
        if milestone_type and milestone_type not in s.project_milestone_types:
            violations.append(StandardsViolation(
                field="milestone_type",
                rule="Valid milestone type",
                expected=f"One of: {', '.join(s.project_milestone_types)}",
                actual=milestone_type,
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        # Check deliverables count
        deliverables = content.get("deliverables", [])

        if len(deliverables) < s.project_min_deliverables:
            violations.append(StandardsViolation(
                field="deliverables",
                rule="Minimum project deliverables",
                expected=f">= {s.project_min_deliverables} deliverables",
                actual=f"{len(deliverables)} deliverables",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(deliverables) > s.project_max_deliverables:
            violations.append(StandardsViolation(
                field="deliverables",
                rule="Maximum project deliverables",
                expected=f"<= {s.project_max_deliverables} deliverables",
                actual=f"{len(deliverables)} deliverables",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        return violations

    def _validate_rubric(self, content: Dict[str, Any]) -> List[StandardsViolation]:
        """Validate rubric content against standards."""
        violations = []
        s = self.standards

        # Check criteria count
        criteria = content.get("criteria", [])

        if len(criteria) < s.rubric_min_criteria:
            violations.append(StandardsViolation(
                field="criteria",
                rule="Minimum rubric criteria",
                expected=f">= {s.rubric_min_criteria} criteria",
                actual=f"{len(criteria)} criteria",
                severity=ViolationSeverity.WARNING,
                auto_fixable=False,
            ))

        if len(criteria) > s.rubric_max_criteria:
            violations.append(StandardsViolation(
                field="criteria",
                rule="Maximum rubric criteria",
                expected=f"<= {s.rubric_max_criteria} criteria",
                actual=f"{len(criteria)} criteria",
                severity=ViolationSeverity.INFO,
                auto_fixable=False,
            ))

        # Check that criteria have all required levels
        expected_levels = set(s.rubric_levels)

        for i, criterion in enumerate(criteria):
            levels = criterion.get("levels", [])
            actual_levels = set(lvl.get("name", "") for lvl in levels)

            missing = expected_levels - actual_levels
            if missing:
                violations.append(StandardsViolation(
                    field=f"criteria[{i}].levels",
                    rule="All rubric performance levels present",
                    expected=f"Levels: {', '.join(expected_levels)}",
                    actual=f"Missing: {', '.join(missing)}",
                    severity=ViolationSeverity.ERROR,
                    auto_fixable=False,
                ))

        return violations


def validate_content(
    item_type: str,
    content: Dict[str, Any],
    standards: ContentStandardsProfile
) -> List[StandardsViolation]:
    """Convenience function to validate content against standards.

    Args:
        item_type: Content type (video, reading, quiz, etc.)
        content: The content dictionary
        standards: The standards profile to validate against

    Returns:
        List of violations (empty if valid)
    """
    validator = StandardsValidator(standards)
    return validator.validate(item_type, content)
