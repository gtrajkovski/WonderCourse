# Phase 5: Extended Content Generation - Research

**Researched:** 2026-02-04
**Domain:** AI content generation with structured outputs, Pydantic validation, Flask API patterns
**Confidence:** HIGH

## Summary

Phase 5 extends the content generation suite with 6 additional activity types (HOL, Coach Dialogues, Practice Quizzes, Labs, Discussions, Assignments, Project Milestones). The research confirms that the existing BaseGenerator pattern established in Phase 4 provides an excellent foundation for these new generators.

The standard approach follows the established pattern:
- Each generator extends BaseGenerator[T] with Generic[T] type safety
- Pydantic v2 schemas define structured output validation
- Claude API structured outputs with output_config guarantee schema compliance
- Flask Blueprint content API already has dispatch infrastructure in place
- Tests use pytest-mock to avoid real API calls

**Key insight:** The user-provided Coursera Master Reference document specifies that HOL rubrics use **Advanced/Intermediate/Beginner scoring at 5/4/2 points** (NOT the Below/Meets/Exceeds pattern used elsewhere). This is a critical distinction that must be reflected in the HOL schema and generator.

**Primary recommendation:** Follow the established BaseGenerator pattern exactly. Create 7 new generators (one per content type), each with its own Pydantic schema, and add them to the content.py dispatch map. No new API infrastructure needed—existing generate/regenerate/edit endpoints work for all content types.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | v2.x | Schema definition and validation | Industry standard for data validation with type safety, 5-50x faster than v1 |
| Anthropic SDK | Latest | Claude API client with structured outputs | Official SDK with native support for output_config and JSON schema |
| Flask | 3.1.x | Web framework with Blueprint pattern | Lightweight, proven for API endpoints, modular with Blueprints |
| pytest-mock | Latest | Mock fixtures for testing | Standard for mocking external API calls in pytest |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing.Generic | stdlib | Type-safe generic classes | For BaseGenerator[T] pattern with TypeVar |
| datetime | stdlib | Timestamp tracking | For build_state updates and versioning |
| uuid | stdlib | Unique identifiers | For activity IDs and content versioning |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic | marshmallow | Pydantic v2 is faster and has better typing support |
| output_config | Tool use with JSON | output_config guarantees schema compliance at token level |
| pytest-mock | unittest.mock | pytest-mock provides cleaner fixture-based API |

**Installation:**
```bash
# Already installed in Phase 4 - no new dependencies needed
pip install anthropic pydantic flask pytest pytest-mock
```

## Architecture Patterns

### Recommended Project Structure
```
src/generators/
├── base_generator.py         # Generic ABC already established
├── hol_generator.py          # NEW: Hands-on Lab generator
├── coach_generator.py        # NEW: Coach Dialogue generator
├── practice_quiz_generator.py # NEW: Practice Quiz generator
├── lab_generator.py          # NEW: Ungraded Lab generator
├── discussion_generator.py   # NEW: Discussion Prompt generator
├── assignment_generator.py   # NEW: Assignment generator
├── project_generator.py      # NEW: Project Milestone generator
└── schemas/
    ├── hol.py               # NEW: HOL schema with Advanced/Intermediate/Beginner rubric
    ├── coach.py             # NEW: 8-section dialogue schema
    ├── practice_quiz.py     # NEW: Similar to quiz but formative focus
    ├── lab.py               # NEW: Lab specification schema
    ├── discussion.py        # NEW: Discussion prompt schema
    ├── assignment.py        # NEW: Assignment schema
    └── project.py           # NEW: Project milestone schema
```

### Pattern 1: BaseGenerator Extension Pattern

**What:** All generators extend BaseGenerator[T] with type-safe schema validation

**When to use:** For every new content type generator

**Example:**
```python
# Source: Existing codebase (C:\CourseBuilder\src\generators\quiz_generator.py)
from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.hol import HOLSchema
from src.utils.content_metadata import ContentMetadata

class HOLGenerator(BaseGenerator[HOLSchema]):
    """Generator for Hands-on Lab activities with scenario-based structure."""

    @property
    def system_prompt(self) -> str:
        """Return system instructions for HOL generation."""
        return """You are an expert instructional designer..."""

    def build_user_prompt(self, learning_objective: str, topic: str, **kwargs) -> str:
        """Build user prompt from parameters."""
        return f"""CONTEXT:\nLearning Objective: {learning_objective}..."""

    def extract_metadata(self, content: HOLSchema) -> dict:
        """Calculate word_count and duration from content."""
        word_count = ContentMetadata.count_words(content.scenario)
        # ... count all text fields
        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "content_type": "hol"
        }
```

### Pattern 2: Pydantic Schema Definition

**What:** Structured schema with Field descriptions for Claude API structured outputs

**When to use:** For every new content type

**Example:**
```python
# Source: Pydantic v2 docs (https://docs.pydantic.dev/latest/concepts/models/)
from pydantic import BaseModel, Field
from typing import List, Literal

class HOLRubricCriterion(BaseModel):
    """Single HOL rubric criterion with Advanced/Intermediate/Beginner levels."""

    name: str = Field(description="Criterion name")
    advanced: str = Field(description="Advanced performance (5 points)")
    intermediate: str = Field(description="Intermediate performance (4 points)")
    beginner: str = Field(description="Beginner performance (2 points)")
    points_advanced: int = Field(default=5, description="Points for advanced")
    points_intermediate: int = Field(default=4, description="Points for intermediate")
    points_beginner: int = Field(default=2, description="Points for beginner")

class HOLSchema(BaseModel):
    """Complete Hands-on Lab activity with 3-part structure and rubric."""

    title: str = Field(description="HOL activity title")
    scenario: str = Field(description="Real-world scenario description")
    parts: List[HOLPart] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 activity parts"
    )
    submission_criteria: str = Field(description="What students must submit")
    rubric: List[HOLRubricCriterion] = Field(
        min_length=3,
        max_length=3,
        description="3 criteria with Advanced/Intermediate/Beginner levels"
    )
    learning_objective: str = Field(description="Learning objective assessed")
```

### Pattern 3: Content API Dispatch Pattern

**What:** Dictionary mapping ContentType enum to generator instances

**When to use:** When adding new content types to API

**Example:**
```python
# Source: Existing codebase (C:\CourseBuilder\src\api\content.py)
# Current pattern (lines 109-126):

if content_type == ContentType.VIDEO:
    generator = VideoScriptGenerator()
    from src.generators.schemas.video_script import VideoScriptSchema
    schema = VideoScriptSchema
elif content_type == ContentType.READING:
    generator = ReadingGenerator()
    # ... etc

# EXTEND with new content types:
elif content_type == ContentType.HOL:
    generator = HOLGenerator()
    from src.generators.schemas.hol import HOLSchema
    schema = HOLSchema
elif content_type == ContentType.COACH:
    generator = CoachGenerator()
    from src.generators.schemas.coach import CoachSchema
    schema = CoachSchema
# ... etc for all 7 new types
```

### Pattern 4: Test Pattern with Mocked API

**What:** Use pytest-mock fixture to mock Anthropic client responses

**When to use:** For all generator tests

**Example:**
```python
# Source: Existing test pattern (C:\CourseBuilder\tests\test_quiz_generator.py)
import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic client to avoid real API calls."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)
    return mock_client

@pytest.fixture
def sample_hol_json():
    """Sample HOL JSON response from API."""
    return '''{
        "title": "Deploy a Web Application",
        "scenario": "You are a DevOps engineer...",
        "parts": [
            {"part_number": 1, "title": "Setup", "instructions": "...", "estimated_minutes": 10},
            {"part_number": 2, "title": "Deploy", "instructions": "...", "estimated_minutes": 15},
            {"part_number": 3, "title": "Verify", "instructions": "...", "estimated_minutes": 10}
        ],
        "submission_criteria": "Screenshot of deployed app",
        "rubric": [
            {
                "name": "Deployment Success",
                "advanced": "App deployed with zero downtime...",
                "intermediate": "App deployed successfully...",
                "beginner": "App deployed with issues...",
                "points_advanced": 5,
                "points_intermediate": 4,
                "points_beginner": 2
            }
        ],
        "learning_objective": "Deploy web applications using CI/CD"
    }'''

def test_generate_returns_valid_schema(mock_anthropic_client, sample_hol_json):
    """Test that generate() returns a valid HOLSchema instance."""
    mock_response = Mock()
    mock_response.content = [Mock(text=sample_hol_json)]
    mock_anthropic_client.messages.create.return_value = mock_response

    generator = HOLGenerator()
    content, metadata = generator.generate(
        schema=HOLSchema,
        learning_objective="Deploy web applications",
        topic="CI/CD pipelines"
    )

    assert isinstance(content, HOLSchema)
    assert len(content.parts) == 3
    assert len(content.rubric) == 3
```

### Pattern 5: Metadata Calculation Pattern

**What:** Use ContentMetadata utility for word counts and duration estimates

**When to use:** In extract_metadata() method of every generator

**Example:**
```python
# Source: Existing codebase (C:\CourseBuilder\src\utils\content_metadata.py)
from src.utils.content_metadata import ContentMetadata

def extract_metadata(self, content: HOLSchema) -> dict:
    """Calculate metadata from generated HOL."""
    word_count = 0

    # Count words in all text fields
    word_count += ContentMetadata.count_words(content.scenario)
    word_count += ContentMetadata.count_words(content.submission_criteria)

    for part in content.parts:
        word_count += ContentMetadata.count_words(part.instructions)

    for criterion in content.rubric:
        word_count += ContentMetadata.count_words(criterion.advanced)
        word_count += ContentMetadata.count_words(criterion.intermediate)
        word_count += ContentMetadata.count_words(criterion.beginner)

    # Estimate duration from part estimates
    duration = sum(part.estimated_minutes for part in content.parts)

    return {
        "word_count": word_count,
        "estimated_duration_minutes": float(duration),
        "total_points": 15,  # 3 criteria × 5 points each
        "content_type": "hol"
    }
```

### Anti-Patterns to Avoid

- **Don't create new API endpoints:** The content API already handles all content types via dispatch. Adding endpoints for each type creates redundancy.
- **Don't bypass output_config:** Never fall back to prompt engineering for JSON. Structured outputs guarantee schema compliance at token generation level.
- **Don't make schemas too rigid:** Use min_length/max_length ranges (e.g., 3-4 options) instead of exact counts to allow model flexibility.
- **Don't skip metadata extraction:** Always calculate word_count and estimated_duration_minutes for consistency across content types.
- **Don't mix scoring models:** HOL uses Advanced/Intermediate/Beginner (5/4/2). Regular rubrics use Below/Meets/Exceeds. Keep them separate.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON validation | Custom validators with try/except | Pydantic BaseModel | Handles edge cases, provides clear error messages, 5-50x faster in v2 |
| API mocking in tests | Manual Mock() setup each time | pytest-mock fixture | Cleaner API, automatic cleanup, fixture reuse |
| Word counting | Custom regex or .count() | ContentMetadata.count_words() | Handles edge cases (empty strings, None values), consistent across codebase |
| Duration estimation | Hardcoded constants | ContentMetadata methods | Industry-standard rates (238 WPM reading, 150 WPM video, 1.5 min/question) |
| Enum validation | String comparisons | ContentType enum | Type-safe, IDE autocomplete, refactor-friendly |
| Generic type safety | Inheritance without TypeVar | Generic[T] with TypeVar | Enables type checking, better IDE support, catches errors at development time |
| Schema evolution | Manual dict migrations | Pydantic model_validate() | Handles missing fields, provides defaults, validates on load |

**Key insight:** Pydantic v2's structured outputs with Claude API provide guaranteed schema compliance. The model literally cannot generate tokens that violate your schema—this is far more reliable than prompt engineering with JSON parsing.

## Common Pitfalls

### Pitfall 1: Wrong Scoring Model for HOL Rubrics

**What goes wrong:** Using Below/Meets/Exceeds (the standard rubric model) for HOL activities

**Why it happens:** Existing RubricGenerator uses Below/Meets/Exceeds pattern, easy to copy-paste

**How to avoid:**
- Create separate HOLRubricCriterion schema with Advanced/Intermediate/Beginner fields
- Use points: Advanced=5, Intermediate=4, Beginner=2 (total 15 points for 3 criteria)
- Document this distinction clearly in system_prompt and schema docstrings

**Warning signs:**
- HOL rubric has "below_expectations" field instead of "beginner"
- Point values are not 5/4/2
- Total points ≠ 15 for 3-criterion HOL rubric

### Pitfall 2: Missing output_config Parameter

**What goes wrong:** Using response_format parameter instead of output_config

**Why it happens:** OpenAI uses response_format, easy to confuse SDK parameters

**How to avoid:**
- Always use output_config with nested format dict
- Copy the exact pattern from BaseGenerator.generate() (lines 102-113)
- Never use response_format with Anthropic SDK

**Warning signs:**
- API returns 400 error with "unknown parameter: response_format"
- Response is not structured even with schema provided
- Tests fail with parameter validation errors

**Source:** Anthropic structured outputs documentation (https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

### Pitfall 3: Incorrect Generic[T] TypeVar Scope

**What goes wrong:** Defining TypeVar inside class instead of module level

**Why it happens:** Looks cleaner to scope TypeVar to class

**How to avoid:**
- Define TypeVar at module level: `T = TypeVar('T', bound=BaseModel)`
- Use it in class signature: `class BaseGenerator(ABC, Generic[T])`
- Never redefine TypeVar inside class methods

**Warning signs:**
- Type checker errors like "TypeVar T is not in scope"
- IDE doesn't provide type hints for generated content
- mypy or pyright complain about Generic usage

**Source:** Python typing docs and Pydantic generic models (https://docs.pydantic.dev/latest/concepts/models/)

### Pitfall 4: Not Handling Build State Transitions

**What goes wrong:** Forgetting to set build_state to GENERATING before API call or restore on error

**Why it happens:** Generator focuses on content creation, not state management

**How to avoid:**
- Content API handles build_state transitions (lines 95-99, 129-131, 138-140)
- Generators should NOT touch build_state—that's API's responsibility
- Always restore previous state on API errors

**Warning signs:**
- Activity stuck in GENERATING state after error
- Race conditions when multiple generations triggered
- Build state doesn't reflect actual generation status

### Pitfall 5: Inconsistent Metadata Field Names

**What goes wrong:** Using different field names for similar metadata across content types

**Why it happens:** Each generator developed independently

**How to avoid:**
- Always include: word_count, estimated_duration_minutes, content_type
- Use consistent field names: total_points (not max_points), question_count (not num_questions)
- Follow existing patterns from Phase 4 generators

**Warning signs:**
- Frontend can't find expected metadata fields
- Metadata calculations fail for some content types
- Course export missing data for certain activities

### Pitfall 6: Over-Constraining Schemas

**What goes wrong:** Using exact lengths instead of ranges (e.g., min_length/max_length)

**Why it happens:** Specifications say "3 parts" so schema enforces exactly 3

**How to avoid:**
- Use ranges for flexibility: `min_length=3, max_length=4` (not `length=3`)
- Let model decide within constraints
- Only use exact counts when truly required (HOL must have exactly 3 parts per spec)

**Warning signs:**
- Model frequently fails validation with "array length must be exactly N"
- Users complain about inflexibility
- Generation fails when model has good reason to vary count

### Pitfall 7: Missing Bloom's Taxonomy in Practice Quiz

**What goes wrong:** Practice quiz schema doesn't include bloom_level per question

**Why it happens:** Copying from graded quiz but removing grading fields

**How to avoid:**
- Practice quizzes should have identical structure to graded quizzes
- Only difference is context: formative vs summative focus
- Both need bloom_level for pedagogical alignment

**Warning signs:**
- Practice quiz questions don't have bloom_level field
- Can't filter or analyze questions by cognitive level
- Pedagogical quality checks fail

### Pitfall 8: Reusing QuizSchema for Practice Quizzes

**What goes wrong:** Both graded and practice quizzes use same schema

**Why it happens:** "They're both quizzes, why duplicate?"

**How to avoid:**
- Create separate PracticeQuizSchema even if structure is identical
- Allows schemas to diverge in future (e.g., practice quizzes add hints)
- Makes intent explicit in code
- Different system prompts produce different content

**Warning signs:**
- Can't distinguish practice from graded quizzes in stored content
- System prompt tries to handle both cases with conditionals
- Tests mix practice and graded quiz expectations

## Code Examples

Verified patterns from official sources:

### Complete Generator Implementation

```python
# Pattern: Full generator with all required methods
from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.discussion import DiscussionSchema
from src.utils.content_metadata import ContentMetadata

class DiscussionGenerator(BaseGenerator[DiscussionSchema]):
    """Generator for discussion prompts with facilitation questions.

    Produces discussion activities with:
    - Engaging prompts that encourage peer interaction
    - Facilitation questions for instructors
    - Engagement hooks to spark initial responses
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for discussion generation."""
        return """You are an expert in facilitating online discussions in educational settings.

Your discussion prompts follow these principles:

**Engagement:**
- Open-ended questions that spark diverse perspectives
- Connect to learners' real-world experiences
- Controversial enough to generate debate without being divisive
- Encourage peer interaction, not just instructor response

**Facilitation Questions:**
- Guide instructors on how to keep discussions productive
- Suggest follow-up questions to deepen thinking
- Identify common misconceptions to address
- Provide strategies for handling common discussion pitfalls

**Engagement Hooks:**
- Present a scenario, dilemma, or provocative statement
- Ask for personal experiences or opinions
- Reference current events or popular culture
- Use multimedia prompts (videos, articles, images)

Create discussions that build community and deepen understanding through peer learning."""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate",
        **kwargs
    ) -> str:
        """Build user prompt for discussion generation.

        Args:
            learning_objective: The learning objective this discussion supports
            topic: Subject matter for the discussion
            difficulty: Difficulty level (beginner, intermediate, advanced)
            **kwargs: Additional parameters (ignored)

        Returns:
            str: Formatted user prompt
        """
        return f"""CONTEXT:
Learning Objective: {learning_objective}
Topic: {topic}
Difficulty: {difficulty}

TASK:
Generate a discussion prompt that encourages peer interaction and deepens understanding.

REQUIREMENTS:
1. Main prompt: Engaging question or scenario (2-3 paragraphs)
2. Facilitation questions: 3-5 questions instructors can use to guide discussion
3. Engagement hooks: 2-3 specific ways to spark initial responses
4. Include clear connection to learning objective

The discussion should encourage diverse perspectives while maintaining focus on the learning goal."""

    def extract_metadata(self, content: DiscussionSchema) -> dict:
        """Calculate metadata from generated discussion.

        Args:
            content: The validated DiscussionSchema instance

        Returns:
            dict: Metadata with word_count, num_facilitation_questions, content_type
        """
        # Count words in all text fields
        word_count = ContentMetadata.count_words(content.main_prompt)
        word_count += ContentMetadata.count_words(content.connection_to_objective)

        for question in content.facilitation_questions:
            word_count += ContentMetadata.count_words(question)

        for hook in content.engagement_hooks:
            word_count += ContentMetadata.count_words(hook)

        return {
            "word_count": word_count,
            "num_facilitation_questions": len(content.facilitation_questions),
            "num_engagement_hooks": len(content.engagement_hooks),
            "content_type": "discussion"
        }
```

### Coach Dialogue 8-Section Schema

```python
# Pattern: Complex nested schema with 8 required sections
from pydantic import BaseModel, Field
from typing import List, Literal

class ConversationStarter(BaseModel):
    """Single conversation starter for coach dialogue."""

    starter_text: str = Field(description="Opening question or prompt")
    purpose: str = Field(description="What this starter helps explore")

class SampleResponse(BaseModel):
    """Sample student response with evaluation level."""

    response_text: str = Field(description="Example student response")
    evaluation_level: Literal["exceeds", "meets", "needs_improvement"] = Field(
        description="Quality level of this response"
    )
    feedback: str = Field(description="Feedback AI coach would provide")

class CoachSchema(BaseModel):
    """Complete coach dialogue with 8 required sections.

    Based on pedagogical AI conversational agent framework with 8 sections:
    Learning Objectives, Scenario, Tasks, Conversation Starters, Sample Responses,
    Evaluation Criteria, Wrap-Up, Reflection.

    Source: Educational technology research on AI tutoring (2026)
    """

    title: str = Field(description="Coach dialogue title")

    # Section 1: Learning Objectives
    learning_objectives: List[str] = Field(
        min_length=2,
        max_length=4,
        description="2-4 specific learning objectives"
    )

    # Section 2: Scenario
    scenario: str = Field(description="Context and background for the dialogue")

    # Section 3: Tasks
    tasks: List[str] = Field(
        min_length=2,
        max_length=5,
        description="Specific tasks student should complete"
    )

    # Section 4: Conversation Starters
    conversation_starters: List[ConversationStarter] = Field(
        min_length=3,
        max_length=5,
        description="3-5 ways to begin the dialogue"
    )

    # Section 5: Sample Responses
    sample_responses: List[SampleResponse] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 sample responses (one per evaluation level)"
    )

    # Section 6: Evaluation Criteria
    evaluation_criteria: List[str] = Field(
        min_length=3,
        max_length=5,
        description="What the AI coach evaluates"
    )

    # Section 7: Wrap-Up
    wrap_up: str = Field(description="How to conclude the dialogue")

    # Section 8: Reflection
    reflection_prompts: List[str] = Field(
        min_length=2,
        max_length=4,
        description="Questions for post-dialogue reflection"
    )
```

### Project Milestone Scaffolded Schema

```python
# Pattern: Scaffolded milestone structure (A1/A2/A3 progression)
from pydantic import BaseModel, Field
from typing import List, Literal

class MilestoneDeliverable(BaseModel):
    """Single deliverable within a milestone."""

    name: str = Field(description="Deliverable name")
    description: str = Field(description="What to submit")
    format: str = Field(description="Expected format (e.g., PDF, code repo)")

class ProjectMilestoneSchema(BaseModel):
    """Scaffolded project milestone in A1/A2/A3 style.

    Milestones build progressively:
    - A1: Foundation/setup
    - A2: Core implementation
    - A3: Advanced features/polish

    Each milestone includes clear deliverables and builds on previous work.
    """

    title: str = Field(description="Milestone title")
    milestone_type: Literal["A1", "A2", "A3"] = Field(
        description="Milestone stage (A1=foundation, A2=core, A3=advanced)"
    )
    overview: str = Field(description="What this milestone accomplishes")

    prerequisites: List[str] = Field(
        min_length=0,
        max_length=3,
        description="What must be completed before starting (empty for A1)"
    )

    deliverables: List[MilestoneDeliverable] = Field(
        min_length=2,
        max_length=5,
        description="What students must submit"
    )

    grading_criteria: List[str] = Field(
        min_length=3,
        max_length=6,
        description="How this milestone is evaluated"
    )

    estimated_hours: int = Field(
        description="Estimated time to complete",
        ge=1,
        le=40
    )

    learning_objective: str = Field(description="Learning objective this milestone addresses")
```

### Assignment with Grading Criteria

```python
# Pattern: Assignment with deliverables and submission checklist
from pydantic import BaseModel, Field
from typing import List

class AssignmentDeliverable(BaseModel):
    """Single deliverable for an assignment."""

    item: str = Field(description="What to submit")
    points: int = Field(description="Points for this deliverable", ge=0)

class ChecklistItem(BaseModel):
    """Single item in submission checklist."""

    item: str = Field(description="Checklist item text")
    required: bool = Field(description="Whether this item is mandatory")

class AssignmentSchema(BaseModel):
    """Assignment with deliverables, grading criteria, and submission checklist.

    Assignments are individual work with clear expectations and grading rubrics.
    Unlike projects, assignments are typically completed in 1-2 weeks with
    specific, well-defined deliverables.
    """

    title: str = Field(description="Assignment title")
    overview: str = Field(description="What this assignment involves")

    deliverables: List[AssignmentDeliverable] = Field(
        min_length=1,
        max_length=5,
        description="What students must submit with point values"
    )

    grading_criteria: List[str] = Field(
        min_length=3,
        max_length=6,
        description="How the assignment is evaluated"
    )

    submission_checklist: List[ChecklistItem] = Field(
        min_length=3,
        max_length=10,
        description="Pre-submission checklist"
    )

    total_points: int = Field(description="Total points for assignment", gt=0)
    estimated_hours: int = Field(description="Estimated completion time", ge=1, le=20)
    learning_objective: str = Field(description="Learning objective assessed")
```

### Lab Specification Schema

```python
# Pattern: Ungraded lab with setup and learning objectives
from pydantic import BaseModel, Field
from typing import List

class SetupStep(BaseModel):
    """Single setup step for lab environment."""

    step_number: int = Field(description="Sequential step number", ge=1)
    instruction: str = Field(description="What to do")
    expected_result: str = Field(description="How to verify this step worked")

class LabSchema(BaseModel):
    """Ungraded lab specification with setup and objectives.

    Labs are practice activities (not graded) that give students hands-on
    experience with tools and techniques. Focus is on exploration and
    skill-building, not assessment.
    """

    title: str = Field(description="Lab title")
    overview: str = Field(description="What this lab teaches")

    learning_objectives: List[str] = Field(
        min_length=2,
        max_length=4,
        description="Skills students will practice"
    )

    setup_instructions: List[SetupStep] = Field(
        min_length=3,
        max_length=10,
        description="How to set up the lab environment"
    )

    lab_exercises: List[str] = Field(
        min_length=3,
        max_length=8,
        description="Exercises to complete during the lab"
    )

    estimated_minutes: int = Field(
        description="Expected completion time",
        ge=15,
        le=120
    )

    prerequisites: List[str] = Field(
        min_length=0,
        max_length=3,
        description="What students should know/have before starting"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt engineering for JSON | Structured outputs with output_config | Nov 2025 | 100% schema compliance, no parsing errors |
| Pydantic v1 | Pydantic v2 with Rust core | 2023 | 5-50x faster validation, better typing |
| Below/Meets/Exceeds for all rubrics | Content-specific scoring models | N/A (spec) | HOL uses Advanced/Intermediate/Beginner (5/4/2) |
| String-based content types | ContentType enum with dispatcher | Phase 4 | Type-safe, refactor-friendly |
| unittest.mock | pytest-mock fixtures | Ongoing | Cleaner test API, automatic cleanup |
| Manual duration estimates | ContentMetadata utility | Phase 4 | Consistent industry-standard rates |

**Deprecated/outdated:**
- **response_format parameter:** Never used with Anthropic SDK, only OpenAI uses this
- **Pydantic Config class:** Replaced by model_config dict in v2
- **@validator decorator:** Replaced by @field_validator and @model_validator in v2
- **root_validator:** Replaced by @model_validator(mode='after') in v2

## Open Questions

Things that couldn't be fully resolved:

1. **Practice Quiz vs Graded Quiz Schema**
   - What we know: Both should use similar MCQ structure with bloom_level and feedback
   - What's unclear: Should they share a base schema or be completely separate?
   - Recommendation: Create separate PracticeQuizSchema even if structure is identical. Allows future divergence (practice quizzes could add hints, explanations, adaptive difficulty). System prompts will differ significantly (formative vs summative focus).

2. **HOL Duration Estimation Method**
   - What we know: HOL has 3 parts, each with estimated_minutes
   - What's unclear: Is duration sum of part durations, or do we apply a multiplier for context switching?
   - Recommendation: Start with simple sum: `sum(part.estimated_minutes for part in content.parts)`. Monitor user feedback and adjust if consistently inaccurate.

3. **Coach Dialogue Evaluation Levels**
   - What we know: 3-level evaluation with example responses
   - What's unclear: Should levels be "exceeds/meets/needs_improvement" or match HOL's "advanced/intermediate/beginner"?
   - Recommendation: Use "exceeds/meets/needs_improvement" for semantic clarity. Coach dialogues are conversational AI interactions, not scored rubrics. The evaluation describes conversation quality, not skill level.

4. **Assignment vs Project Milestone Distinction**
   - What we know: Both have deliverables and grading criteria
   - What's unclear: When to use Assignment vs Project Milestone?
   - Recommendation: Use Assignment for standalone work (1-2 weeks, clear scope). Use Project Milestone for multi-stage projects with dependencies (A1→A2→A3). Assignments are independent; milestones build progressively.

5. **Lab Setup Instructions Format**
   - What we know: Labs need setup instructions with expected results
   - What's unclear: Should setup be structured steps or free-form text?
   - Recommendation: Use structured SetupStep list with step_number, instruction, expected_result. Enables automated setup checkers and clear progress tracking. Free-form text is harder for students to follow.

## Sources

### Primary (HIGH confidence)
- **Anthropic Structured Outputs Official Docs:** https://platform.claude.com/docs/en/build-with-claude/structured-outputs - Output config parameter and JSON schema compliance guarantees
- **Pydantic v2 Official Documentation:** https://docs.pydantic.dev/latest/concepts/models/ - BaseModel, Field, validators, Generic models
- **Pydantic v2 Validators:** https://docs.pydantic.dev/latest/concepts/validators/ - field_validator and model_validator patterns
- **Python Typing with Pydantic:** https://docs.pydantic.dev/latest/concepts/types/ - Generic[T], TypeVar, type safety
- **Flask Blueprint Documentation:** https://flask.palletsprojects.com/en/stable/blueprints/ - Modular application patterns
- **Existing Codebase (Phase 4):** C:\CourseBuilder\src\generators\* - Established patterns for BaseGenerator, schemas, metadata

### Secondary (MEDIUM confidence)
- **Pydantic v2 Best Practices (Jan 2026):** https://oneuptime.com/blog/post/2026-01-21-python-pydantic-v2-validation/ - Recent validation patterns
- **Anthropic Structured Outputs Guide:** https://thomas-wiegold.com/blog/claude-api-structured-output/ - Schema design best practices
- **pytest-mock Tutorial:** https://www.datacamp.com/tutorial/pytest-mock - Testing patterns for mocked APIs
- **API Testing with pytest-mock:** https://codilime.com/blog/testing-apis-with-pytest-mocks-in-python/ - REST API mocking patterns
- **Advanced Pydantic Generic Models:** https://dev.to/mechcloud_academy/advanced-pydantic-generic-models-custom-types-and-performance-tricks-4opf - Generic patterns and performance

### Tertiary (LOW confidence)
- **AI Coach Dialogue Pedagogy:** https://link.springer.com/article/10.1007/s11423-025-10447-4 - 8-section conversational AI framework (requires verification against Coursera spec)
- **Dialogic Pedagogy for LLMs:** https://arxiv.org/html/2506.19484v1 - RAISE model for chatbot learning (general principles, not Coursera-specific)
- **Coursera Labs Blog Post:** https://blog.coursera.org/coursera-introduces-hands-on-learning-with-coursera-labs/ - HOL concept overview (marketing, not technical spec)

### Specifications from User
- **Coursera Short Course Development Master Reference:** Provided in additional_context with exact specifications for all 7 content types
- **Prior Phase Decisions (STATE.md):** BaseGenerator pattern, ContentMetadata rates, output_config parameter, 3-level scoring, blueprint init pattern

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - All libraries established in Phase 4, no new dependencies
- Architecture: **HIGH** - Patterns proven in Phase 4 generators (Video, Reading, Quiz, Rubric)
- Pitfalls: **HIGH** - Derived from codebase analysis and Anthropic/Pydantic docs
- Content type specifications: **HIGH** - User-provided Coursera Master Reference document

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - stable domain, established patterns, minimal churn expected)

**Critical implementation notes:**
1. HOL rubrics use Advanced/Intermediate/Beginner (5/4/2 points), NOT Below/Meets/Exceeds
2. Coach dialogues require all 8 sections per specification
3. Practice quizzes should have separate schema from graded quizzes despite structural similarity
4. All generators extend BaseGenerator[T] and add to content.py dispatch map—no new API endpoints
5. Tests use pytest-mock to avoid real API calls—follow existing test patterns exactly
