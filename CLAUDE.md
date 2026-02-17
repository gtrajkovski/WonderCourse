# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WonderCourse is an AI-powered adaptive learning platform (v2.0 evolution of Course Builder Studio). It generates complete online courses with 12+ content types, featuring:
- **Intelligence Suite**: UDL menus, depth layers, inquiry arcs
- **Adaptive Learning**: prerequisite assessment, mastery-based progression
- **AI Media Integration**: image/video generation
- Structural validation and export-ready packaging

Standalone Flask app, single-user localhost tool. See `.planning/v2.0-IDEAS.md` for the full roadmap.

## Commands

```bash
# Run app
python app.py                        # Flask dev server on port 5003

# Tests (~85 test files)
pytest                               # Run all tests
pytest tests/test_models.py          # Single test file
pytest tests/test_models.py::test_name  # Single test
pytest -k "quiz"                     # Run tests matching keyword

# Dependencies
pip install -r requirements.txt
```

## Architecture

**Layered structure in `src/`:**

- **`src/core/`** - Framework-agnostic domain layer
  - `models.py` - Core dataclasses (Course, Module, Lesson, Activity, LearningOutcome, TextbookChapter, CompletionCriteria, AuditIssue, AuditResult) with 10 enums (ContentType, ActivityType, BuildState, BloomLevel, WWHAAPhase, FlowMode, PageType, AuditCheckType, AuditSeverity, AuditIssueStatus). All models use `from_dict()` class methods that filter unknown fields for schema evolution.
  - `project_store.py` - Disk persistence via JSON files in `projects/{course_id}/course_data.json`. Uses platform-specific file locking for concurrent write safety. Saves atomically after every operation.
  - `standards_store.py` - Standards profile persistence with system presets (Coursera, Flexible, Corporate).

- **`src/api/`** - Flask Blueprints for REST endpoints (modules, lessons, activities, learning_outcomes, blueprint, content, build_state, job_tracker, standards, flow_control). Each blueprint uses `init_*_bp(project_store)` pattern for dependency injection.

- **`src/generators/`** - Content generation using Claude structured outputs
  - `base_generator.py` - Abstract `BaseGenerator[T]` class using tool-based structured outputs. Subclasses implement `system_prompt`, `build_user_prompt()`, and `extract_metadata()`.
  - 15 generators: video_script, reading, quiz, practice_quiz, rubric, hol, coach, lab, discussion, assignment, project, textbook, blueprint, course_page, screencast
  - `schemas/` - Pydantic models for each content type with validation constraints

- **`src/validators/`** - Course structure validation against Coursera requirements
  - `standards_validator.py` - Content validation against standards profiles with severity levels (ERROR, WARNING, INFO)

- **`src/ai/`** - `AIClient` wraps Anthropic SDK with conversation history management. Supports streaming and non-streaming. `src/utils/ai_client.py` provides a stateless generation helper.

- **`src/utils/`** - Shared utilities including `content_metadata.py` (duration calculations), `coherence_validator.py` (textbook coherence checks), `content_humanizer.py` (AI text humanization), and `preview_renderer.py` (learner/author view modes).

- **`src/exporters/`** - Export format handlers: SCORM packages, DOCX textbooks, instructor packages, LMS manifests.

- **`src/auth/`** - Authentication layer with Flask-Login integration, password reset tokens, rate limiting on auth endpoints.

- **`src/collab/`** - Collaboration features: permissions (owner/editor/viewer roles), invitations, comments, audit logging.

- **`src/import/`** - Content import system with parsers for DOCX, HTML, SCORM, Markdown, CSV, QTI formats. URL fetcher for remote content.

- **`src/coach/`** - Interactive coaching system: persona management, conversation state, student evaluation.

- **`src/editing/`** - Content editing: diff generation, version history, autocomplete suggestions.

- **`src/config.py`** - Single `Config` class reading from `.env`. Key values: `ANTHROPIC_API_KEY`, `MODEL` (default `claude-sonnet-4-20250514`), `MAX_TOKENS` (4096), `PORT` (5003). Includes Coursera-specific constants (duration limits, word counts).

**Entry point:** `app.py` registers all blueprints, initializes `ProjectStore` and `AIClient` as module-level singletons, serves Jinja2 templates.

**Frontend:** Jinja2 templates + vanilla JS with dark theme (#1a1a2e background). Templates in `templates/`, CSS in `static/css/`.

## Key Patterns

- **API responses:** Direct JSON (not `{"status": "success/error", "data": ...}` wrapper)
- **Serialization:** `to_dict()` converts recursively with enum-to-string; `from_dict()` filters unknown fields for schema evolution
- **Testing:** Mock `base_generator.Anthropic` for generator tests (no real API calls). Use `authenticated_client` or `client` fixtures for API tests; both provide logged-in sessions.
- **Data hierarchy:** Course → Modules → Lessons → Activities (each level has ordered children)
- **Build state:** DRAFT → GENERATING → GENERATED → REVIEWED → APPROVED → PUBLISHED
- **Content dispatch order:** Practice quiz check MUST precede generic quiz check (both use ContentType.QUIZ, distinguished by ActivityType). See `src/api/content.py` dispatch chain.

## v1.1 Features

**Configurable Content Standards (Phase 1):**
- `ContentStandardsProfile` model with 50+ configurable fields for all content types
- System presets: Coursera (strict), Flexible (lenient), Corporate (formal)
- Standards injection into all generators via `standards_rules` parameter
- Validation API to check content against profiles

**Flow Control & Completion Criteria (Phase 2):**
- `FlowMode` enum: SEQUENTIAL (must complete in order) vs OPEN (any order)
- `CompletionCriteria` dataclass with activity-type-specific rules (video_watch_percent, quiz_passing_score, etc.)
- Activity prerequisites via `prerequisite_ids` list
- Flow control API: `/api/courses/<id>/flow-mode`, `/api/courses/<id>/activities/<id>/prerequisites`

**Auto-Generated Course Pages (Phase 3):**
- `PageType` enum: SYLLABUS, ABOUT, RESOURCES
- Course page generator creates markdown content for each page type
- API: `/api/courses/<id>/pages/<type>` for generation and retrieval

**Course Audit & Quality System (Phase 4):**
- `AuditCheckType` enum: FLOW_ANALYSIS, REPETITION, OBJECTIVE_ALIGNMENT, CONTENT_GAPS, DURATION_BALANCE, BLOOM_PROGRESSION
- `CourseAuditor` class in `src/validators/course_auditor.py` runs quality checks
- Audit API: `/api/courses/<id>/audit` for running audits and retrieving results
- Issue tracking with status workflow (OPEN, IN_PROGRESS, RESOLVED, WONT_FIX, FALSE_POSITIVE)

**AI Text Humanization Engine (Phase 5):**
- `ContentHumanizer` in `src/utils/content_humanizer.py` traverses Pydantic schemas
- `humanize_content()` and `get_content_score()` functions
- ContentStandardsProfile humanization settings (enable_auto_humanize, threshold, etc.)
- Auto-humanize in content generation pipeline
- API: `/api/courses/<id>/activities/<id>/humanize` and `/humanize/score`
- Studio UI: score ring, humanize button, pattern viewer

**Developer Notes + Preview Mode (Phase 6):**
- `DeveloperNote` dataclass with pinned flag and author tracking
- `developer_notes` field on Activity, Lesson, Module, Course
- Notes API: CRUD at all levels with pin/sort functionality
- Preview mode toggle (Author/Learner views) with viewport selector (Desktop/Tablet/Mobile)
- `PreviewRenderer` utility in `src/utils/preview_renderer.py` strips author-only elements

**Video Lesson Studio (Phase 7):**
- `section_timings` metadata in video script generator
- `VideoStudio` component with teleprompter auto-scroll playback
- Speed control (0.5x-2x), section navigation, speaker notes overlay
- Keyboard shortcuts: Space (play/pause), arrows (nav/speed), N (notes), F (fullscreen)
- Full-screen presentation mode for recording

**Progress Dashboard (Phase 8):**
- Enhanced `/api/courses/<id>/progress` with content_metrics, by_content_type, by_module, quality
- Dashboard page with completion ring, build state distribution, module progress bars
- Content type breakdown with completion overlay
- Filterable activity table (All/Draft/Generated/Approved)

## Content Generation

Generators use Claude's tool-based structured outputs:
```python
tools = [{
    "name": "output_structured",
    "description": "Output the generated content in structured format",
    "input_schema": schema.model_json_schema()
}]
response = self.client.messages.create(
    model=self.model,
    max_tokens=Config.MAX_TOKENS,
    system=self.system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    tools=tools,
    tool_choice={"type": "tool", "name": "output_structured"}
)
```

Duration calculations use industry-standard rates (238 WPM reading, 150 WPM video speaking, 1.5 min/quiz question).

## Writing Style for Generated Content

Generated content should sound naturally written, not AI-generated. Avoid these AI telltales:
- Em-dashes (—) — replace with commas, periods, or restructure
- Formal vocabulary ("utilize", "facilitate", "comprehensive") — use plain words
- Three-adjective lists ("structured, hierarchical, and ready") — reduce to two or rephrase
- Overly parallel structures — rough them up slightly
- AI transitions ("Here's where it gets powerful", "Let's bring this together")

## Environment Setup

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. The app runs without an API key but AI features will be disabled (health endpoint reports `ai_enabled: false`).

## Project Status

**Current:** v1.1 Expansion complete (all 8 phases committed)

Planning documentation lives in `.planning/` (PROJECT.md, ROADMAP.md, STATE.md). v1.0 and v1.1 archives in `.planning/milestones/`.
