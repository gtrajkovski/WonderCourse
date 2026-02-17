/**
 * Help Manager Component
 * Manages contextual help panels, tooltips, and glossary
 */

class HelpManager {
  constructor() {
    this.currentPanel = null;
    this.helpPanel = null;
    this.helpPanelTitle = null;
    this.helpPanelContent = null;
  }

  /**
   * Initialize the help manager
   */
  init() {
    this.helpPanel = document.getElementById('help-panel');
    this.helpPanelTitle = document.getElementById('help-panel-title');
    this.helpPanelContent = document.getElementById('help-panel-content');

    if (!this.helpPanel) {
      console.warn('Help panel element not found');
      return;
    }

    // Initialize tooltips
    this.initTooltips();

    // Close panel when clicking outside
    document.addEventListener('click', (e) => {
      if (this.helpPanel && this.helpPanel.classList.contains('open')) {
        if (!this.helpPanel.contains(e.target) && !e.target.closest('.help-btn')) {
          this.hidePanel();
        }
      }
    });

    // Handle escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.helpPanel && this.helpPanel.classList.contains('open')) {
        this.hidePanel();
      }
    });
  }

  /**
   * Show a specific help panel
   * @param {string} panelId - The panel identifier
   * @param {object} options - Optional configuration (title, content)
   */
  showPanel(panelId, options = {}) {
    if (!this.helpPanel) {
      console.warn('Help panel not initialized');
      return;
    }

    this.currentPanel = panelId;

    // Set title
    if (options.title && this.helpPanelTitle) {
      this.helpPanelTitle.textContent = options.title;
    }

    // Set content
    if (options.content && this.helpPanelContent) {
      if (typeof options.content === 'string') {
        this.helpPanelContent.innerHTML = options.content;
      } else {
        this.helpPanelContent.innerHTML = '';
        this.helpPanelContent.appendChild(options.content);
      }
    } else if (panelId) {
      // Load content for this panel
      this.loadContent(panelId);
    }

    // Open the panel
    this.helpPanel.classList.add('open');
  }

  /**
   * Hide the help panel
   */
  hidePanel() {
    if (this.helpPanel) {
      this.helpPanel.classList.remove('open');
      this.currentPanel = null;
    }
  }

  /**
   * Toggle panel visibility
   * @param {string} panelId - The panel identifier
   * @param {object} options - Optional configuration
   */
  togglePanel(panelId, options = {}) {
    if (this.helpPanel && this.helpPanel.classList.contains('open') && this.currentPanel === panelId) {
      this.hidePanel();
    } else {
      this.showPanel(panelId, options);
    }
  }

  /**
   * Load content for a specific topic
   * @param {string} topic - The help topic to load
   */
  async loadContent(topic) {
    if (!this.helpPanelContent) return;

    // Show loading state
    this.helpPanelContent.innerHTML = '<p>Loading...</p>';

    try {
      // Check if it's a glossary request
      if (topic === 'glossary') {
        await this.loadGlossary();
        return;
      }

      // Try to fetch from API
      const response = await fetch(`/api/help/${topic}`);
      if (response.ok) {
        const data = await response.json();
        this.renderHelpContent(data);
      } else {
        // Fallback to static content
        this.renderStaticContent(topic);
      }
    } catch (error) {
      console.warn(`Error loading help content for ${topic}:`, error);
      this.renderStaticContent(topic);
    }
  }

  /**
   * Render help content
   * @param {object} data - The help data
   */
  renderHelpContent(data) {
    if (!this.helpPanelContent) return;

    let html = '';

    if (data.title && this.helpPanelTitle) {
      this.helpPanelTitle.textContent = data.title;
    }

    if (data.description) {
      html += `<p>${data.description}</p>`;
    }

    if (data.sections) {
      data.sections.forEach(section => {
        html += `<h3>${section.title}</h3>`;
        if (section.content) {
          html += `<p>${section.content}</p>`;
        }
        if (section.items) {
          html += '<ul>';
          section.items.forEach(item => {
            html += `<li>${item}</li>`;
          });
          html += '</ul>';
        }
      });
    }

    this.helpPanelContent.innerHTML = html;
  }

  /**
   * Render static fallback content
   * @param {string} topic - The help topic
   */
  renderStaticContent(topic) {
    if (!this.helpPanelContent) return;

    const staticContent = {
      'bloom-taxonomy': {
        title: 'Bloom\'s Taxonomy',
        content: `
          <h3>What is Bloom's Taxonomy?</h3>
          <p>Bloom's Taxonomy is a framework for categorizing educational goals by cognitive complexity.</p>
          <h3>Levels (from lowest to highest)</h3>
          <ul>
            <li><strong>Remember:</strong> Recall facts and basic concepts</li>
            <li><strong>Understand:</strong> Explain ideas or concepts</li>
            <li><strong>Apply:</strong> Use information in new situations</li>
            <li><strong>Analyze:</strong> Draw connections among ideas</li>
            <li><strong>Evaluate:</strong> Justify a decision or course of action</li>
            <li><strong>Create:</strong> Produce new or original work</li>
          </ul>
          <p>Use higher levels for advanced learners and lower levels for foundational content.</p>
        `
      },
      'wwhaa': {
        title: 'WWHAA Framework',
        content: `
          <h3>What is WWHAA?</h3>
          <p>WWHAA is a video script structure used in instructional design.</p>
          <h3>Structure</h3>
          <ul>
            <li><strong>What:</strong> Introduce the concept</li>
            <li><strong>Why:</strong> Explain why it matters</li>
            <li><strong>How:</strong> Demonstrate the process</li>
            <li><strong>Apply:</strong> Show practical application</li>
            <li><strong>Action:</strong> Call to action for learners</li>
          </ul>
        `
      }
    };

    const content = staticContent[topic];
    if (content) {
      if (content.title && this.helpPanelTitle) {
        this.helpPanelTitle.textContent = content.title;
      }
      this.helpPanelContent.innerHTML = content.content;
    } else {
      this.helpPanelContent.innerHTML = '<p>Help content not available for this topic.</p>';
    }
  }

  /**
   * Load and render glossary
   */
  async loadGlossary() {
    try {
      const response = await fetch('/api/help/glossary');
      if (response.ok) {
        const glossary = await response.json();
        this.renderGlossary(glossary);
      } else {
        // Load from static file
        const staticResponse = await fetch('/static/data/glossary.json');
        if (staticResponse.ok) {
          const glossary = await staticResponse.json();
          this.renderGlossary(glossary);
        } else {
          throw new Error('Could not load glossary');
        }
      }
    } catch (error) {
      console.error('Error loading glossary:', error);
      this.helpPanelContent.innerHTML = '<p>Error loading glossary.</p>';
    }
  }

  /**
   * Render glossary in help panel
   * @param {object} glossary - The glossary data
   */
  renderGlossary(glossary) {
    if (!this.helpPanelContent || !this.helpPanelTitle) return;

    this.helpPanelTitle.textContent = 'Glossary';

    let html = '<div class="glossary-search"><input type="text" id="glossary-search-input" placeholder="Search terms..." class="form-input" /></div>';
    html += '<div id="glossary-results" class="glossary-results">';

    // Group terms by first letter
    const grouped = {};
    const terms = glossary.terms || [];

    terms.forEach(term => {
      const firstLetter = term.term[0].toUpperCase();
      if (!grouped[firstLetter]) {
        grouped[firstLetter] = [];
      }
      grouped[firstLetter].push(term);
    });

    // Render grouped terms
    Object.keys(grouped).sort().forEach(letter => {
      html += `<div class="glossary-group">`;
      html += `<h3 class="glossary-letter">${letter}</h3>`;
      grouped[letter].forEach(term => {
        html += `<div class="glossary-term" data-term="${term.term.toLowerCase()}">`;
        html += `<h4 class="glossary-term-title">${term.term}</h4>`;
        html += `<p class="glossary-term-definition">${term.definition}</p>`;
        if (term.examples && term.examples.length > 0) {
          html += '<div class="glossary-term-examples"><strong>Examples:</strong><ul>';
          term.examples.forEach(ex => {
            html += `<li>${ex}</li>`;
          });
          html += '</ul></div>';
        }
        if (term.related && term.related.length > 0) {
          html += '<div class="glossary-term-related"><strong>Related:</strong> ';
          html += term.related.map(r => `<a href="#" class="glossary-link" data-term="${r}">${r}</a>`).join(', ');
          html += '</div>';
        }
        html += `</div>`;
      });
      html += `</div>`;
    });

    html += '</div>';

    this.helpPanelContent.innerHTML = html;

    // Add search functionality
    const searchInput = document.getElementById('glossary-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchGlossary(e.target.value);
      });
    }

    // Add click handlers for related term links
    this.helpPanelContent.querySelectorAll('.glossary-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const term = e.target.dataset.term;
        this.searchGlossary(term);
        // Scroll to term
        const termElement = this.helpPanelContent.querySelector(`[data-term="${term.toLowerCase()}"]`);
        if (termElement) {
          termElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  /**
   * Search glossary terms
   * @param {string} query - The search query
   */
  searchGlossary(query) {
    const terms = this.helpPanelContent.querySelectorAll('.glossary-term');
    const lowerQuery = query.toLowerCase().trim();

    if (!lowerQuery) {
      // Show all terms
      terms.forEach(term => {
        term.style.display = '';
      });
      return;
    }

    terms.forEach(term => {
      const termText = term.dataset.term || '';
      const definitionText = term.querySelector('.glossary-term-definition')?.textContent || '';
      const searchText = (termText + ' ' + definitionText).toLowerCase();

      if (searchText.includes(lowerQuery)) {
        term.style.display = '';
      } else {
        term.style.display = 'none';
      }
    });
  }

  /**
   * Initialize tooltips on all .help-btn elements
   */
  initTooltips() {
    const helpButtons = document.querySelectorAll('.help-btn');

    helpButtons.forEach(btn => {
      const tooltipText = btn.dataset.tooltip || btn.getAttribute('title');
      if (tooltipText) {
        // Create tooltip element
        const tooltip = document.createElement('span');
        tooltip.className = 'tooltip';
        tooltip.textContent = tooltipText;
        btn.appendChild(tooltip);

        // Remove title to prevent default browser tooltip
        btn.removeAttribute('title');

        // Add click handler to show panel if data-panel exists
        if (btn.dataset.panel) {
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            this.showPanel(btn.dataset.panel);
          });
        }
      }
    });
  }
}

// Export and auto-initialize
window.HelpManager = HelpManager;

document.addEventListener('DOMContentLoaded', () => {
  window.help = new HelpManager();
  window.help.init();
});
