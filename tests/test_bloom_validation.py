"""Tests for Bloom taxonomy validation in course auditor."""

import pytest
from src.core.models import (
    Course, Module, Lesson, Activity, LearningOutcome,
    ContentType, ActivityType, BloomLevel, AuditCheckType
)
from src.validators.course_auditor import CourseAuditor


class TestBloomProgression:
    """Tests for Bloom level progression validation."""

    def _create_course_with_outcomes(self, bloom_levels):
        """Create a course with learning outcomes at specified Bloom levels."""
        course = Course(
            id="test-course",
            title="Test Course",
            description="Test"
        )

        for i, level in enumerate(bloom_levels):
            course.learning_outcomes.append(
                LearningOutcome(
                    id=f"lo{i+1}",
                    behavior=f"Outcome {i+1}",
                    bloom_level=level
                )
            )

        return course

    def test_good_progression_passes(self):
        """Test that good Bloom progression generates no issues."""
        course = self._create_course_with_outcomes([
            BloomLevel.REMEMBER,
            BloomLevel.UNDERSTAND,
            BloomLevel.APPLY,
            BloomLevel.ANALYZE
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        regression_issues = [i for i in auditor.issues if "regression" in i.title.lower()]
        assert len(regression_issues) == 0

    def test_significant_regression_detected(self):
        """Test that significant regression (2+ levels) is flagged."""
        course = self._create_course_with_outcomes([
            BloomLevel.ANALYZE,
            BloomLevel.REMEMBER  # Drops 3 levels
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        regression_issues = [i for i in auditor.issues if "regression" in i.title.lower()]
        assert len(regression_issues) == 1

    def test_small_regression_allowed(self):
        """Test that small regression (1 level) is allowed."""
        course = self._create_course_with_outcomes([
            BloomLevel.APPLY,
            BloomLevel.UNDERSTAND  # Drops 1 level - OK
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        regression_issues = [i for i in auditor.issues if "regression" in i.title.lower()]
        assert len(regression_issues) == 0

    def test_limited_cognitive_progression_warning(self):
        """Test warning when course doesn't reach APPLY level."""
        course = self._create_course_with_outcomes([
            BloomLevel.REMEMBER,
            BloomLevel.UNDERSTAND
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        limited_issues = [i for i in auditor.issues if "limited cognitive" in i.title.lower()]
        assert len(limited_issues) == 1

    def test_reaching_apply_passes(self):
        """Test that reaching APPLY level passes cognitive check."""
        course = self._create_course_with_outcomes([
            BloomLevel.REMEMBER,
            BloomLevel.APPLY
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        limited_issues = [i for i in auditor.issues if "limited cognitive" in i.title.lower()]
        assert len(limited_issues) == 0

    def test_overall_progression_issue(self):
        """Test detection when course ends at lower level than it starts."""
        course = self._create_course_with_outcomes([
            BloomLevel.ANALYZE,
            BloomLevel.APPLY,
            BloomLevel.UNDERSTAND
        ])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        overall_issues = [i for i in auditor.issues if "overall progression" in i.title.lower()]
        assert len(overall_issues) == 1

    def test_single_outcome_no_issues(self):
        """Test that single outcome generates no progression issues."""
        course = self._create_course_with_outcomes([BloomLevel.APPLY])

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        assert len(auditor.issues) == 0

    def test_no_outcomes_no_issues(self):
        """Test that empty outcomes list generates no issues."""
        course = Course(title="Test", description="Test")

        auditor = CourseAuditor(course)
        auditor.check_bloom_progression()

        assert len(auditor.issues) == 0


class TestActivityBloomAlignment:
    """Tests for activity-outcome Bloom level alignment."""

    def _create_course_with_activity(self, activity_type, bloom_level, content_type=None):
        """Create a course with one activity linked to one outcome."""
        course = Course(
            id="test-course",
            title="Test Course",
            description="Test"
        )

        outcome = LearningOutcome(
            id="lo1",
            behavior="Test outcome",
            bloom_level=bloom_level,
            mapped_activity_ids=["act1"]  # Map outcome to activity
        )
        course.learning_outcomes.append(outcome)

        module = Module(id="mod1", title="Module 1")
        lesson = Lesson(id="les1", title="Lesson 1")

        # Determine content type from activity type if not provided
        if content_type is None:
            if activity_type == ActivityType.READING_MATERIAL:
                content_type = ContentType.READING
            elif activity_type == ActivityType.HANDS_ON_LAB:
                content_type = ContentType.HOL
            else:
                content_type = ContentType.VIDEO

        activity = Activity(
            id="act1",
            title="Test Activity",
            content_type=content_type,
            activity_type=activity_type
        )

        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        return course

    def test_reading_matches_understand(self):
        """Test that reading activity matches UNDERSTAND level."""
        course = self._create_course_with_activity(
            ActivityType.READING_MATERIAL,
            BloomLevel.UNDERSTAND
        )

        auditor = CourseAuditor(course)
        auditor._check_activity_bloom_alignment()

        mismatch_issues = [i for i in auditor.issues if "mismatch" in i.title.lower()]
        assert len(mismatch_issues) == 0

    def test_reading_mismatches_create(self):
        """Test that reading activity doesn't match CREATE level."""
        course = self._create_course_with_activity(
            ActivityType.READING_MATERIAL,
            BloomLevel.CREATE
        )

        auditor = CourseAuditor(course)
        auditor._check_activity_bloom_alignment()

        mismatch_issues = [i for i in auditor.issues if "mismatch" in i.title.lower()]
        assert len(mismatch_issues) == 1

    def test_hol_matches_apply(self):
        """Test that HOL activity matches APPLY level."""
        course = self._create_course_with_activity(
            ActivityType.HANDS_ON_LAB,
            BloomLevel.APPLY
        )

        auditor = CourseAuditor(course)
        auditor._check_activity_bloom_alignment()

        mismatch_issues = [i for i in auditor.issues if "mismatch" in i.title.lower()]
        assert len(mismatch_issues) == 0

    def test_hol_mismatches_remember(self):
        """Test that HOL doesn't flag for REMEMBER (lower level is fine)."""
        course = self._create_course_with_activity(
            ActivityType.HANDS_ON_LAB,
            BloomLevel.REMEMBER
        )

        auditor = CourseAuditor(course)
        auditor._check_activity_bloom_alignment()

        # HOL is fine for lower levels - we only flag when activity is too simple
        mismatch_issues = [i for i in auditor.issues if "mismatch" in i.title.lower()]
        assert len(mismatch_issues) == 0


class TestBloomCheckIntegration:
    """Integration tests for Bloom validation."""

    def test_bloom_progression_in_run_check(self):
        """Test BLOOM_PROGRESSION check can be run individually."""
        course = Course(title="Test", description="Test")
        auditor = CourseAuditor(course)

        result = auditor.run_check(AuditCheckType.BLOOM_PROGRESSION)
        assert "bloom_progression" in result.checks_run

    def test_bloom_in_run_all_checks(self):
        """Test run_all_checks includes Bloom validation."""
        course = Course(title="Test", description="Test")
        auditor = CourseAuditor(course)

        result = auditor.run_all_checks()
        assert "bloom_progression" in result.checks_run

    def test_suggest_activities_for_bloom(self):
        """Test activity suggestion method."""
        course = Course(title="Test", description="Test")
        auditor = CourseAuditor(course)

        create_suggestion = auditor._suggest_activities_for_bloom(BloomLevel.CREATE)
        assert "project" in create_suggestion.lower()

        apply_suggestion = auditor._suggest_activities_for_bloom(BloomLevel.APPLY)
        assert "lab" in apply_suggestion.lower() or "hol" in apply_suggestion.lower()
