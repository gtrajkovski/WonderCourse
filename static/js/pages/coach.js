/**
 * Coach Controller - Interactive coaching session interface
 *
 * Manages:
 * - Session initialization and lifecycle
 * - Real-time message streaming via SSE
 * - Evaluation display and progress tracking
 * - Session summary and continuation
 */
class CoachController {
  constructor(courseId, activityId, persona, dialogueStructure) {
    this.courseId = courseId;
    this.activityId = activityId;
    this.persona = persona;
    this.dialogueStructure = dialogueStructure;

    this.sessionId = null;
    this.currentEventSource = null;
    this.messageCount = 0;

    // DOM elements
    this.messagesContainer = document.getElementById('messages-container');
    this.messagesList = document.getElementById('messages-list');
    this.messageInput = document.getElementById('message-input');
    this.messageForm = document.getElementById('message-form');
    this.sendBtn = document.getElementById('send-btn');
    this.endSessionBtn = document.getElementById('end-session-btn');
    this.coverageBar = document.getElementById('coverage-bar');
    this.coverageText = document.getElementById('coverage-text');
    this.toggleEvalBtn = document.getElementById('toggle-eval-btn');
    this.evaluationSidebar = document.getElementById('evaluation-sidebar');
    this.currentLevelBadge = document.getElementById('current-level-badge');
    this.strengthsList = document.getElementById('strengths-list');
    this.improvementsList = document.getElementById('improvements-list');
    this.summaryModal = document.getElementById('summary-modal');
    this.summaryContent = document.getElementById('summary-content');
    this.newSessionBtn = document.getElementById('new-session-btn');
    this.continueSessionBtn = document.getElementById('continue-session-btn');

    // Initialize
    this.init();
  }

  async init() {
    // Initialize help manager
    if (window.HelpManager) {
      window.help = new HelpManager();
      window.help.init();
    }

    // Bind event handlers
    this.bindEventHandlers();

    // Check for previous session
    const previousSessionId = sessionStorage.getItem(`coach-session-${this.activityId}`);
    if (previousSessionId) {
      const resume = confirm('You have a previous coaching session. Would you like to continue?');
      if (resume) {
        await this.continuePreviousSession(previousSessionId);
        return;
      }
    }

    // Start new session
    await this.startSession();
  }

  bindEventHandlers() {
    // Message form submission
    this.messageForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Keyboard shortcuts
    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // End session button
    this.endSessionBtn.addEventListener('click', () => {
      this.endSession();
    });

    // Toggle evaluation sidebar
    this.toggleEvalBtn.addEventListener('click', () => {
      this.evaluationSidebar.classList.toggle('collapsed');
    });

    // Summary modal buttons
    this.newSessionBtn.addEventListener('click', () => {
      this.startNewSession();
    });

    this.continueSessionBtn.addEventListener('click', () => {
      this.closeSummaryModal();
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.closeEventSource();
    });
  }

  async startSession() {
    try {
      const response = await window.api.post(
        `/courses/${this.courseId}/activities/${this.activityId}/coach/start`,
        {}
      );

      this.sessionId = response.session_id;
      sessionStorage.setItem(`coach-session-${this.activityId}`, this.sessionId);

      // Display welcome message
      this.addCoachMessage(response.welcome_message, false);

      window.toast.success('Session started');
    } catch (error) {
      window.toast.error('Failed to start session: ' + error.message);
      console.error('Start session error:', error);
    }
  }

  async continuePreviousSession(transcriptId) {
    try {
      const response = await window.api.post(
        `/courses/${this.courseId}/activities/${this.activityId}/coach/continue`,
        { transcript_id: transcriptId }
      );

      this.sessionId = response.session_id;
      sessionStorage.setItem(`coach-session-${this.activityId}`, this.sessionId);

      // Restore messages
      response.messages.forEach(msg => {
        if (msg.role === 'user') {
          this.addUserMessage(msg.content, false);
        } else if (msg.role === 'assistant') {
          this.addCoachMessage(msg.content, false);
        }
      });

      // Update coverage
      if (response.coverage) {
        this.updateCoverage(response.coverage);
      }

      window.toast.success('Session resumed');
    } catch (error) {
      window.toast.error('Failed to resume session: ' + error.message);
      console.error('Continue session error:', error);
      // Fall back to starting new session
      await this.startSession();
    }
  }

  async sendMessage() {
    const message = this.messageInput.value.trim();
    if (!message) return;

    // Disable input
    this.messageInput.disabled = true;
    this.sendBtn.disabled = true;

    // Add user message to UI
    this.addUserMessage(message);

    // Clear input
    this.messageInput.value = '';

    // Start streaming response
    await this.streamCoachResponse(message);

    // Re-enable input
    this.messageInput.disabled = false;
    this.sendBtn.disabled = false;
    this.messageInput.focus();
  }

  async streamCoachResponse(userMessage) {
    // Show typing indicator
    const typingIndicator = this.showTypingIndicator();

    try {
      // Create EventSource for SSE streaming
      const url = `/api/courses/${this.courseId}/activities/${this.activityId}/coach/chat/stream`;

      // Post message first, then create EventSource with session params
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: userMessage,
          evaluate: true
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let coachMessageElement = null;
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          const data = JSON.parse(line.substring(6));

          if (data.type === 'chunk') {
            // Remove typing indicator on first chunk
            if (typingIndicator && typingIndicator.parentElement) {
              typingIndicator.remove();
            }

            // Create message element if it doesn't exist
            if (!coachMessageElement) {
              coachMessageElement = this.addCoachMessage('', true);
            }

            // Append chunk to message
            const textElement = coachMessageElement.querySelector('.message-text');
            textElement.textContent += data.text;

            // Auto-scroll
            this.scrollToBottom();
          } else if (data.type === 'evaluation') {
            // Display evaluation
            this.displayEvaluation(data.data, coachMessageElement);
          } else if (data.type === 'done') {
            // Streaming complete
            break;
          } else if (data.type === 'error') {
            throw new Error(data.error);
          }
        }
      }

    } catch (error) {
      if (typingIndicator && typingIndicator.parentElement) {
        typingIndicator.remove();
      }
      window.toast.error('Failed to get response: ' + error.message);
      console.error('Stream response error:', error);
    }
  }

  addUserMessage(content, scroll = true) {
    const messageEl = this.createMessageElement('user', content, 'You');
    this.messagesList.appendChild(messageEl);

    if (scroll) {
      this.scrollToBottom();
    }

    this.messageCount++;
  }

  addCoachMessage(content, streaming = false) {
    const messageEl = this.createMessageElement('coach', content, this.persona.name);
    this.messagesList.appendChild(messageEl);

    if (!streaming) {
      this.scrollToBottom();
    }

    this.messageCount++;

    return messageEl;
  }

  createMessageElement(type, content, author) {
    const template = document.getElementById('message-template');
    const clone = template.content.cloneNode(true);
    const messageDiv = clone.querySelector('.message');

    messageDiv.classList.add(type);

    const avatar = messageDiv.querySelector('.avatar-icon');
    avatar.textContent = type === 'user' ? '👤' : '🧑‍🏫';

    const authorEl = messageDiv.querySelector('.message-author');
    authorEl.textContent = author;

    const timestampEl = messageDiv.querySelector('.message-timestamp');
    timestampEl.textContent = this.formatTimestamp(new Date());

    const textEl = messageDiv.querySelector('.message-text');
    textEl.textContent = content;

    return messageDiv;
  }

  showTypingIndicator() {
    const template = document.getElementById('typing-indicator-template');
    const clone = template.content.cloneNode(true);
    const indicator = clone.querySelector('.typing-indicator');
    this.messagesList.appendChild(indicator);
    this.scrollToBottom();
    return indicator;
  }

  displayEvaluation(evaluation, messageElement) {
    // Update sidebar
    if (evaluation.level) {
      this.currentLevelBadge.textContent = evaluation.level;
      this.currentLevelBadge.className = `level-badge ${evaluation.level.toLowerCase()}`;
    }

    if (evaluation.strengths && evaluation.strengths.length > 0) {
      this.strengthsList.innerHTML = '';
      evaluation.strengths.forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        this.strengthsList.appendChild(li);
      });
    }

    if (evaluation.areas_for_improvement && evaluation.areas_for_improvement.length > 0) {
      this.improvementsList.innerHTML = '';
      evaluation.areas_for_improvement.forEach(improvement => {
        const li = document.createElement('li');
        li.textContent = improvement;
        this.improvementsList.appendChild(li);
      });
    }

    // Add evaluation badge to message
    if (messageElement && evaluation.level) {
      const evalDiv = messageElement.querySelector('.message-evaluation');
      const badgeEl = evalDiv.querySelector('.eval-badge');
      badgeEl.textContent = evaluation.level;
      badgeEl.className = `eval-badge ${evaluation.level.toLowerCase()}`;
      evalDiv.style.display = 'block';
    }

    // Update coverage if provided
    if (evaluation.coverage !== undefined) {
      this.updateCoverage({ coverage_percentage: evaluation.coverage });
    }
  }

  updateCoverage(coverageData) {
    const percentage = Math.round(coverageData.coverage_percentage || 0);
    this.coverageBar.style.width = `${percentage}%`;
    this.coverageText.textContent = `${percentage}%`;
  }

  async endSession() {
    if (!confirm('Are you sure you want to end this coaching session?')) {
      return;
    }

    try {
      const response = await window.api.post(
        `/courses/${this.courseId}/activities/${this.activityId}/coach/end`,
        { session_id: this.sessionId }
      );

      // Clear session storage
      sessionStorage.removeItem(`coach-session-${this.activityId}`);

      // Show summary modal
      this.showSummary(response);

    } catch (error) {
      window.toast.error('Failed to end session: ' + error.message);
      console.error('End session error:', error);
    }
  }

  showSummary(summaryData) {
    // Build summary HTML
    const template = document.getElementById('session-summary-template');
    const clone = template.content.cloneNode(true);

    // Overall level
    const overallLevel = clone.querySelector('.overall-level');
    if (summaryData.evaluation && summaryData.evaluation.overall_level) {
      overallLevel.textContent = summaryData.evaluation.overall_level;
      overallLevel.className = `overall-level ${summaryData.evaluation.overall_level.toLowerCase()}`;
    }

    // Scores
    const summaryScores = clone.querySelector('.summary-scores');
    if (summaryData.evaluation && summaryData.evaluation.scores) {
      summaryScores.innerHTML = '';
      Object.entries(summaryData.evaluation.scores).forEach(([criterion, score]) => {
        const div = document.createElement('div');
        div.className = 'score-item';
        div.innerHTML = `<span>${criterion}</span><span>${score}/3</span>`;
        summaryScores.appendChild(div);
      });
    }

    // Insights
    const insightsList = clone.querySelector('.insights-list');
    if (summaryData.summary) {
      insightsList.innerHTML = '';
      const insights = summaryData.summary.split('\n').filter(line => line.trim());
      insights.forEach(insight => {
        const li = document.createElement('li');
        li.textContent = insight;
        insightsList.appendChild(li);
      });
    }

    // Recommendations (placeholder)
    const recommendationsList = clone.querySelector('.recommendations-list');
    recommendationsList.innerHTML = '<li>Review the key concepts discussed</li><li>Practice applying what you learned</li>';

    // Coverage
    const coverageDetails = clone.querySelector('.coverage-details');
    coverageDetails.textContent = `Completed ${this.messageCount} conversation turns`;

    // Insert into modal
    this.summaryContent.innerHTML = '';
    this.summaryContent.appendChild(clone);

    // Show modal
    this.summaryModal.style.display = 'flex';
  }

  closeSummaryModal() {
    this.summaryModal.style.display = 'none';
  }

  async startNewSession() {
    this.closeSummaryModal();

    // Clear messages
    this.messagesList.innerHTML = '';
    this.messageCount = 0;

    // Reset evaluation sidebar
    this.currentLevelBadge.textContent = 'Not evaluated';
    this.currentLevelBadge.className = 'level-badge';
    this.strengthsList.innerHTML = '<li class="empty-state">Complete a turn to see evaluation</li>';
    this.improvementsList.innerHTML = '<li class="empty-state">Complete a turn to see evaluation</li>';

    // Reset coverage
    this.coverageBar.style.width = '0%';
    this.coverageText.textContent = '0%';

    // Start new session
    await this.startSession();
  }

  closeEventSource() {
    if (this.currentEventSource) {
      this.currentEventSource.close();
      this.currentEventSource = null;
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  formatTimestamp(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
}

// Make available globally
window.CoachController = CoachController;
