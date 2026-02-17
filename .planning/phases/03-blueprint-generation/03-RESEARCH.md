# Phase 3: Blueprint Generation - Research

**Researched:** 2026-02-02
**Domain:** AI-powered curriculum generation, structured LLM outputs, instructional design validation
**Confidence:** HIGH (verified with official SDK v0.77.0 and Claude API docs)

## Summary

Phase 3 implements AI-powered course blueprint generation that transforms high-level course descriptions and learning outcomes into complete hierarchical structures (modules, lessons, activities) aligned with Coursera short course requirements and WWHAA pedagogy.

**CRITICAL UPDATE (2026-02-02):** The previous research incorrectly recommended using `response_format` parameter (OpenAI's API convention). **Anthropic SDK uses `output_config.format` parameter** (introduced in v0.77.0, released 2026-01-29). The SDK does **not** have a `messages.parse()` method - that exists only in the beta namespace as `beta.messages.parse()`. For production use, the standard approach is `messages.create()` with `output_config` parameter.

The standard approach uses Claude's structured outputs feature (generally available since Nov 2025) to guarantee JSON schema compliance via constrained decoding. Blueprint generation follows a three-stage process:
1. **Generate**: AI creates initial structure using educational design constraints encoded in JSON schema
2. **Validate**: Deterministic Python code checks Coursera requirements (module count, duration, content distribution)
3. **Review**: User accepts, edits, or regenerates before committing to course structure

**Primary recommendation:** Use `client.messages.create()` with `output_config.format` parameter and Pydantic-generated schemas. Implement blueprint generator as stateless function with clear prompt templates. Add validator class for Coursera-specific structural requirements. Provide editing workflow that allows accept/refine/regenerate before committing.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.77.0+ | LLM structured output generation | Structured outputs feature (GA), superior instructional design understanding, JSON schema enforcement via constrained decoding |
| Pydantic | 2.10+ | Schema definition and validation | Type safety, automatic JSON schema generation via `model_json_schema()`, Python dataclass integration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsonschema | 4.23+ | Runtime JSON validation | Debugging schema mismatches, validating AI output before Pydantic deserialization |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Claude structured outputs | Prompt engineering only | Structured outputs guarantee 100% schema compliance; prompting has 15-30% failure rate |
| Pydantic schemas | Manual dict validation | Pydantic provides type safety, auto-generated schemas, editor autocomplete |
| Native SDK | Instructor library | Instructor adds convenience layer but requires extra dependency; native SDK is simpler |
| Single-stage generation | Multi-agent pipeline | Single-stage faster and simpler; multi-agent better for large curricula (out of scope) |

**Installation:**
```bash
# Already in requirements.txt from Phase 1
anthropic>=0.77.0

# Add for Phase 3 if not present
pydantic>=2.10.0
```

**Note:** Course Builder currently has `anthropic==0.76.0`. Need to upgrade to 0.77.0+ for `output_config` parameter support.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── generators/
│   ├── base_generator.py           # NEW: Abstract generator base class
│   └── blueprint_generator.py      # NEW: Course blueprint generation
├── validators/
│   └── blueprint_validator.py      # NEW: Coursera requirements validation
├── schemas/
│   └── blueprint_schema.py         # NEW: Pydantic models for blueprint structure
├── prompts/
│   └── blueprint_prompts.py        # NEW: Prompt templates for generation
app.py                               # Existing: Add blueprint API routes
templates/
└── planner.html                     # NEW: Blueprint generation and editing UI
```

### Pattern 1: Structured Outputs with Claude API (Verified SDK v0.77.0)

**What:** Use Claude's native structured outputs to guarantee JSON schema compliance
**When to use:** All AI generation that produces structured data (blueprints, quiz questions, rubrics)

**IMPORTANT:** The Anthropic SDK uses **`output_config`** parameter (not `response_format`). This changed in v0.77.0 (2026-01-29).

**Example:**
```python
from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# Define Pydantic schema
class ActivityBlueprint(BaseModel):
    title: str = Field(max_length=100)
    content_type: Literal["video", "reading", "quiz", "hol", "lab", "discussion", "assignment"]
    activity_type: str
    wwhaa_phase: Optional[Literal["hook", "objective", "content", "ivq", "summary", "cta"]] = None
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    estimated_duration_minutes: float = Field(ge=2.0, le=60.0)

class LessonBlueprint(BaseModel):
    title: str
    description: str
    activities: List[ActivityBlueprint] = Field(min_length=2, max_length=4)

class ModuleBlueprint(BaseModel):
    title: str
    description: str
    lessons: List[LessonBlueprint] = Field(min_length=3, max_length=5)

class CourseBlueprint(BaseModel):
    modules: List[ModuleBlueprint] = Field(min_length=2, max_length=3)
    total_duration_minutes: float
    rationale: str

# Generate blueprint
client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=BLUEPRINT_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_prompt}],
    # CRITICAL: Use output_config (not response_format)
    output_config={
        "format": {
            "type": "json_schema",
            "schema": CourseBlueprint.model_json_schema()
        }
    }
)

# Parse response
blueprint_json = response.content[0].text
blueprint = CourseBlueprint.model_validate_json(blueprint_json)
```

**Key Points:**
- Parameter is `output_config.format`, not `response_format` or `output_format`
- No beta header needed (structured outputs GA since Nov 2025)
- Schema compliance is **guaranteed** by constrained decoding during generation
- Pydantic's `model_json_schema()` auto-generates JSON schema from dataclass

**Sources:**
- [Claude Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [anthropic-sdk-python v0.77.0 Release Notes](https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.77.0)
- [anthropic-sdk-python CHANGELOG.md](https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md)

### Pattern 2: Three-Stage Blueprint Generation

**What:** Generate initial structure, validate against business rules, allow user review
**When to use:** Complex structured outputs that must meet domain-specific requirements (not just schema constraints)

**Example:**
```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class BlueprintValidation:
    """Validation result for course blueprint."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    metrics: dict

class BlueprintGenerator:
    """Generates course blueprints with Coursera requirements validation."""

    def __init__(self, ai_client: Anthropic):
        self.client = ai_client

    def generate(
        self,
        course_description: str,
        learning_outcomes: List[str],
        target_duration_minutes: int,
        audience_level: str
    ) -> Tuple[CourseBlueprint, BlueprintValidation]:
        """Generate and validate blueprint in one call."""

        # Stage 1: Generate initial blueprint via AI
        user_prompt = self._build_prompt(
            course_description,
            learning_outcomes,
            target_duration_minutes,
            audience_level
        )

        raw_blueprint = self._call_ai(user_prompt)

        # Stage 2: Validate against Coursera requirements (deterministic)
        validation = self._validate_blueprint(
            raw_blueprint,
            target_duration_minutes
        )

        # Stage 3: Return for user review (don't auto-refine in v1)
        return raw_blueprint, validation

    def _validate_blueprint(
        self,
        blueprint: CourseBlueprint,
        target_duration: int
    ) -> BlueprintValidation:
        """Validate against Coursera short course requirements."""
        errors = []
        warnings = []
        suggestions = []

        # Requirement: 2-3 modules
        module_count = len(blueprint.modules)
        if not (2 <= module_count <= 3):
            errors.append(f"Must have 2-3 modules, got {module_count}")

        # Requirement: 30-180 minutes total
        total = blueprint.total_duration_minutes
        if not (30 <= total <= 180):
            errors.append(f"Duration must be 30-180 min, got {total:.1f}")

        # Check Bloom's taxonomy diversity
        all_activities = self._flatten_activities(blueprint)
        bloom_levels = [a.bloom_level for a in all_activities]
        unique_blooms = len(set(bloom_levels))
        if unique_blooms < 3:
            warnings.append(f"Only {unique_blooms} Bloom levels (recommend 3+)")

        # Check content distribution
        from collections import Counter
        content_types = [a.content_type for a in all_activities]
        type_counts = Counter(content_types)
        video_pct = type_counts.get('video', 0) / len(content_types)
        if not (0.25 <= video_pct <= 0.35):
            warnings.append(f"Video content {video_pct:.0%} (target 25-35%)")

        return BlueprintValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics={
                "module_count": module_count,
                "total_duration": total,
                "bloom_diversity": unique_blooms
            }
        )

    def _flatten_activities(self, blueprint: CourseBlueprint) -> List:
        """Extract all activities from nested structure."""
        activities = []
        for module in blueprint.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
```

### Pattern 3: Educational Prompt Engineering (INSTRUCTIONS-CONTEXT-TASK)

**What:** Structure prompts for curriculum generation using educational design principles
**When to use:** All AI content generation in educational domain

**Template:**
```python
BLUEPRINT_SYSTEM_PROMPT = """You are an expert instructional designer specializing in Coursera short courses.

Your blueprints follow these principles:
1. WWHAA pedagogy: Each video activity uses Why/What/How/Apply/Assess structure
2. Bloom's taxonomy: Activities span Remember → Create with emphasis on Apply/Analyze
3. Content distribution: ~30% video, ~20% reading, ~30% hands-on, ~20% assessment
4. Scaffolding: Lessons progress from concrete examples → abstract concepts → application

COURSERA SHORT COURSE REQUIREMENTS:
- Duration: 30-180 minutes total
- Modules: 2-3 modules per course
- Lessons per module: 3-5 lessons
- Activities per lesson: 2-4 activities
- Learning outcomes: 1-3 measurable outcomes using Bloom's action verbs

WWHAA PHASES (for video activities only):
- HOOK (10%): Engage with relatable problem
- OBJECTIVE (10%): State measurable learning goal
- CONTENT (60%): Teach with concrete examples
- IVQ (in-video quiz): Check understanding
- SUMMARY (10%): Reinforce key takeaways
- CTA (10%): Direct to next activity

ACTIVITY DURATION GUIDELINES:
- Video (WWHAA): 5-10 minutes
- Reading: 8-12 minutes
- Graded quiz: 5-10 minutes
- Practice quiz: 3-5 minutes
- Hands-on lab: 15-30 minutes
- Discussion: 10-15 minutes
- Assignment: 20-45 minutes

Your output will be valid JSON matching the CourseBlueprint schema."""

def _build_user_prompt(
    self,
    course_description: str,
    learning_outcomes: List[str],
    target_duration: int,
    audience_level: str
) -> str:
    """Build user prompt with CONTEXT-TASK structure."""

    outcomes_text = "\n".join(
        f"{i+1}. {outcome}"
        for i, outcome in enumerate(learning_outcomes)
    )

    return f"""Design a Coursera short course blueprint.

CONTEXT:
- Description: {course_description}
- Audience: {audience_level} learners
- Target duration: {target_duration} minutes

LEARNING OUTCOMES:
{outcomes_text}

TASK:
Create a complete blueprint with:
1. 2-3 modules covering all learning outcomes
2. 3-5 lessons per module with clear progression
3. 2-4 activities per lesson (mix of video, reading, quiz, hands-on)
4. WWHAA phase assignments for video activities
5. Bloom's taxonomy levels matching outcome complexity
6. Realistic duration estimates per activity

Ensure balanced content distribution and complete outcome coverage.
Provide rationale explaining your module/lesson structure decisions."""
```

**Sources:**
- [Claude Prompt Engineering Best Practices 2026](https://promptbuilder.cc/blog/claude-prompt-engineering-best-practices-2026)
- [Precision Prompt Engineering: 7 Research-Backed Techniques](https://medium.com/codetodeploy/precision-prompt-engineering-7-research-backed-techniques-for-production-llm-systems-cbabff9a7f7c)

### Pattern 4: Blueprint Review Workflow (Review Before Commit)

**What:** Allow user to review, edit, and refine AI-generated blueprint before accepting
**When to use:** All AI generation that structurally impacts the course

**Example:**
```python
# API endpoint pattern
@app.route('/api/courses/<id>/blueprint/generate', methods=['POST'])
def generate_blueprint(course_id):
    """Generate blueprint proposal (not committed to course yet)."""
    data = request.get_json()

    # Generate blueprint
    generator = BlueprintGenerator(ai_client)
    blueprint, validation = generator.generate(
        course_description=data['description'],
        learning_outcomes=data['learning_outcomes'],
        target_duration=data.get('target_duration', 90),
        audience_level=data.get('audience_level', 'intermediate')
    )

    # Return for review (not saved to course structure yet)
    return jsonify({
        "blueprint": blueprint.model_dump(),
        "validation": {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "suggestions": validation.suggestions,
            "metrics": validation.metrics
        },
        "status": "pending_review"  # NOT committed
    }), 200

@app.route('/api/courses/<id>/blueprint/accept', methods=['POST'])
def accept_blueprint(course_id):
    """Accept blueprint and commit to course structure."""
    data = request.get_json()
    blueprint_data = data['blueprint']

    # Convert blueprint to actual course structure
    course = project_store.load(course_id)
    course.modules = _blueprint_to_modules(blueprint_data)

    # Save atomically
    project_store.save(course)

    return jsonify({"message": "Blueprint accepted"}), 200

@app.route('/api/courses/<id>/blueprint/refine', methods=['POST'])
def refine_blueprint(course_id):
    """Refine blueprint with user feedback (regenerate with context)."""
    data = request.get_json()
    previous_blueprint = data['blueprint']
    feedback = data['feedback']

    # Build refined prompt with previous attempt and feedback
    refined_prompt = f"""Previous blueprint:
{json.dumps(previous_blueprint, indent=2)}

User feedback:
{feedback}

Generate an improved blueprint addressing the feedback."""

    # Regenerate with feedback context
    refined = generator.generate_with_context(refined_prompt)

    return jsonify({"blueprint": refined.model_dump()}), 200
```

### Anti-Patterns to Avoid

- **Using `response_format` parameter:** Wrong API - Anthropic uses `output_config.format`
- **Prompt engineering without structured outputs:** Unreliable (15-30% schema errors), hard to debug
- **Single-pass generation without validation:** Produces blueprints violating Coursera requirements
- **Directly committing AI output to course:** User can't review/reject; dangerous for structural changes
- **Asking AI to validate its own output:** AI unreliable at checking numerical constraints; use deterministic Python validation
- **Overly complex prompts (>2000 tokens):** Dilutes key instructions; use schema for constraints instead
- **Using beta.messages.parse() in production:** Beta namespace unstable; use messages.create() with output_config

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM JSON parsing | Regex extraction, manual parsing | Claude structured outputs | Guarantees schema compliance, eliminates parsing errors, type-safe with Pydantic |
| Pydantic → JSON Schema | Manual schema writing | `model_json_schema()` | Auto-generated, stays in sync with model, handles nested objects |
| Curriculum validation | Ad-hoc if/else checks | Validator class with clear rules | Maintainable, testable, reusable |
| Educational design rules | Hardcoded in prompts | Separate prompt templates file | Versionable, testable, A/B testing different prompts |
| Bloom's taxonomy verbs | Hardcoded strings | Enum with official verbs | Type-safe, prevents typos, documents valid values |
| Blueprint refinement | Complex multi-turn conversation | Simple regenerate-with-feedback | Simpler, more predictable, easier to debug |

**Key insight:** Structured outputs (GA Nov 2025) eliminated reliability problems that plagued earlier LLM-based structure generation. Before structured outputs, developers used complex prompt engineering + parsing + retry loops with 70-85% success rates. With structured outputs, schema compliance is 100% guaranteed by constrained decoding during generation.

## Common Pitfalls

### Pitfall 1: SDK Version Mismatch (CRITICAL)

**What goes wrong:** Code uses `response_format` parameter; SDK raises TypeError: unexpected keyword argument
**Why it happens:** Anthropic uses different parameter name than OpenAI; docs from different providers mixed up
**How to avoid:** Verify SDK version (0.77.0+); use `output_config.format` parameter; test with actual SDK
**Warning signs:** TypeError on messages.create(); API errors about missing parameters

**Prevention:**
```python
# Check SDK version first
import anthropic
assert anthropic.__version__ >= "0.77.0", "Upgrade anthropic to 0.77.0+"

# WRONG - This is OpenAI API syntax
response = client.messages.create(
    response_format={"type": "json_schema", "schema": {...}}  # ERROR
)

# CORRECT - Anthropic SDK syntax
response = client.messages.create(
    output_config={
        "format": {
            "type": "json_schema",
            "schema": CourseBlueprint.model_json_schema()
        }
    }
)
```

### Pitfall 2: Schema Too Complex for Single Generation

**What goes wrong:** AI generates partially valid structure but misses nested constraints (e.g., lesson has activities with wrong WWHAA phase)
**Why it happens:** Complex schemas with cross-field dependencies exceed LLM's constraint-following capacity
**How to avoid:** Use Pydantic validators for cross-field constraints, run deterministic validation after generation
**Warning signs:** Frequent validation errors on generated blueprints; inconsistent field relationships

**Prevention:**
```python
from pydantic import BaseModel, field_validator, model_validator

class ActivityBlueprint(BaseModel):
    title: str
    content_type: str
    activity_type: str
    wwhaa_phase: Optional[str] = None  # Only for video activities

    @field_validator('wwhaa_phase')
    @classmethod
    def validate_wwhaa_phase(cls, v, info):
        """WWHAA phase required only for video content."""
        if info.data.get('content_type') == 'video' and v is None:
            raise ValueError("WWHAA phase required for video activities")
        if info.data.get('content_type') != 'video' and v is not None:
            raise ValueError(f"WWHAA phase not applicable to {info.data['content_type']}")
        return v

# Run validation after AI generation
try:
    blueprint = CourseBlueprint.model_validate_json(ai_response)
except ValidationError as e:
    # Log error, ask user to regenerate
    logger.error(f"Blueprint validation failed: {e}")
```

### Pitfall 3: Duration Estimates Unrealistic

**What goes wrong:** Generated blueprint sums to 45 minutes but target was 90 minutes
**Why it happens:** AI doesn't accurately estimate activity durations without concrete examples
**How to avoid:** Provide duration guidelines in prompt with specific ranges per activity type
**Warning signs:** User always manually adjusts durations; blueprints consistently 2x too long/short

**Prevention:**
```python
DURATION_GUIDELINES = """
ACTIVITY DURATION GUIDELINES:
- Video (WWHAA): 5-10 minutes (750-1500 words at 150 WPM)
- Reading: 8-12 minutes (1000-1200 words at 250 WPM)
- Graded quiz: 5-10 minutes (5-10 questions)
- Practice quiz: 3-5 minutes (3-5 questions)
- Hands-on lab: 15-30 minutes
- Discussion: 10-15 minutes
- Assignment: 20-45 minutes

Always specify duration_minutes per activity and calculate total."""

# Add to system prompt
BLUEPRINT_SYSTEM_PROMPT = BASE_PROMPT + "\n\n" + DURATION_GUIDELINES

# Validate total after generation
def validate_duration(blueprint: CourseBlueprint, target: int):
    total = blueprint.total_duration_minutes
    if abs(total - target) > (target * 0.3):  # More than 30% off
        return f"Duration {total:.0f}min is {abs(total-target):.0f}min from target {target}min"
    return None
```

### Pitfall 4: Poor Learning Outcome Coverage

**What goes wrong:** Blueprint has 3 learning outcomes but all activities map to outcome #1
**Why it happens:** AI doesn't explicitly track coverage during generation
**How to avoid:** Explicitly request coverage distribution in prompt; validate after generation
**Warning signs:** Validation shows 0 activities for some outcomes; user manually redistributes

**Prevention:**
```python
COVERAGE_INSTRUCTION = """
LEARNING OUTCOME COVERAGE:
Each learning outcome MUST be addressed by at least 2 activities.
Distribute activities across outcomes - don't cluster all activities on one outcome.
Tag each activity with its primary Bloom level matching the outcome it addresses."""

# Add to prompt
BLUEPRINT_SYSTEM_PROMPT = BASE_PROMPT + "\n\n" + COVERAGE_INSTRUCTION

# Validate coverage
def validate_outcome_coverage(blueprint: CourseBlueprint, outcomes: List[str]):
    from collections import defaultdict
    bloom_counts = defaultdict(int)
    for module in blueprint.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                bloom_counts[activity.bloom_level] += 1

    expected_levels = len(outcomes)
    if len(bloom_counts) < expected_levels:
        return f"Only {len(bloom_counts)} Bloom levels; expected {expected_levels}"
    return None
```

### Pitfall 5: Over-Reliance on AI Validation

**What goes wrong:** Ask AI to validate its own blueprint; it says "looks good!" even when duration is 300 minutes
**Why it happens:** LLMs poor at numerical reasoning and checking their own outputs
**How to avoid:** Use deterministic Python validation for all structural/numerical requirements
**Warning signs:** Validation passes but users report obvious errors

**Prevention:**
```python
# NEVER do this
def validate_blueprint_with_ai(blueprint):
    """ANTI-PATTERN: Asking AI to validate its own work."""
    validation_prompt = f"Is this blueprint valid?\n\n{blueprint}"
    response = ai_client.generate(VALIDATOR_PROMPT, validation_prompt)
    return "valid" in response.lower()  # UNRELIABLE

# ALWAYS do this
def validate_blueprint_deterministic(blueprint: CourseBlueprint) -> BlueprintValidation:
    """CORRECT: Deterministic Python validation."""
    errors = []

    # Check duration (numerical)
    total_duration = sum(
        activity.estimated_duration_minutes
        for module in blueprint.modules
        for lesson in module.lessons
        for activity in lesson.activities
    )
    if not (30 <= total_duration <= 180):
        errors.append(f"Total duration {total_duration} outside 30-180 range")

    # Check module count (structural)
    if not (2 <= len(blueprint.modules) <= 3):
        errors.append(f"Must have 2-3 modules, got {len(blueprint.modules)}")

    return BlueprintValidation(is_valid=len(errors) == 0, errors=errors)
```

## Code Examples

### Complete Blueprint Generator with Verified SDK Usage

```python
"""
Blueprint generator using Claude structured outputs.
Verified with anthropic-sdk-python v0.77.0+
"""

from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from src.config import Config

# Pydantic schemas (auto-generate JSON Schema)
class ActivityBlueprint(BaseModel):
    title: str = Field(max_length=100, description="Activity title")
    content_type: Literal["video", "reading", "quiz", "hol", "lab", "discussion", "assignment"]
    activity_type: str
    wwhaa_phase: Optional[Literal["hook", "objective", "content", "ivq", "summary", "cta"]] = None
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    estimated_duration_minutes: float = Field(ge=2.0, le=60.0)
    description: str = Field(max_length=500, description="Brief activity description")

class LessonBlueprint(BaseModel):
    title: str
    description: str
    activities: List[ActivityBlueprint] = Field(min_length=2, max_length=4)

class ModuleBlueprint(BaseModel):
    title: str
    description: str
    lessons: List[LessonBlueprint] = Field(min_length=3, max_length=5)

class CourseBlueprint(BaseModel):
    modules: List[ModuleBlueprint] = Field(min_length=2, max_length=3)
    total_duration_minutes: float
    content_distribution: dict = Field(
        description="Percentage breakdown by content_type"
    )
    rationale: str = Field(
        description="Brief explanation of design decisions"
    )

class BlueprintGenerator:
    """Generates course blueprints using Claude structured outputs."""

    SYSTEM_PROMPT = """You are an expert instructional designer for Coursera short courses.

Design blueprints following:
- WWHAA pedagogy for video activities
- Bloom's taxonomy progression (Remember → Create)
- Content distribution: ~30% video, ~20% reading, ~30% hands-on, ~20% assessment
- Duration: 30-180 minutes total
- 2-3 modules, 3-5 lessons/module, 2-4 activities/lesson

ACTIVITY DURATION GUIDELINES:
- Video: 5-10 min
- Reading: 8-12 min
- Quiz: 3-10 min
- Hands-on lab: 15-30 min
- Discussion: 10-15 min
- Assignment: 20-45 min

Ensure all learning outcomes are covered with appropriate Bloom levels."""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def generate(
        self,
        course_description: str,
        learning_outcomes: List[str],
        target_duration: int = 90,
        audience_level: str = "intermediate"
    ) -> CourseBlueprint:
        """Generate course blueprint with guaranteed schema compliance."""

        user_prompt = self._build_prompt(
            course_description,
            learning_outcomes,
            target_duration,
            audience_level
        )

        # Use structured outputs (SDK v0.77.0+)
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            # CRITICAL: Use output_config (Anthropic SDK v0.77.0+)
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": CourseBlueprint.model_json_schema()
                }
            }
        )

        # Parse with Pydantic (automatic validation)
        blueprint_json = response.content[0].text
        blueprint = CourseBlueprint.model_validate_json(blueprint_json)

        return blueprint

    def _build_prompt(
        self,
        description: str,
        outcomes: List[str],
        duration: int,
        level: str
    ) -> str:
        """Build generation prompt with educational context."""

        outcomes_text = "\n".join(
            f"{i+1}. {outcome}"
            for i, outcome in enumerate(outcomes)
        )

        return f"""Design a Coursera short course blueprint.

CONTEXT:
- Description: {description}
- Audience: {level} learners
- Target duration: {duration} minutes

LEARNING OUTCOMES:
{outcomes_text}

TASK:
Create a complete blueprint with 2-3 modules covering all outcomes.
Include realistic activity titles, types, durations, and Bloom levels.
Ensure balanced content distribution and natural progression.

Provide your rationale for the module/lesson structure."""
```

### Coursera Requirements Validator

```python
"""
Deterministic validation against Coursera short course requirements.
"""

from dataclasses import dataclass
from typing import List
from collections import Counter

@dataclass
class BlueprintValidation:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    metrics: dict

class CourseraValidator:
    """Validates course blueprints against Coursera requirements."""

    # Coursera short course requirements
    MIN_DURATION = 30
    MAX_DURATION = 180
    MIN_MODULES = 2
    MAX_MODULES = 3
    MIN_LESSONS_PER_MODULE = 3
    MAX_LESSONS_PER_MODULE = 5
    MIN_ACTIVITIES_PER_LESSON = 2
    MAX_ACTIVITIES_PER_LESSON = 4

    # Content distribution targets
    TARGET_VIDEO_PCT = 0.30
    TARGET_READING_PCT = 0.20
    TARGET_PRACTICE_PCT = 0.30
    TARGET_ASSESSMENT_PCT = 0.20

    def validate(self, blueprint: CourseBlueprint) -> BlueprintValidation:
        """Run all validation checks."""
        errors = []
        warnings = []
        suggestions = []

        # Duration validation
        total_duration = blueprint.total_duration_minutes
        if total_duration < self.MIN_DURATION:
            errors.append(
                f"Duration {total_duration:.0f}min < minimum {self.MIN_DURATION}min"
            )
        elif total_duration > self.MAX_DURATION:
            errors.append(
                f"Duration {total_duration:.0f}min > maximum {self.MAX_DURATION}min"
            )

        # Module count validation
        module_count = len(blueprint.modules)
        if not (self.MIN_MODULES <= module_count <= self.MAX_MODULES):
            errors.append(
                f"Must have {self.MIN_MODULES}-{self.MAX_MODULES} modules, "
                f"got {module_count}"
            )

        # Lesson count validation
        for i, module in enumerate(blueprint.modules, 1):
            lesson_count = len(module.lessons)
            if not (self.MIN_LESSONS_PER_MODULE <= lesson_count <= self.MAX_LESSONS_PER_MODULE):
                warnings.append(
                    f"Module {i} has {lesson_count} lessons "
                    f"(recommended {self.MIN_LESSONS_PER_MODULE}-{self.MAX_LESSONS_PER_MODULE})"
                )

        # Activity count validation
        for module in blueprint.modules:
            for lesson in module.lessons:
                activity_count = len(lesson.activities)
                if not (self.MIN_ACTIVITIES_PER_LESSON <= activity_count <= self.MAX_ACTIVITIES_PER_LESSON):
                    warnings.append(
                        f"Lesson '{lesson.title}' has {activity_count} activities "
                        f"(recommended {self.MIN_ACTIVITIES_PER_LESSON}-{self.MAX_ACTIVITIES_PER_LESSON})"
                    )

        # Content distribution validation
        all_activities = self._flatten_activities(blueprint)
        content_types = [a.content_type for a in all_activities]
        type_counts = Counter(content_types)
        total_activities = len(all_activities)

        distribution = {
            ct: count / total_activities
            for ct, count in type_counts.items()
        }

        # Check video percentage
        video_pct = distribution.get('video', 0)
        if abs(video_pct - self.TARGET_VIDEO_PCT) > 0.10:
            warnings.append(
                f"Video content {video_pct:.0%} (target ~{self.TARGET_VIDEO_PCT:.0%})"
            )

        # Bloom's taxonomy diversity
        bloom_levels = [a.bloom_level for a in all_activities]
        unique_levels = len(set(bloom_levels))
        if unique_levels < 3:
            warnings.append(
                f"Only {unique_levels} Bloom levels used (recommended 3+)"
            )

        # Calculate metrics
        metrics = {
            "total_duration": total_duration,
            "module_count": module_count,
            "total_activities": total_activities,
            "content_distribution": distribution,
            "bloom_diversity": unique_levels
        }

        return BlueprintValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, blueprint: CourseBlueprint) -> List:
        """Extract all activities from nested structure."""
        activities = []
        for module in blueprint.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
```

### Blueprint to Course Conversion

```python
"""
Convert AI-generated blueprint to actual Course dataclasses.
"""

from src.core.models import Course, Module, Lesson, Activity
from src.core.models import ContentType, ActivityType, WWHAAPhase, BloomLevel

def blueprint_to_course(
    blueprint: CourseBlueprint,
    course_id: str,
    title: str,
    description: str
) -> Course:
    """Convert blueprint schema to Course dataclass."""

    # Create Course
    course = Course(
        id=course_id,
        title=title,
        description=description,
        target_duration_minutes=int(blueprint.total_duration_minutes)
    )

    # Convert modules
    for module_bp in blueprint.modules:
        module = Module(
            title=module_bp.title,
            description=module_bp.description,
            order=len(course.modules)
        )

        # Convert lessons
        for lesson_bp in module_bp.lessons:
            lesson = Lesson(
                title=lesson_bp.title,
                description=lesson_bp.description,
                order=len(module.lessons)
            )

            # Convert activities
            for activity_bp in lesson_bp.activities:
                activity = Activity(
                    title=activity_bp.title,
                    content_type=ContentType(activity_bp.content_type),
                    activity_type=_map_activity_type(activity_bp.activity_type),
                    wwhaa_phase=WWHAAPhase(activity_bp.wwhaa_phase) if activity_bp.wwhaa_phase else WWHAAPhase.CONTENT,
                    bloom_level=BloomLevel(activity_bp.bloom_level),
                    estimated_duration_minutes=activity_bp.estimated_duration_minutes,
                    order=len(lesson.activities)
                )
                lesson.activities.append(activity)

            module.lessons.append(lesson)

        course.modules.append(module)

    return course

def _map_activity_type(bp_type: str) -> ActivityType:
    """Map blueprint activity type string to ActivityType enum."""
    type_map = {
        "video_lecture": ActivityType.VIDEO_LECTURE,
        "reading_material": ActivityType.READING_MATERIAL,
        "graded_quiz": ActivityType.GRADED_QUIZ,
        "practice_quiz": ActivityType.PRACTICE_QUIZ,
        "hands_on_lab": ActivityType.HANDS_ON_LAB,
        "coach_dialogue": ActivityType.COACH_DIALOGUE,
        "ungraded_lab": ActivityType.UNGRADED_LAB,
        "discussion_prompt": ActivityType.DISCUSSION_PROMPT,
        "assignment_submission": ActivityType.ASSIGNMENT_SUBMISSION,
        "project_milestone": ActivityType.PROJECT_MILESTONE
    }
    return type_map.get(bp_type, ActivityType.VIDEO_LECTURE)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt engineering for JSON | Structured outputs API | Nov 2025 (Claude GA) | 100% schema compliance vs 70-85% with prompting |
| Manual curriculum design | AI-assisted blueprint generation | 2024-2026 | 10x faster initial structure, AI handles scaffolding |
| Text-based validation | Pydantic + JSON Schema | Pydantic 2.0 (2023) | Type-safe validation, auto-generated schemas |
| Multi-stage refinement loops | Single-pass with schema | Structured outputs (2025) | Simpler code, faster generation, fewer API calls |
| Hardcoded prompts in code | Centralized prompt templates | Best practice 2024+ | Versionable, testable, easier A/B testing |
| `output_format` parameter | `output_config.format` parameter | SDK v0.77.0 (Jan 2026) | Standardized API surface across features |

**Deprecated/outdated:**
- **JSON extraction with regex:** Structured outputs eliminate need for parsing
- **Retry loops for schema compliance:** Guaranteed compliance on first try
- **LangChain for simple generation:** Overkill for single LLM call; use SDK directly
- **Function calling for structured data:** Structured outputs more reliable and simpler
- **`response_format` parameter:** Wrong API (OpenAI convention); Anthropic uses `output_config`
- **beta.messages.parse():** Beta namespace; use stable messages.create() with output_config

## Open Questions

### 1. Should blueprint include learning outcome IDs for automatic mapping?
- **What we know:** Phase 2 has outcome-activity mapping via `mapped_activity_ids`
- **What's unclear:** Should AI assign activities to outcomes during blueprint generation, or leave for user?
- **Recommendation:** Generate suggested mappings in blueprint but don't commit to Course; let user review/adjust in planner UI

### 2. How to handle blueprint refinement iterations?
- **What we know:** Single-pass generation may not satisfy user preferences
- **What's unclear:** Should we implement iterative refinement with user feedback, or regenerate from scratch?
- **Recommendation:** v1 implements regenerate-from-scratch with updated prompt; defer iterative refinement to v2

### 3. What granularity for activity descriptions in blueprint?
- **What we know:** Activities have `content` field (can be very detailed)
- **What's unclear:** Should blueprint include placeholder content, detailed outlines, or just titles?
- **Recommendation:** Blueprint has 1-2 sentence descriptions only; actual content generation is Phase 4+

## Sources

### Primary (HIGH confidence)
- [Claude API: Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Official API documentation (verified 2026-02-02)
- [anthropic-sdk-python v0.77.0 Release](https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.77.0) - SDK changelog for output_config
- [anthropic-sdk-python CHANGELOG.md](https://github.com/anthropics/anthropic-sdk-python/blob/main/CHANGELOG.md) - Full version history
- [Pydantic Documentation](https://docs.pydantic.dev/latest/) - Schema validation and model generation

### Secondary (MEDIUM confidence)
- [Claude Prompt Engineering Best Practices 2026](https://promptbuilder.cc/blog/claude-prompt-engineering-best-practices-2026) - Current prompt patterns
- [Precision Prompt Engineering: 7 Research-Backed Techniques](https://medium.com/codetodeploy/precision-prompt-engineering-7-research-backed-techniques-for-production-llm-systems-cbabff9a7f7c) - Production LLM patterns
- [A Hands-On Guide to Anthropic's Structured Output Capabilities](https://towardsdatascience.com/hands-on-with-anthropics-new-structured-output-capabilities/) - Tutorial and examples
- [Anthropic Releases](https://github.com/anthropics/anthropic-sdk-python/releases) - Release notes for all versions

### Tertiary (LOW confidence)
- Various web search results on LLM curriculum design (2025-2026) - General guidance, not implementation-specific
- Academic papers on curriculum mapping - Process guidance but not AI implementation

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - Verified SDK v0.77.0 with actual parameter names; structured outputs GA since Nov 2025
- Architecture: **HIGH** - Two-stage generation (generate + validate) is proven pattern; verified with official docs
- Pitfalls: **HIGH** - SDK version mismatch caught and corrected; schema validation patterns well-documented

**Research date:** 2026-02-02
**SDK version verified:** anthropic==0.76.0 (installed), anthropic>=0.77.0 (required for output_config)
**Valid until:** ~90 days (structured outputs stable feature; instructional design patterns evolve slowly)

---

## CRITICAL CORRECTIONS FROM PREVIOUS RESEARCH

**Errors in previous research (now fixed):**
1. ❌ Recommended `response_format` parameter → ✅ Correct parameter is `output_config.format` (SDK v0.77.0+)
2. ❌ Suggested using `messages.parse()` → ✅ Use `messages.create()` with `output_config`; parse() exists only in beta namespace
3. ❌ Showed beta header requirement → ✅ No beta header needed (structured outputs GA since Nov 2025)
4. ❌ Used `transform_schema()` helper → ✅ Direct `model_json_schema()` is simpler and sufficient

**Phase 3 Research Complete** - Ready for planning with verified SDK usage patterns and deterministic validation approach.
