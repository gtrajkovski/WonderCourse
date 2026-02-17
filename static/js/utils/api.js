/**
 * API Client - Fetch wrapper with error handling
 */
class APIClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const method = options.method || 'GET';
    const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

    // Determine if we should retry (default: true for mutations, false for reads)
    const shouldRetry = options.retry !== undefined ? options.retry : isMutation;

    // Determine operation type for timeout
    const operationType = options.operationType || 'SAVE';

    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    // Add body if present
    if (options.body && typeof options.body === 'object') {
      config.body = JSON.stringify(options.body);
    }

    try {
      let response;

      // Use retry logic for mutations or if explicitly requested
      if (shouldRetry && window.ErrorRecovery) {
        response = await window.ErrorRecovery.fetchWithRetry(
          url,
          config,
          3, // maxAttempts
          operationType
        );
      } else {
        response = await fetch(url, config);
      }

      // Parse JSON response
      const data = await response.json();

      // Handle error responses
      if (!response.ok) {
        const error = new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (error) {
      // Re-throw with additional context if it's a network error
      if (!error.status) {
        error.message = `Network error: ${error.message}`;
      }
      throw error;
    }
  }

  async get(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'GET',
    });
  }

  async post(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body,
    });
  }

  async put(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body,
    });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'DELETE',
    });
  }

  async patch(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body,
    });
  }
}

// Export global instance
window.api = new APIClient();
