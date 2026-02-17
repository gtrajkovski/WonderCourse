# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WonderCourse is an AI-powered adaptive learning platform that generates complete online courses with 15 content types. Standalone Flask app (port 5003), single-user localhost tool. v2.0 focus: UDL menus, depth layers, inquiry arcs, mastery-based progression.

See `.planning/v2.0-IDEAS.md` for the roadmap.

## Commands

```bash
python app.py                           # Flask dev server on port 5003
pytest                                   # All tests (~85 files)
pytest tests/test_models.py              # Single file
pytest tests/test_models.py::test_name   # Single test
pytest -k "quiz"                         # Keyword match
pip install -r requirements.txt          # Dependencies
```

## Architecture

**Entry point:** `app.py` registers blueprints, initializes `ProjectStore` and `AIClient` singletons.

**src/core/** - Domain layer
- `models.py` - Dataclasses (Course, Module, Lesson, Activity, etc.) with 10 enums. All use `from_dict()` that filters unknown fields for schema evolution.
- `project_store.py` - JSON persistence in `projects/{course_id}/course_data.json` with file locking.
- `standards_store.py` - Standards profiles with presets (Coursera, Flexible, Corporate).

**src/api/** - Flask Blueprints using `init_*_bp(project_store)` dependency injection pattern.

**src/generators/** - 15 content generators using Claude structured outputs
- `base_generator.py` - Abstract `BaseGenerator[T]` class. Subclasses implement `system_prompt`, `build_user_prompt()`, `extract_metadata()`.
- `schemas/` - Pydantic models with validation constraints.

**src/validators/** - Course structure and content validation with severity levels (ERROR, WARNING, INFO).

**src/ai/** - `AIClient` wraps Anthropic SDK with conversation history. `src/utils/ai_client.py` provides stateless helper.

**Other directories:** `exporters/` (SCORM, DOCX, LMS), `auth/` (Flask-Login, rate limiting), `collab/` (roles, invitations, comments), `importers/` (DOCX, HTML, SCORM, QTI parsers), `coach/` (Socratic tutoring), `editing/` (diff, history, autocomplete), `utils/` (duration calc, humanization, preview).

**Frontend:** Jinja2 + vanilla JS with dark theme (#1a1a2e).

**Config:** `src/config.py` reads from `.env`. Key: `ANTHROPIC_API_KEY`, `MODEL` (default `claude-sonnet-4-20250514`), `PORT` (5003).

## Key Patterns

**API responses:** Direct JSON, no wrapper object.

**Serialization:** `to_dict()` recursively converts enums to strings; `from_dict()` filters unknown fields.

**Data hierarchy:** Course → Modules → Lessons → Activities (ordered children at each level).

**Build states:** DRAFT → GENERATING → GENERATED → REVIEWED → APPROVED → PUBLISHED

**Content dispatch:** Practice quiz check MUST precede generic quiz check in `src/api/content.py` (both use ContentType.QUIZ, distinguished by ActivityType).

**Testing generators:** Mock `base_generator.Anthropic` to avoid real API calls:
```python
mock_client = mocker.patch('src.generators.base_generator.Anthropic')
```

**Testing APIs:** Use `client` or `authenticated_client` fixtures (both provide logged-in sessions with temp database/project store).

## Content Generation

Generators use tool-based structured outputs:
```python
tools = [{
    "name": "output_structured",
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

Duration rates: 238 WPM reading, 150 WPM video, 1.5 min/quiz question.

## Writing Style for Generated Content

Avoid AI-sounding patterns:
- Em-dashes: replace with commas or periods
- Formal words: "utilize" → "use", "facilitate" → "help"
- Triple adjective lists: "clear, concise, and actionable" → "clear and actionable"
- Forced parallelism: vary sentence structure
- Meta-commentary: "Here's where it gets interesting", "Let's dive in"

## v1.1 Feature Summary

- **Standards Engine:** Configurable profiles (50+ fields), presets, validation
- **Flow Control:** SEQUENTIAL/OPEN modes, prerequisites, completion criteria
- **Course Pages:** Auto-generated syllabus, about, resources
- **Audit System:** Quality checks (flow, repetition, alignment, gaps, duration, Bloom's)
- **Humanization:** AI text scoring and auto-humanize pipeline
- **Developer Notes:** Pinnable notes at all levels, preview mode (Author/Learner)
- **Video Studio:** Teleprompter, speed control, section nav, keyboard shortcuts
- **Progress Dashboard:** Completion metrics, build state distribution, filtering

## Environment Setup

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. App runs without key but AI features are disabled.

## v2.0 Features (In Progress)

**Phase 1: Content Variants & Depth Layers**
- `VariantType` enum: PRIMARY, TRANSCRIPT, AUDIO_ONLY, ILLUSTRATED, INFOGRAPHIC, GUIDED, CHALLENGE, SELF_CHECK
- `DepthLevel` enum: ESSENTIAL (key points), STANDARD (full), ADVANCED (extended)
- `ContentVariant` dataclass stores variant content with generation tracking
- `Activity.content_variants` list for UDL alternatives (lazy populated)
- Variant API: `/api/courses/<id>/activities/<id>/variants`
- `TranscriptVariantGenerator` transforms video scripts to transcripts

**Phase 2: UDL Implementation**
- Variant selector UI in Studio page (tabs + depth pills)
- Generate variant modal for on-demand generation
- `AudioNarrationGenerator` for TTS-optimized narration scripts
- Learner preference mapping (`PREFERENCE_TO_VARIANTS`)
- Recommended variants endpoint: `/api/courses/<id>/activities/<id>/variants/recommended`

## Project Status

v2.0-dev (Phase 2 UDL Implementation complete). Planning docs in `.planning/` (PROJECT.md, ROADMAP.md, v2.0-IDEAS.md).
