# Phase 7: Video Lesson Studio

## Overview

Enhanced video script editing with teleprompter mode and timing tools. Provides authors with professional-grade tools for script review, rehearsal, and delivery.

**Key Features:**
- Teleprompter view with adjustable scroll speed
- Per-section timing breakdown based on 150 WPM speaking rate
- Live elapsed timer with section markers
- Speaker notes overlay toggle
- Full-screen presentation mode

## Implementation Plans

### Plan 1: Enhance Video Script Metadata

**Modify `src/generators/video_script_generator.py`**

Already calculates `section_word_counts` but doesn't persist timing. Add:

```python
def extract_metadata(self, content: VideoScriptSchema, ...) -> Dict[str, Any]:
    # ... existing code ...

    # Calculate per-section timing at 150 WPM
    section_timings = {}
    for section, wc in section_word_counts.items():
        section_timings[section] = round(wc / 150, 2)  # minutes

    return {
        'word_count': total_word_count,
        'estimated_duration_minutes': estimated_duration,
        'section_word_counts': section_word_counts,
        'section_timings': section_timings,  # NEW
    }
```

---

### Plan 2: Video Studio Template

**Create `templates/partials/video-studio.html`**

Teleprompter and timing UI partial:

```html
<!-- Video Studio Modal -->
<div id="video-studio-modal" class="modal modal-fullscreen" aria-hidden="true">
    <div class="video-studio">
        <!-- Header -->
        <div class="video-studio-header">
            <h2 id="video-studio-title">Video Studio</h2>
            <div class="studio-controls">
                <button class="btn btn-icon" id="btn-toggle-notes" title="Toggle speaker notes">Notes</button>
                <button class="btn btn-icon" id="btn-fullscreen" title="Full screen">Fullscreen</button>
                <button class="btn btn-secondary" data-modal-close>Exit</button>
            </div>
        </div>

        <!-- Main Content -->
        <div class="video-studio-body">
            <!-- Timing Sidebar -->
            <div class="timing-sidebar">
                <div class="timing-header">
                    <h3>Timing</h3>
                    <div class="total-duration">
                        <span id="elapsed-time">0:00</span> / <span id="total-time">0:00</span>
                    </div>
                </div>
                <div class="section-timing-list" id="section-timing-list">
                    <!-- Section timing items rendered here -->
                </div>
            </div>

            <!-- Teleprompter -->
            <div class="teleprompter-container">
                <div class="teleprompter-content" id="teleprompter-content">
                    <!-- Script sections rendered here -->
                </div>

                <!-- Speaker Notes Overlay -->
                <div class="speaker-notes-overlay" id="speaker-notes-overlay" style="display: none;">
                    <div class="notes-content" id="current-speaker-notes"></div>
                </div>
            </div>
        </div>

        <!-- Footer Controls -->
        <div class="video-studio-footer">
            <div class="playback-controls">
                <button class="btn btn-icon" id="btn-rewind" title="Restart">⏮</button>
                <button class="btn btn-primary btn-large" id="btn-play-pause" title="Play/Pause">▶</button>
                <button class="btn btn-icon" id="btn-stop" title="Stop">⏹</button>
            </div>
            <div class="speed-control">
                <label>Speed:</label>
                <input type="range" id="scroll-speed" min="0.5" max="2" step="0.1" value="1">
                <span id="speed-value">1.0x</span>
            </div>
            <div class="section-nav">
                <button class="btn btn-secondary" id="btn-prev-section">← Prev</button>
                <span id="current-section-label">Hook</span>
                <button class="btn btn-secondary" id="btn-next-section">Next →</button>
            </div>
        </div>
    </div>
</div>
```

**Modify `templates/studio.html`**

Add Video Studio button in controls panel and include partial:

```html
<!-- In section-edit, after Edit Mode button -->
<button class="btn btn-secondary btn-block" id="btn-video-studio" style="margin-top: 8px; display: none;">
    Video Studio
</button>

<!-- Include partial at end of content block -->
{% include 'partials/video-studio.html' %}
```

---

### Plan 3: Video Studio JavaScript

**Create `static/js/components/video-studio.js`**

```javascript
class VideoStudio {
    constructor(options) {
        this.activityId = options.activityId;
        this.content = options.content;  // Parsed video script
        this.metadata = options.metadata;  // Section timings

        this.isPlaying = false;
        this.scrollSpeed = 1.0;  // 1.0 = 150 WPM
        this.currentSection = 0;
        this.elapsedSeconds = 0;
        this.showNotes = false;

        this.sections = ['hook', 'objective', 'content', 'ivq', 'summary', 'cta'];
        this.sectionLabels = {
            hook: 'Hook',
            objective: 'Learning Objective',
            content: 'Main Content',
            ivq: 'In-Video Question',
            summary: 'Summary',
            cta: 'Call to Action'
        };
    }

    init() {
        this.modal = new Modal('video-studio-modal');
        this.bindEventHandlers();
        this.renderTeleprompter();
        this.renderTimingSidebar();
    }

    open() {
        this.modal.open();
        this.reset();
    }

    renderTeleprompter() {
        // Render each section with markers
    }

    renderTimingSidebar() {
        // Render section timing list with progress indicators
    }

    play() {
        this.isPlaying = true;
        this.startTimer();
        this.startAutoScroll();
    }

    pause() {
        this.isPlaying = false;
        this.stopTimer();
        this.stopAutoScroll();
    }

    startAutoScroll() {
        // Calculate scroll speed based on WPM and speed multiplier
        // Smooth scroll through content
    }

    jumpToSection(sectionIndex) {
        // Scroll to section, update elapsed time
    }

    toggleNotes() {
        this.showNotes = !this.showNotes;
        // Show/hide speaker notes overlay
    }

    updateElapsedDisplay() {
        // Format MM:SS display
    }
}
```

---

### Plan 4: Video Studio CSS

**Create `static/css/components/video-studio.css`**

```css
/* Full-screen modal */
.modal-fullscreen .modal-content {
    width: 100vw;
    height: 100vh;
    max-width: none;
    max-height: none;
    border-radius: 0;
}

.video-studio {
    display: flex;
    flex-direction: column;
    height: 100%;
}

/* Header */
.video-studio-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-panel);
}

/* Body - sidebar + teleprompter */
.video-studio-body {
    flex: 1;
    display: flex;
    overflow: hidden;
}

/* Timing Sidebar */
.timing-sidebar {
    width: 250px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border-subtle);
    padding: var(--spacing-md);
    overflow-y: auto;
}

.section-timing-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-sm);
    margin-bottom: var(--spacing-xs);
    cursor: pointer;
}

.section-timing-item.active {
    background: var(--accent-primary);
    color: white;
}

.section-timing-item.completed {
    opacity: 0.6;
}

/* Teleprompter */
.teleprompter-container {
    flex: 1;
    position: relative;
    overflow: hidden;
    background: var(--bg-base);
}

.teleprompter-content {
    padding: 40vh var(--spacing-xl) 60vh;
    font-size: 2rem;
    line-height: 1.8;
    max-width: 800px;
    margin: 0 auto;
}

.teleprompter-section {
    margin-bottom: var(--spacing-xl);
    padding-bottom: var(--spacing-xl);
    border-bottom: 2px solid var(--border-subtle);
}

.teleprompter-section-label {
    font-size: 1rem;
    color: var(--accent-primary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: var(--spacing-md);
}

.teleprompter-text {
    color: var(--text-primary);
}

/* Center line indicator */
.teleprompter-container::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--accent-primary);
    opacity: 0.3;
    pointer-events: none;
    z-index: 10;
}

/* Speaker Notes Overlay */
.speaker-notes-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.9);
    color: var(--text-primary);
    padding: var(--spacing-lg);
    max-height: 30%;
    overflow-y: auto;
}

/* Footer */
.video-studio-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-panel);
}

.playback-controls {
    display: flex;
    gap: var(--spacing-sm);
}

.speed-control {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.section-nav {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}
```

---

### Plan 5: Studio Integration

**Modify `static/js/pages/studio.js`**

1. Show Video Studio button only for video content:
```javascript
updateControls() {
    // ... existing code ...

    const btnVideoStudio = document.getElementById('btn-video-studio');
    if (btnVideoStudio) {
        if (this.selectedActivity?.content_type === 'video' &&
            this.selectedActivity?.content) {
            btnVideoStudio.style.display = 'block';
        } else {
            btnVideoStudio.style.display = 'none';
        }
    }
}
```

2. Add event handler:
```javascript
bindEventHandlers() {
    // ... existing handlers ...

    const btnVideoStudio = document.getElementById('btn-video-studio');
    if (btnVideoStudio) {
        btnVideoStudio.addEventListener('click', () => this.openVideoStudio());
    }
}

openVideoStudio() {
    if (!this.selectedActivity?.content) return;

    const content = JSON.parse(this.selectedActivity.content);
    const metadata = this.selectedActivity.metadata || {};

    if (!window.videoStudio) {
        window.videoStudio = new VideoStudio({
            activityId: this.selectedActivityId,
            content: content,
            metadata: metadata
        });
        window.videoStudio.init();
    } else {
        window.videoStudio.content = content;
        window.videoStudio.metadata = metadata;
        window.videoStudio.renderTeleprompter();
        window.videoStudio.renderTimingSidebar();
    }

    window.videoStudio.open();
}
```

---

### Plan 6: Keyboard Shortcuts

Add keyboard controls for hands-free operation:

```javascript
// In VideoStudio.bindEventHandlers()
document.addEventListener('keydown', (e) => {
    if (!this.modal.isOpen) return;

    switch(e.key) {
        case ' ':  // Space - play/pause
            e.preventDefault();
            this.isPlaying ? this.pause() : this.play();
            break;
        case 'ArrowLeft':  // Previous section
            this.jumpToSection(this.currentSection - 1);
            break;
        case 'ArrowRight':  // Next section
            this.jumpToSection(this.currentSection + 1);
            break;
        case 'ArrowUp':  // Speed up
            this.setSpeed(this.scrollSpeed + 0.1);
            break;
        case 'ArrowDown':  // Speed down
            this.setSpeed(this.scrollSpeed - 0.1);
            break;
        case 'n':  // Toggle notes
            this.toggleNotes();
            break;
        case 'f':  // Toggle fullscreen
            this.toggleFullscreen();
            break;
        case 'Escape':  // Close
            this.modal.close();
            break;
    }
});
```

---

## Files to Create

| File | Description |
|------|-------------|
| `templates/partials/video-studio.html` | Video studio modal HTML |
| `static/js/components/video-studio.js` | VideoStudio class |
| `static/css/components/video-studio.css` | Video studio styles |
| `tests/test_video_studio.py` | JavaScript behavior tests (optional) |

## Files to Modify

| File | Changes |
|------|---------|
| `src/generators/video_script_generator.py` | Add section_timings to metadata |
| `templates/studio.html` | Add Video Studio button, include partial and scripts |
| `static/js/pages/studio.js` | Add openVideoStudio handler |

## Verification

1. **Manual testing:**
   - Generate video script content
   - Click "Video Studio" button
   - Verify teleprompter renders all sections
   - Verify timing sidebar shows correct durations
   - Test play/pause auto-scroll
   - Test speed adjustment (0.5x to 2x)
   - Test section navigation
   - Test speaker notes toggle
   - Test keyboard shortcuts
   - Test full-screen mode

2. **Edge cases:**
   - Empty sections
   - Very long content sections
   - Missing metadata

## Dependencies

- Requires video content to be generated first
- Uses existing Modal component from studio.js
- Builds on existing Activity metadata structure

## Notes

- Teleprompter scroll speed calculated: base_speed * speed_multiplier
- Base speed derived from 150 WPM speaking rate
- Section timing = word_count / 150 (in minutes)
- Padding at top/bottom of teleprompter centers active text
