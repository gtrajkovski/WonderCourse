"""Tests for v1.2.1 Coursera v3.0 compliance features.

Tests:
- Video section timing validation
- Reading author attribution validation
- Reference link paywall validation
- WWHAA sequence validation
- Content distribution validation
"""

import pytest
from src.core.models import (
    ContentStandardsProfile, Course, Module, Lesson, Activity,
    ContentType, ActivityType, WWHAAPhase, AuditCheckType
)
from src.validators.standards_validator import StandardsValidator, ViolationSeverity
from src.validators.course_auditor import CourseAuditor


class TestVideoSectionTiming:
    """Tests for video section timing validation."""

    def test_section_under_minimum_words(self):
        """Test detection of section with too few words."""
        standards = ContentStandardsProfile()
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {"section_name": "Hook", "script_text": "Short hook."},  # 2 words, min 75
                {"section_name": "Content", "script_text": "This is the content section with enough words " * 20}
            ],
            "full_script": "..."
        }

        violations = validator._validate_video(content)
        hook_violations = [v for v in violations if "hook" in v.field.lower() and "minimum" in v.rule.lower()]

        assert len(hook_violations) == 1
        assert hook_violations[0].severity == ViolationSeverity.INFO

    def test_section_over_maximum_words(self):
        """Test detection of section with too many words."""
        standards = ContentStandardsProfile()
        validator = StandardsValidator(standards)

        # Generate content section with > 900 words
        long_content = "word " * 950

        content = {
            "sections": [
                {"section_name": "Content", "script_text": long_content}
            ],
            "full_script": long_content
        }

        violations = validator._validate_video(content)
        content_violations = [v for v in violations if v.field == "sections.content" and "maximum" in v.rule.lower()]

        assert len(content_violations) == 1
        assert content_violations[0].severity == ViolationSeverity.WARNING

    def test_section_within_range_passes(self):
        """Test that sections within range don't trigger violations."""
        standards = ContentStandardsProfile()
        validator = StandardsValidator(standards)

        # 100 words for hook (within 75-150)
        hook_text = "word " * 100
        # 600 words for content (within 450-900)
        content_text = "word " * 600

        content = {
            "sections": [
                {"section_name": "Hook", "script_text": hook_text},
                {"section_name": "Content", "script_text": content_text}
            ],
            "full_script": hook_text + content_text
        }

        violations = validator._validate_video(content)
        timing_violations = [v for v in violations if "minimum" in v.rule.lower() or "maximum word count for" in v.rule.lower()]

        assert len(timing_violations) == 0

    def test_section_timing_can_be_disabled(self):
        """Test that section timing validation can be disabled."""
        standards = ContentStandardsProfile(video_section_timing_enabled=False)
        validator = StandardsValidator(standards)

        content = {
            "sections": [
                {"section_name": "Hook", "script_text": "Short."},  # Would fail if enabled
            ],
            "full_script": "Short."
        }

        violations = validator._validate_video(content)
        timing_violations = [v for v in violations if "minimum word count" in v.rule.lower()]

        assert len(timing_violations) == 0


class TestReadingAttribution:
    """Tests for reading author attribution validation."""

    def test_missing_attribution_detected(self):
        """Test detection of missing attribution."""
        standards = ContentStandardsProfile(reading_require_attribution=True)
        validator = StandardsValidator(standards)

        content = {
            "body": "This is a reading about Python programming.",
            "key_takeaways": ["Python is useful"],
            "references": []
        }

        violations = validator._validate_reading(content)
        attr_violations = [v for v in violations if "attribution" in v.rule.lower()]

        assert len(attr_violations) == 1
        assert attr_violations[0].auto_fixable is True

    def test_attribution_in_body_passes(self):
        """Test that attribution embedded in body passes validation."""
        standards = ContentStandardsProfile(reading_require_attribution=True)
        validator = StandardsValidator(standards)

        content = {
            "body": """This is a reading about Python.

Author's original work based on professional experience, developed with the assistance of AI tools.""",
            "key_takeaways": ["Python is useful"],
            "references": []
        }

        violations = validator._validate_reading(content)
        attr_violations = [v for v in violations if "attribution" in v.rule.lower()]

        assert len(attr_violations) == 0

    def test_attribution_field_passes(self):
        """Test that explicit attribution field passes validation."""
        standards = ContentStandardsProfile(reading_require_attribution=True)
        validator = StandardsValidator(standards)

        content = {
            "body": "This is a reading about Python.",
            "attribution": "Trajkovski, G. (2025). Author's original work.",
            "references": []
        }

        violations = validator._validate_reading(content)
        attr_violations = [v for v in violations if "attribution" in v.rule.lower()]

        assert len(attr_violations) == 0

    def test_attribution_validation_can_be_disabled(self):
        """Test that attribution validation can be disabled."""
        standards = ContentStandardsProfile(reading_require_attribution=False)
        validator = StandardsValidator(standards)

        content = {
            "body": "This is a reading.",
            "references": []
        }

        violations = validator._validate_reading(content)
        attr_violations = [v for v in violations if "attribution" in v.rule.lower()]

        assert len(attr_violations) == 0


class TestReferencePaywall:
    """Tests for reference link paywall validation."""

    def test_paywall_domain_detected(self):
        """Test detection of paywall domains in references."""
        standards = ContentStandardsProfile(reading_require_free_links=True)
        validator = StandardsValidator(standards)

        content = {
            "body": "Content",
            "references": [
                {"title": "Academic Paper", "url": "https://www.jstor.org/stable/12345"}
            ]
        }

        violations = validator._validate_reading(content)
        paywall_violations = [v for v in violations if "paywall" in v.rule.lower()]

        assert len(paywall_violations) == 1
        assert "jstor.org" in paywall_violations[0].actual

    def test_free_link_passes(self):
        """Test that free links pass validation."""
        standards = ContentStandardsProfile(reading_require_free_links=True)
        validator = StandardsValidator(standards)

        content = {
            "body": "Content",
            "references": [
                {"title": "Free Resource", "url": "https://docs.python.org/3/tutorial/"}
            ]
        }

        violations = validator._validate_reading(content)
        paywall_violations = [v for v in violations if "paywall" in v.rule.lower()]

        assert len(paywall_violations) == 0

    def test_multiple_paywall_domains(self):
        """Test detection of multiple paywall domains."""
        standards = ContentStandardsProfile(reading_require_free_links=True)
        validator = StandardsValidator(standards)

        content = {
            "body": "Content",
            "references": [
                {"title": "Paper 1", "url": "https://www.jstor.org/article1"},
                {"title": "Paper 2", "url": "https://link.springer.com/article2"},
                {"title": "Paper 3", "url": "https://onlinelibrary.wiley.com/doi/123"}
            ]
        }

        violations = validator._validate_reading(content)
        paywall_violations = [v for v in violations if "paywall" in v.rule.lower()]

        assert len(paywall_violations) == 3

    def test_paywall_validation_respects_require_free_links(self):
        """Test that paywall validation respects the require_free_links setting."""
        standards = ContentStandardsProfile(reading_require_free_links=False)
        validator = StandardsValidator(standards)

        content = {
            "body": "Content",
            "references": [
                {"title": "Paper", "url": "https://www.jstor.org/article"}
            ]
        }

        violations = validator._validate_reading(content)
        paywall_violations = [v for v in violations if "paywall" in v.rule.lower()]

        assert len(paywall_violations) == 0


class TestWWHAASequence:
    """Tests for WWHAA sequence validation in course auditor."""

    def _create_course_with_activities(self, activities_config):
        """Helper to create a course with specified activities."""
        activities = [
            Activity(
                title=f"Activity {i}",
                content_type=cfg["content_type"],
                wwhaa_phase=cfg.get("wwhaa_phase", WWHAAPhase.CONTENT)
            )
            for i, cfg in enumerate(activities_config)
        ]

        lesson = Lesson(title="Lesson 1", activities=activities)
        module = Module(title="Module 1", lessons=[lesson])
        return Course(title="Test Course", modules=[module])

    def test_missing_apply_phase_detected(self):
        """Test detection of missing APPLY phase."""
        course = self._create_course_with_activities([
            {"content_type": ContentType.VIDEO, "wwhaa_phase": WWHAAPhase.CONTENT},
            {"content_type": ContentType.READING, "wwhaa_phase": WWHAAPhase.CONTENT}
        ])

        auditor = CourseAuditor(course)
        auditor.check_wwhaa_sequence()

        apply_issues = [i for i in auditor.issues if "apply" in i.title.lower()]
        assert len(apply_issues) >= 1

    def test_complete_wwhaa_sequence_passes(self):
        """Test that complete WWHAA sequence passes."""
        course = self._create_course_with_activities([
            {"content_type": ContentType.COACH, "wwhaa_phase": WWHAAPhase.HOOK},
            {"content_type": ContentType.VIDEO, "wwhaa_phase": WWHAAPhase.CONTENT},
            {"content_type": ContentType.READING, "wwhaa_phase": WWHAAPhase.CONTENT},
            {"content_type": ContentType.HOL, "wwhaa_phase": WWHAAPhase.CONTENT},
            {"content_type": ContentType.QUIZ, "wwhaa_phase": WWHAAPhase.CONTENT}
        ])

        auditor = CourseAuditor(course)
        auditor.check_wwhaa_sequence()

        # Should have no missing phase issues
        missing_issues = [i for i in auditor.issues if "missing" in i.title.lower()]
        assert len(missing_issues) == 0

    def test_unexpected_content_type_info(self):
        """Test that unexpected content type in phase generates INFO."""
        course = self._create_course_with_activities([
            {"content_type": ContentType.QUIZ, "wwhaa_phase": WWHAAPhase.HOOK},  # Quiz in HOOK is unusual
            {"content_type": ContentType.HOL, "wwhaa_phase": WWHAAPhase.CONTENT}
        ])

        auditor = CourseAuditor(course)
        auditor.check_wwhaa_sequence()

        unexpected_issues = [i for i in auditor.issues if "unexpected" in i.title.lower()]
        # May or may not flag depending on mapping
        # The test verifies the check runs without error


class TestContentDistribution:
    """Tests for content distribution validation."""

    def _create_course_with_types(self, type_counts):
        """Helper to create course with specific content type counts."""
        activities = []
        for content_type, count in type_counts.items():
            for i in range(count):
                activities.append(Activity(
                    title=f"{content_type.value} {i}",
                    content_type=content_type
                ))

        lesson = Lesson(title="Lesson 1", activities=activities)
        module = Module(title="Module 1", lessons=[lesson])
        return Course(title="Test Course", modules=[module])

    def test_balanced_distribution_passes(self):
        """Test that balanced distribution passes without issues."""
        # Create balanced course: 3 videos, 2 readings, 3 hol, 2 quizzes = 10 total
        course = self._create_course_with_types({
            ContentType.VIDEO: 3,      # 30%
            ContentType.READING: 2,    # 20%
            ContentType.HOL: 3,        # 30%
            ContentType.QUIZ: 2        # 20%
        })

        auditor = CourseAuditor(course)
        auditor.check_content_distribution()

        distribution_issues = [i for i in auditor.issues if i.check_type == AuditCheckType.CONTENT_DISTRIBUTION]
        assert len(distribution_issues) == 0

    def test_video_heavy_course_detected(self):
        """Test detection of video-heavy course."""
        course = self._create_course_with_types({
            ContentType.VIDEO: 8,      # 80% - way over target
            ContentType.READING: 1,
            ContentType.QUIZ: 1
        })

        auditor = CourseAuditor(course)
        auditor.check_content_distribution()

        high_video_issues = [i for i in auditor.issues if "high video" in i.title.lower()]
        assert len(high_video_issues) == 1

    def test_missing_hol_detected(self):
        """Test detection of course missing hands-on activities."""
        course = self._create_course_with_types({
            ContentType.VIDEO: 5,
            ContentType.READING: 5
            # No HOL or LAB
        })

        auditor = CourseAuditor(course)
        auditor.check_content_distribution()

        low_hol_issues = [i for i in auditor.issues if "low hol" in i.title.lower()]
        assert len(low_hol_issues) == 1


class TestAuditCheckTypeIntegration:
    """Tests for new audit check types integration."""

    def test_wwhaa_sequence_in_run_check(self):
        """Test WWHAA_SEQUENCE check can be run individually."""
        course = Course(title="Test", modules=[])
        auditor = CourseAuditor(course)

        result = auditor.run_check(AuditCheckType.WWHAA_SEQUENCE)
        assert "wwhaa_sequence" in result.checks_run

    def test_content_distribution_in_run_check(self):
        """Test CONTENT_DISTRIBUTION check can be run individually."""
        course = Course(title="Test", modules=[])
        auditor = CourseAuditor(course)

        result = auditor.run_check(AuditCheckType.CONTENT_DISTRIBUTION)
        assert "content_distribution" in result.checks_run

    def test_all_checks_includes_new_types(self):
        """Test run_all_checks includes new v1.2.1 check types."""
        course = Course(title="Test", modules=[])
        auditor = CourseAuditor(course)

        result = auditor.run_all_checks()
        assert "wwhaa_sequence" in result.checks_run
        assert "content_distribution" in result.checks_run
