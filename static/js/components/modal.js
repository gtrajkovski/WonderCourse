/**
 * Modal Component - Dialog with focus trap and ESC handling
 */
class Modal {
  constructor(id) {
    this.id = id;
    this.modal = document.getElementById(id);
    if (!this.modal) {
      console.error(`Modal with id "${id}" not found`);
      return;
    }

    this.backdrop = this.modal.querySelector('.modal-backdrop');
    this.content = this.modal.querySelector('.modal-content');
    this.lastFocusedElement = null;
    this.isOpen = false;

    this.initialize();
  }

  initialize() {
    // Set initial aria-hidden
    this.modal.setAttribute('aria-hidden', 'true');

    // Close on backdrop click
    if (this.backdrop) {
      this.backdrop.addEventListener('click', (e) => {
        if (e.target === this.backdrop) {
          this.close();
        }
      });
    }

    // Close on ESC key
    document.addEventListener('keydown', (e) => {
      if (this.isOpen && e.key === 'Escape') {
        this.close();
      }
    });

    // Trap focus when modal is open
    this.modal.addEventListener('keydown', (e) => {
      if (this.isOpen && e.key === 'Tab') {
        this.trapFocus(e);
      }
    });

    // Find close buttons
    const closeButtons = this.modal.querySelectorAll('[data-modal-close]');
    closeButtons.forEach(btn => {
      btn.addEventListener('click', () => this.close());
    });
  }

  open() {
    this.lastFocusedElement = document.activeElement;
    this.modal.setAttribute('aria-hidden', 'false');
    this.isOpen = true;

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Focus first focusable element
    setTimeout(() => {
      const focusableElements = this.getFocusableElements();
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    }, 100);

    // Dispatch open event
    this.modal.dispatchEvent(new CustomEvent('modal:open', { detail: { modalId: this.id } }));
  }

  close() {
    this.modal.setAttribute('aria-hidden', 'true');
    this.isOpen = false;

    // Restore body scroll
    document.body.style.overflow = '';

    // Restore focus
    if (this.lastFocusedElement) {
      this.lastFocusedElement.focus();
    }

    // Dispatch close event
    this.modal.dispatchEvent(new CustomEvent('modal:close', { detail: { modalId: this.id } }));
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  getFocusableElements() {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ];

    return Array.from(
      this.modal.querySelectorAll(focusableSelectors.join(', '))
    ).filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null);
  }

  trapFocus(e) {
    const focusableElements = this.getFocusableElements();
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      }
    } else {
      // Tab
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }

  destroy() {
    this.close();
    // Remove event listeners would go here if we tracked them
  }
}

// Export Modal class
window.Modal = Modal;

// Auto-initialize modals with data-modal attribute
document.addEventListener('DOMContentLoaded', () => {
  const modalElements = document.querySelectorAll('[data-modal]');
  modalElements.forEach(el => {
    const modalId = el.id;
    if (modalId) {
      window[`modal_${modalId}`] = new Modal(modalId);
    }
  });

  // Handle modal triggers
  const triggers = document.querySelectorAll('[data-modal-target]');
  triggers.forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = trigger.getAttribute('data-modal-target');
      const modal = window[`modal_${targetId}`];
      if (modal) {
        modal.open();
      }
    });
  });
});
