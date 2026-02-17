/**
 * Video Studio - Teleprompter and timing tools for video scripts
 *
 * Provides:
 * - Teleprompter view with auto-scroll
 * - Per-section timing breakdown
 * - Playback controls with speed adjustment
 * - Section navigation
 * - Speaker notes overlay
 * - Keyboard shortcuts
 */
class VideoStudio {
    constructor(options = {}) {
        this.activityId = options.activityId || null;
        this.activityTitle = options.activityTitle || 'Video Script';
        this.content = options.content || {};  // Parsed video script
        this.metadata = options.metadata || {};  // Section timings

        // Playback state
        this.isPlaying = false;
        this.scrollSpeed = 1.0;  // 1.0 = matches 150 WPM
        this.currentSectionIndex = 0;
        this.elapsedSeconds = 0;

        // UI state
        this.showNotes = false;
        this.isFullscreen = false;

        // Section order
        this.sectionKeys = ['hook', 'objective', 'content', 'ivq', 'summary', 'cta'];
        this.sectionLabels = {
            hook: 'Hook',
            objective: 'Learning Objective',
            content: 'Main Content',
            ivq: 'In-Video Question',
            summary: 'Summary',
            cta: 'Call to Action'
        };

        // Timer references
        this.playbackTimer = null;
        this.scrollAnimationId = null;

        // DOM references (set in init)
        this.modal = null;
        this.teleprompterContent = null;
        this.sectionElements = [];
    }

    /**
     * Initialize the video studio
     */
    init() {
        this.modal = new Modal('video-studio-modal');
        this.cacheElements();
        this.bindEventHandlers();
    }

    /**
     * Cache DOM element references
     */
    cacheElements() {
        this.teleprompterContent = document.getElementById('teleprompter-content');
        this.teleprompterContainer = document.getElementById('teleprompter-container');
        this.sectionTimingList = document.getElementById('section-timing-list');
        this.elapsedTimeEl = document.getElementById('studio-elapsed-time');
        this.totalTimeEl = document.getElementById('studio-total-time');
        this.progressBar = document.getElementById('timing-progress-bar');
        this.speedSlider = document.getElementById('scroll-speed');
        this.speedValueEl = document.getElementById('speed-value');
        this.currentSectionLabel = document.getElementById('current-section-label');
        this.speakerNotesOverlay = document.getElementById('speaker-notes-overlay');
        this.currentSpeakerNotes = document.getElementById('current-speaker-notes');
        this.playPauseBtn = document.getElementById('btn-play-pause');
        this.titleEl = document.getElementById('video-studio-title');
        this.subtitleEl = document.getElementById('video-studio-subtitle');
    }

    /**
     * Bind all event handlers
     */
    bindEventHandlers() {
        // Playback controls
        document.getElementById('btn-play-pause')?.addEventListener('click', () => this.togglePlayPause());
        document.getElementById('btn-rewind')?.addEventListener('click', () => this.rewind());
        document.getElementById('btn-stop')?.addEventListener('click', () => this.stop());

        // Speed control
        this.speedSlider?.addEventListener('input', (e) => this.setSpeed(parseFloat(e.target.value)));
        document.getElementById('btn-speed-down')?.addEventListener('click', () => this.adjustSpeed(-0.1));
        document.getElementById('btn-speed-up')?.addEventListener('click', () => this.adjustSpeed(0.1));

        // Section navigation
        document.getElementById('btn-prev-section')?.addEventListener('click', () => this.prevSection());
        document.getElementById('btn-next-section')?.addEventListener('click', () => this.nextSection());

        // Notes toggle
        document.getElementById('btn-toggle-notes')?.addEventListener('click', () => this.toggleNotes());
        document.getElementById('btn-close-notes')?.addEventListener('click', () => this.hideNotes());

        // Fullscreen
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => this.toggleFullscreen());

        // Shortcuts help
        document.getElementById('shortcuts-toggle')?.addEventListener('click', () => this.toggleShortcutsPanel());

        // Section timing clicks
        this.sectionTimingList?.addEventListener('click', (e) => {
            const item = e.target.closest('.section-timing-item');
            if (item) {
                const index = parseInt(item.dataset.index, 10);
                this.jumpToSection(index);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // Close shortcuts panel on click outside
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('shortcuts-panel');
            const toggle = document.getElementById('shortcuts-toggle');
            if (panel && !panel.contains(e.target) && !toggle.contains(e.target)) {
                panel.style.display = 'none';
            }
        });
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboard(e) {
        // Only handle when modal is open
        if (!this.modal || !document.getElementById('video-studio-modal')?.classList.contains('open')) {
            return;
        }

        switch (e.key) {
            case ' ':  // Space - play/pause
                e.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                this.prevSection();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextSection();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.adjustSpeed(0.1);
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.adjustSpeed(-0.1);
                break;
            case 'n':
            case 'N':
                e.preventDefault();
                this.toggleNotes();
                break;
            case 'f':
            case 'F':
                e.preventDefault();
                this.toggleFullscreen();
                break;
            case 'Escape':
                // Let modal handle escape
                break;
        }
    }

    /**
     * Open the video studio modal
     */
    open() {
        this.renderTeleprompter();
        this.renderTimingSidebar();
        this.updateTotalTime();
        this.reset();
        this.modal.open();
    }

    /**
     * Update content and metadata
     */
    setContent(content, metadata, activityTitle) {
        this.content = content;
        this.metadata = metadata;
        this.activityTitle = activityTitle || 'Video Script';
    }

    /**
     * Render teleprompter content
     */
    renderTeleprompter() {
        if (!this.teleprompterContent) return;

        // Update title
        if (this.titleEl) this.titleEl.textContent = 'Video Studio';
        if (this.subtitleEl) this.subtitleEl.textContent = this.activityTitle;

        let html = '';
        this.sectionElements = [];

        for (let i = 0; i < this.sectionKeys.length; i++) {
            const key = this.sectionKeys[i];
            const sectionData = this.content[key];

            if (!sectionData) continue;

            const scriptText = typeof sectionData === 'object'
                ? sectionData.script_text || ''
                : sectionData;

            const title = typeof sectionData === 'object' && sectionData.title
                ? sectionData.title
                : this.sectionLabels[key];

            html += `
                <div class="teleprompter-section${i === 0 ? ' active' : ''}"
                     data-section="${key}"
                     data-index="${i}">
                    <div class="teleprompter-section-label">${this.sectionLabels[key]}</div>
                    ${title !== this.sectionLabels[key] ? `<div class="teleprompter-section-title">${this.escapeHtml(title)}</div>` : ''}
                    <div class="teleprompter-text">${this.escapeHtml(scriptText)}</div>
                </div>
            `;
        }

        this.teleprompterContent.innerHTML = html;

        // Cache section elements
        this.sectionElements = Array.from(
            this.teleprompterContent.querySelectorAll('.teleprompter-section')
        );
    }

    /**
     * Render timing sidebar
     */
    renderTimingSidebar() {
        if (!this.sectionTimingList) return;

        const timings = this.metadata.section_timings || {};
        let html = '';

        for (let i = 0; i < this.sectionKeys.length; i++) {
            const key = this.sectionKeys[i];
            const sectionData = this.content[key];

            if (!sectionData) continue;

            const duration = timings[key] || 0;
            const formattedDuration = this.formatTime(duration * 60);

            html += `
                <div class="section-timing-item${i === 0 ? ' active' : ''}"
                     data-section="${key}"
                     data-index="${i}">
                    <span class="section-timing-name">${this.sectionLabels[key]}</span>
                    <span class="section-timing-duration">${formattedDuration}</span>
                </div>
            `;
        }

        this.sectionTimingList.innerHTML = html;
    }

    /**
     * Update total time display
     */
    updateTotalTime() {
        const totalMinutes = this.metadata.estimated_duration_minutes || 0;
        if (this.totalTimeEl) {
            this.totalTimeEl.textContent = this.formatTime(totalMinutes * 60);
        }
    }

    /**
     * Toggle play/pause
     */
    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    /**
     * Start playback
     */
    play() {
        this.isPlaying = true;
        this.updatePlayPauseButton();
        this.startTimer();
        this.startAutoScroll();
    }

    /**
     * Pause playback
     */
    pause() {
        this.isPlaying = false;
        this.updatePlayPauseButton();
        this.stopTimer();
        this.stopAutoScroll();
    }

    /**
     * Stop playback and reset
     */
    stop() {
        this.pause();
        this.reset();
    }

    /**
     * Rewind to start
     */
    rewind() {
        this.pause();
        this.reset();
    }

    /**
     * Reset to initial state
     */
    reset() {
        this.elapsedSeconds = 0;
        this.currentSectionIndex = 0;
        this.updateElapsedDisplay();
        this.updateProgress();
        this.updateCurrentSection();
        this.scrollToSection(0, false);
    }

    /**
     * Update play/pause button state
     */
    updatePlayPauseButton() {
        if (!this.playPauseBtn) return;

        const playIcon = this.playPauseBtn.querySelector('.play-icon');
        const pauseIcon = this.playPauseBtn.querySelector('.pause-icon');

        if (this.isPlaying) {
            if (playIcon) playIcon.style.display = 'none';
            if (pauseIcon) pauseIcon.style.display = 'inline';
        } else {
            if (playIcon) playIcon.style.display = 'inline';
            if (pauseIcon) pauseIcon.style.display = 'none';
        }
    }

    /**
     * Start elapsed timer
     */
    startTimer() {
        this.stopTimer();  // Clear any existing timer

        this.playbackTimer = setInterval(() => {
            this.elapsedSeconds += 0.1 * this.scrollSpeed;
            this.updateElapsedDisplay();
            this.updateProgress();
            this.checkSectionTransition();
        }, 100);
    }

    /**
     * Stop elapsed timer
     */
    stopTimer() {
        if (this.playbackTimer) {
            clearInterval(this.playbackTimer);
            this.playbackTimer = null;
        }
    }

    /**
     * Start auto-scroll animation
     */
    startAutoScroll() {
        this.stopAutoScroll();

        const scrollContainer = this.teleprompterContent;
        if (!scrollContainer) return;

        // Calculate scroll speed: pixels per frame
        // At 150 WPM and ~10 words per line, ~15 lines per minute
        // Assuming ~40px per line, ~600px per minute at 1x speed
        // At 60fps, that's 10px per second, ~0.17px per frame
        const basePixelsPerSecond = 10;
        const pixelsPerFrame = (basePixelsPerSecond * this.scrollSpeed) / 60;

        const scroll = () => {
            if (!this.isPlaying) return;

            scrollContainer.scrollTop += pixelsPerFrame;
            this.scrollAnimationId = requestAnimationFrame(scroll);
        };

        this.scrollAnimationId = requestAnimationFrame(scroll);
    }

    /**
     * Stop auto-scroll animation
     */
    stopAutoScroll() {
        if (this.scrollAnimationId) {
            cancelAnimationFrame(this.scrollAnimationId);
            this.scrollAnimationId = null;
        }
    }

    /**
     * Check if we've scrolled to a new section
     */
    checkSectionTransition() {
        const timings = this.metadata.section_timings || {};
        let cumulativeTime = 0;

        for (let i = 0; i < this.sectionKeys.length; i++) {
            const key = this.sectionKeys[i];
            const sectionDuration = (timings[key] || 0) * 60;  // Convert to seconds
            cumulativeTime += sectionDuration;

            if (this.elapsedSeconds < cumulativeTime) {
                if (i !== this.currentSectionIndex) {
                    this.currentSectionIndex = i;
                    this.updateCurrentSection();
                }
                break;
            }
        }

        // Check if we've reached the end
        const totalSeconds = (this.metadata.estimated_duration_minutes || 0) * 60;
        if (this.elapsedSeconds >= totalSeconds) {
            this.pause();
        }
    }

    /**
     * Update current section UI
     */
    updateCurrentSection() {
        const key = this.sectionKeys[this.currentSectionIndex];

        // Update section label
        if (this.currentSectionLabel) {
            this.currentSectionLabel.textContent = this.sectionLabels[key] || key;
        }

        // Update sidebar
        const timingItems = this.sectionTimingList?.querySelectorAll('.section-timing-item');
        timingItems?.forEach((item, i) => {
            item.classList.remove('active', 'completed');
            if (i === this.currentSectionIndex) {
                item.classList.add('active');
            } else if (i < this.currentSectionIndex) {
                item.classList.add('completed');
            }
        });

        // Update teleprompter sections
        this.sectionElements.forEach((el, i) => {
            el.classList.remove('active');
            if (i === this.currentSectionIndex) {
                el.classList.add('active');
            }
        });

        // Update speaker notes
        this.updateSpeakerNotes();
    }

    /**
     * Update speaker notes display
     */
    updateSpeakerNotes() {
        const key = this.sectionKeys[this.currentSectionIndex];
        const sectionData = this.content[key];

        if (!this.currentSpeakerNotes) return;

        let notes = '';
        if (sectionData && typeof sectionData === 'object') {
            notes = sectionData.speaker_notes || '';
        }

        this.currentSpeakerNotes.textContent = notes || 'No speaker notes for this section.';
    }

    /**
     * Update elapsed time display
     */
    updateElapsedDisplay() {
        if (this.elapsedTimeEl) {
            this.elapsedTimeEl.textContent = this.formatTime(this.elapsedSeconds);
        }
    }

    /**
     * Update progress bar
     */
    updateProgress() {
        const totalSeconds = (this.metadata.estimated_duration_minutes || 0) * 60;
        if (totalSeconds <= 0) return;

        const progress = Math.min((this.elapsedSeconds / totalSeconds) * 100, 100);

        if (this.progressBar) {
            this.progressBar.style.width = `${progress}%`;
        }
    }

    /**
     * Set playback speed
     */
    setSpeed(speed) {
        this.scrollSpeed = Math.max(0.5, Math.min(2, speed));

        if (this.speedSlider) {
            this.speedSlider.value = this.scrollSpeed;
        }
        if (this.speedValueEl) {
            this.speedValueEl.textContent = `${this.scrollSpeed.toFixed(1)}x`;
        }

        // Restart scroll if playing
        if (this.isPlaying) {
            this.startAutoScroll();
        }
    }

    /**
     * Adjust speed by delta
     */
    adjustSpeed(delta) {
        this.setSpeed(this.scrollSpeed + delta);
    }

    /**
     * Go to previous section
     */
    prevSection() {
        if (this.currentSectionIndex > 0) {
            this.jumpToSection(this.currentSectionIndex - 1);
        }
    }

    /**
     * Go to next section
     */
    nextSection() {
        if (this.currentSectionIndex < this.sectionKeys.length - 1) {
            this.jumpToSection(this.currentSectionIndex + 1);
        }
    }

    /**
     * Jump to specific section
     */
    jumpToSection(index) {
        if (index < 0 || index >= this.sectionElements.length) return;

        // Calculate elapsed time to this section
        const timings = this.metadata.section_timings || {};
        let elapsed = 0;

        for (let i = 0; i < index; i++) {
            const key = this.sectionKeys[i];
            elapsed += (timings[key] || 0) * 60;
        }

        this.elapsedSeconds = elapsed;
        this.currentSectionIndex = index;

        this.updateElapsedDisplay();
        this.updateProgress();
        this.updateCurrentSection();
        this.scrollToSection(index, true);
    }

    /**
     * Scroll teleprompter to section
     */
    scrollToSection(index, smooth = true) {
        const section = this.sectionElements[index];
        if (!section || !this.teleprompterContent) return;

        const containerRect = this.teleprompterContent.getBoundingClientRect();
        const sectionRect = section.getBoundingClientRect();

        // Calculate scroll position to center section at reading line (35% from top)
        const readingLineOffset = containerRect.height * 0.35;
        const targetScroll = this.teleprompterContent.scrollTop +
            (sectionRect.top - containerRect.top) - readingLineOffset;

        if (smooth) {
            this.teleprompterContent.scrollTo({
                top: targetScroll,
                behavior: 'smooth'
            });
        } else {
            this.teleprompterContent.scrollTop = targetScroll;
        }
    }

    /**
     * Toggle speaker notes overlay
     */
    toggleNotes() {
        this.showNotes = !this.showNotes;

        if (this.speakerNotesOverlay) {
            if (this.showNotes) {
                this.speakerNotesOverlay.classList.add('visible');
            } else {
                this.speakerNotesOverlay.classList.remove('visible');
            }
        }

        // Update toggle button state
        const toggleBtn = document.getElementById('btn-toggle-notes');
        if (toggleBtn) {
            toggleBtn.classList.toggle('active', this.showNotes);
        }
    }

    /**
     * Hide speaker notes
     */
    hideNotes() {
        this.showNotes = false;
        this.speakerNotesOverlay?.classList.remove('visible');

        const toggleBtn = document.getElementById('btn-toggle-notes');
        toggleBtn?.classList.remove('active');
    }

    /**
     * Toggle fullscreen mode
     */
    toggleFullscreen() {
        const modalContent = document.querySelector('#video-studio-modal .modal-content');
        if (!modalContent) return;

        if (!document.fullscreenElement) {
            modalContent.requestFullscreen().catch(err => {
                console.warn('Fullscreen request failed:', err);
            });
            this.isFullscreen = true;
        } else {
            document.exitFullscreen();
            this.isFullscreen = false;
        }

        // Update button state
        const btn = document.getElementById('btn-fullscreen');
        btn?.classList.toggle('active', this.isFullscreen);
    }

    /**
     * Toggle shortcuts panel
     */
    toggleShortcutsPanel() {
        const panel = document.getElementById('shortcuts-panel');
        if (panel) {
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    }

    /**
     * Format seconds to MM:SS
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for global access
window.VideoStudio = VideoStudio;
