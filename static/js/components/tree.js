/**
 * Hierarchical Tree Component - Tree view with drag-drop reordering
 *
 * A reusable tree component for displaying hierarchical data with:
 * - Expand/collapse functionality with localStorage persistence
 * - Node selection with callback support
 * - Drag and drop reordering within the same level
 */
class HierarchicalTree {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Tree container "${containerId}" not found`);
      return;
    }

    // Callbacks
    this.onSelect = options.onSelect || (() => {});
    this.onReorder = options.onReorder || (() => {});
    this.onAdd = options.onAdd || (() => {});
    this.onDelete = options.onDelete || (() => {});

    // Drag state
    this.draggedItem = null;
    this.dragOverItem = null;
    this.dropIndicator = null;

    // Storage key for expand state
    this.storageKey = options.storageKey || `tree_expand_${containerId}`;

    // Selected node
    this.selectedNodeId = null;
    this.selectedNodeType = null;

    // Initialize
    this.createDropIndicator();
  }

  /**
   * Create the drop indicator element
   */
  createDropIndicator() {
    this.dropIndicator = document.createElement('div');
    this.dropIndicator.className = 'tree-drop-indicator';
    this.dropIndicator.style.display = 'none';
    document.body.appendChild(this.dropIndicator);
  }

  /**
   * Render the tree from course data
   * @param {Object} course - Course object with modules, lessons, activities
   */
  render(course) {
    if (!this.container) return;

    const expandedNodes = this.loadExpandState();

    let html = '<ul class="tree-root">';

    if (!course.modules || course.modules.length === 0) {
      html += '<li class="tree-empty">No modules yet. Add a module to get started.</li>';
    } else {
      course.modules.forEach((module, moduleIndex) => {
        html += this.renderModule(module, moduleIndex, expandedNodes);
      });
    }

    html += '</ul>';
    this.container.innerHTML = html;

    // Re-select previously selected node if it still exists
    if (this.selectedNodeId) {
      const node = this.container.querySelector(`[data-node-id="${this.selectedNodeId}"]`);
      if (node) {
        node.classList.add('selected');
      } else {
        this.selectedNodeId = null;
        this.selectedNodeType = null;
      }
    }

    // Initialize event handlers
    this.initEventHandlers();
    this.initDragHandlers();
  }

  /**
   * Render a module node
   */
  renderModule(module, index, expandedNodes) {
    const isExpanded = expandedNodes.has(module.id);
    const hasChildren = module.lessons && module.lessons.length > 0;

    let html = `
      <li class="tree-item tree-module ${isExpanded ? 'expanded' : ''}"
          data-node-id="${module.id}"
          data-node-type="module"
          data-index="${index}"
          draggable="true">
        <div class="tree-item-content">
          ${hasChildren ? `<span class="tree-toggle" data-toggle="${module.id}">${isExpanded ? '&#9660;' : '&#9654;'}</span>` : '<span class="tree-toggle-spacer"></span>'}
          <span class="tree-icon">&#128193;</span>
          <span class="tree-label">${this.escapeHtml(module.title)}</span>
          <span class="tree-meta">${module.lessons?.length || 0} lessons</span>
        </div>`;

    if (hasChildren) {
      html += '<ul class="tree-children">';
      module.lessons.forEach((lesson, lessonIndex) => {
        html += this.renderLesson(lesson, lessonIndex, module.id, expandedNodes);
      });
      html += '</ul>';
    }

    html += '</li>';
    return html;
  }

  /**
   * Render a lesson node
   */
  renderLesson(lesson, index, parentId, expandedNodes) {
    const isExpanded = expandedNodes.has(lesson.id);
    const hasChildren = lesson.activities && lesson.activities.length > 0;

    let html = `
      <li class="tree-item tree-lesson ${isExpanded ? 'expanded' : ''}"
          data-node-id="${lesson.id}"
          data-node-type="lesson"
          data-parent-id="${parentId}"
          data-index="${index}"
          draggable="true">
        <div class="tree-item-content">
          ${hasChildren ? `<span class="tree-toggle" data-toggle="${lesson.id}">${isExpanded ? '&#9660;' : '&#9654;'}</span>` : '<span class="tree-toggle-spacer"></span>'}
          <span class="tree-icon">&#128196;</span>
          <span class="tree-label">${this.escapeHtml(lesson.title)}</span>
          <span class="tree-meta">${lesson.activities?.length || 0} activities</span>
        </div>`;

    if (hasChildren) {
      html += '<ul class="tree-children">';
      lesson.activities.forEach((activity, activityIndex) => {
        html += this.renderActivity(activity, activityIndex, lesson.id);
      });
      html += '</ul>';
    }

    html += '</li>';
    return html;
  }

  /**
   * Render an activity node (leaf)
   */
  renderActivity(activity, index, parentId) {
    const stateClass = this.getBuildStateClass(activity.build_state);
    const contentIcon = this.getContentTypeIcon(activity.content_type);

    return `
      <li class="tree-item tree-activity"
          data-node-id="${activity.id}"
          data-node-type="activity"
          data-parent-id="${parentId}"
          data-index="${index}"
          draggable="true">
        <div class="tree-item-content">
          <span class="tree-toggle-spacer"></span>
          <span class="tree-icon">${contentIcon}</span>
          <span class="tree-label">${this.escapeHtml(activity.title)}</span>
          <span class="tree-state ${stateClass}">${this.formatBuildState(activity.build_state)}</span>
        </div>
      </li>`;
  }

  /**
   * Get icon for content type
   */
  getContentTypeIcon(contentType) {
    const icons = {
      video: '&#127909;',       // Movie camera
      reading: '&#128196;',     // Document
      quiz: '&#10067;',         // Question mark
      discussion: '&#128172;',  // Speech balloon
      lab: '&#128300;',         // Microscope
      assignment: '&#128221;',  // Memo
      project: '&#127919;',     // Target/Project
      coach: '&#128100;',       // Person
      hol: '&#9997;'            // Hand writing
    };
    return icons[contentType] || '&#128196;';
  }

  /**
   * Get CSS class for build state
   */
  getBuildStateClass(state) {
    const classes = {
      draft: 'state-draft',
      generating: 'state-generating',
      generated: 'state-generated',
      reviewed: 'state-reviewed',
      approved: 'state-approved',
      published: 'state-published'
    };
    return classes[state] || 'state-draft';
  }

  /**
   * Format build state for display
   */
  formatBuildState(state) {
    if (!state) return 'Draft';
    return state.charAt(0).toUpperCase() + state.slice(1);
  }

  /**
   * Initialize click handlers for selection and toggle
   */
  initEventHandlers() {
    // Toggle expand/collapse
    this.container.querySelectorAll('.tree-toggle').forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const nodeId = toggle.dataset.toggle;
        this.toggleNode(nodeId);
      });
    });

    // Select node on click
    this.container.querySelectorAll('.tree-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const nodeId = item.dataset.nodeId;
        const nodeType = item.dataset.nodeType;
        this.selectNode(nodeId, nodeType);
      });
    });
  }

  /**
   * Toggle expand/collapse for a node
   */
  toggleNode(nodeId) {
    const item = this.container.querySelector(`[data-node-id="${nodeId}"]`);
    if (!item) return;

    const isExpanded = item.classList.contains('expanded');
    const toggle = item.querySelector('.tree-toggle');

    if (isExpanded) {
      item.classList.remove('expanded');
      if (toggle) toggle.innerHTML = '&#9654;';
    } else {
      item.classList.add('expanded');
      if (toggle) toggle.innerHTML = '&#9660;';
    }

    this.saveExpandState();
  }

  /**
   * Select a node
   */
  selectNode(nodeId, nodeType) {
    // Clear previous selection
    this.clearSelection();

    // Set new selection
    const item = this.container.querySelector(`[data-node-id="${nodeId}"]`);
    if (item) {
      item.classList.add('selected');
      this.selectedNodeId = nodeId;
      this.selectedNodeType = nodeType;

      // Call callback
      this.onSelect(nodeId, nodeType);
    }
  }

  /**
   * Clear selection
   */
  clearSelection() {
    this.container.querySelectorAll('.tree-item.selected').forEach(item => {
      item.classList.remove('selected');
    });
    this.selectedNodeId = null;
    this.selectedNodeType = null;
  }

  /**
   * Save expand state to localStorage
   */
  saveExpandState() {
    try {
      const expandedNodes = [];
      this.container.querySelectorAll('.tree-item.expanded').forEach(item => {
        expandedNodes.push(item.dataset.nodeId);
      });
      localStorage.setItem(this.storageKey, JSON.stringify(expandedNodes));
    } catch (e) {
      // QuotaExceededError or other storage error
      console.warn('Could not save tree expand state:', e);
    }
  }

  /**
   * Load expand state from localStorage
   */
  loadExpandState() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        return new Set(JSON.parse(stored));
      }
    } catch (e) {
      console.warn('Could not load tree expand state:', e);
    }
    return new Set();
  }

  /**
   * Initialize drag and drop handlers
   */
  initDragHandlers() {
    const items = this.container.querySelectorAll('.tree-item');

    items.forEach(item => {
      item.addEventListener('dragstart', (e) => this.onDragStart(e, item));
      item.addEventListener('dragover', (e) => this.onDragOver(e, item));
      item.addEventListener('dragenter', (e) => this.onDragEnter(e, item));
      item.addEventListener('dragleave', (e) => this.onDragLeave(e, item));
      item.addEventListener('drop', (e) => this.onDrop(e, item));
      item.addEventListener('dragend', (e) => this.onDragEnd(e));
    });
  }

  /**
   * Handle drag start
   */
  onDragStart(e, item) {
    e.stopPropagation();

    this.draggedItem = item;
    item.classList.add('dragging');

    // Set drag data
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', item.dataset.nodeId);

    // Create custom drag image
    const dragImage = this.createDragImage(item);
    document.body.appendChild(dragImage);
    e.dataTransfer.setDragImage(dragImage, 10, 10);
    setTimeout(() => dragImage.remove(), 0);
  }

  /**
   * Handle drag over
   */
  onDragOver(e, item) {
    e.preventDefault();
    e.stopPropagation();

    if (!this.draggedItem) return;
    if (item === this.draggedItem) return;

    // Check if valid drop target (same type and same parent for lessons/activities)
    if (!this.isValidDrop(this.draggedItem, item)) {
      e.dataTransfer.dropEffect = 'none';
      return;
    }

    e.dataTransfer.dropEffect = 'move';

    // Calculate drop position (before or after)
    const rect = item.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    const position = e.clientY < midY ? 'before' : 'after';

    // Show drop indicator
    this.showDropIndicator(item, position);
    this.dragOverItem = item;
  }

  /**
   * Handle drag enter
   */
  onDragEnter(e, item) {
    e.preventDefault();
    e.stopPropagation();

    if (!this.draggedItem || item === this.draggedItem) return;

    if (this.isValidDrop(this.draggedItem, item)) {
      item.classList.add('drag-over');
    }
  }

  /**
   * Handle drag leave
   */
  onDragLeave(e, item) {
    e.preventDefault();
    e.stopPropagation();

    item.classList.remove('drag-over');
  }

  /**
   * Handle drop
   */
  onDrop(e, item) {
    e.preventDefault();
    e.stopPropagation();

    if (!this.draggedItem) return;
    if (item === this.draggedItem) return;
    if (!this.isValidDrop(this.draggedItem, item)) return;

    // Calculate drop position
    const rect = item.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    const position = e.clientY < midY ? 'before' : 'after';

    // Get indices
    const draggedId = this.draggedItem.dataset.nodeId;
    const draggedType = this.draggedItem.dataset.nodeType;
    const draggedIndex = parseInt(this.draggedItem.dataset.index, 10);
    const targetIndex = parseInt(item.dataset.index, 10);
    const parentId = this.draggedItem.dataset.parentId || null;

    // Calculate new index
    let newIndex = targetIndex;
    if (position === 'after') {
      newIndex = targetIndex + 1;
    }
    if (draggedIndex < targetIndex && position === 'before') {
      newIndex = targetIndex - 1;
    }

    // Don't trigger if position hasn't changed
    if (newIndex !== draggedIndex) {
      this.onReorder(draggedId, draggedType, draggedIndex, newIndex, parentId);
    }

    // Clean up
    this.hideDropIndicator();
    item.classList.remove('drag-over');
  }

  /**
   * Handle drag end
   */
  onDragEnd(e) {
    e.preventDefault();

    if (this.draggedItem) {
      this.draggedItem.classList.remove('dragging');
    }

    // Clean up all drag states
    this.container.querySelectorAll('.drag-over').forEach(el => {
      el.classList.remove('drag-over');
    });

    this.hideDropIndicator();
    this.draggedItem = null;
    this.dragOverItem = null;
  }

  /**
   * Check if drop is valid (same type and same parent)
   */
  isValidDrop(dragged, target) {
    // Must be same type
    if (dragged.dataset.nodeType !== target.dataset.nodeType) {
      return false;
    }

    // For lessons and activities, must have same parent
    const draggedType = dragged.dataset.nodeType;
    if (draggedType === 'lesson' || draggedType === 'activity') {
      if (dragged.dataset.parentId !== target.dataset.parentId) {
        return false;
      }
    }

    // Can't drop onto self
    if (dragged.dataset.nodeId === target.dataset.nodeId) {
      return false;
    }

    // Prevent dropping parent into child (not possible with same-type constraint but check anyway)
    if (target.contains(dragged)) {
      return false;
    }

    return true;
  }

  /**
   * Show drop indicator
   */
  showDropIndicator(targetItem, position) {
    const rect = targetItem.getBoundingClientRect();
    const indicatorY = position === 'before' ? rect.top : rect.bottom;

    this.dropIndicator.style.display = 'block';
    this.dropIndicator.style.left = `${rect.left}px`;
    this.dropIndicator.style.top = `${indicatorY - 2}px`;
    this.dropIndicator.style.width = `${rect.width}px`;
  }

  /**
   * Hide drop indicator
   */
  hideDropIndicator() {
    if (this.dropIndicator) {
      this.dropIndicator.style.display = 'none';
    }
  }

  /**
   * Create custom drag image
   */
  createDragImage(element) {
    const label = element.querySelector('.tree-label');
    const clone = document.createElement('div');
    clone.className = 'tree-drag-image';
    clone.textContent = label ? label.textContent : 'Item';
    clone.style.cssText = `
      position: absolute;
      top: -1000px;
      left: -1000px;
      padding: 4px 8px;
      background: var(--bg-panel, #16213e);
      border: 1px solid var(--accent-primary, #4361ee);
      border-radius: 4px;
      color: var(--text-primary, #fff);
      font-size: 14px;
      white-space: nowrap;
    `;
    return clone;
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  /**
   * Get currently selected node info
   */
  getSelectedNode() {
    if (!this.selectedNodeId) return null;
    return {
      id: this.selectedNodeId,
      type: this.selectedNodeType
    };
  }

  /**
   * Expand all nodes
   */
  expandAll() {
    this.container.querySelectorAll('.tree-item').forEach(item => {
      item.classList.add('expanded');
      const toggle = item.querySelector('.tree-toggle');
      if (toggle) toggle.innerHTML = '&#9660;';
    });
    this.saveExpandState();
  }

  /**
   * Collapse all nodes
   */
  collapseAll() {
    this.container.querySelectorAll('.tree-item').forEach(item => {
      item.classList.remove('expanded');
      const toggle = item.querySelector('.tree-toggle');
      if (toggle) toggle.innerHTML = '&#9654;';
    });
    this.saveExpandState();
  }

  /**
   * Clean up event listeners and elements
   */
  destroy() {
    if (this.dropIndicator && this.dropIndicator.parentNode) {
      this.dropIndicator.parentNode.removeChild(this.dropIndicator);
    }
  }
}

// Export for use
window.HierarchicalTree = HierarchicalTree;
