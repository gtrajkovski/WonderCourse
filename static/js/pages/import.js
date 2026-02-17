/**
 * Import Controller - Handles paste, file upload, URL fetch, and Google OAuth
 */
class ImportController {
  constructor(containerEl, courseId = null) {
    this.container = containerEl;
    this.courseId = courseId;
    this.currentFile = null;
    this.currentContent = null;
    this.analysisResult = null;

    this.init();
  }

  init() {
    this.setupTabs();
    this.setupPaste();
    this.setupDropzone();
    this.setupURLFetch();
    this.setupGoogleOAuth();
    this.setupActions();
  }

  /**
   * Tab switching
   */
  setupTabs() {
    const tabs = this.container.querySelectorAll('.import-tab');
    const sections = this.container.querySelectorAll('.import-section');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;

        // Update tabs
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Update sections
        sections.forEach(s => {
          if (s.dataset.section === targetTab) {
            s.classList.add('active');
          } else {
            s.classList.remove('active');
          }
        });
      });
    });
  }

  /**
   * Paste area handling
   */
  setupPaste() {
    const pasteInput = document.getElementById('paste-input');
    const charCount = this.container.querySelector('.char-count');
    const formatDetected = document.getElementById('format-detected');

    if (!pasteInput) return;

    pasteInput.addEventListener('input', (e) => {
      const content = e.target.value;
      charCount.textContent = `${content.length} characters`;

      // Simple format detection
      if (content.length > 0) {
        const format = this.detectFormat(content);
        formatDetected.textContent = format;
      } else {
        formatDetected.textContent = 'Auto-detect';
      }

      this.currentContent = content;
    });

    pasteInput.addEventListener('paste', (e) => {
      // Handle paste event
      setTimeout(() => {
        const content = pasteInput.value;
        this.currentContent = content;
      }, 10);
    });
  }

  /**
   * Dropzone handling
   */
  setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileSelectBtn = document.getElementById('file-select-btn');
    const fileList = document.getElementById('file-list');

    if (!dropzone) return;

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    });

    dropzone.addEventListener('dragenter', () => {
      dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', (e) => {
      if (e.target === dropzone) {
        dropzone.classList.remove('drag-over');
      }
    });

    dropzone.addEventListener('drop', (e) => {
      dropzone.classList.remove('drag-over');
      const files = e.dataTransfer.files;
      this.handleFiles(files);
    });

    // File select button
    fileSelectBtn.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const files = e.target.files;
      this.handleFiles(files);
    });
  }

  /**
   * Handle uploaded files
   */
  handleFiles(files) {
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';

    Array.from(files).forEach((file, index) => {
      // Validate file type
      const ext = file.name.split('.').pop().toUpperCase();
      const supportedFormats = ['DOCX', 'JSON', 'TXT', 'MD', 'CSV', 'HTML', 'ZIP', 'SCORM', 'QTI'];

      if (!supportedFormats.includes(ext)) {
        window.toast && window.toast.error(`Unsupported file format: ${ext}`);
        return;
      }

      // Create file item
      const fileItem = document.createElement('div');
      fileItem.className = 'file-item';
      fileItem.innerHTML = `
        <div class="file-icon">${ext}</div>
        <div class="file-info">
          <div class="file-name">${file.name}</div>
          <div class="file-size">${this.formatFileSize(file.size)}</div>
        </div>
        <button class="file-remove" data-index="${index}">&times;</button>
      `;

      fileList.appendChild(fileItem);

      // Store file for upload
      this.currentFile = file;

      // Remove button
      fileItem.querySelector('.file-remove').addEventListener('click', () => {
        fileItem.remove();
        this.currentFile = null;
      });
    });
  }

  /**
   * URL fetch handling
   */
  setupURLFetch() {
    const urlInput = document.getElementById('url-input');
    const fetchBtn = document.getElementById('fetch-url-btn');

    if (!urlInput || !fetchBtn) return;

    fetchBtn.addEventListener('click', async () => {
      const url = urlInput.value.trim();

      if (!url) {
        window.toast && window.toast.error('Please enter a URL');
        return;
      }

      try {
        this.showProgress('Fetching URL...');
        const result = await window.api.post('/import/fetch-url', { url });
        this.hideProgress();

        this.currentContent = result.content;
        this.displayPreview(result.content, result.content_type);
        window.toast && window.toast.success('Content fetched successfully');

      } catch (error) {
        this.hideProgress();
        window.toast && window.toast.error(error.message || 'Failed to fetch URL');
      }
    });
  }

  /**
   * Google OAuth handling
   */
  setupGoogleOAuth() {
    const connectBtn = document.getElementById('google-connect-btn');
    const statusIndicator = document.getElementById('google-oauth-status');
    const docInput = document.getElementById('google-doc-input');
    const googleDocUrl = document.getElementById('google-doc-url');
    const fetchDocBtn = document.getElementById('fetch-google-doc-btn');

    if (!connectBtn) return;

    // Check OAuth status on load
    this.checkOAuthStatus();

    // Connect button
    connectBtn.addEventListener('click', async () => {
      try {
        // Redirect to OAuth flow
        window.location.href = '/api/import/oauth/google';
      } catch (error) {
        window.toast && window.toast.error('Failed to initiate Google OAuth');
      }
    });

    // Fetch Google Doc button
    if (fetchDocBtn) {
      fetchDocBtn.addEventListener('click', async () => {
        const docUrlOrId = googleDocUrl.value.trim();

        if (!docUrlOrId) {
          window.toast && window.toast.error('Please enter a Google Doc URL or ID');
          return;
        }

        try {
          this.showProgress('Fetching Google Doc...');
          const result = await window.api.post('/import/google-doc', {
            doc_url: docUrlOrId
          });
          this.hideProgress();

          this.currentContent = result.content;
          this.displayPreview(result.content, 'text/plain');
          window.toast && window.toast.success(`Fetched: ${result.title || 'Document'}`);

        } catch (error) {
          this.hideProgress();
          window.toast && window.toast.error(error.message || 'Failed to fetch Google Doc');
        }
      });
    }
  }

  /**
   * Check OAuth connection status
   */
  async checkOAuthStatus() {
    try {
      const status = await window.api.get('/import/oauth/status');
      const statusIndicator = this.container.querySelector('#google-oauth-status .status-indicator');
      const docInput = document.getElementById('google-doc-input');

      if (status.google_connected) {
        statusIndicator.setAttribute('data-connected', 'true');
        statusIndicator.textContent = 'Connected';
        docInput && docInput.classList.remove('hidden');
      } else {
        statusIndicator.setAttribute('data-connected', 'false');
        statusIndicator.textContent = 'Not connected';
        docInput && docInput.classList.add('hidden');
      }
    } catch (error) {
      console.error('Failed to check OAuth status:', error);
    }
  }

  /**
   * Action buttons
   */
  setupActions() {
    const analyzeBtn = document.getElementById('analyze-btn');
    const importBtn = document.getElementById('import-btn');
    const cancelBtn = document.getElementById('cancel-import-btn');
    const clearPreviewBtn = document.getElementById('clear-preview-btn');

    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', () => this.analyzeContent());
    }

    if (importBtn) {
      importBtn.addEventListener('click', () => this.confirmImport());
    }

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        if (this.courseId) {
          window.location.href = `/courses/${this.courseId}`;
        } else {
          window.location.href = '/';
        }
      });
    }

    if (clearPreviewBtn) {
      clearPreviewBtn.addEventListener('click', () => this.clearPreview());
    }
  }

  /**
   * Analyze content via API
   */
  async analyzeContent() {
    let contentToAnalyze = null;
    let filename = null;

    // Get content from current tab
    if (this.currentFile) {
      contentToAnalyze = this.currentFile;
      filename = this.currentFile.name;
    } else if (this.currentContent) {
      contentToAnalyze = this.currentContent;
      filename = 'pasted-content.txt';
    } else {
      window.toast && window.toast.error('No content to analyze');
      return;
    }

    try {
      this.showProgress('Analyzing content...');

      let result;
      if (contentToAnalyze instanceof File) {
        // Upload file
        const formData = new FormData();
        formData.append('file', contentToAnalyze);

        const response = await fetch('/api/import/analyze', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Analysis failed');
        }

        result = await response.json();
      } else {
        // Send text content
        result = await window.api.post('/import/analyze', {
          content: contentToAnalyze,
          filename: filename
        });
      }

      this.hideProgress();
      this.analysisResult = result;
      this.displayAnalysis(result);
      this.displayPreview(contentToAnalyze, result.format_detected);

      // Show import button
      document.getElementById('import-btn').classList.remove('hidden');

      window.toast && window.toast.success('Content analyzed successfully');

    } catch (error) {
      this.hideProgress();
      window.toast && window.toast.error(error.message || 'Analysis failed');
    }
  }

  /**
   * Display analysis results
   */
  displayAnalysis(result) {
    const analysisSection = document.getElementById('import-analysis');
    const badgesContainer = document.getElementById('analysis-badges');
    const detailsContainer = document.getElementById('analysis-details');

    if (!analysisSection) return;

    // Show analysis section
    analysisSection.classList.remove('hidden');

    // Display format badge
    badgesContainer.innerHTML = `
      <span class="analysis-badge format">${result.format_detected.toUpperCase()}</span>
    `;

    // Display analysis details if available
    if (result.analysis) {
      const analysis = result.analysis;

      // Add Bloom's level badge if available
      if (analysis.bloom_level) {
        badgesContainer.innerHTML += `
          <span class="analysis-badge bloom">${analysis.bloom_level.toUpperCase()}</span>
        `;
      }

      // Display metrics
      detailsContainer.innerHTML = `
        <div class="analysis-item">
          <span class="analysis-label">Suggested Type</span>
          <span class="analysis-value">${analysis.suggested_type || 'Unknown'}</span>
        </div>
        <div class="analysis-item">
          <span class="analysis-label">Word Count</span>
          <span class="analysis-value">${analysis.word_count || 0}</span>
        </div>
        <div class="analysis-item">
          <span class="analysis-label">Estimated Duration</span>
          <span class="analysis-value">${analysis.estimated_duration || 0} min</span>
        </div>
      `;

      // Display suggestions if available
      if (analysis.suggestions && analysis.suggestions.length > 0) {
        detailsContainer.innerHTML += `
          <div class="analysis-suggestions">
            <h4>Suggestions</h4>
            <ul>
              ${analysis.suggestions.map(s => `<li>${s}</li>`).join('')}
            </ul>
          </div>
        `;
      }
    } else {
      detailsContainer.innerHTML = '<p>Analysis data not available</p>';
    }
  }

  /**
   * Display content preview
   */
  displayPreview(content, contentType) {
    const previewContent = document.getElementById('preview-content');

    if (!previewContent) return;

    if (content instanceof File) {
      previewContent.innerHTML = `
        <div class="preview-text">
          File: ${content.name}<br>
          Size: ${this.formatFileSize(content.size)}<br>
          Type: ${content.type || 'Unknown'}
        </div>
      `;
    } else {
      const preview = content.length > 1000 ? content.substring(0, 1000) + '...' : content;
      previewContent.innerHTML = `<div class="preview-text">${this.escapeHtml(preview)}</div>`;
    }
  }

  /**
   * Clear preview and analysis
   */
  clearPreview() {
    const previewContent = document.getElementById('preview-content');
    const analysisSection = document.getElementById('import-analysis');
    const importBtn = document.getElementById('import-btn');

    if (previewContent) {
      previewContent.innerHTML = `
        <div class="preview-placeholder">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
          </svg>
          <p>Content preview will appear here</p>
        </div>
      `;
    }

    if (analysisSection) {
      analysisSection.classList.add('hidden');
    }

    if (importBtn) {
      importBtn.classList.add('hidden');
    }

    this.currentContent = null;
    this.currentFile = null;
    this.analysisResult = null;
  }

  /**
   * Confirm import and execute
   */
  async confirmImport() {
    if (!this.analysisResult) {
      window.toast && window.toast.error('Please analyze content first');
      return;
    }

    if (!this.courseId) {
      window.toast && window.toast.error('No course context for import');
      return;
    }

    try {
      this.showProgress('Importing content...');

      let result;
      if (this.currentFile) {
        // Upload file
        const formData = new FormData();
        formData.append('file', this.currentFile);

        const response = await fetch(
          `/api/courses/${this.courseId}/import?target_type=activity`,
          {
            method: 'POST',
            body: formData
          }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Import failed');
        }

        result = await response.json();
      } else {
        // Send text content
        result = await window.api.post(
          `/courses/${this.courseId}/import?target_type=activity`,
          {
            content: this.currentContent,
            filename: 'imported-content.txt'
          }
        );
      }

      this.hideProgress();
      window.toast && window.toast.success('Content imported successfully');

      // Redirect back to course
      setTimeout(() => {
        window.location.href = `/courses/${this.courseId}`;
      }, 1000);

    } catch (error) {
      this.hideProgress();
      window.toast && window.toast.error(error.message || 'Import failed');
    }
  }

  /**
   * Utility: Detect format from content
   */
  detectFormat(content) {
    // Try JSON
    try {
      JSON.parse(content);
      return 'JSON';
    } catch (e) {}

    // Check for markdown
    if (content.match(/^#{1,6}\s/m) || content.match(/\*\*.*\*\*/)) {
      return 'Markdown';
    }

    // Check for HTML
    if (content.match(/<[a-z][\s\S]*>/i)) {
      return 'HTML';
    }

    // Check for CSV
    if (content.split('\n').some(line => line.includes(',') || line.includes('\t'))) {
      return 'CSV';
    }

    return 'Plain Text';
  }

  /**
   * Utility: Format file size
   */
  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  /**
   * Utility: Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show progress overlay
   */
  showProgress(message) {
    const overlay = document.getElementById('progress-overlay');
    const messageEl = document.getElementById('progress-message');

    if (overlay) {
      overlay.classList.remove('hidden');
      if (messageEl) {
        messageEl.textContent = message;
      }
    }
  }

  /**
   * Hide progress overlay
   */
  hideProgress() {
    const overlay = document.getElementById('progress-overlay');
    if (overlay) {
      overlay.classList.add('hidden');
    }
  }
}
