/**
 * Internationalization (i18n) utility for Course Builder Studio
 *
 * Handles loading translations, language switching, and DOM updates.
 */

class I18n {
  constructor() {
    this.translations = {};
    this.currentLocale = 'en';
    this.fallbackLocale = 'en';
    this.supportedLocales = ['en', 'es', 'pt', 'mk', 'fr', 'de'];
    this.localesPath = '/static/locales';
    this.initialized = false;
  }

  /**
   * Initialize the i18n system
   */
  async init() {
    // Get saved locale or detect from browser
    const savedLocale = localStorage.getItem('cbs_locale');
    const browserLocale = navigator.language.split('-')[0];

    // Determine which locale to use
    let locale = savedLocale || browserLocale;
    if (!this.supportedLocales.includes(locale)) {
      locale = this.fallbackLocale;
    }

    // Load translations
    await this.loadLocale(locale);
    await this.loadLocale(this.fallbackLocale); // Always load fallback

    this.currentLocale = locale;
    this.initialized = true;

    // Apply translations to DOM
    this.translatePage();

    // Update HTML lang attribute
    document.documentElement.lang = locale;

    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('i18n:ready', { detail: { locale } }));
  }

  /**
   * Load a locale file
   */
  async loadLocale(locale) {
    if (this.translations[locale]) {
      return; // Already loaded
    }

    try {
      const response = await fetch(`${this.localesPath}/${locale}.json`);
      if (!response.ok) {
        throw new Error(`Failed to load locale: ${locale}`);
      }
      this.translations[locale] = await response.json();
    } catch (error) {
      console.warn(`Could not load locale ${locale}:`, error);
      this.translations[locale] = {};
    }
  }

  /**
   * Change the current locale
   */
  async setLocale(locale) {
    if (!this.supportedLocales.includes(locale)) {
      console.warn(`Unsupported locale: ${locale}`);
      return false;
    }

    // Load locale if not already loaded
    await this.loadLocale(locale);

    this.currentLocale = locale;
    localStorage.setItem('cbs_locale', locale);

    // Apply translations
    this.translatePage();

    // Update HTML lang attribute
    document.documentElement.lang = locale;

    // Dispatch event
    window.dispatchEvent(new CustomEvent('i18n:localeChanged', { detail: { locale } }));

    return true;
  }

  /**
   * Get a translation by key
   * @param {string} key - Dot-notation key (e.g., 'common.save')
   * @param {object} params - Parameters for interpolation (e.g., {count: 5})
   */
  t(key, params = {}) {
    let value = this.getNestedValue(this.translations[this.currentLocale], key);

    // Fallback to default locale
    if (value === undefined) {
      value = this.getNestedValue(this.translations[this.fallbackLocale], key);
    }

    // Return key if no translation found
    if (value === undefined) {
      return key;
    }

    // Interpolate parameters
    if (params && typeof value === 'string') {
      Object.keys(params).forEach(param => {
        value = value.replace(new RegExp(`\\{${param}\\}`, 'g'), params[param]);
      });
    }

    return value;
  }

  /**
   * Get nested value from object using dot notation
   */
  getNestedValue(obj, key) {
    if (!obj) return undefined;
    return key.split('.').reduce((o, k) => (o || {})[k], obj);
  }

  /**
   * Translate all elements with data-i18n attribute
   */
  translatePage() {
    // Translate text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const params = el.getAttribute('data-i18n-params');
      const parsedParams = params ? JSON.parse(params) : {};
      el.textContent = this.t(key, parsedParams);
    });

    // Translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = this.t(key);
    });

    // Translate titles (tooltips)
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = this.t(key);
    });

    // Translate aria-labels
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria');
      el.setAttribute('aria-label', this.t(key));
    });
  }

  /**
   * Get list of available locales with metadata
   */
  getAvailableLocales() {
    return this.supportedLocales.map(code => {
      const meta = this.translations[code]?.meta || {};
      return {
        code,
        name: meta.name || code,
        nativeName: meta.nativeName || code,
        direction: meta.direction || 'ltr'
      };
    });
  }

  /**
   * Get current locale code
   */
  getLocale() {
    return this.currentLocale;
  }
}

// Create global instance
window.i18n = new I18n();

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.i18n.init());
} else {
  window.i18n.init();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = I18n;
}
