/**
 * LazyLoader - Generic lazy loading utility with pagination and infinite scroll
 *
 * Provides:
 * - Paginated data fetching
 * - Infinite scroll via Intersection Observer
 * - "Load More" button fallback
 * - Caching to avoid re-fetching
 * - Skeleton loading states
 */
class LazyLoader {
  /**
   * Create a lazy loader instance
   *
   * @param {Object} options Configuration options
   * @param {string} options.containerId DOM element ID where items are rendered
   * @param {Function} options.fetchFn Async function(page) that returns items array
   * @param {Function} options.renderFn Function(item) that returns HTML string for item
   * @param {number} options.perPage Items per page (default 20)
   * @param {boolean} options.infiniteScroll Enable infinite scroll (default true)
   * @param {string} options.loadMoreText Text for load more button (default "Load More")
   * @param {string} options.loadingText Text while loading (default "Loading...")
   */
  constructor(options) {
    this.containerId = options.containerId;
    this.fetchFn = options.fetchFn;
    this.renderFn = options.renderFn;
    this.perPage = options.perPage || 20;
    this.infiniteScroll = options.infiniteScroll !== false;
    this.loadMoreText = options.loadMoreText || 'Load More';
    this.loadingText = options.loadingText || 'Loading...';

    // State
    this.currentPage = 0;
    this.hasMore = true;
    this.isLoading = false;
    this.items = [];

    // DOM elements
    this.container = null;
    this.loadMoreBtn = null;
    this.observer = null;
  }

  /**
   * Initialize the loader and fetch first page
   */
  async init() {
    this.container = document.getElementById(this.containerId);
    if (!this.container) {
      console.error(`LazyLoader: Container #${this.containerId} not found`);
      return;
    }

    // Create load more button
    this.createLoadMoreButton();

    // Set up infinite scroll if enabled
    if (this.infiniteScroll) {
      this.setupIntersectionObserver();
    }

    // Load first page
    await this.loadMore();
  }

  /**
   * Create and append load more button to container
   */
  createLoadMoreButton() {
    this.loadMoreBtn = document.createElement('button');
    this.loadMoreBtn.className = 'btn-load-more';
    this.loadMoreBtn.textContent = this.loadMoreText;
    this.loadMoreBtn.style.cssText = `
      display: block;
      margin: 2rem auto;
      padding: 0.75rem 2rem;
      background: var(--color-primary, #4f46e5);
      color: white;
      border: none;
      border-radius: 0.5rem;
      cursor: pointer;
      font-size: 1rem;
      transition: background 0.2s;
    `;

    this.loadMoreBtn.addEventListener('click', () => this.loadMore());
    this.container.appendChild(this.loadMoreBtn);
  }

  /**
   * Set up Intersection Observer for infinite scroll
   */
  setupIntersectionObserver() {
    const options = {
      root: null,
      rootMargin: '100px',
      threshold: 0.1
    };

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !this.isLoading && this.hasMore) {
          this.loadMore();
        }
      });
    }, options);

    // Observe the load more button
    if (this.loadMoreBtn) {
      this.observer.observe(this.loadMoreBtn);
    }
  }

  /**
   * Load next page of items
   */
  async loadMore() {
    if (this.isLoading || !this.hasMore) {
      return;
    }

    this.isLoading = true;
    this.showLoading();

    try {
      this.currentPage++;
      const response = await this.fetchFn(this.currentPage);

      // Handle both array responses and paginated responses
      let items, hasMore;
      if (Array.isArray(response)) {
        items = response;
        hasMore = items.length >= this.perPage;
      } else {
        items = response.items || response.courses || response.activities || [];
        hasMore = response.has_more !== undefined ? response.has_more : false;
      }

      // Store items
      this.items.push(...items);
      this.hasMore = hasMore;

      // Render new items
      this.renderItems(items);

      // Update button visibility
      if (!this.hasMore) {
        this.hideLoadMoreButton();
      }
    } catch (error) {
      console.error('LazyLoader: Error loading items', error);
      this.showError('Failed to load items. Please try again.');
      this.currentPage--; // Revert page increment
    } finally {
      this.isLoading = false;
      this.hideLoading();
    }
  }

  /**
   * Render items to container
   *
   * @param {Array} items Items to render
   */
  renderItems(items) {
    items.forEach(item => {
      const html = this.renderFn(item);
      const element = document.createElement('div');
      element.innerHTML = html;
      this.container.insertBefore(element.firstElementChild, this.loadMoreBtn);
    });
  }

  /**
   * Show loading state
   */
  showLoading() {
    if (this.loadMoreBtn) {
      this.loadMoreBtn.disabled = true;
      this.loadMoreBtn.textContent = this.loadingText;
    }
  }

  /**
   * Hide loading state
   */
  hideLoading() {
    if (this.loadMoreBtn) {
      this.loadMoreBtn.disabled = false;
      this.loadMoreBtn.textContent = this.loadMoreText;
    }
  }

  /**
   * Hide load more button
   */
  hideLoadMoreButton() {
    if (this.loadMoreBtn) {
      this.loadMoreBtn.style.display = 'none';
    }
  }

  /**
   * Show error message
   *
   * @param {string} message Error message
   */
  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'lazy-loader-error';
    errorDiv.style.cssText = `
      padding: 1rem;
      margin: 1rem 0;
      background: var(--color-error-bg, #fee);
      color: var(--color-error, #c00);
      border-radius: 0.5rem;
      text-align: center;
    `;
    errorDiv.textContent = message;
    this.container.insertBefore(errorDiv, this.loadMoreBtn);

    // Remove error after 5 seconds
    setTimeout(() => errorDiv.remove(), 5000);
  }

  /**
   * Reset loader and fetch from beginning
   */
  async refresh() {
    this.currentPage = 0;
    this.hasMore = true;
    this.items = [];

    // Clear container except load more button
    while (this.container.firstChild !== this.loadMoreBtn) {
      this.container.removeChild(this.container.firstChild);
    }

    // Show load more button again
    if (this.loadMoreBtn) {
      this.loadMoreBtn.style.display = 'block';
    }

    // Load first page
    await this.loadMore();
  }

  /**
   * Destroy the loader and clean up
   */
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
    if (this.loadMoreBtn) {
      this.loadMoreBtn.remove();
    }
  }
}


/**
 * ModuleLoader - Specialized loader for course module tree
 *
 * Features:
 * - Lazy loads module content (lessons/activities) on expand
 * - Caches loaded modules to avoid re-fetching
 * - Shows skeleton while loading
 */
class ModuleLoader {
  /**
   * Create a module loader
   *
   * @param {string} courseId Course identifier
   * @param {Object} options Configuration options
   */
  constructor(courseId, options = {}) {
    this.courseId = courseId;
    this.onModuleLoaded = options.onModuleLoaded || (() => {});
    this.onError = options.onError || ((err) => console.error(err));

    // Cache of loaded module content
    this.loadedModules = new Map();

    // Track loading state per module
    this.loadingModules = new Set();
  }

  /**
   * Check if module content is already loaded
   *
   * @param {string} moduleId Module identifier
   * @returns {boolean} True if loaded
   */
  isLoaded(moduleId) {
    return this.loadedModules.has(moduleId);
  }

  /**
   * Check if module is currently loading
   *
   * @param {string} moduleId Module identifier
   * @returns {boolean} True if loading
   */
  isLoading(moduleId) {
    return this.loadingModules.has(moduleId);
  }

  /**
   * Load module content (lessons and activities) on demand
   *
   * @param {string} moduleId Module identifier
   * @returns {Promise<Object>} Module content with lessons and activities
   */
  async loadModuleContent(moduleId) {
    // Return cached content if already loaded
    if (this.isLoaded(moduleId)) {
      return this.loadedModules.get(moduleId);
    }

    // Prevent concurrent loads of same module
    if (this.isLoading(moduleId)) {
      // Wait for existing load to complete
      return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
          if (!this.isLoading(moduleId)) {
            clearInterval(checkInterval);
            resolve(this.loadedModules.get(moduleId));
          }
        }, 100);
      });
    }

    this.loadingModules.add(moduleId);

    try {
      // Show skeleton in UI
      this.showSkeleton(moduleId);

      // Fetch module with lessons and activities
      const response = await fetch(`/api/courses/${this.courseId}/modules/${moduleId}`);
      if (!response.ok) {
        throw new Error(`Failed to load module: ${response.statusText}`);
      }

      const moduleData = await response.json();

      // Cache the loaded content
      this.loadedModules.set(moduleId, moduleData);

      // Hide skeleton
      this.hideSkeleton(moduleId);

      // Notify callback
      this.onModuleLoaded(moduleId, moduleData);

      return moduleData;
    } catch (error) {
      this.onError(error);
      this.hideSkeleton(moduleId);
      throw error;
    } finally {
      this.loadingModules.delete(moduleId);
    }
  }

  /**
   * Show loading skeleton for module
   *
   * @param {string} moduleId Module identifier
   */
  showSkeleton(moduleId) {
    const moduleElement = document.querySelector(`[data-module-id="${moduleId}"]`);
    if (!moduleElement) return;

    const childrenContainer = moduleElement.querySelector('.tree-children');
    if (!childrenContainer) return;

    // Add skeleton items
    const skeleton = `
      <div class="tree-skeleton">
        <div class="skeleton-line" style="width: 80%; height: 1rem; background: var(--color-border, #ccc); border-radius: 0.25rem; margin: 0.5rem 0;"></div>
        <div class="skeleton-line" style="width: 60%; height: 1rem; background: var(--color-border, #ccc); border-radius: 0.25rem; margin: 0.5rem 0;"></div>
        <div class="skeleton-line" style="width: 70%; height: 1rem; background: var(--color-border, #ccc); border-radius: 0.25rem; margin: 0.5rem 0;"></div>
      </div>
    `;
    childrenContainer.innerHTML = skeleton;
  }

  /**
   * Hide loading skeleton for module
   *
   * @param {string} moduleId Module identifier
   */
  hideSkeleton(moduleId) {
    const moduleElement = document.querySelector(`[data-module-id="${moduleId}"]`);
    if (!moduleElement) return;

    const skeleton = moduleElement.querySelector('.tree-skeleton');
    if (skeleton) {
      skeleton.remove();
    }
  }

  /**
   * Clear cache for specific module or all modules
   *
   * @param {string} moduleId Optional module ID to clear, or clears all if omitted
   */
  clearCache(moduleId = null) {
    if (moduleId) {
      this.loadedModules.delete(moduleId);
    } else {
      this.loadedModules.clear();
    }
  }

  /**
   * Preload module content in background
   *
   * @param {string} moduleId Module identifier
   */
  async preload(moduleId) {
    if (!this.isLoaded(moduleId) && !this.isLoading(moduleId)) {
      await this.loadModuleContent(moduleId);
    }
  }
}


// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { LazyLoader, ModuleLoader };
}
