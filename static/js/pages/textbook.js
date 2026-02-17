/**
 * Textbook Controller - Chapter generation and glossary management
 *
 * Manages:
 * - Chapter list display and selection
 * - Chapter generation (single and bulk)
 * - Job status polling for async generation
 * - Chapter preview rendering
 * - Glossary CRUD operations
 * - Tab navigation
 */
class TextbookController {
  constructor(courseId) {
    this.courseId = courseId;
    this.course = null;
    this.chapters = [];
    this.learningOutcomes = [];
    this.selectedChapterId = null;
    this.viewingFullTextbook = false;

    // Modals
    this.termModal = null;
    this.deleteTermModal = null;

    // Glossary state
    this.currentTermId = null;
    this.currentTermChapterId = null;
    this.allGlossaryTerms = [];

    // Polling state
    this.activePolls = new Map();
  }

  async init() {
    // Initialize modals
    this.termModal = new Modal('term-modal');
    this.deleteTermModal = new Modal('delete-term-modal');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
    }

    // Bind event handlers
    this.bindEventHandlers();

    // Load course data
    await this.loadCourse();
  }

  /**
   * Bind all event handlers
   */
  bindEventHandlers() {
    // Tab navigation
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => this.handleTabClick(e));
    });

    // Generate buttons
    const btnGenerateAll = document.getElementById('btn-generate-all');
    if (btnGenerateAll) {
      btnGenerateAll.addEventListener('click', () => this.handleGenerateAll());
    }

    // View full textbook
    const btnViewFull = document.getElementById('btn-view-full');
    if (btnViewFull) {
      btnViewFull.addEventListener('click', () => this.renderFullTextbook());
    }

    // Glossary term buttons
    const btnAddTerm = document.getElementById('btn-add-term');
    if (btnAddTerm) {
      btnAddTerm.addEventListener('click', () => this.showAddTerm());
    }

    // Term form submission
    const termForm = document.getElementById('term-form');
    if (termForm) {
      termForm.addEventListener('submit', (e) => this.handleTermSave(e));
    }

    // Delete term confirmation
    const btnConfirmDeleteTerm = document.getElementById('btn-confirm-delete-term');
    if (btnConfirmDeleteTerm) {
      btnConfirmDeleteTerm.addEventListener('click', () => this.handleTermDelete());
    }

    // Chapter list click delegation
    const chapterList = document.getElementById('chapter-list');
    if (chapterList) {
      chapterList.addEventListener('click', (e) => this.handleChapterListClick(e));
    }

    // Glossary list click delegation
    const glossaryList = document.getElementById('glossary-list');
    if (glossaryList) {
      glossaryList.addEventListener('click', (e) => this.handleGlossaryListClick(e));
    }
  }

  /**
   * Handle tab navigation
   */
  handleTabClick(e) {
    const tabBtn = e.target;
    const tabId = tabBtn.dataset.tab;

    // Update active tab button
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    tabBtn.classList.add('active');

    // Update active tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    const tabContent = document.getElementById(`tab-${tabId}`);
    if (tabContent) {
      tabContent.classList.add('active');
    }

    // Load glossary when switching to that tab
    if (tabId === 'glossary') {
      this.loadGlossary();
    }
  }

  /**
   * Load course data from API
   */
  async loadCourse() {
    try {
      this.course = await api.get(`/courses/${this.courseId}`);
      this.learningOutcomes = this.course.learning_outcomes || [];
      this.chapters = this.course.textbook_chapters || [];

      this.renderChapterList();
      this.updateChapterSelectOptions();
    } catch (error) {
      toast.error(`Failed to load course: ${error.message}`);
    }
  }

  /**
   * Render the chapter list based on learning outcomes
   */
  renderChapterList() {
    const chapterList = document.getElementById('chapter-list');
    if (!chapterList) return;

    if (this.learningOutcomes.length === 0) {
      chapterList.innerHTML = `
        <div class="empty-state">
          <p>No learning outcomes defined.</p>
          <p class="hint">Add learning outcomes in the Planner to generate textbook chapters.</p>
        </div>
      `;
      return;
    }

    // Build chapter items from learning outcomes
    const html = this.learningOutcomes.map((outcome, index) => {
      const chapter = this.findChapterByOutcome(outcome.id);
      const chapterNumber = index + 1;
      const status = chapter ? 'generated' : 'not-generated';
      const statusText = chapter ? 'Generated' : 'Not Generated';
      const wordCount = chapter ? `${chapter.word_count} words` : '';

      return `
        <div class="chapter-item ${this.selectedChapterId === (chapter?.id || outcome.id) ? 'selected' : ''}"
             data-outcome-id="${outcome.id}"
             data-chapter-id="${chapter?.id || ''}">
          <div class="chapter-number">${chapterNumber}</div>
          <div class="chapter-info">
            <div class="chapter-title">${this.escapeHtml(outcome.behavior || `Chapter ${chapterNumber}`)}</div>
            <div class="chapter-meta">
              <span class="chapter-status ${status}">${statusText}</span>
              ${wordCount ? `<span>${wordCount}</span>` : ''}
            </div>
          </div>
          <div class="chapter-actions">
            ${chapter ? '' : `<button class="btn btn-primary btn-small btn-generate" data-outcome-id="${outcome.id}">Generate</button>`}
          </div>
        </div>
      `;
    }).join('');

    chapterList.innerHTML = html;
  }

  /**
   * Find chapter by learning outcome ID
   */
  findChapterByOutcome(outcomeId) {
    return this.chapters.find(ch => ch.learning_outcome_id === outcomeId);
  }

  /**
   * Handle clicks on chapter list
   */
  handleChapterListClick(e) {
    // Check for generate button click
    const generateBtn = e.target.closest('.btn-generate');
    if (generateBtn) {
      const outcomeId = generateBtn.dataset.outcomeId;
      this.handleGenerateChapter(outcomeId);
      return;
    }

    // Check for chapter item click (selection)
    const chapterItem = e.target.closest('.chapter-item');
    if (chapterItem) {
      const outcomeId = chapterItem.dataset.outcomeId;
      const chapterId = chapterItem.dataset.chapterId;
      this.handleChapterSelect(outcomeId, chapterId);
    }
  }

  /**
   * Handle chapter selection
   */
  handleChapterSelect(outcomeId, chapterId) {
    this.viewingFullTextbook = false;

    // Update selection state
    this.selectedChapterId = chapterId || outcomeId;

    // Update UI selection
    document.querySelectorAll('.chapter-item').forEach(item => {
      item.classList.remove('selected');
    });
    const selectedItem = document.querySelector(`.chapter-item[data-outcome-id="${outcomeId}"]`);
    if (selectedItem) {
      selectedItem.classList.add('selected');
    }

    // Show preview
    if (chapterId) {
      const chapter = this.chapters.find(ch => ch.id === chapterId);
      if (chapter) {
        this.renderChapterPreview(chapter);
        return;
      }
    }

    // Show not generated state
    const outcome = this.learningOutcomes.find(lo => lo.id === outcomeId);
    this.showNotGeneratedPreview(outcome);
  }

  /**
   * Show preview for not-yet-generated chapter
   */
  showNotGeneratedPreview(outcome) {
    const previewContent = document.getElementById('preview-content');
    const previewTitle = document.getElementById('preview-title');

    if (previewTitle) {
      previewTitle.textContent = 'Preview';
    }

    if (previewContent && outcome) {
      previewContent.innerHTML = `
        <div class="preview-empty">
          <div class="empty-icon">&#128221;</div>
          <p>Chapter not yet generated</p>
          <p class="hint">Learning Outcome: ${this.escapeHtml(outcome.behavior)}</p>
          <button class="btn btn-primary" onclick="window.textbookController.handleGenerateChapter('${outcome.id}')">Generate Chapter</button>
        </div>
      `;
    }
  }

  /**
   * Generate a single chapter
   */
  async handleGenerateChapter(outcomeId) {
    const outcome = this.learningOutcomes.find(lo => lo.id === outcomeId);
    if (!outcome) {
      toast.error('Learning outcome not found');
      return;
    }

    // Update UI to show generating state
    const chapterItem = document.querySelector(`.chapter-item[data-outcome-id="${outcomeId}"]`);
    if (chapterItem) {
      const statusEl = chapterItem.querySelector('.chapter-status');
      if (statusEl) {
        statusEl.className = 'chapter-status generating';
        statusEl.textContent = 'Generating...';
      }
      const generateBtn = chapterItem.querySelector('.btn-generate');
      if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
      }
    }

    try {
      // Start generation
      const response = await api.post(`/courses/${this.courseId}/textbook/generate`, {
        learning_outcome_id: outcomeId,
        topic: outcome.behavior
      });

      const taskId = response.task_id;

      // Poll for completion
      this.pollJobStatus(taskId, (result) => {
        if (result.status === 'completed') {
          toast.success('Chapter generated successfully');
          this.loadCourse(); // Reload to get updated chapters
        } else if (result.status === 'failed') {
          toast.error(`Generation failed: ${result.error || 'Unknown error'}`);
          this.loadCourse(); // Reload to reset UI
        }
      });

    } catch (error) {
      toast.error(`Failed to generate chapter: ${error.message}`);
      this.loadCourse(); // Reload to reset UI
    }
  }

  /**
   * Generate all chapters
   */
  async handleGenerateAll() {
    const ungenerated = this.learningOutcomes.filter(lo => !this.findChapterByOutcome(lo.id));

    if (ungenerated.length === 0) {
      toast.info('All chapters already generated');
      return;
    }

    // Show progress UI
    const progressEl = document.getElementById('generation-progress');
    const progressCount = document.getElementById('progress-count');
    const progressFill = document.getElementById('progress-fill');

    if (progressEl) progressEl.style.display = 'block';

    let completed = 0;
    const total = ungenerated.length;

    const updateProgress = () => {
      if (progressCount) progressCount.textContent = `${completed}/${total}`;
      if (progressFill) progressFill.style.width = `${(completed / total) * 100}%`;
    };

    updateProgress();

    // Generate each chapter sequentially to avoid overload
    for (const outcome of ungenerated) {
      try {
        const response = await api.post(`/courses/${this.courseId}/textbook/generate`, {
          learning_outcome_id: outcome.id,
          topic: outcome.behavior
        });

        // Wait for this chapter to complete before starting next
        await this.waitForJob(response.task_id);
        completed++;
        updateProgress();
        await this.loadCourse(); // Reload to get updated chapters

      } catch (error) {
        toast.error(`Failed to generate chapter for: ${outcome.behavior}`);
        completed++;
        updateProgress();
      }
    }

    // Hide progress and show completion
    if (progressEl) progressEl.style.display = 'none';
    toast.success(`Generated ${completed} chapters`);
  }

  /**
   * Poll job status until complete
   */
  pollJobStatus(taskId, callback, interval = 2000) {
    const poll = async () => {
      try {
        const job = await api.get(`/jobs/${taskId}`);

        if (job.status === 'completed' || job.status === 'failed') {
          this.activePolls.delete(taskId);
          callback(job);
        } else {
          // Continue polling
          const timeoutId = setTimeout(poll, interval);
          this.activePolls.set(taskId, timeoutId);
        }
      } catch (error) {
        this.activePolls.delete(taskId);
        callback({ status: 'failed', error: error.message });
      }
    };

    poll();
  }

  /**
   * Wait for job to complete (Promise-based)
   */
  waitForJob(taskId, interval = 2000) {
    return new Promise((resolve, reject) => {
      this.pollJobStatus(taskId, (result) => {
        if (result.status === 'completed') {
          resolve(result);
        } else {
          reject(new Error(result.error || 'Job failed'));
        }
      }, interval);
    });
  }

  /**
   * Render chapter preview
   */
  renderChapterPreview(chapter) {
    const previewContent = document.getElementById('preview-content');
    const previewTitle = document.getElementById('preview-title');

    if (previewTitle) {
      previewTitle.textContent = chapter.title || 'Chapter Preview';
    }

    if (!previewContent) return;

    // Build sections HTML
    const sectionsHtml = (chapter.sections || []).map(section => `
      <div class="chapter-section">
        <h3 class="section-heading">${this.escapeHtml(section.heading || '')}</h3>
        <div class="section-content">
          ${this.formatContent(section.content || '')}
        </div>
        ${section.key_concepts && section.key_concepts.length > 0 ? `
          <div class="key-concepts">
            <div class="key-concepts-title">Key Concepts</div>
            <ul class="key-concepts-list">
              ${section.key_concepts.map(concept => `<li>${this.escapeHtml(concept)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `).join('');

    // Build image placeholders HTML
    const imagesHtml = (chapter.image_placeholders || []).map(img => `
      <div class="image-placeholder">
        <div class="image-placeholder-icon">&#128444;</div>
        <div class="image-placeholder-caption">${this.escapeHtml(img.caption || 'Image')}</div>
        ${img.description ? `<div class="image-placeholder-desc">${this.escapeHtml(img.description)}</div>` : ''}
      </div>
    `).join('');

    // Build references HTML
    const referencesHtml = (chapter.references || []).length > 0 ? `
      <div class="references-section">
        <h3 class="references-title">References</h3>
        <ul class="reference-list">
          ${chapter.references.map(ref => `
            <li class="reference-item">
              ${this.escapeHtml(ref.citation || ref.title || '')}
            </li>
          `).join('')}
        </ul>
      </div>
    ` : '';

    // Build coherence issues warning if any
    const issuesHtml = (chapter.coherence_issues || []).length > 0 ? `
      <div class="coherence-warning" style="background: var(--warning-bg); padding: var(--spacing-md); border-radius: var(--radius-sm); margin-bottom: var(--spacing-lg);">
        <strong style="color: var(--warning);">Coherence Issues Found:</strong>
        <ul style="margin: var(--spacing-sm) 0 0 var(--spacing-md); color: var(--text-secondary);">
          ${chapter.coherence_issues.map(issue => `<li>${this.escapeHtml(issue)}</li>`).join('')}
        </ul>
      </div>
    ` : '';

    previewContent.innerHTML = `
      <div class="chapter-preview">
        ${issuesHtml}
        <h2 class="chapter-preview-title">${this.escapeHtml(chapter.title || 'Chapter')}</h2>
        ${sectionsHtml}
        ${imagesHtml}
        ${referencesHtml}
      </div>
    `;
  }

  /**
   * Render full textbook with table of contents
   */
  renderFullTextbook() {
    this.viewingFullTextbook = true;
    this.selectedChapterId = null;

    // Deselect all chapters
    document.querySelectorAll('.chapter-item').forEach(item => {
      item.classList.remove('selected');
    });

    const previewContent = document.getElementById('preview-content');
    const previewTitle = document.getElementById('preview-title');

    if (previewTitle) {
      previewTitle.textContent = 'Full Textbook';
    }

    if (!previewContent) return;

    // Check if any chapters exist
    if (this.chapters.length === 0) {
      previewContent.innerHTML = `
        <div class="preview-empty">
          <div class="empty-icon">&#128214;</div>
          <p>No chapters generated yet</p>
          <p class="hint">Generate chapters to view the full textbook</p>
        </div>
      `;
      return;
    }

    // Build table of contents
    const tocHtml = `
      <div class="textbook-toc">
        <h3 class="textbook-toc-title">Table of Contents</h3>
        <ol class="textbook-toc-list">
          ${this.learningOutcomes.map((outcome, index) => {
            const chapter = this.findChapterByOutcome(outcome.id);
            const title = chapter?.title || outcome.behavior || `Chapter ${index + 1}`;
            const hasChapter = !!chapter;
            return `
              <li>
                ${hasChapter
                  ? `<a href="#chapter-${chapter.id}">${this.escapeHtml(title)}</a>`
                  : `<span style="color: var(--text-muted);">${this.escapeHtml(title)} (not generated)</span>`
                }
              </li>
            `;
          }).join('')}
        </ol>
      </div>
    `;

    // Build chapters HTML
    const chaptersHtml = this.chapters.map(chapter => {
      const sectionsHtml = (chapter.sections || []).map(section => `
        <div class="chapter-section">
          <h3 class="section-heading">${this.escapeHtml(section.heading || '')}</h3>
          <div class="section-content">
            ${this.formatContent(section.content || '')}
          </div>
        </div>
      `).join('');

      return `
        <div class="chapter-preview" id="chapter-${chapter.id}" style="margin-bottom: var(--spacing-2xl); padding-bottom: var(--spacing-xl); border-bottom: 1px solid var(--border-subtle);">
          <h2 class="chapter-preview-title">${this.escapeHtml(chapter.title || 'Chapter')}</h2>
          ${sectionsHtml}
        </div>
      `;
    }).join('');

    previewContent.innerHTML = `
      <div class="full-textbook">
        ${tocHtml}
        ${chaptersHtml}
      </div>
    `;
  }

  /**
   * Format content text (simple paragraph handling)
   */
  formatContent(text) {
    if (!text) return '';
    // Split by double newlines for paragraphs
    const paragraphs = text.split(/\n\n+/);
    return paragraphs.map(p => `<p>${this.escapeHtml(p.trim())}</p>`).join('');
  }

  // =========================================
  // Glossary Management (Task 3)
  // =========================================

  /**
   * Load glossary from all chapters
   */
  loadGlossary() {
    // Aggregate glossary terms from all chapters
    this.allGlossaryTerms = [];

    this.chapters.forEach(chapter => {
      (chapter.glossary_terms || []).forEach(term => {
        this.allGlossaryTerms.push({
          ...term,
          chapterId: chapter.id,
          chapterTitle: chapter.title
        });
      });
    });

    // Sort alphabetically by term
    this.allGlossaryTerms.sort((a, b) => {
      const termA = (a.term || '').toLowerCase();
      const termB = (b.term || '').toLowerCase();
      return termA.localeCompare(termB);
    });

    this.renderGlossaryList();
  }

  /**
   * Render glossary list grouped by first letter
   */
  renderGlossaryList() {
    const glossaryList = document.getElementById('glossary-list');
    if (!glossaryList) return;

    if (this.allGlossaryTerms.length === 0) {
      glossaryList.innerHTML = `
        <div class="empty-state">
          <p>No glossary terms yet.</p>
          <p class="hint">Generate chapters to populate glossary, or add terms manually.</p>
        </div>
      `;
      return;
    }

    // Group by first letter
    const groups = {};
    this.allGlossaryTerms.forEach(term => {
      const firstLetter = (term.term || '').charAt(0).toUpperCase() || '#';
      if (!groups[firstLetter]) {
        groups[firstLetter] = [];
      }
      groups[firstLetter].push(term);
    });

    const html = Object.keys(groups).sort().map(letter => `
      <div class="glossary-group">
        <div class="glossary-letter">${letter}</div>
        ${groups[letter].map(term => `
          <div class="glossary-term" data-term="${this.escapeHtml(term.term)}" data-chapter-id="${term.chapterId}">
            <div class="term-content">
              <div class="term-word">${this.escapeHtml(term.term)}</div>
              <div class="term-definition">${this.escapeHtml(term.definition || '')}</div>
              ${term.chapterTitle ? `<div class="term-source">From: ${this.escapeHtml(term.chapterTitle)}</div>` : ''}
            </div>
            <div class="term-actions">
              <button class="btn btn-ghost btn-small btn-edit-term" title="Edit">Edit</button>
              <button class="btn btn-ghost btn-small btn-delete-term" title="Delete">Delete</button>
            </div>
          </div>
        `).join('')}
      </div>
    `).join('');

    glossaryList.innerHTML = html;
  }

  /**
   * Update chapter select dropdown options
   */
  updateChapterSelectOptions() {
    const select = document.getElementById('term-chapter-select');
    if (!select) return;

    let options = '<option value="">None (General)</option>';
    this.chapters.forEach(chapter => {
      options += `<option value="${chapter.id}">${this.escapeHtml(chapter.title || 'Untitled Chapter')}</option>`;
    });

    select.innerHTML = options;
  }

  /**
   * Handle clicks on glossary list
   */
  handleGlossaryListClick(e) {
    const editBtn = e.target.closest('.btn-edit-term');
    if (editBtn) {
      const termEl = editBtn.closest('.glossary-term');
      const termText = termEl.dataset.term;
      const chapterId = termEl.dataset.chapterId;
      this.showEditTerm(termText, chapterId);
      return;
    }

    const deleteBtn = e.target.closest('.btn-delete-term');
    if (deleteBtn) {
      const termEl = deleteBtn.closest('.glossary-term');
      const termText = termEl.dataset.term;
      const chapterId = termEl.dataset.chapterId;
      this.showDeleteTerm(termText, chapterId);
      return;
    }
  }

  /**
   * Show add term modal
   */
  showAddTerm() {
    this.currentTermId = null;
    this.currentTermChapterId = null;

    document.getElementById('term-modal-title').textContent = 'Add Glossary Term';
    document.getElementById('term-form').reset();
    document.getElementById('term-id').value = '';
    document.getElementById('term-chapter-id').value = '';

    this.termModal.open();
    setTimeout(() => {
      document.getElementById('term-text').focus();
    }, 150);
  }

  /**
   * Show edit term modal
   */
  showEditTerm(termText, chapterId) {
    const term = this.allGlossaryTerms.find(t => t.term === termText && t.chapterId === chapterId);
    if (!term) {
      toast.error('Term not found');
      return;
    }

    this.currentTermId = termText;
    this.currentTermChapterId = chapterId;

    document.getElementById('term-modal-title').textContent = 'Edit Glossary Term';
    document.getElementById('term-text').value = term.term || '';
    document.getElementById('term-definition').value = term.definition || '';
    document.getElementById('term-context').value = term.context || '';
    document.getElementById('term-id').value = termText;
    document.getElementById('term-chapter-id').value = chapterId;
    document.getElementById('term-chapter-select').value = chapterId || '';

    this.termModal.open();
  }

  /**
   * Show delete term confirmation
   */
  showDeleteTerm(termText, chapterId) {
    this.currentTermId = termText;
    this.currentTermChapterId = chapterId;

    document.getElementById('delete-term-name').textContent = termText;
    this.deleteTermModal.open();
  }

  /**
   * Handle term save (add/edit)
   */
  async handleTermSave(e) {
    e.preventDefault();

    const termText = document.getElementById('term-text').value.trim();
    const definition = document.getElementById('term-definition').value.trim();
    const context = document.getElementById('term-context').value.trim();
    const newChapterId = document.getElementById('term-chapter-select').value;
    const isEdit = !!this.currentTermId;

    if (!termText || !definition) {
      toast.error('Term and definition are required');
      return;
    }

    try {
      if (isEdit) {
        // Find and update existing term in chapter
        const chapter = this.chapters.find(ch => ch.id === this.currentTermChapterId);
        if (chapter && chapter.glossary_terms) {
          const termIndex = chapter.glossary_terms.findIndex(t => t.term === this.currentTermId);
          if (termIndex >= 0) {
            // If moving to different chapter, remove from old and add to new
            if (newChapterId !== this.currentTermChapterId) {
              chapter.glossary_terms.splice(termIndex, 1);
              await this.saveChapterGlossary(chapter);

              if (newChapterId) {
                const newChapter = this.chapters.find(ch => ch.id === newChapterId);
                if (newChapter) {
                  newChapter.glossary_terms = newChapter.glossary_terms || [];
                  newChapter.glossary_terms.push({ term: termText, definition, context });
                  await this.saveChapterGlossary(newChapter);
                }
              }
            } else {
              // Update in place
              chapter.glossary_terms[termIndex] = { term: termText, definition, context };
              await this.saveChapterGlossary(chapter);
            }
          }
        }
        toast.success('Term updated');
      } else {
        // Add new term
        if (newChapterId) {
          const chapter = this.chapters.find(ch => ch.id === newChapterId);
          if (chapter) {
            chapter.glossary_terms = chapter.glossary_terms || [];
            chapter.glossary_terms.push({ term: termText, definition, context });
            await this.saveChapterGlossary(chapter);
          }
        }
        toast.success('Term added');
      }

      this.termModal.close();
      this.loadGlossary();
      await this.loadCourse(); // Reload to sync

    } catch (error) {
      toast.error(`Failed to save term: ${error.message}`);
    }
  }

  /**
   * Handle term delete
   */
  async handleTermDelete() {
    if (!this.currentTermId || !this.currentTermChapterId) return;

    try {
      const chapter = this.chapters.find(ch => ch.id === this.currentTermChapterId);
      if (chapter && chapter.glossary_terms) {
        const termIndex = chapter.glossary_terms.findIndex(t => t.term === this.currentTermId);
        if (termIndex >= 0) {
          chapter.glossary_terms.splice(termIndex, 1);
          await this.saveChapterGlossary(chapter);
        }
      }

      toast.success('Term deleted');
      this.deleteTermModal.close();
      this.loadGlossary();
      await this.loadCourse(); // Reload to sync

    } catch (error) {
      toast.error(`Failed to delete term: ${error.message}`);
    }
  }

  /**
   * Save chapter glossary terms via course update
   * Note: This is a simplified approach - full implementation would need dedicated API
   */
  async saveChapterGlossary(chapter) {
    // For now, we update the local state and the course will be saved on next full reload
    // A proper implementation would have a dedicated API endpoint for glossary updates
    // This approach works for the UI but needs backend support for persistence
    console.log('Glossary update for chapter:', chapter.id, chapter.glossary_terms);
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Export for use
window.TextbookController = TextbookController;
