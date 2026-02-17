/**
 * Skeleton Manager - Loading state management
 */
class SkeletonManager {
  constructor() {
    this.activeLoaders = new Map();
  }

  /**
   * Show skeleton for a container
   * @param {string} containerId - Container element ID or selector
   */
  show(containerId) {
    const container = typeof containerId === 'string'
      ? document.querySelector(containerId)
      : containerId;

    if (!container) {
      console.warn(`[SkeletonManager] Container not found: ${containerId}`);
      return;
    }

    container.setAttribute('data-loading', 'true');

    // Track start time for elapsed time display
    this.activeLoaders.set(container, {
      startTime: Date.now(),
      elapsedInterval: null,
    });
  }

  /**
   * Hide skeleton for a container
   * @param {string} containerId - Container element ID or selector
   */
  hide(containerId) {
    const container = typeof containerId === 'string'
      ? document.querySelector(containerId)
      : containerId;

    if (!container) {
      console.warn(`[SkeletonManager] Container not found: ${containerId}`);
      return;
    }

    container.setAttribute('data-loading', 'false');

    // Clear elapsed time tracking
    const loader = this.activeLoaders.get(container);
    if (loader && loader.elapsedInterval) {
      clearInterval(loader.elapsedInterval);
    }
    this.activeLoaders.delete(container);
  }

  /**
   * Run async function with skeleton loading state
   * @param {string} containerId - Container element ID or selector
   * @param {Function} asyncFn - Async function to execute
   * @param {Object} options - Options (showElapsedAfter: ms threshold to show elapsed time)
   * @returns {Promise<any>} Result of asyncFn
   */
  async withSkeleton(containerId, asyncFn, options = {}) {
    const container = typeof containerId === 'string'
      ? document.querySelector(containerId)
      : containerId;

    if (!container) {
      console.warn(`[SkeletonManager] Container not found: ${containerId}`);
      return asyncFn();
    }

    this.show(container);

    // Show elapsed time after threshold
    const showElapsedAfter = options.showElapsedAfter || 2000;
    let elapsedInterval = null;

    if (showElapsedAfter > 0) {
      setTimeout(() => {
        const loader = this.activeLoaders.get(container);
        if (loader) {
          // Add elapsed time display
          let elapsedDisplay = container.querySelector('.elapsed-time');
          if (!elapsedDisplay) {
            const loadingMsg = container.querySelector('.loading-message');
            if (loadingMsg) {
              elapsedDisplay = document.createElement('span');
              elapsedDisplay.className = 'elapsed-time';
              loadingMsg.appendChild(elapsedDisplay);
            }
          }

          if (elapsedDisplay) {
            // Update every second
            elapsedInterval = setInterval(() => {
              const elapsed = Math.floor((Date.now() - loader.startTime) / 1000);
              elapsedDisplay.textContent = `(${elapsed}s)`;
            }, 1000);

            loader.elapsedInterval = elapsedInterval;
          }
        }
      }, showElapsedAfter);
    }

    try {
      const result = await asyncFn();
      return result;
    } finally {
      // Clear elapsed interval
      if (elapsedInterval) {
        clearInterval(elapsedInterval);
      }

      this.hide(container);
    }
  }

  /**
   * Check if container is currently loading
   * @param {string} containerId - Container element ID or selector
   * @returns {boolean}
   */
  isLoading(containerId) {
    const container = typeof containerId === 'string'
      ? document.querySelector(containerId)
      : containerId;

    if (!container) return false;

    return container.getAttribute('data-loading') === 'true';
  }

  /**
   * Get elapsed time for a loading container
   * @param {string} containerId - Container element ID or selector
   * @returns {number} Elapsed time in milliseconds, or 0 if not loading
   */
  getElapsedTime(containerId) {
    const container = typeof containerId === 'string'
      ? document.querySelector(containerId)
      : containerId;

    if (!container) return 0;

    const loader = this.activeLoaders.get(container);
    if (!loader) return 0;

    return Date.now() - loader.startTime;
  }
}

// Export global instance
window.skeleton = new SkeletonManager();
