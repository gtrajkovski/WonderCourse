"""Tests for v1.2.0 validation features (Coursera v3.0 compliance)."""

import pytest
from src.validators.standards_validator import (
    StandardsValidator,
    StandardsViolation,
    ViolationSeverity,
)
from src.validators.course_auditor import CourseAuditor
from src.core.models import (
    ContentStandardsProfile, Course, Module, Lesson, Activity,
    AuditCheckType, ContentType, ActivityType
)


class TestCTAValidation:
    """Tests for CTA validation in video scripts."""

    def test_cta_under_word_limit_passes(self):
        """CTA under 35 words should pass validation."""
        standards = ContentStandardsProfile(
            video_cta_max_words=35,
            video_section_timing_enabled=False  # Disable timing validation for this test
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Ready to put this into practice? Let's go!"
                }
            ]
        }

        violations = validator.validate("video", content)
        cta_violations = [v for v in violations if "CTA" in v.rule]
        assert len(cta_violations) == 0

    def test_cta_over_word_limit_warning(self):
        """CTA over 35 words should produce warning."""
        standards = ContentStandardsProfile(video_cta_max_words=35)
        validator = StandardsValidator(standards)

        # Generate a CTA with 40 words
        long_cta = " ".join(["word"] * 40)
        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": long_cta
                }
            ]
        }

        violations = validator.validate("video", content)
        cta_word_violations = [v for v in violations if "CTA maximum word" in v.rule]
        assert len(cta_word_violations) == 1
        assert cta_word_violations[0].severity == ViolationSeverity.WARNING

    def test_cta_forbidden_phrase_next_youll(self):
        """CTA with 'next you'll' should produce warning."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=True
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Next you'll practice with a hands-on activity."
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        assert len(preview_violations) >= 1

    def test_cta_forbidden_phrase_upcoming(self):
        """CTA with 'upcoming' should produce warning."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=True
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "In the upcoming quiz, you'll test your knowledge."
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        assert len(preview_violations) >= 1

    def test_cta_forbidden_phrase_coach_dialogue(self):
        """CTA with 'coach dialogue' should produce warning."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=True
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Practice these skills in the coach dialogue."
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        assert len(preview_violations) >= 1

    def test_cta_no_forbidden_phrases_passes(self):
        """CTA without forbidden phrases should pass."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=True
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Ready to put this into practice? Let's go!"
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        assert len(preview_violations) == 0

    def test_cta_validation_disabled(self):
        """CTA validation should not run when disabled."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=False
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Next you'll complete a graded assessment."
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        # Should not produce violations when disabled
        assert len(preview_violations) == 0

    def test_cta_multiple_forbidden_phrases(self):
        """CTA with multiple forbidden phrases should produce multiple warnings."""
        standards = ContentStandardsProfile(
            video_cta_forbid_activity_previews=True
        )
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Next you'll work through a hands-on lab and then take the final quiz."
                }
            ]
        }

        violations = validator.validate("video", content)
        preview_violations = [v for v in violations if "activity previews" in v.rule]
        # Should detect multiple forbidden phrases
        assert len(preview_violations) >= 2


class TestQuizDistributionValidation:
    """Tests for quiz answer distribution validation (v1.2.0 enhanced)."""

    def test_answer_exceeds_maximum_distribution(self):
        """Answer at 50% with 10 questions should produce warning."""
        standards = ContentStandardsProfile(
            quiz_require_balanced_distribution=True,
            quiz_max_distribution_skew_percent=35,
            quiz_min_distribution_percent=15
        )
        validator = StandardsValidator(standards)

        # 10 questions: 5x A, 2x B, 2x C, 1x D
        questions = [
            {"correct_answer": "A"} for _ in range(5)
        ] + [
            {"correct_answer": "B"} for _ in range(2)
        ] + [
            {"correct_answer": "C"} for _ in range(2)
        ] + [
            {"correct_answer": "D"}
        ]
        content = {"questions": questions}

        violations = validator.validate("quiz", content)
        max_violations = [v for v in violations if "maximum" in v.rule.lower()]
        assert len(max_violations) == 1
        assert max_violations[0].severity == ViolationSeverity.WARNING

    def test_answer_below_minimum_distribution(self):
        """Answer at 10% with 10 questions should produce INFO."""
        standards = ContentStandardsProfile(
            quiz_require_balanced_distribution=True,
            quiz_max_distribution_skew_percent=35,
            quiz_min_distribution_percent=15
        )
        validator = StandardsValidator(standards)

        # 10 questions: 3x A, 3x B, 3x C, 1x D = D is 10%
        questions = [
            {"correct_answer": "A"} for _ in range(3)
        ] + [
            {"correct_answer": "B"} for _ in range(3)
        ] + [
            {"correct_answer": "C"} for _ in range(3)
        ] + [
            {"correct_answer": "D"}
        ]
        content = {"questions": questions}

        violations = validator.validate("quiz", content)
        min_violations = [v for v in violations if "minimum" in v.rule.lower()]
        assert len(min_violations) == 1
        assert min_violations[0].severity == ViolationSeverity.INFO

    def test_balanced_distribution_passes(self):
        """Evenly distributed answers should pass."""
        standards = ContentStandardsProfile(
            quiz_require_balanced_distribution=True,
            quiz_max_distribution_skew_percent=35,
            quiz_min_distribution_percent=15
        )
        validator = StandardsValidator(standards)

        # 8 questions: 2x each letter
        questions = [
            {"correct_answer": "A"}, {"correct_answer": "A"},
            {"correct_answer": "B"}, {"correct_answer": "B"},
            {"correct_answer": "C"}, {"correct_answer": "C"},
            {"correct_answer": "D"}, {"correct_answer": "D"},
        ]
        content = {"questions": questions}

        violations = validator.validate("quiz", content)
        dist_violations = [v for v in violations if "distribution" in v.rule.lower()]
        assert len(dist_violations) == 0

    def test_small_quiz_skips_distribution_check(self):
        """Quizzes with < 4 questions should skip distribution check."""
        standards = ContentStandardsProfile(
            quiz_require_balanced_distribution=True,
            quiz_max_distribution_skew_percent=35,
            quiz_min_distribution_percent=15
        )
        validator = StandardsValidator(standards)

        # 3 questions: all A (would be 100% but shouldn't trigger)
        questions = [
            {"correct_answer": "A"},
            {"correct_answer": "A"},
            {"correct_answer": "A"},
        ]
        content = {"questions": questions}

        violations = validator.validate("quiz", content)
        dist_violations = [v for v in violations if "distribution" in v.rule.lower()]
        assert len(dist_violations) == 0

    def test_distribution_check_disabled(self):
        """No distribution violations when check is disabled."""
        standards = ContentStandardsProfile(
            quiz_require_balanced_distribution=False
        )
        validator = StandardsValidator(standards)

        # Heavily skewed distribution
        questions = [{"correct_answer": "A"} for _ in range(10)]
        content = {"questions": questions}

        violations = validator.validate("quiz", content)
        dist_violations = [v for v in violations if "distribution" in v.rule.lower()]
        assert len(dist_violations) == 0


class TestSequentialReferenceDetection:
    """Tests for sequential reference detection (v1.2.0)."""

    def _make_course_with_content(self, content: str) -> Course:
        """Helper to create a course with a single activity containing content."""
        course = Course(title="Test Course")
        module = Module(title="Test Module")
        lesson = Lesson(title="Test Lesson")
        activity = Activity(
            title="Test Activity",
            content_type=ContentType.VIDEO,
            activity_type=ActivityType.VIDEO_LECTURE,
            content=content
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)
        return course

    def test_detect_as_we_discussed_in_module(self):
        """Should detect 'as we discussed in Module 1' references."""
        course = self._make_course_with_content(
            "As we discussed in Module 1, this concept is important."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_detect_in_previous_video(self):
        """Should detect 'in the previous video' references."""
        course = self._make_course_with_content(
            "In the previous video, we covered the basics."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_detect_in_the_next_lesson(self):
        """Should detect 'in the next lesson' references."""
        course = self._make_course_with_content(
            "In the next lesson, we'll explore advanced topics."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_detect_earlier_in_course(self):
        """Should detect 'earlier in this course' references."""
        course = self._make_course_with_content(
            "Earlier in this course, we introduced the foundation."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_detect_module_number_reference(self):
        """Should detect 'in Module 2' style references."""
        course = self._make_course_with_content(
            "The tools introduced in Module 2 will be essential here."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_clean_content_passes(self):
        """Content without sequential references should pass."""
        course = self._make_course_with_content(
            "Python is a versatile programming language. "
            "It supports multiple programming paradigms. "
            "You can write scripts or build applications."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references()

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) == 0

    def test_check_disabled_skips_detection(self):
        """Should skip detection when forbid=False."""
        course = self._make_course_with_content(
            "As we discussed in Module 1, this is important."
        )

        auditor = CourseAuditor(course)
        auditor.check_sequential_references(forbid=False)

        seq_issues = [i for i in auditor.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) == 0

    def test_run_all_checks_includes_sequential(self):
        """run_all_checks should include sequential reference detection."""
        course = self._make_course_with_content(
            "Remember from Module 1 how we set this up."
        )

        auditor = CourseAuditor(course)
        result = auditor.run_all_checks()

        seq_issues = [i for i in result.issues
                     if i.check_type == AuditCheckType.SEQUENTIAL_REFERENCE]
        assert len(seq_issues) >= 1

    def test_run_specific_check(self):
        """Should be able to run sequential reference check specifically."""
        course = self._make_course_with_content(
            "In the last video, we explored functions."
        )

        auditor = CourseAuditor(course)
        result = auditor.run_check(AuditCheckType.SEQUENTIAL_REFERENCE)

        assert AuditCheckType.SEQUENTIAL_REFERENCE.value in result.checks_run
        assert len(result.issues) >= 1
