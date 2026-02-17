# WonderCourse

## Current State

**Version:** v2.0-dev (forked from Course Builder Studio v1.3.1)

WonderCourse is the v2.0 evolution of Course Builder Studio, focusing on **adaptive learning** and **content intelligence**. The platform generates complete online courses with:

- 15 content generators covering all activity types
- AI-powered blueprint generation with auto-fix
- Interactive AI coach with Socratic tutoring
- Multi-user collaboration with role-based permissions
- Learner profiles for audience-aware content
- Bloom's taxonomy validation and analysis
- Export to instructor packages, LMS manifests, SCORM, and DOCX
- Full dark theme UI with progress dashboard

**Foundation:** Course Builder Studio v1.3.1 (all Coursera v3.0 compliance complete)

## What This Is

An AI-powered adaptive learning platform that creates courses tailored to different learners. Beyond content generation, WonderCourse will offer:

- **UDL Menus**: Multiple content representations (video, audio, text, visual)
- **Depth Layers**: Essential/Standard/Advanced content variants
- **Inquiry Arcs**: Question-driven learning paths
- **Adaptive Progression**: Mastery-based advancement with remediation

## v2.0 Goals

See `.planning/v2.0-IDEAS.md` for the complete roadmap.

### Phase 1: Foundation
- [ ] Carry forward v1.x backlog (duration config, custom presets)
- [ ] Content variant data model
- [ ] Depth layer infrastructure

### Phase 2: UDL Implementation
- [ ] Variant generators (audio, transcript, infographic)
- [ ] UDL mode UI
- [ ] Learner preference storage

### Phase 3: Depth Layers
- [ ] Multi-depth generation
- [ ] Depth switching UI
- [ ] Profile-based defaults

### Phase 4: Inquiry Arcs
- [ ] Arc data model
- [ ] Arc-aware blueprint generator
- [ ] Question-based navigation

### Phase 5: AI Media Integration
- [ ] Image generation service integration (DALL-E, Midjourney)
- [ ] Video generation exploration
- [ ] Interactive simulation framework

### Phase 6: Review & Collaboration
- [ ] SME review workflow
- [ ] Version comparison
- [ ] Team templates

## Constraints

- **Tech stack**: Python + Flask + Jinja2 + vanilla JS
- **AI provider**: Anthropic Claude API (primary), OpenAI for images
- **Port**: 5003
- **Persistence**: Disk-based JSON per project

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Fork from Course Builder Studio | Solid v1.3.1 foundation with all compliance | Done |
| Keep Flask + vanilla JS | Avoid rewrite, focus on features | Active |
| UDL-first approach | Accessibility and learner choice as core value | Planned |
| Depth layers over branching | Simpler model, same content structure | Planned |

## v1.x Foundation (Inherited)

All 90+ requirements from Course Builder Studio:

- **Infrastructure**: Disk persistence, path safety, Claude API, Flask app
- **Course Management**: CRUD, modules/lessons/activities, outcomes, WWHAA phases
- **Content Generation**: 15 generators + regeneration + inline editing
- **Quality & Validation**: Coursera validation, outcome alignment, Bloom's analysis
- **Export & Publishing**: Instructor ZIP, LMS manifest, DOCX, SCORM, preview
- **Authentication**: Registration, login, sessions, isolation, profiles
- **Collaboration**: Invitations, roles, commenting, audit trail
- **v1.1 Expansion**: Standards engine, flow control, course pages, audit system, humanization, developer notes, video studio, progress dashboard
- **v1.2-v1.3**: Coursera v3.0 compliance (CTA validation, quiz distribution, AI detection, image generators)

---
*Created: 2026-02-17 — WonderCourse v2.0 development begins*
