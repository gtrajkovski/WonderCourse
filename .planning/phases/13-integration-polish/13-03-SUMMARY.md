---
phase: 13-integration-polish
plan: 03
title: In-App Help System
subsystem: help
tags: [onboarding, help, glossary, tooltips, intro.js]
requires: [13-01-error-handling, 13-02-skeleton-loading]
provides:
  - Interactive onboarding tour with Intro.js
  - Contextual help panels and tooltips
  - Searchable instructional design glossary
  - Help API with 4 endpoints
affects: [user-experience, documentation]
tech-stack:
  added:
    - intro.js@7.2.0
  patterns:
    - Help panel slide-in overlay
    - Glossary with search and related term linking
    - localStorage for onboarding state persistence
key-files:
  created:
    - static/js/onboarding.js
    - static/css/components/help.css
    - static/js/components/help.js
    - templates/partials/help-panel.html
    - static/data/glossary.json
    - src/api/help.py
    - templates/help/glossary.html
  modified:
    - templates/base.html
    - templates/partials/header.html
    - templates/dashboard.html
    - static/js/pages/dashboard.js
    - app.py
decisions:
  - decision: Use Intro.js CDN instead of local install
    rationale: Zero build step, immediate availability, automatic updates
    alternatives: [Local install, custom tour implementation]
  - decision: Store onboarding state in localStorage
    rationale: Persists across sessions, no server-side tracking needed
    alternatives: [Server-side user preferences, sessionStorage]
  - decision: 18 glossary terms covering core concepts
    rationale: Covers essential instructional design vocabulary without overwhelming
    alternatives: [Minimal 10-term glossary, comprehensive 50+ term glossary]
  - decision: Help API supports both database and static JSON
    rationale: Flexibility for future expansion while working out-of-the-box
    alternatives: [Database-only, static-only]
metrics:
  duration: 12 minutes
  completed: 2026-02-11
---

# Phase 13 Plan 03: In-App Help System Summary

**One-liner:** Intro.js onboarding tour with contextual help panels, tooltips, and 18-term instructional design glossary

## What Was Built

### 1. Interactive Onboarding Tour (Intro.js)

Added Intro.js 7.2.0 via CDN with fully customized dark theme styling:

- **Dashboard tour:** Welcome, create course, navigation, help menu (4 steps)
- **Planner tour:** Outcomes, blueprint, Bloom selector (3 steps)
- **Studio tour:** Activity list, preview, generate, AI toolbar (4 steps)
- **Builder, Textbook, Publish tours:** Page-specific guidance

**Auto-start behavior:**
- Checks `localStorage.onboarding_completed` and `onboarding_skipped`
- Auto-starts for new users on dashboard after 500ms
- Detects page via body class (`page-dashboard`, `page-planner`, etc.)

**Manual replay:**
- Help menu dropdown in header with "Replay Tour" option
- "Reset Onboarding" clears localStorage for testing

**Dark theme integration:**
- Tooltip background: `#16213e`
- Accent color: `#4da6ff`
- Overlay: `rgba(26, 26, 46, 0.85)`
- Matches app aesthetic seamlessly

### 2. Contextual Help Panels & Tooltips

Created `HelpManager` class for managing help system:

**Features:**
- Slide-in panel from right (360px width, full height)
- Tooltips on `.help-btn` elements (hover-activated)
- Escape key and click-outside to close
- Support for static and API-loaded content

**Help panel structure:**
- Header with title and close button
- Scrollable content area
- Glossary rendering with search
- Related term linking (click to navigate)

**Tooltip system:**
- Positioned above help buttons
- Max-width 300px for readability
- Arrow pointing to button
- Automatic title attribute detection

### 3. Instructional Design Glossary

Created comprehensive glossary with 18 terms:

**Core pedagogical concepts:**
- WWHAA, Bloom's Taxonomy, Learning Outcome
- ABCD Format, Hook, Scaffolding, Cognitive Load

**Assessment terms:**
- Formative Assessment, Summative Assessment
- Distractor, Rubric, Practice Quiz

**Technical terms:**
- SCORM, LMS, IVQ, Module, Activity

**Course structure:**
- Hands-On Lab, Discussion Forum

**Each term includes:**
- Clear definition
- 2-6 practical examples
- Related terms (clickable links)

**Glossary features:**
- Alphabetical grouping (A, B, C...)
- Real-time search (filters terms and definitions)
- Related term navigation (smooth scroll)
- Responsive card layout with hover effects

### 4. Help API (Flask Blueprint)

Created `src/api/help.py` with 4 endpoints:

```
GET /api/help/glossary
  → All terms with examples and related

GET /api/help/glossary/<term>
  → Specific term (case-insensitive)
  → 404 if not found

GET /api/help/search?q=query
  → Search terms and definitions
  → Returns: {query, count, results[]}

GET /api/help/topics
  → Available help topics metadata
  → Returns: [{id, title, description}]
```

**Dual content source:**
- Primary: `/static/data/glossary.json`
- Fallback: Static content in `help.js`
- Graceful degradation if file missing

## Files Created

```
static/js/onboarding.js          (200 lines) - Tour configuration and auto-init
static/css/components/help.css   (480 lines) - Help system and Intro.js styling
static/js/components/help.js     (420 lines) - HelpManager class
templates/partials/help-panel.html (25 lines) - Help panel structure
static/data/glossary.json       (11KB JSON) - 18 instructional design terms
src/api/help.py                 (200 lines) - Help API blueprint
templates/help/glossary.html    (220 lines) - Standalone glossary page
```

## Files Modified

```
templates/base.html              - Added Intro.js CDN, help.js, help panel
templates/partials/header.html   - Added help menu dropdown
templates/dashboard.html         - Added page-dashboard class, #create-course-btn
static/js/pages/dashboard.js     - Support both button IDs (compatibility)
app.py                           - Registered help_bp, added /glossary route
```

## How It Works

### Onboarding Flow

1. User visits dashboard (first time)
2. `onboarding.js` checks localStorage → not completed
3. Waits 500ms for page load
4. Starts Intro.js tour with dashboard steps
5. User completes or exits tour
6. Sets `onboarding_completed=true` in localStorage
7. Tour won't auto-start again (unless reset)

### Help Panel Flow

1. User clicks "Glossary" in help menu
2. Calls `window.help.togglePanel('glossary')`
3. HelpManager fetches `/api/help/glossary`
4. Renders terms grouped alphabetically
5. User searches → filters terms client-side
6. Clicks related term → scrolls to term, highlights

### Glossary API Flow

```
Request:  GET /api/help/glossary
Process:  Read static/data/glossary.json
          Parse JSON, validate structure
Response: {"terms": [{term, definition, examples, related}]}
```

## Verification

Tested scenarios:

1. **New user experience:**
   - Dashboard tour auto-starts ✓
   - Can skip and restart later ✓

2. **Help menu:**
   - Dropdown opens on click ✓
   - "Replay Tour" re-runs current page tour ✓
   - "Glossary" opens help panel ✓
   - "Reset Onboarding" clears localStorage ✓

3. **Glossary:**
   - API returns all 18 terms ✓
   - Search filters in real-time ✓
   - Related terms navigate correctly ✓
   - Alphabetical grouping works ✓

4. **Tooltips:**
   - Appear on hover over help buttons ✓
   - Positioned correctly above button ✓
   - Match dark theme ✓

## Performance Notes

- Intro.js CDN: ~50KB (gzip)
- Glossary JSON: 11KB (loads once, cached)
- Help panel: Lazy-loaded content
- Zero impact on initial page load (scripts load after DOM)

## Integration Points

**With authentication:**
- All help features require `@login_required`
- Glossary page at `/glossary` (protected)

**With existing UI:**
- Help menu button in header (next to user avatar)
- Help panel overlays content (z-index 999)
- Intro.js overlays everything (z-index 999999)

**With other features:**
- Help buttons can be added to any page with `.help-btn` class
- Tour steps reference specific element IDs (customizable per page)
- Glossary terms can reference actual features (WWHAA → video generation)

## Deviations from Plan

None - plan executed exactly as written.

## Known Limitations

1. **Page detection:** Relies on body class (e.g., `page-planner`)
   - **Impact:** Tours won't start if class missing
   - **Mitigation:** All major pages have body_class block

2. **Tour step targeting:** Uses element IDs and classes
   - **Impact:** Tour breaks if IDs change
   - **Mitigation:** IDs are stable, documented in onboarding.js

3. **Glossary is static:** No admin UI to edit terms
   - **Impact:** Must edit JSON directly
   - **Future:** Could add CRUD endpoints for terms

4. **Single language:** English only
   - **Impact:** Not i18n-ready
   - **Future:** Extract strings to translation files

## Next Phase Readiness

**Unblocked phases:**
- ✓ Any phase needing user guidance
- ✓ New user onboarding flows
- ✓ Advanced feature tutorials

**Provides foundation for:**
- Page-specific help content
- Video tutorials (link from help panel)
- Progressive disclosure of advanced features

**Blockers/Concerns:**
- None

## Lessons Learned

1. **Intro.js theming:** Required extensive CSS overrides (150+ lines)
   - Dark theme not supported out-of-box
   - Worth it for polished UX

2. **Glossary scope:** 18 terms is right balance
   - Covers essentials without overwhelming
   - Users can search if unsure

3. **localStorage persistence:** Simple, effective for onboarding state
   - No server-side complexity
   - Works across sessions

4. **Help panel architecture:** Flexible for future expansion
   - Can add help content without code changes
   - Static fallback ensures robustness
