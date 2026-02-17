# Phase 12: AI Interactive Features — Context

## Decisions

### Content Import Flow

**Import Sources**: Full multi-source support
- Paste from clipboard
- File upload (drag & drop)
- URL fetch with authentication

**Supported Formats**: Comprehensive format coverage
- Plain text, JSON, Markdown
- DOCX (Word documents)
- CSV (spreadsheets)
- HTML
- ZIP archives
- SCORM packages
- QTI files (quiz interchange)

**AI Enhancement**: Dual-mode enhancement
- Auto-analyze on import (detect structure, suggest content type)
- Manual trigger for user-controlled enhancement

**Import Locations**: Both pages
- Planner page (course structure import)
- Studio page (content import)

**Conflict Handling**: Ask each time
- When importing over existing content, prompt user
- Options: Replace, Merge, Cancel

**Preview Mode**: Direct import
- Import immediately, edit afterwards
- No preview step required

**URL Authentication**: Full integrations
- Public URLs (no auth)
- Google Docs OAuth
- Additional OAuth providers as needed

**AI Conversion**: Suggest with confirmation
- AI analyzes content and suggests appropriate content type
- User confirms or changes before finalizing

**Bulk Import**: Full package support
- ZIP archives with multiple files
- SCORM packages (full fidelity parsing)
- QTI files (quiz import with full fidelity)

**Error Handling**: Best effort + review
- Import what can be parsed
- Flag problematic items for user review
- Don't fail entire import for partial issues

**Attribution**: Full provenance tracking
- Track original source for all imported content
- Store import metadata (source URL, date, original format)

**Import UI**: Full page
- Dedicated import page/modal
- Not inline in existing editors

**Bidirectional Sync**: Import + export
- Import from Google Docs, etc.
- Export back to those services

**Asset Handling**: User chooses
- Option to reference external assets (links)
- Option to download and embed assets locally

**Import History**: No history
- Don't track import log
- Focus on current content state

### Inline AI Toolbar

**Trigger**: Selection + keyboard shortcut
- Toolbar appears on text selection
- Also accessible via keyboard shortcut

**Actions**: Full suite
- Improve
- Expand
- Simplify
- Rewrite
- Fix Grammar
- Translate
- Change Tone
- Add Examples
- Make Academic
- Summarize

**Suggestion Display**: All options available
- Inline replacement
- Side-by-side diff view
- Popup preview

**Custom Prompt**: Always visible
- Free-text prompt input always available in toolbar
- Not hidden behind menu

**Context Awareness**: Content-type specific + smart highlight
- Toolbar actions adapt to content type (quiz vs reading vs video)
- Smart highlight for potential issues (passive voice, complexity, etc.)

**Multiple Suggestions**: Regenerate button
- Single suggestion shown at a time
- Regenerate button to get alternative

**Autocomplete**: Ghost text + sentence completion
- Copilot-style ghost text suggestions
- Sentence completion on demand

**Bloom's Level Indicator**: Show + suggest
- Display current Bloom's level for selected content
- Suggest adjustments to match target level

**Learning Outcome Context**: Active alignment
- Show which outcomes current content addresses
- Warn when edits drift from mapped outcomes

**Keyboard Shortcuts**: Full customizable system
- Default shortcuts for common actions
- User can customize all shortcuts

**Toolbar Scope**: Any scope
- Apply to selection
- Apply to section/paragraph
- Apply to whole document

**AI Chat**: Inline chat in toolbar
- Chat interface embedded in toolbar
- Ask questions about content, get suggestions

**Formatting Suggestions**: Full formatting
- Suggest heading structure
- Suggest list formatting
- Suggest emphasis and structure improvements

**Tone Presets**: Custom + built-in
- Built-in presets (Academic, Conversational, Professional)
- User can create custom tone presets

**Track Changes**: Full revision mode
- Show all AI changes as tracked revisions
- Accept/reject individual changes (like Word)

**Version History**: Named versions
- Save named snapshots of content
- Compare and restore previous versions

### Interactive Coach Chat

**Access Mode**: Both options
- Separate student view for actual learner interaction
- Preview mode in Studio for instructor testing

**Guardrails**: Hybrid approach
- Must cover key learning points
- Flexible on order and phrasing
- Not rigidly scripted

**Socratic Method**: Configurable per activity
- Enable/disable Socratic questioning per coach activity
- When enabled, coach asks guiding questions rather than giving answers

**Persona**: Instructor configurable
- Coach name
- Personality traits
- Communication style
- Avatar/appearance

**Off-Topic Handling**: Configurable
- Set how strictly coach stays on topic
- Options from strict redirect to flexible exploration

**Transcripts**: Always save for instructor
- All student-coach conversations logged
- Instructor can review transcripts

**Evaluation**: Configurable rubric + AI summary + coaching report
- Rubric levels configurable per activity
- AI generates summary of student performance
- Coaching report with recommendations

**Session Continuity**: Both options
- Fresh start (new conversation)
- Continue previous (resume where left off)

**Media Support**: Configurable per coach activity
- Enable/disable media in chat (images, diagrams)
- Per-activity setting

**Hints System**: Configurable per activity
- Enable/disable hints
- Configure hint frequency and style

**Time Limits**: Configurable per activity
- Optional time limit on coach sessions
- Behavior when time expires (warning, end session, extend)

### AI Response Speed & UX

**Progress Indication**: Context-appropriate indicators
- Simple spinner for quick operations
- Streaming text for content generation
- Progress stages for multi-step operations
- Automatic selection based on operation type

**Timeout Handling**: Configurable per operation
- Keep waiting option for long operations
- Offer cancel after threshold
- Background processing with notification
- User can configure behavior

**Error Recovery**: Full resilience
- Auto-retry 2-3 times before showing error
- Fallback options (different model, simpler request, manual)
- Save draft state so no work is lost

**Caching & Prefetching**: Full optimization
- Session cache for undo/redo
- Smart prefetch for likely requests
- Cache common operations

**Concurrent Operations**: User control
- User can set priority for queued requests
- Control parallelism settings
- See queue status

**Quality vs Speed**: Per-operation choice
- Each AI request can be configured
- "Fast Draft" vs "Best Quality" options
- Slider or preset selection

**Offline Mode**: Full offline support
- Queue AI requests for when service returns
- Local fallbacks where possible
- Offline editing with sync later

**Rate Limit Handling**: Full management
- Graceful throttle on high demand
- Priority queue for important requests
- Usage dashboard showing consumption
- Alerts before hitting limits

## Claude's Discretion

The following areas are left to implementation judgment:

- Specific UI component library choices
- Exact keyboard shortcut defaults
- API endpoint structure
- Database schema for transcripts and versions
- Specific OAuth provider implementation order
- Cache invalidation strategies
- Prefetch prediction algorithms
- Specific retry timing and backoff strategies

## Deferred Ideas

None captured during this discussion.
