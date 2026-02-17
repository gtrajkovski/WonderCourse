/**
 * Sidebar Component - Collapsible navigation with state persistence
 */
class Sidebar {
  constructor() {
    this.sidebar = document.getElementById('sidebar');
    this.toggle = document.getElementById('sidebar-toggle');
    this.storageKey = 'sidebar_collapsed';

    if (!this.sidebar) {
      console.warn('Sidebar element not found');
      return;
    }

    this.initialize();
  }

  initialize() {
    // Load saved state
    const isCollapsed = window.storage.get(this.storageKey, false);
    if (isCollapsed) {
      this.collapse(false);
    }

    // Set up toggle button
    if (this.toggle) {
      this.toggle.addEventListener('click', () => {
        this.toggleCollapse();
      });
    }

    // Update body class
    this.updateBodyClass();
  }

  collapse(animate = true) {
    if (!animate) {
      this.sidebar.style.transition = 'none';
    }

    this.sidebar.classList.add('collapsed');
    document.body.classList.add('sidebar-collapsed');
    window.storage.set(this.storageKey, true);

    if (!animate) {
      setTimeout(() => {
        this.sidebar.style.transition = '';
      }, 10);
    }

    this.dispatchEvent('collapse');
  }

  expand(animate = true) {
    if (!animate) {
      this.sidebar.style.transition = 'none';
    }

    this.sidebar.classList.remove('collapsed');
    document.body.classList.remove('sidebar-collapsed');
    window.storage.set(this.storageKey, false);

    if (!animate) {
      setTimeout(() => {
        this.sidebar.style.transition = '';
      }, 10);
    }

    this.dispatchEvent('expand');
  }

  toggleCollapse() {
    if (this.isCollapsed()) {
      this.expand();
    } else {
      this.collapse();
    }
  }

  isCollapsed() {
    return this.sidebar.classList.contains('collapsed');
  }

  updateBodyClass() {
    if (this.sidebar) {
      document.body.classList.add('has-sidebar');
    }
  }

  dispatchEvent(action) {
    const event = new CustomEvent('sidebar:change', {
      detail: {
        action,
        collapsed: this.isCollapsed(),
      },
    });
    this.sidebar.dispatchEvent(event);
  }

  setActive(path) {
    // Remove active class from all nav items
    const navItems = this.sidebar.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.classList.remove('active');
    });

    // Add active class to matching nav item
    const activeItem = this.sidebar.querySelector(`a.nav-item[href="${path}"]`);
    if (activeItem) {
      activeItem.classList.add('active');
    }
  }

  destroy() {
    if (this.toggle) {
      this.toggle.removeEventListener('click', this.toggleCollapse);
    }
    document.body.classList.remove('has-sidebar', 'sidebar-collapsed');
  }
}

// Export Sidebar class
window.Sidebar = Sidebar;

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.sidebar = new Sidebar();

  // Set active nav item based on current path
  if (window.sidebar && window.sidebar.sidebar) {
    window.sidebar.setActive(window.location.pathname);
  }
});
