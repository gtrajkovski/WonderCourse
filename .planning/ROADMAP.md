# Roadmap: Course Builder Studio

## Milestones

- [x] **v1.0** — AI-powered course authoring with 11 content generators, collaboration, and export ([archived](.planning/milestones/v1.0-ROADMAP.md))
- [x] **v1.1** — Course Builder Studio Expansion (complete)
- [x] **v1.2.0** — Coursera v3.0 Compliance HIGH (complete)
- [x] **v1.2.1** — Coursera v3.0 Compliance MEDIUM (complete)
- [x] **v1.3.0** — Coursera v3.0 Compliance LOW + Image Generation (complete)

## v1.3.0 Coursera v3.0 Compliance (LOW) + Image Generation [COMPLETE]

Implements LOW priority features from Coursera v3.0 analysis plus user-requested image generation.

### Feature 1: Visual Cue Validation [COMPLETE]
Video visual cue detection and validation:
- Configurable cue interval (default 75 seconds)
- Detects [Talking head/B-roll/Screen recording/Animation/Graphic] patterns
- Calculates expected vs actual cues based on video duration
- INFO severity for missing cues

### Feature 2: Terminal Screenshot Generator [COMPLETE]
Terminal-style image generator for HOL code examples:
- Dark theme (RGB 30,30,30 background)
- macOS-style window chrome with traffic lights
- TerminalLine helpers (prompt, output, error, success, comment)
- Graceful Pillow fallback

### Feature 3: CTA Slide Generator [COMPLETE]
End-of-video CTA slide generator:
- 1280x720 px canvas, Coursera blue (#0056D2)
- Course label, video title, tagline, footer
- Gradient background option

### Feature 4: Video Slide Generator [COMPLETE]
On-demand presentation slides from video scripts:
- SlideType: TITLE, OBJECTIVE, KEY_POINT, VISUAL_CUE, SUMMARY, CTA
- 1920x1080 HD canvas
- parse_script() extracts slides from video content
- Extracts visual cues, key points, bullet points

### Feature 5: Reading Image Generator [COMPLETE]
User-specified image count for text-based activities:
- ImageType: CONCEPT, DIAGRAM, EXAMPLE, COMPARISON, INFOGRAPHIC
- Extract concepts from headers, phrases, definitions, examples
- Keyword extraction with stop word filtering
- generate_reading_images(count=N) for 1-5 images
- extract_image_concepts() for external AI image generation

---

## v1.2.1 Coursera v3.0 Compliance (MEDIUM) [COMPLETE]

Implements 5 MEDIUM priority features from Coursera Master Reference v3.0 analysis.

### Feature 1: Video Section Timing Validation [COMPLETE]
Per-section word count validation:
- Hook: 75-150 words
- Objective: 75-112 words
- Content: 450-900 words
- IVQ: 75-150 words
- Summary: 75-112 words
- CTA: 37-75 words

### Feature 2: WWHAA Sequence Validation [COMPLETE]
Module structure validation against WWHAA pedagogy model:
- WHY: Coach dialogues, Hook phase videos
- WHAT: Videos, Readings (content delivery)
- HOW: Screencasts (demonstrations)
- APPLY: HOL, Labs, Practice Quizzes
- ASSESS: Graded Quizzes, Assignments

### Feature 3: Reading Author Attribution [COMPLETE]
Attribution validation for readings:
- Configurable attribution template
- Detection of embedded attribution in body
- Auto-fixable violation suggestion

### Feature 4: Reference Link Validation [COMPLETE]
Paywall domain detection:
- 18 common academic paywall domains
- Links must be freely accessible
- WARNING severity for violations

### Feature 5: Content Distribution Validation [COMPLETE]
Course content type balance:
- Videos: ~30% (±10%)
- Readings: ~20% (±10%)
- HOL/Labs: ~30% (±10%)
- Assessments: ~20% (±10%)

---

## v1.2.0 Coursera v3.0 Compliance [COMPLETE]

Implements 5 HIGH priority features from Coursera Master Reference v3.0 analysis.

### Feature 1: AI Detection Expansion [COMPLETE]
Added 5 new AI pattern detection types to TextHumanizer:
- REPEAT_OPENER: Consecutive sentences starting with same word
- ENSURES_OPENER: "This ensures/enables/allows" constructions
- NOT_ONLY_BUT: "Not only X, but also Y" patterns
- LONG_COMMA_LIST: 4+ item comma-separated lists
- ADVERB_TRIPLET: 3+ adverbs in close proximity

### Feature 2: CTA Validation [COMPLETE]
Video CTA section validation per v3.0 requirements:
- Maximum 35 words
- No activity previews (forbidden phrases)
- ContentStandardsProfile configuration

### Feature 3: Quiz Answer Distribution [COMPLETE]
Enhanced quiz validation with 15-35% per letter:
- Minimum 15% distribution (INFO severity)
- Maximum 35% distribution (WARNING severity)
- Only validates quizzes with 4+ questions

### Feature 4: Sequential Reference Detection [COMPLETE]
Course auditor check for standalone content:
- New SEQUENTIAL_REFERENCE AuditCheckType
- 11 detection patterns
- Integrated into run_all_checks()

### Feature 5: Configurable HOL Rubric [COMPLETE]
Dynamic rubric configuration via standards profile:
- 2-5 criteria allowed (was fixed at 3)
- Level names and points from ContentStandardsProfile
- Generator prompts use standards_rules injection

---

## v1.1 Expansion

### Phase 1: Configurable Content Standards Engine [COMMITTED]

Create a flexible standards profile system that governs all content generation.

**Deliverables:**
- ContentStandardsProfile model with 50+ configurable fields
- StandardsStore with system presets (Coursera, Flexible, Corporate)
- StandardsValidator for content validation
- Standards API (CRUD + validation)
- Planner page standards selector
- Prompt injection to all 11 generators

### Phase 2: Completion Criteria & Flow Control [COMMITTED]

Add flow control and completion tracking for learner progression.

**Deliverables:**
- FlowMode enum (SEQUENTIAL, OPEN)
- CompletionCriteria dataclass
- Course/Module flow_mode fields
- Activity prerequisite_ids and completion_criteria
- Flow control API endpoints
- Builder UI for flow mode and prerequisites

### Phase 3: Auto-Generated Course Pages [COMMITTED]

Generate consistent course pages (syllabus, about, resources) automatically.

**Deliverables:**
- PageType enum and CoursePage model
- CoursePageGenerator for syllabus, about, resources
- Course pages API endpoints
- Pages UI with generation and preview

### Phase 4: Course Audit & Quality System [COMMITTED]

Comprehensive course quality auditing with issue detection and resolution tracking.

**Deliverables:**
- AuditCheckType, AuditSeverity, AuditIssueStatus enums
- AuditIssue and AuditResult dataclasses
- CourseAuditor with 6 check types:
  - Flow analysis (logical progression, prerequisites)
  - Repetition detection (duplicate titles, content similarity)
  - Objective alignment (unmapped outcomes/activities)
  - Content gaps (draft activities, missing video/practice)
  - Duration balance (module duration variance)
  - Bloom progression (cognitive level regression)
- Audit API endpoints
- Audit UI with score card, issue list, and resolution workflow

### Phase 5: AI Text Humanization Engine [COMMITTED]

Reduce AI-sounding patterns in generated content.

**Deliverables:**
- ContentHumanizer utility with TEXT_FIELDS mapping for 12 schemas
- humanize_content() and get_content_score() functions
- ContentStandardsProfile humanization settings (7 fields)
- Auto-humanize in content generation pipeline
- Humanize API endpoints (POST humanize, GET score)
- Studio UI: score ring, humanize button, pattern viewer
- Planner UI: auto-humanize toggle, threshold input
- 20 unit tests

### Phase 6: Developer Notes + Preview Mode [COMMITTED]

Internal documentation and preview capabilities for content authors.

**Deliverables:**
- DeveloperNote dataclass with pinned, author tracking
- developer_notes field on Activity, Lesson, Module, Course
- Notes API: CRUD at all levels with sorting
- Studio notes panel with add/edit/delete/pin
- Preview mode toggle (Author/Learner views)
- Viewport selector (Desktop/Tablet/Mobile)
- PreviewRenderer utility for learner-facing HTML
- 45 tests (18 notes API + 27 preview renderer)

### Phase 7: Video Lesson Studio [COMMITTED]

Enhanced video script editing with teleprompter and timing tools.

**Deliverables:**
- section_timings in video script metadata
- VideoStudio component with teleprompter view
- Per-section timing sidebar with progress
- Auto-scroll playback with speed control (0.5x-2x)
- Section navigation and jump
- Speaker notes overlay toggle
- Keyboard shortcuts (Space, arrows, N, F, Esc)
- Full-screen presentation mode

### Phase 8: Progress Dashboard [COMMITTED]

Visualize course completion status and content generation progress.

**Deliverables:**
- Enhanced progress API with content_metrics, structure, by_content_type, by_module, quality
- Progress dashboard page with summary cards (completion ring, activities, duration, quality)
- Build state distribution with horizontal bar chart
- Module progress list with progress bars
- Content type breakdown with completion overlay
- Filterable activity table (All/Draft/Generated/Approved)
- Structure stats panel (modules, lessons, activities, words)
- Sidebar navigation integration

---
*Last updated: 2026-02-16 — v1.2.1 Coursera v3.0 Compliance (MEDIUM) complete*
