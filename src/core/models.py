"""Core data models for Course Builder Studio.

All dataclasses support to_dict() -> dict and from_dict(dict) -> instance
round-trips with schema evolution support.
"""

from dataclasses import dataclass, field, fields
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


# ===========================
# Enums
# ===========================


class ContentType(Enum):
    """Content type categorization for activities."""

    VIDEO = "video"
    READING = "reading"
    QUIZ = "quiz"
    HOL = "hol"
    COACH = "coach"
    LAB = "lab"
    DISCUSSION = "discussion"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    RUBRIC = "rubric"
    SCREENCAST = "screencast"


class ActivityType(Enum):
    """Specific activity type within content categories."""

    GRADED_QUIZ = "graded_quiz"
    PRACTICE_QUIZ = "practice_quiz"
    UNGRADED_LAB = "ungraded_lab"
    PEER_REVIEW = "peer_review"
    DISCUSSION_PROMPT = "discussion_prompt"
    HANDS_ON_LAB = "hands_on_lab"
    COACH_DIALOGUE = "coach_dialogue"
    VIDEO_LECTURE = "video_lecture"
    READING_MATERIAL = "reading_material"
    ASSIGNMENT_SUBMISSION = "assignment_submission"
    PROJECT_MILESTONE = "project_milestone"
    SCREENCAST_SIMULATION = "screencast_simulation"


class BuildState(Enum):
    """Build/generation state of content."""

    DRAFT = "draft"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"


class BloomLevel(Enum):
    """Bloom's Taxonomy cognitive levels."""

    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class WWHAAPhase(Enum):
    """WWHAA script structure phases (Coursera pedagogy)."""

    HOOK = "hook"
    OBJECTIVE = "objective"
    CONTENT = "content"
    IVQ = "ivq"
    SUMMARY = "summary"
    CTA = "cta"


class FlowMode(Enum):
    """Course/module navigation flow mode."""

    SEQUENTIAL = "sequential"  # Must complete activities in order
    OPEN = "open"              # Access any activity anytime


class PageType(Enum):
    """Types of auto-generated course pages."""

    SYLLABUS = "syllabus"      # Course schedule, objectives, grading
    ABOUT = "about"            # Course description, prerequisites, audience
    RESOURCES = "resources"    # Tools, technologies, additional materials


class AuditCheckType(Enum):
    """Types of audit checks performed on a course."""

    FLOW_ANALYSIS = "flow_analysis"           # Logical progression through content
    REPETITION = "repetition"                 # Duplicate or overlapping content
    OBJECTIVE_ALIGNMENT = "objective_alignment"  # Activities map to learning outcomes
    BLUEPRINT_COMPLIANCE = "blueprint_compliance"  # Structure matches blueprint
    CONTENT_GAPS = "content_gaps"             # Missing required content
    DURATION_BALANCE = "duration_balance"     # Time distribution across modules
    BLOOM_PROGRESSION = "bloom_progression"   # Cognitive level progression
    SEQUENTIAL_REFERENCE = "sequential_reference"  # v1.2.0: References to other content
    WWHAA_SEQUENCE = "wwhaa_sequence"         # v1.2.1: WWHAA phase sequence validation
    CONTENT_DISTRIBUTION = "content_distribution"  # v1.2.1: Content type balance


class AuditSeverity(Enum):
    """Severity levels for audit issues."""

    ERROR = "error"      # Must fix before publishing
    WARNING = "warning"  # Should fix, but not blocking
    INFO = "info"        # Suggestion for improvement


class AuditIssueStatus(Enum):
    """Status of an audit issue."""

    OPEN = "open"           # Not yet addressed
    IN_PROGRESS = "in_progress"  # Being worked on
    RESOLVED = "resolved"   # Fixed
    WONT_FIX = "wont_fix"   # Acknowledged but not fixing
    FALSE_POSITIVE = "false_positive"  # Not actually an issue


class TaxonomyType(str, Enum):
    """Type of cognitive taxonomy structure."""

    LINEAR = "linear"           # Levels are ordered progressively (Bloom, SOLO, Webb, Marzano)
    CATEGORICAL = "categorical"  # Levels are independent categories (Fink)


class VariantType(str, Enum):
    """Content representation variants for UDL (Universal Design for Learning)."""

    PRIMARY = "primary"           # Original/main content
    AUDIO_ONLY = "audio_only"     # Audio version (video/reading → audio)
    TRANSCRIPT = "transcript"      # Text transcript of video
    ILLUSTRATED = "illustrated"    # Visual summary with illustrations
    INFOGRAPHIC = "infographic"    # Infographic version of reading
    GUIDED = "guided"             # Guided walkthrough (HOL)
    CHALLENGE = "challenge"        # Challenge mode (minimal guidance)
    SELF_CHECK = "self_check"      # Self-assessment version of quiz


class DepthLevel(str, Enum):
    """Content complexity depth levels."""

    ESSENTIAL = "essential"   # Key points only, minimal examples
    STANDARD = "standard"     # Full explanations, 2-3 examples (default)
    ADVANCED = "advanced"     # Extended theory, edge cases, research links


# ===========================
# Dataclasses
# ===========================


@dataclass
class CompletionCriteria:
    """Defines what "complete" means for an activity.

    Different content types have different completion rules:
    - Video: watched X% of duration
    - Reading: scrolled to bottom / spent time on page
    - Quiz: submitted with passing score
    - HOL/Assignment: submitted for grading
    - Discussion: posted response
    """

    # Video completion
    video_watch_percent: int = 90  # Must watch X% to complete

    # Reading completion
    reading_scroll_to_bottom: bool = True
    reading_min_time_seconds: int = 30  # Minimum time on page

    # Quiz completion
    quiz_must_submit: bool = True
    quiz_passing_score_percent: Optional[int] = None  # None = any score passes
    quiz_max_attempts: Optional[int] = None  # None = unlimited

    # Practice Quiz completion (usually just attempt required)
    practice_quiz_must_attempt: bool = True

    # HOL/Assignment/Project completion
    submission_required: bool = True

    # Discussion completion
    discussion_must_post: bool = True
    discussion_min_word_count: int = 50

    # Coach dialogue completion
    coach_must_complete_dialogue: bool = True

    # Lab completion
    lab_must_complete_exercises: bool = True
    lab_min_exercises_completed: Optional[int] = None  # None = all exercises

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "video_watch_percent": self.video_watch_percent,
            "reading_scroll_to_bottom": self.reading_scroll_to_bottom,
            "reading_min_time_seconds": self.reading_min_time_seconds,
            "quiz_must_submit": self.quiz_must_submit,
            "quiz_passing_score_percent": self.quiz_passing_score_percent,
            "quiz_max_attempts": self.quiz_max_attempts,
            "practice_quiz_must_attempt": self.practice_quiz_must_attempt,
            "submission_required": self.submission_required,
            "discussion_must_post": self.discussion_must_post,
            "discussion_min_word_count": self.discussion_min_word_count,
            "coach_must_complete_dialogue": self.coach_must_complete_dialogue,
            "lab_must_complete_exercises": self.lab_must_complete_exercises,
            "lab_min_exercises_completed": self.lab_min_exercises_completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletionCriteria":
        """Deserialize from dictionary with schema evolution support."""
        if data is None:
            return cls()
        data = dict(data)  # Defensive copy

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class ContentVariant:
    """A content variant representing the same learning material in a different format.

    ContentVariants enable Universal Design for Learning (UDL) by providing
    multiple representations of the same activity content, and support depth
    layers for different complexity levels.
    """

    id: str = field(default_factory=lambda: f"var_{uuid.uuid4().hex[:8]}")
    variant_type: VariantType = VariantType.PRIMARY
    depth_level: DepthLevel = DepthLevel.STANDARD

    # Content storage (same pattern as Activity.content)
    content: str = ""  # JSON serialized Pydantic schema
    build_state: BuildState = BuildState.DRAFT

    # Metadata
    word_count: int = 0
    estimated_duration_minutes: float = 0.0

    # Generation tracking
    generated_from_variant_id: Optional[str] = None  # Source variant if derived

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "variant_type": self.variant_type.value if isinstance(self.variant_type, VariantType) else self.variant_type,
            "depth_level": self.depth_level.value if isinstance(self.depth_level, DepthLevel) else self.depth_level,
            "content": self.content,
            "build_state": self.build_state.value if isinstance(self.build_state, BuildState) else self.build_state,
            "word_count": self.word_count,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "generated_from_variant_id": self.generated_from_variant_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentVariant":
        """Deserialize with schema evolution support."""
        if data is None:
            return cls()
        data = dict(data)

        # Deserialize enums
        if "variant_type" in data and isinstance(data["variant_type"], str):
            try:
                data["variant_type"] = VariantType(data["variant_type"])
            except ValueError:
                data["variant_type"] = VariantType.PRIMARY

        if "depth_level" in data and isinstance(data["depth_level"], str):
            try:
                data["depth_level"] = DepthLevel(data["depth_level"])
            except ValueError:
                data["depth_level"] = DepthLevel.STANDARD

        if "build_state" in data and isinstance(data["build_state"], str):
            try:
                data["build_state"] = BuildState(data["build_state"])
            except ValueError:
                data["build_state"] = BuildState.DRAFT

        # Filter to known fields
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class TaxonomyLevel:
    """A single level within a cognitive taxonomy.

    Each level has a name, description, order (for linear taxonomies),
    and associated verb patterns for detection.
    """

    id: str = field(default_factory=lambda: f"tl_{uuid.uuid4().hex[:8]}")
    name: str = ""                          # e.g., "Remember", "Apply"
    value: str = ""                         # Lowercase identifier: "remember", "apply"
    description: str = ""                   # Detailed description of this level
    order: int = 0                          # Position in sequence (1-based for linear)
    example_verbs: List[str] = field(default_factory=list)  # ["define", "list", "recall"]
    color: str = "#808080"                  # UI display color

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "order": self.order,
            "example_verbs": self.example_verbs,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaxonomyLevel":
        """Deserialize from dictionary."""
        data = dict(data)
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ActivityLevelMapping:
    """Defines which taxonomy levels are appropriate for each activity type.

    Maps activity types to compatible cognitive levels.
    """

    activity_type: ActivityType = ActivityType.VIDEO_LECTURE
    compatible_levels: List[str] = field(default_factory=list)  # Level value strings
    primary_levels: List[str] = field(default_factory=list)     # Most common/expected

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "activity_type": self.activity_type.value,
            "compatible_levels": self.compatible_levels,
            "primary_levels": self.primary_levels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLevelMapping":
        """Deserialize from dictionary."""
        data = dict(data)
        if "activity_type" in data and isinstance(data["activity_type"], str):
            try:
                data["activity_type"] = ActivityType(data["activity_type"])
            except ValueError:
                data["activity_type"] = ActivityType.VIDEO_LECTURE
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class CognitiveTaxonomy:
    """A complete cognitive taxonomy definition.

    System presets (Bloom, SOLO, etc.) cannot be modified but can be duplicated.
    Custom taxonomies can be freely edited.
    """

    id: str = field(default_factory=lambda: f"tax_{uuid.uuid4().hex[:8]}")
    name: str = "Custom Taxonomy"
    description: str = ""
    taxonomy_type: TaxonomyType = TaxonomyType.LINEAR
    is_system_preset: bool = False

    # Ordered list of levels
    levels: List[TaxonomyLevel] = field(default_factory=list)

    # Activity-level mappings (optional - uses defaults if not specified)
    activity_mappings: List[ActivityLevelMapping] = field(default_factory=list)

    # Validation settings
    require_progression: bool = True          # For linear: lower to higher
    allow_regression_within: int = 1          # Allow N levels regression
    minimum_unique_levels: int = 2            # Minimum diversity
    require_higher_order: bool = True         # Must include upper levels
    higher_order_threshold: int = 3           # Levels >= this are "higher order"

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_level(self, value: str) -> Optional[TaxonomyLevel]:
        """Get level by value string."""
        for level in self.levels:
            if level.value == value:
                return level
        return None

    def get_level_order(self, value: str) -> int:
        """Get the order index for a level value."""
        level = self.get_level(value)
        return level.order if level else 0

    def get_ordered_levels(self) -> List[TaxonomyLevel]:
        """Return levels sorted by order."""
        return sorted(self.levels, key=lambda l: l.order)

    def get_higher_order_levels(self) -> List[TaxonomyLevel]:
        """Return levels considered 'higher order'."""
        return [l for l in self.levels if l.order >= self.higher_order_threshold]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "taxonomy_type": self.taxonomy_type.value if isinstance(self.taxonomy_type, TaxonomyType) else self.taxonomy_type,
            "is_system_preset": self.is_system_preset,
            "levels": [l.to_dict() for l in self.levels],
            "activity_mappings": [m.to_dict() for m in self.activity_mappings],
            "require_progression": self.require_progression,
            "allow_regression_within": self.allow_regression_within,
            "minimum_unique_levels": self.minimum_unique_levels,
            "require_higher_order": self.require_higher_order,
            "higher_order_threshold": self.higher_order_threshold,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveTaxonomy":
        """Deserialize from dictionary."""
        data = dict(data)

        # Pop nested objects
        levels_data = data.pop("levels", [])
        mappings_data = data.pop("activity_mappings", [])

        # Deserialize enum
        if "taxonomy_type" in data and isinstance(data["taxonomy_type"], str):
            try:
                data["taxonomy_type"] = TaxonomyType(data["taxonomy_type"])
            except ValueError:
                data["taxonomy_type"] = TaxonomyType.LINEAR

        # Filter to known fields
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}

        taxonomy = cls(**filtered)
        taxonomy.levels = [TaxonomyLevel.from_dict(l) for l in levels_data]
        taxonomy.activity_mappings = [ActivityLevelMapping.from_dict(m) for m in mappings_data]

        return taxonomy

    def to_prompt_context(self) -> str:
        """Generate prompt context for AI content generation."""
        parts = [f"**Cognitive Taxonomy: {self.name}**"]
        parts.append(f"\n{self.description}")
        parts.append(f"\n**Taxonomy Type:** {self.taxonomy_type.value if isinstance(self.taxonomy_type, TaxonomyType) else self.taxonomy_type}")
        parts.append("\n**Levels (in order):**")

        for level in self.get_ordered_levels():
            verbs_str = ", ".join(level.example_verbs[:5]) if level.example_verbs else "N/A"
            parts.append(f"- {level.order}. **{level.name}**: {level.description}")
            parts.append(f"  Example verbs: {verbs_str}")

        if self.taxonomy_type == TaxonomyType.LINEAR:
            parts.append(f"\n**Progression:** Content should progress from lower to higher levels.")
        else:
            parts.append(f"\n**Structure:** Levels are independent categories, not a progression.")

        return "\n".join(parts)


@dataclass
class CoursePage:
    """Auto-generated course page (syllabus, about, resources).

    These pages are generated from course metadata and structure,
    providing consistent documentation for learners.
    """

    id: str = field(default_factory=lambda: f"page_{uuid.uuid4().hex[:8]}")
    page_type: PageType = PageType.ABOUT
    title: str = ""
    content: str = ""  # Markdown content
    sections: List[Dict[str, str]] = field(default_factory=list)  # [{title, content}]
    build_state: BuildState = BuildState.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "page_type": self.page_type.value,
            "title": self.title,
            "content": self.content,
            "sections": self.sections,
            "build_state": self.build_state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoursePage":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Deserialize enums
        if "page_type" in data and isinstance(data["page_type"], str):
            try:
                data["page_type"] = PageType(data["page_type"])
            except ValueError:
                data["page_type"] = PageType.ABOUT

        if "build_state" in data and isinstance(data["build_state"], str):
            try:
                data["build_state"] = BuildState(data["build_state"])
            except ValueError:
                data["build_state"] = BuildState.DRAFT

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class AuditIssue:
    """A single issue found during course audit.

    Tracks the issue type, severity, affected elements, and resolution status.
    """

    id: str = field(default_factory=lambda: f"issue_{uuid.uuid4().hex[:8]}")
    check_type: AuditCheckType = AuditCheckType.CONTENT_GAPS
    severity: AuditSeverity = AuditSeverity.WARNING
    title: str = ""
    description: str = ""
    affected_elements: List[Dict[str, str]] = field(default_factory=list)  # [{type, id, title}]
    suggested_fix: str = ""
    status: AuditIssueStatus = AuditIssueStatus.OPEN
    resolution_notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "check_type": self.check_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_elements": self.affected_elements,
            "suggested_fix": self.suggested_fix,
            "status": self.status.value,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditIssue":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Deserialize enums
        if "check_type" in data and isinstance(data["check_type"], str):
            try:
                data["check_type"] = AuditCheckType(data["check_type"])
            except ValueError:
                data["check_type"] = AuditCheckType.CONTENT_GAPS

        if "severity" in data and isinstance(data["severity"], str):
            try:
                data["severity"] = AuditSeverity(data["severity"])
            except ValueError:
                data["severity"] = AuditSeverity.WARNING

        if "status" in data and isinstance(data["status"], str):
            try:
                data["status"] = AuditIssueStatus(data["status"])
            except ValueError:
                data["status"] = AuditIssueStatus.OPEN

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class AuditResult:
    """Results of a course audit run.

    Contains all issues found, summary statistics, and audit metadata.
    """

    id: str = field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:8]}")
    issues: List[AuditIssue] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)  # List of AuditCheckType values
    score: int = 100  # Overall score 0-100
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "issues": [issue.to_dict() for issue in self.issues],
            "checks_run": self.checks_run,
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditResult":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Pop and deserialize nested issues
        issues_data = data.pop("issues", [])

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        result = cls(**filtered)
        result.issues = [AuditIssue.from_dict(i) for i in issues_data]

        return result


@dataclass
class DeveloperNote:
    """Internal note for content authors.

    Developer notes are visible in the studio but excluded from learner exports.
    They serve as TODOs, reminders, or internal documentation.
    """

    id: str = field(default_factory=lambda: f"note_{uuid.uuid4().hex[:8]}")
    content: str = ""
    author_id: int = 0
    author_name: str = ""
    pinned: bool = False  # Pinned notes sort to top
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "pinned": self.pinned,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeveloperNote":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class Activity:
    """Atomic content unit within a lesson.

    Activities are the smallest unit of content generation. They map to
    specific learning objectives and have a defined content type and
    activity type for platform delivery.
    """

    id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    title: str = ""
    content_type: ContentType = ContentType.VIDEO
    activity_type: ActivityType = ActivityType.VIDEO_LECTURE
    wwhaa_phase: WWHAAPhase = WWHAAPhase.CONTENT
    content: str = ""
    build_state: BuildState = BuildState.DRAFT
    word_count: int = 0
    estimated_duration_minutes: float = 0.0
    bloom_level: Optional[BloomLevel] = None
    cognitive_level: Optional[str] = None  # Dynamic level value from any taxonomy
    order: int = 0
    prerequisite_ids: List[str] = field(default_factory=list)  # Activity IDs that must be completed first
    completion_criteria: Optional[CompletionCriteria] = None  # Custom completion rules (None = use defaults)
    developer_notes: List["DeveloperNote"] = field(default_factory=list)  # Internal author notes
    versions: List[Dict[str, Any]] = field(default_factory=list)  # Named version snapshots
    metadata: Dict[str, Any] = field(default_factory=dict)
    # UDL content variants (empty = no variants, backward compatible)
    content_variants: List[ContentVariant] = field(default_factory=list)
    default_depth_level: Optional[DepthLevel] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_variant(
        self,
        variant_type: VariantType = VariantType.PRIMARY,
        depth_level: DepthLevel = DepthLevel.STANDARD
    ) -> Optional[ContentVariant]:
        """Get specific variant by type and depth.

        For PRIMARY + STANDARD, returns a virtual ContentVariant wrapping
        self.content for API consistency.
        """
        # Primary + Standard is stored in main content field
        if variant_type == VariantType.PRIMARY and depth_level == DepthLevel.STANDARD:
            return ContentVariant(
                id=f"{self.id}_primary_standard",
                variant_type=VariantType.PRIMARY,
                depth_level=DepthLevel.STANDARD,
                content=self.content,
                build_state=self.build_state,
                word_count=self.word_count,
                estimated_duration_minutes=self.estimated_duration_minutes,
            )

        # Search content_variants
        for variant in self.content_variants:
            if variant.variant_type == variant_type and variant.depth_level == depth_level:
                return variant
        return None

    def get_available_variants(self) -> List[tuple]:
        """List all variants and their generation status.

        Returns:
            List of (variant_type, depth_level, build_state) tuples.
        """
        result = [(VariantType.PRIMARY, DepthLevel.STANDARD, self.build_state)]
        for variant in self.content_variants:
            result.append((variant.variant_type, variant.depth_level, variant.build_state))
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with enum values as strings."""
        return {
            "id": self.id,
            "title": self.title,
            "content_type": self.content_type.value,
            "activity_type": self.activity_type.value,
            "wwhaa_phase": self.wwhaa_phase.value,
            "content": self.content,
            "build_state": self.build_state.value,
            "word_count": self.word_count,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "bloom_level": self.bloom_level.value if self.bloom_level else None,
            "cognitive_level": self.cognitive_level,
            "order": self.order,
            "prerequisite_ids": self.prerequisite_ids,
            "completion_criteria": self.completion_criteria.to_dict() if self.completion_criteria else None,
            "developer_notes": [note.to_dict() for note in self.developer_notes],
            "versions": self.versions,
            "metadata": self.metadata,
            "content_variants": [v.to_dict() for v in self.content_variants],
            "default_depth_level": self.default_depth_level.value if self.default_depth_level else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Activity":
        """Deserialize from dictionary with schema evolution support.

        Unknown fields are ignored to support adding new fields in future versions.
        Invalid enum values fall back to first enum value.
        """
        data = dict(data)  # Defensive copy

        # Deserialize enums from strings
        if "content_type" in data and isinstance(data["content_type"], str):
            try:
                data["content_type"] = ContentType(data["content_type"])
            except ValueError:
                data["content_type"] = ContentType.VIDEO

        if "activity_type" in data and isinstance(data["activity_type"], str):
            try:
                data["activity_type"] = ActivityType(data["activity_type"])
            except ValueError:
                data["activity_type"] = ActivityType.VIDEO_LECTURE

        if "wwhaa_phase" in data and isinstance(data["wwhaa_phase"], str):
            try:
                data["wwhaa_phase"] = WWHAAPhase(data["wwhaa_phase"])
            except ValueError:
                data["wwhaa_phase"] = WWHAAPhase.CONTENT

        if "build_state" in data and isinstance(data["build_state"], str):
            try:
                data["build_state"] = BuildState(data["build_state"])
            except ValueError:
                data["build_state"] = BuildState.DRAFT

        if "bloom_level" in data and data["bloom_level"] is not None:
            if isinstance(data["bloom_level"], str):
                try:
                    data["bloom_level"] = BloomLevel(data["bloom_level"])
                except ValueError:
                    data["bloom_level"] = None

        # Deserialize completion_criteria if present
        if "completion_criteria" in data and data["completion_criteria"] is not None:
            if isinstance(data["completion_criteria"], dict):
                data["completion_criteria"] = CompletionCriteria.from_dict(data["completion_criteria"])

        # Deserialize default_depth_level if present
        if "default_depth_level" in data and data["default_depth_level"] is not None:
            if isinstance(data["default_depth_level"], str):
                try:
                    data["default_depth_level"] = DepthLevel(data["default_depth_level"])
                except ValueError:
                    data["default_depth_level"] = None

        # Pop and deserialize developer_notes and content_variants
        developer_notes_data = data.pop("developer_notes", [])
        content_variants_data = data.pop("content_variants", [])

        # Filter to only known fields for schema evolution
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        activity = cls(**filtered)
        activity.developer_notes = [DeveloperNote.from_dict(n) for n in developer_notes_data]
        activity.content_variants = [ContentVariant.from_dict(v) for v in content_variants_data]

        return activity


@dataclass
class Lesson:
    """Container for related activities within a module.

    Lessons group activities around a cohesive learning objective or topic.
    """

    id: str = field(default_factory=lambda: f"les_{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    activities: List[Activity] = field(default_factory=list)
    developer_notes: List[DeveloperNote] = field(default_factory=list)  # Internal author notes
    order: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with recursive activity serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "activities": [activity.to_dict() for activity in self.activities],
            "developer_notes": [note.to_dict() for note in self.developer_notes],
            "order": self.order,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        """Deserialize from dictionary with recursive activity deserialization."""
        data = dict(data)  # Defensive copy

        # Pop and deserialize nested objects
        activities_data = data.pop("activities", [])
        developer_notes_data = data.pop("developer_notes", [])

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        lesson = cls(**filtered)
        lesson.activities = [Activity.from_dict(a) for a in activities_data]
        lesson.developer_notes = [DeveloperNote.from_dict(n) for n in developer_notes_data]

        return lesson


@dataclass
class Module:
    """Container for related lessons within a course.

    Modules represent major course units or themes, typically 1-2 weeks of content.
    """

    id: str = field(default_factory=lambda: f"mod_{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    lessons: List[Lesson] = field(default_factory=list)
    developer_notes: List[DeveloperNote] = field(default_factory=list)  # Internal author notes
    flow_mode: FlowMode = FlowMode.SEQUENTIAL  # Module-level navigation mode
    order: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with recursive lesson serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "lessons": [lesson.to_dict() for lesson in self.lessons],
            "developer_notes": [note.to_dict() for note in self.developer_notes],
            "flow_mode": self.flow_mode.value,
            "order": self.order,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Module":
        """Deserialize from dictionary with recursive lesson deserialization."""
        data = dict(data)  # Defensive copy

        # Pop and deserialize nested objects
        lessons_data = data.pop("lessons", [])
        developer_notes_data = data.pop("developer_notes", [])

        # Deserialize flow_mode enum
        if "flow_mode" in data and isinstance(data["flow_mode"], str):
            try:
                data["flow_mode"] = FlowMode(data["flow_mode"])
            except ValueError:
                data["flow_mode"] = FlowMode.SEQUENTIAL

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        module = cls(**filtered)
        module.lessons = [Lesson.from_dict(lesson) for lesson in lessons_data]
        module.developer_notes = [DeveloperNote.from_dict(n) for n in developer_notes_data]

        return module


@dataclass
class LearningOutcome:
    """Learning outcome with Bloom's taxonomy and ABCD components.

    Uses the ABCD model:
    - Audience: Who will achieve the outcome
    - Behavior: What they will be able to do
    - Condition: Under what circumstances
    - Degree: To what standard/level of proficiency
    """

    id: str = field(default_factory=lambda: f"lo_{uuid.uuid4().hex[:8]}")
    audience: str = ""
    behavior: str = ""
    condition: str = ""
    degree: str = ""
    bloom_level: BloomLevel = BloomLevel.APPLY
    cognitive_level: Optional[str] = None  # Dynamic level value from any taxonomy
    tags: List[str] = field(default_factory=list)
    mapped_activity_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with enum value as string."""
        return {
            "id": self.id,
            "audience": self.audience,
            "behavior": self.behavior,
            "condition": self.condition,
            "degree": self.degree,
            "bloom_level": self.bloom_level.value,
            "cognitive_level": self.cognitive_level,
            "tags": self.tags,
            "mapped_activity_ids": self.mapped_activity_ids,
        }

    def get_effective_audience(self, default_audience: str = "Learners") -> str:
        """Get the effective audience, using default if not specified.

        Learning outcomes can inherit a default audience from the course level,
        reducing repetitive entry of the same audience for each objective.

        Args:
            default_audience: Default audience to use if self.audience is empty.
                              Typically passed from Course.default_audience.

        Returns:
            The outcome's audience if set, otherwise the default.
        """
        return self.audience if self.audience else default_audience

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningOutcome":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Deserialize bloom_level enum
        if "bloom_level" in data and isinstance(data["bloom_level"], str):
            try:
                data["bloom_level"] = BloomLevel(data["bloom_level"])
            except ValueError:
                data["bloom_level"] = BloomLevel.APPLY

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class TextbookChapter:
    """Textbook-style chapter with sections and glossary.

    Provides supplemental reading material organized into sections.
    Includes glossary terms for key concepts.
    """

    id: str = field(default_factory=lambda: f"ch_{uuid.uuid4().hex[:8]}")
    title: str = ""
    sections: List[Dict[str, str]] = field(default_factory=list)
    glossary_terms: List[Dict[str, str]] = field(default_factory=list)
    word_count: int = 0
    learning_outcome_id: Optional[str] = None
    image_placeholders: List[Dict[str, str]] = field(default_factory=list)
    references: List[Dict[str, str]] = field(default_factory=list)
    coherence_issues: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "sections": self.sections,
            "glossary_terms": self.glossary_terms,
            "word_count": self.word_count,
            "learning_outcome_id": self.learning_outcome_id,
            "image_placeholders": self.image_placeholders,
            "references": self.references,
            "coherence_issues": self.coherence_issues,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextbookChapter":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


@dataclass
class ContentStandardsProfile:
    """Configurable content standards profile.

    Defines all content rules, constraints, and formatting requirements.
    Coursera ships as a built-in preset; designers can create custom profiles.
    """

    id: str = field(default_factory=lambda: f"std_{uuid.uuid4().hex[:8]}")
    name: str = "Custom Profile"
    description: str = ""
    is_system_preset: bool = False

    # Video standards
    video_max_duration_min: int = 10
    video_ideal_min_duration: int = 3
    video_ideal_max_duration: int = 7
    video_structure: List[str] = field(default_factory=lambda: [
        "Hook", "Objective", "Content", "IVQ", "Summary", "CTA"
    ])
    video_structure_required: bool = True
    video_wpm: int = 150  # Words per minute for duration calculation

    # CTA validation (v1.2.0 - Coursera v3.0)
    video_cta_max_words: int = 35
    video_cta_forbid_activity_previews: bool = True
    video_cta_forbidden_phrases: List[str] = field(default_factory=lambda: [
        "next you'll", "upcoming", "in the next", "following activity",
        "coach dialogue", "graded assessment", "final quiz", "next video",
        "next lesson", "next module", "practice quiz", "hands-on lab"
    ])

    # Video section timing validation (v1.2.1 - Coursera v3.0)
    video_section_timing_enabled: bool = True
    video_section_word_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "hook": {"min": 75, "max": 150},
        "objective": {"min": 75, "max": 112},
        "content": {"min": 450, "max": 900},
        "ivq": {"min": 75, "max": 150},
        "summary": {"min": 75, "max": 112},
        "cta": {"min": 37, "max": 75}
    })

    # Visual cue validation (v1.3.0 - Coursera v3.0)
    video_visual_cue_enabled: bool = True
    video_visual_cue_interval_seconds: int = 75  # Visual cue every 60-90 seconds (use 75 as midpoint)
    video_visual_cue_pattern: str = r"\[(?:Talking head|B-roll|Screen recording|Animation|Graphic):[^\]]+\]"

    # Reading standards
    reading_max_words: int = 1200
    reading_min_references: int = 3
    reading_max_references: int = 4
    reading_reference_format: str = "apa7"  # apa7|mla9|chicago|ieee|none
    reading_require_free_links: bool = True
    reading_max_optional: int = 4

    # Reading attribution validation (v1.2.1 - Coursera v3.0)
    reading_require_attribution: bool = True
    reading_attribution_template: str = "{author} ({year}). Author's original work based on professional experience, developed with the assistance of AI tools (Claude AI)."

    # Reference link validation (v1.2.1 - Coursera v3.0)
    reading_paywall_domains: List[str] = field(default_factory=lambda: [
        "jstor.org", "sciencedirect.com", "springer.com", "springerlink.com",
        "wiley.com", "onlinelibrary.wiley.com", "tandfonline.com",
        "nature.com", "ieee.org", "ieeexplore.ieee.org", "acm.org",
        "dl.acm.org", "elsevier.com", "sagepub.com", "oxfordjournals.org",
        "cambridge.org", "emerald.com", "taylorfrancis.com"
    ])

    # HOL (Hands-On Learning) standards
    hol_rubric_criteria_count: int = 3
    hol_rubric_total_points: int = 15
    hol_rubric_levels: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"name": "Advanced", "points": 5},
        {"name": "Intermediate", "points": 4},
        {"name": "Beginner", "points": 2}
    ])
    hol_submission_format: str = ".txt"  # .txt|.pdf|.docx|.zip|any
    hol_max_word_count: int = 150

    # Quiz/Assessment standards
    quiz_options_per_question: int = 4
    quiz_require_per_option_feedback: bool = True
    quiz_require_balanced_distribution: bool = True
    quiz_min_distribution_percent: int = 15  # v1.2.0: Minimum per answer letter
    quiz_max_distribution_skew_percent: int = 35
    quiz_allow_multiple_correct: bool = True
    quiz_allow_scenario_based: bool = True
    quiz_time_per_question_min: float = 1.5  # Minutes per question

    # Practice Quiz standards (formative assessment)
    practice_quiz_require_hints: bool = True
    practice_quiz_require_explanations: bool = True

    # Coach/Dialogue standards
    coach_evaluation_levels: List[str] = field(default_factory=lambda: [
        "Advanced", "Intermediate", "Beginner"
    ])
    coach_require_example_responses: bool = True
    coach_require_scenario: bool = True

    # Lab standards
    lab_min_exercises: int = 3
    lab_max_exercises: int = 8
    lab_require_setup_steps: bool = True

    # Discussion standards
    discussion_min_facilitation_questions: int = 3
    discussion_max_facilitation_questions: int = 5
    discussion_require_engagement_hooks: bool = True

    # Assignment standards
    assignment_min_deliverables: int = 1
    assignment_max_deliverables: int = 5
    assignment_min_grading_criteria: int = 3
    assignment_max_grading_criteria: int = 6

    # Project milestone standards
    project_milestone_types: List[str] = field(default_factory=lambda: ["A1", "A2", "A3"])
    project_min_deliverables: int = 2
    project_max_deliverables: int = 5

    # Rubric standards
    rubric_min_criteria: int = 3
    rubric_max_criteria: int = 6
    rubric_levels: List[str] = field(default_factory=lambda: [
        "Below Expectations", "Meets Expectations", "Exceeds Expectations"
    ])

    # Course structure standards
    course_flow_model: str = "WWHAA"  # WWHAA|ADDIE|SAM|custom
    course_min_modules: int = 2
    course_max_modules: int = 3
    course_min_duration_min: int = 30
    course_max_duration_min: int = 180
    course_min_learning_objectives: int = 1
    course_max_learning_objectives: int = 3
    course_min_items: int = 12
    course_max_items: int = 18
    forbid_sequential_references: bool = True

    # Content distribution validation (v1.2.1 - Coursera v3.0)
    content_distribution_enabled: bool = True
    content_distribution_targets: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "video": {"target": 30, "tolerance": 10},    # ~30% ±10%
        "reading": {"target": 20, "tolerance": 10},  # ~20% ±10%
        "hol": {"target": 30, "tolerance": 10},      # ~30% ±10% (includes labs, HOL)
        "assessment": {"target": 20, "tolerance": 10}  # ~20% ±10% (quizzes, assignments)
    })

    # WWHAA sequence validation (v1.2.1 - Coursera v3.0)
    wwhaa_sequence_enabled: bool = True
    wwhaa_phase_config: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "why": {"order": 1, "content_types": ["coach", "video"], "min_duration": 5, "max_duration": 15},
        "what": {"order": 2, "content_types": ["video", "reading"], "min_duration": 10, "max_duration": 20},
        "how": {"order": 3, "content_types": ["screencast", "video"], "min_duration": 15, "max_duration": 20},
        "apply": {"order": 4, "content_types": ["hol", "lab", "quiz"], "min_duration": 20, "max_duration": 30},
        "assess": {"order": 5, "content_types": ["quiz", "assignment"], "min_duration": 10, "max_duration": 20}
    })

    # Tone & voice standards
    tone_description: str = "Conversational but professional. Like a knowledgeable colleague, not a textbook."
    tone_allow_first_person: bool = True
    tone_require_active_voice: bool = True
    tone_require_concrete_examples: bool = True
    tone_custom_guidelines: str = ""

    # Attribution
    author_attribution: str = ""
    require_attribution: bool = True

    # Accessibility
    accessibility_standard: str = "WCAG_2.2_AA"  # WCAG_2.2_AA|WCAG_2.1_AA|Section508|none
    require_alt_text: bool = True
    require_captions: bool = True

    # Humanization settings
    enable_auto_humanize: bool = True  # Auto-humanize generated content
    humanize_em_dashes: bool = True  # Replace em-dashes with commas/periods
    humanize_formal_vocabulary: bool = True  # Replace formal words with plain alternatives
    humanize_adjective_lists: bool = True  # Reduce three-adjective lists
    humanize_ai_transitions: bool = True  # Remove AI transition phrases
    humanize_filler_phrases: bool = True  # Remove filler phrases and intensifiers
    humanization_score_threshold: int = 70  # Minimum acceptable humanization score

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_system_preset": self.is_system_preset,
            "video_max_duration_min": self.video_max_duration_min,
            "video_ideal_min_duration": self.video_ideal_min_duration,
            "video_ideal_max_duration": self.video_ideal_max_duration,
            "video_structure": self.video_structure,
            "video_structure_required": self.video_structure_required,
            "video_wpm": self.video_wpm,
            "video_cta_max_words": self.video_cta_max_words,
            "video_cta_forbid_activity_previews": self.video_cta_forbid_activity_previews,
            "video_cta_forbidden_phrases": self.video_cta_forbidden_phrases,
            "video_section_timing_enabled": self.video_section_timing_enabled,
            "video_section_word_counts": self.video_section_word_counts,
            "video_visual_cue_enabled": self.video_visual_cue_enabled,
            "video_visual_cue_interval_seconds": self.video_visual_cue_interval_seconds,
            "video_visual_cue_pattern": self.video_visual_cue_pattern,
            "reading_max_words": self.reading_max_words,
            "reading_min_references": self.reading_min_references,
            "reading_max_references": self.reading_max_references,
            "reading_reference_format": self.reading_reference_format,
            "reading_require_free_links": self.reading_require_free_links,
            "reading_max_optional": self.reading_max_optional,
            "reading_require_attribution": self.reading_require_attribution,
            "reading_attribution_template": self.reading_attribution_template,
            "reading_paywall_domains": self.reading_paywall_domains,
            "hol_rubric_criteria_count": self.hol_rubric_criteria_count,
            "hol_rubric_total_points": self.hol_rubric_total_points,
            "hol_rubric_levels": self.hol_rubric_levels,
            "hol_submission_format": self.hol_submission_format,
            "hol_max_word_count": self.hol_max_word_count,
            "quiz_options_per_question": self.quiz_options_per_question,
            "quiz_require_per_option_feedback": self.quiz_require_per_option_feedback,
            "quiz_require_balanced_distribution": self.quiz_require_balanced_distribution,
            "quiz_min_distribution_percent": self.quiz_min_distribution_percent,
            "quiz_max_distribution_skew_percent": self.quiz_max_distribution_skew_percent,
            "quiz_allow_multiple_correct": self.quiz_allow_multiple_correct,
            "quiz_allow_scenario_based": self.quiz_allow_scenario_based,
            "quiz_time_per_question_min": self.quiz_time_per_question_min,
            "practice_quiz_require_hints": self.practice_quiz_require_hints,
            "practice_quiz_require_explanations": self.practice_quiz_require_explanations,
            "coach_evaluation_levels": self.coach_evaluation_levels,
            "coach_require_example_responses": self.coach_require_example_responses,
            "coach_require_scenario": self.coach_require_scenario,
            "lab_min_exercises": self.lab_min_exercises,
            "lab_max_exercises": self.lab_max_exercises,
            "lab_require_setup_steps": self.lab_require_setup_steps,
            "discussion_min_facilitation_questions": self.discussion_min_facilitation_questions,
            "discussion_max_facilitation_questions": self.discussion_max_facilitation_questions,
            "discussion_require_engagement_hooks": self.discussion_require_engagement_hooks,
            "assignment_min_deliverables": self.assignment_min_deliverables,
            "assignment_max_deliverables": self.assignment_max_deliverables,
            "assignment_min_grading_criteria": self.assignment_min_grading_criteria,
            "assignment_max_grading_criteria": self.assignment_max_grading_criteria,
            "project_milestone_types": self.project_milestone_types,
            "project_min_deliverables": self.project_min_deliverables,
            "project_max_deliverables": self.project_max_deliverables,
            "rubric_min_criteria": self.rubric_min_criteria,
            "rubric_max_criteria": self.rubric_max_criteria,
            "rubric_levels": self.rubric_levels,
            "course_flow_model": self.course_flow_model,
            "course_min_modules": self.course_min_modules,
            "course_max_modules": self.course_max_modules,
            "course_min_duration_min": self.course_min_duration_min,
            "course_max_duration_min": self.course_max_duration_min,
            "course_min_learning_objectives": self.course_min_learning_objectives,
            "course_max_learning_objectives": self.course_max_learning_objectives,
            "course_min_items": self.course_min_items,
            "course_max_items": self.course_max_items,
            "forbid_sequential_references": self.forbid_sequential_references,
            "content_distribution_enabled": self.content_distribution_enabled,
            "content_distribution_targets": self.content_distribution_targets,
            "wwhaa_sequence_enabled": self.wwhaa_sequence_enabled,
            "wwhaa_phase_config": self.wwhaa_phase_config,
            "tone_description": self.tone_description,
            "tone_allow_first_person": self.tone_allow_first_person,
            "tone_require_active_voice": self.tone_require_active_voice,
            "tone_require_concrete_examples": self.tone_require_concrete_examples,
            "tone_custom_guidelines": self.tone_custom_guidelines,
            "author_attribution": self.author_attribution,
            "require_attribution": self.require_attribution,
            "accessibility_standard": self.accessibility_standard,
            "require_alt_text": self.require_alt_text,
            "require_captions": self.require_captions,
            "enable_auto_humanize": self.enable_auto_humanize,
            "humanize_em_dashes": self.humanize_em_dashes,
            "humanize_formal_vocabulary": self.humanize_formal_vocabulary,
            "humanize_adjective_lists": self.humanize_adjective_lists,
            "humanize_ai_transitions": self.humanize_ai_transitions,
            "humanize_filler_phrases": self.humanize_filler_phrases,
            "humanization_score_threshold": self.humanization_score_threshold,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentStandardsProfile":
        """Deserialize from dictionary with schema evolution support."""
        data = dict(data)  # Defensive copy

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)


# Learning preference options
class LearningPreference(str, Enum):
    """Learning style preferences."""
    VISUAL = "visual"           # Prefers diagrams, videos, charts
    HANDS_ON = "hands_on"       # Prefers practical exercises
    READING = "reading"         # Prefers text-based content
    AUDITORY = "auditory"       # Prefers listening/lectures
    MIXED = "mixed"             # No strong preference


class TechnicalLevel(str, Enum):
    """Technical proficiency levels."""
    NON_TECHNICAL = "non_technical"    # No coding/technical background
    BASIC = "basic"                    # Basic computer skills
    INTERMEDIATE = "intermediate"      # Some programming/tech experience
    ADVANCED = "advanced"              # Strong technical background
    EXPERT = "expert"                  # Deep technical expertise


class LanguageProficiency(str, Enum):
    """Language proficiency levels."""
    NATIVE = "native"              # Native speaker
    FLUENT = "fluent"              # Near-native fluency
    PROFICIENT = "proficient"      # Strong working proficiency
    INTERMEDIATE = "intermediate"  # Basic working proficiency
    BEGINNER = "beginner"          # Limited proficiency


class LearningContext(str, Enum):
    """Learning context/environment."""
    ACADEMIC = "academic"           # University/college student
    PROFESSIONAL = "professional"   # Working professional
    CAREER_CHANGE = "career_change" # Transitioning careers
    UPSKILLING = "upskilling"       # Current role enhancement
    HOBBY = "hobby"                 # Personal interest
    CERTIFICATION = "certification" # Preparing for certification


@dataclass
class LearnerProfile:
    """Detailed learner characteristics that influence content generation.

    Profiles describe the target audience's background, skills, preferences,
    and constraints. This information helps tailor content complexity,
    pacing, examples, and vocabulary.
    """

    id: str = field(default_factory=lambda: f"lp_{uuid.uuid4().hex[:12]}")
    name: str = "Default Learner"
    description: str = ""

    # Background & Skills
    prior_knowledge: List[str] = field(default_factory=list)  # e.g., ["Python basics", "SQL"]
    prerequisites: List[str] = field(default_factory=list)     # Required knowledge
    technical_level: TechnicalLevel = TechnicalLevel.INTERMEDIATE
    industry_background: Optional[str] = None  # e.g., "Healthcare", "Finance"

    # Language & Communication
    language_proficiency: LanguageProficiency = LanguageProficiency.NATIVE
    preferred_language: str = "English"
    jargon_familiarity: List[str] = field(default_factory=list)  # Domain terms they know

    # Learning Style
    learning_preference: LearningPreference = LearningPreference.MIXED
    attention_span_minutes: int = 15  # Optimal segment length
    prefers_examples: bool = True
    prefers_analogies: bool = True

    # Context & Constraints
    learning_context: LearningContext = LearningContext.PROFESSIONAL
    available_hours_per_week: int = 5
    has_time_constraints: bool = False
    completion_deadline: Optional[str] = None  # ISO date string

    # Accessibility
    accessibility_needs: List[str] = field(default_factory=list)  # e.g., ["screen_reader", "captions"]
    color_blind_friendly: bool = False
    large_text_needed: bool = False

    # Goals
    learning_goals: List[str] = field(default_factory=list)  # What they want to achieve
    certification_goal: bool = False

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prior_knowledge": self.prior_knowledge,
            "prerequisites": self.prerequisites,
            "technical_level": self.technical_level.value if isinstance(self.technical_level, TechnicalLevel) else self.technical_level,
            "industry_background": self.industry_background,
            "language_proficiency": self.language_proficiency.value if isinstance(self.language_proficiency, LanguageProficiency) else self.language_proficiency,
            "preferred_language": self.preferred_language,
            "jargon_familiarity": self.jargon_familiarity,
            "learning_preference": self.learning_preference.value if isinstance(self.learning_preference, LearningPreference) else self.learning_preference,
            "attention_span_minutes": self.attention_span_minutes,
            "prefers_examples": self.prefers_examples,
            "prefers_analogies": self.prefers_analogies,
            "learning_context": self.learning_context.value if isinstance(self.learning_context, LearningContext) else self.learning_context,
            "available_hours_per_week": self.available_hours_per_week,
            "has_time_constraints": self.has_time_constraints,
            "completion_deadline": self.completion_deadline,
            "accessibility_needs": self.accessibility_needs,
            "color_blind_friendly": self.color_blind_friendly,
            "large_text_needed": self.large_text_needed,
            "learning_goals": self.learning_goals,
            "certification_goal": self.certification_goal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnerProfile":
        """Deserialize from dictionary."""
        data = dict(data)

        # Convert enum strings to enums
        if "technical_level" in data and isinstance(data["technical_level"], str):
            data["technical_level"] = TechnicalLevel(data["technical_level"])
        if "language_proficiency" in data and isinstance(data["language_proficiency"], str):
            data["language_proficiency"] = LanguageProficiency(data["language_proficiency"])
        if "learning_preference" in data and isinstance(data["learning_preference"], str):
            data["learning_preference"] = LearningPreference(data["learning_preference"])
        if "learning_context" in data and isinstance(data["learning_context"], str):
            data["learning_context"] = LearningContext(data["learning_context"])

        # Filter to known fields
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}

        return cls(**filtered)

    def to_prompt_context(self) -> str:
        """Generate prompt context string for AI content generation.

        Returns:
            Formatted string describing the learner for use in prompts.
        """
        parts = [f"**Target Learner Profile: {self.name}**"]

        if self.description:
            parts.append(f"\n{self.description}")

        # Technical level
        parts.append(f"\n- Technical level: {self.technical_level.value.replace('_', ' ')}")

        # Prior knowledge
        if self.prior_knowledge:
            parts.append(f"- Prior knowledge: {', '.join(self.prior_knowledge)}")

        # Language
        if self.language_proficiency != LanguageProficiency.NATIVE:
            parts.append(f"- Language proficiency: {self.language_proficiency.value} English speaker")

        # Learning style
        if self.learning_preference != LearningPreference.MIXED:
            parts.append(f"- Learning preference: {self.learning_preference.value.replace('_', '-')} learner")

        # Context
        parts.append(f"- Learning context: {self.learning_context.value.replace('_', ' ')}")

        # Attention span
        parts.append(f"- Optimal content segment: {self.attention_span_minutes} minutes")

        # Preferences
        prefs = []
        if self.prefers_examples:
            prefs.append("practical examples")
        if self.prefers_analogies:
            prefs.append("relatable analogies")
        if prefs:
            parts.append(f"- Prefers: {', '.join(prefs)}")

        # Goals
        if self.learning_goals:
            parts.append(f"- Learning goals: {', '.join(self.learning_goals)}")

        # Accessibility
        if self.accessibility_needs:
            parts.append(f"- Accessibility needs: {', '.join(self.accessibility_needs)}")

        return "\n".join(parts)


# Duration presets for course configuration
DURATION_PRESETS = {
    "mini": {"minutes": 30, "label": "30 min (Mini Course)", "description": "Brief introduction or single topic"},
    "short": {"minutes": 60, "label": "60 min (Short Course)", "description": "Standard short course"},
    "standard": {"minutes": 90, "label": "90 min (Standard)", "description": "Comprehensive single topic"},
    "extended": {"minutes": 120, "label": "120 min (Extended)", "description": "Multi-topic coverage"},
    "comprehensive": {"minutes": 180, "label": "180 min (Comprehensive)", "description": "Full curriculum"},
}


@dataclass
class Course:
    """Root container for entire course structure.

    Contains all modules, learning outcomes, and textbook chapters.
    Provides metadata for course-level configuration.
    """

    id: str = field(default_factory=lambda: f"course_{uuid.uuid4().hex[:12]}")
    title: str = "Untitled Course"
    description: str = ""
    target_learner_description: str = ""  # Learner segment description for deriving audience level
    audience_level: str = "intermediate"  # beginner, intermediate, advanced - inferred from learner description
    default_audience: str = "Learners"  # Default audience for learning outcomes (ABCD model)
    target_duration_minutes: int = 60
    modality: str = "online"
    language: str = "English"
    flow_mode: FlowMode = FlowMode.SEQUENTIAL  # Course-level navigation mode
    prerequisites: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    grading_policy: Optional[str] = None
    standards_profile_id: Optional[str] = None  # References ContentStandardsProfile
    learner_profile_id: Optional[str] = None     # References LearnerProfile
    taxonomy_id: Optional[str] = None            # References CognitiveTaxonomy
    modules: List[Module] = field(default_factory=list)
    learning_outcomes: List[LearningOutcome] = field(default_factory=list)
    textbook_chapters: List[TextbookChapter] = field(default_factory=list)
    course_pages: List[CoursePage] = field(default_factory=list)
    audit_results: List[AuditResult] = field(default_factory=list)
    developer_notes: List[DeveloperNote] = field(default_factory=list)  # Course-level author notes
    transcripts: List[Dict[str, Any]] = field(default_factory=list)  # Coaching session transcripts
    accepted_blueprint: Optional[Dict[str, Any]] = None  # Stored blueprint after acceptance
    schema_version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with recursive serialization of all nested objects."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_learner_description": self.target_learner_description,
            "audience_level": self.audience_level,
            "default_audience": self.default_audience,
            "target_duration_minutes": self.target_duration_minutes,
            "modality": self.modality,
            "language": self.language,
            "flow_mode": self.flow_mode.value,
            "prerequisites": self.prerequisites,
            "tools": self.tools,
            "grading_policy": self.grading_policy,
            "standards_profile_id": self.standards_profile_id,
            "learner_profile_id": self.learner_profile_id,
            "taxonomy_id": self.taxonomy_id,
            "modules": [module.to_dict() for module in self.modules],
            "learning_outcomes": [lo.to_dict() for lo in self.learning_outcomes],
            "textbook_chapters": [chapter.to_dict() for chapter in self.textbook_chapters],
            "course_pages": [page.to_dict() for page in self.course_pages],
            "audit_results": [ar.to_dict() for ar in self.audit_results],
            "developer_notes": [note.to_dict() for note in self.developer_notes],
            "transcripts": self.transcripts,
            "accepted_blueprint": self.accepted_blueprint,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def get_actual_duration_minutes(self) -> float:
        """Calculate actual total duration from all activities."""
        total = 0.0
        for module in self.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    total += activity.estimated_duration_minutes
        return total

    def get_duration_comparison(self) -> Dict[str, Any]:
        """Compare actual duration to target duration.

        Returns:
            Dict with target, actual, deviation, and status fields.
        """
        actual = self.get_actual_duration_minutes()
        target = self.target_duration_minutes

        if target == 0:
            deviation_pct = 0.0
        else:
            deviation_pct = ((actual - target) / target) * 100

        # Determine status based on deviation
        if abs(deviation_pct) <= 10:
            status = "on_target"
        elif abs(deviation_pct) <= 20:
            status = "acceptable"
        else:
            status = "needs_adjustment"

        return {
            "target_minutes": target,
            "actual_minutes": round(actual, 1),
            "deviation_minutes": round(actual - target, 1),
            "deviation_percent": round(deviation_pct, 1),
            "status": status,
            "status_label": {
                "on_target": "On Target",
                "acceptable": "Acceptable",
                "needs_adjustment": "Needs Adjustment"
            }[status]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Course":
        """Deserialize from dictionary with recursive deserialization of all nested objects."""
        data = dict(data)  # Defensive copy

        # Pop and deserialize nested objects
        modules_data = data.pop("modules", [])
        learning_outcomes_data = data.pop("learning_outcomes", [])
        textbook_chapters_data = data.pop("textbook_chapters", [])
        course_pages_data = data.pop("course_pages", [])
        audit_results_data = data.pop("audit_results", [])
        developer_notes_data = data.pop("developer_notes", [])

        # Deserialize flow_mode enum
        if "flow_mode" in data and isinstance(data["flow_mode"], str):
            try:
                data["flow_mode"] = FlowMode(data["flow_mode"])
            except ValueError:
                data["flow_mode"] = FlowMode.SEQUENTIAL

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}

        course = cls(**filtered)
        course.modules = [Module.from_dict(m) for m in modules_data]
        course.learning_outcomes = [LearningOutcome.from_dict(lo) for lo in learning_outcomes_data]
        course.textbook_chapters = [TextbookChapter.from_dict(ch) for ch in textbook_chapters_data]
        course.course_pages = [CoursePage.from_dict(p) for p in course_pages_data]
        course.audit_results = [AuditResult.from_dict(ar) for ar in audit_results_data]
        course.developer_notes = [DeveloperNote.from_dict(n) for n in developer_notes_data]

        return course
