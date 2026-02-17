"""Course quality auditor for detecting issues and ensuring consistency.

Performs multiple audit checks on course structure and content:
- Flow analysis: Logical progression through modules/lessons
- Repetition detection: Duplicate or overlapping content
- Objective alignment: Activities map to learning outcomes
- Content gaps: Missing required elements
- Duration balance: Time distribution across modules
- Bloom progression: Cognitive level advancement (supports multiple taxonomies)
"""

from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import re

from src.core.models import (
    Course, Module, Lesson, Activity, LearningOutcome,
    AuditResult, AuditIssue, AuditCheckType, AuditSeverity, AuditIssueStatus,
    ContentType, ActivityType, BloomLevel, BuildState,
    CognitiveTaxonomy, TaxonomyType, TaxonomyLevel
)


class CourseAuditor:
    """Audits course quality and detects issues.

    Run all checks or specific checks to identify issues that need attention
    before publishing. Issues have severity levels and suggested fixes.

    Supports multiple cognitive taxonomies (Bloom's, SOLO, Webb's DOK, etc.)
    via optional taxonomy parameter.
    """

    # Default Bloom's taxonomy levels (used when no taxonomy provided)
    BLOOM_ORDER = [
        BloomLevel.REMEMBER,
        BloomLevel.UNDERSTAND,
        BloomLevel.APPLY,
        BloomLevel.ANALYZE,
        BloomLevel.EVALUATE,
        BloomLevel.CREATE
    ]

    def __init__(self, course: Course, taxonomy: Optional[CognitiveTaxonomy] = None):
        """Initialize auditor with a course to audit.

        Args:
            course: Course object to audit
            taxonomy: Optional taxonomy for cognitive level checks. If None,
                      uses Bloom's taxonomy as default.
        """
        self.course = course
        self.taxonomy = taxonomy
        self.issues: List[AuditIssue] = []

    def _get_cognitive_level(self, item) -> Optional[str]:
        """Get cognitive level from an activity or learning outcome.

        Prefers cognitive_level if set, falls back to bloom_level.value.

        Args:
            item: Activity or LearningOutcome with bloom_level/cognitive_level

        Returns:
            Cognitive level string value or None
        """
        # Prefer explicit cognitive_level
        if hasattr(item, 'cognitive_level') and item.cognitive_level:
            return item.cognitive_level

        # Fall back to bloom_level
        if hasattr(item, 'bloom_level') and item.bloom_level:
            return item.bloom_level.value

        return None

    def _get_level_order(self, level_value: str) -> int:
        """Get the order of a cognitive level.

        Args:
            level_value: The level value string (e.g., "apply", "analyze")

        Returns:
            Order index (0-based), or -1 if not found
        """
        if self.taxonomy:
            return self.taxonomy.get_level_order(level_value)

        # Default to Bloom's ordering
        bloom_value_order = {
            "remember": 0,
            "understand": 1,
            "apply": 2,
            "analyze": 3,
            "evaluate": 4,
            "create": 5
        }
        return bloom_value_order.get(level_value, -1)

    def _get_level_name(self, level_value: str) -> str:
        """Get display name for a cognitive level.

        Args:
            level_value: The level value string

        Returns:
            Display name or the value itself
        """
        if self.taxonomy:
            level = self.taxonomy.get_level(level_value)
            if level:
                return level.name
        return level_value.title()

    def _is_categorical_taxonomy(self) -> bool:
        """Check if the current taxonomy is categorical (non-linear)."""
        if self.taxonomy:
            return self.taxonomy.taxonomy_type == TaxonomyType.CATEGORICAL
        return False

    def _get_higher_order_threshold(self) -> int:
        """Get the threshold for higher-order cognitive levels.

        Returns the minimum level index that must be reached.
        For default Bloom's: 2 (APPLY), meaning course must reach at least APPLY.
        """
        if self.taxonomy:
            return self.taxonomy.higher_order_threshold
        return 2  # Default: must reach APPLY or above for Bloom's

    def _get_activity_compatible_levels(self, activity_type: ActivityType) -> Set[str]:
        """Get compatible cognitive levels for an activity type.

        Args:
            activity_type: The activity type

        Returns:
            Set of compatible level values
        """
        if self.taxonomy:
            for mapping in self.taxonomy.activity_mappings:
                if mapping.activity_type == activity_type:
                    return set(mapping.compatible_levels)
            # No mapping found, return all levels as compatible
            return {level.value for level in self.taxonomy.levels}

        # Default Bloom's mapping
        default_map = {
            ActivityType.READING_MATERIAL: {"remember", "understand"},
            ActivityType.VIDEO_LECTURE: {"remember", "understand", "apply"},
            ActivityType.GRADED_QUIZ: {"remember", "understand", "apply"},
            ActivityType.PRACTICE_QUIZ: {"remember", "understand", "apply"},
            ActivityType.HANDS_ON_LAB: {"apply", "analyze"},
            ActivityType.UNGRADED_LAB: {"apply", "analyze", "create"},
            ActivityType.DISCUSSION_PROMPT: {"analyze", "evaluate"},
            ActivityType.ASSIGNMENT_SUBMISSION: {"apply", "analyze", "evaluate", "create"},
            ActivityType.PROJECT_MILESTONE: {"analyze", "evaluate", "create"},
            ActivityType.COACH_DIALOGUE: {"remember", "understand"},
            ActivityType.SCREENCAST_SIMULATION: {"apply", "analyze"},
        }
        return default_map.get(activity_type, set())

    def run_all_checks(self) -> AuditResult:
        """Run all available audit checks.

        Returns:
            AuditResult with all issues found
        """
        self.issues = []

        # Run each check
        self.check_flow_analysis()
        self.check_repetition()
        self.check_objective_alignment()
        self.check_content_gaps()
        self.check_duration_balance()
        self.check_bloom_progression()
        self.check_sequential_references()  # v1.2.0
        self.check_wwhaa_sequence()  # v1.2.1
        self.check_content_distribution()  # v1.2.1

        return self._build_result([ct.value for ct in AuditCheckType])

    def run_check(self, check_type: AuditCheckType) -> AuditResult:
        """Run a specific audit check.

        Args:
            check_type: Type of check to run

        Returns:
            AuditResult with issues from that check
        """
        self.issues = []

        if check_type == AuditCheckType.FLOW_ANALYSIS:
            self.check_flow_analysis()
        elif check_type == AuditCheckType.REPETITION:
            self.check_repetition()
        elif check_type == AuditCheckType.OBJECTIVE_ALIGNMENT:
            self.check_objective_alignment()
        elif check_type == AuditCheckType.CONTENT_GAPS:
            self.check_content_gaps()
        elif check_type == AuditCheckType.DURATION_BALANCE:
            self.check_duration_balance()
        elif check_type == AuditCheckType.BLOOM_PROGRESSION:
            self.check_bloom_progression()
        elif check_type == AuditCheckType.SEQUENTIAL_REFERENCE:
            self.check_sequential_references()
        elif check_type == AuditCheckType.WWHAA_SEQUENCE:
            self.check_wwhaa_sequence()
        elif check_type == AuditCheckType.CONTENT_DISTRIBUTION:
            self.check_content_distribution()

        return self._build_result([check_type.value])

    def check_flow_analysis(self):
        """Check logical flow and progression through course content."""
        # Check for empty modules
        for module in self.course.modules:
            if not module.lessons:
                self._add_issue(
                    AuditCheckType.FLOW_ANALYSIS,
                    AuditSeverity.ERROR,
                    f"Empty module: {module.title}",
                    "Module has no lessons. Add lessons or remove the module.",
                    [{"type": "module", "id": module.id, "title": module.title}],
                    "Add at least one lesson to this module."
                )
            else:
                # Check for empty lessons
                for lesson in module.lessons:
                    if not lesson.activities:
                        self._add_issue(
                            AuditCheckType.FLOW_ANALYSIS,
                            AuditSeverity.WARNING,
                            f"Empty lesson: {lesson.title}",
                            "Lesson has no activities. Add activities or remove the lesson.",
                            [{"type": "lesson", "id": lesson.id, "title": lesson.title}],
                            "Add at least one activity to this lesson."
                        )

        # Check for prerequisite cycles
        self._check_prerequisite_cycles()

        # Check for orphaned prerequisites
        self._check_orphaned_prerequisites()

    def _check_prerequisite_cycles(self):
        """Detect circular prerequisite dependencies."""
        all_activities = self._get_all_activities()
        activity_map = {a.id: a for a in all_activities}

        def has_cycle(activity_id: str, visited: Set[str], path: Set[str]) -> bool:
            if activity_id in path:
                return True
            if activity_id in visited:
                return False

            visited.add(activity_id)
            path.add(activity_id)

            activity = activity_map.get(activity_id)
            if activity:
                for prereq_id in activity.prerequisite_ids:
                    if has_cycle(prereq_id, visited, path):
                        return True

            path.remove(activity_id)
            return False

        for activity in all_activities:
            if activity.prerequisite_ids:
                if has_cycle(activity.id, set(), set()):
                    self._add_issue(
                        AuditCheckType.FLOW_ANALYSIS,
                        AuditSeverity.ERROR,
                        f"Prerequisite cycle detected",
                        f"Activity '{activity.title}' is part of a circular prerequisite chain.",
                        [{"type": "activity", "id": activity.id, "title": activity.title}],
                        "Remove one of the prerequisites to break the cycle."
                    )

    def _check_orphaned_prerequisites(self):
        """Check for prerequisites referencing non-existent activities."""
        all_activity_ids = {a.id for a in self._get_all_activities()}

        for activity in self._get_all_activities():
            for prereq_id in activity.prerequisite_ids:
                if prereq_id not in all_activity_ids:
                    self._add_issue(
                        AuditCheckType.FLOW_ANALYSIS,
                        AuditSeverity.ERROR,
                        f"Invalid prerequisite reference",
                        f"Activity '{activity.title}' references non-existent prerequisite '{prereq_id}'.",
                        [{"type": "activity", "id": activity.id, "title": activity.title}],
                        "Remove the invalid prerequisite ID."
                    )

    def check_repetition(self):
        """Detect duplicate or highly similar content."""
        all_activities = self._get_all_activities()

        # Check for duplicate titles
        title_counts = Counter(a.title.lower().strip() for a in all_activities)
        for title, count in title_counts.items():
            if count > 1 and title:
                duplicates = [a for a in all_activities if a.title.lower().strip() == title]
                self._add_issue(
                    AuditCheckType.REPETITION,
                    AuditSeverity.WARNING,
                    f"Duplicate activity title: '{duplicates[0].title}'",
                    f"Found {count} activities with the same title.",
                    [{"type": "activity", "id": a.id, "title": a.title} for a in duplicates],
                    "Rename activities to be more specific and unique."
                )

        # Check for similar content (basic keyword overlap)
        self._check_content_similarity(all_activities)

    def _check_content_similarity(self, activities: List[Activity]):
        """Check for content with high keyword overlap."""
        # Only check activities with generated content
        activities_with_content = [a for a in activities if a.content and len(a.content) > 100]

        for i, act1 in enumerate(activities_with_content):
            keywords1 = self._extract_keywords(act1.content)
            for act2 in activities_with_content[i+1:]:
                keywords2 = self._extract_keywords(act2.content)

                if keywords1 and keywords2:
                    overlap = len(keywords1 & keywords2) / min(len(keywords1), len(keywords2))
                    if overlap > 0.7:  # 70% keyword overlap
                        self._add_issue(
                            AuditCheckType.REPETITION,
                            AuditSeverity.INFO,
                            "Similar content detected",
                            f"Activities '{act1.title}' and '{act2.title}' have highly similar content ({int(overlap*100)}% overlap).",
                            [
                                {"type": "activity", "id": act1.id, "title": act1.title},
                                {"type": "activity", "id": act2.id, "title": act2.title}
                            ],
                            "Review both activities to ensure they cover distinct topics."
                        )

    def _extract_keywords(self, content: str) -> Set[str]:
        """Extract significant keywords from content."""
        # Remove common words and extract significant terms
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                     'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                     'very', 'just', 'also', 'now', 'here', 'there', 'when',
                     'where', 'why', 'how', 'all', 'each', 'every', 'both',
                     'few', 'more', 'most', 'other', 'some', 'such', 'no',
                     'any', 'this', 'that', 'these', 'those', 'what', 'which',
                     'who', 'whom', 'whose', 'it', 'its', 'you', 'your', 'we',
                     'our', 'they', 'their', 'i', 'me', 'my', 'he', 'him',
                     'his', 'she', 'her', 'hers'}

        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        return {w for w in words if w not in stopwords}

    def check_objective_alignment(self):
        """Check that activities align with learning outcomes."""
        # Check for unmapped learning outcomes
        for lo in self.course.learning_outcomes:
            if not lo.mapped_activity_ids:
                self._add_issue(
                    AuditCheckType.OBJECTIVE_ALIGNMENT,
                    AuditSeverity.WARNING,
                    f"Unmapped learning outcome",
                    f"Learning outcome '{lo.behavior}' has no mapped activities.",
                    [{"type": "learning_outcome", "id": lo.id, "title": lo.behavior}],
                    "Map this outcome to relevant activities in the course."
                )

        # Check for activities not mapped to any outcome
        all_activities = self._get_all_activities()
        mapped_ids = set()
        for lo in self.course.learning_outcomes:
            mapped_ids.update(lo.mapped_activity_ids)

        # Only flag graded activities without outcomes
        graded_types = {ContentType.QUIZ, ContentType.ASSIGNMENT, ContentType.PROJECT}
        for activity in all_activities:
            if activity.content_type in graded_types and activity.id not in mapped_ids:
                self._add_issue(
                    AuditCheckType.OBJECTIVE_ALIGNMENT,
                    AuditSeverity.INFO,
                    f"Unmapped graded activity",
                    f"Graded activity '{activity.title}' is not mapped to any learning outcome.",
                    [{"type": "activity", "id": activity.id, "title": activity.title}],
                    "Consider mapping this activity to a learning outcome."
                )

    def check_content_gaps(self):
        """Check for missing required content elements."""
        all_activities = self._get_all_activities()

        # Check for activities without generated content
        draft_count = sum(1 for a in all_activities if a.build_state == BuildState.DRAFT)
        if draft_count > 0:
            self._add_issue(
                AuditCheckType.CONTENT_GAPS,
                AuditSeverity.WARNING,
                f"{draft_count} activities without content",
                "Some activities have not been generated yet.",
                [{"type": "activity", "id": a.id, "title": a.title}
                 for a in all_activities if a.build_state == BuildState.DRAFT][:5],  # Limit to 5
                "Generate content for all draft activities."
            )

        # Check for modules without video content
        for module in self.course.modules:
            has_video = False
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.content_type == ContentType.VIDEO:
                        has_video = True
                        break
                if has_video:
                    break

            if not has_video and module.lessons:
                self._add_issue(
                    AuditCheckType.CONTENT_GAPS,
                    AuditSeverity.INFO,
                    f"Module without video content",
                    f"Module '{module.title}' has no video lectures.",
                    [{"type": "module", "id": module.id, "title": module.title}],
                    "Consider adding video content for better engagement."
                )

        # Check for missing practice opportunities
        for module in self.course.modules:
            has_practice = False
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.content_type in {ContentType.QUIZ, ContentType.LAB, ContentType.HOL}:
                        has_practice = True
                        break
                if has_practice:
                    break

            if not has_practice and module.lessons:
                self._add_issue(
                    AuditCheckType.CONTENT_GAPS,
                    AuditSeverity.WARNING,
                    f"Module without practice activities",
                    f"Module '{module.title}' has no quizzes, labs, or hands-on activities.",
                    [{"type": "module", "id": module.id, "title": module.title}],
                    "Add practice activities to reinforce learning."
                )

    def check_duration_balance(self):
        """Check time distribution across modules."""
        if not self.course.modules:
            return

        module_durations = []
        for module in self.course.modules:
            total_duration = 0
            for lesson in module.lessons:
                for activity in lesson.activities:
                    total_duration += activity.estimated_duration_minutes
            module_durations.append((module, total_duration))

        if not module_durations:
            return

        avg_duration = sum(d for _, d in module_durations) / len(module_durations)

        for module, duration in module_durations:
            if avg_duration > 0:
                if duration < avg_duration * 0.3:  # Less than 30% of average
                    self._add_issue(
                        AuditCheckType.DURATION_BALANCE,
                        AuditSeverity.WARNING,
                        f"Short module: {module.title}",
                        f"Module duration ({duration:.0f} min) is much shorter than average ({avg_duration:.0f} min).",
                        [{"type": "module", "id": module.id, "title": module.title}],
                        "Consider expanding this module or merging with another."
                    )
                elif duration > avg_duration * 2.5:  # More than 250% of average
                    self._add_issue(
                        AuditCheckType.DURATION_BALANCE,
                        AuditSeverity.WARNING,
                        f"Long module: {module.title}",
                        f"Module duration ({duration:.0f} min) is much longer than average ({avg_duration:.0f} min).",
                        [{"type": "module", "id": module.id, "title": module.title}],
                        "Consider splitting this module into smaller units."
                    )

    def check_bloom_progression(self):
        """Check that cognitive levels progress appropriately.

        Supports any cognitive taxonomy (Bloom's, SOLO, Webb's, etc.).
        For categorical taxonomies (like Fink's), checks diversity instead of progression.

        Validates:
        1. Learning outcomes progress from lower to higher cognitive levels
        2. No significant regressions (beyond taxonomy's allow_regression_within)
        3. Course reaches higher-order thinking (per taxonomy's higher_order_threshold)
        4. Activities match their associated outcome cognitive levels
        """
        if not self.course.learning_outcomes:
            return

        # For categorical taxonomies, check diversity instead of progression
        if self._is_categorical_taxonomy():
            self._check_categorical_diversity()
            self._check_activity_bloom_alignment()
            return

        # Get cognitive levels in order they appear
        levels_sequence = []
        lo_list = []
        for lo in self.course.learning_outcomes:
            level = self._get_cognitive_level(lo)
            if level:
                levels_sequence.append(level)
                lo_list.append(lo)

        if len(levels_sequence) < 2:
            return

        # Get regression threshold from taxonomy
        allow_regression = 1
        if self.taxonomy:
            allow_regression = self.taxonomy.allow_regression_within

        # Check for significant regression in cognitive levels
        for i in range(1, len(levels_sequence)):
            curr_idx = self._get_level_order(levels_sequence[i])
            prev_idx = self._get_level_order(levels_sequence[i-1])

            # Skip if levels not found in taxonomy
            if curr_idx == -1 or prev_idx == -1:
                continue

            # If we drop more than allowed, flag it
            if prev_idx - curr_idx > allow_regression:
                lo = lo_list[i]
                prev_lo = lo_list[i-1]
                taxonomy_name = self.taxonomy.name if self.taxonomy else "Bloom's"
                self._add_issue(
                    AuditCheckType.BLOOM_PROGRESSION,
                    AuditSeverity.INFO,
                    "Cognitive level regression",
                    f"Learning outcome '{lo.behavior}' ({self._get_level_name(levels_sequence[i])}) is at a lower level than previous outcome '{prev_lo.behavior}' ({self._get_level_name(levels_sequence[i-1])}).",
                    [
                        {"type": "learning_outcome", "id": lo.id, "title": lo.behavior},
                        {"type": "learning_outcome", "id": prev_lo.id, "title": prev_lo.behavior}
                    ],
                    f"Consider reordering outcomes for progressive cognitive challenge ({taxonomy_name})."
                )

        # Check that course reaches higher-order thinking
        # For default Bloom's (no taxonomy), always check; for custom, check if required
        higher_order_threshold = self._get_higher_order_threshold()
        should_check_higher_order = (self.taxonomy is None) or self.taxonomy.require_higher_order
        if should_check_higher_order:
            max_level_idx = max(
                (self._get_level_order(level) for level in levels_sequence if self._get_level_order(level) != -1),
                default=-1
            )
            if max_level_idx != -1 and max_level_idx < higher_order_threshold:
                max_level_name = self._get_level_name(levels_sequence[0])  # First level for display
                for level in levels_sequence:
                    if self._get_level_order(level) == max_level_idx:
                        max_level_name = self._get_level_name(level)
                        break

                higher_levels = []
                if self.taxonomy:
                    higher_levels = [
                        l.name for l in self.taxonomy.levels
                        if l.order >= higher_order_threshold
                    ]

                self._add_issue(
                    AuditCheckType.BLOOM_PROGRESSION,
                    AuditSeverity.WARNING,
                    "Limited cognitive progression",
                    f"Course outcomes only reach '{max_level_name}' level. Consider adding outcomes at higher cognitive levels.",
                    [],
                    f"Add learning outcomes at these levels: {', '.join(higher_levels) if higher_levels else 'higher-order levels'}."
                )

        # Check overall progression (first to last)
        if len(levels_sequence) >= 3:
            first_idx = self._get_level_order(levels_sequence[0])
            last_idx = self._get_level_order(levels_sequence[-1])
            if first_idx != -1 and last_idx != -1 and last_idx < first_idx:
                self._add_issue(
                    AuditCheckType.BLOOM_PROGRESSION,
                    AuditSeverity.INFO,
                    "Overall progression issue",
                    f"Course ends at a lower cognitive level ({self._get_level_name(levels_sequence[-1])}) than it starts ({self._get_level_name(levels_sequence[0])}).",
                    [],
                    "Consider reordering outcomes so the course builds toward higher cognitive demands."
                )

        # Check activity-outcome alignment
        self._check_activity_bloom_alignment()

    def _check_categorical_diversity(self):
        """Check cognitive diversity for categorical taxonomies like Fink's.

        Instead of progression, checks that multiple categories are covered.
        """
        if not self.taxonomy or not self.course.learning_outcomes:
            return

        # Get unique levels used
        levels_used = set()
        for lo in self.course.learning_outcomes:
            level = self._get_cognitive_level(lo)
            if level:
                levels_used.add(level)

        min_unique = self.taxonomy.minimum_unique_levels
        if len(levels_used) < min_unique:
            available_levels = [l.name for l in self.taxonomy.levels]
            self._add_issue(
                AuditCheckType.BLOOM_PROGRESSION,
                AuditSeverity.WARNING,
                "Limited cognitive diversity",
                f"Course uses only {len(levels_used)} of {len(self.taxonomy.levels)} categories in {self.taxonomy.name}.",
                [],
                f"Consider adding outcomes in other categories: {', '.join(available_levels)}."
            )

    def _check_activity_bloom_alignment(self):
        """Check that activity types align with their outcome cognitive levels.

        Uses taxonomy's activity_mappings if available, otherwise falls back
        to default Bloom's mapping.
        """
        # Build reverse lookup: activity_id -> list of learning outcomes
        # (LearningOutcome.mapped_activity_ids holds the activity IDs)
        activity_to_outcomes: Dict[str, List[LearningOutcome]] = {}
        for lo in self.course.learning_outcomes:
            for act_id in lo.mapped_activity_ids:
                if act_id not in activity_to_outcomes:
                    activity_to_outcomes[act_id] = []
                activity_to_outcomes[act_id].append(lo)

        for module in self.course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    linked_outcomes = activity_to_outcomes.get(activity.id, [])
                    if not linked_outcomes:
                        continue

                    for lo in linked_outcomes:
                        lo_level = self._get_cognitive_level(lo)
                        if not lo_level:
                            continue

                        compatible_levels = self._get_activity_compatible_levels(activity.activity_type)
                        if compatible_levels and lo_level not in compatible_levels:
                            # Check if activity is too simple for the outcome
                            lo_idx = self._get_level_order(lo_level)
                            max_activity_idx = max(
                                (self._get_level_order(level) for level in compatible_levels
                                 if self._get_level_order(level) != -1),
                                default=0
                            )

                            if lo_idx != -1 and lo_idx > max_activity_idx:
                                taxonomy_name = self.taxonomy.name if self.taxonomy else "Bloom's"
                                self._add_issue(
                                    AuditCheckType.BLOOM_PROGRESSION,
                                    AuditSeverity.INFO,
                                    "Activity-outcome mismatch",
                                    f"Activity '{activity.title}' ({activity.activity_type.value}) may not adequately address outcome '{lo.behavior}' ({self._get_level_name(lo_level)}). Consider a more challenging activity type.",
                                    [
                                        {"type": "activity", "id": activity.id, "title": activity.title},
                                        {"type": "learning_outcome", "id": lo.id, "title": lo.behavior}
                                    ],
                                    f"For {self._get_level_name(lo_level)}-level outcomes ({taxonomy_name}), consider: {self._suggest_activities_for_level(lo_level)}"
                                )

    def _suggest_activities_for_level(self, level_value: str) -> str:
        """Suggest activity types for a given cognitive level.

        Args:
            level_value: The cognitive level value string

        Returns:
            Suggestion string for appropriate activities
        """
        # If we have a taxonomy, find activities that match this level
        if self.taxonomy:
            matching_activities = []
            for mapping in self.taxonomy.activity_mappings:
                if level_value in mapping.primary_levels:
                    # Convert enum to readable name
                    activity_name = mapping.activity_type.value.replace("_", " ")
                    matching_activities.append(activity_name)
            if matching_activities:
                return ", ".join(matching_activities[:3])

        # Fall back to default Bloom's suggestions
        suggestions = {
            "remember": "readings, videos with recall questions",
            "understand": "videos with explanation, readings with comprehension checks",
            "apply": "hands-on labs, practice quizzes, HOL activities",
            "analyze": "case study discussions, labs with analysis tasks",
            "evaluate": "peer-reviewed discussions, critical analysis assignments",
            "create": "projects, creative assignments, labs with original design"
        }
        return suggestions.get(level_value, "appropriate activities")

    def _suggest_activities_for_bloom(self, bloom_level: BloomLevel) -> str:
        """Suggest activity types for a given Bloom level (backward compat)."""
        return self._suggest_activities_for_level(bloom_level.value)

    # v1.2.0: Sequential reference detection patterns (Coursera v3.0)
    SEQUENTIAL_PATTERNS = [
        r"as we (?:discussed|learned|covered|saw) in (?:module|lesson|video)\s+\d+",
        r"in the previous (?:video|lesson|module|reading)",
        r"in the next (?:video|lesson|module|reading)",
        r"(?:earlier|later) in (?:this|the) (?:course|module|lesson)",
        r"remember (?:from|in) (?:module|lesson|video)\s+\d+",
        r"(?:you|we) (?:saw|learned|covered) (?:earlier|previously|before)",
        r"as (?:mentioned|discussed|covered) (?:earlier|previously)",
        r"building on (?:what we learned|the previous)",
        r"in the last (?:video|lesson|section)",
        r"(?:next|upcoming) (?:video|lesson|module)",
        r"in (?:module|lesson|video|week)\s+\d+",
    ]

    def check_sequential_references(self, forbid: bool = True):
        """Check for forbidden sequential references in content.

        Coursera v3.0 requires content to be standalone - no references
        to specific module/lesson numbers or "previous/next" content.

        Args:
            forbid: If False, skip this check entirely
        """
        if not forbid:
            return

        compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SEQUENTIAL_PATTERNS
        ]

        for activity in self._get_all_activities():
            content = activity.content or ""
            if not content:
                continue

            # Check each pattern
            for pattern in compiled_patterns:
                matches = pattern.findall(content)
                for match in matches:
                    self._add_issue(
                        AuditCheckType.SEQUENTIAL_REFERENCE,
                        AuditSeverity.WARNING,
                        f"Sequential reference in '{activity.title}'",
                        f"Content contains reference to other course items: '{match}'",
                        [{"type": "activity", "id": activity.id, "title": activity.title}],
                        "Remove or rephrase sequential references for standalone viewing."
                    )

    # v1.2.1: WWHAA phase configuration for validation
    WWHAA_PHASES = ["why", "what", "how", "apply", "assess"]
    WWHAA_CONTENT_TYPES = {
        "why": {ContentType.COACH, ContentType.VIDEO},
        "what": {ContentType.VIDEO, ContentType.READING},
        "how": {ContentType.SCREENCAST, ContentType.VIDEO},
        "apply": {ContentType.HOL, ContentType.LAB, ContentType.QUIZ},
        "assess": {ContentType.QUIZ, ContentType.ASSIGNMENT}
    }

    def check_wwhaa_sequence(self):
        """Check that modules follow WHY → WHAT → HOW → APPLY → ASSESS sequence.

        v1.2.1: Validates module structure against WWHAA pedagogy model.
        Each phase should contain appropriate content types.

        Classification is based on content_type (primary) with wwhaa_phase as secondary:
        - WHY: Coach dialogues, Hook phase videos
        - WHAT: Videos, Readings (content delivery)
        - HOW: Screencasts (demonstrations)
        - APPLY: HOL, Labs, Practice Quizzes
        - ASSESS: Graded Quizzes, Assignments
        """
        for module in self.course.modules:
            if not module.lessons:
                continue

            # Get all activities in this module grouped by phase
            phase_activities: Dict[str, List[Activity]] = {phase: [] for phase in self.WWHAA_PHASES}

            for lesson in module.lessons:
                for activity in lesson.activities:
                    # Classify based on content_type first (more reliable)
                    content_type = activity.content_type
                    wwhaa_phase = activity.wwhaa_phase.value.lower()

                    # Determine pedagogical phase based on content type
                    if content_type == ContentType.COACH:
                        phase_name = "why"
                    elif content_type == ContentType.SCREENCAST:
                        phase_name = "how"
                    elif content_type in {ContentType.HOL, ContentType.LAB}:
                        phase_name = "apply"
                    elif content_type == ContentType.QUIZ:
                        # Practice quizzes are APPLY, graded quizzes are ASSESS
                        if activity.activity_type == ActivityType.PRACTICE_QUIZ:
                            phase_name = "apply"
                        else:
                            phase_name = "assess"
                    elif content_type in {ContentType.ASSIGNMENT, ContentType.PROJECT}:
                        phase_name = "assess"
                    elif content_type in {ContentType.VIDEO, ContentType.READING}:
                        # Videos/readings in hook phase count as WHY
                        if wwhaa_phase == "hook":
                            phase_name = "why"
                        else:
                            phase_name = "what"
                    elif content_type == ContentType.DISCUSSION:
                        phase_name = "apply"  # Discussions are application
                    else:
                        phase_name = "what"  # Default fallback

                    phase_activities[phase_name].append(activity)

            # Check for missing essential phases
            essential_phases = ["what", "apply"]  # Minimum required
            for phase in essential_phases:
                if not phase_activities[phase]:
                    self._add_issue(
                        AuditCheckType.WWHAA_SEQUENCE,
                        AuditSeverity.WARNING,
                        f"Missing {phase.upper()} phase in module '{module.title}'",
                        f"Module should include {phase.upper()} activities for complete learning cycle.",
                        [{"type": "module", "id": module.id, "title": module.title}],
                        f"Add {phase.upper()} activities (e.g., {', '.join(ct.value for ct in self.WWHAA_CONTENT_TYPES[phase])})"
                    )

            # Check content type alignment for each phase
            for phase, activities in phase_activities.items():
                expected_types = self.WWHAA_CONTENT_TYPES.get(phase, set())
                for activity in activities:
                    if activity.content_type not in expected_types and expected_types:
                        self._add_issue(
                            AuditCheckType.WWHAA_SEQUENCE,
                            AuditSeverity.INFO,
                            f"Unexpected content type in {phase.upper()} phase",
                            f"Activity '{activity.title}' ({activity.content_type.value}) is not typical for {phase.upper()} phase.",
                            [{"type": "activity", "id": activity.id, "title": activity.title}],
                            f"Consider using: {', '.join(ct.value for ct in expected_types)}"
                        )

    def check_content_distribution(self):
        """Check that content types are balanced across the course.

        v1.2.1: Validates content distribution against target percentages:
        - Videos: ~30%
        - Readings: ~20%
        - HOL/Labs: ~30%
        - Assessments: ~20%
        """
        all_activities = self._get_all_activities()
        if not all_activities:
            return

        total = len(all_activities)

        # Count by category
        video_count = sum(1 for a in all_activities if a.content_type == ContentType.VIDEO)
        reading_count = sum(1 for a in all_activities if a.content_type == ContentType.READING)
        hol_count = sum(1 for a in all_activities if a.content_type in {ContentType.HOL, ContentType.LAB})
        assessment_count = sum(1 for a in all_activities if a.content_type in {ContentType.QUIZ, ContentType.ASSIGNMENT, ContentType.PROJECT})

        # Calculate percentages
        distribution = {
            "video": (video_count / total * 100, 30, 10),      # actual, target, tolerance
            "reading": (reading_count / total * 100, 20, 10),
            "hol": (hol_count / total * 100, 30, 10),
            "assessment": (assessment_count / total * 100, 20, 10),
        }

        for content_type, (actual, target, tolerance) in distribution.items():
            if actual < target - tolerance:
                self._add_issue(
                    AuditCheckType.CONTENT_DISTRIBUTION,
                    AuditSeverity.INFO,
                    f"Low {content_type} content percentage",
                    f"Course has {actual:.0f}% {content_type} content (target: ~{target}%).",
                    [],
                    f"Consider adding more {content_type} activities for better balance."
                )
            elif actual > target + tolerance:
                self._add_issue(
                    AuditCheckType.CONTENT_DISTRIBUTION,
                    AuditSeverity.INFO,
                    f"High {content_type} content percentage",
                    f"Course has {actual:.0f}% {content_type} content (target: ~{target}%).",
                    [],
                    f"Consider reducing {content_type} activities or adding other content types."
                )

    def _get_all_activities(self) -> List[Activity]:
        """Get flat list of all activities in course."""
        activities = []
        for module in self.course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities

    def _add_issue(
        self,
        check_type: AuditCheckType,
        severity: AuditSeverity,
        title: str,
        description: str,
        affected_elements: List[Dict[str, str]],
        suggested_fix: str
    ):
        """Add an issue to the results."""
        self.issues.append(AuditIssue(
            check_type=check_type,
            severity=severity,
            title=title,
            description=description,
            affected_elements=affected_elements,
            suggested_fix=suggested_fix,
            status=AuditIssueStatus.OPEN
        ))

    def _build_result(self, checks_run: List[str]) -> AuditResult:
        """Build final audit result from collected issues."""
        error_count = sum(1 for i in self.issues if i.severity == AuditSeverity.ERROR)
        warning_count = sum(1 for i in self.issues if i.severity == AuditSeverity.WARNING)
        info_count = sum(1 for i in self.issues if i.severity == AuditSeverity.INFO)

        # Calculate score: start at 100, subtract for issues
        score = 100
        score -= error_count * 15    # Errors are severe
        score -= warning_count * 5   # Warnings are moderate
        score -= info_count * 1      # Info is minor
        score = max(0, min(100, score))  # Clamp to 0-100

        return AuditResult(
            issues=self.issues,
            checks_run=checks_run,
            score=score,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count
        )
