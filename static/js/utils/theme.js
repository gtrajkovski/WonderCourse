/**
 * Theme Manager - Handles light/dark theme switching with localStorage persistence
 */
(function() {
  'use strict';

  const STORAGE_KEY = 'cbs-theme';
  const THEMES = ['light', 'dark'];

  /**
   * Get the current theme from localStorage or system preference
   */
  function getStoredTheme() {
    return localStorage.getItem(STORAGE_KEY);
  }

  /**
   * Get the system's preferred color scheme
   */
  function getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  }

  /**
   * Get the effective current theme
   */
  function getCurrentTheme() {
    const stored = getStoredTheme();
    if (stored && THEMES.includes(stored)) {
      return stored;
    }
    return getSystemTheme();
  }

  /**
   * Apply theme to the document
   */
  function applyTheme(theme) {
    if (!THEMES.includes(theme)) {
      theme = 'dark';
    }
    document.documentElement.setAttribute('data-theme', theme);
  }

  /**
   * Save theme preference to localStorage
   */
  function saveTheme(theme) {
    localStorage.setItem(STORAGE_KEY, theme);
  }

  /**
   * Toggle between light and dark themes
   */
  function toggleTheme() {
    const current = getCurrentTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    saveTheme(next);
    return next;
  }

  /**
   * Set a specific theme
   */
  function setTheme(theme) {
    if (THEMES.includes(theme)) {
      applyTheme(theme);
      saveTheme(theme);
    }
  }

  /**
   * Initialize theme on page load
   */
  function initTheme() {
    // Apply stored theme immediately (before DOM ready) to prevent flash
    const theme = getCurrentTheme();
    applyTheme(theme);

    // Set up toggle button when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setupToggleButton);
    } else {
      setupToggleButton();
    }

    // Listen for system theme changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function(e) {
        // Only auto-switch if user hasn't set a preference
        if (!getStoredTheme()) {
          applyTheme(e.matches ? 'light' : 'dark');
        }
      });
    }
  }

  /**
   * Set up the theme toggle button click handler
   */
  function setupToggleButton() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function() {
        const newTheme = toggleTheme();
        // Update button title
        this.title = newTheme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
      });
      // Set initial title
      const current = getCurrentTheme();
      toggleBtn.title = current === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
    }
  }

  // Export to window
  window.ThemeManager = {
    getCurrentTheme: getCurrentTheme,
    setTheme: setTheme,
    toggleTheme: toggleTheme,
    init: initTheme
  };

  // Auto-initialize
  initTheme();
})();
