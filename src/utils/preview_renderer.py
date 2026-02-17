"""Learner-facing preview renderer.

Transforms content into learner-facing HTML, stripping author-only
elements like speaker notes, correct answer indicators, and explanations.
"""

import json
from typing import Any, Dict, Optional
import html


class PreviewRenderer:
    """Renders content as learners would see it.

    Strips author-only elements and formats content for learner preview.
    """

    def render_content(self, content_type: str, content: Any) -> str:
        """Dispatch to appropriate renderer based on content type.

        Args:
            content_type: The type of content (video, reading, quiz, etc.)
            content: The content data (dict or JSON string)

        Returns:
            HTML string for learner preview.
        """
        # Parse JSON string if needed
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return self._escape(content)

        if not isinstance(content, dict):
            return f"<p>{self._escape(str(content))}</p>"

        renderers = {
            'video': self.render_video_script,
            'reading': self.render_reading,
            'quiz': self.render_quiz,
            'hol': self.render_hol,
            'coach': self.render_coach,
            'lab': self.render_lab,
            'discussion': self.render_discussion,
            'assignment': self.render_assignment,
            'project': self.render_project,
        }

        renderer = renderers.get(content_type, self.render_generic)
        return renderer(content)

    def render_video_script(self, content: Dict[str, Any]) -> str:
        """Render video script as formatted HTML.

        Excludes speaker notes (author-only).
        """
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('learning_objective'):
            html_parts.append(
                f'<div class="learning-objective">'
                f'<strong>Learning Objective:</strong> {self._escape(content["learning_objective"])}'
                f'</div>'
            )

        # WWHAA sections
        sections = ['hook', 'objective', 'content', 'ivq', 'summary', 'cta']
        section_labels = {
            'hook': 'Introduction',
            'objective': 'What You\'ll Learn',
            'content': 'Main Content',
            'ivq': 'Check Your Understanding',
            'summary': 'Summary',
            'cta': 'Next Steps'
        }

        for section_key in sections:
            section_data = content.get(section_key)
            if section_data:
                if isinstance(section_data, dict):
                    script_text = section_data.get('script_text', '')
                    title = section_data.get('title', section_labels.get(section_key, section_key.title()))
                else:
                    script_text = section_data
                    title = section_labels.get(section_key, section_key.title())

                if script_text:
                    html_parts.append(
                        f'<div class="video-section">'
                        f'<h2>{self._escape(title)}</h2>'
                        f'<p>{self._escape(script_text)}</p>'
                        f'</div>'
                    )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_reading(self, content: Dict[str, Any]) -> str:
        """Render reading as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('introduction'):
            html_parts.append(f'<div class="introduction"><p>{self._escape(content["introduction"])}</p></div>')

        sections = content.get('sections', [])
        for section in sections:
            heading = section.get('heading') or section.get('title', '')
            body = section.get('body') or section.get('content') or section.get('text', '')

            html_parts.append(
                f'<div class="reading-section">'
                f'<h2>{self._escape(heading)}</h2>'
                f'<p>{self._escape(body)}</p>'
                f'</div>'
            )

        if content.get('conclusion'):
            html_parts.append(
                f'<div class="conclusion">'
                f'<h2>Conclusion</h2>'
                f'<p>{self._escape(content["conclusion"])}</p>'
                f'</div>'
            )

        references = content.get('references', [])
        if references:
            ref_items = []
            for ref in references:
                if isinstance(ref, dict):
                    citation = ref.get('citation') or ref.get('title', '')
                    url = ref.get('url')
                    if url:
                        ref_items.append(f'<li><a href="{self._escape(url)}">{self._escape(citation)}</a></li>')
                    else:
                        ref_items.append(f'<li>{self._escape(citation)}</li>')
                else:
                    ref_items.append(f'<li>{self._escape(str(ref))}</li>')

            html_parts.append(
                f'<div class="references">'
                f'<h3>References</h3>'
                f'<ul>{"".join(ref_items)}</ul>'
                f'</div>'
            )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_quiz(self, content: Dict[str, Any]) -> str:
        """Render quiz as interactive learner experience.

        Learner selects an answer, then sees feedback for their choice.
        Correct/incorrect status and explanation shown after selection.
        """
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('passing_score_percentage'):
            html_parts.append(
                f'<p class="quiz-info">Passing score: {content["passing_score_percentage"]}%</p>'
            )

        questions = content.get('questions', [])
        for i, q in enumerate(questions, 1):
            question_text = q.get('question_text') or q.get('question') or q.get('text', '')
            explanation = q.get('explanation', '')

            q_html = [
                f'<div class="quiz-question" data-question="{i}">',
                f'<p class="question-text"><strong>Question {i}:</strong> {self._escape(question_text)}</p>',
                f'<div class="options">'
            ]

            options = q.get('options') or q.get('choices', [])
            for j, opt in enumerate(options):
                if isinstance(opt, dict):
                    opt_text = opt.get('text', '')
                    is_correct = opt.get('is_correct', False)
                    feedback = opt.get('feedback', '')
                    hint = opt.get('hint', '')  # For practice quizzes
                else:
                    opt_text = str(opt)
                    is_correct = False
                    feedback = ''
                    hint = ''

                letter = chr(65 + j)  # A, B, C, D...
                correct_class = 'correct' if is_correct else 'incorrect'
                feedback_icon = "✓" if is_correct else "✗"
                hint_html = f'<div class="option-hint hidden">{self._escape(hint)}</div>' if hint else ""

                q_html.append(
                    f'<div class="option" data-correct="{str(is_correct).lower()}">'
                    f'<input type="radio" name="q{i}" id="q{i}_{letter}" value="{letter}" '
                    f'onclick="handleQuizAnswer(this, {str(is_correct).lower()})">'
                    f'<label for="q{i}_{letter}">{letter}. {self._escape(opt_text)}</label>'
                    f'<div class="option-feedback hidden" data-feedback="{correct_class}">'
                    f'<span class="feedback-icon">{feedback_icon}</span> '
                    f'{self._escape(feedback)}'
                    f'</div>'
                    f'{hint_html}'
                    f'</div>'
                )

            q_html.append('</div>')  # close options

            # Add explanation (shown after answering)
            if explanation:
                q_html.append(
                    f'<div class="question-explanation hidden">'
                    f'<strong>Explanation:</strong> {self._escape(explanation)}'
                    f'</div>'
                )

            q_html.append('</div>')  # close question

            html_parts.append('\n'.join(q_html))

        # Add interactive JavaScript
        html_parts.append('''
<script>
function handleQuizAnswer(input, isCorrect) {
    const questionDiv = input.closest('.quiz-question');
    const options = questionDiv.querySelectorAll('.option');

    // Disable all inputs in this question
    options.forEach(opt => {
        opt.querySelector('input').disabled = true;
    });

    // Show feedback for selected option
    const selectedOption = input.closest('.option');
    const feedback = selectedOption.querySelector('.option-feedback');
    if (feedback) {
        feedback.classList.remove('hidden');
        selectedOption.classList.add(isCorrect ? 'selected-correct' : 'selected-incorrect');
    }

    // Show correct answer if wrong
    if (!isCorrect) {
        options.forEach(opt => {
            if (opt.dataset.correct === 'true') {
                opt.classList.add('show-correct');
                const correctFeedback = opt.querySelector('.option-feedback');
                if (correctFeedback) correctFeedback.classList.remove('hidden');
            }
        });
    }

    // Show explanation
    const explanation = questionDiv.querySelector('.question-explanation');
    if (explanation) {
        explanation.classList.remove('hidden');
    }
}
</script>
<style>
.quiz-question { margin-bottom: 24px; padding: 16px; background: #2a2a3e; border-radius: 8px; }
.option { padding: 8px 12px; margin: 4px 0; border-radius: 4px; cursor: pointer; }
.option:hover { background: #3a3a4e; }
.option input[disabled] { cursor: not-allowed; }
.option-feedback { margin-top: 8px; padding: 8px; border-radius: 4px; font-size: 0.9em; }
.option-feedback[data-feedback="correct"] { background: #1a3a1a; color: #4ade80; }
.option-feedback[data-feedback="incorrect"] { background: #3a1a1a; color: #f87171; }
.option-feedback .feedback-icon { font-weight: bold; }
.selected-correct { background: #1a3a1a; border: 1px solid #4ade80; }
.selected-incorrect { background: #3a1a1a; border: 1px solid #f87171; }
.show-correct { background: #1a3a1a; border: 1px solid #4ade80; }
.question-explanation { margin-top: 16px; padding: 12px; background: #1a1a2e; border-left: 3px solid #60a5fa; }
.hidden { display: none; }
</style>
''')

        return '\n'.join(html_parts) or '<p class="empty">No questions available.</p>'

    def render_hol(self, content: Dict[str, Any]) -> str:
        """Render hands-on lab as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('scenario'):
            html_parts.append(
                f'<div class="scenario">'
                f'<h2>Scenario</h2>'
                f'<p>{self._escape(content["scenario"])}</p>'
                f'</div>'
            )

        parts = content.get('parts', [])
        for part in parts:
            html_parts.append(
                f'<div class="hol-part">'
                f'<h2>Part {part.get("part_number", "")}: {self._escape(part.get("title", ""))}</h2>'
                f'<p class="time-estimate">Estimated time: {part.get("estimated_minutes", 0)} minutes</p>'
                f'<div class="instructions">{self._escape(part.get("instructions", ""))}</div>'
                f'</div>'
            )

        if content.get('submission_criteria'):
            html_parts.append(
                f'<div class="submission">'
                f'<h2>Submission Criteria</h2>'
                f'<p>{self._escape(content["submission_criteria"])}</p>'
                f'</div>'
            )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_coach(self, content: Dict[str, Any]) -> str:
        """Render coach dialogue as formatted HTML.

        Excludes sample responses and evaluation criteria (author-only).
        """
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        objectives = content.get('learning_objectives', [])
        if objectives:
            obj_items = ''.join(f'<li>{self._escape(obj)}</li>' for obj in objectives)
            html_parts.append(
                f'<div class="objectives">'
                f'<h2>Learning Objectives</h2>'
                f'<ul>{obj_items}</ul>'
                f'</div>'
            )

        if content.get('scenario'):
            html_parts.append(
                f'<div class="scenario">'
                f'<h2>Scenario</h2>'
                f'<p>{self._escape(content["scenario"])}</p>'
                f'</div>'
            )

        tasks = content.get('tasks', [])
        if tasks:
            task_items = ''.join(f'<li>{self._escape(task)}</li>' for task in tasks)
            html_parts.append(
                f'<div class="tasks">'
                f'<h2>Your Tasks</h2>'
                f'<ol>{task_items}</ol>'
                f'</div>'
            )

        starters = content.get('conversation_starters', [])
        if starters:
            html_parts.append('<div class="starters"><h2>Conversation Starters</h2>')
            for starter in starters:
                text = starter.get('starter_text', '') if isinstance(starter, dict) else str(starter)
                html_parts.append(f'<p class="starter">"{self._escape(text)}"</p>')
            html_parts.append('</div>')

        if content.get('wrap_up'):
            html_parts.append(
                f'<div class="wrapup">'
                f'<h2>Wrap-Up</h2>'
                f'<p>{self._escape(content["wrap_up"])}</p>'
                f'</div>'
            )

        prompts = content.get('reflection_prompts', [])
        if prompts:
            prompt_items = ''.join(f'<li>{self._escape(p)}</li>' for p in prompts)
            html_parts.append(
                f'<div class="reflection">'
                f'<h2>Reflection Questions</h2>'
                f'<ul>{prompt_items}</ul>'
                f'</div>'
            )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_lab(self, content: Dict[str, Any]) -> str:
        """Render lab as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('overview'):
            html_parts.append(f'<p class="overview">{self._escape(content["overview"])}</p>')

        if content.get('estimated_minutes'):
            html_parts.append(
                f'<p class="time-estimate">Estimated time: {content["estimated_minutes"]} minutes</p>'
            )

        prereqs = content.get('prerequisites', [])
        if prereqs:
            prereq_items = ''.join(f'<li>{self._escape(p)}</li>' for p in prereqs)
            html_parts.append(
                f'<div class="prerequisites">'
                f'<h2>Prerequisites</h2>'
                f'<ul>{prereq_items}</ul>'
                f'</div>'
            )

        objectives = content.get('learning_objectives', [])
        if objectives:
            obj_items = ''.join(f'<li>{self._escape(obj)}</li>' for obj in objectives)
            html_parts.append(
                f'<div class="objectives">'
                f'<h2>Learning Objectives</h2>'
                f'<ul>{obj_items}</ul>'
                f'</div>'
            )

        setup = content.get('setup_instructions', [])
        if setup:
            html_parts.append('<div class="setup"><h2>Setup Instructions</h2>')
            for step in setup:
                html_parts.append(
                    f'<div class="setup-step">'
                    f'<p><strong>Step {step.get("step_number", "")}:</strong> {self._escape(step.get("instruction", ""))}</p>'
                    f'<p class="expected">Expected result: {self._escape(step.get("expected_result", ""))}</p>'
                    f'</div>'
                )
            html_parts.append('</div>')

        exercises = content.get('lab_exercises', [])
        if exercises:
            ex_items = ''.join(f'<li>{self._escape(ex)}</li>' for ex in exercises)
            html_parts.append(
                f'<div class="exercises">'
                f'<h2>Exercises</h2>'
                f'<ol>{ex_items}</ol>'
                f'</div>'
            )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_discussion(self, content: Dict[str, Any]) -> str:
        """Render discussion as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('main_prompt'):
            html_parts.append(
                f'<div class="main-prompt">'
                f'<h2>Discussion Prompt</h2>'
                f'<p>{self._escape(content["main_prompt"])}</p>'
                f'</div>'
            )

        questions = content.get('facilitation_questions', [])
        if questions:
            q_items = ''.join(f'<li>{self._escape(q)}</li>' for q in questions)
            html_parts.append(
                f'<div class="facilitation">'
                f'<h2>Discussion Questions</h2>'
                f'<ul>{q_items}</ul>'
                f'</div>'
            )

        hooks = content.get('engagement_hooks', [])
        if hooks:
            html_parts.append('<div class="hooks"><h2>Things to Consider</h2>')
            for hook in hooks:
                html_parts.append(f'<p class="hook">{self._escape(hook)}</p>')
            html_parts.append('</div>')

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_assignment(self, content: Dict[str, Any]) -> str:
        """Render assignment as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        if content.get('overview'):
            html_parts.append(f'<p class="overview">{self._escape(content["overview"])}</p>')

        meta = []
        if content.get('total_points'):
            meta.append(f'Total Points: {content["total_points"]}')
        if content.get('estimated_hours'):
            meta.append(f'Estimated Time: {content["estimated_hours"]} hours')
        if meta:
            html_parts.append(f'<p class="assignment-meta">{" | ".join(meta)}</p>')

        deliverables = content.get('deliverables', [])
        if deliverables:
            html_parts.append('<div class="deliverables"><h2>Deliverables</h2><ul>')
            for d in deliverables:
                item = d.get('item', '') if isinstance(d, dict) else str(d)
                points = d.get('points', 0) if isinstance(d, dict) else 0
                html_parts.append(f'<li>{self._escape(item)} ({points} points)</li>')
            html_parts.append('</ul></div>')

        criteria = content.get('grading_criteria', [])
        if criteria:
            c_items = ''.join(f'<li>{self._escape(c)}</li>' for c in criteria)
            html_parts.append(
                f'<div class="grading">'
                f'<h2>Grading Criteria</h2>'
                f'<ul>{c_items}</ul>'
                f'</div>'
            )

        checklist = content.get('submission_checklist', [])
        if checklist:
            html_parts.append('<div class="checklist"><h2>Submission Checklist</h2><ul>')
            for item in checklist:
                if isinstance(item, dict):
                    text = item.get('item', '')
                    required = item.get('required', True)
                    label = ' (optional)' if not required else ''
                else:
                    text = str(item)
                    label = ''
                html_parts.append(f'<li>{self._escape(text)}{label}</li>')
            html_parts.append('</ul></div>')

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_project(self, content: Dict[str, Any]) -> str:
        """Render project as formatted HTML."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        overview = content.get('overview') or content.get('description')
        if overview:
            html_parts.append(f'<p class="overview">{self._escape(overview)}</p>')

        objectives = content.get('learning_objectives', [])
        if objectives:
            obj_items = ''.join(f'<li>{self._escape(obj)}</li>' for obj in objectives)
            html_parts.append(
                f'<div class="objectives">'
                f'<h2>Learning Objectives</h2>'
                f'<ul>{obj_items}</ul>'
                f'</div>'
            )

        milestones = content.get('milestones', [])
        if milestones:
            html_parts.append('<div class="milestones"><h2>Milestones</h2>')
            for i, m in enumerate(milestones, 1):
                if isinstance(m, dict):
                    title = m.get('title') or m.get('name', f'Milestone {i}')
                    desc = m.get('description') or m.get('deliverables', '')
                else:
                    title = str(m)
                    desc = ''

                html_parts.append(
                    f'<div class="milestone">'
                    f'<h3>Milestone {i}: {self._escape(title)}</h3>'
                    f'{f"<p>{self._escape(desc)}</p>" if desc else ""}'
                    f'</div>'
                )
            html_parts.append('</div>')

        criteria = content.get('grading_criteria', [])
        if criteria:
            c_items = ''.join(f'<li>{self._escape(c)}</li>' for c in criteria)
            html_parts.append(
                f'<div class="grading">'
                f'<h2>Grading Criteria</h2>'
                f'<ul>{c_items}</ul>'
                f'</div>'
            )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def render_generic(self, content: Dict[str, Any]) -> str:
        """Render generic content as formatted sections."""
        html_parts = []

        if content.get('title'):
            html_parts.append(f'<h1 class="content-title">{self._escape(content["title"])}</h1>')

        # Render remaining key-value pairs
        for key, value in content.items():
            if key == 'title':
                continue

            if isinstance(value, str):
                html_parts.append(
                    f'<div class="section">'
                    f'<h2>{self._escape(key.replace("_", " ").title())}</h2>'
                    f'<p>{self._escape(value)}</p>'
                    f'</div>'
                )
            elif isinstance(value, list):
                items = ''.join(f'<li>{self._escape(str(v))}</li>' for v in value)
                html_parts.append(
                    f'<div class="section">'
                    f'<h2>{self._escape(key.replace("_", " ").title())}</h2>'
                    f'<ul>{items}</ul>'
                    f'</div>'
                )

        return '\n'.join(html_parts) or '<p class="empty">No content available.</p>'

    def _escape(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ''
        return html.escape(str(text))


# Module-level instance for convenience
_renderer = PreviewRenderer()


def render_learner_preview(content_type: str, content: Any) -> str:
    """Render content as learner would see it.

    Convenience function using module-level renderer instance.

    Args:
        content_type: The type of content (video, reading, quiz, etc.)
        content: The content data (dict or JSON string)

    Returns:
        HTML string for learner preview.
    """
    return _renderer.render_content(content_type, content)
