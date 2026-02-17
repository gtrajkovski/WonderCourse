/**
 * Elapsed Timer - Tracks and displays elapsed time during generation
 */
class ElapsedTimer {
  constructor(displayElementId) {
    this.displayElement = document.getElementById(displayElementId);
    this.startTime = null;
    this.intervalId = null;
  }

  start() {
    this.startTime = Date.now();
    this.updateDisplay();
    this.intervalId = setInterval(() => this.updateDisplay(), 1000);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  reset() {
    this.stop();
    this.startTime = null;
    if (this.displayElement) {
      this.displayElement.textContent = '0';
    }
  }

  updateDisplay() {
    if (!this.startTime || !this.displayElement) return;

    const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
    this.displayElement.textContent = elapsed;
  }
}

/**
 * Studio Controller - Content generation and editing interface
 *
 * Manages:
 * - Activity selection and content preview
 * - Streaming content generation via SSE
 * - Inline editing with auto-save
 * - Regeneration with feedback
 * - Build state transitions
 */
class StudioController {
  constructor(courseId, initialActivityId = null) {
    this.courseId = courseId;
    this.selectedActivityId = initialActivityId;
    this.selectedActivity = null;
    this.course = null;

    // SSE connection for streaming
    this.currentEventSource = null;

    // Edit mode state
    this.isEditMode = false;

    // Modal reference
    this.editorModal = null;

    // Elapsed timer for generation
    this.elapsedTimer = null;

    // AbortController for canceling generation
    this.abortController = null;

    // Preview mode state
    this.previewMode = 'author';  // 'author' | 'learner'
    this.viewport = 'desktop';     // 'desktop' | 'tablet' | 'mobile'

    // Notes state
    this.activityNotes = [];

    // Variant state
    this.selectedVariant = { type: 'primary', depth: 'standard' };
    this.availableVariants = [];  // From /variants API
    this.variantModal = null;
  }

  async init() {
    // Initialize modals
    this.editorModal = new Modal('editor-modal');
    this.variantModal = new Modal('variant-modal');

    // Initialize elapsed timer
    this.elapsedTimer = new ElapsedTimer('elapsed-seconds');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
      this.bindHelpHandlers();
    }

    // Bind event handlers
    this.bindEventHandlers();

    // Setup length calculation listeners
    this.setupLengthCalculation();

    // Load course data
    await this.loadCourse();

    // If initial activity ID provided, select it
    if (this.selectedActivityId) {
      this.handleActivitySelect(this.selectedActivityId);
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => this.closeEventSource());
  }

  /**
   * Bind all event handlers
   */
  bindEventHandlers() {
    // Activity list click delegation
    const activityList = document.getElementById('activity-list');
    if (activityList) {
      activityList.addEventListener('click', (e) => {
        const activityItem = e.target.closest('.activity-item');
        if (activityItem) {
          const activityId = activityItem.dataset.activityId;
          this.handleActivitySelect(activityId);
        }
      });
    }

    // Generate button
    const btnGenerate = document.getElementById('btn-generate');
    if (btnGenerate) {
      btnGenerate.addEventListener('click', () => this.handleGenerate());
    }

    // Edit mode toggle
    const btnEditMode = document.getElementById('btn-edit-mode');
    if (btnEditMode) {
      btnEditMode.addEventListener('click', () => this.toggleEditMode());
    }

    // Full editor button
    const btnFullEditor = document.getElementById('btn-full-editor');
    if (btnFullEditor) {
      btnFullEditor.addEventListener('click', () => this.showFullEditor());
    }

    // Save editor button
    const btnSaveEditor = document.getElementById('btn-save-editor');
    if (btnSaveEditor) {
      btnSaveEditor.addEventListener('click', () => this.handleSaveEditor());
    }

    // Regenerate button
    const btnRegenerate = document.getElementById('btn-regenerate');
    if (btnRegenerate) {
      btnRegenerate.addEventListener('click', () => this.handleRegenerateWithFeedback());
    }

    // State transition buttons
    const btnMarkReviewed = document.getElementById('btn-mark-reviewed');
    if (btnMarkReviewed) {
      btnMarkReviewed.addEventListener('click', () => this.handleMarkReviewed());
    }

    const btnApprove = document.getElementById('btn-approve');
    if (btnApprove) {
      btnApprove.addEventListener('click', () => this.handleApprove());
    }

    // Cancel generation button
    const btnCancelGeneration = document.getElementById('cancel-generation');
    if (btnCancelGeneration) {
      btnCancelGeneration.addEventListener('click', () => this.handleCancelGeneration());
    }

    // Humanization buttons
    const btnHumanize = document.getElementById('btn-humanize');
    if (btnHumanize) {
      btnHumanize.addEventListener('click', () => this.handleHumanize());
    }

    const btnViewPatterns = document.getElementById('btn-view-patterns');
    if (btnViewPatterns) {
      btnViewPatterns.addEventListener('click', () => this.handleViewPatterns());
    }

    // Video Studio button
    const btnVideoStudio = document.getElementById('btn-video-studio');
    if (btnVideoStudio) {
      btnVideoStudio.addEventListener('click', () => this.openVideoStudio());
    }

    // Preview mode toggle
    const btnAuthorView = document.getElementById('btn-author-view');
    const btnLearnerPreview = document.getElementById('btn-learner-preview');
    if (btnAuthorView) {
      btnAuthorView.addEventListener('click', () => this.handleTogglePreviewMode('author'));
    }
    if (btnLearnerPreview) {
      btnLearnerPreview.addEventListener('click', () => this.handleTogglePreviewMode('learner'));
    }

    // Viewport selector
    const viewportSelector = document.getElementById('viewport-selector');
    if (viewportSelector) {
      viewportSelector.addEventListener('click', (e) => {
        const viewportBtn = e.target.closest('.viewport-btn');
        if (viewportBtn) {
          const viewport = viewportBtn.dataset.viewport;
          this.handleViewportChange(viewport);
        }
      });
    }

    // Notes panel
    const btnAddNote = document.getElementById('btn-add-note');
    if (btnAddNote) {
      btnAddNote.addEventListener('click', () => this.handleAddNote());
    }

    // Notes list delegation
    const notesList = document.getElementById('notes-list');
    if (notesList) {
      notesList.addEventListener('click', (e) => {
        const target = e.target;
        const noteCard = target.closest('.note-card');
        if (!noteCard) return;

        const noteId = noteCard.dataset.noteId;

        if (target.closest('.note-pin-btn')) {
          this.handleTogglePin(noteId);
        } else if (target.closest('.note-edit-btn')) {
          this.handleEditNote(noteId);
        } else if (target.closest('.note-delete-btn')) {
          this.handleDeleteNote(noteId);
        }
      });
    }

    // Variant tabs delegation
    const variantTabs = document.getElementById('variant-tabs');
    if (variantTabs) {
      variantTabs.addEventListener('click', (e) => {
        const tab = e.target.closest('.variant-tab');
        if (tab) {
          const variantType = tab.dataset.variant;
          const depthLevel = tab.dataset.depth || 'standard';
          this.handleVariantSelect(variantType, depthLevel);
        }
      });
    }

    // Depth pills delegation
    const depthPills = document.getElementById('depth-pills');
    if (depthPills) {
      depthPills.addEventListener('click', (e) => {
        const pill = e.target.closest('.depth-pill');
        if (pill && !pill.classList.contains('unavailable')) {
          const depth = pill.dataset.depth;
          this.handleVariantSelect(this.selectedVariant.type, depth);
        }
      });
    }

    // Add variant button
    const btnAddVariant = document.getElementById('btn-add-variant');
    if (btnAddVariant) {
      btnAddVariant.addEventListener('click', () => this.openVariantModal());
    }

    // Generate variant button in modal
    const btnGenerateVariant = document.getElementById('btn-generate-variant');
    if (btnGenerateVariant) {
      btnGenerateVariant.addEventListener('click', () => this.handleGenerateVariant());
    }
  }

  /**
   * Load course data from API
   */
  async loadCourse() {
    const activityList = document.getElementById('activity-list');

    try {
      // Show skeleton while loading
      if (activityList && window.skeleton) {
        window.skeleton.show(activityList);
      }

      this.course = await api.get(`/courses/${this.courseId}`);

    } catch (error) {
      toast.error(`Failed to load course: ${error.message}`);
    } finally {
      // Hide skeleton
      if (activityList && window.skeleton) {
        window.skeleton.hide(activityList);
      }
    }
  }

  /**
   * Handle activity selection
   */
  async handleActivitySelect(activityId) {
    // Update selection state
    this.selectedActivityId = activityId;

    // Find the activity in course data
    this.selectedActivity = this.findActivity(activityId);

    // Reset variant selection to primary/standard
    this.selectedVariant = { type: 'primary', depth: 'standard' };

    // Update UI selection
    this.updateActivityListSelection(activityId);

    // Load variants for this activity
    await this.loadVariants();

    // Load and render preview
    await this.renderPreview();

    // Update controls based on activity state
    this.updateControls();
  }

  /**
   * Find activity by ID in course data
   */
  findActivity(activityId) {
    if (!this.course || !this.course.modules) return null;

    for (const module of this.course.modules) {
      for (const lesson of (module.lessons || [])) {
        for (const activity of (lesson.activities || [])) {
          if (activity.id === activityId) {
            return activity;
          }
        }
      }
    }
    return null;
  }

  /**
   * Update activity list selection UI
   */
  updateActivityListSelection(activityId) {
    // Remove previous selection
    const previousSelected = document.querySelector('.activity-item.selected');
    if (previousSelected) {
      previousSelected.classList.remove('selected');
    }

    // Add selection to new item
    const newSelected = document.querySelector(`.activity-item[data-activity-id="${activityId}"]`);
    if (newSelected) {
      newSelected.classList.add('selected');
    }
  }

  /**
   * Render preview based on activity state and content
   */
  async renderPreview() {
    const previewEmpty = document.getElementById('preview-empty');
    const previewContent = document.getElementById('preview-content');
    const previewStreaming = document.getElementById('preview-streaming');
    const previewFooter = document.getElementById('preview-footer');
    const previewTitle = document.getElementById('preview-title');
    const previewBadge = document.getElementById('preview-badge');
    const previewBody = document.getElementById('preview-body');
    const previewModeToggle = document.getElementById('preview-mode-toggle');
    const notesPanel = document.getElementById('notes-panel');

    if (!this.selectedActivity) {
      // Show empty state
      previewEmpty.style.display = 'flex';
      previewContent.style.display = 'none';
      previewStreaming.style.display = 'none';
      previewFooter.style.display = 'none';
      previewTitle.textContent = 'Select an Activity';
      previewBadge.style.display = 'none';
      if (previewModeToggle) previewModeToggle.style.display = 'none';
      if (notesPanel) notesPanel.style.display = 'none';
      return;
    }

    // Show preview mode toggle when activity is selected
    if (previewModeToggle) previewModeToggle.style.display = 'flex';

    // Show notes panel only in author mode
    if (notesPanel && this.previewMode === 'author') {
      notesPanel.style.display = 'block';
      // Load notes for this activity
      this.loadActivityNotes();
    } else if (notesPanel) {
      notesPanel.style.display = 'none';
    }

    // Update header
    previewTitle.textContent = this.selectedActivity.title;
    previewBadge.textContent = this.formatContentType(this.selectedActivity.content_type);
    previewBadge.style.display = 'inline-block';

    const buildState = this.selectedActivity.build_state || 'draft';

    if (buildState === 'draft' && !this.selectedActivity.content) {
      // No content yet
      previewEmpty.style.display = 'flex';
      previewEmpty.innerHTML = `
        <div class="empty-icon">&#128196;</div>
        <p>No content yet. Click <strong>Generate</strong> to create content for this activity.</p>
      `;
      previewContent.style.display = 'none';
      previewStreaming.style.display = 'none';
      previewFooter.style.display = 'none';
    } else if (buildState === 'generating') {
      // Currently generating - use streaming display, not skeleton
      previewEmpty.style.display = 'none';
      previewContent.style.display = 'none';
      previewStreaming.style.display = 'flex';
      previewFooter.style.display = 'none';
    } else {
      // Has content - show skeleton briefly while rendering
      if (previewBody && window.skeleton) {
        window.skeleton.show(previewBody);
      }

      try {
        // Has content - render it
        previewEmpty.style.display = 'none';
        previewContent.style.display = 'block';
        previewStreaming.style.display = 'none';
        previewFooter.style.display = 'block';

        this.renderContent(this.selectedActivity);
        this.updateMetadata(this.selectedActivity);
        this.initAIToolbar();
      } finally {
        // Hide skeleton after render
        if (previewBody && window.skeleton) {
          // Small delay to show skeleton briefly
          setTimeout(() => {
            window.skeleton.hide(previewBody);
          }, 100);
        }
      }
    }
  }

  /**
   * Initialize AI toolbar for current activity
   */
  initAIToolbar() {
    if (!this.selectedActivity) return;

    const previewContent = document.getElementById('preview-content');
    if (!previewContent) return;

    // Detach previous toolbar if exists
    if (window.aiToolbar) {
      window.aiToolbar.detach();
    }

    // Get learning outcomes for context
    const learningOutcomes = this.course.learning_outcomes || [];

    // Initialize new toolbar
    window.aiToolbar = new AIToolbar({
      courseId: this.courseId,
      activityId: this.selectedActivity.id,
      contentType: this.selectedActivity.content_type,
      bloomLevel: this.selectedActivity.bloom_level,
      learningOutcomes: learningOutcomes.map(o => o.outcome_text || o.text),
      onContentChange: () => {
        // Reload course and re-render
        this.loadCourse().then(() => {
          this.selectedActivity = this.findActivity(this.selectedActivityId);
          this.renderPreview();
        });
      }
    });

    // Attach to preview content area
    window.aiToolbar.attach(previewContent);
  }

  /**
   * Format content type for display
   */
  formatContentType(contentType) {
    // Normalize - handle both string and object formats
    const type = typeof contentType === 'object' ? contentType?.value : contentType;
    const typeMap = {
      'video': 'Video Script',
      'reading': 'Reading',
      'quiz': 'Quiz',
      'hol': 'Hands-on Lab',
      'coach': 'Coach Dialogue',
      'lab': 'Lab',
      'discussion': 'Discussion',
      'assignment': 'Assignment',
      'project': 'Project',
      'rubric': 'Rubric'
    };
    return typeMap[type] || type;
  }

  /**
   * Render content based on type
   */
  renderContent(activity) {
    const previewContent = document.getElementById('preview-content');
    const content = activity.content;

    if (!content) {
      previewContent.innerHTML = '<p class="text-muted">No content available.</p>';
      return;
    }

    // Try to parse as JSON
    let contentData = content;
    if (typeof content === 'string') {
      try {
        contentData = JSON.parse(content);
      } catch (e) {
        // Plain text content
        previewContent.innerHTML = `<div class="content-section"><div class="content-section-body">${this.escapeHtml(content)}</div></div>`;
        return;
      }
    }

    // Normalize content type - handle both string and object formats
    const rawContentType = activity.content_type;
    const contentType = typeof rawContentType === 'object' ? rawContentType?.value : rawContentType;

    if (contentType === 'video') {
      previewContent.innerHTML = this.renderVideoScript(contentData);
    } else if (contentType === 'reading') {
      previewContent.innerHTML = this.renderReading(contentData);
    } else if (contentType === 'quiz') {
      previewContent.innerHTML = this.renderQuiz(contentData);
    } else if (contentType === 'hol') {
      previewContent.innerHTML = this.renderHOL(contentData);
    } else if (contentType === 'coach') {
      previewContent.innerHTML = this.renderCoach(contentData);
    } else if (contentType === 'discussion') {
      previewContent.innerHTML = this.renderDiscussion(contentData);
    } else if (contentType === 'lab') {
      previewContent.innerHTML = this.renderLab(contentData);
    } else if (contentType === 'assignment') {
      previewContent.innerHTML = this.renderAssignment(contentData);
    } else if (contentType === 'project') {
      previewContent.innerHTML = this.renderProject(contentData);
    } else {
      // Generic JSON rendering
      previewContent.innerHTML = this.renderGenericContent(contentData);
    }
  }

  /**
   * Render video script with WWHAA sections
   */
  renderVideoScript(content) {
    let html = '';

    // Add title if present
    if (content.title) {
      html += `<h2 class="video-title" style="margin-bottom: 1.5rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    const sections = [
      { key: 'hook', label: 'Hook' },
      { key: 'objective', label: 'Objective' },
      { key: 'content', label: 'Content' },
      { key: 'ivq', label: 'In-Video Question' },
      { key: 'summary', label: 'Summary' },
      { key: 'cta', label: 'Call to Action' }
    ];

    for (const section of sections) {
      const sectionData = content[section.key];
      if (sectionData) {
        // Handle both object (VideoScriptSection) and string formats
        const scriptText = typeof sectionData === 'object' ? sectionData.script_text : sectionData;
        const sectionTitle = typeof sectionData === 'object' && sectionData.title ? sectionData.title : section.label;
        const speakerNotes = typeof sectionData === 'object' ? sectionData.speaker_notes : null;

        html += `
          <div class="video-section">
            <div class="video-section-header">${this.escapeHtml(sectionTitle)}</div>
            <div class="video-section-content" contenteditable="false" data-section="${section.key}">
              ${this.escapeHtml(scriptText || '')}
            </div>
            ${speakerNotes ? `<div class="speaker-notes" style="margin-top: 0.5rem; padding: 0.5rem; background: var(--surface-alt); border-radius: 4px; font-size: 0.85rem; color: var(--text-secondary);"><strong>Speaker Notes:</strong> ${this.escapeHtml(speakerNotes)}</div>` : ''}
          </div>
        `;
      }
    }

    // Handle content sections array if present (alternative format)
    if (content.sections && Array.isArray(content.sections)) {
      for (const section of content.sections) {
        const scriptText = section.script_text || section.content || section.text || '';
        html += `
          <div class="video-section">
            <div class="video-section-header">${this.escapeHtml(section.title || 'Section')}</div>
            <div class="video-section-content" contenteditable="false" data-section="sections">
              ${this.escapeHtml(scriptText)}
            </div>
            ${section.speaker_notes ? `<div class="speaker-notes" style="margin-top: 0.5rem; padding: 0.5rem; background: var(--surface-alt); border-radius: 4px; font-size: 0.85rem; color: var(--text-secondary);"><strong>Speaker Notes:</strong> ${this.escapeHtml(section.speaker_notes)}</div>` : ''}
          </div>
        `;
      }
    }

    return html || '<p class="text-muted">No video script content.</p>';
  }

  /**
   * Render reading content
   */
  renderReading(content) {
    let html = '';

    if (content.title) {
      html += `<h2 class="reading-title" style="margin-bottom: 1.5rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.introduction) {
      html += `<div class="reading-section" style="margin-bottom: 1.5rem;"><p style="line-height: 1.6;">${this.escapeHtml(content.introduction)}</p></div>`;
    }

    if (content.sections && Array.isArray(content.sections)) {
      for (const section of content.sections) {
        // Handle both {heading, body} and {title, content/text} formats
        const heading = section.heading || section.title || '';
        const body = section.body || section.content || section.text || '';
        html += `
          <div class="reading-section" style="margin-bottom: 1.5rem;">
            <h3 class="reading-section-title" style="color: var(--text-primary); margin-bottom: 0.75rem;">${this.escapeHtml(heading)}</h3>
            <div contenteditable="false" data-section="sections" style="line-height: 1.6;">
              ${this.escapeHtml(body)}
            </div>
          </div>
        `;
      }
    }

    if (content.conclusion) {
      html += `<div class="reading-section" style="margin-bottom: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border);"><h3 style="color: var(--text-primary); margin-bottom: 0.75rem;">Conclusion</h3><p style="line-height: 1.6;">${this.escapeHtml(content.conclusion)}</p></div>`;
    }

    if (content.references && Array.isArray(content.references) && content.references.length > 0) {
      html += `
        <div class="reading-references" style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border);">
          <h4 style="margin-bottom: 0.75rem;">References</h4>
          <ul style="list-style: none; padding: 0;">
            ${content.references.map(ref => {
              // Handle both {citation, url} object and string formats
              const citation = typeof ref === 'object' ? (ref.citation || ref.title || '') : ref;
              const url = typeof ref === 'object' ? ref.url : null;
              return `<li style="margin-bottom: 0.5rem; font-size: 0.9rem; color: var(--text-secondary);">${this.escapeHtml(citation)}${url ? ` <a href="${this.escapeHtml(url)}" target="_blank" style="color: var(--accent);">[Link]</a>` : ''}</li>`;
            }).join('')}
          </ul>
        </div>
      `;
    }

    return html || '<p class="text-muted">No reading content.</p>';
  }

  /**
   * Render quiz content
   * Author mode: shows answers and feedback
   * Learner mode: interactive quiz with feedback shown after selection
   */
  renderQuiz(content) {
    // Use learner mode rendering if in learner preview
    if (this.previewMode === 'learner') {
      return this.renderQuizLearner(content);
    }
    return this.renderQuizAuthor(content);
  }

  /**
   * Render quiz for author view (shows all answers and feedback)
   */
  renderQuizAuthor(content) {
    let html = '';

    if (content.title) {
      html += `<h2 class="quiz-title" style="margin-bottom: 1.5rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.passing_score_percentage) {
      html += `<p style="margin-bottom: 1.5rem; color: var(--text-secondary);">Passing Score: ${content.passing_score_percentage}%</p>`;
    }

    const questions = content.questions || [];

    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      const questionText = q.question_text || q.question || q.text || '';

      html += `
        <div class="quiz-question" style="margin-bottom: 1.5rem; padding: 1rem; background: var(--surface-alt); border-radius: 8px;">
          <div class="quiz-question-text" style="font-weight: 500; margin-bottom: 0.75rem;">${i + 1}. ${this.escapeHtml(questionText)}</div>
          ${q.bloom_level ? `<span style="font-size: 0.75rem; padding: 2px 8px; background: var(--accent); color: white; border-radius: 4px; margin-bottom: 0.5rem; display: inline-block;">${this.escapeHtml(q.bloom_level)}</span>` : ''}
          <ul class="quiz-options" style="list-style: none; padding: 0; margin-top: 0.75rem;">
      `;

      const options = q.options || q.choices || [];

      for (let j = 0; j < options.length; j++) {
        const option = options[j];
        const optionText = typeof option === 'object' ? option.text : option;
        const isCorrect = typeof option === 'object' ? option.is_correct : (j === q.correct_answer || j === q.correct_index);
        const feedback = typeof option === 'object' ? option.feedback : null;

        html += `
          <li class="quiz-option" style="padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; background: ${isCorrect ? 'rgba(46, 204, 113, 0.1)' : 'var(--surface)'}; border: 1px solid ${isCorrect ? 'var(--success)' : 'var(--border)'}; border-radius: 4px; display: flex; align-items: flex-start; gap: 0.5rem;">
            <span class="quiz-option-marker" style="font-weight: 500; min-width: 1.5rem;">${String.fromCharCode(65 + j)}.</span>
            <div style="flex: 1;">
              <span>${this.escapeHtml(optionText)}</span>
              ${isCorrect ? '<span style="margin-left: 0.5rem; color: var(--success); font-size: 0.85rem;">✓ Correct</span>' : ''}
              ${feedback ? `<div style="margin-top: 0.25rem; font-size: 0.85rem; color: var(--text-secondary);"><em>Feedback: ${this.escapeHtml(feedback)}</em></div>` : ''}
            </div>
          </li>
        `;
      }

      html += `</ul>`;

      if (q.explanation) {
        html += `<div style="margin-top: 0.75rem; padding: 0.75rem; background: rgba(52, 152, 219, 0.1); border-radius: 4px; font-size: 0.9rem;"><strong>Explanation:</strong> ${this.escapeHtml(q.explanation)}</div>`;
      }

      html += `</div>`;
    }

    return html || '<p class="text-muted">No quiz content.</p>';
  }

  /**
   * Render quiz for learner view (interactive with hidden feedback)
   */
  renderQuizLearner(content) {
    let html = '';

    if (content.title) {
      html += `<h2 class="quiz-title" style="margin-bottom: 1.5rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.passing_score_percentage) {
      html += `<p style="margin-bottom: 1.5rem; color: var(--text-secondary);">Passing Score: ${content.passing_score_percentage}%</p>`;
    }

    const questions = content.questions || [];

    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      const questionText = q.question_text || q.question || q.text || '';
      const explanation = q.explanation || '';

      html += `
        <div class="quiz-question-learner" data-question="${i}" style="margin-bottom: 1.5rem; padding: 1rem; background: var(--surface-alt); border-radius: 8px;">
          <div class="quiz-question-text" style="font-weight: 500; margin-bottom: 0.75rem;">${i + 1}. ${this.escapeHtml(questionText)}</div>
          <div class="quiz-options-learner" style="margin-top: 0.75rem;">
      `;

      const options = q.options || q.choices || [];

      for (let j = 0; j < options.length; j++) {
        const option = options[j];
        const optionText = typeof option === 'object' ? option.text : option;
        const isCorrect = typeof option === 'object' ? option.is_correct : (j === q.correct_answer || j === q.correct_index);
        const feedback = typeof option === 'object' ? (option.feedback || '') : '';
        const letter = String.fromCharCode(65 + j);

        html += `
          <div class="quiz-option-learner" data-correct="${isCorrect}" data-feedback="${this.escapeHtml(feedback)}"
               style="padding: 0.75rem; margin-bottom: 0.5rem; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; transition: all 0.2s;"
               onclick="window.studioController.handleQuizOptionClick(this, ${i}, ${isCorrect})">
            <span style="font-weight: 500; margin-right: 0.5rem;">${letter}.</span>
            <span>${this.escapeHtml(optionText)}</span>
            <div class="option-feedback-learner" style="display: none; margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; font-size: 0.9rem;"></div>
          </div>
        `;
      }

      html += `</div>`;

      // Hidden explanation (shown after answering)
      if (explanation) {
        html += `<div class="question-explanation-learner" style="display: none; margin-top: 0.75rem; padding: 0.75rem; background: rgba(52, 152, 219, 0.1); border-radius: 4px; font-size: 0.9rem;"><strong>Explanation:</strong> ${this.escapeHtml(explanation)}</div>`;
      }

      html += `</div>`;
    }

    return html || '<p class="text-muted">No quiz content.</p>';
  }

  /**
   * Handle quiz option click in learner mode
   */
  handleQuizOptionClick(optionEl, questionIndex, isCorrect) {
    const questionDiv = optionEl.closest('.quiz-question-learner');
    if (questionDiv.dataset.answered === 'true') return; // Already answered

    questionDiv.dataset.answered = 'true';
    const options = questionDiv.querySelectorAll('.quiz-option-learner');

    // Disable all options
    options.forEach(opt => {
      opt.style.cursor = 'default';
      opt.onclick = null;
    });

    // Show feedback for selected option
    const feedback = optionEl.dataset.feedback;
    const feedbackDiv = optionEl.querySelector('.option-feedback-learner');

    if (isCorrect) {
      optionEl.style.background = 'rgba(46, 204, 113, 0.15)';
      optionEl.style.borderColor = 'var(--success)';
      feedbackDiv.style.background = 'rgba(46, 204, 113, 0.1)';
      feedbackDiv.innerHTML = `<span style="color: var(--success);">✓ Correct!</span> ${feedback}`;
    } else {
      optionEl.style.background = 'rgba(231, 76, 60, 0.15)';
      optionEl.style.borderColor = 'var(--error)';
      feedbackDiv.style.background = 'rgba(231, 76, 60, 0.1)';
      feedbackDiv.innerHTML = `<span style="color: var(--error);">✗ Incorrect.</span> ${feedback}`;

      // Highlight correct answer
      options.forEach(opt => {
        if (opt.dataset.correct === 'true') {
          opt.style.background = 'rgba(46, 204, 113, 0.15)';
          opt.style.borderColor = 'var(--success)';
          const correctFeedback = opt.querySelector('.option-feedback-learner');
          correctFeedback.style.background = 'rgba(46, 204, 113, 0.1)';
          correctFeedback.innerHTML = `<span style="color: var(--success);">✓ This was the correct answer.</span> ${opt.dataset.feedback}`;
          correctFeedback.style.display = 'block';
        }
      });
    }

    feedbackDiv.style.display = 'block';

    // Show explanation
    const explanation = questionDiv.querySelector('.question-explanation-learner');
    if (explanation) {
      explanation.style.display = 'block';
    }
  }

  /**
   * Render generic content as formatted JSON
   */
  renderGenericContent(content) {
    return `<pre style="white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono); font-size: 14px;">${this.escapeHtml(JSON.stringify(content, null, 2))}</pre>`;
  }

  /**
   * Render Hands-on Lab content
   */
  renderHOL(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.scenario) {
      html += `<div style="margin-bottom: 1.5rem; padding: 1rem; background: rgba(52, 152, 219, 0.1); border-radius: 8px;"><strong>Scenario:</strong> ${this.escapeHtml(content.scenario)}</div>`;
    }

    if (content.parts && Array.isArray(content.parts)) {
      html += '<h3 style="margin-bottom: 1rem;">Parts</h3>';
      for (const part of content.parts) {
        html += `
          <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--surface-alt); border-radius: 8px;">
            <h4 style="margin-bottom: 0.5rem;">Part ${part.part_number}: ${this.escapeHtml(part.title)}</h4>
            <p style="margin-bottom: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">⏱ ${part.estimated_minutes} minutes</p>
            <div style="white-space: pre-wrap;">${this.escapeHtml(part.instructions)}</div>
          </div>
        `;
      }
    }

    if (content.submission_criteria) {
      html += `<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Submission Criteria</h3><p>${this.escapeHtml(content.submission_criteria)}</p></div>`;
    }

    if (content.rubric && Array.isArray(content.rubric)) {
      html += '<h3 style="margin-bottom: 1rem;">Rubric</h3>';
      html += '<table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">';
      html += '<tr style="background: var(--surface-alt);"><th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid var(--border);">Criterion</th><th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid var(--border);">Advanced</th><th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid var(--border);">Intermediate</th><th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid var(--border);">Beginner</th></tr>';
      for (const criterion of content.rubric) {
        html += `<tr><td style="padding: 0.5rem; border-bottom: 1px solid var(--border); font-weight: 500;">${this.escapeHtml(criterion.name)}</td><td style="padding: 0.5rem; border-bottom: 1px solid var(--border);">${this.escapeHtml(criterion.advanced)} (${criterion.points_advanced || 5}pts)</td><td style="padding: 0.5rem; border-bottom: 1px solid var(--border);">${this.escapeHtml(criterion.intermediate)} (${criterion.points_intermediate || 4}pts)</td><td style="padding: 0.5rem; border-bottom: 1px solid var(--border);">${this.escapeHtml(criterion.beginner)} (${criterion.points_beginner || 2}pts)</td></tr>`;
      }
      html += '</table>';
    }

    return html || '<p class="text-muted">No HOL content.</p>';
  }

  /**
   * Render Coach Dialogue content
   */
  renderCoach(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.learning_objectives && Array.isArray(content.learning_objectives)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Learning Objectives</h3><ul style="padding-left: 1.5rem;">';
      for (const obj of content.learning_objectives) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(obj)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.scenario) {
      html += `<div style="margin-bottom: 1.5rem; padding: 1rem; background: rgba(52, 152, 219, 0.1); border-radius: 8px;"><strong>Scenario:</strong> ${this.escapeHtml(content.scenario)}</div>`;
    }

    if (content.tasks && Array.isArray(content.tasks)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Tasks</h3><ol style="padding-left: 1.5rem;">';
      for (const task of content.tasks) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(task)}</li>`;
      }
      html += '</ol></div>';
    }

    if (content.conversation_starters && Array.isArray(content.conversation_starters)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Conversation Starters</h3>';
      for (const starter of content.conversation_starters) {
        html += `<div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--surface-alt); border-radius: 8px;"><p style="font-weight: 500;">"${this.escapeHtml(starter.starter_text)}"</p><p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;"><em>Purpose: ${this.escapeHtml(starter.purpose)}</em></p></div>`;
      }
      html += '</div>';
    }

    if (content.sample_responses && Array.isArray(content.sample_responses)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Sample Responses</h3>';
      const levelColors = { exceeds: 'var(--success)', meets: 'var(--accent)', needs_improvement: 'var(--warning)' };
      for (const response of content.sample_responses) {
        const color = levelColors[response.evaluation_level] || 'var(--text-secondary)';
        html += `<div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--surface-alt); border-radius: 8px; border-left: 3px solid ${color};"><span style="font-size: 0.75rem; padding: 2px 8px; background: ${color}; color: white; border-radius: 4px;">${this.escapeHtml(response.evaluation_level.replace('_', ' '))}</span><p style="margin-top: 0.5rem;">"${this.escapeHtml(response.response_text)}"</p><p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;"><strong>Feedback:</strong> ${this.escapeHtml(response.feedback)}</p></div>`;
      }
      html += '</div>';
    }

    if (content.evaluation_criteria && Array.isArray(content.evaluation_criteria)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Evaluation Criteria</h3><ul style="padding-left: 1.5rem;">';
      for (const criteria of content.evaluation_criteria) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(criteria)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.wrap_up) {
      html += `<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Wrap-Up</h3><p>${this.escapeHtml(content.wrap_up)}</p></div>`;
    }

    if (content.reflection_prompts && Array.isArray(content.reflection_prompts)) {
      html += '<div style="margin-bottom: 1rem;"><h3 style="margin-bottom: 0.5rem;">Reflection Prompts</h3><ul style="padding-left: 1.5rem;">';
      for (const prompt of content.reflection_prompts) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(prompt)}</li>`;
      }
      html += '</ul></div>';
    }

    return html || '<p class="text-muted">No coach dialogue content.</p>';
  }

  /**
   * Render Discussion content
   */
  renderDiscussion(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.main_prompt) {
      html += `<div style="margin-bottom: 1.5rem; padding: 1.5rem; background: var(--surface-alt); border-radius: 8px; border-left: 4px solid var(--accent);"><h3 style="margin-bottom: 0.5rem;">Discussion Prompt</h3><p style="font-size: 1.1rem; line-height: 1.6;">${this.escapeHtml(content.main_prompt)}</p></div>`;
    }

    if (content.facilitation_questions && Array.isArray(content.facilitation_questions)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Facilitation Questions</h3><ul style="padding-left: 1.5rem;">';
      for (const q of content.facilitation_questions) {
        html += `<li style="margin-bottom: 0.5rem;">${this.escapeHtml(q)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.engagement_hooks && Array.isArray(content.engagement_hooks)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Engagement Hooks</h3>';
      for (const hook of content.engagement_hooks) {
        html += `<div style="margin-bottom: 0.5rem; padding: 0.75rem; background: rgba(46, 204, 113, 0.1); border-radius: 4px;">💡 ${this.escapeHtml(hook)}</div>`;
      }
      html += '</div>';
    }

    if (content.connection_to_objective) {
      html += `<div style="margin-bottom: 1rem; padding: 0.75rem; background: rgba(52, 152, 219, 0.1); border-radius: 8px;"><strong>Connection to Learning Objective:</strong> ${this.escapeHtml(content.connection_to_objective)}</div>`;
    }

    return html || '<p class="text-muted">No discussion content.</p>';
  }

  /**
   * Render Lab content
   */
  renderLab(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.overview) {
      html += `<p style="margin-bottom: 1.5rem; font-size: 1.05rem; line-height: 1.6;">${this.escapeHtml(content.overview)}</p>`;
    }

    if (content.estimated_minutes) {
      html += `<p style="margin-bottom: 1rem; color: var(--text-secondary);">⏱ Estimated time: ${content.estimated_minutes} minutes</p>`;
    }

    if (content.prerequisites && Array.isArray(content.prerequisites) && content.prerequisites.length > 0) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Prerequisites</h3><ul style="padding-left: 1.5rem;">';
      for (const prereq of content.prerequisites) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(prereq)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.learning_objectives && Array.isArray(content.learning_objectives)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Learning Objectives</h3><ul style="padding-left: 1.5rem;">';
      for (const obj of content.learning_objectives) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(obj)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.setup_instructions && Array.isArray(content.setup_instructions)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Setup Instructions</h3>';
      for (const step of content.setup_instructions) {
        html += `<div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--surface-alt); border-radius: 8px;"><strong>Step ${step.step_number}:</strong> ${this.escapeHtml(step.instruction)}<p style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--success);"><em>Expected: ${this.escapeHtml(step.expected_result)}</em></p></div>`;
      }
      html += '</div>';
    }

    if (content.lab_exercises && Array.isArray(content.lab_exercises)) {
      html += '<div style="margin-bottom: 1rem;"><h3 style="margin-bottom: 0.5rem;">Exercises</h3><ol style="padding-left: 1.5rem;">';
      for (const exercise of content.lab_exercises) {
        html += `<li style="margin-bottom: 0.5rem;">${this.escapeHtml(exercise)}</li>`;
      }
      html += '</ol></div>';
    }

    return html || '<p class="text-muted">No lab content.</p>';
  }

  /**
   * Render Assignment content
   */
  renderAssignment(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.overview) {
      html += `<p style="margin-bottom: 1.5rem; font-size: 1.05rem; line-height: 1.6;">${this.escapeHtml(content.overview)}</p>`;
    }

    if (content.total_points || content.estimated_hours) {
      html += '<div style="margin-bottom: 1.5rem; display: flex; gap: 1.5rem;">';
      if (content.total_points) html += `<span style="color: var(--text-secondary);">📊 Total Points: <strong>${content.total_points}</strong></span>`;
      if (content.estimated_hours) html += `<span style="color: var(--text-secondary);">⏱ Estimated: <strong>${content.estimated_hours} hours</strong></span>`;
      html += '</div>';
    }

    if (content.deliverables && Array.isArray(content.deliverables)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Deliverables</h3>';
      for (const d of content.deliverables) {
        html += `<div style="margin-bottom: 0.5rem; padding: 0.75rem; background: var(--surface-alt); border-radius: 8px; display: flex; justify-content: space-between; align-items: center;"><span>${this.escapeHtml(d.item)}</span><span style="font-weight: 500; color: var(--accent);">${d.points} pts</span></div>`;
      }
      html += '</div>';
    }

    if (content.grading_criteria && Array.isArray(content.grading_criteria)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Grading Criteria</h3><ul style="padding-left: 1.5rem;">';
      for (const criteria of content.grading_criteria) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(criteria)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.submission_checklist && Array.isArray(content.submission_checklist)) {
      html += '<div style="margin-bottom: 1rem;"><h3 style="margin-bottom: 0.5rem;">Submission Checklist</h3>';
      for (const item of content.submission_checklist) {
        const icon = item.required ? '☑️' : '◻️';
        const label = item.required ? '' : ' <span style="font-size: 0.75rem; color: var(--text-secondary);">(optional)</span>';
        html += `<div style="margin-bottom: 0.25rem;">${icon} ${this.escapeHtml(item.item)}${label}</div>`;
      }
      html += '</div>';
    }

    return html || '<p class="text-muted">No assignment content.</p>';
  }

  /**
   * Render Project content
   */
  renderProject(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    // Project schemas vary - render what we find
    if (content.overview || content.description) {
      html += `<p style="margin-bottom: 1.5rem; font-size: 1.05rem; line-height: 1.6;">${this.escapeHtml(content.overview || content.description)}</p>`;
    }

    if (content.milestones && Array.isArray(content.milestones)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Milestones</h3>';
      for (let i = 0; i < content.milestones.length; i++) {
        const m = content.milestones[i];
        const title = typeof m === 'string' ? m : (m.title || m.name || `Milestone ${i + 1}`);
        const desc = typeof m === 'object' ? (m.description || m.deliverables || '') : '';
        html += `<div style="margin-bottom: 0.75rem; padding: 0.75rem; background: var(--surface-alt); border-radius: 8px; border-left: 3px solid var(--accent);"><strong>Milestone ${i + 1}:</strong> ${this.escapeHtml(title)}${desc ? `<p style="margin-top: 0.25rem; font-size: 0.9rem; color: var(--text-secondary);">${this.escapeHtml(desc)}</p>` : ''}</div>`;
      }
      html += '</div>';
    }

    if (content.learning_objectives && Array.isArray(content.learning_objectives)) {
      html += '<div style="margin-bottom: 1.5rem;"><h3 style="margin-bottom: 0.5rem;">Learning Objectives</h3><ul style="padding-left: 1.5rem;">';
      for (const obj of content.learning_objectives) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(obj)}</li>`;
      }
      html += '</ul></div>';
    }

    if (content.grading_criteria && Array.isArray(content.grading_criteria)) {
      html += '<div style="margin-bottom: 1rem;"><h3 style="margin-bottom: 0.5rem;">Grading Criteria</h3><ul style="padding-left: 1.5rem;">';
      for (const criteria of content.grading_criteria) {
        html += `<li style="margin-bottom: 0.25rem;">${this.escapeHtml(criteria)}</li>`;
      }
      html += '</ul></div>';
    }

    // Fallback to generic rendering if no recognized fields
    if (!html) {
      return this.renderGenericContent(content);
    }

    return html;
  }

  /**
   * Escape HTML special characters
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Update metadata footer
   */
  updateMetadata(activity) {
    document.getElementById('meta-word-count').textContent = activity.word_count || 0;
    document.getElementById('meta-duration').textContent = `${(activity.estimated_duration_minutes || 0).toFixed(1)} min`;
    document.getElementById('meta-bloom').textContent = activity.bloom_level ? activity.bloom_level.charAt(0).toUpperCase() + activity.bloom_level.slice(1) : '-';

    // Show WPM indicator for video content
    const wpmItem = document.getElementById('meta-wpm-item');
    const wpmValue = document.getElementById('meta-wpm');
    if (wpmItem && wpmValue) {
      const contentType = activity.content_type;
      const isVideo = contentType === 'video_script' || contentType === 'video' ||
                      contentType?.value === 'video_script' || contentType?.value === 'video';
      if (isVideo) {
        // Calculate WPM from word count and duration, or use default
        const wordCount = activity.word_count || 0;
        const duration = activity.estimated_duration_minutes || 0;
        const calculatedWpm = duration > 0 ? Math.round(wordCount / duration) : 120;
        wpmValue.textContent = calculatedWpm;
        wpmItem.style.display = 'inline';
      } else {
        wpmItem.style.display = 'none';
      }
    }
  }

  // ===========================
  // Variant Methods
  // ===========================

  /**
   * Load available variants for current activity
   */
  async loadVariants() {
    if (!this.selectedActivity) {
      this.availableVariants = [];
      return;
    }

    try {
      const response = await api.get(
        `/courses/${this.courseId}/activities/${this.selectedActivity.id}/variants`
      );
      this.availableVariants = response.variants || [];
      this.renderVariantTabs();
    } catch (error) {
      console.warn('Failed to load variants:', error);
      this.availableVariants = [];
    }
  }

  /**
   * Render variant tabs based on available variants
   */
  renderVariantTabs() {
    const variantTabs = document.getElementById('variant-tabs');
    const variantSelector = document.getElementById('variant-selector');
    const depthPills = document.getElementById('depth-pills');

    if (!variantTabs || !this.selectedActivity) {
      if (variantSelector) variantSelector.style.display = 'none';
      return;
    }

    // Only show variant selector if activity has content
    const hasContent = this.selectedActivity.content &&
                       this.selectedActivity.build_state !== 'draft';
    if (!hasContent) {
      variantSelector.style.display = 'none';
      return;
    }

    variantSelector.style.display = 'flex';

    // Group variants by type
    const variantsByType = {};
    for (const v of this.availableVariants) {
      if (!variantsByType[v.variant_type]) {
        variantsByType[v.variant_type] = [];
      }
      variantsByType[v.variant_type].push(v);
    }

    // Build tabs HTML
    let html = '';
    const types = ['primary', ...Object.keys(variantsByType).filter(t => t !== 'primary')];

    for (const type of types) {
      const variants = variantsByType[type] || [];
      const hasGenerated = variants.some(v => v.generated);
      const isActive = type === this.selectedVariant.type;
      const label = this.formatVariantType(type);

      html += `
        <button class="variant-tab${isActive ? ' active' : ''}"
                data-variant="${type}"
                data-depth="${this.selectedVariant.depth}">
          ${label}
          ${hasGenerated ? '<span class="variant-badge generated">&#10003;</span>' : ''}
        </button>
      `;
    }

    variantTabs.innerHTML = html;

    // Update depth pills availability
    if (depthPills) {
      const currentTypeVariants = variantsByType[this.selectedVariant.type] || [];
      depthPills.style.display = 'flex';

      depthPills.querySelectorAll('.depth-pill').forEach(pill => {
        const depth = pill.dataset.depth;
        const variant = currentTypeVariants.find(v => v.depth_level === depth);
        const isAvailable = depth === 'standard' || (variant && variant.generated);
        const isActive = depth === this.selectedVariant.depth;

        pill.classList.toggle('active', isActive);
        pill.classList.toggle('unavailable', !isAvailable && depth !== 'standard');
      });
    }
  }

  /**
   * Format variant type for display
   */
  formatVariantType(type) {
    const typeMap = {
      'primary': 'Primary',
      'transcript': 'Transcript',
      'audio_only': 'Audio',
      'illustrated': 'Illustrated',
      'infographic': 'Infographic',
      'guided': 'Guided',
      'challenge': 'Challenge',
      'self_check': 'Self-Check'
    };
    return typeMap[type] || type;
  }

  /**
   * Handle variant selection
   */
  async handleVariantSelect(variantType, depthLevel) {
    this.selectedVariant = { type: variantType, depth: depthLevel };

    // Update tab UI
    document.querySelectorAll('.variant-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.variant === variantType);
    });

    // Update depth pills UI
    document.querySelectorAll('.depth-pill').forEach(pill => {
      pill.classList.toggle('active', pill.dataset.depth === depthLevel);
    });

    // Re-render content with selected variant
    await this.renderVariantContent();
  }

  /**
   * Render content for selected variant
   */
  async renderVariantContent() {
    const previewContent = document.getElementById('preview-content');

    if (!this.selectedActivity) return;

    // For primary/standard, use main activity content
    if (this.selectedVariant.type === 'primary' && this.selectedVariant.depth === 'standard') {
      this.renderContent(this.selectedActivity);
      this.updateMetadata(this.selectedActivity);
      return;
    }

    // Find variant in available variants
    const variant = this.availableVariants.find(
      v => v.variant_type === this.selectedVariant.type &&
           v.depth_level === this.selectedVariant.depth
    );

    if (!variant || !variant.generated) {
      previewContent.innerHTML = `
        <div class="preview-empty" style="height: auto; padding: 2rem;">
          <p>This variant has not been generated yet.</p>
          <button class="btn btn-primary" onclick="window.studioController.openVariantModal()">
            Generate Variant
          </button>
        </div>
      `;
      return;
    }

    // Fetch full variant content
    try {
      const response = await api.get(
        `/courses/${this.courseId}/activities/${this.selectedActivity.id}/variants/${this.selectedVariant.type}?depth=${this.selectedVariant.depth}`
      );

      // Render variant content
      this.renderVariantContentData(response);

      // Update metadata with variant info
      document.getElementById('meta-word-count').textContent = response.word_count || 0;
      document.getElementById('meta-duration').textContent =
        `${(response.estimated_duration_minutes || 0).toFixed(1)} min`;
    } catch (error) {
      toast.error(`Failed to load variant: ${error.message}`);
    }
  }

  /**
   * Render variant content based on type
   */
  renderVariantContentData(variant) {
    const previewContent = document.getElementById('preview-content');

    let content = variant.content;
    if (typeof content === 'string') {
      try {
        content = JSON.parse(content);
      } catch (e) {
        // Plain text
        previewContent.innerHTML = `<div class="content-section"><div class="content-section-body">${this.escapeHtml(content)}</div></div>`;
        return;
      }
    }

    // Render based on variant type
    if (variant.variant_type === 'transcript') {
      previewContent.innerHTML = this.renderTranscript(content);
    } else {
      previewContent.innerHTML = this.renderGenericContent(content);
    }
  }

  /**
   * Render transcript variant
   */
  renderTranscript(content) {
    let html = '';

    if (content.title) {
      html += `<h2 style="margin-bottom: 1.5rem; color: var(--accent);">${this.escapeHtml(content.title)}</h2>`;
    }

    if (content.learning_objective) {
      html += `<div class="learning-objective" style="padding: 1rem; background: var(--info-bg); border-radius: var(--radius-md); margin-bottom: 1.5rem;">
        <strong>Learning Objective:</strong> ${this.escapeHtml(content.learning_objective)}
      </div>`;
    }

    if (content.content) {
      // Convert markdown-ish content to HTML
      const formatted = content.content
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/^## (.+)$/gm, '<h2 style="margin-top: 1.5rem; color: var(--accent-light);">$1</h2>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
      html += `<div class="transcript-content"><p>${formatted}</p></div>`;
    }

    return html || '<p class="text-muted">No transcript content.</p>';
  }

  /**
   * Open variant generation modal
   */
  openVariantModal() {
    if (!this.selectedActivity) {
      toast.error('Please select an activity first');
      return;
    }

    if (!this.selectedActivity.content || this.selectedActivity.build_state === 'draft') {
      toast.error('Generate primary content first before creating variants');
      return;
    }

    // Update available options based on content type
    const variantTypeSelect = document.getElementById('variant-type-select');
    const contentType = this.selectedActivity.content_type?.value || this.selectedActivity.content_type;

    // Set available variant types based on content type
    let options = '<option value="transcript">Transcript (text version)</option>';
    if (contentType === 'video') {
      options = `
        <option value="transcript">Transcript (text version)</option>
        <option value="audio_only">Audio Narration Script</option>
      `;
    } else if (contentType === 'reading') {
      options = `
        <option value="audio_only">Audio Narration Script</option>
      `;
    }
    variantTypeSelect.innerHTML = options;

    this.variantModal.open();
  }

  /**
   * Handle generate variant button click
   */
  async handleGenerateVariant() {
    const variantType = document.getElementById('variant-type-select').value;
    const depthLevel = document.getElementById('depth-level-select').value;

    const btnGenerate = document.getElementById('btn-generate-variant');
    btnGenerate.disabled = true;
    btnGenerate.textContent = 'Generating...';

    try {
      const response = await api.post(
        `/courses/${this.courseId}/activities/${this.selectedActivity.id}/variants/generate`,
        { variant_type: variantType, depth_level: depthLevel }
      );

      toast.success('Variant generated successfully');
      this.variantModal.close();

      // Reload variants and select the new one
      await this.loadVariants();
      this.handleVariantSelect(variantType, depthLevel);
    } catch (error) {
      toast.error(`Failed to generate variant: ${error.message}`);
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.textContent = 'Generate Variant';
    }
  }

  // ===========================
  // End Variant Methods
  // ===========================

  /**
   * Update controls based on activity state
   */
  updateControls() {
    const btnGenerate = document.getElementById('btn-generate');
    const sectionEdit = document.getElementById('section-edit');
    const sectionRegenerate = document.getElementById('section-regenerate');
    const sectionState = document.getElementById('section-state');
    const sectionHumanize = document.getElementById('section-humanize');

    if (!this.selectedActivity) {
      btnGenerate.disabled = true;
      sectionEdit.style.display = 'none';
      sectionRegenerate.style.display = 'none';
      sectionState.style.display = 'none';
      if (sectionHumanize) sectionHumanize.style.display = 'none';
      return;
    }

    const buildState = this.selectedActivity.build_state || 'draft';

    // Generate button
    btnGenerate.disabled = buildState === 'generating';

    // Edit section - show if has content
    if (this.selectedActivity.content && buildState !== 'generating') {
      sectionEdit.style.display = 'block';
    } else {
      sectionEdit.style.display = 'none';
    }

    // Video Studio button - show only for video content
    const btnVideoStudio = document.getElementById('btn-video-studio');
    if (btnVideoStudio) {
      const contentType = this.selectedActivity.content_type;
      const isVideo = contentType === 'video' || contentType?.value === 'video';
      if (isVideo && this.selectedActivity.content && buildState !== 'generating') {
        btnVideoStudio.style.display = 'block';
      } else {
        btnVideoStudio.style.display = 'none';
      }
    }

    // Humanization section - show if has content
    if (sectionHumanize) {
      if (this.selectedActivity.content && buildState !== 'generating') {
        sectionHumanize.style.display = 'block';
        // Fetch humanization score
        this.fetchHumanizationScore();
      } else {
        sectionHumanize.style.display = 'none';
      }
    }

    // Regenerate section - show if generated or reviewed
    if (buildState === 'generated' || buildState === 'reviewed') {
      sectionRegenerate.style.display = 'block';
      // Show appropriate length controls based on content type
      this.updateLengthControls();
    } else {
      sectionRegenerate.style.display = 'none';
    }

    // State transitions - show if generated or reviewed
    if (buildState === 'generated' || buildState === 'reviewed') {
      sectionState.style.display = 'block';
    } else {
      sectionState.style.display = 'none';
    }
  }

  /**
   * Show/hide length controls based on content type and pre-fill with current values
   */
  updateLengthControls() {
    const textControls = document.getElementById('length-controls-text');
    const videoControls = document.getElementById('length-controls-video');

    if (!textControls || !videoControls || !this.selectedActivity) return;

    const contentType = this.selectedActivity.content_type;
    const isVideo = contentType === 'video_script' || contentType === 'video' ||
                    contentType?.value === 'video_script' || contentType?.value === 'video';

    // Reset inputs when switching activities
    const durationInput = document.getElementById('target-duration');
    const wpmInput = document.getElementById('speaking-wpm');
    const wordCountInput = document.getElementById('target-word-count');

    if (isVideo) {
      textControls.style.display = 'none';
      videoControls.style.display = 'block';

      // Pre-fill with current duration
      const currentDuration = this.selectedActivity.estimated_duration_minutes;
      if (durationInput) {
        durationInput.value = currentDuration ? Math.round(currentDuration * 10) / 10 : '';
      }

      // Calculate and set WPM based on actual content, or use default
      if (wpmInput) {
        const wordCount = this.selectedActivity.word_count || 0;
        const duration = this.selectedActivity.estimated_duration_minutes || 0;
        if (wordCount > 0 && duration > 0) {
          const calculatedWpm = Math.round(wordCount / duration);
          // Round to nearest 10 for cleaner display
          wpmInput.value = Math.round(calculatedWpm / 10) * 10;
        } else {
          wpmInput.value = 120; // Default
        }
      }

      this.updateWordCountCalculation();
    } else {
      textControls.style.display = 'block';
      videoControls.style.display = 'none';

      // Pre-fill word count input with current value
      const currentWordCount = this.selectedActivity.word_count;
      if (wordCountInput) {
        wordCountInput.value = ''; // Clear value so user can enter new target
        wordCountInput.placeholder = currentWordCount ? `Current: ${currentWordCount}` : 'e.g., 500';
      }
    }
  }

  /**
   * Update the calculated word count display for video
   */
  updateWordCountCalculation() {
    const durationInput = document.getElementById('target-duration');
    const wpmInput = document.getElementById('speaking-wpm');
    const calcDisplay = document.getElementById('calc-word-count');

    if (!durationInput || !wpmInput || !calcDisplay) return;

    const duration = parseFloat(durationInput.value) || 0;
    const wpm = parseInt(wpmInput.value) || 120;
    calcDisplay.textContent = Math.round(duration * wpm);
  }

  /**
   * Setup length calculation event listeners
   */
  setupLengthCalculation() {
    const durationInput = document.getElementById('target-duration');
    const wpmInput = document.getElementById('speaking-wpm');

    if (durationInput) {
      durationInput.addEventListener('input', () => this.updateWordCountCalculation());
    }
    if (wpmInput) {
      wpmInput.addEventListener('input', () => this.updateWordCountCalculation());
    }
  }

  /**
   * Handle generate button click
   */
  async handleGenerate() {
    if (!this.selectedActivityId) {
      toast.error('Please select an activity first');
      return;
    }

    // Close any existing SSE connection
    this.closeEventSource();

    // Show progress indicator
    const progressDiv = document.getElementById('generation-progress');
    const stageText = document.getElementById('stage-text');
    if (progressDiv) {
      progressDiv.style.display = 'block';
      stageText.textContent = 'Analyzing context...';
    }

    // Start elapsed timer
    this.elapsedTimer.reset();
    this.elapsedTimer.start();

    // Show streaming UI
    const previewEmpty = document.getElementById('preview-empty');
    const previewContent = document.getElementById('preview-content');
    const previewStreaming = document.getElementById('preview-streaming');
    const streamingOutput = document.getElementById('streaming-output');

    previewEmpty.style.display = 'none';
    previewContent.style.display = 'none';
    previewStreaming.style.display = 'flex';
    streamingOutput.innerHTML = '<span class="streaming-cursor"></span>';

    // Disable generate button
    const btnGenerate = document.getElementById('btn-generate');
    btnGenerate.disabled = true;

    // Update activity state in list
    const activityItem = document.querySelector(`.activity-item[data-activity-id="${this.selectedActivityId}"]`);
    if (activityItem) {
      const stateSpan = activityItem.querySelector('.activity-state');
      if (stateSpan) {
        stateSpan.className = 'activity-state state-generating';
        stateSpan.textContent = 'Generating';
      }
    }

    // Start SSE connection
    const url = `/api/courses/${this.courseId}/activities/${this.selectedActivityId}/generate/stream`;

    try {
      // Update stage indicator
      if (stageText) {
        setTimeout(() => { stageText.textContent = 'Generating content...'; }, 2000);
      }

      this.currentEventSource = new EventSource(url);

      this.currentEventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'heartbeat') {
          // Keep-alive message, just ignore (but connection stays open)
          return;
        } else if (data.type === 'chunk') {
          // Update stage to formatting once content starts arriving
          if (stageText && stageText.textContent === 'Generating content...') {
            stageText.textContent = 'Formatting output...';
          }

          // Show progress dots instead of raw JSON (which looks like gibberish)
          if (!this._chunkCount) this._chunkCount = 0;
          this._chunkCount++;
          const dots = '.'.repeat((this._chunkCount % 4) + 1);
          streamingOutput.innerHTML = `<div class="generating-message">Receiving content${dots}</div><span class="streaming-cursor"></span>`;
        } else if (data.type === 'complete') {
          // Generation complete
          this.closeEventSource();
          this.handleGenerationComplete(data.content);
        } else if (data.type === 'error') {
          this.closeEventSource();
          toast.error(`Generation failed: ${data.message}`);
          this.handleGenerationError();
        }
      };

      this.currentEventSource.onerror = (error) => {
        this.closeEventSource();
        toast.error('Connection lost during generation');
        this.handleGenerationError();
      };

    } catch (error) {
      toast.error(`Failed to start generation: ${error.message}`);
      this.handleGenerationError();
    }
  }

  /**
   * Handle generation complete
   */
  async handleGenerationComplete(content) {
    console.log('[DEBUG] handleGenerationComplete called with content:', content);

    // Stop elapsed timer
    this.elapsedTimer.stop();

    // Reset chunk counter
    this._chunkCount = 0;

    // Hide progress indicator
    const progressDiv = document.getElementById('generation-progress');
    if (progressDiv) {
      progressDiv.style.display = 'none';
    }

    // Hide streaming output immediately
    const previewStreaming = document.getElementById('preview-streaming');
    if (previewStreaming) {
      previewStreaming.style.display = 'none';
    }

    toast.success('Content generated successfully');

    // Reload course data to get updated activity
    console.log('[DEBUG] Loading course data...');
    await this.loadCourse();
    console.log('[DEBUG] Course loaded:', this.course ? 'yes' : 'no');

    // Update selected activity reference
    this.selectedActivity = this.findActivity(this.selectedActivityId);
    console.log('[DEBUG] Found activity:', this.selectedActivity ? 'yes' : 'no');
    console.log('[DEBUG] Activity content:', this.selectedActivity?.content ? 'has content' : 'NO CONTENT');
    console.log('[DEBUG] Activity build_state:', this.selectedActivity?.build_state);

    // Re-render preview
    await this.renderPreview();

    // Update controls
    this.updateControls();

    // Update activity state in list
    const activityItem = document.querySelector(`.activity-item[data-activity-id="${this.selectedActivityId}"]`);
    if (activityItem) {
      const stateSpan = activityItem.querySelector('.activity-state');
      if (stateSpan) {
        stateSpan.className = 'activity-state state-generated';
        stateSpan.textContent = 'Generated';
      }
    }
  }

  /**
   * Handle generation error
   */
  handleGenerationError() {
    // Stop elapsed timer
    this.elapsedTimer.stop();

    // Reset chunk counter
    this._chunkCount = 0;

    // Hide progress indicator
    const progressDiv = document.getElementById('generation-progress');
    if (progressDiv) {
      progressDiv.style.display = 'none';
    }

    // Hide streaming output
    const previewStreaming = document.getElementById('preview-streaming');
    if (previewStreaming) {
      previewStreaming.style.display = 'none';
    }

    // Re-enable generate button
    const btnGenerate = document.getElementById('btn-generate');
    btnGenerate.disabled = false;

    // Reset activity state in list
    const activityItem = document.querySelector(`.activity-item[data-activity-id="${this.selectedActivityId}"]`);
    if (activityItem) {
      const stateSpan = activityItem.querySelector('.activity-state');
      if (stateSpan) {
        stateSpan.className = 'activity-state state-draft';
        stateSpan.textContent = 'Draft';
      }
    }

    // Show empty state or previous content
    this.renderPreview();
  }

  /**
   * Handle cancel generation
   */
  handleCancelGeneration() {
    // Close SSE connection
    this.closeEventSource();

    // Stop timer
    this.elapsedTimer.stop();

    // Hide progress indicator
    const progressDiv = document.getElementById('generation-progress');
    if (progressDiv) {
      progressDiv.style.display = 'none';
    }

    toast.info('Generation cancelled');

    // Re-enable generate button and restore UI
    this.handleGenerationError();
  }

  /**
   * Close SSE connection
   */
  closeEventSource() {
    if (this.currentEventSource) {
      this.currentEventSource.close();
      this.currentEventSource = null;
    }
  }

  /**
   * Toggle edit mode
   */
  toggleEditMode() {
    this.isEditMode = !this.isEditMode;

    const previewContent = document.getElementById('preview-content');
    const btnEditMode = document.getElementById('btn-edit-mode');

    if (this.isEditMode) {
      previewContent.classList.add('editing');
      btnEditMode.textContent = 'Done Editing';

      // Make content editable
      const editables = previewContent.querySelectorAll('[data-section]');
      editables.forEach(el => {
        el.contentEditable = 'true';
        el.addEventListener('blur', (e) => this.handleContentEdit(e));
      });
    } else {
      previewContent.classList.remove('editing');
      btnEditMode.textContent = 'Edit Mode';

      // Remove editable
      const editables = previewContent.querySelectorAll('[contenteditable]');
      editables.forEach(el => {
        el.contentEditable = 'false';
      });
    }
  }

  /**
   * Handle inline content edit
   */
  async handleContentEdit(event) {
    if (!this.selectedActivity) return;

    const section = event.target.dataset.section;
    const newValue = event.target.textContent.trim();

    // Parse existing content
    let contentObj = this.selectedActivity.content;
    if (typeof contentObj === 'string') {
      try {
        contentObj = JSON.parse(contentObj);
      } catch (e) {
        // Plain text content - update directly
        try {
          const result = await api.put(`/courses/${this.courseId}/activities/${this.selectedActivityId}/content`, {
            content: newValue
          });
          this.selectedActivity.word_count = result.word_count;
          this.updateMetadata(this.selectedActivity);
          toast.success('Saved');
        } catch (error) {
          toast.error(`Failed to save: ${error.message}`);
        }
        return;
      }
    }

    // Update the specific section in the content object
    if (section && section !== 'sections') {
      contentObj[section] = newValue;
    }

    // Save the updated content
    try {
      const result = await api.put(`/courses/${this.courseId}/activities/${this.selectedActivityId}/content`, {
        content: JSON.stringify(contentObj)
      });

      // Update local activity data
      this.selectedActivity.content = JSON.stringify(contentObj);
      this.selectedActivity.word_count = result.word_count;
      this.updateMetadata(this.selectedActivity);

      toast.success('Saved');
    } catch (error) {
      toast.error(`Failed to save: ${error.message}`);
    }
  }

  /**
   * Show full editor modal
   */
  showFullEditor() {
    if (!this.selectedActivity) return;

    const content = this.selectedActivity.content || '';
    const editorContent = document.getElementById('editor-content');

    // Format content for editing
    if (typeof content === 'string') {
      try {
        const parsed = JSON.parse(content);
        editorContent.value = JSON.stringify(parsed, null, 2);
      } catch (e) {
        editorContent.value = content;
      }
    } else {
      editorContent.value = JSON.stringify(content, null, 2);
    }

    this.editorModal.open();
  }

  /**
   * Handle save from editor modal
   */
  async handleSaveEditor() {
    const editorContent = document.getElementById('editor-content');
    const newContent = editorContent.value;

    try {
      await api.put(`/courses/${this.courseId}/activities/${this.selectedActivityId}/content`, {
        content: newContent
      });

      // Reload and re-render
      await this.loadCourse();
      this.selectedActivity = this.findActivity(this.selectedActivityId);
      await this.renderPreview();

      this.editorModal.close();
      toast.success('Content saved successfully');
    } catch (error) {
      toast.error(`Failed to save: ${error.message}`);
    }
  }

  /**
   * Handle regenerate with feedback and/or length constraints
   */
  async handleRegenerateWithFeedback() {
    const feedbackInput = document.getElementById('regenerate-feedback');
    const feedback = feedbackInput.value.trim();

    // Build request data
    const requestData = {};
    if (feedback) {
      requestData.feedback = feedback;
    }

    // Get content type
    const contentType = this.selectedActivity?.content_type;
    const isVideo = contentType === 'video_script' || contentType === 'video' ||
                    contentType?.value === 'video_script' || contentType?.value === 'video';

    // Get length constraints based on content type
    if (isVideo) {
      const durationInput = document.getElementById('target-duration');
      const wpmInput = document.getElementById('speaking-wpm');
      const duration = durationInput?.value;
      const wpm = wpmInput?.value;

      if (duration) {
        requestData.target_duration_minutes = parseFloat(duration);
        requestData.speaking_wpm = parseInt(wpm) || 120;
      }
    } else {
      const wordCountInput = document.getElementById('target-word-count');
      const wordCount = wordCountInput?.value;

      if (wordCount) {
        requestData.target_word_count = parseInt(wordCount);
      }
    }

    // Require at least feedback or length constraint
    if (!feedback && !requestData.target_duration_minutes && !requestData.target_word_count) {
      toast.error('Please enter feedback or specify a target length');
      return;
    }

    // Close any existing SSE connection
    this.closeEventSource();

    // Show streaming UI
    const previewEmpty = document.getElementById('preview-empty');
    const previewContent = document.getElementById('preview-content');
    const previewStreaming = document.getElementById('preview-streaming');
    const streamingOutput = document.getElementById('streaming-output');

    previewEmpty.style.display = 'none';
    previewContent.style.display = 'none';
    previewStreaming.style.display = 'flex';
    streamingOutput.innerHTML = '<span class="streaming-cursor"></span>';

    // Disable buttons
    const btnRegenerate = document.getElementById('btn-regenerate');
    btnRegenerate.disabled = true;

    try {
      // POST to regenerate endpoint
      const result = await api.post(`/courses/${this.courseId}/activities/${this.selectedActivityId}/regenerate`, requestData);

      // Clear inputs
      feedbackInput.value = '';
      const wordCountInput = document.getElementById('target-word-count');
      const durationInput = document.getElementById('target-duration');
      if (wordCountInput) wordCountInput.value = '';
      if (durationInput) durationInput.value = '';

      // Handle completion
      await this.handleGenerationComplete(result.content);

    } catch (error) {
      toast.error(`Regeneration failed: ${error.message}`);
      this.handleGenerationError();
    } finally {
      btnRegenerate.disabled = false;
    }
  }

  /**
   * Handle mark as reviewed
   */
  async handleMarkReviewed() {
    if (!this.selectedActivityId) return;

    try {
      await api.put(`/courses/${this.courseId}/activities/${this.selectedActivityId}/state`, {
        build_state: 'reviewed'
      });

      // Reload and update
      await this.loadCourse();
      this.selectedActivity = this.findActivity(this.selectedActivityId);

      // Update UI
      this.updateActivityState('reviewed');
      toast.success('Marked as reviewed');

    } catch (error) {
      toast.error(`Failed to update state: ${error.message}`);
    }
  }

  /**
   * Handle approve
   */
  async handleApprove() {
    if (!this.selectedActivityId) return;

    try {
      await api.put(`/courses/${this.courseId}/activities/${this.selectedActivityId}/state`, {
        build_state: 'approved'
      });

      // Reload and update
      await this.loadCourse();
      this.selectedActivity = this.findActivity(this.selectedActivityId);

      // Update UI
      this.updateActivityState('approved');
      toast.success('Activity approved');

    } catch (error) {
      toast.error(`Failed to update state: ${error.message}`);
    }
  }

  /**
   * Update activity state in UI
   */
  updateActivityState(newState) {
    // Update activity list
    const activityItem = document.querySelector(`.activity-item[data-activity-id="${this.selectedActivityId}"]`);
    if (activityItem) {
      const stateSpan = activityItem.querySelector('.activity-state');
      if (stateSpan) {
        stateSpan.className = `activity-state state-${newState}`;
        stateSpan.textContent = newState.charAt(0).toUpperCase() + newState.slice(1);
      }
    }

    // Update controls
    this.updateControls();
  }

  // ===========================
  // Humanization
  // ===========================

  /**
   * Fetch and display humanization score for current activity
   */
  async fetchHumanizationScore() {
    if (!this.selectedActivityId || !this.selectedActivity?.content) return;

    try {
      const scoreData = await api.get(
        `/courses/${this.courseId}/activities/${this.selectedActivityId}/humanize/score`
      );

      this.updateHumanizationDisplay(scoreData.score);

      // Update metadata display
      const metaItem = document.getElementById('meta-humanization-item');
      const metaScore = document.getElementById('meta-humanization-score');
      if (metaItem && metaScore) {
        metaItem.style.display = 'inline';
        metaScore.textContent = `${scoreData.score}/100`;
      }

    } catch (error) {
      // Silently fail - humanization score is not critical
      console.warn('Failed to fetch humanization score:', error);
    }
  }

  /**
   * Update the humanization score ring display
   */
  updateHumanizationDisplay(score) {
    const scoreValue = document.getElementById('humanization-score');
    const progressRing = document.getElementById('score-ring-progress');

    if (scoreValue) {
      scoreValue.textContent = score;
    }

    if (progressRing) {
      // Update stroke-dasharray for progress
      progressRing.setAttribute('stroke-dasharray', `${score}, 100`);

      // Update color based on score
      progressRing.classList.remove('score-low', 'score-medium', 'score-high');
      if (score < 50) {
        progressRing.classList.add('score-low');
      } else if (score < 75) {
        progressRing.classList.add('score-medium');
      } else {
        progressRing.classList.add('score-high');
      }
    }
  }

  /**
   * Handle humanize button click
   */
  async handleHumanize() {
    if (!this.selectedActivityId) {
      toast.error('Please select an activity first');
      return;
    }

    const btnHumanize = document.getElementById('btn-humanize');
    if (btnHumanize) {
      btnHumanize.disabled = true;
      btnHumanize.textContent = 'Humanizing...';
    }

    try {
      const result = await api.post(
        `/courses/${this.courseId}/activities/${this.selectedActivityId}/humanize`,
        { detect_only: false }
      );

      // Update activity content
      this.selectedActivity.content = JSON.stringify(result.content);

      // Re-render preview
      await this.renderPreview();

      // Update score display
      this.updateHumanizationDisplay(result.score);

      // Show success message
      if (result.patterns_fixed > 0) {
        toast.success(`Fixed ${result.patterns_fixed} AI patterns. Score: ${result.original_score} → ${result.score}`);
      } else {
        toast.info('No patterns to fix. Content already well-humanized.');
      }

      // Reload course data
      await this.loadCourse();
      this.selectedActivity = this.findActivity(this.selectedActivityId);

    } catch (error) {
      toast.error(`Failed to humanize content: ${error.message}`);
    } finally {
      if (btnHumanize) {
        btnHumanize.disabled = false;
        btnHumanize.textContent = 'Humanize Text';
      }
    }
  }

  /**
   * Handle view patterns button click
   */
  async handleViewPatterns() {
    if (!this.selectedActivityId) {
      toast.error('Please select an activity first');
      return;
    }

    try {
      const result = await api.post(
        `/courses/${this.courseId}/activities/${this.selectedActivityId}/humanize`,
        { detect_only: true }
      );

      // Show patterns in a simple alert/modal for now
      const breakdown = result.patterns_found > 0
        ? Object.entries(result.field_results || {})
            .filter(([_, r]) => r.patterns_found?.length > 0)
            .slice(0, 10)
            .map(([field, r]) => `• ${field}: ${r.patterns_found?.length || 0} patterns`)
            .join('\n')
        : 'No AI patterns detected.';

      const message = `Humanization Score: ${result.score}/100
Patterns Found: ${result.patterns_found}

${breakdown}`;

      alert(message);

    } catch (error) {
      toast.error(`Failed to analyze patterns: ${error.message}`);
    }
  }

  // ===========================
  // Video Studio
  // ===========================

  /**
   * Open Video Studio for the current video activity
   */
  openVideoStudio() {
    if (!this.selectedActivity || !this.selectedActivity.content) {
      toast.error('No video content to display');
      return;
    }

    // Parse content
    let content;
    try {
      content = typeof this.selectedActivity.content === 'string'
        ? JSON.parse(this.selectedActivity.content)
        : this.selectedActivity.content;
    } catch (e) {
      toast.error('Failed to parse video content');
      return;
    }

    // Get metadata (may contain section_timings)
    const metadata = this.selectedActivity.metadata || {};

    // Calculate section timings if not present
    if (!metadata.section_timings) {
      const sections = ['hook', 'objective', 'content', 'ivq', 'summary', 'cta'];
      const sectionTimings = {};
      let totalWords = 0;

      for (const key of sections) {
        const section = content[key];
        if (section) {
          const text = typeof section === 'object' ? section.script_text || '' : section;
          const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
          sectionTimings[key] = Math.round(wordCount / 150 * 100) / 100;  // minutes
          totalWords += wordCount;
        }
      }

      metadata.section_timings = sectionTimings;
      metadata.estimated_duration_minutes = totalWords / 150;
    }

    // Initialize or update VideoStudio
    if (!window.videoStudio) {
      window.videoStudio = new VideoStudio({
        activityId: this.selectedActivityId,
        activityTitle: this.selectedActivity.title,
        content: content,
        metadata: metadata
      });
      window.videoStudio.init();
    } else {
      window.videoStudio.setContent(content, metadata, this.selectedActivity.title);
    }

    // Open the studio
    window.videoStudio.open();
  }

  // ===========================
  // Preview Mode
  // ===========================

  /**
   * Handle preview mode toggle between author and learner views
   */
  handleTogglePreviewMode(mode) {
    this.previewMode = mode;

    // Update toggle buttons
    const btnAuthorView = document.getElementById('btn-author-view');
    const btnLearnerPreview = document.getElementById('btn-learner-preview');
    const viewportSelector = document.getElementById('viewport-selector');
    const notesPanel = document.getElementById('notes-panel');
    const previewContent = document.getElementById('preview-content');

    if (mode === 'author') {
      btnAuthorView?.classList.add('active');
      btnLearnerPreview?.classList.remove('active');
      viewportSelector.style.display = 'none';
      if (notesPanel && this.selectedActivity) {
        notesPanel.style.display = 'block';
      }
      previewContent?.classList.remove('viewport-tablet', 'viewport-mobile');
    } else {
      btnAuthorView?.classList.remove('active');
      btnLearnerPreview?.classList.add('active');
      viewportSelector.style.display = 'flex';
      if (notesPanel) {
        notesPanel.style.display = 'none';
      }
      // Apply current viewport
      this.applyViewport();
    }

    // Re-render preview
    this.renderPreview();
  }

  /**
   * Handle viewport change for learner preview
   */
  handleViewportChange(viewport) {
    this.viewport = viewport;

    // Update viewport buttons
    const viewportBtns = document.querySelectorAll('.viewport-btn');
    viewportBtns.forEach(btn => {
      if (btn.dataset.viewport === viewport) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Apply viewport constraints
    this.applyViewport();
  }

  /**
   * Apply viewport constraints to preview content
   */
  applyViewport() {
    const previewContent = document.getElementById('preview-content');
    if (!previewContent) return;

    previewContent.classList.remove('viewport-desktop', 'viewport-tablet', 'viewport-mobile');
    previewContent.classList.add(`viewport-${this.viewport}`);
  }

  // ===========================
  // Developer Notes
  // ===========================

  /**
   * Load notes for the selected activity
   */
  async loadActivityNotes() {
    if (!this.selectedActivityId) {
      this.activityNotes = [];
      this.renderNotes();
      return;
    }

    try {
      const response = await api.get(
        `/courses/${this.courseId}/activities/${this.selectedActivityId}/notes`
      );
      this.activityNotes = response.notes || [];
      this.renderNotes();
    } catch (error) {
      console.warn('Failed to load notes:', error);
      this.activityNotes = [];
      this.renderNotes();
    }
  }

  /**
   * Render notes list
   */
  renderNotes() {
    const notesList = document.getElementById('notes-list');
    const notesEmpty = document.getElementById('notes-empty');
    if (!notesList) return;

    // Clear current content except empty state
    const existingCards = notesList.querySelectorAll('.note-card');
    existingCards.forEach(card => card.remove());

    if (this.activityNotes.length === 0) {
      if (notesEmpty) notesEmpty.style.display = 'block';
      return;
    }

    if (notesEmpty) notesEmpty.style.display = 'none';

    // Sort notes: pinned first, then by created_at descending
    const sortedNotes = [...this.activityNotes].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.created_at) - new Date(a.created_at);
    });

    for (const note of sortedNotes) {
      const noteCard = document.createElement('div');
      noteCard.className = `note-card${note.pinned ? ' pinned' : ''}`;
      noteCard.dataset.noteId = note.id;

      const createdDate = new Date(note.created_at).toLocaleDateString();

      noteCard.innerHTML = `
        <div class="note-header">
          <span class="note-author">${this.escapeHtml(note.author_name || 'Unknown')}</span>
          <span class="note-date">${createdDate}</span>
        </div>
        <div class="note-content">${this.escapeHtml(note.content)}</div>
        <div class="note-actions">
          <button class="note-pin-btn" title="${note.pinned ? 'Unpin' : 'Pin'}">
            ${note.pinned ? '📌' : '📍'}
          </button>
          <button class="note-edit-btn" title="Edit">✏️</button>
          <button class="note-delete-btn" title="Delete">🗑️</button>
        </div>
      `;

      notesList.appendChild(noteCard);
    }
  }

  /**
   * Handle add note
   */
  async handleAddNote() {
    if (!this.selectedActivityId) {
      toast.error('Please select an activity first');
      return;
    }

    const content = prompt('Enter note content:');
    if (!content || !content.trim()) return;

    try {
      const response = await api.post(
        `/courses/${this.courseId}/activities/${this.selectedActivityId}/notes`,
        { content: content.trim() }
      );

      this.activityNotes.push(response);
      this.renderNotes();
      toast.success('Note added');
    } catch (error) {
      toast.error(`Failed to add note: ${error.message}`);
    }
  }

  /**
   * Handle edit note
   */
  async handleEditNote(noteId) {
    const note = this.activityNotes.find(n => n.id === noteId);
    if (!note) return;

    const newContent = prompt('Edit note:', note.content);
    if (newContent === null || newContent.trim() === note.content) return;

    if (!newContent.trim()) {
      toast.error('Note content cannot be empty');
      return;
    }

    try {
      const response = await api.put(
        `/courses/${this.courseId}/notes/${noteId}`,
        { content: newContent.trim() }
      );

      // Update local state
      const index = this.activityNotes.findIndex(n => n.id === noteId);
      if (index !== -1) {
        this.activityNotes[index] = response;
      }
      this.renderNotes();
      toast.success('Note updated');
    } catch (error) {
      toast.error(`Failed to update note: ${error.message}`);
    }
  }

  /**
   * Handle delete note
   */
  async handleDeleteNote(noteId) {
    if (!confirm('Delete this note?')) return;

    try {
      await api.delete(`/courses/${this.courseId}/notes/${noteId}`);

      // Remove from local state
      this.activityNotes = this.activityNotes.filter(n => n.id !== noteId);
      this.renderNotes();
      toast.success('Note deleted');
    } catch (error) {
      toast.error(`Failed to delete note: ${error.message}`);
    }
  }

  /**
   * Handle toggle pin
   */
  async handleTogglePin(noteId) {
    const note = this.activityNotes.find(n => n.id === noteId);
    if (!note) return;

    try {
      const response = await api.put(
        `/courses/${this.courseId}/notes/${noteId}`,
        { pinned: !note.pinned }
      );

      // Update local state
      const index = this.activityNotes.findIndex(n => n.id === noteId);
      if (index !== -1) {
        this.activityNotes[index] = response;
      }
      this.renderNotes();
    } catch (error) {
      toast.error(`Failed to update note: ${error.message}`);
    }
  }

  // ===========================
  // Help System
  // ===========================

  bindHelpHandlers() {
    // Handle help button clicks
    document.addEventListener('click', (e) => {
      const helpBtn = e.target.closest('.help-btn');
      if (helpBtn) {
        e.preventDefault();
        const helpTopic = helpBtn.dataset.help;
        if (helpTopic && window.help) {
          window.help.showTerm(helpTopic);
        }
      }
    });
  }
}

// Export for use
window.StudioController = StudioController;
