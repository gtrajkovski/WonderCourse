/**
 * Publish Controller - Course validation and export management
 */
class PublishController {
  constructor() {
    this.courseId = null;
    this.validationData = null;
    this.isPublishable = false;
    this.errorCount = 0;
    this.previewModal = null;
    this.forceExportModal = null;
    this.currentFormat = null;
  }

  init() {
    // Get course ID from data attribute
    const publishContainer = document.querySelector('.publish');
    if (!publishContainer) {
      console.error('Publish container not found');
      return;
    }
    this.courseId = publishContainer.dataset.courseId;

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
      this.bindHelpHandlers();
    }

    // Initialize modals
    this.previewModal = new Modal('preview-modal');
    this.forceExportModal = new Modal('force-export-modal');

    // Bind event handlers
    this.bindEventHandlers();

    // Load validation on init
    this.loadValidation();
  }

  bindEventHandlers() {
    // Refresh validation button
    const btnRefresh = document.getElementById('btn-refresh-validation');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.handleRefreshValidation());
    }

    // Export card buttons (event delegation)
    const exportGrid = document.getElementById('export-grid');
    if (exportGrid) {
      exportGrid.addEventListener('click', (e) => {
        const previewBtn = e.target.closest('.btn-preview');
        const downloadBtn = e.target.closest('.btn-download');

        if (previewBtn) {
          const format = previewBtn.dataset.format;
          this.handlePreview(format);
        } else if (downloadBtn) {
          const format = downloadBtn.dataset.format;
          this.handleDownload(format);
        }
      });
    }

    // Preview modal download button
    const btnPreviewDownload = document.getElementById('btn-preview-download');
    if (btnPreviewDownload) {
      btnPreviewDownload.addEventListener('click', () => {
        if (this.currentFormat) {
          this.previewModal.close();
          this.handleDownload(this.currentFormat);
        }
      });
    }

    // Force export button
    const btnForceExport = document.getElementById('btn-force-export');
    if (btnForceExport) {
      btnForceExport.addEventListener('click', () => {
        this.forceExportModal.close();
        this.triggerDownload(this.currentFormat, true);
      });
    }
  }

  async loadValidation() {
    const loadingEl = document.getElementById('validation-loading');
    const resultsEl = document.getElementById('validation-results');

    // Show loading state
    if (loadingEl) loadingEl.style.display = 'flex';
    if (resultsEl) resultsEl.style.display = 'none';

    try {
      this.validationData = await api.get(`/courses/${this.courseId}/validate`);
      this.isPublishable = this.validationData.is_publishable;

      // Render validation results
      this.renderValidation(this.validationData);

      // Initialize and update export card states
      this.initExportCards();
    } catch (error) {
      console.error('Failed to load validation:', error);
      toast.error(`Failed to load validation: ${error.message}`);
    } finally {
      // Hide loading, show results
      if (loadingEl) loadingEl.style.display = 'none';
      if (resultsEl) resultsEl.style.display = 'block';
    }
  }

  renderValidation(data) {
    // Render overall status badge
    const statusBadge = document.getElementById('validation-status-badge');
    if (statusBadge) {
      statusBadge.classList.remove('status-ready', 'status-warning', 'status-error');

      let statusClass, statusText;
      if (data.summary.total_errors > 0) {
        statusClass = 'status-error';
        statusText = 'Not Ready';
      } else if (data.summary.total_warnings > 0) {
        statusClass = 'status-warning';
        statusText = 'Has Warnings';
      } else {
        statusClass = 'status-ready';
        statusText = 'Ready to Publish';
      }

      statusBadge.classList.add(statusClass);
      statusBadge.querySelector('.status-text').textContent = statusText;
    }

    // Render counts
    const countsEl = document.getElementById('validation-counts');
    if (countsEl) {
      countsEl.innerHTML = `
        <div class="validation-count count-error">
          <span>${data.summary.total_errors}</span> errors
        </div>
        <div class="validation-count count-warning">
          <span>${data.summary.total_warnings}</span> warnings
        </div>
        <div class="validation-count count-suggestion">
          <span>${data.summary.total_suggestions}</span> suggestions
        </div>
      `;
    }

    // Render validator groups
    const groupsEl = document.getElementById('validator-groups');
    if (groupsEl) {
      groupsEl.innerHTML = '';

      for (const [name, result] of Object.entries(data.validators)) {
        const group = this.renderValidatorGroup(name, result);
        groupsEl.appendChild(group);
      }
    }
  }

  renderValidatorGroup(name, result) {
    const group = document.createElement('div');
    group.className = 'validator-group';
    group.dataset.validator = name;

    // Determine icon class and count
    let iconClass = 'icon-valid';
    let iconSymbol = '\u2713'; // checkmark
    let issueCount = 0;

    const errorCount = result.errors ? result.errors.length : 0;
    const warningCount = result.warnings ? result.warnings.length : 0;
    const suggestionCount = result.suggestions ? result.suggestions.length : 0;

    if (errorCount > 0) {
      iconClass = 'icon-error';
      iconSymbol = errorCount.toString();
      issueCount = errorCount;
    } else if (warningCount > 0) {
      iconClass = 'icon-warning';
      iconSymbol = warningCount.toString();
      issueCount = warningCount;
    } else if (suggestionCount > 0) {
      iconSymbol = suggestionCount.toString();
    }

    // Format validator name for display
    const displayName = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    // Build count summary
    const countParts = [];
    if (errorCount > 0) countParts.push(`${errorCount} error${errorCount > 1 ? 's' : ''}`);
    if (warningCount > 0) countParts.push(`${warningCount} warning${warningCount > 1 ? 's' : ''}`);
    if (suggestionCount > 0) countParts.push(`${suggestionCount} suggestion${suggestionCount > 1 ? 's' : ''}`);
    const countSummary = countParts.length > 0 ? countParts.join(', ') : 'All checks passed';

    group.innerHTML = `
      <div class="validator-header">
        <div class="validator-icon ${iconClass}">${iconSymbol}</div>
        <span class="validator-name">${displayName}</span>
        <span class="validator-summary">${countSummary}</span>
        <span class="validator-toggle">\u25BC</span>
      </div>
      <div class="validator-issues">
        ${this.renderIssueList(result)}
      </div>
    `;

    // Toggle expand/collapse on header click
    const header = group.querySelector('.validator-header');
    header.addEventListener('click', () => {
      group.classList.toggle('expanded');
    });

    return group;
  }

  renderIssueList(result) {
    const allIssues = [];

    // Collect all issues with type
    if (result.errors) {
      result.errors.forEach(msg => allIssues.push({ type: 'error', message: msg }));
    }
    if (result.warnings) {
      result.warnings.forEach(msg => allIssues.push({ type: 'warning', message: msg }));
    }
    if (result.suggestions) {
      result.suggestions.forEach(msg => allIssues.push({ type: 'suggestion', message: msg }));
    }

    if (allIssues.length === 0) {
      return '<p class="no-issues">All checks passed</p>';
    }

    const items = allIssues.map(issue => `
      <li class="issue-item issue-${issue.type}">
        <span class="issue-icon"></span>
        <span class="issue-text">${issue.message}</span>
      </li>
    `).join('');

    return `<ul class="issue-list">${items}</ul>`;
  }

  handleRefreshValidation() {
    toast.info('Refreshing validation...');
    this.loadValidation();
  }

  async checkPublishable() {
    try {
      const data = await api.get(`/courses/${this.courseId}/publishable`);
      this.isPublishable = data.is_publishable;
      this.errorCount = data.error_count;
      this.updateExportCards();
      return data;
    } catch (error) {
      console.error('Failed to check publishable status:', error);
      return { is_publishable: false, error_count: -1 };
    }
  }

  toggleValidator(name) {
    const group = document.querySelector(`.validator-group[data-validator="${name}"]`);
    if (group) {
      group.classList.toggle('expanded');
    }
  }

  initExportCards() {
    // Initialize export card states based on current validation
    this.updateExportCards();
  }

  updateExportCards() {
    const cards = document.querySelectorAll('.export-card');
    cards.forEach(card => {
      const format = card.dataset.format;
      const downloadBtn = card.querySelector('.btn-download');
      const previewBtn = card.querySelector('.btn-preview');

      if (this.isPublishable) {
        card.classList.remove('has-issues');
        if (downloadBtn) {
          downloadBtn.classList.remove('btn-danger');
          downloadBtn.classList.add('btn-primary');
        }
      } else {
        card.classList.add('has-issues');
        if (downloadBtn) {
          downloadBtn.classList.remove('btn-primary');
          downloadBtn.classList.add('btn-warning');
        }
      }
      // Cards are never fully disabled - force export is always available
    });
  }

  updateExportCardState(format, enabled, message) {
    const card = document.querySelector(`.export-card[data-format="${format}"]`);
    if (!card) return;

    const statusEl = card.querySelector('.export-card-status');
    if (enabled) {
      card.classList.remove('disabled');
      if (statusEl) statusEl.textContent = message || 'Ready';
    } else {
      if (statusEl) statusEl.textContent = message || 'Issues found';
    }
  }

  async handlePreview(format) {
    this.currentFormat = format;

    // Open modal and show loading
    this.previewModal.open();
    const loadingEl = document.getElementById('preview-loading');
    const contentEl = document.getElementById('preview-content');

    if (loadingEl) loadingEl.style.display = 'flex';
    if (contentEl) contentEl.style.display = 'none';

    // Update modal title
    const formatNames = {
      instructor: 'Instructor Package',
      lms: 'LMS Manifest',
      docx: 'Textbook',
      scorm: 'SCORM Package'
    };
    const titleEl = document.getElementById('preview-modal-title');
    if (titleEl) {
      titleEl.textContent = `${formatNames[format] || format} Preview`;
    }

    try {
      const data = await api.get(`/courses/${this.courseId}/export/preview?format=${format}`);
      this.renderPreviewContent(format, data);
    } catch (error) {
      console.error('Failed to load preview:', error);
      if (contentEl) {
        contentEl.innerHTML = `<p class="error-message">Failed to load preview: ${error.message}</p>`;
        contentEl.style.display = 'block';
      }
    } finally {
      if (loadingEl) loadingEl.style.display = 'none';
    }
  }

  renderPreviewContent(format, data) {
    const contentEl = document.getElementById('preview-content');
    if (!contentEl) return;

    let html = `
      <div class="preview-info">
        <div class="preview-info-row">
          <span class="preview-info-label">Course:</span>
          <span class="preview-info-value">${data.course_title}</span>
        </div>
        <div class="preview-info-row">
          <span class="preview-info-label">Format:</span>
          <span class="preview-info-value">${format.toUpperCase()}</span>
        </div>
        <div class="preview-info-row">
          <span class="preview-info-label">Ready:</span>
          <span class="preview-info-value">${data.ready ? 'Yes' : 'No'}</span>
        </div>
      </div>
    `;

    // File list
    if (data.files && data.files.length > 0) {
      html += `
        <div class="preview-files">
          <h4>Files to be included (${data.files.length}):</h4>
          <ul class="file-list">
            ${data.files.map(file => `<li>${file}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // Warnings
    if (data.warnings && data.warnings.length > 0) {
      html += `
        <div class="preview-warnings">
          <h4>Warnings:</h4>
          <ul>
            ${data.warnings.map(w => `<li>${w}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // Validation errors
    if (data.validation_errors && data.validation_errors.length > 0) {
      html += `
        <div class="preview-warnings" style="background: var(--error-bg);">
          <h4 style="color: var(--error);">Validation Issues:</h4>
          <ul style="color: var(--error);">
            ${data.validation_errors.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    contentEl.innerHTML = html;
    contentEl.style.display = 'block';
  }

  handleDownload(format, force = false) {
    this.currentFormat = format;

    // If not publishable and not forcing, show confirmation
    if (!this.isPublishable && !force) {
      this.showForceExportWarning(format);
      return;
    }

    // Trigger download
    this.triggerDownload(format, force);
  }

  showForceExportWarning(format) {
    // Populate issues list
    const issuesEl = document.getElementById('force-export-issues');
    if (issuesEl && this.validationData) {
      const errors = [];
      for (const [name, result] of Object.entries(this.validationData.validators)) {
        if (result.errors) {
          result.errors.forEach(msg => errors.push(msg));
        }
      }

      if (errors.length > 0) {
        issuesEl.innerHTML = `<ul>${errors.map(e => `<li>${e}</li>`).join('')}</ul>`;
      } else {
        issuesEl.innerHTML = '<p>Course has warnings but no critical errors.</p>';
      }
    }

    // Show modal
    this.forceExportModal.open();
  }

  triggerDownload(format, force = false) {
    const forceParam = force ? '?force=true' : '';
    const url = `/api/courses/${this.courseId}/export/${format}${forceParam}`;

    // Create hidden anchor and click it
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = '';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);

    toast.success('Download started');
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

      // Handle validator clicks for detailed help
      const validatorHeader = e.target.closest('.validator-header');
      if (validatorHeader && e.shiftKey) {
        // Shift-click on validator shows contextual help
        e.preventDefault();
        const group = validatorHeader.closest('.validator-group');
        if (group) {
          const validatorName = group.dataset.validator;
          this.showValidatorHelp(validatorName);
        }
      }
    });
  }

  showValidatorHelp(validatorName) {
    if (!window.help) return;

    const helpContent = {
      'structure_validation': {
        title: 'Structure Validation',
        content: `
          <p>Validates that your course meets Coursera's structural requirements:</p>
          <ul>
            <li><strong>Module count:</strong> Minimum 2 modules required</li>
            <li><strong>Lesson count:</strong> Each module needs lessons</li>
            <li><strong>Activity count:</strong> Each lesson needs activities</li>
            <li><strong>Duration:</strong> Course must be between 15-600 minutes</li>
          </ul>
        `
      },
      'outcome_coverage': {
        title: 'Outcome Coverage',
        content: `
          <p>Checks alignment between learning outcomes and activities:</p>
          <ul>
            <li><strong>Coverage score:</strong> Percentage of outcomes addressed</li>
            <li><strong>Mapping quality:</strong> How well activities align with outcomes</li>
            <li><strong>Bloom's distribution:</strong> Cognitive complexity balance</li>
          </ul>
          <p>Good alignment ensures learners can achieve stated outcomes.</p>
        `
      },
      'blooms_distribution': {
        title: "Bloom's Distribution",
        content: `
          <p>Analyzes cognitive complexity across your course:</p>
          <ul>
            <li><strong>Remember/Understand:</strong> 30-40% (foundational)</li>
            <li><strong>Apply/Analyze:</strong> 40-50% (application)</li>
            <li><strong>Evaluate/Create:</strong> 10-20% (higher-order)</li>
          </ul>
          <p>Balanced distribution supports progressive learning.</p>
        `
      },
      'distractor_quality': {
        title: 'Distractor Quality',
        content: `
          <p>Evaluates quiz question quality:</p>
          <ul>
            <li><strong>Option count:</strong> 3-5 options per question</li>
            <li><strong>Distractor plausibility:</strong> Wrong answers should be believable</li>
            <li><strong>Feedback quality:</strong> Explanations for why answers are correct/incorrect</li>
          </ul>
          <p>Quality distractors test understanding, not just memorization.</p>
        `
      }
    };

    const help = helpContent[validatorName];
    if (help) {
      window.help.showPanel(validatorName, {
        title: help.title,
        content: help.content
      });
    } else {
      window.help.showPanel('validation-help', {
        title: 'Validation Help',
        content: `
          <p>Click on a validator to see its details.</p>
          <p><strong>Shift-click</strong> on a validator header for detailed help.</p>
          <p>Fix all errors before publishing. Warnings are optional but recommended.</p>
        `
      });
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const publishController = new PublishController();
  publishController.init();

  // Export for debugging
  window.publishController = publishController;
});
