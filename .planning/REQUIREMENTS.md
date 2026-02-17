# Requirements: Course Builder Studio

**Defined:** 2026-02-02
**Core Value:** Generate all content types for a complete Coursera short course from a high-level blueprint, with AI-powered generation, structural validation, and export-ready packaging.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Course Management

- [ ] **COURSE-01**: User can create a new course with title, description, audience level, duration, and modality
- [ ] **COURSE-02**: User can view course list on dashboard with status and metadata
- [ ] **COURSE-03**: User can edit course metadata (title, description, prerequisites, tools, grading policy)
- [ ] **COURSE-04**: User can delete a course from dashboard
- [ ] **COURSE-05**: User can generate a course blueprint from high-level inputs using AI
- [ ] **COURSE-06**: User can define learning outcomes with Bloom's taxonomy levels and tags
- [ ] **COURSE-07**: User can add, remove, and reorder modules within a course
- [ ] **COURSE-08**: User can add, remove, and reorder lessons within a module
- [ ] **COURSE-09**: User can add, remove, and reorder activities within a lesson
- [ ] **COURSE-10**: User can assign WWHAA phase to each activity
- [ ] **COURSE-11**: User can assign activity types (video, reading, HOL, quiz, lab, discussion, assignment, project, reflection)
- [ ] **COURSE-12**: User can map learning outcomes to activities

### Content Generation

- [x] **GEN-01**: User can generate video scripts following WWHAA structure (Hook, Objective, Content, IVQ, Summary, CTA)
- [x] **GEN-02**: User can generate readings (max 1200 words, APA 7 references, structured sections)
- [x] **GEN-03**: User can generate HOL activities (scenario, 3 parts, submission criteria, 3-criterion rubric)
- [x] **GEN-04**: User can generate coach dialogues (8 sections, 3-level evaluation with example responses)
- [x] **GEN-05**: User can generate graded quizzes (MCQ with option-level feedback, balanced answer distribution)
- [x] **GEN-06**: User can generate practice quizzes (formative assessment with immediate feedback)
- [x] **GEN-07**: User can generate ungraded lab specifications
- [x] **GEN-08**: User can generate discussion prompts (facilitation questions, engagement hooks)
- [x] **GEN-09**: User can generate assignment specifications (deliverables, grading criteria, submission checklists)
- [x] **GEN-10**: User can generate project milestone prompts (scaffolded A1/A2/A3 style)
- [x] **GEN-11**: User can generate textbook chapters (~3000 words per learning outcome)
- [x] **GEN-12**: User can regenerate any content item with different parameters
- [x] **GEN-13**: User can edit generated content inline before approving

### Quality & Validation

- [x] **QA-01**: System validates course structure against Coursera requirements (duration 30-180 min, module count, content distribution)
- [x] **QA-02**: System tracks build state per content item (draft -> generating -> generated -> reviewed -> approved -> published)
- [x] **QA-03**: User can view outcome-activity alignment with coverage scoring
- [x] **QA-04**: User can detect alignment gaps between outcomes and content
- [x] **QA-05**: System validates Bloom's taxonomy level distribution across activities
- [x] **QA-06**: User can run distractor quality analysis on quiz questions
- [x] **QA-07**: User can view validation issues and warnings per course

### Export & Publishing

- [x] **PUB-01**: User can export instructor package as ZIP (syllabus, lesson plans, rubrics, quizzes, textbook)
- [x] **PUB-02**: User can export LMS manifest as structured JSON
- [x] **PUB-03**: User can export textbook as DOCX
- [x] **PUB-04**: User can export SCORM-compliant package for LMS import
- [x] **PUB-05**: User can view export preview before downloading

### UI Pages

- [ ] **UI-01**: Dashboard page shows course list with create/delete and status indicators
- [ ] **UI-02**: Planner page for course setup, learning outcomes, and blueprint generation
- [ ] **UI-03**: Builder page with module/lesson/activity tree editor
- [ ] **UI-04**: Studio page for content generation with preview panes
- [ ] **UI-05**: Textbook page for chapter generation, glossary, and preview
- [ ] **UI-06**: Publish page for export selection and package download
- [ ] **UI-07**: Dark theme UI consistent with ScreenCast Studio aesthetic
- [ ] **UI-08**: Left navigation between all pages with course context

### Infrastructure

- [ ] **INFRA-01**: Disk persistence to projects/{id}/course_data.json after every operation
- [ ] **INFRA-02**: Path traversal protection on all file operations
- [ ] **INFRA-03**: Claude API integration for all AI generation
- [ ] **INFRA-04**: Flask app on port 5003 with Jinja2 templates

### Authentication & Accounts

- [ ] **AUTH-01**: User can register with email and password
- [ ] **AUTH-02**: User can log in and receive a session/token
- [ ] **AUTH-03**: User can log out and session is invalidated
- [ ] **AUTH-04**: All API endpoints require authentication (except register/login)
- [ ] **AUTH-05**: Each user's courses are isolated (user can only see/edit their own courses)
- [ ] **AUTH-06**: User can view and update their profile (name, email)
- [ ] **AUTH-07**: Password reset flow via email

### Collaboration

- [x] **COLLAB-01**: Course owner can invite collaborators by email with a role (SME, designer, reviewer)
- [x] **COLLAB-02**: Version control and audit trail for content changes
- [x] **COLLAB-03**: Commenting and approval workflows on content items
- [x] **COLLAB-04**: Role-based permissions (owner: full access, designer: edit, reviewer: comment/approve, SME: view/comment)
- [x] **COLLAB-05**: Activity feed showing recent changes by all collaborators on a course

### AI Inline Editing

AI-powered inline editing with real-time suggestions, similar to ScreenCast Studio experience.

- [x] **EDIT-01**: Inline text editor with AI-powered suggestions (improve, expand, simplify, etc.)
- [x] **EDIT-02**: Context-aware autocomplete for course content based on learning outcomes and topic
- [x] **EDIT-03**: Tone and clarity suggestions with one-click apply
- [x] **EDIT-04**: Bloom's level suggestions — flag content that doesn't match target cognitive level
- [x] **EDIT-05**: AI rewrite options (more academic, more conversational, shorter, longer)
- [x] **EDIT-06**: Blueprint inline editing with AI suggestions for structure improvements
- [x] **EDIT-07**: Floating AI toolbar on text selection with quick actions
- [x] **EDIT-08**: Undo/redo for AI-applied changes

### Interactive AI Coach

Transform Coach Dialogue activities into live AI-guided conversations where students interact with an AI tutor.

- [x] **COACH-01**: Interactive chat interface for Coach Dialogue activities (student types, AI responds)
- [x] **COACH-02**: AI coach follows generated dialogue structure as guardrails (8 sections, evaluation criteria)
- [x] **COACH-03**: Coach stays on-topic using activity's learning outcomes and topic constraints
- [x] **COACH-04**: Coach uses Socratic method — asks probing questions rather than giving answers
- [x] **COACH-05**: Real-time evaluation against the 3-level rubric (developing, proficient, exemplary)
- [x] **COACH-06**: Session transcript saved for instructor review
- [x] **COACH-07**: Coach personality/tone configurable per activity (supportive, challenging, formal)
- [x] **COACH-08**: Conversation summary with learning progress indicators

### Content Import & Enhancement

Import existing content (blueprints, course structures, content) and enhance with AI editing tools.

- [x] **IMPORT-01**: User can paste or upload an existing blueprint (JSON or structured text) and import it
- [x] **IMPORT-02**: User can import existing module/lesson/activity structures from external sources
- [x] **IMPORT-03**: User can paste existing content (video scripts, readings, quizzes) into activities
- [x] **IMPORT-04**: Imported content is automatically analyzed for Bloom's level, word count, and structure
- [x] **IMPORT-05**: User can apply AI editing tools (improve, expand, simplify) to imported content
- [x] **IMPORT-06**: User can convert imported plain text into structured format (e.g., text → WWHAA video script)
- [x] **IMPORT-07**: Import supports common formats (JSON, Markdown, plain text, CSV for quizzes)

### Intelligence Suite (Teacher Empowerment)

AI features that deepen a teacher's craft rather than replace it. Core principle: give educators a nudge to try something new, not do the thinking for them.

- [ ] **INTEL-01**: UDL Learning Menu generation — anticipate learning barriers and generate choice-rich menus per UDL principles (Representation, Engagement, Action/Expression)
- [ ] **INTEL-02**: UDL Menu API endpoint (POST /api/courses/<id>/activities/<id>/udl-menu) that enhances existing content with barrier anticipation
- [ ] **INTEL-03**: Depth Layer generation — inject critical thinking, ethical reasoning, and "unautomatable" questions that push above current Bloom level
- [ ] **INTEL-04**: Depth Layer API endpoint (POST /api/courses/<id>/activities/<id>/depth-layer) for adding reasoning challenges to activities
- [ ] **INTEL-05**: Optional depth layer injection in discussion, quiz, and coach dialogue generators (backward-compatible, disabled by default)
- [ ] **INTEL-06**: Inquiry Arc generation — scaffold student questions into 6-phase inquiry projects (Wonder, Hypothesize, Investigate, Synthesize, Reflect, Share)
- [ ] **INTEL-07**: Inquiry Arc API endpoint (POST /api/courses/<id>/modules/<id>/inquiry) with INQUIRY activity type
- [ ] **INTEL-08**: Activity model extended with optional udl_menu, depth_layer, inquiry_arc fields (backward-compatible)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Features

- **ADV-01**: Cross-content consistency validation (terminology, tone, complexity level)
- ~~**ADV-02**: AI instructional design coach (proactive suggestions)~~ — Moved to v1 as EDIT-01 through EDIT-08
- **ADV-03**: React SPA frontend (migrate from Jinja)
- **ADV-04**: Accessibility compliance (WCAG 2.1 AA)
- **ADV-05**: Advanced LMS export (xAPI, cmi5)
- **ADV-06**: Textbook PDF export
- **ADV-07**: IMS Common Cartridge full implementation
- **ADV-08**: Content reusability library (cross-course import)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time multi-user editing | Conflict resolution too complex for structured educational content |
| Custom AI models per organization | Expensive, increases hallucination risk, prompt engineering sufficient |
| AI auto-publish | Human review required for educational content given hallucination rates |
| Video production | Different domain; focus on content generation, not media production |
| Learner-facing features | This is an authoring tool, not a delivery platform |
| Mobile app | Course authoring is desktop work |
| Blockchain credentials | Overkill for current scope |
| Gamification of authoring | Incentivizes quantity over quality |
| Multi-provider LLM support | Claude API only for simplicity |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| COURSE-01 | Phase 2 | Complete |
| COURSE-02 | Phase 2 | Complete |
| COURSE-03 | Phase 2 | Complete |
| COURSE-04 | Phase 2 | Complete |
| COURSE-06 | Phase 2 | Complete |
| COURSE-07 | Phase 2 | Complete |
| COURSE-08 | Phase 2 | Complete |
| COURSE-09 | Phase 2 | Complete |
| COURSE-10 | Phase 2 | Complete |
| COURSE-11 | Phase 2 | Complete |
| COURSE-12 | Phase 2 | Complete |
| COURSE-05 | Phase 3 | Complete |
| GEN-01 | Phase 4 | Complete |
| GEN-02 | Phase 4 | Complete |
| GEN-05 | Phase 4 | Complete |
| GEN-12 | Phase 4 | Complete |
| GEN-13 | Phase 4 | Complete |
| GEN-03 | Phase 5 | Complete |
| GEN-04 | Phase 5 | Complete |
| GEN-06 | Phase 5 | Complete |
| GEN-07 | Phase 5 | Complete |
| GEN-08 | Phase 5 | Complete |
| GEN-09 | Phase 5 | Complete |
| GEN-10 | Phase 5 | Complete |
| GEN-11 | Phase 6 | Complete |
| QA-01 | Phase 7 | Complete |
| QA-02 | Phase 7 | Complete |
| QA-03 | Phase 7 | Complete |
| QA-04 | Phase 7 | Complete |
| QA-05 | Phase 7 | Complete |
| QA-06 | Phase 7 | Complete |
| QA-07 | Phase 7 | Complete |
| PUB-01 | Phase 8 | Complete |
| PUB-02 | Phase 8 | Complete |
| PUB-03 | Phase 8 | Complete |
| PUB-04 | Phase 8 | Complete |
| PUB-05 | Phase 8 | Complete |
| AUTH-01 | Phase 9 | Pending |
| AUTH-02 | Phase 9 | Pending |
| AUTH-03 | Phase 9 | Pending |
| AUTH-04 | Phase 9 | Pending |
| AUTH-05 | Phase 9 | Pending |
| AUTH-06 | Phase 9 | Pending |
| AUTH-07 | Phase 9 | Pending |
| COLLAB-01 | Phase 10 | Complete |
| COLLAB-02 | Phase 10 | Complete |
| COLLAB-03 | Phase 10 | Complete |
| COLLAB-04 | Phase 10 | Complete |
| COLLAB-05 | Phase 10 | Complete |
| UI-01 | Phase 11 | Pending |
| UI-02 | Phase 11 | Pending |
| UI-03 | Phase 11 | Pending |
| UI-04 | Phase 11 | Pending |
| UI-05 | Phase 11 | Complete |
| UI-06 | Phase 11 | Complete |
| UI-07 | Phase 11 | Complete |
| UI-08 | Phase 11 | Complete |
| EDIT-01 | Phase 12 | Complete |
| EDIT-02 | Phase 12 | Complete |
| EDIT-03 | Phase 12 | Complete |
| EDIT-04 | Phase 12 | Complete |
| EDIT-05 | Phase 12 | Complete |
| EDIT-06 | Phase 12 | Complete |
| EDIT-07 | Phase 12 | Complete |
| EDIT-08 | Phase 12 | Complete |
| COACH-01 | Phase 12 | Complete |
| COACH-02 | Phase 12 | Complete |
| COACH-03 | Phase 12 | Complete |
| COACH-04 | Phase 12 | Complete |
| COACH-05 | Phase 12 | Complete |
| COACH-06 | Phase 12 | Complete |
| COACH-07 | Phase 12 | Complete |
| COACH-08 | Phase 12 | Complete |
| IMPORT-01 | Phase 12 | Complete |
| IMPORT-02 | Phase 12 | Complete |
| IMPORT-03 | Phase 12 | Complete |
| IMPORT-04 | Phase 12 | Complete |
| IMPORT-05 | Phase 12 | Complete |
| IMPORT-06 | Phase 12 | Complete |
| IMPORT-07 | Phase 12 | Complete |

**Coverage:**
- v1 requirements: 90 total
- Mapped to phases: 90
- Unmapped: 0

---
*Requirements defined: 2026-02-02*
*Last updated: 2026-02-06 — Phase 8 (PUB-01 through PUB-05) marked Complete*
