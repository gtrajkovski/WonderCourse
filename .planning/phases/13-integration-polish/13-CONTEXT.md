# Phase 13: Integration & Polish - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

## Phase Boundary

End-to-end workflow refinement ensuring all 12 phases work together smoothly. Users can complete full journeys from registration through export without errors. Includes error handling standardization, performance optimization, and in-app help system. No new features — polish and integration only.

## Decisions

### E2E Workflow Testing

**Test Coverage:** All major paths
- Happy path: Registration → Course → Blueprint → Content → Validation → Export
- Collaboration: Sharing, multi-user editing, role permissions
- Import flows: Paste, upload, URL, SCORM/QTI
- Coach interactions: Chat, evaluation, transcripts
- Textbook generation: Chapters, coherence validation

**Test Structure:** Hybrid approach
- Automated browser tests (Playwright) for regression
- Manual test scripts for exploratory testing

**Test Data:** Both fixtures and fresh data with reset
- Seeded fixtures for speed (known state)
- Fresh data option for clean environment
- Reset capability between test runs

**AI in Tests:** Mock by default, real optional
- Mock AI responses for fast, deterministic tests
- Flag to enable real AI calls for integration verification (e.g., `--real-ai`)

### Error Handling & Feedback

**Error Display:** Contextual + toast
- Inline errors where relevant (form validation, field-level)
- Toast notifications for system-level issues (network, server errors)
- Non-blocking unless action required

**Error Recovery:** Smart recovery
- Auto-retry for transient failures (network timeout, 5xx)
- Manual retry button for persistent failures
- Cancel option to abort and return to stable state
- Suggested alternatives when applicable

**Error Verbosity:** Context-aware
- User-friendly messages in UI (plain language)
- Technical details in browser console for developers
- No jargon in user-facing messages

### Claude's Discretion: Error Logging
Claude can determine appropriate logging strategy (console, localStorage, server-side).

### Performance & Loading

**AI Progress:** Streaming preview where possible, stage indicators otherwise
- For streaming-capable endpoints: Show content as it generates
- For non-streaming: Stage indicators ("Analyzing content..." → "Writing sections..." → "Formatting...")
- Always show elapsed time for long operations

**Timeout Handling:** Adaptive thresholds
- Quick operations (save, navigation): 30 seconds
- Content generation: 90 seconds
- Large operations (export, textbook): 120 seconds
- After threshold: Show warning with cancel/keep waiting options

**Large Courses:** Lazy loading
- Load modules on demand as user navigates
- Initial load shows course structure (titles, counts)
- Full content loaded when user expands/selects

### Claude's Discretion: Navigation Feedback
Claude can determine best UX practice for page transitions (progress bar, skeleton screens, or none based on load times).

### Help & Documentation

**Inline Help:** All three levels
- Tooltips on icons and interactive elements
- Info buttons (?) for detailed explanations
- Contextual help panels on complex pages (collapsible)

**Onboarding:** Interactive walkthrough + accessible tour
- First-time users: Guided step-by-step creation of first course
- Tour available anytime: Menu option to replay key feature highlights
- Progressive disclosure: Don't overwhelm, reveal features as needed

**Documentation Format:** In-app help pages
- Built-in documentation within the app
- Searchable help system
- Links to relevant help from contextual (?) buttons

**Educational Context:** Full glossary
- Comprehensive glossary of instructional design terms
- WWHAA, Bloom's taxonomy, SCORM, etc. explained
- Terms linked from context where they appear
- Examples with each definition

## Claude's Discretion

The following areas are left to implementation judgment:
- Error logging strategy (console, localStorage, server-side)
- Navigation feedback mechanism (progress bar vs skeleton screens)
- Specific transition animations
- Help panel placement and toggle behavior
- Tour/walkthrough library choice

## Deferred Ideas

None captured during this discussion.

---

*Phase: 13-integration-polish*
*Context gathered: 2026-02-11*
