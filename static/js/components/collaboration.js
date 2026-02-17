/**
 * Collaboration Controller - Invite modal, comments panel, activity feed
 */
class CollaborationController {
  constructor(courseId) {
    this.courseId = courseId;
    this.inviteModal = null;
    this.roles = [];
    this.collaborators = [];
    this.pendingInvitations = [];

    // Comments state
    this.commentsPanel = null;
    this.comments = [];
    this.currentFilter = 'all';
    this.activityId = null;

    // Activity feed state
    this.activityFeed = null;
    this.activities = [];
    this.activityPage = 0;
    this.activityHasMore = true;

    // Mention autocomplete state
    this.mentionAutocomplete = null;
    this.mentionQuery = '';
    this.mentionStartPos = -1;

    this.initialize();
  }

  initialize() {
    // Initialize invite modal
    const modalEl = document.getElementById('collab-modal');
    if (modalEl) {
      this.inviteModal = window.modal_collab_modal || new Modal('collab-modal');
      this.setupInviteModalListeners();
    }

    // Initialize comments panel
    this.commentsPanel = document.getElementById('comments-panel');
    if (this.commentsPanel) {
      this.setupCommentsPanelListeners();
    }

    // Initialize activity feed
    this.activityFeed = document.getElementById('activity-feed');
    if (this.activityFeed) {
      this.setupActivityFeedListeners();
    }

    // Load roles for dropdowns
    this.loadRoles();
  }

  // ===== Invite Modal =====

  async loadRoles() {
    try {
      this.roles = await window.api.get(`/courses/${this.courseId}/roles`);
      this.populateRoleDropdowns();
    } catch (error) {
      console.error('Failed to load roles:', error);
    }
  }

  populateRoleDropdowns() {
    const dropdowns = ['invite-role', 'link-role'];
    dropdowns.forEach(id => {
      const select = document.getElementById(id);
      if (select) {
        select.innerHTML = '';
        this.roles.forEach(role => {
          // Exclude Owner role from invitations
          if (role.name !== 'Owner') {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.name;
            select.appendChild(option);
          }
        });
      }
    });
  }

  setupInviteModalListeners() {
    // Listen for modal open
    const modalEl = document.getElementById('collab-modal');
    modalEl.addEventListener('modal:open', () => this.onInviteModalOpen());

    // Invite form submit
    const inviteForm = document.getElementById('invite-form');
    if (inviteForm) {
      inviteForm.addEventListener('submit', (e) => this.handleSendInvite(e));
    }

    // Create shareable link
    const createLinkBtn = document.getElementById('create-link-btn');
    if (createLinkBtn) {
      createLinkBtn.addEventListener('click', () => this.handleCreateShareableLink());
    }

    // Copy link
    const copyLinkBtn = document.getElementById('copy-link-btn');
    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', () => this.handleCopyLink());
    }
  }

  async onInviteModalOpen() {
    await Promise.all([
      this.loadCollaborators(),
      this.loadPendingInvitations()
    ]);
    // Reset shareable link display
    const linkDisplay = document.getElementById('shareable-link-display');
    if (linkDisplay) linkDisplay.classList.add('hidden');
  }

  async loadCollaborators() {
    try {
      this.collaborators = await window.api.get(`/courses/${this.courseId}/collaborators`);
      this.renderCollaborators();
    } catch (error) {
      console.error('Failed to load collaborators:', error);
    }
  }

  renderCollaborators() {
    const list = document.getElementById('collaborator-list');
    if (!list) return;

    if (this.collaborators.length === 0) {
      list.innerHTML = '<div class="empty-state">No collaborators yet</div>';
      return;
    }

    list.innerHTML = this.collaborators.map(collab => `
      <div class="collaborator-item" data-id="${collab.id}">
        <div class="collaborator-avatar">${this.getInitials(collab.user_name || collab.user_email)}</div>
        <div class="collaborator-info">
          <div class="collaborator-name">${this.escapeHtml(collab.user_name || 'Unknown')}</div>
          <div class="collaborator-email">${this.escapeHtml(collab.user_email)}</div>
        </div>
        <span class="collaborator-role ${collab.role_name === 'Owner' ? 'role-owner' : ''}">${this.escapeHtml(collab.role_name)}</span>
        ${collab.role_name !== 'Owner' ? `
          <div class="collaborator-actions">
            <button class="btn btn-ghost btn-small" onclick="window.collab.handleRemoveCollab(${collab.id})" title="Remove">
              &#x2715;
            </button>
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  async loadPendingInvitations() {
    try {
      this.pendingInvitations = await window.api.get(`/courses/${this.courseId}/invitations`);
      this.renderPendingInvitations();
    } catch (error) {
      console.error('Failed to load invitations:', error);
    }
  }

  renderPendingInvitations() {
    const list = document.getElementById('pending-list');
    if (!list) return;

    if (this.pendingInvitations.length === 0) {
      list.innerHTML = '<div class="empty-state">No pending invitations</div>';
      return;
    }

    list.innerHTML = this.pendingInvitations.map(inv => {
      const expiresText = inv.expires_at ? this.formatDate(inv.expires_at) : 'Never';
      return `
        <div class="pending-item" data-id="${inv.id}">
          <span class="pending-email ${inv.email ? '' : 'pending-link'}">
            ${inv.email ? this.escapeHtml(inv.email) : 'Shareable Link'}
          </span>
          <span class="collaborator-role">${this.escapeHtml(inv.role_name || 'Unknown')}</span>
          <span class="pending-expires">Expires: ${expiresText}</span>
          <div class="collaborator-actions">
            <button class="btn btn-ghost btn-small" onclick="window.collab.handleRevokeInvite(${inv.id})" title="Revoke">
              &#x2715;
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  async handleSendInvite(e) {
    e.preventDefault();

    const form = e.target;
    const email = form.email.value.trim();
    const roleId = parseInt(form.role_id.value, 10);
    const expiresIn = form.expires_in.value ? parseInt(form.expires_in.value, 10) : null;

    try {
      await window.api.post(`/courses/${this.courseId}/invitations`, {
        email,
        role_id: roleId,
        expires_in: expiresIn
      });

      window.toast.success(`Invitation sent to ${email}`);
      form.reset();
      await this.loadPendingInvitations();
    } catch (error) {
      window.toast.error(error.message || 'Failed to send invitation');
    }
  }

  async handleCreateShareableLink() {
    const roleSelect = document.getElementById('link-role');
    const expirySelect = document.getElementById('link-expiry');
    const roleId = parseInt(roleSelect.value, 10);
    const expiresIn = expirySelect.value ? parseInt(expirySelect.value, 10) : null;

    try {
      const invitation = await window.api.post(`/courses/${this.courseId}/invitations`, {
        email: null,
        role_id: roleId,
        expires_in: expiresIn
      });

      // Build shareable URL
      const baseUrl = window.location.origin;
      const shareUrl = `${baseUrl}/invite/${invitation.token}`;

      const linkInput = document.getElementById('shareable-link-input');
      const linkDisplay = document.getElementById('shareable-link-display');

      if (linkInput && linkDisplay) {
        linkInput.value = shareUrl;
        linkDisplay.classList.remove('hidden');
      }

      window.toast.success('Shareable link created');
      await this.loadPendingInvitations();
    } catch (error) {
      window.toast.error(error.message || 'Failed to create link');
    }
  }

  handleCopyLink() {
    const linkInput = document.getElementById('shareable-link-input');
    if (linkInput) {
      navigator.clipboard.writeText(linkInput.value).then(() => {
        window.toast.success('Link copied to clipboard');
      }).catch(() => {
        // Fallback for older browsers
        linkInput.select();
        document.execCommand('copy');
        window.toast.success('Link copied to clipboard');
      });
    }
  }

  async handleRevokeInvite(inviteId) {
    if (!confirm('Revoke this invitation?')) return;

    try {
      await window.api.delete(`/courses/${this.courseId}/invitations/${inviteId}`);
      window.toast.success('Invitation revoked');
      await this.loadPendingInvitations();
    } catch (error) {
      window.toast.error(error.message || 'Failed to revoke invitation');
    }
  }

  async handleRemoveCollab(collabId) {
    if (!confirm('Remove this collaborator from the course?')) return;

    try {
      await window.api.delete(`/courses/${this.courseId}/collaborators/${collabId}`);
      window.toast.success('Collaborator removed');
      await this.loadCollaborators();
    } catch (error) {
      window.toast.error(error.message || 'Failed to remove collaborator');
    }
  }

  showInviteModal() {
    if (this.inviteModal) {
      this.inviteModal.open();
    }
  }


  // ===== Comments Panel =====

  setupCommentsPanelListeners() {
    // Toggle button
    const toggleBtn = this.commentsPanel.querySelector('.comments-panel-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggleCommentsPanel());
    }

    // Close button
    const closeBtn = this.commentsPanel.querySelector('.comments-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.toggleCommentsPanel());
    }

    // Filter buttons
    const filterBtns = this.commentsPanel.querySelectorAll('.comments-filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.dataset.filter;
        this.renderComments();
      });
    });

    // Add comment form
    const addForm = this.commentsPanel.querySelector('.add-comment-form');
    if (addForm) {
      addForm.addEventListener('submit', (e) => this.handleAddComment(e));
    }

    // Mention autocomplete on textarea
    const textarea = this.commentsPanel.querySelector('.add-comment-input');
    if (textarea) {
      textarea.addEventListener('input', (e) => this.handleMentionInput(e));
      textarea.addEventListener('keydown', (e) => this.handleMentionKeydown(e));
    }
  }

  toggleCommentsPanel() {
    if (this.commentsPanel) {
      this.commentsPanel.classList.toggle('collapsed');
      const isCollapsed = this.commentsPanel.classList.contains('collapsed');
      window.storage.set('comments-panel-collapsed', isCollapsed);
    }
  }

  async loadComments(activityId = null) {
    this.activityId = activityId;

    try {
      const endpoint = activityId
        ? `/courses/${this.courseId}/activities/${activityId}/comments?include_resolved=true`
        : `/courses/${this.courseId}/comments?include_resolved=true`;

      this.comments = await window.api.get(endpoint);
      this.renderComments();
      this.updateCommentCount();
    } catch (error) {
      console.error('Failed to load comments:', error);
    }
  }

  renderComments() {
    const list = this.commentsPanel?.querySelector('.comment-list');
    if (!list) return;

    // Filter comments
    let filtered = this.comments;
    if (this.currentFilter === 'unresolved') {
      filtered = this.comments.filter(c => !c.resolved);
    } else if (this.currentFilter === 'mentions') {
      // Filter by mentions of current user would need user ID
      filtered = this.comments.filter(c => c.content && c.content.includes('@'));
    }

    if (filtered.length === 0) {
      list.innerHTML = '<div class="empty-state">No comments yet</div>';
      return;
    }

    list.innerHTML = filtered.map(comment => this.renderComment(comment)).join('');
  }

  renderComment(comment) {
    const repliesHtml = comment.replies && comment.replies.length > 0
      ? `<div class="comment-replies">${comment.replies.map(r => this.renderComment(r)).join('')}</div>`
      : '';

    const isTopLevel = !comment.parent_id;

    return `
      <div class="comment-item ${comment.resolved ? 'resolved' : ''}" data-id="${comment.id}">
        <div class="comment-header">
          <div class="comment-avatar">${this.getInitials(comment.author_name || 'U')}</div>
          <span class="comment-author">${this.escapeHtml(comment.author_name || 'Unknown')}</span>
          <span class="comment-time">${this.formatRelativeTime(comment.created_at)}</span>
        </div>
        <div class="comment-text">${this.formatCommentText(comment.content)}</div>
        <div class="comment-actions">
          ${isTopLevel ? `<button class="comment-action-btn" onclick="window.collab.showReplyForm(${comment.id})">Reply</button>` : ''}
          ${!comment.resolved ? `<button class="comment-action-btn" onclick="window.collab.handleResolve(${comment.id})">Resolve</button>` : ''}
          ${comment.resolved ? `<button class="comment-action-btn" onclick="window.collab.handleUnresolve(${comment.id})">Unresolve</button>` : ''}
        </div>
        <div class="reply-form hidden" id="reply-form-${comment.id}">
          <input type="text" class="form-input" placeholder="Write a reply..." onkeydown="if(event.key==='Enter'){window.collab.handleReply(${comment.id}, this.value);this.value=''}">
          <button class="btn btn-small btn-primary" onclick="window.collab.handleReply(${comment.id}, this.previousElementSibling.value);this.previousElementSibling.value=''">Send</button>
        </div>
        ${repliesHtml}
      </div>
    `;
  }

  formatCommentText(text) {
    if (!text) return '';
    // Highlight @mentions
    return this.escapeHtml(text).replace(/@(\w+)/g, '<span class="mention">@$1</span>');
  }

  updateCommentCount() {
    const countEl = this.commentsPanel?.querySelector('.comments-count');
    if (countEl) {
      const unresolvedCount = this.comments.filter(c => !c.resolved).length;
      countEl.textContent = unresolvedCount;
      countEl.style.display = unresolvedCount > 0 ? 'inline-flex' : 'none';
    }
  }

  showReplyForm(commentId) {
    const form = document.getElementById(`reply-form-${commentId}`);
    if (form) {
      form.classList.toggle('hidden');
      if (!form.classList.contains('hidden')) {
        form.querySelector('input')?.focus();
      }
    }
  }

  async handleAddComment(e) {
    e.preventDefault();

    const textarea = e.target.querySelector('.add-comment-input');
    const content = textarea.value.trim();
    if (!content) return;

    try {
      const endpoint = this.activityId
        ? `/courses/${this.courseId}/activities/${this.activityId}/comments`
        : `/courses/${this.courseId}/comments`;

      await window.api.post(endpoint, { content });

      textarea.value = '';
      await this.loadComments(this.activityId);
      window.toast.success('Comment added');
    } catch (error) {
      window.toast.error(error.message || 'Failed to add comment');
    }
  }

  async handleReply(commentId, content) {
    if (!content || !content.trim()) return;

    try {
      const endpoint = this.activityId
        ? `/courses/${this.courseId}/activities/${this.activityId}/comments`
        : `/courses/${this.courseId}/comments`;

      await window.api.post(endpoint, {
        content: content.trim(),
        parent_id: commentId
      });

      await this.loadComments(this.activityId);
      window.toast.success('Reply added');
    } catch (error) {
      window.toast.error(error.message || 'Failed to add reply');
    }
  }

  async handleResolve(commentId) {
    try {
      await window.api.post(`/courses/${this.courseId}/comments/${commentId}/resolve`);
      await this.loadComments(this.activityId);
      window.toast.success('Comment resolved');
    } catch (error) {
      window.toast.error(error.message || 'Failed to resolve comment');
    }
  }

  async handleUnresolve(commentId) {
    try {
      await window.api.post(`/courses/${this.courseId}/comments/${commentId}/unresolve`);
      await this.loadComments(this.activityId);
    } catch (error) {
      window.toast.error(error.message || 'Failed to unresolve comment');
    }
  }

  handleMentionInput(e) {
    const textarea = e.target;
    const text = textarea.value;
    const cursorPos = textarea.selectionStart;

    // Find @ before cursor
    const beforeCursor = text.substring(0, cursorPos);
    const atMatch = beforeCursor.match(/@(\w*)$/);

    if (atMatch) {
      this.mentionQuery = atMatch[1];
      this.mentionStartPos = atMatch.index;
      this.showMentionAutocomplete(textarea);
    } else {
      this.hideMentionAutocomplete();
    }
  }

  handleMentionKeydown(e) {
    if (!this.mentionAutocomplete || this.mentionAutocomplete.classList.contains('hidden')) {
      return;
    }

    const options = this.mentionAutocomplete.querySelectorAll('.mention-option');
    const selected = this.mentionAutocomplete.querySelector('.mention-option.selected');
    let selectedIndex = Array.from(options).indexOf(selected);

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, options.length - 1);
      options.forEach((opt, i) => opt.classList.toggle('selected', i === selectedIndex));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
      options.forEach((opt, i) => opt.classList.toggle('selected', i === selectedIndex));
    } else if (e.key === 'Enter' && selected) {
      e.preventDefault();
      this.selectMention(selected.dataset.name, e.target);
    } else if (e.key === 'Escape') {
      this.hideMentionAutocomplete();
    }
  }

  async showMentionAutocomplete(textarea) {
    // Filter collaborators by query
    const filtered = this.collaborators.filter(c =>
      (c.user_name && c.user_name.toLowerCase().includes(this.mentionQuery.toLowerCase())) ||
      (c.user_email && c.user_email.toLowerCase().includes(this.mentionQuery.toLowerCase()))
    );

    if (filtered.length === 0) {
      this.hideMentionAutocomplete();
      return;
    }

    // Create or update autocomplete
    if (!this.mentionAutocomplete) {
      this.mentionAutocomplete = document.createElement('div');
      this.mentionAutocomplete.className = 'mention-autocomplete';
      document.body.appendChild(this.mentionAutocomplete);
    }

    this.mentionAutocomplete.innerHTML = filtered.slice(0, 5).map((c, i) => `
      <div class="mention-option ${i === 0 ? 'selected' : ''}" data-name="${this.escapeHtml(c.user_name || c.user_email)}">
        <div class="mention-option-avatar">${this.getInitials(c.user_name || c.user_email)}</div>
        <span class="mention-option-name">${this.escapeHtml(c.user_name || c.user_email)}</span>
      </div>
    `).join('');

    // Position near textarea
    const rect = textarea.getBoundingClientRect();
    this.mentionAutocomplete.style.left = `${rect.left}px`;
    this.mentionAutocomplete.style.top = `${rect.bottom + 4}px`;
    this.mentionAutocomplete.classList.remove('hidden');

    // Click handler
    this.mentionAutocomplete.querySelectorAll('.mention-option').forEach(opt => {
      opt.addEventListener('click', () => this.selectMention(opt.dataset.name, textarea));
    });
  }

  selectMention(name, textarea) {
    const text = textarea.value;
    const before = text.substring(0, this.mentionStartPos);
    const after = text.substring(textarea.selectionStart);

    textarea.value = `${before}@${name} ${after}`;
    textarea.focus();
    const newPos = this.mentionStartPos + name.length + 2;
    textarea.setSelectionRange(newPos, newPos);

    this.hideMentionAutocomplete();
  }

  hideMentionAutocomplete() {
    if (this.mentionAutocomplete) {
      this.mentionAutocomplete.classList.add('hidden');
    }
    this.mentionQuery = '';
    this.mentionStartPos = -1;
  }


  // ===== Activity Feed =====

  setupActivityFeedListeners() {
    // Close button
    const closeBtn = this.activityFeed.querySelector('.activity-feed-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.toggleActivityFeed());
    }

    // Filter buttons
    const filterBtns = this.activityFeed.querySelectorAll('.activity-filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Filter logic could be implemented here
      });
    });

    // Load more button
    const loadMoreBtn = this.activityFeed.querySelector('.load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => this.handleLoadMore());
    }

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (this.activityFeed.classList.contains('open') &&
          !this.activityFeed.contains(e.target) &&
          !e.target.closest('.header-icon-btn[data-activity-feed]')) {
        this.toggleActivityFeed();
      }
    });
  }

  toggleActivityFeed() {
    if (this.activityFeed) {
      const isOpen = this.activityFeed.classList.toggle('open');
      if (isOpen && this.activities.length === 0) {
        this.loadActivityFeed();
      }
    }
  }

  async loadActivityFeed(page = 0) {
    try {
      const limit = 20;
      const offset = page * limit;
      const response = await window.api.get(`/courses/${this.courseId}/activity?limit=${limit}&offset=${offset}`);

      if (page === 0) {
        this.activities = response.feed;
      } else {
        this.activities = [...this.activities, ...response.feed];
      }

      this.activityPage = page;
      this.activityHasMore = response.has_more;
      this.renderActivityFeed();
    } catch (error) {
      console.error('Failed to load activity feed:', error);
    }
  }

  renderActivityFeed() {
    const list = this.activityFeed?.querySelector('.activity-list');
    const loadMoreWrapper = this.activityFeed?.querySelector('.activity-load-more');

    if (!list) return;

    if (this.activities.length === 0) {
      list.innerHTML = '<div class="empty-state">No recent activity</div>';
      if (loadMoreWrapper) loadMoreWrapper.classList.add('hidden');
      return;
    }

    list.innerHTML = this.activities.map(activity => `
      <div class="activity-item" data-entity-type="${activity.entity_type}" data-entity-id="${activity.entity_id}">
        <div class="activity-avatar">${this.getInitials(activity.user_name || 'U')}</div>
        <div class="activity-content">
          <div class="activity-description">
            <span class="activity-user">${this.escapeHtml(activity.user_name || 'Unknown')}</span>
            ${this.formatActivityAction(activity)}
          </div>
          <div class="activity-time">${this.formatRelativeTime(activity.created_at)}</div>
        </div>
      </div>
    `).join('');

    // Show/hide load more
    if (loadMoreWrapper) {
      loadMoreWrapper.classList.toggle('hidden', !this.activityHasMore);
    }
  }

  formatActivityAction(activity) {
    const actionMap = {
      'content_generated': 'generated content for',
      'content_edited': 'edited',
      'content_approved': 'approved',
      'content_published': 'published',
      'comment_added': 'commented on',
      'comment_resolved': 'resolved a comment on',
      'collaborator_joined': 'joined as collaborator',
      'collaborator_removed': 'was removed from',
      'role_changed': 'changed role for',
      'course_created': 'created the course',
      'course_updated': 'updated course settings',
      'module_created': 'created module',
      'module_deleted': 'deleted module',
      'lesson_created': 'created lesson',
      'lesson_deleted': 'deleted lesson',
      'activity_created': 'created activity',
      'activity_deleted': 'deleted activity'
    };

    const actionText = actionMap[activity.action] || activity.action;
    const entityText = activity.entity_type ? `<span class="activity-entity">${activity.entity_type}</span>` : '';

    return `${actionText} ${entityText}`;
  }

  handleLoadMore() {
    this.loadActivityFeed(this.activityPage + 1);
  }


  // ===== Utility Methods =====

  getInitials(name) {
    if (!name) return 'U';
    const parts = name.split(/[\s@]+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  formatDate(isoString) {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  formatRelativeTime(isoString) {
    if (!isoString) return '';

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;

    return this.formatDate(isoString);
  }
}

// Export for global access
window.CollaborationController = CollaborationController;
