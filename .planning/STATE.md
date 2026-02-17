# State: Course Builder Studio

## Current

**Status:** v1.3.1 Backlog Features — Implementation Complete
**Version:** 1.3.1
**Task:** Blueprint Auto-Fix, Learner Profiles, Bloom Validation, Images API implemented

## v1.3.1 Backlog Features

| Feature | Status | Tests |
|---------|--------|-------|
| Blueprint Auto-Fix | Complete | 10 tests |
| Learner Profiles | Complete | 15 tests |
| Images API | Complete | 12 tests |
| Bloom Validation | Complete | 14 tests |

**Total:** 51 new tests

### v1.3.1 Implementation Summary

**Feature 1: Blueprint Auto-Fix (src/validators/blueprint_autofix.py)**
- BlueprintAutoFixer class with deterministic fixes
- Duration scaling to meet target (with min/max bounds per content type)
- Auto-assign WWHAA phases to activities missing them
- Activity balance suggestions for lessons with < 2 activities
- Refinement feedback generator for AI regeneration prompts

**Feature 2: Learner Profiles (src/api/learner_profiles.py)**
- LearnerProfile model with 20+ fields for audience characteristics
- Enums: TechnicalLevel, LanguageProficiency, LearningPreference, LearningContext
- CRUD API at /api/learner-profiles
- 4 default profiles: Beginner Professional, Intermediate Developer, Career Changer, ESL Learner
- Course assignment via /api/courses/<id>/learner-profile
- Prompt context generation for AI content tailoring

**Feature 3: Images API (src/api/images.py)**
- REST endpoints for all image generators
- Video slides: POST /api/courses/<id>/activities/<id>/slides
- Reading images: POST /api/courses/<id>/activities/<id>/images
- Terminal screenshots: POST /api/images/terminal
- CTA slides: POST /api/courses/<id>/activities/<id>/cta-slide
- Standalone endpoints for arbitrary content
- Base64 and binary output formats
- Graceful Pillow fallback with status endpoint

**Feature 4: Bloom Validation (src/editing/bloom_analyzer.py)**
- BloomAnalyzer class with verb-based level detection
- TaxonomyAnalyzer for custom taxonomies (SOLO, Webb, Marzano, Fink)
- Alignment checking with actionable suggestions
- Integration with CourseAuditor for progression checks

---

## v1.3.0 Coursera v3.0 Compliance (LOW Priority + Enhancements)

| Feature | Status | Tests |
|---------|--------|-------|
| Visual Cue Validation | Complete | 5 tests |
| Terminal Screenshot Generator | Complete | 4 tests |
| CTA Slide Generator | Complete | 4 tests |
| Video Slide Generator | Complete | 10 tests |
| Reading Image Generator | Complete | 12 tests |

**Total:** 45 new tests (25 pass, 20 skipped w/o Pillow), 1173 total tests passing

### v1.3.0 Implementation Summary

**Feature 1: Visual Cue Validation (src/validators/standards_validator.py)**
- Added video_visual_cue_enabled, video_visual_cue_interval_seconds to ContentStandardsProfile
- Detects [Talking head/B-roll/Screen recording/Animation/Graphic] patterns
- Calculates expected vs actual cues based on video duration
- INFO severity for missing cues

**Feature 2: Terminal Screenshot Generator (src/utils/terminal_image_generator.py)**
- TerminalStyle dataclass with Coursera v3.0 specs (30,30,30 bg, 204,204,204 text)
- TerminalLine helpers for prompt, output, error, success, comment
- TerminalImageGenerator class with macOS-style title bar
- generate_simple() for quick command/output images
- Graceful Pillow fallback (PILLOW_AVAILABLE flag)

**Feature 3: CTA Slide Generator (src/utils/cta_slide_generator.py)**
- CTASlideStyle dataclass (1280x720 px, Coursera blue #0056D2)
- CTASlideContent with video_title, course_label, tagline, footer
- CTASlideGenerator with gradient background, centered layout
- generate_cta_slide() convenience function

**Feature 4: Video Slide Generator (src/utils/video_slide_generator.py)**
- SlideType enum: TITLE, OBJECTIVE, CONTENT, KEY_POINT, VISUAL_CUE, SUMMARY, CTA
- SlideStyle with 1920x1080 HD canvas, Coursera blue
- VideoSlideGenerator.parse_script() parses video content into slides
- Extracts visual cues, key points, bullet points from script
- generate_video_slides() convenience function

**Feature 5: Reading Image Generator (src/utils/reading_image_generator.py)**
- ImageType enum: CONCEPT, DIAGRAM, EXAMPLE, COMPARISON, INFOGRAPHIC
- ImageConcept with title, description, keywords, AI prompt generation
- ReadingImageGenerator extracts concepts from reading content:
  - Headers, key phrases, definitions, examples
  - Keyword extraction with stop word filtering
  - Concept ranking by importance
- Generate placeholder images with type-specific icons
- generate_reading_images(count=N) for user-specified image count
- extract_image_concepts() for external AI image generation

---

## v1.2.1 Coursera v3.0 Compliance (MEDIUM Priority)

| Feature | Status | Tests |
|---------|--------|-------|
| Video Section Timing Validation | Complete | 4 tests |
| WWHAA Sequence Validation | Complete | 3 tests |
| Reading Author Attribution | Complete | 4 tests |
| Reference Link Validation | Complete | 4 tests |
| Content Distribution Validation | Complete | 6 tests |

**Total:** 21 new tests, 1148 total tests passing

### v1.2.1 Implementation Summary

**Feature 1: Video Section Timing Validation (src/validators/standards_validator.py)**
- Added video_section_timing_enabled and video_section_word_counts to ContentStandardsProfile
- Per-section word count validation (Hook: 75-150, Content: 450-900, etc.)
- INFO for under minimum, WARNING for over maximum

**Feature 2: WWHAA Sequence Validation (src/validators/course_auditor.py)**
- Added WWHAA_SEQUENCE to AuditCheckType enum
- Content type-based phase classification (WHY/WHAT/HOW/APPLY/ASSESS)
- Validates essential phases (WHAT, APPLY) are present

**Feature 3: Reading Author Attribution (src/validators/standards_validator.py)**
- Added reading_require_attribution and reading_attribution_template to ContentStandardsProfile
- Checks for explicit attribution field or embedded attribution in body
- Auto-fixable suggestion with template

**Feature 4: Reference Link Validation (src/validators/standards_validator.py)**
- Added reading_paywall_domains (18 domains) to ContentStandardsProfile
- Detects jstor.org, springer.com, wiley.com, etc.
- WARNING severity for paywall links

**Feature 5: Content Distribution Validation (src/validators/course_auditor.py)**
- Added CONTENT_DISTRIBUTION to AuditCheckType enum
- Validates ~30% video, ~20% reading, ~30% HOL, ~20% assessment
- INFO severity for out-of-range distributions

---

## v1.2.0 Coursera v3.0 Compliance (HIGH Priority)

| Feature | Status | Tests |
|---------|--------|-------|
| AI Detection Expansion (5 new patterns) | Complete | 10 tests |
| CTA Validation | Complete | 8 tests |
| Quiz Answer Distribution (15-35%) | Complete | 5 tests |
| Sequential Reference Detection | Complete | 9 tests |
| Configurable HOL Rubric | Complete | 6 tests |

**Total:** 57 new tests, 1127 total tests passing

---

## v1.1 Expansion Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | Configurable Content Standards Engine | Committed |
| 2 | Completion Criteria & Flow Control | Committed |
| 3 | Auto-Generated Course Pages | Committed |
| 4 | Course Audit & Quality System | Committed |
| 5 | AI Text Humanization Engine | Committed |
| 6 | Developer Notes + Preview Mode | Committed |
| 7 | Video Lesson Studio | Committed |
| 8 | Progress Dashboard | Committed |

## Phase 8 Summary

Implemented Progress Dashboard for course completion visualization:

**Enhanced Progress API (src/api/build_state.py):**
- Expanded `/api/courses/<id>/progress` endpoint with comprehensive metrics
- Added content_metrics: word count, duration vs target, percentage
- Added structure: module/lesson/activity counts
- Added by_content_type: per-content-type completion breakdown
- Added by_module: per-module progress with percentages
- Added quality: audit score, open issues, last audit timestamp

**Dashboard Page (templates/progress.html):**
- Summary cards: completion ring, activity count, duration, quality score
- Build state distribution with horizontal bars
- Module progress list with progress bars
- Content type breakdown with completion overlay
- Filterable activity table (All/Draft/Generated/Approved)
- Structure stats panel (modules, lessons, activities, words)

**JavaScript Controller (static/js/pages/progress.js):**
- ProgressDashboard class with full rendering pipeline
- Filter handling for activity table
- Progress ring animation
- Content type icons mapping

**Styling (static/css/pages/progress.css):**
- Responsive grid layout (4-col to 2-col to 1-col)
- Progress ring SVG animation
- State bar colors with pulse animation for generating
- Status and type badges
- Dark theme compatible

**Integration:**
- Flask route `/courses/<id>/progress` in app.py
- Sidebar navigation link (chart icon) between Audit and Publish

## Phase 7 Summary

Implemented Video Lesson Studio with teleprompter and timing tools:

**Metadata Enhancement (src/generators/video_script_generator.py):**
- Added `section_timings` dict to metadata
- Per-section timing calculated at 150 WPM speaking rate

**VideoStudio Component (static/js/components/video-studio.js):**
- Teleprompter view with auto-scroll playback
- Reading line indicator for current position
- Play/pause/stop/rewind controls
- Speed adjustment (0.5x to 2x)
- Section navigation (prev/next/jump)
- Keyboard shortcuts:
  - Space: Play/Pause
  - Arrow keys: Section nav, speed adjust
  - N: Toggle speaker notes
  - F: Fullscreen mode
  - Esc: Exit

**UI (templates/partials/video-studio.html, static/css/components/video-studio.css):**
- Full-screen modal with dark theme
- Timing sidebar with section breakdown
- Progress bar with elapsed/total time
- Speaker notes overlay (togglable)
- Shortcuts help panel

**Integration (templates/studio.html, static/js/pages/studio.js):**
- "Video Studio" button in edit section (video content only)
- Opens full-screen teleprompter modal
- Calculates section timings on-the-fly if metadata missing

## Phase 6 Summary

Implemented developer notes and preview mode:

**Models (src/core/models.py):**
- `DeveloperNote` dataclass with id, content, author_id, author_name, pinned, timestamps
- `developer_notes: List[DeveloperNote]` field on Activity, Lesson, Module, Course

**API (src/api/notes.py):**
- CRUD endpoints at all levels (course, module, lesson, activity)
- Notes sorted: pinned first, then by created_at descending

**Preview Mode:**
- Author/Learner view toggle
- Viewport selector (Desktop/Tablet/Mobile)
- `PreviewRenderer` utility strips author-only elements

**UI:**
- Notes panel below preview with add/edit/delete/pin
- Preview mode toggle in header
- Viewport constraints via CSS

**Tests:**
- 18 notes API tests
- 27 preview renderer tests

## Phase 5 Summary

Implemented AI text humanization engine to reduce AI-sounding patterns in generated content:

**Content Humanizer (src/utils/content_humanizer.py):**
- `TEXT_FIELDS` mapping for all 12 content type schemas
- `humanize_content()` - Traverses Pydantic models, humanizes all text fields
- `get_content_score()` - Returns humanization score and pattern breakdown
- `ContentHumanizationResult` dataclass with serialization support
- Handles nested fields and arrays (e.g., `questions[].options[].text`)

**Models (src/core/models.py):**
- Added to ContentStandardsProfile:
  - `enable_auto_humanize: bool = True`
  - `humanize_em_dashes`, `humanize_formal_vocabulary`, etc.
  - `humanization_score_threshold: int = 70`

**Standards Presets (src/core/standards_store.py):**
- Coursera: auto-humanize enabled (threshold 70)
- Flexible: auto-humanize disabled
- Corporate: auto-humanize enabled (threshold 75)

**API (src/api/content.py):**
- Auto-humanize in `generate_content()` and `regenerate_content()` pipelines
- POST `/api/courses/<id>/activities/<id>/humanize` - humanize content
- GET `/api/courses/<id>/activities/<id>/humanize/score` - get score

**UI:**
- Studio: Score ring visualization, "Humanize Text" button, pattern viewer
- Planner: Auto-humanize toggle, quality threshold input

**Tests:**
- 20 unit tests in `tests/test_content_humanizer.py`

## Previous Phase Summaries

**Phase 4:** Course audit and quality system with 6 check types
**Phase 3:** Auto-generated course pages (syllabus, about, resources)
**Phase 2:** Flow control and completion criteria
**Phase 1:** Configurable content standards engine

## Next Steps

v1.3.1 Backlog Features complete. Remaining backlog items:
- Configurable Course Duration (prominent UI selector before blueprint generation)
- Custom Course Type Presets (user-defined standards profiles)
- AI-powered image generation integration (connect to DALL-E, Midjourney, etc.)

## v1.0 Archives

- `.planning/milestones/v1.0-ROADMAP.md` - full phase details
- `.planning/milestones/v1.0-REQUIREMENTS.md` - all 90 requirements
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` - verification report

---
*Last updated: 2026-02-17 - v1.3.1 Backlog Features complete*
