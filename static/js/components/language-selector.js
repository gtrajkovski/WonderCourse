/**
 * Language Selector Component
 *
 * Dropdown for selecting UI language
 */

class LanguageSelector {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.warn('Language selector container not found:', containerId);
      return;
    }

    this.init();
  }

  init() {
    // Wait for i18n to be ready
    if (window.i18n && window.i18n.initialized) {
      this.render();
    } else {
      window.addEventListener('i18n:ready', () => this.render());
    }
  }

  render() {
    const locales = window.i18n.getAvailableLocales();
    const currentLocale = window.i18n.getLocale();

    // Find current locale data
    const currentLocaleData = locales.find(l => l.code === currentLocale) || locales[0];

    this.container.innerHTML = `
      <div class="language-selector">
        <button class="language-selector-btn" id="language-selector-btn" aria-haspopup="true" aria-expanded="false">
          <span class="language-icon">&#127760;</span>
          <span class="language-name">${currentLocaleData.nativeName}</span>
          <span class="language-arrow">&#9662;</span>
        </button>
        <ul class="language-dropdown" id="language-dropdown" role="menu">
          ${locales.map(locale => `
            <li role="menuitem">
              <button class="language-option ${locale.code === currentLocale ? 'active' : ''}"
                      data-locale="${locale.code}">
                <span class="language-option-native">${locale.nativeName}</span>
                <span class="language-option-name">${locale.name}</span>
                ${locale.code === currentLocale ? '<span class="language-check">&#10003;</span>' : ''}
              </button>
            </li>
          `).join('')}
        </ul>
      </div>
    `;

    this.attachEvents();
  }

  attachEvents() {
    const btn = this.container.querySelector('#language-selector-btn');
    const dropdown = this.container.querySelector('#language-dropdown');

    // Toggle dropdown
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.toggle('open');
      btn.setAttribute('aria-expanded', isOpen);
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!this.container.contains(e.target)) {
        dropdown.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
      }
    });

    // Handle language selection
    dropdown.querySelectorAll('.language-option').forEach(option => {
      option.addEventListener('click', async () => {
        const locale = option.getAttribute('data-locale');
        await window.i18n.setLocale(locale);
        this.render(); // Re-render to update selection

        // Show toast notification
        if (window.toast) {
          window.toast.success(window.i18n.t('common.success'));
        }
      });
    });

    // Keyboard navigation
    btn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        btn.click();
      }
    });
  }
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('language-selector-container')) {
    window.languageSelector = new LanguageSelector('language-selector-container');
  }
});
