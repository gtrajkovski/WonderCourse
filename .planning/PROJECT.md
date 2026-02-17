# Course Builder Studio

## Current State

**Version:** v1.0 (shipped 2026-02-12)

Course Builder Studio v1.0 is complete. The platform generates complete Coursera short courses from high-level blueprints with:

- 11 content generators covering all activity types
- AI-powered blueprint generation
- Interactive AI coach with Socratic tutoring
- Multi-user collaboration with role-based permissions
- Export to instructor packages, LMS manifests, SCORM, and DOCX
- Full dark theme UI with onboarding and help system

**Milestone Archives:** `.planning/milestones/`

## What This Is

An AI-powered course development platform that handles the entire Coursera short course creation workflow: Plan (blueprint, outcomes, pacing) -> Build (11 content types including video scripts, readings, HOL activities, coach dialogues, quizzes, labs, textbook) -> Publish (instructor packages, LMS export). A standalone Flask app with proven patterns from ScreenCast Studio as its foundation.

## Core Value

Generate all content types for a complete Coursera short course from a high-level blueprint, with AI-powered generation, structural validation, and export-ready packaging.

## v1.0 Validated Requirements

All 90 requirements shipped and validated:

- **Infrastructure (4):** Disk persistence, path safety, Claude API, Flask app
- **Course Management (12):** CRUD, modules/lessons/activities, outcomes, WWHAA phases
- **Content Generation (13):** 11 generators + regeneration + inline editing
- **Quality & Validation (7):** Coursera validation, outcome alignment, Bloom's distribution, distractor analysis
- **Export & Publishing (5):** Instructor ZIP, LMS manifest, DOCX, SCORM, preview
- **Authentication (7):** Registration, login, sessions, isolation, profiles, password reset
- **Collaboration (5):** Invitations, roles, commenting, audit trail, activity feed
- **UI Pages (8):** Dashboard, planner, builder, studio, textbook, publish, dark theme, navigation
- **AI Inline Editing (8):** Suggestions, autocomplete, tone/clarity, Bloom's warnings, rewrite, undo/redo
- **Interactive Coach (8):** Chat interface, guardrails, Socratic method, evaluation, transcripts
- **Content Import (7):** Paste/upload, format parsing, AI analysis, conversion

## Next Milestone Goals

*(To be defined with `/gsd:new-milestone`)*

Potential v1.1 scope:
- Intelligence Suite (UDL menus, depth layers, inquiry arcs)
- Performance optimizations
- Additional export formats

## Constraints

- **Tech stack**: Python + Flask + Jinja2 + vanilla JS
- **AI provider**: Anthropic Claude API only
- **Port**: 5003
- **Persistence**: Disk-based JSON per project

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate repo from ScreenCast Studio | Clean separation, independent planning | Shipped v1.0 |
| Copy code from ScreenCast Studio | Proven patterns as foundation | Shipped v1.0 |
| Jinja + vanilla JS frontend | Faster to build, React migration later | Shipped v1.0 |
| Claude API only | Simplicity, no abstraction layer | Shipped v1.0 |
| Full system scope | All content types + exports + QA in v1 | Shipped v1.0 |
| course_data.json per project | Parallel to ScreenCast Studio pattern | Shipped v1.0 |

<details>
<summary>Original Context (v1.0 planning)</summary>

Course Builder Studio was born from ScreenCast Studio (C:\ScreencastHelper), a screencast production tool with mature patterns for AI-powered content generation. Key code copied as starting point:

- `src/core/models.py` -- Dataclasses with to_dict/from_dict serialization
- `src/core/store.py` -- ProjectStore disk persistence pattern
- `src/ai/client.py` -- Conversational AI client
- `src/utils/ai_client.py` -- One-shot AI client
- `src/config.py` -- Configuration constants pattern

The target is Coursera short courses (30-180 minutes, 2-3 modules, 1-3 learning outcomes). Content follows WWHAA instructional design and Bloom's taxonomy.

</details>

---
*Last updated: 2026-02-12 — v1.0 milestone complete*
