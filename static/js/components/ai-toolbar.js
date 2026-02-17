/**
 * AI Toolbar Controller
 *
 * Manages the floating AI editing toolbar that appears on text selection.
 * Provides quick actions, custom prompts, diff preview, and undo/redo.
 */
class AIToolbar {
  constructor(options = {}) {
    this.options = {
      apiBaseUrl: '/api/edit',
      courseId: options.courseId || null,
      activityId: options.activityId || null,
      contentType: options.contentType || null,
      learningOutcomes: options.learningOutcomes || [],
      bloomLevel: options.bloomLevel || null,
      ...options
    };

    // Toolbar elements
    this.toolbarEl = null;
    this.containerEl = null;
    this.currentSelection = null;
    this.currentRange = null;

    // State
    this.isVisible = false;
    this.isLoading = false;
    this.currentSuggestion = null;
    this.currentAction = null;
    this.selectionDebounceTimer = null;
    this.lastSelectionTime = 0;

    // History (session-scoped)
    this.sessionId = this._generateSessionId();
    this.historyEnabled = false;

    // Keyboard shortcuts
    this.shortcuts = {
      'improve': 'ctrl+shift+i',
      'expand': 'ctrl+shift+e',
      'simplify': 'ctrl+shift+s',
      'undo': 'ctrl+z',
      'redo': 'ctrl+shift+z'
    };

    // Initialize
    this._init();
  }

  /**
   * Initialize the toolbar
   */
  _init() {
    // Create toolbar element from template or existing element
    this.toolbarEl = document.getElementById('ai-toolbar');
    if (!this.toolbarEl) {
      console.error('AI toolbar element not found');
      return;
    }

    // Bind event handlers
    this._bindEvents();

    // Update Bloom badge if provided
    if (this.options.bloomLevel) {
      this._updateBloomBadge(this.options.bloomLevel);
    }

    // Initialize history state
    this._initHistory();
  }

  /**
   * Attach toolbar to a content container
   */
  attach(containerEl) {
    this.containerEl = containerEl;

    // Listen for selection changes
    document.addEventListener('selectionchange', this._handleSelectionChange.bind(this));

    // Listen for clicks outside
    document.addEventListener('click', this._handleClickOutside.bind(this));

    // Listen for keyboard shortcuts
    document.addEventListener('keydown', this._handleKeyboardShortcut.bind(this));

    // Listen for escape key
    document.addEventListener('keydown', this._handleEscape.bind(this));

    console.log('AI Toolbar attached to container');
  }

  /**
   * Detach toolbar
   */
  detach() {
    this.hide();
    document.removeEventListener('selectionchange', this._handleSelectionChange.bind(this));
    document.removeEventListener('click', this._handleClickOutside.bind(this));
    document.removeEventListener('keydown', this._handleKeyboardShortcut.bind(this));
    document.removeEventListener('keydown', this._handleEscape.bind(this));
  }

  /**
   * Bind event handlers to toolbar elements
   */
  _bindEvents() {
    // Action buttons
    const actionBtns = this.toolbarEl.querySelectorAll('[data-action]');
    actionBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const tone = btn.dataset.tone || null;
        this._handleAction(action, tone);
      });
    });

    // Dropdown toggle
    const dropdownToggle = this.toolbarEl.querySelector('[data-toggle-dropdown]');
    if (dropdownToggle) {
      dropdownToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this._toggleDropdown();
      });
    }

    // Custom prompt input
    const customInput = this.toolbarEl.querySelector('[data-custom-input]');
    if (customInput) {
      customInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this._handleAction('custom');
        }
      });
    }

    // Preview actions
    const acceptBtn = this.toolbarEl.querySelector('[data-preview-accept]');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => this._acceptSuggestion());
    }

    const rejectBtn = this.toolbarEl.querySelector('[data-preview-reject]');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => this._rejectSuggestion());
    }

    const regenerateBtn = this.toolbarEl.querySelector('[data-preview-regenerate]');
    if (regenerateBtn) {
      regenerateBtn.addEventListener('click', () => this._regenerateSuggestion());
    }

    const previewClose = this.toolbarEl.querySelector('[data-preview-close]');
    if (previewClose) {
      previewClose.addEventListener('click', () => this._closePreview());
    }

    // History buttons
    const undoBtn = this.toolbarEl.querySelector('[data-undo]');
    if (undoBtn) {
      undoBtn.addEventListener('click', () => this._undo());
    }

    const redoBtn = this.toolbarEl.querySelector('[data-redo]');
    if (redoBtn) {
      redoBtn.addEventListener('click', () => this._redo());
    }
  }

  /**
   * Handle selection change (debounced to prevent flicker during selection)
   */
  _handleSelectionChange() {
    // Clear any pending debounce timer
    if (this.selectionDebounceTimer) {
      clearTimeout(this.selectionDebounceTimer);
    }

    // Debounce the selection handling to wait for selection to stabilize
    this.selectionDebounceTimer = setTimeout(() => {
      this._processSelection();
    }, 150);
  }

  /**
   * Process the current selection after debounce
   */
  _processSelection() {
    const selection = window.getSelection();

    // Hide toolbar if no selection or selection is empty
    if (!selection || selection.toString().trim().length === 0) {
      this.hide();
      return;
    }

    // Check if selection is within our container
    if (!this.containerEl || !this.containerEl.contains(selection.anchorNode)) {
      this.hide();
      return;
    }

    // Show toolbar at selection
    this.currentSelection = selection.toString();
    this.currentRange = selection.getRangeAt(0);
    this.lastSelectionTime = Date.now();
    this.show(selection);
  }

  /**
   * Show toolbar at selection
   */
  show(selection) {
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Position toolbar above selection
    const toolbarRect = this.toolbarEl.getBoundingClientRect();
    const top = rect.top + window.scrollY - toolbarRect.height - 8;
    const left = rect.left + window.scrollX + (rect.width / 2) - (toolbarRect.width / 2);

    // Adjust if toolbar would go off-screen
    const adjustedLeft = Math.max(8, Math.min(left, window.innerWidth - toolbarRect.width - 8));

    this.toolbarEl.style.top = `${top}px`;
    this.toolbarEl.style.left = `${adjustedLeft}px`;
    this.toolbarEl.style.display = 'block';
    this.toolbarEl.classList.add('visible');

    this.isVisible = true;
  }

  /**
   * Hide toolbar
   */
  hide() {
    if (!this.isVisible) return;

    this.toolbarEl.classList.remove('visible');
    setTimeout(() => {
      this.toolbarEl.style.display = 'none';
    }, 200);

    this.isVisible = false;
    this.currentSelection = null;
    this.currentRange = null;

    // Close dropdown if open
    this._closeDropdown();
    this._closePreview();
  }

  /**
   * Handle action button click
   */
  async _handleAction(action, tone = null) {
    if (!this.currentSelection) {
      console.warn('No text selected');
      return;
    }

    // Get custom prompt if action is custom
    let customPrompt = null;
    if (action === 'custom') {
      const customInput = this.toolbarEl.querySelector('[data-custom-input]');
      customPrompt = customInput ? customInput.value.trim() : null;

      if (tone) {
        customPrompt = `Change the tone to be more ${tone}`;
      }

      if (!customPrompt) {
        window.toast?.error('Please enter a custom instruction');
        return;
      }
    }

    this.currentAction = action;

    // Close dropdown
    this._closeDropdown();

    // Show loading state
    this._showLoading();

    try {
      // Call suggestion API
      const suggestion = await this._callSuggest(this.currentSelection, action, customPrompt);

      // Hide loading
      this._hideLoading();

      // Show preview
      this._showPreview(suggestion);

      // Clear custom input
      if (action === 'custom') {
        const customInput = this.toolbarEl.querySelector('[data-custom-input]');
        if (customInput) customInput.value = '';
      }

    } catch (error) {
      console.error('AI suggestion error:', error);
      this._hideLoading();
      window.toast?.error(`Failed to generate suggestion: ${error.message}`);
    }
  }

  /**
   * Call suggest API
   */
  async _callSuggest(text, action, customPrompt = null) {
    const url = `${this.options.apiBaseUrl}/suggest`;

    const payload = {
      text: text,
      action: action,
      custom_prompt: customPrompt,
      context: {
        content_type: this.options.contentType,
        bloom_level: this.options.bloomLevel,
        learning_outcomes: this.options.learningOutcomes
      }
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'API request failed');
    }

    const data = await response.json();
    return data;
  }

  /**
   * Show loading state
   */
  _showLoading() {
    this.isLoading = true;
    const loadingEl = this.toolbarEl.querySelector('[data-loading]');
    if (loadingEl) {
      loadingEl.style.display = 'flex';
    }

    // Hide toolbar content
    const contentEl = this.toolbarEl.querySelector('.toolbar-content');
    if (contentEl) {
      contentEl.style.display = 'none';
    }
  }

  /**
   * Hide loading state
   */
  _hideLoading() {
    this.isLoading = false;
    const loadingEl = this.toolbarEl.querySelector('[data-loading]');
    if (loadingEl) {
      loadingEl.style.display = 'none';
    }

    // Show toolbar content
    const contentEl = this.toolbarEl.querySelector('.toolbar-content');
    if (contentEl) {
      contentEl.style.display = 'flex';
    }
  }

  /**
   * Show preview with diff
   */
  _showPreview(suggestion) {
    this.currentSuggestion = suggestion;

    const previewEl = this.toolbarEl.querySelector('[data-preview]');
    const diffEl = this.toolbarEl.querySelector('[data-preview-diff]');

    if (!previewEl || !diffEl) return;

    // Generate inline diff HTML
    const diffHtml = this._generateInlineDiff(
      this.currentSelection,
      suggestion.suggestion
    );

    diffEl.innerHTML = diffHtml;
    previewEl.style.display = 'block';

    // Update Bloom level if provided
    if (suggestion.bloom_level) {
      this._updateBloomBadge(suggestion.bloom_level);
    }
  }

  /**
   * Generate inline diff HTML
   */
  _generateInlineDiff(original, suggested) {
    // Simple word-level diff
    const originalWords = original.split(/\s+/);
    const suggestedWords = suggested.split(/\s+/);

    let html = '';
    const maxLen = Math.max(originalWords.length, suggestedWords.length);

    for (let i = 0; i < maxLen; i++) {
      const origWord = originalWords[i];
      const suggWord = suggestedWords[i];

      if (origWord === suggWord) {
        html += `${origWord} `;
      } else if (!origWord && suggWord) {
        html += `<ins>${suggWord}</ins> `;
      } else if (origWord && !suggWord) {
        html += `<del>${origWord}</del> `;
      } else {
        html += `<del>${origWord}</del> <ins>${suggWord}</ins> `;
      }
    }

    return html;
  }

  /**
   * Close preview
   */
  _closePreview() {
    const previewEl = this.toolbarEl.querySelector('[data-preview]');
    if (previewEl) {
      previewEl.style.display = 'none';
    }
    this.currentSuggestion = null;
  }

  /**
   * Accept suggestion
   */
  async _acceptSuggestion() {
    if (!this.currentSuggestion || !this.currentRange) return;

    const newText = this.currentSuggestion.suggestion;

    // Replace selected text
    this.currentRange.deleteContents();
    this.currentRange.insertNode(document.createTextNode(newText));

    // Push to history
    await this._pushToHistory({
      type: 'ai_edit',
      action: this.currentAction,
      original_text: this.currentSelection,
      new_text: newText,
      position: this._getSelectionPosition(this.currentRange)
    });

    // Close preview and hide toolbar
    this._closePreview();
    this.hide();

    // Notify user
    window.toast?.success('Suggestion applied');

    // Trigger content save if callback provided
    if (this.options.onContentChange) {
      this.options.onContentChange();
    }
  }

  /**
   * Reject suggestion
   */
  _rejectSuggestion() {
    this._closePreview();
    window.toast?.info('Suggestion rejected');
  }

  /**
   * Regenerate suggestion
   */
  async _regenerateSuggestion() {
    if (!this.currentAction) return;

    this._closePreview();
    await this._handleAction(this.currentAction);
  }

  /**
   * Toggle dropdown menu
   */
  _toggleDropdown() {
    const dropdown = this.toolbarEl.querySelector('[data-dropdown-menu]');
    if (dropdown) {
      dropdown.classList.toggle('show');
    }
  }

  /**
   * Close dropdown menu
   */
  _closeDropdown() {
    const dropdown = this.toolbarEl.querySelector('[data-dropdown-menu]');
    if (dropdown) {
      dropdown.classList.remove('show');
    }
  }

  /**
   * Update Bloom's badge
   */
  _updateBloomBadge(level) {
    const badge = this.toolbarEl.querySelector('[data-bloom-badge]');
    if (badge) {
      badge.textContent = level.charAt(0).toUpperCase() + level.slice(1);
      badge.setAttribute('data-level', level.toLowerCase());
    }
  }

  /**
   * Initialize history
   */
  async _initHistory() {
    if (!this.options.courseId || !this.options.activityId) {
      console.warn('History requires courseId and activityId');
      return;
    }

    try {
      // Check history state from API
      const response = await fetch(
        `/api/edit/history/state?session_id=${this.sessionId}&course_id=${this.options.courseId}&activity_id=${this.options.activityId}`
      );

      if (response.ok) {
        const state = await response.json();
        this.historyEnabled = true;
        this._updateHistoryButtons(state.can_undo, state.can_redo);
      }
    } catch (error) {
      console.warn('Failed to initialize history:', error);
    }
  }

  /**
   * Push command to history
   */
  async _pushToHistory(command) {
    if (!this.historyEnabled) return;

    try {
      const response = await fetch('/api/edit/history/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          course_id: this.options.courseId,
          activity_id: this.options.activityId,
          command: command
        })
      });

      if (response.ok) {
        const state = await response.json();
        this._updateHistoryButtons(state.can_undo, state.can_redo);
      }
    } catch (error) {
      console.error('Failed to push to history:', error);
    }
  }

  /**
   * Undo last command
   */
  async _undo() {
    if (!this.historyEnabled) return;

    try {
      const response = await fetch('/api/edit/history/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          course_id: this.options.courseId,
          activity_id: this.options.activityId
        })
      });

      if (response.ok) {
        const result = await response.json();

        if (result.command) {
          // Apply undo by reverting to original text
          this._applyHistoryCommand(result.command, true);
        }

        this._updateHistoryButtons(result.can_undo, result.can_redo);
        window.toast?.success('Undo applied');
      }
    } catch (error) {
      console.error('Undo failed:', error);
      window.toast?.error('Undo failed');
    }
  }

  /**
   * Redo last undone command
   */
  async _redo() {
    if (!this.historyEnabled) return;

    try {
      const response = await fetch('/api/edit/history/redo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          course_id: this.options.courseId,
          activity_id: this.options.activityId
        })
      });

      if (response.ok) {
        const result = await response.json();

        if (result.command) {
          // Apply redo by reapplying new text
          this._applyHistoryCommand(result.command, false);
        }

        this._updateHistoryButtons(result.can_undo, result.can_redo);
        window.toast?.success('Redo applied');
      }
    } catch (error) {
      console.error('Redo failed:', error);
      window.toast?.error('Redo failed');
    }
  }

  /**
   * Apply history command to content
   */
  _applyHistoryCommand(command, isUndo) {
    // This is a simplified version - real implementation would need
    // to find and replace text at the correct position in the document
    console.log('Apply history command:', command, 'undo:', isUndo);

    // Trigger content reload if callback provided
    if (this.options.onContentChange) {
      this.options.onContentChange();
    }
  }

  /**
   * Update history button states
   */
  _updateHistoryButtons(canUndo, canRedo) {
    const undoBtn = this.toolbarEl.querySelector('[data-undo]');
    const redoBtn = this.toolbarEl.querySelector('[data-redo]');

    if (undoBtn) {
      undoBtn.disabled = !canUndo;
    }

    if (redoBtn) {
      redoBtn.disabled = !canRedo;
    }
  }

  /**
   * Handle click outside toolbar
   */
  _handleClickOutside(e) {
    if (!this.isVisible) return;

    // Don't hide if we just selected text (within 300ms)
    // This prevents the toolbar from disappearing on mouseup after selection
    if (Date.now() - this.lastSelectionTime < 300) {
      return;
    }

    // Don't hide if clicking inside the container (might be selecting more text)
    if (this.containerEl && this.containerEl.contains(e.target)) {
      // Check if there's still a valid selection
      const selection = window.getSelection();
      if (selection && selection.toString().trim().length > 0) {
        return;
      }
    }

    if (!this.toolbarEl.contains(e.target)) {
      this.hide();
    }
  }

  /**
   * Handle escape key
   */
  _handleEscape(e) {
    if (e.key === 'Escape' && this.isVisible) {
      this.hide();
    }
  }

  /**
   * Handle keyboard shortcuts
   */
  _handleKeyboardShortcut(e) {
    // Check for shortcuts
    const key = this._getShortcutKey(e);

    if (key === this.shortcuts.improve && this.currentSelection) {
      e.preventDefault();
      this._handleAction('improve');
    } else if (key === this.shortcuts.expand && this.currentSelection) {
      e.preventDefault();
      this._handleAction('expand');
    } else if (key === this.shortcuts.simplify && this.currentSelection) {
      e.preventDefault();
      this._handleAction('simplify');
    } else if (key === this.shortcuts.undo) {
      e.preventDefault();
      this._undo();
    } else if (key === this.shortcuts.redo) {
      e.preventDefault();
      this._redo();
    }
  }

  /**
   * Get shortcut key string from event
   */
  _getShortcutKey(e) {
    const parts = [];
    if (e.ctrlKey || e.metaKey) parts.push('ctrl');
    if (e.shiftKey) parts.push('shift');
    if (e.altKey) parts.push('alt');
    parts.push(e.key.toLowerCase());
    return parts.join('+');
  }

  /**
   * Get selection position in document
   */
  _getSelectionPosition(range) {
    // Calculate character offset from container start
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(this.containerEl);
    preCaretRange.setEnd(range.startContainer, range.startOffset);
    return preCaretRange.toString().length;
  }

  /**
   * Generate unique session ID
   */
  _generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Export for use
window.AIToolbar = AIToolbar;
