"""Content-level humanization utilities.

Traverses Pydantic content schemas and humanizes all text fields,
providing a bridge between the text humanizer and content generation pipeline.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from src.utils.text_humanizer import (
    TextHumanizer,
    HumanizationResult,
    PatternMatch,
    PatternType,
    get_humanizer,
)


# Text fields to humanize for each content type schema
# Uses dot notation for nested fields, [] for list items
TEXT_FIELDS: Dict[str, List[str]] = {
    'VideoScriptSchema': [
        'title',
        'learning_objective',
        'hook.title',
        'hook.script_text',
        'hook.speaker_notes',
        'objective.title',
        'objective.script_text',
        'objective.speaker_notes',
        'content.title',
        'content.script_text',
        'content.speaker_notes',
        'ivq.title',
        'ivq.script_text',
        'ivq.speaker_notes',
        'summary.title',
        'summary.script_text',
        'summary.speaker_notes',
        'cta.title',
        'cta.script_text',
        'cta.speaker_notes',
    ],
    'ReadingSchema': [
        'title',
        'introduction',
        'sections[].heading',
        'sections[].body',
        'conclusion',
        'learning_objective',
    ],
    'QuizSchema': [
        'title',
        'questions[].question_text',
        'questions[].options[].text',
        'questions[].options[].feedback',
        'questions[].explanation',
        'learning_objective',
    ],
    'PracticeQuizSchema': [
        'title',
        'questions[].question_text',
        'questions[].options[].text',
        'questions[].options[].feedback',
        'questions[].options[].hint',
        'questions[].explanation',
        'learning_objective',
    ],
    'HOLSchema': [
        'title',
        'scenario',
        'parts[].title',
        'parts[].instructions',
        'submission_criteria',
        'rubric[].name',
        'rubric[].advanced',
        'rubric[].intermediate',
        'rubric[].beginner',
        'learning_objective',
    ],
    'CoachSchema': [
        'title',
        'learning_objectives[]',
        'scenario',
        'tasks[]',
        'conversation_starters[].starter_text',
        'conversation_starters[].purpose',
        'sample_responses[].response_text',
        'sample_responses[].feedback',
        'evaluation_criteria[]',
        'wrap_up',
        'reflection_prompts[]',
    ],
    'LabSchema': [
        'title',
        'overview',
        'learning_objectives[]',
        'setup_instructions[].instruction',
        'setup_instructions[].expected_result',
        'lab_exercises[]',
        'prerequisites[]',
    ],
    'DiscussionSchema': [
        'title',
        'main_prompt',
        'facilitation_questions[]',
        'engagement_hooks[]',
        'connection_to_objective',
        'learning_objective',
    ],
    'AssignmentSchema': [
        'title',
        'overview',
        'deliverables[].item',
        'grading_criteria[]',
        'submission_checklist[].item',
        'learning_objective',
    ],
    'ProjectMilestoneSchema': [
        'title',
        'overview',
        'prerequisites[]',
        'deliverables[].name',
        'deliverables[].description',
        'grading_criteria[]',
        'learning_objective',
    ],
    'RubricSchema': [
        'title',
        'criteria[].name',
        'criteria[].description',
        'criteria[].below_expectations',
        'criteria[].meets_expectations',
        'criteria[].exceeds_expectations',
        'learning_objective',
    ],
    'TextbookChapterSchema': [
        'title',
        'sections[].heading',
        'sections[].body',
        'glossary_terms[].term',
        'glossary_terms[].definition',
    ],
}


@dataclass
class ContentHumanizationResult:
    """Result of humanizing content.

    Attributes:
        content: The humanized content (Pydantic model or dict)
        original_score: Humanization score before processing
        score: Humanization score after processing
        patterns_found: Total patterns detected before humanization
        patterns_fixed: Number of patterns that were fixed
        field_results: Per-field humanization details
    """
    content: Any
    original_score: int
    score: int
    patterns_found: int
    patterns_fixed: int
    field_results: Dict[str, HumanizationResult]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'original_score': self.original_score,
            'score': self.score,
            'patterns_found': self.patterns_found,
            'patterns_fixed': self.patterns_fixed,
            'field_results': {
                k: v.to_dict() for k, v in self.field_results.items()
            }
        }


def _get_schema_name(content: Any) -> Optional[str]:
    """Get the schema name from a content object.

    Args:
        content: Pydantic model instance or dict with schema info

    Returns:
        Schema name string or None if not found
    """
    if isinstance(content, BaseModel):
        return content.__class__.__name__
    if isinstance(content, dict) and '_schema' in content:
        return content['_schema']
    return None


def _get_nested_value(obj: Any, path: str) -> Any:
    """Get a value from a nested object using dot notation.

    Args:
        obj: Object to traverse (dict or Pydantic model)
        path: Dot-separated path (e.g., 'hook.script_text')

    Returns:
        The value at the path, or None if not found
    """
    parts = path.split('.')
    current = obj

    for part in parts:
        if current is None:
            return None

        if isinstance(current, BaseModel):
            current = getattr(current, part, None)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def _set_nested_value(obj: Any, path: str, value: Any) -> None:
    """Set a value in a nested object using dot notation.

    Args:
        obj: Object to modify (dict or Pydantic model)
        path: Dot-separated path (e.g., 'hook.script_text')
        value: Value to set
    """
    parts = path.split('.')
    current = obj

    for part in parts[:-1]:
        if isinstance(current, BaseModel):
            current = getattr(current, part, None)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return

    final_part = parts[-1]
    if isinstance(current, BaseModel):
        setattr(current, final_part, value)
    elif isinstance(current, dict):
        current[final_part] = value


def _collect_text_values(content: Any, field_paths: List[str], prefix: str = "") -> Dict[str, str]:
    """Collect all text values from content based on field paths.

    Handles array notation like 'sections[].body' by expanding to all items.
    Supports nested arrays like 'questions[].options[].text'.

    Args:
        content: Content object (Pydantic model or dict)
        field_paths: List of field paths to extract
        prefix: Path prefix for nested calls

    Returns:
        Dictionary mapping expanded paths to their text values
    """
    texts = {}

    for path in field_paths:
        if '[]' in path:
            # Handle array fields - split only on first []
            bracket_pos = path.find('[]')
            base_path = path[:bracket_pos]
            remaining = path[bracket_pos + 2:].lstrip('.')

            # Get the array
            array = _get_nested_value(content, base_path) if base_path else content
            if not isinstance(array, list):
                continue

            for i, item in enumerate(array):
                # Build the indexed path
                indexed_base = f"{prefix}{base_path}[{i}]" if prefix else f"{base_path}[{i}]"

                if remaining:
                    if '[]' in remaining:
                        # More arrays to process - recurse
                        nested_texts = _collect_text_values(item, [remaining], indexed_base + ".")
                        texts.update(nested_texts)
                    else:
                        # Simple field after array index
                        value = _get_nested_value(item, remaining)
                        if isinstance(value, str) and value:
                            full_path = f"{indexed_base}.{remaining}"
                            texts[full_path] = value
                else:
                    # Direct string array
                    if isinstance(item, str):
                        texts[indexed_base] = item
        else:
            # Simple field path
            value = _get_nested_value(content, path)
            if isinstance(value, str) and value:
                full_path = f"{prefix}{path}" if prefix else path
                texts[full_path] = value

    return texts


def _apply_humanized_values(content: Any, humanized: Dict[str, str]) -> Any:
    """Apply humanized text values back to content.

    Args:
        content: Content object (Pydantic model or dict)
        humanized: Dictionary mapping paths to humanized text

    Returns:
        Modified content object (same instance if Pydantic, new dict if dict)
    """
    # Work with a mutable copy if dict
    if isinstance(content, dict):
        content = dict(content)
    elif isinstance(content, BaseModel):
        # Convert to dict for mutation, then back
        content = content.model_copy(deep=True)

    for path, text in humanized.items():
        _set_value_by_path(content, path, text)

    return content


def _set_value_by_path(obj: Any, path: str, value: str) -> None:
    """Set a value using a path that may include array indices.

    Args:
        obj: Object to modify
        path: Path with possible array indices (e.g., 'sections[0].body')
        value: Value to set
    """
    import re

    # Parse path into segments
    segments = []
    current = path
    while current:
        # Check for array index
        match = re.match(r'^(\w+)?\[(\d+)\](.*)$', current)
        if match:
            if match.group(1):
                segments.append(('attr', match.group(1)))
            segments.append(('index', int(match.group(2))))
            current = match.group(3).lstrip('.')
        else:
            # Regular attribute
            dot_pos = current.find('.')
            bracket_pos = current.find('[')

            if dot_pos == -1 and bracket_pos == -1:
                segments.append(('attr', current))
                break
            elif dot_pos == -1:
                segments.append(('attr', current[:bracket_pos]))
                current = current[bracket_pos:]
            elif bracket_pos == -1 or dot_pos < bracket_pos:
                segments.append(('attr', current[:dot_pos]))
                current = current[dot_pos + 1:]
            else:
                segments.append(('attr', current[:bracket_pos]))
                current = current[bracket_pos:]

    # Navigate to parent and set final value
    current_obj = obj
    for i, (seg_type, seg_value) in enumerate(segments[:-1]):
        if seg_type == 'attr':
            if isinstance(current_obj, BaseModel):
                current_obj = getattr(current_obj, seg_value)
            elif isinstance(current_obj, dict):
                current_obj = current_obj[seg_value]
        else:  # index
            current_obj = current_obj[seg_value]

    # Set final value
    final_type, final_value = segments[-1]
    if final_type == 'attr':
        if isinstance(current_obj, BaseModel):
            setattr(current_obj, final_value, value)
        elif isinstance(current_obj, dict):
            current_obj[final_value] = value
    else:  # index
        current_obj[final_value] = value


def humanize_content(
    content: Any,
    schema_name: Optional[str] = None,
    detect_only: bool = False,
    enabled_patterns: Optional[Dict[str, bool]] = None
) -> ContentHumanizationResult:
    """Humanize all text fields in a content object.

    Traverses the content structure and applies text humanization to all
    relevant text fields based on the schema type.

    Args:
        content: Pydantic model or dict representing generated content
        schema_name: Override schema name detection (useful for dicts)
        detect_only: If True, only detect patterns without applying fixes
        enabled_patterns: Dict of pattern types to enable/disable
                         (e.g., {'em_dash': True, 'formal_vocabulary': False})

    Returns:
        ContentHumanizationResult with humanized content and statistics
    """
    # Determine schema
    if schema_name is None:
        schema_name = _get_schema_name(content)

    if schema_name is None or schema_name not in TEXT_FIELDS:
        # Unknown schema, try to humanize common text fields
        field_paths = ['title', 'content', 'description', 'text', 'body']
    else:
        field_paths = TEXT_FIELDS[schema_name]

    # Collect all text values
    texts = _collect_text_values(content, field_paths)

    # Get humanizer
    humanizer = get_humanizer()

    # Calculate original score (before humanization)
    all_original_text = ' '.join(texts.values())
    original_score_data = humanizer.get_score(all_original_text)
    original_score = original_score_data['score']
    total_patterns_found = original_score_data['total_patterns']

    # Humanize each text field
    field_results = {}
    humanized_texts = {}
    patterns_fixed = 0

    for path, text in texts.items():
        result = humanizer.humanize(text, detect_only=detect_only)
        field_results[path] = result

        if not detect_only:
            humanized_texts[path] = result.humanized
            # Count patterns that were actually changed
            if result.humanized != result.original:
                patterns_fixed += result.pattern_count
        else:
            humanized_texts[path] = text

    # Apply humanized values back to content
    if not detect_only:
        content = _apply_humanized_values(content, humanized_texts)

    # Calculate final score
    all_humanized_text = ' '.join(humanized_texts.values())
    final_score_data = humanizer.get_score(all_humanized_text)
    final_score = final_score_data['score']

    return ContentHumanizationResult(
        content=content,
        original_score=original_score,
        score=final_score,
        patterns_found=total_patterns_found,
        patterns_fixed=patterns_fixed,
        field_results=field_results
    )


def get_content_score(content: Any, schema_name: Optional[str] = None) -> Dict[str, Any]:
    """Calculate humanization score for content without modifying it.

    Args:
        content: Pydantic model or dict representing generated content
        schema_name: Override schema name detection

    Returns:
        Score dictionary with overall score and per-field breakdown
    """
    # Determine schema
    if schema_name is None:
        schema_name = _get_schema_name(content)

    if schema_name is None or schema_name not in TEXT_FIELDS:
        field_paths = ['title', 'content', 'description', 'text', 'body']
    else:
        field_paths = TEXT_FIELDS[schema_name]

    # Collect all text values
    texts = _collect_text_values(content, field_paths)

    # Get humanizer
    humanizer = get_humanizer()

    # Calculate overall score
    all_text = ' '.join(texts.values())
    overall = humanizer.get_score(all_text)

    # Calculate per-field scores
    field_scores = {}
    for path, text in texts.items():
        if text:
            field_scores[path] = humanizer.get_score(text)

    # Get pattern breakdown
    patterns = humanizer.detect_patterns(all_text)
    pattern_breakdown = {}
    for pattern in patterns:
        ptype = pattern.pattern_type.value
        pattern_breakdown[ptype] = pattern_breakdown.get(ptype, 0) + 1

    return {
        'score': overall['score'],
        'word_count': overall['word_count'],
        'total_patterns': overall['total_patterns'],
        'patterns_per_100_words': overall['patterns_per_100_words'],
        'breakdown': pattern_breakdown,
        'field_scores': field_scores
    }


def get_supported_schemas() -> List[str]:
    """Get list of schema names that support humanization.

    Returns:
        List of schema name strings
    """
    return list(TEXT_FIELDS.keys())
