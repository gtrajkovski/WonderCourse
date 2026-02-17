"""Standards loader utility for content generation.

Loads active standards profiles and builds prompt rule strings
for injection into AI generator system prompts.
"""

from typing import Optional
from pathlib import Path

from src.core.models import ContentStandardsProfile, Course
from src.core.standards_store import StandardsStore


# Module-level store instance (lazy initialization)
_standards_store: Optional[StandardsStore] = None


def get_standards_store() -> StandardsStore:
    """Get or create the standards store singleton."""
    global _standards_store
    if _standards_store is None:
        _standards_store = StandardsStore()
    return _standards_store


def load_standards(course: Course) -> ContentStandardsProfile:
    """Load the active standards profile for a course.

    Args:
        course: The course to get standards for

    Returns:
        The active ContentStandardsProfile
    """
    store = get_standards_store()
    return store.get_for_course(course)


def load_standards_by_id(profile_id: Optional[str] = None) -> ContentStandardsProfile:
    """Load a standards profile by ID or get default.

    Args:
        profile_id: Optional profile ID. If None, returns default.

    Returns:
        The ContentStandardsProfile
    """
    store = get_standards_store()
    if profile_id:
        profile = store.load(profile_id)
        if profile:
            return profile
    return store.get_default()


def build_video_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build video generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for video script generation
    """
    structure_text = " -> ".join(standards.video_structure) if standards.video_structure else "flexible structure"
    structure_req = "REQUIRED" if standards.video_structure_required else "suggested"

    return f"""**VIDEO RULES:**
- Maximum duration: {standards.video_max_duration_min} minutes
- Ideal duration: {standards.video_ideal_min_duration}-{standards.video_ideal_max_duration} minutes
- Speaking rate: {standards.video_wpm} words per minute
- Structure ({structure_req}): {structure_text}
- Include speaker notes for delivery guidance"""


def build_reading_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build reading generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for reading generation
    """
    ref_format = standards.reading_reference_format.upper()
    if ref_format == "NONE":
        ref_text = "References are optional"
    else:
        ref_text = f"Include {standards.reading_min_references}-{standards.reading_max_references} references in {ref_format} format"

    free_links = "Ensure all links are freely accessible" if standards.reading_require_free_links else ""

    return f"""**READING RULES:**
- Maximum word count: {standards.reading_max_words} words
- {ref_text}
- Maximum optional readings: {standards.reading_max_optional}
{f"- {free_links}" if free_links else ""}"""


def build_quiz_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build quiz generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for quiz generation
    """
    feedback_req = "REQUIRED for each option" if standards.quiz_require_per_option_feedback else "optional"
    balance_req = f"No answer letter should exceed {standards.quiz_max_distribution_skew_percent}% of total" if standards.quiz_require_balanced_distribution else "distribution not enforced"

    return f"""**QUIZ RULES:**
- Options per question: {standards.quiz_options_per_question}
- Per-option feedback: {feedback_req}
- Answer distribution: {balance_req}
- Time estimate: {standards.quiz_time_per_question_min} minutes per question
- Multiple correct answers: {"allowed" if standards.quiz_allow_multiple_correct else "not allowed"}
- Scenario-based questions: {"allowed" if standards.quiz_allow_scenario_based else "not allowed"}"""


def build_practice_quiz_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build practice quiz generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for practice quiz generation
    """
    hints_req = "REQUIRED" if standards.practice_quiz_require_hints else "optional"
    explanations_req = "REQUIRED" if standards.practice_quiz_require_explanations else "optional"

    base_rules = build_quiz_prompt_rules(standards)

    return f"""{base_rules}

**PRACTICE QUIZ SPECIFIC:**
- Hints per option: {hints_req}
- Detailed explanations: {explanations_req}
- Focus on formative learning, not evaluation
- Provide scaffolded feedback that guides without giving away answers"""


def build_hol_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build HOL generation rules for prompt injection.

    v1.2.0: Enhanced to provide explicit rubric configuration with
    exact level names, point values, and criteria count.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for HOL generation
    """
    # Build detailed levels text
    levels_text = ", ".join([f"{l['name']} ({l['points']} pts)" for l in standards.hol_rubric_levels])
    level_names = [l['name'] for l in standards.hol_rubric_levels]
    level_names_list = ", ".join(level_names)

    return f"""**HANDS-ON LAB RULES:**
- Submission format: {standards.hol_submission_format}
- Maximum written response: {standards.hol_max_word_count} words

**RUBRIC CONFIGURATION (CRITICAL - FOLLOW EXACTLY):**
- Create exactly {standards.hol_rubric_criteria_count} evaluation criteria (STRICT)
- Total possible points: {standards.hol_rubric_total_points}
- Performance levels (USE THESE EXACT NAMES): {levels_text}

Each criterion MUST include descriptions for ALL of these levels: {level_names_list}
Use the EXACT point values shown above for each level."""


def build_coach_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build coach dialogue generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for coach generation
    """
    levels_text = ", ".join(standards.coach_evaluation_levels)
    scenario_req = "REQUIRED" if standards.coach_require_scenario else "optional"
    examples_req = "REQUIRED" if standards.coach_require_example_responses else "optional"

    return f"""**COACH DIALOGUE RULES:**
- Evaluation levels: {levels_text}
- Scenario: {scenario_req}
- Example responses per level: {examples_req}
- Use Socratic questioning to guide student thinking
- Provide formative, growth-oriented feedback"""


def build_lab_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build lab generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for lab generation
    """
    setup_req = "REQUIRED" if standards.lab_require_setup_steps else "optional"

    return f"""**LAB RULES:**
- Exercises: {standards.lab_min_exercises}-{standards.lab_max_exercises}
- Setup steps: {setup_req}
- Lab is UNGRADED - focus on practice and exploration
- Include clear verification steps for each exercise"""


def build_discussion_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build discussion generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for discussion generation
    """
    hooks_req = "REQUIRED" if standards.discussion_require_engagement_hooks else "optional"

    return f"""**DISCUSSION RULES:**
- Facilitation questions: {standards.discussion_min_facilitation_questions}-{standards.discussion_max_facilitation_questions}
- Engagement hooks: {hooks_req}
- Design for peer interaction, not just instructor-student Q&A
- Create open-ended prompts that invite diverse perspectives"""


def build_assignment_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build assignment generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for assignment generation
    """
    return f"""**ASSIGNMENT RULES:**
- Deliverables: {standards.assignment_min_deliverables}-{standards.assignment_max_deliverables}
- Grading criteria: {standards.assignment_min_grading_criteria}-{standards.assignment_max_grading_criteria}
- Each deliverable must have clear point value
- Include submission checklist with required and optional items"""


def build_project_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build project milestone generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for project generation
    """
    milestones = ", ".join(standards.project_milestone_types)

    return f"""**PROJECT MILESTONE RULES:**
- Milestone types: {milestones}
- Deliverables per milestone: {standards.project_min_deliverables}-{standards.project_max_deliverables}
- Build scaffolded progression across milestones
- Include prerequisites linking to prior milestones"""


def build_rubric_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build rubric generation rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for rubric generation
    """
    levels_text = ", ".join(standards.rubric_levels)

    return f"""**RUBRIC RULES:**
- Criteria: {standards.rubric_min_criteria}-{standards.rubric_max_criteria}
- Performance levels: {levels_text}
- Each criterion must have clear descriptions for all levels
- Weights must sum to 100%"""


def build_tone_prompt_rules(standards: ContentStandardsProfile) -> str:
    """Build tone and voice rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for tone guidelines
    """
    voice_rules = []
    if standards.tone_allow_first_person:
        voice_rules.append("First-person narrative is allowed")
    else:
        voice_rules.append("Avoid first-person narrative")

    if standards.tone_require_active_voice:
        voice_rules.append("Use active voice")

    if standards.tone_require_concrete_examples:
        voice_rules.append("Include concrete examples with specific numbers/details")

    voice_text = "\n- ".join(voice_rules)
    custom = f"\n- {standards.tone_custom_guidelines}" if standards.tone_custom_guidelines else ""

    return f"""**TONE & VOICE:**
{standards.tone_description}

- {voice_text}{custom}"""


def build_attribution_rules(standards: ContentStandardsProfile) -> str:
    """Build attribution rules for prompt injection.

    Args:
        standards: The active standards profile

    Returns:
        Formatted rules string for attribution
    """
    if not standards.require_attribution:
        return ""

    if standards.author_attribution:
        return f"""**ATTRIBUTION:**
Include this attribution: {standards.author_attribution}"""
    else:
        return """**ATTRIBUTION:**
Include appropriate author attribution."""


def build_all_prompt_rules(
    standards: ContentStandardsProfile,
    content_type: str
) -> str:
    """Build all relevant prompt rules for a content type.

    Args:
        standards: The active standards profile
        content_type: One of: video, reading, quiz, practice_quiz, hol, coach,
                     lab, discussion, assignment, project, rubric

    Returns:
        Combined rules string for the content type
    """
    # Content-specific rules
    rules_map = {
        "video": build_video_prompt_rules,
        "reading": build_reading_prompt_rules,
        "quiz": build_quiz_prompt_rules,
        "practice_quiz": build_practice_quiz_prompt_rules,
        "hol": build_hol_prompt_rules,
        "coach": build_coach_prompt_rules,
        "lab": build_lab_prompt_rules,
        "discussion": build_discussion_prompt_rules,
        "assignment": build_assignment_prompt_rules,
        "project": build_project_prompt_rules,
        "rubric": build_rubric_prompt_rules,
    }

    content_rules = rules_map.get(content_type, lambda s: "")
    tone_rules = build_tone_prompt_rules(standards)
    attribution_rules = build_attribution_rules(standards)

    parts = [content_rules(standards), tone_rules]
    if attribution_rules:
        parts.append(attribution_rules)

    return "\n\n".join(parts)
