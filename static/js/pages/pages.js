/**
 * Pages Controller - Course pages management
 *
 * Manages:
 * - Generating course pages (syllabus, about, resources)
 * - Viewing generated pages
 * - Regenerating and deleting pages
 */
class PagesController {
  constructor(courseId) {
    this.courseId = courseId;
    this.pages = {};
    this.currentPageType = null;
    this.generatingModal = null;
  }

  async init() {
    // Initialize modal
    this.generatingModal = new Modal('generating-modal');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
    }

    // Bind event handlers
    this.bindEventHandlers();

    // Load existing pages
    await this.loadPages();
  }

  bindEventHandlers() {
    // Generate buttons
    document.querySelectorAll('.btn-generate').forEach(btn => {
      btn.addEventListener('click', () => this.generatePage(btn.dataset.pageType));
    });

    // View buttons
    document.querySelectorAll('.btn-view').forEach(btn => {
      btn.addEventListener('click', () => this.viewPage(btn.dataset.pageType));
    });

    // Regenerate buttons
    document.querySelectorAll('.btn-regenerate').forEach(btn => {
      btn.addEventListener('click', () => this.regeneratePage(btn.dataset.pageType));
    });

    // Generate all button
    const btnGenerateAll = document.getElementById('btn-generate-all');
    if (btnGenerateAll) {
      btnGenerateAll.addEventListener('click', () => this.generateAllPages());
    }

    // Close preview button
    const btnClosePreview = document.getElementById('btn-close-preview');
    if (btnClosePreview) {
      btnClosePreview.addEventListener('click', () => this.closePreview());
    }

    // Copy content button
    const btnCopyContent = document.getElementById('btn-copy-content');
    if (btnCopyContent) {
      btnCopyContent.addEventListener('click', () => this.copyContent());
    }

    // Delete page button
    const btnDeletePage = document.getElementById('btn-delete-page');
    if (btnDeletePage) {
      btnDeletePage.addEventListener('click', () => this.deletePage());
    }
  }

  async loadPages() {
    try {
      const response = await api.get(`/courses/${this.courseId}/pages`);

      // Store pages by type
      this.pages = {};
      for (const page of response.pages) {
        this.pages[page.page_type] = page;
      }

      // Update UI for each page type
      this.updatePageCard('syllabus');
      this.updatePageCard('about');
      this.updatePageCard('resources');

    } catch (error) {
      console.error('Failed to load pages:', error);
    }
  }

  updatePageCard(pageType) {
    const card = document.querySelector(`.page-card[data-page-type="${pageType}"]`);
    if (!card) return;

    const page = this.pages[pageType];
    const statusEl = card.querySelector('.page-status .status-badge');
    const generateBtn = card.querySelector('.btn-generate');
    const viewBtn = card.querySelector('.btn-view');
    const regenerateBtn = card.querySelector('.btn-regenerate');

    if (page) {
      // Page exists
      statusEl.textContent = 'Generated';
      statusEl.className = 'status-badge status-generated';
      generateBtn.style.display = 'none';
      viewBtn.style.display = 'inline-block';
      regenerateBtn.style.display = 'inline-block';
    } else {
      // Page not generated
      statusEl.textContent = 'Not Generated';
      statusEl.className = 'status-badge status-not-generated';
      generateBtn.style.display = 'inline-block';
      viewBtn.style.display = 'none';
      regenerateBtn.style.display = 'none';
    }
  }

  async generatePage(pageType) {
    this.showGenerating(`Generating ${pageType} page...`);

    try {
      const response = await api.post(`/courses/${this.courseId}/pages/${pageType}`);

      this.pages[pageType] = response.page;
      this.updatePageCard(pageType);
      this.hideGenerating();

      toast.success(`${this.formatPageType(pageType)} page generated successfully`);

      // Auto-show preview
      this.viewPage(pageType);

    } catch (error) {
      this.hideGenerating();
      if (error.status === 409) {
        // Page already exists
        toast.info('Page already exists. Use Regenerate to update it.');
      } else {
        toast.error(`Failed to generate page: ${error.message}`);
      }
    }
  }

  async regeneratePage(pageType) {
    this.showGenerating(`Regenerating ${pageType} page...`);

    try {
      const response = await api.post(`/courses/${this.courseId}/pages/${pageType}`, {
        regenerate: true
      });

      this.pages[pageType] = response.page;
      this.updatePageCard(pageType);
      this.hideGenerating();

      toast.success(`${this.formatPageType(pageType)} page regenerated successfully`);

      // Auto-show preview
      this.viewPage(pageType);

    } catch (error) {
      this.hideGenerating();
      toast.error(`Failed to regenerate page: ${error.message}`);
    }
  }

  async generateAllPages() {
    this.showGenerating('Generating all pages...');

    try {
      const response = await api.post(`/courses/${this.courseId}/pages/generate-all`, {
        regenerate: false
      });

      // Reload pages
      await this.loadPages();
      this.hideGenerating();

      const generated = Object.values(response.results).filter(r => r === 'generated').length;
      const skipped = Object.values(response.results).filter(r => r.includes('skipped')).length;

      if (generated > 0) {
        toast.success(`Generated ${generated} page(s)` + (skipped > 0 ? `, ${skipped} already existed` : ''));
      } else if (skipped > 0) {
        toast.info('All pages already exist. Use individual Regenerate buttons to update.');
      }

    } catch (error) {
      this.hideGenerating();
      toast.error(`Failed to generate pages: ${error.message}`);
    }
  }

  async viewPage(pageType) {
    const page = this.pages[pageType];
    if (!page) {
      toast.error('Page not found. Generate it first.');
      return;
    }

    this.currentPageType = pageType;

    // Update preview header
    const previewTitle = document.getElementById('preview-title');
    previewTitle.textContent = page.title || this.formatPageType(pageType);

    // Render content
    const previewContent = document.getElementById('preview-content');
    previewContent.innerHTML = this.renderMarkdown(page.content);

    // Show preview panel
    const previewPanel = document.getElementById('page-preview');
    previewPanel.style.display = 'block';

    // Scroll to preview
    previewPanel.scrollIntoView({ behavior: 'smooth' });
  }

  closePreview() {
    const previewPanel = document.getElementById('page-preview');
    previewPanel.style.display = 'none';
    this.currentPageType = null;
  }

  async copyContent() {
    if (!this.currentPageType || !this.pages[this.currentPageType]) {
      toast.error('No page selected');
      return;
    }

    const content = this.pages[this.currentPageType].content;

    try {
      await navigator.clipboard.writeText(content);
      toast.success('Content copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy content');
    }
  }

  async deletePage() {
    if (!this.currentPageType) {
      toast.error('No page selected');
      return;
    }

    if (!confirm(`Are you sure you want to delete the ${this.formatPageType(this.currentPageType)} page?`)) {
      return;
    }

    try {
      await api.delete(`/courses/${this.courseId}/pages/${this.currentPageType}`);

      delete this.pages[this.currentPageType];
      this.updatePageCard(this.currentPageType);
      this.closePreview();

      toast.success('Page deleted successfully');

    } catch (error) {
      toast.error(`Failed to delete page: ${error.message}`);
    }
  }

  showGenerating(message) {
    const messageEl = document.getElementById('generating-message');
    if (messageEl) {
      messageEl.textContent = message;
    }
    this.generatingModal.open();
  }

  hideGenerating() {
    this.generatingModal.close();
  }

  formatPageType(pageType) {
    const names = {
      syllabus: 'Syllabus',
      about: 'About',
      resources: 'Resources'
    };
    return names[pageType] || pageType;
  }

  renderMarkdown(markdown) {
    if (!markdown) return '<p class="text-muted">No content</p>';

    // Simple markdown rendering
    let html = markdown
      // Escape HTML
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Headers
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      // Bold and italic
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Lists
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
      // Paragraphs
      .replace(/\n\n/g, '</p><p>')
      // Line breaks
      .replace(/\n/g, '<br>');

    // Wrap in paragraph if not starting with header
    if (!html.startsWith('<h')) {
      html = '<p>' + html + '</p>';
    }

    // Fix list items
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    return html;
  }
}

// Export for use
window.PagesController = PagesController;
