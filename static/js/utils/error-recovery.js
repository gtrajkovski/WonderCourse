/**
 * Error Recovery - Auto-retry logic and timeout handling
 */
class ErrorRecovery {
  // Operation-specific timeout thresholds (milliseconds)
  static TIMEOUTS = {
    SAVE: 30000,      // 30s for quick saves
    GENERATE: 90000,  // 90s for content generation
    TEXTBOOK: 120000, // 2min for textbook/export
    STREAM: 0,        // no timeout for SSE streams
  };

  /**
   * Fetch with automatic retry on 5xx errors
   * @param {string} url - URL to fetch
   * @param {Object} options - Fetch options
   * @param {number} maxAttempts - Maximum retry attempts (default 3)
   * @param {string} operationType - Operation type for timeout (SAVE, GENERATE, TEXTBOOK, STREAM)
   * @returns {Promise<Response>}
   */
  static async fetchWithRetry(url, options = {}, maxAttempts = 3, operationType = 'SAVE') {
    const timeout = this.TIMEOUTS[operationType] || this.TIMEOUTS.SAVE;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        // Create abort controller for timeout
        const controller = new AbortController();
        let timeoutId = null;

        if (timeout > 0) {
          timeoutId = setTimeout(() => controller.abort(), timeout);
        }

        const fetchOptions = {
          ...options,
          signal: controller.signal,
        };

        const response = await fetch(url, fetchOptions);

        if (timeoutId) {
          clearTimeout(timeoutId);
        }

        // Success - return response
        if (response.ok) {
          return response;
        }

        // 4xx errors - don't retry (client errors)
        if (response.status >= 400 && response.status < 500) {
          return response;
        }

        // 5xx errors - retry with exponential backoff
        if (response.status >= 500 && attempt < maxAttempts) {
          const backoff = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
          const jitter = Math.random() * 500;
          const delay = backoff + jitter;

          console.log(`[ErrorRecovery] Attempt ${attempt} failed with ${response.status}, retrying in ${Math.round(delay)}ms`);

          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        // Last attempt or non-5xx error
        return response;

      } catch (error) {
        // AbortError (timeout)
        if (error.name === 'AbortError') {
          console.log(`[ErrorRecovery] Request timed out after ${timeout}ms on attempt ${attempt}`);

          if (attempt < maxAttempts) {
            // Retry after timeout
            const backoff = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
            const jitter = Math.random() * 500;
            const delay = backoff + jitter;

            await new Promise(resolve => setTimeout(resolve, delay));
            continue;
          }

          // Final timeout - show timeout dialog
          throw new Error(`Request timed out after ${timeout}ms`);
        }

        // Network error
        if (attempt < maxAttempts) {
          const backoff = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
          const jitter = Math.random() * 500;
          const delay = backoff + jitter;

          console.log(`[ErrorRecovery] Network error on attempt ${attempt}, retrying in ${Math.round(delay)}ms`, error);

          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        // Final attempt failed
        throw error;
      }
    }

    // Should never reach here
    throw new Error('Max retry attempts exceeded');
  }

  /**
   * Handle API errors with appropriate UI feedback
   * @param {Error} error - Error object
   * @param {Function} retryFn - Function to call on retry
   * @param {string} context - Context description for error message
   */
  static handleApiError(error, retryFn = null, context = 'operation') {
    console.error('[ErrorRecovery] API error:', error);

    const status = error.status || error.response?.status;

    // 502/503 - Server temporarily unavailable
    if (status === 502 || status === 503) {
      this.showRetryDialog(
        'Server Temporarily Unavailable',
        'The server is experiencing issues. Please try again in a moment.',
        retryFn
      );
      return;
    }

    // 400 - Bad request
    if (status === 400) {
      const errorData = error.data || {};

      // If error has field-specific info, show inline
      if (errorData.field) {
        this.showFieldError(errorData.field, errorData.message || 'Invalid value');
        return;
      }

      // Generic 400
      window.toast?.error(errorData.error || 'Invalid request. Please check your input.');
      return;
    }

    // 401 - Unauthorized
    if (status === 401) {
      window.toast?.error('Authentication required. Redirecting to login...');
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
      return;
    }

    // 403 - Forbidden
    if (status === 403) {
      window.toast?.error('Permission denied. You do not have access to this resource.');
      return;
    }

    // 429 - Rate limited
    if (status === 429) {
      const retryAfter = error.response?.headers?.get('Retry-After');
      const message = retryAfter
        ? `Rate limit exceeded. Please try again in ${retryAfter} seconds.`
        : 'Rate limit exceeded. Please try again later.';

      window.toast?.warning(message, 5000);
      return;
    }

    // Timeout
    if (error.message?.includes('timed out')) {
      this.showTimeoutDialog(context, retryFn);
      return;
    }

    // Unknown error
    const message = error.data?.error || error.message || `Failed to complete ${context}`;
    window.toast?.error(message);
  }

  /**
   * Show retry dialog for server errors
   */
  static showRetryDialog(title, message, retryFn) {
    const dialog = document.createElement('div');
    dialog.className = 'error-dialog-overlay';
    dialog.innerHTML = `
      <div class="error-dialog">
        <h3>${title}</h3>
        <p>${message}</p>
        <div class="error-dialog-actions">
          <button class="btn btn-secondary" data-action="close">Close</button>
          ${retryFn ? '<button class="btn btn-primary" data-action="retry">Retry</button>' : ''}
        </div>
      </div>
    `;

    dialog.querySelector('[data-action="close"]').addEventListener('click', () => {
      document.body.removeChild(dialog);
    });

    if (retryFn) {
      dialog.querySelector('[data-action="retry"]').addEventListener('click', () => {
        document.body.removeChild(dialog);
        retryFn();
      });
    }

    document.body.appendChild(dialog);
  }

  /**
   * Show timeout dialog with keep waiting/retry/cancel options
   */
  static showTimeoutDialog(operationName, retryFn, cancelFn) {
    const dialog = document.createElement('div');
    dialog.className = 'error-dialog-overlay';
    dialog.innerHTML = `
      <div class="error-dialog timeout-dialog">
        <h3>Operation Taking Longer Than Expected</h3>
        <p>The ${operationName} is taking longer than usual to complete.</p>
        <p>You can keep waiting, retry the operation, or cancel it.</p>
        <div class="error-dialog-actions">
          ${cancelFn ? '<button class="btn btn-secondary" data-action="cancel">Cancel</button>' : ''}
          ${retryFn ? '<button class="btn btn-secondary" data-action="retry">Retry</button>' : ''}
          <button class="btn btn-primary" data-action="wait">Keep Waiting</button>
        </div>
      </div>
    `;

    if (cancelFn) {
      dialog.querySelector('[data-action="cancel"]').addEventListener('click', () => {
        document.body.removeChild(dialog);
        cancelFn();
      });
    }

    if (retryFn) {
      dialog.querySelector('[data-action="retry"]').addEventListener('click', () => {
        document.body.removeChild(dialog);
        retryFn();
      });
    }

    dialog.querySelector('[data-action="wait"]').addEventListener('click', () => {
      document.body.removeChild(dialog);
      // User chose to keep waiting - do nothing, let operation continue
    });

    document.body.appendChild(dialog);
  }

  /**
   * Show field-specific error
   */
  static showFieldError(fieldName, message) {
    const field = document.querySelector(`[name="${fieldName}"], #${fieldName}`);

    if (field) {
      // Add error class to field
      field.classList.add('field-error');

      // Create or update error message
      let errorMsg = field.parentElement.querySelector('.field-error-message');
      if (!errorMsg) {
        errorMsg = document.createElement('div');
        errorMsg.className = 'field-error-message';
        field.parentElement.appendChild(errorMsg);
      }
      errorMsg.textContent = message;

      // Focus the field
      field.focus();

      // Clear error on input
      const clearError = () => {
        field.classList.remove('field-error');
        if (errorMsg) {
          errorMsg.remove();
        }
        field.removeEventListener('input', clearError);
      };
      field.addEventListener('input', clearError);
    } else {
      // Field not found, show as toast
      window.toast?.error(`${fieldName}: ${message}`);
    }
  }
}

// Export to global scope
window.ErrorRecovery = ErrorRecovery;
