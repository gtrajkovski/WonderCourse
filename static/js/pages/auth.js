/**
 * Auth Forms - Login and Registration with validation
 */

// Email validation regex (basic format check)
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Show error on a specific form field
 * @param {HTMLElement} formGroup - The .form-group container
 * @param {string} message - Error message to display
 */
function showFieldError(formGroup, message) {
  formGroup.classList.add('has-error');
  const errorSpan = formGroup.querySelector('.form-error');
  if (errorSpan) {
    errorSpan.textContent = message;
  }
}

/**
 * Clear error from a specific form field
 * @param {HTMLElement} formGroup - The .form-group container
 */
function clearFieldError(formGroup) {
  formGroup.classList.remove('has-error');
  const errorSpan = formGroup.querySelector('.form-error');
  if (errorSpan) {
    errorSpan.textContent = '';
  }
}

/**
 * Clear all field errors in a form
 * @param {HTMLFormElement} form - The form element
 */
function clearAllErrors(form) {
  const groups = form.querySelectorAll('.form-group');
  groups.forEach(group => clearFieldError(group));
}

/**
 * Show a general form error (API errors)
 * @param {string} formId - Form element ID
 * @param {string} message - Error message
 */
function showFormError(formId, message) {
  const errorEl = document.getElementById('form-error');
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.classList.add('visible');
  }
}

/**
 * Hide the general form error
 */
function hideFormError() {
  const errorEl = document.getElementById('form-error');
  if (errorEl) {
    errorEl.classList.remove('visible');
    errorEl.textContent = '';
  }
}

/**
 * Set button loading state
 * @param {HTMLButtonElement} button - Submit button
 * @param {boolean} loading - Loading state
 * @param {string} originalText - Original button text
 */
function setButtonLoading(button, loading, originalText) {
  if (loading) {
    button.classList.add('loading');
    button.textContent = 'Please wait...';
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.textContent = originalText;
    button.disabled = false;
  }
}


/**
 * Login Form Handler
 */
class LoginForm {
  constructor(formId) {
    this.form = document.getElementById(formId);
    if (!this.form) return;

    this.submitBtn = this.form.querySelector('#submit-btn');
    this.originalBtnText = this.submitBtn ? this.submitBtn.textContent : 'Log In';

    this.form.addEventListener('submit', (e) => this.handleSubmit(e));

    // Clear errors on input
    this.form.querySelectorAll('.form-input').forEach(input => {
      input.addEventListener('input', () => {
        const group = input.closest('.form-group');
        if (group) clearFieldError(group);
        hideFormError();
      });
    });
  }

  validate() {
    let isValid = true;
    clearAllErrors(this.form);
    hideFormError();

    const email = this.form.querySelector('#email');
    const password = this.form.querySelector('#password');

    // Email validation
    if (!email.value.trim()) {
      showFieldError(email.closest('.form-group'), 'Email is required');
      isValid = false;
    } else if (!EMAIL_REGEX.test(email.value.trim())) {
      showFieldError(email.closest('.form-group'), 'Please enter a valid email address');
      isValid = false;
    }

    // Password validation
    if (!password.value) {
      showFieldError(password.closest('.form-group'), 'Password is required');
      isValid = false;
    }

    return isValid;
  }

  async handleSubmit(e) {
    e.preventDefault();

    if (!this.validate()) {
      return;
    }

    const email = this.form.querySelector('#email').value.trim();
    const password = this.form.querySelector('#password').value;

    setButtonLoading(this.submitBtn, true, this.originalBtnText);

    try {
      await window.api.post('/auth/login', { email, password });

      // Login successful, redirect to dashboard
      window.location.href = '/dashboard';
    } catch (error) {
      setButtonLoading(this.submitBtn, false, this.originalBtnText);

      // Display error from API
      const message = error.data?.error || error.message || 'Login failed. Please try again.';
      showFormError('login-form', message);
    }
  }
}


/**
 * Register Form Handler
 */
class RegisterForm {
  constructor(formId) {
    this.form = document.getElementById(formId);
    if (!this.form) return;

    this.submitBtn = this.form.querySelector('#submit-btn');
    this.originalBtnText = this.submitBtn ? this.submitBtn.textContent : 'Create Account';

    this.form.addEventListener('submit', (e) => this.handleSubmit(e));

    // Clear errors on input
    this.form.querySelectorAll('.form-input').forEach(input => {
      input.addEventListener('input', () => {
        const group = input.closest('.form-group');
        if (group) clearFieldError(group);
        hideFormError();
      });
    });
  }

  validate() {
    let isValid = true;
    clearAllErrors(this.form);
    hideFormError();

    const email = this.form.querySelector('#email');
    const password = this.form.querySelector('#password');
    const confirmPassword = this.form.querySelector('#confirm_password');

    // Email validation
    if (!email.value.trim()) {
      showFieldError(email.closest('.form-group'), 'Email is required');
      isValid = false;
    } else if (!EMAIL_REGEX.test(email.value.trim())) {
      showFieldError(email.closest('.form-group'), 'Please enter a valid email address');
      isValid = false;
    }

    // Password validation
    if (!password.value) {
      showFieldError(password.closest('.form-group'), 'Password is required');
      isValid = false;
    } else if (password.value.length < 8) {
      showFieldError(password.closest('.form-group'), 'Password must be at least 8 characters');
      isValid = false;
    }

    // Confirm password validation
    if (!confirmPassword.value) {
      showFieldError(confirmPassword.closest('.form-group'), 'Please confirm your password');
      isValid = false;
    } else if (password.value !== confirmPassword.value) {
      showFieldError(confirmPassword.closest('.form-group'), 'Passwords do not match');
      isValid = false;
    }

    return isValid;
  }

  async handleSubmit(e) {
    e.preventDefault();

    if (!this.validate()) {
      return;
    }

    const name = this.form.querySelector('#name').value.trim();
    const email = this.form.querySelector('#email').value.trim();
    const password = this.form.querySelector('#password').value;

    setButtonLoading(this.submitBtn, true, this.originalBtnText);

    try {
      await window.api.post('/auth/register', { email, password, name: name || undefined });

      // Registration successful, redirect to login with success message
      window.location.href = '/login?registered=true';
    } catch (error) {
      setButtonLoading(this.submitBtn, false, this.originalBtnText);

      // Display error from API
      const message = error.data?.error || error.message || 'Registration failed. Please try again.';
      showFormError('register-form', message);
    }
  }
}

// Export for use in templates
window.LoginForm = LoginForm;
window.RegisterForm = RegisterForm;
