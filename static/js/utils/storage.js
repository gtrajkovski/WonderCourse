/**
 * Safe Storage - localStorage wrapper with error handling
 */
class SafeStorage {
  constructor(prefix = 'cbs_') {
    this.prefix = prefix;
  }

  set(key, value) {
    try {
      const prefixedKey = `${this.prefix}${key}`;
      const serialized = JSON.stringify(value);
      localStorage.setItem(prefixedKey, serialized);
      return true;
    } catch (error) {
      if (error.name === 'QuotaExceededError') {
        console.error('localStorage quota exceeded:', error);
      } else {
        console.error('localStorage set error:', error);
      }
      return false;
    }
  }

  get(key, defaultValue = null) {
    try {
      const prefixedKey = `${this.prefix}${key}`;
      const item = localStorage.getItem(prefixedKey);
      if (item === null) {
        return defaultValue;
      }
      return JSON.parse(item);
    } catch (error) {
      console.error('localStorage get error:', error);
      return defaultValue;
    }
  }

  remove(key) {
    try {
      const prefixedKey = `${this.prefix}${key}`;
      localStorage.removeItem(prefixedKey);
      return true;
    } catch (error) {
      console.error('localStorage remove error:', error);
      return false;
    }
  }

  clear() {
    try {
      // Remove only prefixed keys
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(this.prefix)) {
          localStorage.removeItem(key);
        }
      });
      return true;
    } catch (error) {
      console.error('localStorage clear error:', error);
      return false;
    }
  }
}

/**
 * Scroll Manager - Persist and restore scroll positions
 */
class ScrollManager {
  constructor(storage) {
    this.storage = storage;
    this.scrollKey = 'scroll';
  }

  save() {
    const scrollData = {
      x: window.scrollX,
      y: window.scrollY,
      pathname: window.location.pathname,
    };
    this.storage.set(`${this.scrollKey}_${scrollData.pathname}`, scrollData);
  }

  restore() {
    const pathname = window.location.pathname;
    const scrollData = this.storage.get(`${this.scrollKey}_${pathname}`);

    if (scrollData && scrollData.pathname === pathname) {
      window.scrollTo(scrollData.x, scrollData.y);
    }
  }

  clear() {
    const pathname = window.location.pathname;
    this.storage.remove(`${this.scrollKey}_${pathname}`);
  }

  initialize() {
    // Restore scroll position on load
    window.addEventListener('load', () => {
      this.restore();
    });

    // Save scroll position before unload
    window.addEventListener('beforeunload', () => {
      this.save();
    });

    // Save periodically for SPA-like navigation
    let scrollTimeout;
    window.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        this.save();
      }, 100);
    });
  }
}

// Export global instances
window.storage = new SafeStorage();
window.scrollManager = new ScrollManager(window.storage);
