/**
 * Dashboard Controller - Course management with modal dialogs
 */
class DashboardController {
  constructor() {
    this.createCourseModal = null;
    this.deleteCourseModal = null;
    this.importCourseModal = null;
    this.courseToDelete = null;
    this.courseTitleToDelete = '';
    this.currentView = 'grid';
  }

  init() {
    // Initialize modals
    this.createCourseModal = new Modal('create-course-modal');
    this.deleteCourseModal = new Modal('delete-course-modal');
    this.importCourseModal = new Modal('import-course-modal');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
    }

    // Load saved view preference
    this.currentView = localStorage.getItem('dashboard-view') || 'grid';
    this.setView(this.currentView);

    // Bind event handlers
    this.bindEventHandlers();
  }

  bindEventHandlers() {
    // New Course buttons (support both IDs for compatibility)
    const btnNewCourse = document.getElementById('create-course-btn') || document.getElementById('btn-new-course');
    const btnNewCourseEmpty = document.getElementById('btn-new-course-empty');

    if (btnNewCourse) {
      btnNewCourse.addEventListener('click', () => this.showCreateModal());
    }
    if (btnNewCourseEmpty) {
      btnNewCourseEmpty.addEventListener('click', () => this.showCreateModal());
    }

    // Create course form submit
    const createForm = document.getElementById('create-course-form');
    if (createForm) {
      createForm.addEventListener('submit', (e) => this.handleCreateSubmit(e));
    }

    // Delete confirmation button
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    if (btnConfirmDelete) {
      btnConfirmDelete.addEventListener('click', () => this.handleDeleteConfirm());
    }

    // Import button and form
    const btnImport = document.getElementById('import-course-btn');
    if (btnImport) {
      btnImport.addEventListener('click', () => this.showImportModal());
    }

    const importForm = document.getElementById('import-course-form');
    if (importForm) {
      importForm.addEventListener('submit', (e) => this.handleImportSubmit(e));
    }

    // Import tabs
    document.querySelectorAll('.import-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchImportTab(tab.dataset.tab));
    });

    // File upload area
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileInput = document.getElementById('import-file');
    if (fileUploadArea && fileInput) {
      fileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUploadArea.classList.add('dragover');
      });
      fileUploadArea.addEventListener('dragleave', () => {
        fileUploadArea.classList.remove('dragover');
      });
      fileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          fileInput.files = e.dataTransfer.files;
          this.updateFileDisplay(fileInput.files[0]);
        }
      });
      fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
          this.updateFileDisplay(fileInput.files[0]);
        }
      });
    }

    // Clear file button
    const btnClearFile = document.querySelector('.btn-clear-file');
    if (btnClearFile) {
      btnClearFile.addEventListener('click', (e) => {
        e.stopPropagation();
        this.clearFileSelection();
      });
    }

    // View toggle buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.dataset.view;
        this.setView(view);
      });
    });

    // Bind course card buttons using event delegation for all views
    this.bindCourseActions('.course-grid');
    this.bindCourseActions('.course-list');
    this.bindCourseActions('.course-compact');
  }

  bindCourseActions(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (container) {
      container.addEventListener('click', (e) => {
        const openBtn = e.target.closest('.btn-open');
        const deleteBtn = e.target.closest('.btn-delete');

        if (openBtn) {
          const courseId = openBtn.dataset.courseId;
          this.viewCourse(courseId);
        } else if (deleteBtn) {
          const courseId = deleteBtn.dataset.courseId;
          const courseTitle = deleteBtn.dataset.courseTitle;
          this.showDeleteModal(courseId, courseTitle);
        }
      });
    }
  }

  setView(view) {
    this.currentView = view;
    localStorage.setItem('dashboard-view', view);

    // Update button states
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Update view visibility
    document.querySelectorAll('.view-grid, .view-list, .view-compact').forEach(el => {
      el.classList.remove('active');
    });
    const activeView = document.querySelector(`.view-${view}`);
    if (activeView) {
      activeView.classList.add('active');
    }
  }

  showImportModal() {
    // Reset form
    const form = document.getElementById('import-course-form');
    if (form) {
      form.reset();
    }
    this.clearFileSelection();
    this.switchImportTab('file');
    this.importCourseModal.open();
  }

  switchImportTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.import-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });

    // Update tab content
    document.querySelectorAll('.import-tab-content').forEach(c => {
      c.classList.toggle('active', c.dataset.content === tab);
    });
  }

  updateFileDisplay(file) {
    const prompt = document.querySelector('.file-upload-prompt');
    const selected = document.querySelector('.file-selected');
    const fileName = document.querySelector('.file-name');

    if (prompt && selected && fileName) {
      prompt.style.display = 'none';
      selected.style.display = 'flex';
      fileName.textContent = file.name;
    }
  }

  clearFileSelection() {
    const fileInput = document.getElementById('import-file');
    const prompt = document.querySelector('.file-upload-prompt');
    const selected = document.querySelector('.file-selected');

    if (fileInput) {
      fileInput.value = '';
    }
    if (prompt) {
      prompt.style.display = 'block';
    }
    if (selected) {
      selected.style.display = 'none';
    }
  }

  async handleImportSubmit(e) {
    e.preventDefault();

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Importing...';

    try {
      const activeTab = document.querySelector('.import-tab.active').dataset.tab;
      const newIds = document.getElementById('import-new-ids').checked;
      const includeContent = document.getElementById('import-include-content').checked;

      let courseData;

      if (activeTab === 'file') {
        const fileInput = document.getElementById('import-file');
        if (!fileInput.files.length) {
          throw new Error('Please select a file to import');
        }

        const file = fileInput.files[0];
        if (file.name.endsWith('.json')) {
          const text = await file.text();
          courseData = JSON.parse(text);
        } else if (file.name.endsWith('.zip')) {
          toast.error('ZIP import is not yet implemented');
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
          return;
        } else {
          throw new Error('Unsupported file type');
        }
      } else {
        const jsonText = document.getElementById('import-json').value.trim();
        if (!jsonText) {
          throw new Error('Please paste course JSON');
        }
        courseData = JSON.parse(jsonText);
      }

      // Send to import API
      const result = await api.post('/courses/import', {
        course_data: courseData,
        new_ids: newIds,
        include_content: includeContent
      });

      this.importCourseModal.close();
      toast.success(`Course "${result.title}" imported successfully`);

      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (error) {
      toast.error(`Import failed: ${error.message}`);
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  }

  showCreateModal() {
    // Reset form
    const form = document.getElementById('create-course-form');
    if (form) {
      form.reset();
    }

    // Open modal
    this.createCourseModal.open();

    // Focus title field
    setTimeout(() => {
      const titleInput = document.getElementById('course-title');
      if (titleInput) {
        titleInput.focus();
      }
    }, 150);
  }

  async handleCreateSubmit(e) {
    e.preventDefault();

    const titleInput = document.getElementById('course-title');
    const descriptionInput = document.getElementById('course-description');

    const title = titleInput.value.trim();
    const description = descriptionInput.value.trim();

    // Validate title
    if (!title) {
      toast.error('Course title is required');
      titleInput.focus();
      return;
    }

    // Disable form while submitting
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    try {
      const course = await api.post('/courses', { title, description });

      // Close modal
      this.createCourseModal.close();

      // Show success toast
      toast.success(`Course "${course.title}" created successfully`);

      // Reload page to show new course
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (error) {
      toast.error(`Error creating course: ${error.message}`);
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  }

  showDeleteModal(courseId, courseTitle) {
    this.courseToDelete = courseId;
    this.courseTitleToDelete = courseTitle;

    // Update modal text with course title
    const titleElement = document.querySelector('.course-title-to-delete');
    if (titleElement) {
      titleElement.textContent = courseTitle;
    }

    // Open modal
    this.deleteCourseModal.open();
  }

  async handleDeleteConfirm() {
    if (!this.courseToDelete) return;

    // Disable button while deleting
    const deleteBtn = document.getElementById('btn-confirm-delete');
    const originalText = deleteBtn.textContent;
    deleteBtn.disabled = true;
    deleteBtn.textContent = 'Deleting...';

    try {
      await api.delete(`/courses/${this.courseToDelete}`);

      // Close modal
      this.deleteCourseModal.close();

      // Show success toast
      toast.success(`Course "${this.courseTitleToDelete}" deleted successfully`);

      // Remove card from DOM
      const card = document.querySelector(`[data-course-id="${this.courseToDelete}"]`);
      if (card) {
        card.style.transition = 'opacity 0.3s, transform 0.3s';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        setTimeout(() => {
          card.remove();

          // Check if grid is now empty
          const remainingCards = document.querySelectorAll('.course-card');
          if (remainingCards.length === 0) {
            // Reload to show empty state
            window.location.reload();
          }
        }, 300);
      }

      // Reset state
      this.courseToDelete = null;
      this.courseTitleToDelete = '';
    } catch (error) {
      toast.error(`Error deleting course: ${error.message}`);
      deleteBtn.disabled = false;
      deleteBtn.textContent = originalText;
    }
  }

  viewCourse(courseId) {
    // Navigate to planner page
    window.location.href = `/courses/${courseId}/planner`;
  }
}

// Initialize dashboard controller when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Remove loading class to hide skeleton
  document.body.classList.remove('loading');

  const dashboardController = new DashboardController();
  dashboardController.init();

  // Export for debugging
  window.dashboardController = dashboardController;
});
