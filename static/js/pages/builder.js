/**
 * Builder Controller - Course structure management with tree and detail panels
 *
 * Manages:
 * - Hierarchical tree display of course structure
 * - Node selection and detail panel updates
 * - CRUD operations for modules, lessons, activities
 * - Drag-drop reordering within same level
 * - Inline editing of item properties
 */
class BuilderController {
  constructor(courseId) {
    this.courseId = courseId;
    this.course = null;
    this.tree = null;

    // Selected item state
    this.selectedItem = null;
    this.selectedType = null;

    // Modals
    this.addModuleModal = null;
    this.addLessonModal = null;
    this.addActivityModal = null;
    this.deleteConfirmModal = null;

    // For delete confirmation
    this.deleteItemId = null;
    this.deleteItemType = null;
    this.deleteItemName = null;
    this.deleteParentId = null;

    // Module lazy loader
    this.moduleLoader = null;

    // Prerequisite picker
    this.prerequisitePickerModal = null;
    this.selectedPrerequisites = [];
  }

  async init() {
    // Initialize modals
    this.addModuleModal = new Modal('add-module-modal');
    this.addLessonModal = new Modal('add-lesson-modal');
    this.addActivityModal = new Modal('add-activity-modal');
    this.deleteConfirmModal = new Modal('delete-confirm-modal');
    this.prerequisitePickerModal = new Modal('prerequisite-picker-modal');

    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
      this.bindHelpHandlers();
    }

    // Initialize module lazy loader
    if (window.ModuleLoader) {
      this.moduleLoader = new ModuleLoader(this.courseId, {
        onModuleLoaded: (moduleId, moduleData) => {
          // Update tree with loaded module content
          this.onModuleContentLoaded(moduleId, moduleData);
        },
        onError: (error) => {
          toast.error(`Failed to load module: ${error.message}`);
        }
      });
    }

    // Initialize tree
    this.tree = new HierarchicalTree('course-tree', {
      onSelect: (nodeId, nodeType) => this.handleSelect(nodeId, nodeType),
      onReorder: (itemId, itemType, oldIndex, newIndex, parentId) =>
        this.handleReorder(itemId, itemType, oldIndex, newIndex, parentId),
      onExpand: (nodeId, nodeType) => this.handleExpand(nodeId, nodeType),
      storageKey: `builder_tree_${this.courseId}`
    });

    // Bind event handlers
    this.bindEventHandlers();

    // Add keyboard shortcut for help
    document.addEventListener('keydown', (e) => {
      if (e.key === 'F1') {
        e.preventDefault();
        this.showContextualHelp();
      }
    });

    // Load course data
    await this.loadCourse();
  }

  /**
   * Bind all event handlers
   */
  bindEventHandlers() {
    // Add buttons in tree panel
    const btnAddModule = document.getElementById('btn-add-module');
    if (btnAddModule) {
      btnAddModule.addEventListener('click', () => this.showAddModuleModal());
    }

    const btnExpandAll = document.getElementById('btn-expand-all');
    if (btnExpandAll) {
      btnExpandAll.addEventListener('click', () => this.tree.expandAll());
    }

    const btnCollapseAll = document.getElementById('btn-collapse-all');
    if (btnCollapseAll) {
      btnCollapseAll.addEventListener('click', () => this.tree.collapseAll());
    }

    // Add buttons in detail panel
    const btnAddLesson = document.getElementById('btn-add-lesson');
    if (btnAddLesson) {
      btnAddLesson.addEventListener('click', () => this.showAddLessonModal());
    }

    const btnAddActivity = document.getElementById('btn-add-activity');
    if (btnAddActivity) {
      btnAddActivity.addEventListener('click', () => this.showAddActivityModal());
    }

    // Delete buttons in detail panel
    const btnDeleteModule = document.getElementById('btn-delete-module');
    if (btnDeleteModule) {
      btnDeleteModule.addEventListener('click', () => this.showDeleteConfirm('module'));
    }

    const btnDeleteLesson = document.getElementById('btn-delete-lesson');
    if (btnDeleteLesson) {
      btnDeleteLesson.addEventListener('click', () => this.showDeleteConfirm('lesson'));
    }

    const btnDeleteActivity = document.getElementById('btn-delete-activity');
    if (btnDeleteActivity) {
      btnDeleteActivity.addEventListener('click', () => this.showDeleteConfirm('activity'));
    }

    // Generate content button
    const btnGenerateContent = document.getElementById('btn-generate-content');
    if (btnGenerateContent) {
      btnGenerateContent.addEventListener('click', () => this.navigateToStudio());
    }

    // Form submissions
    const addModuleForm = document.getElementById('add-module-form');
    if (addModuleForm) {
      addModuleForm.addEventListener('submit', (e) => this.handleAddModule(e));
    }

    const addLessonForm = document.getElementById('add-lesson-form');
    if (addLessonForm) {
      addLessonForm.addEventListener('submit', (e) => this.handleAddLesson(e));
    }

    const addActivityForm = document.getElementById('add-activity-form');
    if (addActivityForm) {
      addActivityForm.addEventListener('submit', (e) => this.handleAddActivity(e));
    }

    // Delete confirmation
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    if (btnConfirmDelete) {
      btnConfirmDelete.addEventListener('click', () => this.handleDelete());
    }

    // Prerequisite buttons
    const btnAddPrerequisite = document.getElementById('btn-add-prerequisite');
    if (btnAddPrerequisite) {
      btnAddPrerequisite.addEventListener('click', () => this.showPrerequisitePicker());
    }

    const btnConfirmPrerequisites = document.getElementById('btn-confirm-prerequisites');
    if (btnConfirmPrerequisites) {
      btnConfirmPrerequisites.addEventListener('click', () => this.savePrerequisites());
    }

    // Inline edit handlers
    this.bindInlineEditHandlers();
  }

  /**
   * Bind inline edit handlers for blur save
   */
  bindInlineEditHandlers() {
    // Module inline edits
    const moduleTitle = document.getElementById('module-title-input');
    const moduleDesc = document.getElementById('module-description-input');
    const moduleFlowMode = document.getElementById('module-flow-mode-select');

    if (moduleTitle) {
      moduleTitle.addEventListener('blur', () => this.handleInlineEdit('module', 'title', moduleTitle.value));
    }
    if (moduleDesc) {
      moduleDesc.addEventListener('blur', () => this.handleInlineEdit('module', 'description', moduleDesc.value));
    }
    if (moduleFlowMode) {
      moduleFlowMode.addEventListener('change', () => this.handleFlowModeChange(moduleFlowMode.value));
    }

    // Lesson inline edits
    const lessonTitle = document.getElementById('lesson-title-input');
    if (lessonTitle) {
      lessonTitle.addEventListener('blur', () => this.handleInlineEdit('lesson', 'title', lessonTitle.value));
    }

    // Activity inline edits
    const activityTitle = document.getElementById('activity-title-input');
    const activityContentType = document.getElementById('activity-content-type-select');
    const activityType = document.getElementById('activity-type-select');
    const activityWwhaa = document.getElementById('activity-wwhaa-select');

    if (activityTitle) {
      activityTitle.addEventListener('blur', () => this.handleInlineEdit('activity', 'title', activityTitle.value));
    }
    if (activityContentType) {
      activityContentType.addEventListener('change', () => this.handleInlineEdit('activity', 'content_type', activityContentType.value));
    }
    if (activityType) {
      activityType.addEventListener('change', () => this.handleInlineEdit('activity', 'activity_type', activityType.value));
    }
    if (activityWwhaa) {
      activityWwhaa.addEventListener('change', () => this.handleInlineEdit('activity', 'wwhaa_phase', activityWwhaa.value));
    }
  }

  /**
   * Load course data from API
   */
  async loadCourse() {
    try {
      this.course = await api.get(`/courses/${this.courseId}`);
      this.tree.render(this.course);
    } catch (error) {
      toast.error(`Failed to load course: ${error.message}`);
    }
  }

  /**
   * Handle node expansion in tree (lazy load module content)
   */
  async handleExpand(nodeId, nodeType) {
    if (nodeType === 'module' && this.moduleLoader) {
      // Check if module content already loaded
      if (!this.moduleLoader.isLoaded(nodeId)) {
        await this.moduleLoader.loadModuleContent(nodeId);
      }
    }
  }

  /**
   * Callback when module content is loaded
   */
  onModuleContentLoaded(moduleId, moduleData) {
    // Update course data with loaded module content
    const module = this.findModule(moduleId);
    if (module) {
      module.lessons = moduleData.lessons || [];
      // Re-render the tree to show the loaded content
      if (this.tree) {
        this.tree.render(this.course);
      }
    }
  }

  /**
   * Handle node selection in tree
   */
  async handleSelect(nodeId, nodeType) {
    this.selectedItem = nodeId;
    this.selectedType = nodeType;

    // Hide all detail views
    this.hideAllDetailViews();

    // Show appropriate detail view
    if (nodeType === 'module') {
      await this.showModuleDetail(nodeId);
    } else if (nodeType === 'lesson') {
      await this.showLessonDetail(nodeId);
    } else if (nodeType === 'activity') {
      await this.showActivityDetail(nodeId);
    }
  }

  /**
   * Hide all detail views and show empty state
   */
  hideAllDetailViews() {
    document.getElementById('detail-empty').style.display = 'none';
    document.getElementById('detail-module').style.display = 'none';
    document.getElementById('detail-lesson').style.display = 'none';
    document.getElementById('detail-activity').style.display = 'none';
  }

  /**
   * Show module detail view
   */
  async showModuleDetail(moduleId) {
    const module = this.findModule(moduleId);
    if (!module) return;

    // Update detail view
    document.getElementById('module-title').textContent = module.title;
    document.getElementById('module-title-input').value = module.title;
    document.getElementById('module-description-input').value = module.description || '';
    document.getElementById('module-flow-mode-select').value = module.flow_mode || 'sequential';
    document.getElementById('module-order').textContent = module.order + 1;
    document.getElementById('module-lesson-count').textContent = module.lessons?.length || 0;

    // Show the view
    document.getElementById('detail-module').style.display = 'block';
  }

  /**
   * Show lesson detail view
   */
  async showLessonDetail(lessonId) {
    const { lesson, module } = this.findLesson(lessonId);
    if (!lesson) return;

    // Update detail view
    document.getElementById('lesson-title').textContent = lesson.title;
    document.getElementById('lesson-title-input').value = lesson.title;
    document.getElementById('lesson-order').textContent = lesson.order + 1;
    document.getElementById('lesson-activity-count').textContent = lesson.activities?.length || 0;
    document.getElementById('lesson-module-name').textContent = module?.title || '-';

    // Show the view
    document.getElementById('detail-lesson').style.display = 'block';
  }

  /**
   * Show activity detail view
   */
  async showActivityDetail(activityId) {
    const { activity, lesson } = this.findActivity(activityId);
    if (!activity) return;

    // Update detail view
    document.getElementById('activity-title').textContent = activity.title;
    document.getElementById('activity-title-input').value = activity.title;
    document.getElementById('activity-content-type-select').value = activity.content_type || 'video';
    document.getElementById('activity-type-select').value = activity.activity_type || 'video_lecture';
    document.getElementById('activity-wwhaa-select').value = activity.wwhaa_phase || 'content';
    document.getElementById('activity-build-state').textContent = this.formatBuildState(activity.build_state);
    document.getElementById('activity-lesson-name').textContent = lesson?.title || '-';

    // Update state badge
    const stateBadge = document.getElementById('activity-state-badge');
    stateBadge.textContent = this.formatBuildState(activity.build_state);
    stateBadge.className = 'badge state-' + (activity.build_state || 'draft');

    // Render prerequisites list
    this.renderPrerequisitesList(activity.prerequisite_ids || []);

    // Show the view
    document.getElementById('detail-activity').style.display = 'block';
  }

  /**
   * Format build state for display
   */
  formatBuildState(state) {
    if (!state) return 'Draft';
    return state.charAt(0).toUpperCase() + state.slice(1);
  }

  /**
   * Find module by ID
   */
  findModule(moduleId) {
    return this.course?.modules?.find(m => m.id === moduleId);
  }

  /**
   * Find lesson by ID and return with parent module
   */
  findLesson(lessonId) {
    for (const module of (this.course?.modules || [])) {
      const lesson = module.lessons?.find(l => l.id === lessonId);
      if (lesson) {
        return { lesson, module };
      }
    }
    return { lesson: null, module: null };
  }

  /**
   * Find activity by ID and return with parent lesson
   */
  findActivity(activityId) {
    for (const module of (this.course?.modules || [])) {
      for (const lesson of (module.lessons || [])) {
        const activity = lesson.activities?.find(a => a.id === activityId);
        if (activity) {
          return { activity, lesson, module };
        }
      }
    }
    return { activity: null, lesson: null, module: null };
  }

  /**
   * Handle reorder from tree drag-drop
   */
  async handleReorder(itemId, itemType, oldIndex, newIndex, parentId) {
    try {
      let endpoint = '';

      if (itemType === 'module') {
        endpoint = `/courses/${this.courseId}/modules/reorder`;
      } else if (itemType === 'lesson') {
        endpoint = `/courses/${this.courseId}/modules/${parentId}/lessons/reorder`;
      } else if (itemType === 'activity') {
        endpoint = `/courses/${this.courseId}/lessons/${parentId}/activities/reorder`;
      }

      await api.put(endpoint, {
        old_index: oldIndex,
        new_index: newIndex
      });

      toast.success('Item reordered successfully');

      // Reload course data and refresh tree
      await this.loadCourse();

    } catch (error) {
      toast.error(`Failed to reorder: ${error.message}`);
      // Reload to restore correct order
      await this.loadCourse();
    }
  }

  /**
   * Handle inline edit save
   */
  async handleInlineEdit(itemType, field, value) {
    if (!this.selectedItem) return;

    // Get current value to avoid unnecessary saves
    let currentValue = '';
    if (itemType === 'module') {
      const module = this.findModule(this.selectedItem);
      currentValue = module?.[field] || '';
    } else if (itemType === 'lesson') {
      const { lesson } = this.findLesson(this.selectedItem);
      currentValue = lesson?.[field] || '';
    } else if (itemType === 'activity') {
      const { activity } = this.findActivity(this.selectedItem);
      currentValue = activity?.[field] || '';
    }

    // Don't save if value hasn't changed
    if (value === currentValue) return;

    try {
      let endpoint = '';

      if (itemType === 'module') {
        endpoint = `/courses/${this.courseId}/modules/${this.selectedItem}`;
      } else if (itemType === 'lesson') {
        endpoint = `/courses/${this.courseId}/lessons/${this.selectedItem}`;
      } else if (itemType === 'activity') {
        endpoint = `/courses/${this.courseId}/activities/${this.selectedItem}`;
      }

      await api.put(endpoint, { [field]: value });
      toast.success('Saved');

      // Reload course data and refresh tree
      await this.loadCourse();

    } catch (error) {
      toast.error(`Failed to save: ${error.message}`);
    }
  }

  /**
   * Show add module modal
   */
  showAddModuleModal() {
    document.getElementById('add-module-form').reset();
    this.addModuleModal.open();
    setTimeout(() => {
      document.getElementById('new-module-title').focus();
    }, 150);
  }

  /**
   * Show add lesson modal
   */
  showAddLessonModal() {
    if (!this.selectedItem || this.selectedType !== 'module') {
      toast.error('Please select a module first');
      return;
    }

    const module = this.findModule(this.selectedItem);
    if (!module) return;

    document.getElementById('add-lesson-form').reset();
    document.getElementById('lesson-parent-module').value = module.title;
    document.getElementById('lesson-parent-module-id').value = module.id;

    this.addLessonModal.open();
    setTimeout(() => {
      document.getElementById('new-lesson-title').focus();
    }, 150);
  }

  /**
   * Show add activity modal
   */
  showAddActivityModal() {
    if (!this.selectedItem || this.selectedType !== 'lesson') {
      toast.error('Please select a lesson first');
      return;
    }

    const { lesson } = this.findLesson(this.selectedItem);
    if (!lesson) return;

    document.getElementById('add-activity-form').reset();
    document.getElementById('activity-parent-lesson').value = lesson.title;
    document.getElementById('activity-parent-lesson-id').value = lesson.id;

    this.addActivityModal.open();
    setTimeout(() => {
      document.getElementById('new-activity-title').focus();
    }, 150);
  }

  /**
   * Handle add module form submission
   */
  async handleAddModule(e) {
    e.preventDefault();

    const title = document.getElementById('new-module-title').value.trim();
    const description = document.getElementById('new-module-description').value.trim();

    if (!title) {
      toast.error('Module title is required');
      return;
    }

    try {
      await api.post(`/courses/${this.courseId}/modules`, {
        title,
        description
      });

      this.addModuleModal.close();
      toast.success('Module added successfully');

      // Reload and refresh
      await this.loadCourse();

    } catch (error) {
      toast.error(`Failed to add module: ${error.message}`);
    }
  }

  /**
   * Handle add lesson form submission
   */
  async handleAddLesson(e) {
    e.preventDefault();

    const moduleId = document.getElementById('lesson-parent-module-id').value;
    const title = document.getElementById('new-lesson-title').value.trim();

    if (!title) {
      toast.error('Lesson title is required');
      return;
    }

    try {
      await api.post(`/courses/${this.courseId}/modules/${moduleId}/lessons`, {
        title
      });

      this.addLessonModal.close();
      toast.success('Lesson added successfully');

      // Reload and refresh
      await this.loadCourse();

    } catch (error) {
      toast.error(`Failed to add lesson: ${error.message}`);
    }
  }

  /**
   * Handle add activity form submission
   */
  async handleAddActivity(e) {
    e.preventDefault();

    const lessonId = document.getElementById('activity-parent-lesson-id').value;
    const title = document.getElementById('new-activity-title').value.trim();
    const contentType = document.getElementById('new-activity-content-type').value;
    const activityType = document.getElementById('new-activity-type').value;

    if (!title) {
      toast.error('Activity title is required');
      return;
    }

    try {
      await api.post(`/courses/${this.courseId}/lessons/${lessonId}/activities`, {
        title,
        content_type: contentType,
        activity_type: activityType
      });

      this.addActivityModal.close();
      toast.success('Activity added successfully');

      // Reload and refresh
      await this.loadCourse();

    } catch (error) {
      toast.error(`Failed to add activity: ${error.message}`);
    }
  }

  /**
   * Show delete confirmation modal
   */
  showDeleteConfirm(itemType) {
    if (!this.selectedItem) return;

    let itemName = '';
    let showCascade = false;

    if (itemType === 'module') {
      const module = this.findModule(this.selectedItem);
      itemName = module?.title || 'this module';
      showCascade = (module?.lessons?.length || 0) > 0;
    } else if (itemType === 'lesson') {
      const { lesson } = this.findLesson(this.selectedItem);
      itemName = lesson?.title || 'this lesson';
      showCascade = (lesson?.activities?.length || 0) > 0;
    } else if (itemType === 'activity') {
      const { activity, lesson } = this.findActivity(this.selectedItem);
      itemName = activity?.title || 'this activity';
      this.deleteParentId = lesson?.id;
    }

    this.deleteItemId = this.selectedItem;
    this.deleteItemType = itemType;
    this.deleteItemName = itemName;

    document.getElementById('delete-item-name').textContent = itemName;
    document.getElementById('delete-cascade-warning').style.display = showCascade ? 'block' : 'none';

    this.deleteConfirmModal.open();
  }

  /**
   * Handle delete confirmation
   */
  async handleDelete() {
    if (!this.deleteItemId || !this.deleteItemType) return;

    try {
      let endpoint = '';

      if (this.deleteItemType === 'module') {
        endpoint = `/courses/${this.courseId}/modules/${this.deleteItemId}`;
      } else if (this.deleteItemType === 'lesson') {
        endpoint = `/courses/${this.courseId}/lessons/${this.deleteItemId}`;
      } else if (this.deleteItemType === 'activity') {
        endpoint = `/courses/${this.courseId}/activities/${this.deleteItemId}`;
      }

      await api.delete(endpoint);

      this.deleteConfirmModal.close();
      toast.success(`${this.deleteItemName} deleted successfully`);

      // Clear selection
      this.selectedItem = null;
      this.selectedType = null;

      // Hide detail views
      this.hideAllDetailViews();
      document.getElementById('detail-empty').style.display = 'flex';

      // Reload and refresh
      await this.loadCourse();

      // Clear delete state
      this.deleteItemId = null;
      this.deleteItemType = null;
      this.deleteItemName = null;
      this.deleteParentId = null;

    } catch (error) {
      toast.error(`Failed to delete: ${error.message}`);
    }
  }

  /**
   * Navigate to Studio page for content generation
   */
  navigateToStudio() {
    if (!this.selectedItem || this.selectedType !== 'activity') {
      toast.error('Please select an activity');
      return;
    }

    // Navigate to studio with activity ID as query param
    window.location.href = `/courses/${this.courseId}/studio?activity=${this.selectedItem}`;
  }

  // ===========================
  // Flow Control & Prerequisites
  // ===========================

  /**
   * Handle module flow mode change
   */
  async handleFlowModeChange(flowMode) {
    if (!this.selectedItem || this.selectedType !== 'module') return;

    try {
      await api.put(`/courses/${this.courseId}/modules/${this.selectedItem}/flow-mode`, {
        flow_mode: flowMode
      });
      toast.success('Flow mode updated');
    } catch (error) {
      toast.error(`Failed to update flow mode: ${error.message}`);
      // Reload to restore correct value
      await this.loadCourse();
    }
  }

  /**
   * Render prerequisites list for current activity
   */
  renderPrerequisitesList(prerequisiteIds) {
    const container = document.getElementById('prerequisites-list');
    if (!container) return;

    if (!prerequisiteIds || prerequisiteIds.length === 0) {
      container.innerHTML = '<div class="prerequisites-empty">No prerequisites set</div>';
      return;
    }

    // Build HTML for each prerequisite
    const items = prerequisiteIds.map(prereqId => {
      const { activity, lesson, module } = this.findActivity(prereqId);
      if (!activity) {
        return `<div class="prerequisite-item">
          <span class="prerequisite-label">Unknown activity (${prereqId})</span>
          <button class="btn btn-danger btn-small btn-remove-prerequisite" data-prereq-id="${prereqId}">Remove</button>
        </div>`;
      }

      const path = `${module?.title || ''} > ${lesson?.title || ''}`;
      return `<div class="prerequisite-item">
        <span class="prerequisite-label">${activity.title}<span class="prerequisite-path">${path}</span></span>
        <button class="btn btn-danger btn-small btn-remove-prerequisite" data-prereq-id="${prereqId}">Remove</button>
      </div>`;
    });

    container.innerHTML = items.join('');

    // Bind remove handlers
    container.querySelectorAll('.btn-remove-prerequisite').forEach(btn => {
      btn.addEventListener('click', () => this.removePrerequisite(btn.dataset.prereqId));
    });
  }

  /**
   * Show prerequisite picker modal
   */
  showPrerequisitePicker() {
    if (!this.selectedItem || this.selectedType !== 'activity') return;

    const { activity } = this.findActivity(this.selectedItem);
    if (!activity) return;

    // Get current prerequisites
    this.selectedPrerequisites = [...(activity.prerequisite_ids || [])];

    // Build picker content
    const picker = document.getElementById('prerequisite-picker-list');
    if (!picker) return;

    let html = '';
    for (const module of (this.course?.modules || [])) {
      for (const lesson of (module.lessons || [])) {
        if (!lesson.activities || lesson.activities.length === 0) continue;

        html += `<div class="prerequisite-picker-group">
          <div class="prerequisite-picker-header">${module.title} > ${lesson.title}</div>`;

        for (const act of lesson.activities) {
          const isSelf = act.id === this.selectedItem;
          const isChecked = this.selectedPrerequisites.includes(act.id);
          const disabled = isSelf ? 'disabled' : '';
          const disabledClass = isSelf ? 'disabled' : '';

          html += `<div class="prerequisite-picker-item ${disabledClass}">
            <input type="checkbox" id="prereq-${act.id}" value="${act.id}"
                   ${isChecked ? 'checked' : ''} ${disabled}>
            <label for="prereq-${act.id}">${act.title}</label>
            <span class="activity-type-badge">${act.content_type || 'unknown'}</span>
          </div>`;
        }

        html += '</div>';
      }
    }

    if (!html) {
      html = '<div class="prerequisites-empty">No other activities available</div>';
    }

    picker.innerHTML = html;

    // Bind checkbox handlers
    picker.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          if (!this.selectedPrerequisites.includes(checkbox.value)) {
            this.selectedPrerequisites.push(checkbox.value);
          }
        } else {
          this.selectedPrerequisites = this.selectedPrerequisites.filter(id => id !== checkbox.value);
        }
      });
    });

    this.prerequisitePickerModal.open();
  }

  /**
   * Save selected prerequisites
   */
  async savePrerequisites() {
    if (!this.selectedItem || this.selectedType !== 'activity') return;

    try {
      await api.put(`/courses/${this.courseId}/activities/${this.selectedItem}/prerequisites`, {
        prerequisite_ids: this.selectedPrerequisites
      });

      this.prerequisitePickerModal.close();
      toast.success('Prerequisites updated');

      // Reload and refresh display
      await this.loadCourse();

      // Re-show activity detail
      if (this.selectedItem) {
        await this.showActivityDetail(this.selectedItem);
      }

    } catch (error) {
      toast.error(`Failed to update prerequisites: ${error.message}`);
    }
  }

  /**
   * Remove a single prerequisite
   */
  async removePrerequisite(prereqId) {
    if (!this.selectedItem || this.selectedType !== 'activity') return;

    const { activity } = this.findActivity(this.selectedItem);
    if (!activity) return;

    const newPrereqs = (activity.prerequisite_ids || []).filter(id => id !== prereqId);

    try {
      await api.put(`/courses/${this.courseId}/activities/${this.selectedItem}/prerequisites`, {
        prerequisite_ids: newPrereqs
      });

      toast.success('Prerequisite removed');

      // Reload and refresh display
      await this.loadCourse();

      // Re-show activity detail
      if (this.selectedItem) {
        await this.showActivityDetail(this.selectedItem);
      }

    } catch (error) {
      toast.error(`Failed to remove prerequisite: ${error.message}`);
    }
  }

  // ===========================
  // Help System
  // ===========================

  bindHelpHandlers() {
    // Handle help button clicks
    document.addEventListener('click', (e) => {
      const helpBtn = e.target.closest('.help-btn');
      if (helpBtn) {
        e.preventDefault();
        const helpTopic = helpBtn.dataset.help;
        if (helpTopic && window.help) {
          window.help.showTerm(helpTopic);
        }
      }
    });
  }

  showContextualHelp() {
    if (!window.help) return;

    // Show help based on what's selected
    if (this.selectedType === 'module') {
      window.help.showPanel('module-help', {
        title: 'Module Help',
        content: `
          <p>Modules are major thematic units in your course. They group related lessons together.</p>
          <ul>
            <li><strong>Title:</strong> Give your module a descriptive name</li>
            <li><strong>Description:</strong> Optional overview of what this module covers</li>
            <li><strong>Drag to reorder:</strong> Change module sequence by dragging in the tree</li>
          </ul>
        `
      });
    } else if (this.selectedType === 'lesson') {
      window.help.showPanel('lesson-help', {
        title: 'Lesson Help',
        content: `
          <p>Lessons are focused learning sessions within a module. Each lesson contains multiple activities.</p>
          <ul>
            <li><strong>Title:</strong> Specific, actionable lesson name</li>
            <li><strong>Activities:</strong> Videos, readings, quizzes that deliver the lesson content</li>
            <li><strong>Drag to reorder:</strong> Change lesson sequence within the module</li>
          </ul>
        `
      });
    } else if (this.selectedType === 'activity') {
      window.help.showTerm('wwhaa');
    } else {
      window.help.showPanel('builder-help', {
        title: 'Course Builder Help',
        content: `
          <p>Build your course structure using a hierarchical tree:</p>
          <ul>
            <li><strong>Modules:</strong> Major thematic units (e.g., "Introduction to Python")</li>
            <li><strong>Lessons:</strong> Focused sessions (e.g., "Variables and Data Types")</li>
            <li><strong>Activities:</strong> Individual content pieces (videos, readings, quizzes)</li>
          </ul>
          <p>Click any item to edit its details. Drag items to reorder them.</p>
          <p><strong>Press F1</strong> anytime for contextual help.</p>
        `
      });
    }
  }
}

// Export for use
window.BuilderController = BuilderController;
