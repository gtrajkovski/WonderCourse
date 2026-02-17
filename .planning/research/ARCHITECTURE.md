# Architecture Research

**Domain:** AI-powered course development platform
**Researched:** 2026-02-02
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Web Layer (Flask)                                 │
│  Routes → Request Validation → Response Formatting                        │
├─────────────────────────────────────────────────────────────────────────┤
│                      Generation Orchestration                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Blueprint    │  │ Content Gen  │  │ Textbook     │                   │
│  │ Generator    │  │ Orchestrator │  │ Generator    │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
│         │                  │                  │                           │
├─────────┴──────────────────┴──────────────────┴───────────────────────────┤
│                      Generator Layer (Plugin-based)                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐     │
│  │ Video  │ │Reading │ │  HOL   │ │ Coach  │ │ Quiz   │ │  Lab   │ ... │
│  │  Gen   │ │  Gen   │ │  Gen   │ │  Gen   │ │  Gen   │ │  Gen   │     │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘     │
│      │          │          │          │          │          │           │
├──────┴──────────┴──────────┴──────────┴──────────┴──────────┴───────────┤
│                         AI Orchestration Layer                            │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  AI Router → Model Selection → Prompt Engineering → RAG Context  │     │
│  └─────────────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────────┤
│                       Validation & Analysis Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Outcome      │  │ Cognitive    │  │ Accessibility│                   │
│  │ Alignment    │  │ Load Check   │  │ Check        │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
│         │                  │                  │                           │
├─────────┴──────────────────┴──────────────────┴───────────────────────────┤
│                          Data & State Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  ProjectStore    │  │  Build State     │  │  Content Cache   │       │
│  │  (JSON on disk)  │  │  Tracker         │  │  (optional)      │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Web Layer** | HTTP handling, routing, template rendering | Flask routes with Blueprints for modularity |
| **Generation Orchestrator** | Coordinates multi-step content generation, manages build state | State machine tracking draft→generating→generated→reviewed→approved |
| **Generator Layer** | Content-type-specific generation logic | Base generator class with generate(), validate(), improve() methods |
| **AI Orchestration** | Model routing, prompt engineering, context injection | Request routing (simple→fast model, complex→capable model), RAG for domain knowledge |
| **Validation Layer** | Holistic quality checks across content | Post-generation validators for outcome coverage, WWHAA completeness, Bloom's distribution |
| **Data Layer** | Persistence, state tracking, caching | JSON files per project (course_data.json), optional vector DB for RAG |

## Recommended Project Structure

```
src/
├── web/                    # Flask application layer
│   ├── app.py             # Application factory
│   ├── routes/            # Blueprint-based routes
│   │   ├── courses.py     # Course CRUD
│   │   ├── blueprint.py   # Blueprint generation
│   │   ├── content.py     # Content generation
│   │   └── export.py      # Package export
│   └── templates/         # Jinja2 templates
├── core/                   # Domain models and storage
│   ├── models.py          # Course, Module, Lesson, Activity dataclasses
│   ├── store.py           # ProjectStore (disk persistence)
│   └── enums.py           # ContentType, BuildState, BloomLevel, etc.
├── generators/             # Content generation plugins
│   ├── base.py            # BaseGenerator abstract class
│   ├── video_generator.py # WWHAA video script generator
│   ├── reading_generator.py
│   ├── hol_generator.py
│   ├── coach_generator.py
│   ├── quiz_generator.py
│   ├── lab_generator.py
│   ├── textbook_generator.py
│   └── blueprint_generator.py
├── ai/                     # AI orchestration
│   ├── client.py          # Conversational AI client (chat, chat_stream)
│   ├── router.py          # Model selection based on complexity
│   ├── prompts.py         # Prompt templates per content type
│   └── improver.py        # Iterative improvement pattern
├── validators/             # Holistic validation
│   ├── outcome_mapper.py  # Outcome-activity alignment
│   ├── cognitive_load.py  # Cognitive load analysis
│   ├── accessibility.py   # Accessibility checker
│   └── distractor.py      # Quiz distractor quality
├── exporters/              # Package export
│   ├── instructor_package.py  # ZIP with syllabus, rubrics, etc.
│   ├── lms_manifest.py    # LMS export (JSON/IMS)
│   └── textbook_exporter.py   # DOCX textbook
├── utils/                  # Shared utilities
│   ├── file_handler.py    # Path safety (sanitize_id, safe_filename)
│   └── logger.py
└── config.py               # Configuration constants
```

### Structure Rationale

- **web/**: Isolates Flask-specific code; routes are Blueprints for clean separation
- **core/**: Framework-agnostic domain models; can be reused if migrating to another web framework
- **generators/**: Plugin architecture—each content type is self-contained; add new types without modifying existing code
- **ai/**: Centralizes AI concerns; router prevents coupling generators to specific models
- **validators/**: Holistic checks run after generation; keeps generators focused on single content types
- **exporters/**: Separate export logic from generation; supports multiple export formats

## Architectural Patterns

### Pattern 1: Generator Plugin Architecture

**What:** Each content type has a dedicated generator class implementing a common interface (BaseGenerator), with generate(), validate(), and improve() methods. Generators are stateless and dependency-injected with AI client and prompts.

**When to use:** When you have multiple content types with similar workflows but different domain logic. Prevents monolithic God classes and enables independent testing.

**Trade-offs:**
- ✅ Extensibility: Add new content types without modifying existing code
- ✅ Testability: Each generator can be unit-tested in isolation
- ✅ Maintainability: Domain logic is colocated by content type
- ⚠️ Complexity: More files/classes than a single generation function
- ⚠️ Discovery: Need a registry pattern to enumerate available generators

**Example:**
```python
# generators/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class GenerationResult:
    content: dict
    metadata: dict
    validation_passed: bool
    suggestions: list[str]

class BaseGenerator(ABC):
    def __init__(self, ai_client, prompt_template):
        self.ai_client = ai_client
        self.prompt_template = prompt_template

    @abstractmethod
    def generate(self, context: dict) -> GenerationResult:
        """Generate content from context."""
        pass

    @abstractmethod
    def validate(self, content: dict) -> tuple[bool, list[str]]:
        """Validate generated content against domain rules."""
        pass

    def improve(self, content: dict, feedback: str) -> GenerationResult:
        """Iteratively improve content based on feedback."""
        pass

# generators/video_generator.py
class VideoScriptGenerator(BaseGenerator):
    def generate(self, context: dict) -> GenerationResult:
        # WWHAA-specific logic
        prompt = self.prompt_template.format(**context)
        script = self.ai_client.generate(prompt)
        return GenerationResult(
            content={"script": script, "duration": estimate_duration(script)},
            metadata={"word_count": len(script.split())},
            validation_passed=self._validate_wwhaa(script),
            suggestions=[]
        )

    def validate(self, content: dict) -> tuple[bool, list[str]]:
        script = content["script"]
        issues = []
        # Check WWHAA structure
        if "## HOOK" not in script: issues.append("Missing HOOK section")
        if "## OBJECTIVE" not in script: issues.append("Missing OBJECTIVE section")
        # ... more checks
        return len(issues) == 0, issues
```

### Pattern 2: AI Orchestration with Model Routing

**What:** An orchestration layer sits between generators and AI providers, routing requests to appropriate models based on complexity (simple queries → fast/cheap model, complex reasoning → capable/expensive model).

**When to use:** When AI costs matter and you have a mix of simple and complex generation tasks. Reduces costs by 60-70% without impacting quality (per 2026 research).

**Trade-offs:**
- ✅ Cost optimization: Avoid using expensive models for trivial tasks
- ✅ Performance: Fast models respond quicker for simple requests
- ✅ Future-proof: Swap models without changing generators
- ⚠️ Complexity categorization: Need heuristics or metadata to classify request complexity

**Example:**
```python
# ai/router.py
class AIRouter:
    def __init__(self, fast_model="claude-haiku", capable_model="claude-sonnet-4"):
        self.fast_model = fast_model
        self.capable_model = capable_model

    def route_request(self, request_type: str, prompt: str, context: dict) -> str:
        """Route to appropriate model based on request complexity."""
        complexity = self._assess_complexity(request_type, prompt, context)

        if complexity == "simple":
            return self.fast_model
        elif complexity == "complex":
            return self.capable_model
        else:  # medium
            return self.fast_model  # Default to cheaper option

    def _assess_complexity(self, request_type: str, prompt: str, context: dict) -> str:
        # Heuristics for complexity
        if request_type in ["quiz_question", "discussion_prompt"]:
            return "simple"
        if request_type in ["textbook_chapter", "coach_dialogue"]:
            return "complex"
        if len(prompt) > 2000 or context.get("requires_reasoning"):
            return "complex"
        return "medium"
```

### Pattern 3: Two-Phase Validation (Individual + Holistic)

**What:** Generators perform individual content validation (e.g., WWHAA section presence), then holistic validators check cross-content properties (outcome coverage, WWHAA distribution, cognitive load balance).

**When to use:** When content items must work together as a system, not just individually. Common in instructional design where learning outcomes must be covered across multiple activities.

**Trade-offs:**
- ✅ Comprehensive: Catches both local and systemic issues
- ✅ Separation of concerns: Generators focus on single content, validators focus on course-level
- ✅ Actionable feedback: Can identify gaps ("Outcome 3 has no Apply activities")
- ⚠️ Two-pass process: Holistic validation happens after all content is generated
- ⚠️ Rework risk: Late-stage holistic failures may require regenerating multiple items

**Example:**
```python
# validators/outcome_mapper.py
class OutcomeMapper:
    def validate_coverage(self, course: Course) -> dict:
        """Validate learning outcome coverage across activities."""
        coverage = {outcome.id: {"count": 0, "bloom_levels": set(), "wwhaa_phases": set()}
                    for outcome in course.learning_outcomes}

        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    for outcome_id in activity.aligned_outcomes:
                        coverage[outcome_id]["count"] += 1
                        coverage[outcome_id]["bloom_levels"].add(activity.bloom_level)
                        coverage[outcome_id]["wwhaa_phases"].add(activity.wwhaa_phase)

        gaps = []
        for outcome_id, data in coverage.items():
            if data["count"] == 0:
                gaps.append(f"Outcome {outcome_id} has no aligned activities")
            if "APPLY" not in data["wwhaa_phases"]:
                gaps.append(f"Outcome {outcome_id} has no Apply activities")
            if "REMEMBER" in data["bloom_levels"] and len(data["bloom_levels"]) == 1:
                gaps.append(f"Outcome {outcome_id} only targets low-level Bloom's")

        return {
            "coverage": coverage,
            "gaps": gaps,
            "score": 100 - (len(gaps) * 10)  # Deduct 10 points per gap
        }
```

### Pattern 4: RAG-Enhanced Generation with Domain Context

**What:** Retrieval-Augmented Generation injects relevant domain knowledge (e.g., Coursera style guides, instructional design best practices, example content) into prompts before generation.

**When to use:** When generated content must follow domain-specific conventions that aren't in the base LLM's training. Essential for specialized domains like instructional design.

**Trade-offs:**
- ✅ Consistency: Generated content follows organizational style guides
- ✅ Accuracy: Reduces hallucinations by grounding in retrieved facts
- ✅ Few-shot learning: Examples from knowledge base improve quality
- ⚠️ Latency: Retrieval adds 100-300ms overhead
- ⚠️ Infrastructure: Requires vector database or search index

**Example:**
```python
# ai/rag_context.py
class RAGContext:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def enrich_prompt(self, base_prompt: str, content_type: str, query: str) -> str:
        """Retrieve relevant examples and inject into prompt."""
        # Retrieve top-3 relevant examples
        examples = self.vector_store.search(
            query=f"{content_type} examples: {query}",
            top_k=3
        )

        # Retrieve style guidelines
        guidelines = self.vector_store.search(
            query=f"{content_type} style guide",
            top_k=1
        )

        # Construct enriched prompt
        context = "\n\n".join([
            "# Style Guidelines",
            guidelines[0]["text"],
            "\n# Examples",
            *[f"## Example {i+1}\n{ex['text']}" for i, ex in enumerate(examples)]
        ])

        return f"{context}\n\n# Task\n{base_prompt}"
```

### Pattern 5: Build State Machine with Rollback

**What:** Content items transition through states (draft → generating → generated → reviewed → approved → published) with rollback capability. State transitions are logged for auditability.

**When to use:** When generation is multi-step, expensive, and may fail. Users need visibility into progress and ability to revert bad generations.

**Trade-offs:**
- ✅ User visibility: Clear progress indication
- ✅ Error recovery: Can retry failed generations without losing state
- ✅ Audit trail: Know when each piece of content was generated/approved
- ⚠️ State management complexity: Need to handle concurrent state transitions
- ⚠️ Storage overhead: Must persist state history

**Example:**
```python
# core/state_tracker.py
from enum import Enum
from datetime import datetime

class BuildState(Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"

class StateTracker:
    def __init__(self, store):
        self.store = store

    def transition(self, item_id: str, from_state: BuildState, to_state: BuildState) -> bool:
        """Transition item state with validation."""
        item = self.store.get_item(item_id)

        if item.state != from_state:
            raise ValueError(f"Item is in {item.state}, expected {from_state}")

        # Validate transition
        valid_transitions = {
            BuildState.DRAFT: [BuildState.GENERATING],
            BuildState.GENERATING: [BuildState.GENERATED, BuildState.DRAFT],  # Can fail back to draft
            BuildState.GENERATED: [BuildState.REVIEWED, BuildState.GENERATING],  # Can regenerate
            BuildState.REVIEWED: [BuildState.APPROVED, BuildState.GENERATING],
            BuildState.APPROVED: [BuildState.PUBLISHED, BuildState.REVIEWED],
        }

        if to_state not in valid_transitions.get(from_state, []):
            raise ValueError(f"Invalid transition {from_state} → {to_state}")

        # Record transition
        item.state = to_state
        item.state_history.append({
            "from": from_state.value,
            "to": to_state.value,
            "timestamp": datetime.utcnow().isoformat()
        })

        self.store.save_item(item)
        return True
```

## Data Flow

### Generation Request Flow

```
User Request (UI or API)
    ↓
Route Handler → Validate Input → Check Auth (if applicable)
    ↓
Generation Orchestrator
    ↓
    ├──→ Load Course Context from ProjectStore
    ├──→ Check Build State (can we generate?)
    └──→ Select Generator based on content_type
            ↓
        Generator.generate()
            ↓
            ├──→ AI Router → Select Model (fast vs capable)
            ├──→ RAG Context → Retrieve Examples/Guidelines
            └──→ AI Client → Generate Content
                    ↓
                Individual Validation (Generator.validate())
                    ↓
                    ├─✅─→ Mark as "generated"
                    └─❌─→ Return errors, stay in "draft"
                            ↓
                        Update Build State → Save to ProjectStore
                            ↓
                        Return Response to UI
```

### Holistic Validation Flow

```
User Triggers "Validate Course"
    ↓
Load Full Course from ProjectStore
    ↓
Parallel Validation Checks:
    ├──→ OutcomeMapper.validate_coverage()
    ├──→ CognitiveLoadAnalyzer.analyze()
    ├──→ AccessibilityChecker.check()
    └──→ WWHAAValidator.check_distribution()
            ↓
        Aggregate Results
            ↓
        Generate Report
            ├─ Gaps: ["Outcome 2 has no Apply activities"]
            ├─ Warnings: ["Module 1 exceeds cognitive load threshold"]
            └─ Scores: {outcome_coverage: 85, accessibility: 95, wwhaa_balance: 78}
                    ↓
                Return Report to UI
```

### Export Flow

```
User Requests Export
    ↓
Check All Content is in "approved" state
    ↓
    ├─❌─→ Return error "Cannot export with unapproved content"
    └─✅─→ Continue
            ↓
        Select Exporter (InstructorPackage, LMSManifest, TextbookExporter)
            ↓
        Exporter.export()
            ├──→ Generate Syllabus
            ├──→ Generate Lesson Plans
            ├──→ Generate Rubrics
            ├──→ Compile Quizzes
            ├──→ Format Textbook (DOCX)
            └──→ Create ZIP archive
                    ↓
                Save to projects/{id}/exports/
                    ↓
                Return Download URL
```

### Key Data Flows

1. **Blueprint Generation Flow:** User inputs → AI generates full course structure (modules, lessons, placeholder activities) → ProjectStore saves → UI displays tree
2. **Outcome Alignment Flow:** User assigns outcomes to activities → OutcomeMapper validates coverage → UI displays coverage matrix with gaps highlighted
3. **Iterative Improvement Flow:** User provides feedback → Improver.improve() regenerates content → Validator checks → State updated

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-50 courses** | Monolith with disk-based JSON storage; all generators in-process; single Flask server |
| **50-500 courses** | Add Redis for build state caching; move long-running generations (textbook, blueprint) to background tasks (Celery); keep disk storage but add indexes |
| **500-5000 courses** | Migrate to PostgreSQL with JSONB for course data; horizontal scaling with load balancer; dedicated RAG service with vector DB (Pinecone, Weaviate); separate export workers |
| **5000+ courses** | Microservices architecture (generation service, validation service, export service); event-driven orchestration (Kafka); CDN for exported packages; multi-region deployment |

### Scaling Priorities

1. **First bottleneck (50-100 courses):** Long-running textbook generation blocks UI → Move to background tasks with job queue (Celery + Redis). Estimated fix time: 1 week.
2. **Second bottleneck (500-1000 courses):** Disk I/O for course_data.json becomes slow → Migrate to PostgreSQL with JSONB columns. Estimated migration: 2 weeks.
3. **Third bottleneck (2000+ courses):** AI API rate limits hit → Implement request batching and smart caching (deduplicate similar prompts). Estimated implementation: 1 week.

## Anti-Patterns

### Anti-Pattern 1: Generators Directly Calling LLM APIs

**What people do:** Each generator imports `anthropic` SDK and calls `client.messages.create()` directly.

**Why it's wrong:**
- Tight coupling to Anthropic; impossible to switch providers
- No request routing (always use expensive model)
- Duplicated retry logic, error handling, prompt versioning
- Difficult to mock for testing

**Do this instead:** Inject an AI client abstraction (`AIClient` interface) that handles provider details, model routing, retries, and prompt management. Generators call `self.ai_client.generate(prompt_template, context)`.

### Anti-Pattern 2: Validating Only After All Content Generated

**What people do:** Generate all 30+ activities, then run holistic validation. Discover Outcome 2 has no Apply activities. Now must regenerate multiple items.

**Why it's wrong:**
- Late feedback causes expensive rework
- User wastes time waiting for full generation
- Cascading failures (one bad outcome coverage affects multiple activities)

**Do this instead:** Incremental validation. After each activity is generated, check partial coverage. If Outcome 2 needs Apply but none exists yet, prompt user to generate an Apply activity next. "Just-in-time" validation guides generation toward valid state.

### Anti-Pattern 3: Storing Generated Content Only, Not Prompts

**What people do:** Save generated video script to database, discard the prompt and context used to generate it.

**Why it's wrong:**
- Cannot reproduce generation (debugging impossible)
- Cannot iterate on prompts to improve quality
- Cannot explain why AI generated specific content
- A/B testing prompts requires regenerating entire corpus

**Do this instead:** Store generation metadata alongside content: `{content: "...", prompt_template_id: "v3.2", prompt_variables: {...}, model: "claude-sonnet-4", timestamp: "..."}`. Enables prompt versioning, reproducibility, debugging.

### Anti-Pattern 4: Synchronous Generation Blocking UI

**What people do:** User clicks "Generate Textbook" → Flask route calls `TextbookGenerator.generate()` → 45 seconds later, response returns.

**Why it's wrong:**
- Terrible UX (user thinks app froze)
- HTTP timeout risk (some proxies kill >30s requests)
- Cannot show progress updates
- User cannot cancel

**Do this instead:** Asynchronous job pattern. User clicks "Generate" → API returns `{job_id: "abc123", status: "queued"}` immediately → Background worker processes job → Frontend polls `/api/jobs/abc123` for progress → When complete, fetch result. Bonus: WebSocket for real-time updates.

### Anti-Pattern 5: No Versioning for Generated Content

**What people do:** User generates video script, reviews it, approves it. Later, regenerates it (accidentally or to try improvements). Old approved version is lost.

**Why it's wrong:**
- Cannot compare versions (which was better?)
- Accidental overwrites destroy approved content
- No audit trail (who changed what when)

**Do this instead:** Version each generation. Store as `{activity_id: "xyz", versions: [{v: 1, content: "...", state: "approved"}, {v: 2, content: "...", state: "draft"}]}`. Always create new version, never overwrite. UI shows version history with diff viewer.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Anthropic Claude API** | HTTP REST via `anthropic` SDK | Rate limits: 4000 req/min (Tier 3); implement exponential backoff |
| **Vector DB (optional)** | HTTP/gRPC for RAG retrieval | Pinecone, Weaviate, or Qdrant; only needed if using RAG pattern |
| **Document Export** | `python-docx` for DOCX, future PDF | DOCX generation is synchronous; PDF requires `weasyprint` (heavy dependency) |
| **LMS APIs** | Future integration for direct publish | Canvas API, Moodle API; start with JSON export, add API later |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Web ↔ Orchestrator** | Direct function calls | Orchestrator is application service layer |
| **Orchestrator ↔ Generators** | Dependency injection | Orchestrator instantiates generators with AI client |
| **Generators ↔ AI Client** | Interface abstraction | Generators never import `anthropic` directly |
| **Validators ↔ ProjectStore** | Direct data access | Validators read full course to analyze |
| **Exporters ↔ ProjectStore** | Direct data access | Exporters read approved content only |

## Build Order and Dependencies

### Suggested Build Order

Based on architectural dependencies and risk, build in this order:

**Phase 0: Foundation (Week 1)**
1. Core models (Course, Module, Lesson, Activity dataclasses)
2. ProjectStore (disk persistence with path safety)
3. Flask app skeleton (routes structure, templates)
4. AI client abstraction (no RAG, just basic prompt→response)

**Phase 1: Basic Generation (Week 2)**
5. BaseGenerator abstract class
6. VideoScriptGenerator (WWHAA validation)
7. ReadingGenerator
8. Build state tracker (draft→generating→generated)
9. UI for triggering generation and viewing results

**Phase 2: Expand Content Types (Week 3-4)**
10. QuizGenerator (MCQ with distractors)
11. HOLGenerator
12. CoachGenerator
13. LabGenerator
14. DiscussionGenerator
15. AssignmentGenerator
16. ProjectMilestoneGenerator

**Phase 3: Blueprint & Orchestration (Week 5)**
17. BlueprintGenerator (full course structure from high-level input)
18. AI Router (model selection based on complexity)
19. Generation orchestrator (coordinate multi-step workflows)

**Phase 4: Holistic Validation (Week 6)**
20. OutcomeMapper (coverage analysis)
21. CognitiveLoadAnalyzer
22. AccessibilityChecker
23. DistractorQualityChecker
24. WWHAAValidator
25. Validation dashboard UI

**Phase 5: Textbook (Week 7)**
26. TextbookGenerator (chapter-by-chapter generation)
27. TextbookExporter (DOCX with images, references)
28. Background job system (Celery + Redis)

**Phase 6: Export & Polish (Week 8)**
29. InstructorPackageExporter (ZIP with syllabus, rubrics, etc.)
30. LMSManifestExporter (JSON)
31. Iterative improver (feedback→regenerate→rescore loop)
32. Final UI polish (dark theme, progress indicators)

### Dependency Rationale

- **Models before generators:** Generators need type definitions
- **ProjectStore before generators:** Generators need to persist results
- **BaseGenerator before specific generators:** Avoids code duplication
- **Basic generation before blueprint:** Blueprint needs to create Activities, so Activity model and basic generators must exist
- **Individual generators before holistic validation:** Cannot validate outcome coverage until activities exist
- **Textbook late:** Most complex generator, depends on all learning outcomes being defined
- **Export last:** Requires all content to be generated and approved

### Critical Path

The critical dependency chain is:
1. Core models → ProjectStore → AI client → BaseGenerator → VideoScriptGenerator → Blueprint → Validation → Export

Everything else can be built in parallel off this spine. For example, QuizGenerator, HOLGenerator, and CoachGenerator have no dependencies on each other and can be developed simultaneously.

## Sources

### AI Architecture & Orchestration
- [AI System Design Patterns for 2026: Architecture That Scales](https://zenvanriel.nl/ai-engineer-blog/ai-system-design-patterns-2026/)
- [In 2026, AI Is Merging With Platform Engineering. Are You Ready? - The New Stack](https://thenewstack.io/in-2026-ai-is-merging-with-platform-engineering-are-you-ready/)
- [Implementing Generative AI: A Pipeline Architecture | by NeuroCortex.AI | Medium](https://medium.com/@neurocortexai/implementing-generative-ai-a-pipeline-architecture-7321e0a5cec4)
- [What is an AI Pipeline? +5 Use Cases & Examples in 2026 | Lindy](https://www.lindy.ai/blog/ai-pipeline)

### RAG Best Practices
- [Designing a Production-Grade RAG Architecture | Level Up Coding](https://levelup.gitconnected.com/designing-a-production-grade-rag-architecture-bee5a4e4d9aa)
- [RAG in 2026: A Practical Blueprint for Retrieval-Augmented Generation - DEV Community](https://dev.to/suraj_khaitan_f893c243958/-rag-in-2026-a-practical-blueprint-for-retrieval-augmented-generation-16pp)
- [Enhancing Retrieval-Augmented Generation: A Study of Best Practices](https://arxiv.org/abs/2501.07391)
- [Retrieval-Augmented Generation: A Comprehensive Survey](https://arxiv.org/html/2506.00054v1)

### Validation & Data Quality
- [The continuous validation framework for data pipelines](https://platformengineering.org/blog/the-continuous-validation-framework-for-data-pipelines)
- [Data Validation in ETL - 2026 Guide | Integrate.io](https://www.integrate.io/blog/data-validation-etl/)
- [Why data validation is critical to your pipelines • Great Expectations](https://greatexpectations.io/blog/why-data-validation-is-critical-to-your-pipelines/)

### Flask Architecture
- [How To Structure a Large Flask Application-Best Practices for 2025 - DEV Community](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
- [Structuring a Large Production Flask Application | Level Up Coding](https://levelup.gitconnected.com/structuring-a-large-production-flask-application-7a0066a65447)
- [Flask - Full Stack Python](https://www.fullstackpython.com/flask.html)
- [Patterns for Flask — Flask Documentation](https://flask.palletsprojects.com/en/stable/patterns/)

### Instructional Design & Learning Analytics
- [System Design and Evaluation of RAG-Enhanced Digital Humans in Design Education](https://www.mdpi.com/2076-3417/16/2/1068)
- [Instructional Design In 2026: What To Master Beyond The Hype - eLearning Industry](https://elearningindustry.com/beyond-the-hype-what-instructional-designers-really-need-to-master-in-2026)
- [Bloom's Taxonomy for Learning Outcomes - University of Utah](https://us.utah.edu/learning-outcomes-assessment/blooms-taxonomy.php)
- [Using Bloom's Taxonomy to Write Effective Learning Objectives](https://tips.uark.edu/using-blooms-taxonomy/)

### Design Patterns
- [Understanding Dependency Injection: A Powerful Design Pattern | Medium](https://medium.com/@sardar.khan299/understanding-dependency-injection-a-powerful-design-pattern-for-flexible-and-testable-code-5e1161dd37dd)
- [Microservices Design Patterns - GeeksforGeeks](https://www.geeksforgeeks.org/system-design/microservices-design-patterns/)
- [Design Patterns for Microservices - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/patterns)

---
*Architecture research for: AI-powered course development platform*
*Researched: 2026-02-02*
