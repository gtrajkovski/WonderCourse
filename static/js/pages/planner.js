/**
 * Planner Controller - Course setup, outcomes, and blueprint generation
 */
class PlannerController {
  constructor(courseId) {
    this.courseId = courseId;
    this.outcomeModal = null;
    this.deleteOutcomeModal = null;
    this.currentOutcomeId = null;
    this.outcomeToDelete = null;
    this.lastBlueprint = null;
  }

  init() {
    // Initialize modals
    this.outcomeModal = new Modal('outcome-modal');
    this.deleteOutcomeModal = new Modal('delete-outcome-modal');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
      this.bindHelpHandlers();
    }

    // Initialize tabs
    this.initTabs();

    // Load standards profiles
    this.loadStandardsProfiles();

    // Bind event handlers
    this.bindMetadataHandlers();
    this.bindOutcomeHandlers();
    this.bindBlueprintHandlers();

    // Add keyboard shortcut for help
    document.addEventListener('keydown', (e) => {
      if (e.key === 'F1') {
        e.preventDefault();
        this.showContextualHelp();
      }
    });
  }

  // ===========================
  // Standards Profiles
  // ===========================

  async loadStandardsProfiles() {
    const select = document.getElementById('standards-profile');
    if (!select) return;

    const currentValue = select.dataset.current || 'std_coursera';

    try {
      const profiles = await api.get('/standards');

      select.innerHTML = profiles.map(profile => {
        const selected = profile.id === currentValue ? 'selected' : '';
        const badge = profile.is_system_preset ? ' (preset)' : '';
        return `<option value="${profile.id}" ${selected}>${this.escapeHtml(profile.name)}${badge}</option>`;
      }).join('');
    } catch (error) {
      // If standards API fails, show a fallback option
      select.innerHTML = '<option value="std_coursera">Coursera Short Course (default)</option>';
      console.warn('Could not load standards profiles:', error.message);
    }
  }

  // ===========================
  // Tab Navigation
  // ===========================

  initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        this.switchTab(tabId);
      });
    });
  }

  switchTab(tabId) {
    // Update button states
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update section visibility
    document.querySelectorAll('.planner-section').forEach(section => {
      section.classList.toggle('active', section.id === `tab-${tabId}`);
    });

    // Load existing blueprint when switching to blueprint tab
    if (tabId === 'blueprint' && !this.lastBlueprint) {
      this.loadExistingBlueprint();
    }
  }

  /**
   * Load existing accepted blueprint from the course
   */
  async loadExistingBlueprint() {
    try {
      const response = await api.get(`/courses/${this.courseId}/blueprint`);

      if (response.has_blueprint && response.blueprint) {
        this.lastBlueprint = response.blueprint;

        // Render with a "valid" validation since it was already accepted
        this.renderBlueprintPreview({
          blueprint: response.blueprint,
          validation: { is_valid: true, errors: [], warnings: [], suggestions: [] }
        });

        // Show preview and action buttons
        const previewDiv = document.getElementById('blueprint-preview');
        previewDiv.style.display = 'block';
        document.getElementById('btn-accept-blueprint').style.display = 'inline-block';
        document.getElementById('btn-refine-toggle').style.display = 'inline-block';

        // Show info that this is a saved blueprint
        const statusDiv = document.getElementById('blueprint-status');
        if (statusDiv) {
          statusDiv.innerHTML = `
            <div class="blueprint-saved-notice" style="padding: 0.75rem; background: rgba(52, 152, 219, 0.1); border-radius: 8px; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
              <span style="color: var(--accent);">&#x2713;</span>
              <span>This blueprint was previously accepted and applied. You can regenerate or refine it.</span>
            </div>
          `;
          statusDiv.style.display = 'block';
        }
      }
    } catch (error) {
      // Silently fail - no existing blueprint
      console.log('No existing blueprint found');
    }
  }

  // ===========================
  // Course Metadata
  // ===========================

  bindMetadataHandlers() {
    const form = document.getElementById('metadata-form');
    if (form) {
      form.addEventListener('submit', (e) => this.handleMetadataSave(e));
    }
  }

  async handleMetadataSave(e) {
    e.preventDefault();

    const saveBtn = document.getElementById('btn-save-metadata');
    const saveIndicator = document.getElementById('save-indicator');
    const originalText = saveBtn.textContent;

    // Gather form values
    const title = document.getElementById('course-title').value.trim();
    const description = document.getElementById('course-description').value.trim();
    const audienceLevel = document.getElementById('audience-level').value;
    const targetDuration = parseInt(document.getElementById('target-duration').value, 10);
    const modality = document.getElementById('modality').value;
    const language = document.getElementById('course-language').value;
    const standardsProfileId = document.getElementById('standards-profile')?.value || null;
    const prerequisites = document.getElementById('prerequisites').value.trim();
    const toolsRaw = document.getElementById('tools').value.trim();
    const tools = toolsRaw ? toolsRaw.split(',').map(t => t.trim()).filter(t => t) : [];

    // Validate required fields
    if (!title) {
      toast.error('Course title is required');
      document.getElementById('course-title').focus();
      return;
    }

    // Show saving state
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    if (saveIndicator) {
      saveIndicator.textContent = 'Saving...';
      saveIndicator.className = 'save-indicator saving';
    }

    try {
      const data = {
        title,
        description,
        audience_level: audienceLevel,
        target_duration_minutes: targetDuration,
        modality,
        language,
        standards_profile_id: standardsProfileId,
        prerequisites: prerequisites || null,
        tools
      };

      await api.put(`/courses/${this.courseId}`, data);

      toast.success('Course settings saved successfully');
      if (saveIndicator) {
        saveIndicator.textContent = 'Saved';
        saveIndicator.className = 'save-indicator saved';
        setTimeout(() => {
          saveIndicator.textContent = '';
          saveIndicator.className = 'save-indicator';
        }, 3000);
      }
    } catch (error) {
      toast.error(`Error saving course: ${error.message}`);
      if (saveIndicator) {
        saveIndicator.textContent = '';
        saveIndicator.className = 'save-indicator';
      }
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = originalText;
    }
  }

  // ===========================
  // Learning Outcomes
  // ===========================

  bindOutcomeHandlers() {
    // Add outcome button
    const addBtn = document.getElementById('btn-add-outcome');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.showAddOutcome());
    }

    // Outcome form submit
    const form = document.getElementById('outcome-form');
    if (form) {
      form.addEventListener('submit', (e) => this.handleOutcomeSave(e));
    }

    // Delete confirmation
    const confirmDeleteBtn = document.getElementById('btn-confirm-delete-outcome');
    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener('click', () => this.handleOutcomeDeleteConfirm());
    }

    // Use event delegation for edit/delete buttons
    const outcomesList = document.getElementById('outcomes-list');
    if (outcomesList) {
      outcomesList.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit-outcome');
        const deleteBtn = e.target.closest('.btn-delete-outcome');

        if (editBtn) {
          const outcomeId = editBtn.dataset.outcomeId;
          this.showEditOutcome(outcomeId);
        } else if (deleteBtn) {
          const outcomeId = deleteBtn.dataset.outcomeId;
          this.showDeleteOutcome(outcomeId);
        }
      });
    }
  }

  showAddOutcome() {
    this.currentOutcomeId = null;

    // Reset form
    const form = document.getElementById('outcome-form');
    if (form) form.reset();

    // Update modal title
    const modalTitle = document.getElementById('outcome-modal-title');
    if (modalTitle) modalTitle.textContent = 'Add Learning Outcome';

    // Set default bloom level
    const bloomSelect = document.getElementById('outcome-bloom');
    if (bloomSelect) bloomSelect.value = 'apply';

    // Open modal
    this.outcomeModal.open();

    // Focus first field
    setTimeout(() => {
      const audienceInput = document.getElementById('outcome-audience');
      if (audienceInput) audienceInput.focus();
    }, 150);
  }

  async showEditOutcome(outcomeId) {
    this.currentOutcomeId = outcomeId;

    try {
      // Fetch outcome data
      const outcomes = await api.get(`/courses/${this.courseId}/outcomes`);
      const outcome = outcomes.find(o => o.id === outcomeId);

      if (!outcome) {
        toast.error('Outcome not found');
        return;
      }

      // Populate form
      document.getElementById('outcome-audience').value = outcome.audience || '';
      document.getElementById('outcome-behavior').value = outcome.behavior || '';
      document.getElementById('outcome-condition').value = outcome.condition || '';
      document.getElementById('outcome-degree').value = outcome.degree || '';
      document.getElementById('outcome-bloom').value = outcome.bloom_level || 'apply';

      // Update modal title
      const modalTitle = document.getElementById('outcome-modal-title');
      if (modalTitle) modalTitle.textContent = 'Edit Learning Outcome';

      // Open modal
      this.outcomeModal.open();
    } catch (error) {
      toast.error(`Error loading outcome: ${error.message}`);
    }
  }

  async handleOutcomeSave(e) {
    e.preventDefault();

    const saveBtn = document.getElementById('btn-save-outcome');
    const originalText = saveBtn.textContent;

    // Gather form values
    const audience = document.getElementById('outcome-audience').value.trim();
    const behavior = document.getElementById('outcome-behavior').value.trim();
    const condition = document.getElementById('outcome-condition').value.trim();
    const degree = document.getElementById('outcome-degree').value.trim();
    const bloomLevel = document.getElementById('outcome-bloom').value;

    // Validate required fields
    if (!audience || !behavior) {
      toast.error('Audience and Behavior are required');
      return;
    }

    // Show saving state
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
      const data = {
        audience,
        behavior,
        condition,
        degree,
        bloom_level: bloomLevel
      };

      if (this.currentOutcomeId) {
        // Update existing
        await api.put(`/courses/${this.courseId}/outcomes/${this.currentOutcomeId}`, data);
        toast.success('Learning outcome updated');
      } else {
        // Create new
        await api.post(`/courses/${this.courseId}/outcomes`, data);
        toast.success('Learning outcome added');
      }

      // Close modal and reload outcomes
      this.outcomeModal.close();
      await this.reloadOutcomes();
    } catch (error) {
      toast.error(`Error saving outcome: ${error.message}`);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = originalText;
    }
  }

  showDeleteOutcome(outcomeId) {
    this.outcomeToDelete = outcomeId;
    this.deleteOutcomeModal.open();
  }

  async handleOutcomeDeleteConfirm() {
    if (!this.outcomeToDelete) return;

    const deleteBtn = document.getElementById('btn-confirm-delete-outcome');
    const originalText = deleteBtn.textContent;

    deleteBtn.disabled = true;
    deleteBtn.textContent = 'Deleting...';

    try {
      await api.delete(`/courses/${this.courseId}/outcomes/${this.outcomeToDelete}`);

      toast.success('Learning outcome deleted');
      this.deleteOutcomeModal.close();
      await this.reloadOutcomes();
    } catch (error) {
      toast.error(`Error deleting outcome: ${error.message}`);
    } finally {
      this.outcomeToDelete = null;
      deleteBtn.disabled = false;
      deleteBtn.textContent = originalText;
    }
  }

  async reloadOutcomes() {
    try {
      const outcomes = await api.get(`/courses/${this.courseId}/outcomes`);
      this.renderOutcomes(outcomes);
    } catch (error) {
      toast.error(`Error loading outcomes: ${error.message}`);
    }
  }

  renderOutcomes(outcomes) {
    const container = document.getElementById('outcomes-list');
    if (!container) return;

    if (!outcomes || outcomes.length === 0) {
      container.innerHTML = `
        <div class="empty-outcomes">
          <p>No learning outcomes defined yet.</p>
          <p class="text-muted">Learning outcomes help generate a more focused course structure.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = outcomes.map(outcome => `
      <div class="outcome-item" data-outcome-id="${outcome.id}">
        <div class="outcome-content">
          <span class="bloom-badge bloom-${outcome.bloom_level}">${this.capitalizeFirst(outcome.bloom_level)}</span>
          <p class="outcome-text">
            <strong>${this.escapeHtml(outcome.audience)}</strong> will be able to
            <strong>${this.escapeHtml(outcome.behavior)}</strong>
            ${outcome.condition ? this.escapeHtml(outcome.condition) : ''}
            ${outcome.degree ? this.escapeHtml(outcome.degree) : ''}.
          </p>
        </div>
        <div class="outcome-actions">
          <button class="btn btn-secondary btn-small btn-edit-outcome" data-outcome-id="${outcome.id}">Edit</button>
          <button class="btn btn-danger btn-small btn-delete-outcome" data-outcome-id="${outcome.id}">Delete</button>
        </div>
      </div>
    `).join('');
  }

  // ===========================
  // Blueprint Generation
  // ===========================

  bindBlueprintHandlers() {
    const generateBtn = document.getElementById('btn-generate-blueprint');
    if (generateBtn) {
      generateBtn.addEventListener('click', () => this.handleGenerateBlueprint());
    }

    const acceptBtn = document.getElementById('btn-accept-blueprint');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => this.handleAcceptBlueprint());
    }

    const refineToggleBtn = document.getElementById('btn-refine-toggle');
    if (refineToggleBtn) {
      refineToggleBtn.addEventListener('click', () => this.toggleRefineSection());
    }

    const refineBtn = document.getElementById('btn-refine-blueprint');
    if (refineBtn) {
      refineBtn.addEventListener('click', () => this.handleRefineBlueprint());
    }

    // Paste/Upload blueprint handlers
    const pasteBtn = document.getElementById('btn-paste-blueprint');
    if (pasteBtn) {
      pasteBtn.addEventListener('click', () => this.togglePasteSection());
    }

    const cancelPasteBtn = document.getElementById('btn-cancel-paste');
    if (cancelPasteBtn) {
      cancelPasteBtn.addEventListener('click', () => this.togglePasteSection(false));
    }

    const loadBtn = document.getElementById('btn-load-blueprint');
    if (loadBtn) {
      loadBtn.addEventListener('click', () => this.handleLoadBlueprint());
    }

    const fileInput = document.getElementById('blueprint-file-input');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
    }
  }

  togglePasteSection(show = null) {
    const section = document.getElementById('paste-blueprint-section');
    const pasteBtn = document.getElementById('btn-paste-blueprint');
    if (show === null) {
      show = section.style.display === 'none';
    }
    section.style.display = show ? 'block' : 'none';
    pasteBtn.textContent = show ? 'Cancel' : 'Paste/Upload Blueprint';
  }

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById('blueprint-json').value = e.target.result;
      toast.success('File loaded. Click "Load Blueprint" to apply.');
    };
    reader.onerror = () => {
      toast.error('Error reading file');
    };
    reader.readAsText(file);
  }

  async handleLoadBlueprint() {
    const jsonText = document.getElementById('blueprint-json').value.trim();
    if (!jsonText) {
      toast.error('Please paste or upload blueprint JSON');
      return;
    }

    let blueprint;
    try {
      blueprint = JSON.parse(jsonText);
    } catch (e) {
      toast.error('Invalid JSON format');
      return;
    }

    // Validate and preview the blueprint
    this.lastBlueprint = blueprint;
    this.renderBlueprintPreview({
      blueprint: blueprint,
      validation: { is_valid: true, warnings: [], errors: [] }
    });

    // Show preview
    document.getElementById('paste-blueprint-section').style.display = 'none';
    document.getElementById('btn-paste-blueprint').textContent = 'Paste/Upload Blueprint';
    document.getElementById('blueprint-preview').style.display = 'block';
    document.getElementById('btn-accept-blueprint').style.display = 'inline-block';
    document.getElementById('btn-refine-toggle').style.display = 'inline-block';

    toast.success('Blueprint loaded. Review and click Accept to apply.');
  }

  async handleGenerateBlueprint() {
    const generateBtn = document.getElementById('btn-generate-blueprint');
    const statusDiv = document.getElementById('blueprint-status');
    const previewDiv = document.getElementById('blueprint-preview');

    // Show loading state
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    statusDiv.style.display = 'flex';
    previewDiv.style.display = 'none';

    try {
      const result = await api.post(`/courses/${this.courseId}/blueprint/generate`, {});

      this.lastBlueprint = result.blueprint;
      this.renderBlueprintPreview(result);

      // Hide status, show preview
      statusDiv.style.display = 'none';
      previewDiv.style.display = 'block';

      // Show action buttons
      document.getElementById('btn-accept-blueprint').style.display = 'inline-block';
      document.getElementById('btn-refine-toggle').style.display = 'inline-block';

      toast.success('Blueprint generated successfully');
    } catch (error) {
      toast.error(`Error generating blueprint: ${error.message}`);
      statusDiv.style.display = 'none';
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = 'Generate Blueprint';
    }
  }

  renderBlueprintPreview(result) {
    const blueprint = result.blueprint;
    const validation = result.validation;
    const contentDiv = document.getElementById('preview-content');
    const validationDiv = document.getElementById('preview-validation');

    // Render validation badge
    if (validation.is_valid) {
      validationDiv.innerHTML = '<span class="validation-badge valid">Valid</span>';
    } else {
      validationDiv.innerHTML = '<span class="validation-badge invalid">Has Issues</span>';
    }

    if (validation.warnings && validation.warnings.length > 0) {
      validationDiv.innerHTML += `<span class="validation-badge warning">${validation.warnings.length} Warning(s)</span>`;
    }

    // Count totals
    let lessonCount = 0;
    let activityCount = 0;
    blueprint.modules.forEach(mod => {
      lessonCount += mod.lessons.length;
      mod.lessons.forEach(les => {
        activityCount += les.activities ? les.activities.length : 0;
      });
    });

    // Render summary
    let html = `
      <div class="preview-summary">
        <div class="summary-item">
          <span class="count">${blueprint.modules.length}</span>
          <span class="label">Modules</span>
        </div>
        <div class="summary-item">
          <span class="count">${lessonCount}</span>
          <span class="label">Lessons</span>
        </div>
        <div class="summary-item">
          <span class="count">${activityCount}</span>
          <span class="label">Activities</span>
        </div>
      </div>
    `;

    // Render module structure
    blueprint.modules.forEach((mod, idx) => {
      html += `
        <div class="module-preview">
          <h5>Module ${idx + 1}: ${this.escapeHtml(mod.title)}</h5>
          <ul class="lesson-list">
      `;
      mod.lessons.forEach(les => {
        const actCount = les.activities ? les.activities.length : 0;
        html += `<li>${this.escapeHtml(les.title)}<span class="activity-count">(${actCount} activities)</span></li>`;
      });
      html += '</ul></div>';
    });

    // Render validation messages
    if (validation.errors && validation.errors.length > 0) {
      html += `
        <div class="validation-messages">
          <div class="validation-errors">
            <h5>Errors</h5>
            <ul class="validation-list">
              ${validation.errors.map(e => `<li>${this.escapeHtml(e)}</li>`).join('')}
            </ul>
          </div>
        </div>
      `;
    }

    if (validation.warnings && validation.warnings.length > 0) {
      html += `
        <div class="validation-messages">
          <div class="validation-warnings">
            <h5>Warnings</h5>
            <ul class="validation-list">
              ${validation.warnings.map(w => `<li>${this.escapeHtml(w)}</li>`).join('')}
            </ul>
          </div>
        </div>
      `;
    }

    contentDiv.innerHTML = html;
  }

  async handleAcceptBlueprint() {
    if (!this.lastBlueprint) {
      toast.error('No blueprint to accept');
      return;
    }

    const acceptBtn = document.getElementById('btn-accept-blueprint');
    const originalText = acceptBtn.textContent;

    acceptBtn.disabled = true;
    acceptBtn.textContent = 'Accepting...';

    try {
      const result = await api.post(`/courses/${this.courseId}/blueprint/accept`, {
        blueprint: this.lastBlueprint
      });

      toast.success(`Blueprint accepted: ${result.module_count} modules, ${result.lesson_count} lessons, ${result.activity_count} activities created`);

      // Navigate to builder page
      setTimeout(() => {
        window.location.href = `/courses/${this.courseId}/builder`;
      }, 1500);
    } catch (error) {
      toast.error(`Error accepting blueprint: ${error.message}`);
      acceptBtn.disabled = false;
      acceptBtn.textContent = originalText;
    }
  }

  toggleRefineSection() {
    const refineSection = document.getElementById('refine-section');
    if (refineSection.style.display === 'none') {
      refineSection.style.display = 'block';
      document.getElementById('refine-feedback').focus();
    } else {
      refineSection.style.display = 'none';
    }
  }

  async handleRefineBlueprint() {
    if (!this.lastBlueprint) {
      toast.error('No blueprint to refine');
      return;
    }

    const feedback = document.getElementById('refine-feedback').value.trim();
    if (!feedback) {
      toast.error('Please provide feedback for refinement');
      document.getElementById('refine-feedback').focus();
      return;
    }

    const refineBtn = document.getElementById('btn-refine-blueprint');
    const statusDiv = document.getElementById('blueprint-status');
    const originalText = refineBtn.textContent;

    refineBtn.disabled = true;
    refineBtn.textContent = 'Refining...';
    statusDiv.style.display = 'flex';
    document.querySelector('.status-text').textContent = 'Refining blueprint...';

    try {
      const result = await api.post(`/courses/${this.courseId}/blueprint/refine`, {
        blueprint: this.lastBlueprint,
        feedback: feedback
      });

      this.lastBlueprint = result.blueprint;
      this.renderBlueprintPreview(result);

      // Hide status
      statusDiv.style.display = 'none';

      // Clear feedback
      document.getElementById('refine-feedback').value = '';
      document.getElementById('refine-section').style.display = 'none';

      toast.success('Blueprint refined successfully');
    } catch (error) {
      toast.error(`Error refining blueprint: ${error.message}`);
      statusDiv.style.display = 'none';
    } finally {
      refineBtn.disabled = false;
      refineBtn.textContent = originalText;
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

  showContextualHelp() {
    // Show help based on current active tab
    const activeTab = document.querySelector('.tab-btn.active');
    if (!activeTab || !window.help) return;

    const tabId = activeTab.dataset.tab;
    if (tabId === 'outcomes') {
      window.help.showTerm('learning-outcome');
    } else if (tabId === 'blueprint') {
      window.help.showPanel('blueprint-generation', {
        title: 'Blueprint Generation Help',
        content: `
          <p>The AI blueprint generator creates a complete course structure with:</p>
          <ul>
            <li><strong>Modules:</strong> Major thematic units</li>
            <li><strong>Lessons:</strong> Focused learning sessions within each module</li>
            <li><strong>Activities:</strong> Individual content pieces (videos, readings, quizzes)</li>
          </ul>
          <p>The generator uses your course description and learning outcomes to create a pedagogically sound structure.</p>
        `
      });
    } else {
      window.help.showPanel('course-setup', {
        title: 'Course Setup Help',
        content: `
          <p>Define your course metadata to guide the AI generation process:</p>
          <ul>
            <li><strong>Title:</strong> Clear, descriptive course name</li>
            <li><strong>Description:</strong> What learners will achieve</li>
            <li><strong>Target Audience:</strong> Beginner, Intermediate, or Advanced</li>
            <li><strong>Duration:</strong> Total course length in minutes</li>
          </ul>
        `
      });
    }
  }

  // ===========================
  // Utility Methods
  // ===========================

  capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Initialize planner controller when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const plannerEl = document.querySelector('.planner');
  if (plannerEl) {
    const courseId = plannerEl.dataset.courseId;
    if (courseId) {
      const plannerController = new PlannerController(courseId);
      plannerController.init();

      // Export for debugging
      window.plannerController = plannerController;
    }
  }
});
