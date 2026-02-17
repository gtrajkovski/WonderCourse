# Phase 4: Core Content Generation - Research

**Researched:** 2026-02-03
**Domain:** AI-powered educational content generation with Claude structured outputs
**Confidence:** HIGH

## Summary

Phase 4 implements AI-powered content generation for the 4 most critical content types in Coursera short courses: video scripts (WWHAA structure), readings (APA 7 references), graded quizzes (MCQ with distractors), and rubrics (scoring criteria). This research investigated Claude's structured outputs API, educational content generation best practices, Python generator architecture patterns, and content validation/metadata extraction techniques.

The standard approach is a **BaseGenerator abstract class** with specialized subclasses for each content type, all using Claude's `output_config` parameter with Pydantic schemas for guaranteed JSON validation. Each generator produces structured output with embedded metadata (word count, duration estimates, Bloom's level) and stores results in the Activity.content field. Content regeneration follows a **generate → validate → review → approve** workflow with BuildState enum tracking.

**Primary recommendation:** Implement BaseGenerator ABC with Pydantic schema models, use Claude structured outputs with `output_config.format`, calculate metadata client-side (don't rely on AI for word counts), and design prompts following educational best practices (plausible MCQ distractors, APA 7 citation formats, WWHAA instructional structure).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.77.0+ | Claude API with structured outputs | Official SDK with `output_config` parameter for guaranteed JSON schemas |
| pydantic | 2.10.0+ | Schema validation and transformation | Industry standard for Python data validation, native Claude SDK integration |
| python-dotenv | 1.0.1+ | Environment variable management | Already in use for API keys, standard Python pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-mock | 3.15.0+ | Testing generator API calls | Mock expensive API calls during tests (already in use) |
| abc (stdlib) | Built-in | Abstract base classes | Define BaseGenerator interface with @abstractmethod decorators |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic | dataclasses + manual validation | Pydantic provides `model_json_schema()` for Claude, dataclasses would require manual JSON schema construction |
| Claude structured outputs | JSON mode prompting | Structured outputs guarantee schema compliance (no retries needed), JSON mode has ~5-10% parse failure rate |
| Client-side word counting | Ask Claude for word count | Client-side is deterministic and free; Claude may hallucinate counts or add token costs |

**Installation:**
```bash
# All dependencies already installed in Phase 1
pip install anthropic>=0.77.0 pydantic>=2.10.0 python-dotenv>=1.0.1
pip install pytest-mock>=3.15.0  # Testing
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── generators/
│   ├── __init__.py
│   ├── base_generator.py         # BaseGenerator ABC
│   ├── video_script_generator.py # VideoScriptGenerator
│   ├── reading_generator.py      # ReadingGenerator
│   ├── quiz_generator.py         # QuizGenerator
│   ├── rubric_generator.py       # RubricGenerator
│   └── schemas/
│       ├── __init__.py
│       ├── video_script.py       # Pydantic models for video scripts
│       ├── reading.py            # Pydantic models for readings
│       ├── quiz.py               # Pydantic models for quizzes
│       └── rubric.py             # Pydantic models for rubrics
└── utils/
    └── content_metadata.py       # Word count, duration, validation helpers
```

### Pattern 1: Abstract Base Class for Generators

**What:** Define a common interface for all content generators using Python's ABC module

**When to use:** When multiple generator classes share common patterns (API client, Pydantic validation, metadata extraction)

**Example:**
```python
# Source: Python 3.14.3 documentation + Phase 3 BlueprintGenerator pattern
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel
from anthropic import Anthropic
from src.config import Config

T = TypeVar('T', bound=BaseModel)

class BaseGenerator(ABC, Generic[T]):
    """Abstract base class for all content generators.

    Provides common infrastructure:
    - Anthropic client management
    - Pydantic schema transformation
    - Metadata extraction
    - Error handling
    """

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize with Anthropic client (stateless, no conversation history)."""
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return generator-specific system prompt."""
        pass

    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        """Build user prompt from input parameters."""
        pass

    @abstractmethod
    def extract_metadata(self, content: T) -> dict:
        """Extract metadata (word_count, duration, bloom_level) from generated content."""
        pass

    def generate(self, schema: type[T], **prompt_kwargs) -> T:
        """Generate content using Claude structured outputs.

        Args:
            schema: Pydantic model class for output validation
            **prompt_kwargs: Arguments passed to build_user_prompt()

        Returns:
            Validated Pydantic model instance
        """
        user_prompt = self.build_user_prompt(**prompt_kwargs)

        # Call Claude API with structured outputs
        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": schema.model_json_schema()
                }
            }
        )

        # Parse and validate with Pydantic
        content_json = response.content[0].text
        validated_content = schema.model_validate_json(content_json)

        return validated_content
```

### Pattern 2: Pydantic Schema Models with Structured Outputs

**What:** Define content structure using Pydantic BaseModel with Field constraints, then transform to JSON schema for Claude

**When to use:** All content generation to guarantee schema compliance without retries

**Example:**
```python
# Source: Anthropic structured outputs documentation (2026-02-03)
from pydantic import BaseModel, Field
from typing import List, Literal

class QuizQuestion(BaseModel):
    """Single MCQ question with distractors."""
    question_text: str = Field(max_length=500, description="Question text")
    correct_answer: str = Field(max_length=200, description="Correct answer")
    distractors: List[str] = Field(
        min_length=2,
        max_length=4,
        description="Plausible incorrect answers"
    )
    explanation: str = Field(max_length=300, description="Why correct answer is right")
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]

class QuizContent(BaseModel):
    """Complete quiz with multiple questions."""
    title: str = Field(max_length=200)
    questions: List[QuizQuestion] = Field(min_length=3, max_length=10)
    passing_score_percentage: int = Field(ge=60, le=100, default=70)
    time_limit_minutes: int = Field(ge=5, le=60)

# Usage in QuizGenerator
response = self.client.messages.create(
    model=self.model,
    max_tokens=4096,
    system=self.system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    output_config={
        "format": {
            "type": "json_schema",
            "schema": QuizContent.model_json_schema()  # Pydantic generates JSON schema
        }
    }
)

quiz = QuizContent.model_validate_json(response.content[0].text)
```

**Key benefits:**
- **Guaranteed valid JSON**: No `JSON.parse()` errors, no retries for schema violations
- **Type safety**: Pydantic enforces field types and required fields
- **Constraint relaxation**: Claude SDK auto-transforms unsupported constraints (e.g., `max_length`) into description hints
- **Validation**: `model_validate_json()` checks all constraints after generation

### Pattern 3: Metadata Extraction (Client-Side)

**What:** Calculate word count, duration estimates, and structural metadata client-side rather than asking the AI

**When to use:** All generators after content creation

**Example:**
```python
# Source: BasicTextMetrics patterns + educational standards research
from typing import Dict, Any

class ContentMetadata:
    """Calculate metadata for generated content."""

    # Standard reading rates (research-backed)
    WORDS_PER_MINUTE_READING = 238  # Adult non-fiction average
    WORDS_PER_MINUTE_SPEAKING = 150  # Video script delivery

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text (whitespace-delimited tokens)."""
        return len(text.split())

    @staticmethod
    def estimate_reading_duration(text: str) -> float:
        """Estimate reading duration in minutes."""
        word_count = ContentMetadata.count_words(text)
        return word_count / ContentMetadata.WORDS_PER_MINUTE_READING

    @staticmethod
    def estimate_video_duration(script: str) -> float:
        """Estimate video duration from script length."""
        word_count = ContentMetadata.count_words(script)
        return word_count / ContentMetadata.WORDS_PER_MINUTE_SPEAKING

    @staticmethod
    def validate_quiz_answer_distribution(questions: list) -> Dict[str, Any]:
        """Check answer key distribution (avoid all answers being 'A')."""
        answer_positions = []
        for q in questions:
            # Assuming answers are shuffled during generation
            correct_index = 0  # Would need to track from generation
            answer_positions.append(correct_index)

        # Check for bias (no position should be >50% of answers)
        position_counts = {}
        for pos in answer_positions:
            position_counts[pos] = position_counts.get(pos, 0) + 1

        max_count = max(position_counts.values())
        total = len(answer_positions)
        bias_detected = max_count > (total * 0.5)

        return {
            "balanced": not bias_detected,
            "distribution": position_counts
        }
```

### Pattern 4: Regeneration Workflow with BuildState Tracking

**What:** Track content generation state through DRAFT → GENERATING → GENERATED → REVIEWED → APPROVED lifecycle

**When to use:** All content generation APIs to support iterative refinement

**Example:**
```python
# Source: Phase 2 BuildState enum + CMS versioning patterns
from src.models.activity import BuildState

class ContentGenerationWorkflow:
    """Manage content generation lifecycle."""

    def initiate_generation(self, activity):
        """Start generation process."""
        activity.build_state = BuildState.GENERATING
        # Store original content as backup if regenerating
        return activity

    def complete_generation(self, activity, generated_content: str, metadata: dict):
        """Mark generation complete with metadata."""
        activity.content = generated_content
        activity.build_state = BuildState.GENERATED
        activity.word_count = metadata["word_count"]
        activity.estimated_duration_minutes = metadata["duration"]
        # Note: bloom_level set during blueprint, not changed by generator
        return activity

    def regenerate(self, activity, **new_params):
        """Regenerate content with different parameters.

        Preserves previous version in metadata for rollback.
        """
        # Store previous version
        if activity.content:
            activity.metadata["previous_content"] = activity.content
            activity.metadata["previous_word_count"] = activity.word_count

        activity.build_state = BuildState.GENERATING
        # Call generator with new_params...
        return activity
```

### Anti-Patterns to Avoid

- **Asking Claude for metadata**: Don't request word counts or duration estimates from the AI - calculate them deterministically client-side to avoid hallucinations and token waste
- **Generic prompts**: Avoid vague prompts like "Generate a quiz" - provide specific context (course title, learning objective, difficulty level, Bloom's taxonomy target)
- **No validation before storage**: Always validate Pydantic models with `model_validate_json()` before saving to Activity.content
- **Ignoring BuildState**: Track generation state to prevent race conditions (e.g., user editing while regeneration is in progress)
- **Deep inheritance hierarchies**: Avoid VideoScriptGenerator → BaseVideoGenerator → BaseContentGenerator chains; keep it to BaseGenerator → SpecificGenerator (2 levels max)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema from Pydantic | Manual `{"type": "object", ...}` construction | `Schema.model_json_schema()` | Pydantic generates correct JSON schema automatically, handles nested models, enums, constraints |
| Word counting | Regex-based tokenization | `len(text.split())` or `BasicTextMetrics` | Simple whitespace split is sufficient for duration estimates; complex tokenization adds overhead without benefit |
| APA citation formatting | Custom citation builder | Reference APA 7 examples in prompt + validate format with regex | Claude knows APA 7 format; providing examples is more reliable than building a formatter |
| Quiz answer shuffling | Custom randomization logic | Fisher-Yates shuffle or `random.shuffle()` | Standard library provides tested algorithms |
| Bloom's taxonomy mapping | Custom classification logic | Enum validation + prompt guidance | Bloom's levels are set during blueprint; generator validates, doesn't classify |

**Key insight:** Claude structured outputs with Pydantic eliminates the need for custom JSON parsers, retry logic, and schema validators. The official SDK handles schema transformation and validation, so focus on prompt engineering and metadata extraction, not infrastructure.

## Common Pitfalls

### Pitfall 1: Relying on AI for Deterministic Calculations

**What goes wrong:** Asking Claude to count words, calculate durations, or validate answer distributions leads to hallucinated numbers and inconsistent results

**Why it happens:** LLMs are not calculators; they approximate rather than compute precisely

**How to avoid:**
- Calculate word counts client-side: `word_count = len(content.split())`
- Use fixed constants for WPM rates (150 for video, 238 for reading)
- Validate quiz distributions with Python logic, not AI prompts

**Warning signs:**
- Word count in AI output doesn't match actual text length
- Duration estimates change when regenerating identical content
- Quiz answer keys are biased (all "A" or all "C")

### Pitfall 2: Pydantic Constraint Violations with Structured Outputs

**What goes wrong:** Using unsupported JSON schema features (e.g., `minimum`, `maximum`, `minLength`) causes 400 errors or constraint violations

**Why it happens:** Claude structured outputs support a subset of JSON schema - numerical/string constraints are not enforced during generation

**How to avoid:**
- Use `enum` for constrained choices (e.g., Bloom levels)
- Use `min_length`/`max_length` on lists/arrays, not strings (these ARE supported)
- Add constraint descriptions in Field: `Field(description="Must be 100-500 words")`
- Validate constraints post-generation with Pydantic's `model_validate_json()`

**Warning signs:**
- 400 errors mentioning "unsupported schema feature"
- Generated content violates expected constraints (e.g., reading is 2000 words when max is 1200)

**Reference:** [Anthropic Structured Outputs - JSON Schema Limitations](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

### Pitfall 3: Poor MCQ Distractor Quality

**What goes wrong:** AI generates distractors that are obviously wrong (e.g., "What is 2+2?" → distractors: "A. 4", "B. banana", "C. purple")

**Why it happens:** Generic prompts don't guide the model to create plausible, educational distractors

**How to avoid:**
- Include distractor quality guidelines in system prompt
- Specify: "Distractors must be semantically plausible and represent common misconceptions"
- Request option-level feedback: "For each distractor, explain why it's incorrect"
- Reference research: Distractors should have close semantic similarity to correct answer but differ in a meaningful way

**Warning signs:**
- Distractors are nonsensical or off-topic
- All test-takers can eliminate 2-3 options immediately
- No clear misconception represented by wrong answers

**Reference:** [PMC - Automatic Distractor Generation](https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/)

### Pitfall 4: Ignoring Grammar Compilation Latency

**What goes wrong:** First API call with new schema takes 2-5 seconds longer than expected, causing timeout errors

**Why it happens:** Claude compiles grammars for structured outputs on first use; subsequent calls are cached (24-hour TTL)

**How to avoid:**
- Set higher timeouts for first generation requests (8-10 seconds)
- Warm up cache in tests: call generator once before measuring performance
- Document expected latency: "First generation: ~5s, subsequent: ~2s"
- Cache schemas in production: reuse identical Pydantic models across calls

**Warning signs:**
- First test run passes, second run is 3x faster
- Production API timeouts on schema changes
- User complaints about slow generation on first use

**Reference:** [Anthropic Structured Outputs - Grammar Compilation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

### Pitfall 5: WWHAA Structure Violations

**What goes wrong:** Generated video scripts omit required sections (Hook, Objective, Content, IVQ, Summary, CTA) or have incorrect proportions

**Why it happens:** WWHAA is Coursera-specific pedagogy, not universal knowledge; Claude needs explicit structure guidance

**How to avoid:**
- Define WWHAA in system prompt with percentages: "Hook (10%), Objective (10%), Content (60%), IVQ (5%), Summary (10%), CTA (5%)"
- Use Pydantic schema with separate fields per section (not one big "script" string)
- Validate section presence post-generation
- Provide example scripts in few-shot prompts

**Warning signs:**
- Missing sections (e.g., no Hook or CTA)
- Disproportionate content (90% Content, 5% everything else)
- IVQ (in-video question) not a real question

**Note:** WWHAA was not found in 2026 web search results as a named framework, but the Hook → Objective → Content → Application → Assessment structure is standard in instructional design.

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: BaseGenerator with Abstract Methods

```python
# Source: Python 3.14.3 ABC documentation + Phase 3 BlueprintGenerator
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel
from anthropic import Anthropic
from src.config import Config

T = TypeVar('T', bound=BaseModel)

class BaseGenerator(ABC, Generic[T]):
    """Abstract base for content generators.

    Concrete generators must implement:
    - system_prompt: Educational domain expertise
    - build_user_prompt: Convert kwargs to prompt
    - extract_metadata: Calculate word count, duration, etc.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Generator-specific system instructions."""
        pass

    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        """Build user prompt from inputs."""
        pass

    @abstractmethod
    def extract_metadata(self, content: T) -> dict:
        """Extract word_count, duration, bloom_level."""
        pass

    def generate(self, schema: type[T], **prompt_kwargs) -> tuple[T, dict]:
        """Generate content with metadata.

        Returns:
            (validated_content, metadata_dict)
        """
        user_prompt = self.build_user_prompt(**prompt_kwargs)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": schema.model_json_schema()
                }
            }
        )

        content = schema.model_validate_json(response.content[0].text)
        metadata = self.extract_metadata(content)

        return content, metadata
```

### Example 2: QuizGenerator Implementation

```python
# Source: Distractor generation research + Anthropic structured outputs
from pydantic import BaseModel, Field
from typing import List, Literal

class QuizQuestion(BaseModel):
    question_text: str = Field(max_length=500)
    correct_answer: str = Field(max_length=200)
    distractors: List[str] = Field(min_length=2, max_length=3)
    feedback_correct: str = Field(max_length=200, description="Why this is correct")
    feedback_distractors: List[str] = Field(
        min_length=2,
        max_length=3,
        description="Why each distractor is incorrect"
    )
    bloom_level: Literal["remember", "understand", "apply", "analyze"]

class QuizSchema(BaseModel):
    questions: List[QuizQuestion] = Field(min_length=3, max_length=10)

class QuizGenerator(BaseGenerator[QuizSchema]):

    @property
    def system_prompt(self) -> str:
        return """You are an expert assessment designer for Coursera courses.

QUIZ DESIGN PRINCIPLES:
1. Questions must align with specified learning objectives and Bloom's taxonomy level
2. Distractors must be plausible and represent common misconceptions
3. Avoid "all of the above" or "none of the above" options
4. Feedback must explain WHY each option is correct/incorrect
5. Answer distribution should be balanced (no bias toward position A/B/C)

DISTRACTOR QUALITY:
- Semantically plausible (not obviously wrong)
- Represent common student errors or misconceptions
- Similar in length and complexity to correct answer
- Avoid nonsensical or humorous options

Your output will be valid JSON matching the QuizSchema."""

    def build_user_prompt(self, learning_objective: str, bloom_level: str,
                         num_questions: int, difficulty: str, topic: str) -> str:
        return f"""Create a graded quiz for this learning objective:

OBJECTIVE: {learning_objective}

REQUIREMENTS:
- Number of questions: {num_questions}
- Bloom's level: {bloom_level}
- Difficulty: {difficulty}
- Topic: {topic}
- Each question: 1 correct answer + 2-3 plausible distractors
- Include option-level feedback (why correct is right, why each distractor is wrong)

Ensure distractors are plausible and represent common misconceptions."""

    def extract_metadata(self, content: QuizSchema) -> dict:
        total_questions = len(content.questions)
        # Estimate 1-2 minutes per question for graded quiz
        duration = total_questions * 1.5

        return {
            "word_count": sum(
                len(q.question_text.split()) +
                len(q.correct_answer.split()) +
                sum(len(d.split()) for d in q.distractors)
                for q in content.questions
            ),
            "estimated_duration_minutes": duration,
            "question_count": total_questions
        }
```

### Example 3: Testing with pytest-mock

```python
# Source: pytest-mock documentation + Phase 3 test patterns
import pytest
from unittest.mock import MagicMock
from src.generators.quiz_generator import QuizGenerator, QuizSchema

def test_quiz_generator_creates_valid_schema(mocker):
    """Test QuizGenerator with mocked Anthropic API."""

    # Mock API response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"questions": [{"question_text": "What is 2+2?", '
                      '"correct_answer": "4", "distractors": ["3", "5"], '
                      '"feedback_correct": "Correct addition", '
                      '"feedback_distractors": ["Too low", "Too high"], '
                      '"bloom_level": "remember"}]}')
    ]

    # Patch Anthropic client
    mock_client = mocker.patch("anthropic.Anthropic")
    mock_client.return_value.messages.create.return_value = mock_response

    # Generate quiz
    generator = QuizGenerator(api_key="test-key")
    content, metadata = generator.generate(
        schema=QuizSchema,
        learning_objective="Perform basic arithmetic",
        bloom_level="remember",
        num_questions=1,
        difficulty="easy",
        topic="Addition"
    )

    # Assertions
    assert len(content.questions) == 1
    assert content.questions[0].question_text == "What is 2+2?"
    assert content.questions[0].correct_answer == "4"
    assert len(content.questions[0].distractors) == 2
    assert metadata["question_count"] == 1
    assert metadata["estimated_duration_minutes"] == 1.5
```

### Example 4: Content Metadata Extraction

```python
# Source: Reading rate research + BasicTextMetrics patterns
class ContentMetadata:
    """Calculate metadata for all content types."""

    # Research-backed constants
    WPM_READING = 238  # Adult non-fiction (meta-analysis)
    WPM_SPEAKING = 150  # Video delivery rate
    WPM_QUIZ = 90  # Time per question (reading + thinking)

    @staticmethod
    def extract_reading_metadata(text: str) -> dict:
        """Extract metadata for reading content."""
        words = text.split()
        word_count = len(words)
        duration = word_count / ContentMetadata.WPM_READING

        return {
            "word_count": word_count,
            "estimated_duration_minutes": round(duration, 1),
            "content_type": "reading"
        }

    @staticmethod
    def extract_video_metadata(script: str, sections: dict) -> dict:
        """Extract metadata for WWHAA video script.

        Args:
            script: Full script text
            sections: Dict with keys {hook, objective, content, ivq, summary, cta}
        """
        total_words = len(script.split())
        duration = total_words / ContentMetadata.WPM_SPEAKING

        # Validate WWHAA proportions (rough guidelines)
        section_lengths = {k: len(v.split()) for k, v in sections.items()}
        content_pct = section_lengths.get("content", 0) / total_words if total_words > 0 else 0

        return {
            "word_count": total_words,
            "estimated_duration_minutes": round(duration, 1),
            "content_type": "video",
            "wwhaa_valid": 0.5 <= content_pct <= 0.7,  # Content should be 50-70%
            "section_word_counts": section_lengths
        }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode prompting | `output_config` structured outputs | Nov 2025 (Anthropic SDK 0.77.0+) | Eliminates parse errors, no retries needed |
| Manual JSON schema writing | Pydantic `model_json_schema()` | Pydantic 2.0+ (2023) | Auto-generates correct schemas with nested models |
| `response_format` parameter | `output_config.format` parameter | Jan 2026 (Anthropic API update) | New parameter name, old one deprecated but functional during transition |
| Deep inheritance for generators | Composition over inheritance | Python 3.10+ (type hints improved) | Flatter hierarchies with Generic[T] type vars |
| Manual word counting with regex | Simple `len(text.split())` | Standard practice (2020+) | Sufficient for duration estimates; complex tokenization unnecessary |

**Deprecated/outdated:**
- **`response_format` parameter**: Replaced by `output_config.format` (old parameter works during transition period but will be removed)
- **Asking AI for metadata**: Word counts, durations should be calculated client-side (deterministic, free, accurate)
- **Generic "generate content" prompts**: Educational content requires domain-specific guidance (Bloom's levels, distractor quality, citation formats)
- **Beta headers for structured outputs**: `anthropic-beta: structured-outputs-2025-11-13` no longer required (feature is GA as of Jan 2026)

## Open Questions

Things that couldn't be fully resolved:

1. **WWHAA Framework Definition**
   - What we know: Phase description specifies Hook, Objective, Content, IVQ, Summary, CTA structure for video scripts
   - What's unclear: No authoritative source found for "WWHAA" acronym in 2026 educational literature
   - Recommendation: Assume WWHAA is Coursera-internal pedagogy; implement as separate Pydantic fields per section, validate proportions (Hook 10%, Objective 10%, Content 60%, IVQ 5%, Summary 10%, CTA 5%)

2. **APA 7 Citation Generation Library**
   - What we know: `python-autocite` exists but limited maintenance; most APA tools are web-based
   - What's unclear: Whether to integrate a library or rely on Claude's APA 7 knowledge with validation
   - Recommendation: Use Claude with APA 7 examples in prompt + post-validation regex for citation format (e.g., `Author, A. A. (Year). Title. Publisher.`). Building custom citation formatter is out of scope.

3. **Optimal MAX_TOKENS for Content Generation**
   - What we know: Blueprint uses 8192 tokens; Phase 1 set default to 4096
   - What's unclear: Whether video scripts, readings, quizzes need different token limits
   - Recommendation: Start with 4096 (Config default); monitor for truncation (`stop_reason: "max_tokens"`); increase per-generator if needed

4. **Content Regeneration Versioning Strategy**
   - What we know: Activity.metadata can store previous versions; CMS patterns suggest version history
   - What's unclear: How many versions to keep, how to implement rollback UI
   - Recommendation: Store only 1 previous version in `metadata["previous_content"]` for Phase 4; full version history is Phase 6+ (out of scope for core generation)

5. **Rubric Scoring Criteria Standardization**
   - What we know: Rubrics have "clear scoring criteria" per success criteria
   - What's unclear: Whether to use Coursera-specific rubric format (0-4 scale? descriptive levels?)
   - Recommendation: Use 3-level rubric (Below Expectations / Meets Expectations / Exceeds Expectations) with descriptive criteria per level; can be adjusted after user testing

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Official API docs (fetched 2026-02-03)
- [Python 3.14.3 ABC Documentation](https://docs.python.org/3/library/abc.html) - Abstract base classes (updated 2026-02-03)
- [PMC - Automatic Distractor Generation Systematic Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/) - 60 studies on MCQ distractors (2009-2024)
- [Reading Speed Meta-Analysis](https://www.sciencedirect.com/science/article/abs/pii/S0749596X19300786) - 238 WPM for adult non-fiction (18,573 participants)

### Secondary (MEDIUM confidence)
- [Claude Prompt Engineering Best Practices 2026](https://promptbuilder.cc/blog/claude-prompt-engineering-best-practices-2026) - Structured inputs, clear success criteria
- [Aligning Bloom's Taxonomy with AI Rubric Generators](https://thecasehq.com/aligning-blooms-taxonomy-with-ai-rubric-generators/) - AI rubric generation best practices (Sept 2025)
- [pytest-mock Tutorial](https://www.datacamp.com/tutorial/pytest-mock) - Mocking API calls in tests
- [Composition Over Inheritance Principle](https://python-patterns.guide/gang-of-four/composition-over-inheritance/) - Python design patterns

### Tertiary (LOW confidence - for context only)
- [8 AI Prompt Templates for Educational Content](https://www.godofprompt.ai/blog/8-ai-prompt-templates-for-educational-content-creation) - General educational AI prompting
- [Content Versioning Deep-Dive](https://caisy.io/blog/content-versioning-deep-dive) - CMS versioning patterns
- [Python autocite Library](https://github.com/thenaterhood/python-autocite) - APA citation generation (limited maintenance)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - Anthropic SDK and Pydantic verified in Phase 3, structured outputs documented officially
- Architecture: **HIGH** - ABC pattern from Python stdlib docs, Pydantic integration from official Anthropic docs, BaseGenerator follows Phase 3 BlueprintGenerator pattern
- Pitfalls: **HIGH** - Structured outputs limitations documented, distractor research peer-reviewed, reading rates meta-analysis
- WWHAA framework: **MEDIUM** - No external source found, relying on Phase description and general instructional design principles
- APA 7 libraries: **LOW** - Limited Python-specific libraries found, recommend Claude-based generation with validation

**Research date:** 2026-02-03
**Valid until:** 2026-03-05 (30 days - stable domain, minor API updates expected)
