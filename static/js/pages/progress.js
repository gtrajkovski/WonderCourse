/**
 * Progress Dashboard Controller
 *
 * Visualizes course completion status and content generation progress.
 */
class ProgressDashboard {
    constructor(courseId) {
        this.courseId = courseId;
        this.progressData = null;
        this.currentFilter = 'all';
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        await this.loadProgress();
        this.renderSummaryCards();
        this.renderStateBars();
        this.renderModuleProgress();
        this.renderContentTypes();
        this.renderStructure();
        this.renderActivityTable();
        this.bindEventHandlers();
    }

    /**
     * Load progress data from API
     */
    async loadProgress() {
        try {
            const response = await fetch(`/api/courses/${this.courseId}/progress`);
            if (!response.ok) {
                throw new Error('Failed to load progress');
            }
            this.progressData = await response.json();
        } catch (error) {
            console.error('Error loading progress:', error);
            this.progressData = {
                total_activities: 0,
                by_state: { draft: 0, generating: 0, generated: 0, reviewed: 0, approved: 0, published: 0 },
                completion_percentage: 0,
                activities: [],
                content_metrics: { total_word_count: 0, total_duration_minutes: 0, target_duration_minutes: 60, duration_percentage: 0 },
                structure: { module_count: 0, lesson_count: 0, activity_count: 0 },
                by_content_type: {},
                by_module: [],
                quality: { audit_score: null, open_issues: 0, last_audit: null }
            };
        }
    }

    /**
     * Render summary cards with key metrics
     */
    renderSummaryCards() {
        const data = this.progressData;

        // Completion percentage with ring
        const completionEl = document.getElementById('completion-percentage');
        const ringEl = document.getElementById('completion-ring');
        const pct = data.completion_percentage || 0;
        completionEl.textContent = `${Math.round(pct)}%`;
        ringEl.setAttribute('stroke-dasharray', `${pct}, 100`);

        // Set ring color based on percentage
        if (pct >= 80) {
            ringEl.classList.add('high');
        } else if (pct >= 50) {
            ringEl.classList.add('medium');
        }

        // Total activities
        document.getElementById('total-activities').textContent = data.total_activities || 0;

        // Duration
        const metrics = data.content_metrics || {};
        const duration = Math.round(metrics.total_duration_minutes || 0);
        const target = metrics.target_duration_minutes || 60;
        document.getElementById('total-duration').textContent = `${duration} min`;
        document.getElementById('duration-target').textContent = `Target: ${target} min`;

        // Quality score
        const quality = data.quality || {};
        const scoreEl = document.getElementById('quality-score');
        if (quality.audit_score !== null && quality.audit_score !== undefined) {
            scoreEl.textContent = quality.audit_score;
            if (quality.audit_score >= 80) {
                scoreEl.classList.add('score-high');
            } else if (quality.audit_score >= 60) {
                scoreEl.classList.add('score-medium');
            } else {
                scoreEl.classList.add('score-low');
            }
        } else {
            scoreEl.textContent = '--';
        }
    }

    /**
     * Render build state bar chart
     */
    renderStateBars() {
        const byState = this.progressData.by_state || {};
        const total = this.progressData.total_activities || 1;

        const states = ['draft', 'generating', 'generated', 'reviewed', 'approved', 'published'];

        states.forEach(state => {
            const count = byState[state] || 0;
            const percentage = (count / total) * 100;

            const barEl = document.querySelector(`.state-bar[data-state="${state}"]`);
            if (barEl) {
                const fillEl = barEl.querySelector('.state-bar-fill');
                const countEl = barEl.querySelector('.state-count');

                fillEl.style.width = `${percentage}%`;
                countEl.textContent = count;
            }
        });
    }

    /**
     * Render module progress list
     */
    renderModuleProgress() {
        const moduleList = document.getElementById('module-list');
        const byModule = this.progressData.by_module || [];

        if (byModule.length === 0) {
            moduleList.innerHTML = '<div class="empty-message">No modules yet</div>';
            return;
        }

        moduleList.innerHTML = byModule.map(module => `
            <div class="module-item">
                <div class="module-header">
                    <span class="module-title">${this.escapeHtml(module.title)}</span>
                    <span class="module-stats">${module.completed}/${module.total}</span>
                </div>
                <div class="module-progress-bar">
                    <div class="module-progress-fill" style="width: ${module.percentage}%"></div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render content type breakdown
     */
    renderContentTypes() {
        const chart = document.getElementById('content-type-chart');
        const byType = this.progressData.by_content_type || {};
        const types = Object.keys(byType);

        if (types.length === 0) {
            chart.innerHTML = '<div class="empty-message">No activities yet</div>';
            return;
        }

        // Content type icons
        const icons = {
            video: '&#127909;',
            reading: '&#128196;',
            quiz: '&#10067;',
            practice_quiz: '&#128221;',
            lab: '&#128300;',
            discussion: '&#128172;',
            hol: '&#9997;',
            coach: '&#128100;',
            assignment: '&#128221;',
            project: '&#127919;',
            rubric: '&#128203;'
        };

        // Find max for scaling
        const maxCount = Math.max(...types.map(t => byType[t].count));

        chart.innerHTML = types.map(type => {
            const data = byType[type];
            const pct = (data.count / maxCount) * 100;
            const completedPct = data.count > 0 ? (data.completed / data.count) * 100 : 0;

            return `
                <div class="content-type-row">
                    <div class="type-icon">${icons[type] || '&#128196;'}</div>
                    <div class="type-label">${this.formatContentType(type)}</div>
                    <div class="type-bar-track">
                        <div class="type-bar-fill" style="width: ${pct}%">
                            <div class="type-bar-completed" style="width: ${completedPct}%"></div>
                        </div>
                    </div>
                    <div class="type-count">${data.completed}/${data.count}</div>
                </div>
            `;
        }).join('');
    }

    /**
     * Render structure stats
     */
    renderStructure() {
        const structure = this.progressData.structure || {};
        const metrics = this.progressData.content_metrics || {};

        document.getElementById('module-count').textContent = structure.module_count || 0;
        document.getElementById('lesson-count').textContent = structure.lesson_count || 0;
        document.getElementById('activity-count').textContent = structure.activity_count || 0;
        document.getElementById('total-words').textContent = (metrics.total_word_count || 0).toLocaleString();
    }

    /**
     * Render activity table with current filter
     */
    renderActivityTable() {
        const tbody = document.getElementById('activity-tbody');
        let activities = this.progressData.activities || [];

        // Apply filter
        if (this.currentFilter !== 'all') {
            activities = activities.filter(a => a.build_state === this.currentFilter);
        }

        if (activities.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="5" class="empty-message">
                        ${this.currentFilter === 'all' ? 'No activities yet' : `No ${this.currentFilter} activities`}
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = activities.map(activity => `
            <tr class="activity-row" data-activity-id="${activity.id}">
                <td class="activity-title">
                    <a href="/courses/${this.courseId}/studio?activity=${activity.id}">
                        ${this.escapeHtml(activity.title)}
                    </a>
                </td>
                <td class="activity-module">${this.escapeHtml(activity.module_title || '')}</td>
                <td class="activity-type">
                    <span class="type-badge type-${activity.content_type}">
                        ${this.formatContentType(activity.content_type)}
                    </span>
                </td>
                <td class="activity-status">
                    <span class="status-badge status-${activity.build_state}">
                        ${this.formatState(activity.build_state)}
                    </span>
                </td>
                <td class="activity-words">${(activity.word_count || 0).toLocaleString()}</td>
            </tr>
        `).join('');
    }

    /**
     * Bind event handlers
     */
    bindEventHandlers() {
        // Filter buttons
        const filters = document.querySelectorAll('.filter-btn');
        filters.forEach(btn => {
            btn.addEventListener('click', () => {
                filters.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.filter;
                this.renderActivityTable();
            });
        });
    }

    /**
     * Format content type for display
     */
    formatContentType(type) {
        const names = {
            video: 'Video',
            reading: 'Reading',
            quiz: 'Quiz',
            practice_quiz: 'Practice Quiz',
            lab: 'Lab',
            discussion: 'Discussion',
            hol: 'Hands-On',
            coach: 'Coach',
            assignment: 'Assignment',
            project: 'Project',
            rubric: 'Rubric'
        };
        return names[type] || type;
    }

    /**
     * Format build state for display
     */
    formatState(state) {
        return state.charAt(0).toUpperCase() + state.slice(1);
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Export for use
window.ProgressDashboard = ProgressDashboard;
