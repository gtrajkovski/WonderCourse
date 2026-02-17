/**
 * Audit Page Controller
 * Manages course audit functionality including running audits,
 * displaying results, and updating issue status.
 */

class AuditController {
    constructor(courseId) {
        this.courseId = courseId;
        this.latestResult = null;
        this.selectedIssue = null;

        // DOM elements
        this.scoreCard = document.getElementById('score-card');
        this.noAudit = document.getElementById('no-audit');
        this.issuesSection = document.getElementById('issues-section');
        this.issuesList = document.getElementById('issues-list');
        this.checksGrid = document.getElementById('checks-grid');

        // Buttons
        this.btnRunAudit = document.getElementById('btn-run-audit');
        this.btnRunAuditEmpty = document.getElementById('btn-run-audit-empty');

        // Modals
        this.issueModal = document.getElementById('issue-modal');
        this.auditRunningModal = document.getElementById('audit-running-modal');

        // Filters
        this.filterErrors = document.getElementById('filter-errors');
        this.filterWarnings = document.getElementById('filter-warnings');
        this.filterInfo = document.getElementById('filter-info');
        this.filterResolved = document.getElementById('filter-resolved');
    }

    async init() {
        this.bindEvents();
        await this.loadLatestAudit();
    }

    bindEvents() {
        // Run audit buttons
        this.btnRunAudit?.addEventListener('click', () => this.runFullAudit());
        this.btnRunAuditEmpty?.addEventListener('click', () => this.runFullAudit());

        // Individual check buttons
        this.checksGrid?.querySelectorAll('.btn-run-check').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const checkType = btn.dataset.check;
                this.runCheck(checkType);
            });
        });

        // Filter checkboxes
        [this.filterErrors, this.filterWarnings, this.filterInfo, this.filterResolved].forEach(filter => {
            filter?.addEventListener('change', () => this.renderIssues());
        });

        // Issue modal save button
        document.getElementById('btn-save-issue')?.addEventListener('click', () => this.saveIssue());

        // Modal close handlers
        document.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.modal')?.setAttribute('aria-hidden', 'true');
            });
        });

        // Close modal on backdrop click
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', () => {
                backdrop.closest('.modal')?.setAttribute('aria-hidden', 'true');
            });
        });
    }

    async loadLatestAudit() {
        try {
            const response = await fetch(`/api/courses/${this.courseId}/audit`);
            const data = await response.json();

            if (data.result) {
                this.latestResult = data.result;
                this.showResults();
            } else {
                this.showNoAudit();
            }
        } catch (error) {
            console.error('Failed to load audit:', error);
            this.showNoAudit();
        }
    }

    async runFullAudit() {
        await this.runAudit();
    }

    async runCheck(checkType) {
        await this.runAudit([checkType]);
    }

    async runAudit(checks = null) {
        this.showRunningModal('Running audit...');

        try {
            const body = checks ? { checks } : {};
            const response = await fetch(`/api/courses/${this.courseId}/audit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                throw new Error('Audit failed');
            }

            const data = await response.json();
            this.latestResult = data.result;
            this.hideRunningModal();
            this.showResults();

        } catch (error) {
            console.error('Audit error:', error);
            this.hideRunningModal();
            alert('Failed to run audit. Please try again.');
        }
    }

    showRunningModal(message) {
        document.getElementById('audit-running-message').textContent = message;
        this.auditRunningModal?.setAttribute('aria-hidden', 'false');
    }

    hideRunningModal() {
        this.auditRunningModal?.setAttribute('aria-hidden', 'true');
    }

    showNoAudit() {
        this.scoreCard.style.display = 'none';
        this.issuesSection.style.display = 'none';
        this.noAudit.style.display = 'block';
    }

    showResults() {
        this.noAudit.style.display = 'none';
        this.scoreCard.style.display = 'flex';
        this.issuesSection.style.display = 'block';

        this.updateScoreCard();
        this.renderIssues();
    }

    updateScoreCard() {
        const result = this.latestResult;
        if (!result) return;

        // Update score with CSS variable for conic gradient
        const scoreValue = document.getElementById('score-value');
        scoreValue.textContent = result.score;
        this.scoreCard.style.setProperty('--score', result.score);

        // Update counts
        document.getElementById('error-count').textContent = result.error_count;
        document.getElementById('warning-count').textContent = result.warning_count;
        document.getElementById('info-count').textContent = result.info_count;

        // Update timestamp
        const timestamp = document.getElementById('audit-timestamp');
        if (result.created_at) {
            const date = new Date(result.created_at);
            timestamp.textContent = `Last run: ${date.toLocaleString()}`;
        }
    }

    renderIssues() {
        if (!this.latestResult?.issues) {
            this.issuesList.innerHTML = '<div class="issues-empty"><div class="issues-empty-icon">&#10003;</div><p>No issues found</p></div>';
            return;
        }

        const showErrors = this.filterErrors?.checked ?? true;
        const showWarnings = this.filterWarnings?.checked ?? true;
        const showInfo = this.filterInfo?.checked ?? true;
        const showResolved = this.filterResolved?.checked ?? false;

        const resolvedStatuses = ['resolved', 'wont_fix', 'false_positive'];

        const filteredIssues = this.latestResult.issues.filter(issue => {
            const isResolved = resolvedStatuses.includes(issue.status);
            if (isResolved && !showResolved) return false;
            if (!isResolved && !showResolved) {
                // Show open issues based on severity filter
            }

            switch (issue.severity) {
                case 'error': return showErrors;
                case 'warning': return showWarnings;
                case 'info': return showInfo;
                default: return true;
            }
        });

        if (filteredIssues.length === 0) {
            this.issuesList.innerHTML = '<div class="issues-empty"><div class="issues-empty-icon">&#128270;</div><p>No issues match current filters</p></div>';
            return;
        }

        this.issuesList.innerHTML = filteredIssues.map(issue => this.renderIssueItem(issue)).join('');

        // Bind click handlers
        this.issuesList.querySelectorAll('.issue-item').forEach(item => {
            item.addEventListener('click', () => {
                const issueId = item.dataset.issueId;
                const issue = this.latestResult.issues.find(i => i.id === issueId);
                if (issue) this.showIssueModal(issue);
            });
        });
    }

    renderIssueItem(issue) {
        const resolvedStatuses = ['resolved', 'wont_fix', 'false_positive'];
        const isResolved = resolvedStatuses.includes(issue.status);
        const checkTypeLabel = this.formatCheckType(issue.check_type);

        return `
            <div class="issue-item ${isResolved ? 'resolved' : ''}" data-issue-id="${issue.id}">
                <span class="issue-severity ${issue.severity}"></span>
                <div class="issue-content">
                    <div class="issue-title">${this.escapeHtml(issue.title)}</div>
                    <p class="issue-description">${this.escapeHtml(issue.description)}</p>
                    <div class="issue-meta">
                        <span class="issue-check-type">${checkTypeLabel}</span>
                        <span class="issue-status-badge ${issue.status}">${this.formatStatus(issue.status)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    showIssueModal(issue) {
        this.selectedIssue = issue;

        document.getElementById('issue-modal-title').textContent = issue.title;

        const severityBadge = document.getElementById('issue-modal-severity');
        severityBadge.textContent = issue.severity;
        severityBadge.className = `issue-severity-badge ${issue.severity}`;

        document.getElementById('issue-modal-description').textContent = issue.description;

        // Affected elements
        const affectedList = document.getElementById('issue-modal-affected');
        if (issue.affected_elements?.length > 0) {
            affectedList.innerHTML = issue.affected_elements.map(el =>
                `<li>${this.escapeHtml(el)}</li>`
            ).join('');
            affectedList.parentElement.style.display = 'block';
        } else {
            affectedList.parentElement.style.display = 'none';
        }

        // Suggested fix
        const fixEl = document.getElementById('issue-modal-fix');
        if (issue.suggested_fix) {
            fixEl.textContent = issue.suggested_fix;
            fixEl.parentElement.style.display = 'block';
        } else {
            fixEl.parentElement.style.display = 'none';
        }

        // Status and notes
        document.getElementById('issue-modal-status').value = issue.status;
        document.getElementById('issue-modal-notes').value = issue.resolution_notes || '';

        this.issueModal?.setAttribute('aria-hidden', 'false');
    }

    async saveIssue() {
        if (!this.selectedIssue) return;

        const status = document.getElementById('issue-modal-status').value;
        const notes = document.getElementById('issue-modal-notes').value;

        try {
            const response = await fetch(
                `/api/courses/${this.courseId}/audit/issues/${this.selectedIssue.id}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status, resolution_notes: notes })
                }
            );

            if (!response.ok) {
                throw new Error('Failed to update issue');
            }

            const data = await response.json();

            // Update local state
            const index = this.latestResult.issues.findIndex(i => i.id === this.selectedIssue.id);
            if (index !== -1) {
                this.latestResult.issues[index] = data.issue;
            }

            this.issueModal?.setAttribute('aria-hidden', 'true');
            this.renderIssues();

        } catch (error) {
            console.error('Failed to save issue:', error);
            alert('Failed to update issue. Please try again.');
        }
    }

    formatCheckType(checkType) {
        const labels = {
            'flow_analysis': 'Flow Analysis',
            'repetition': 'Repetition',
            'objective_alignment': 'Objective Alignment',
            'content_gaps': 'Content Gaps',
            'duration_balance': 'Duration Balance',
            'bloom_progression': 'Bloom Progression'
        };
        return labels[checkType] || checkType;
    }

    formatStatus(status) {
        const labels = {
            'open': 'Open',
            'in_progress': 'In Progress',
            'resolved': 'Resolved',
            'wont_fix': "Won't Fix",
            'false_positive': 'False Positive'
        };
        return labels[status] || status;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
