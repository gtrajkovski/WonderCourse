"""Utility for inferring audience level from learner description.

Analyzes target learner description to determine appropriate content difficulty level.
"""

import re
from typing import Tuple


# Keywords indicating beginner level
BEGINNER_KEYWORDS = [
    'beginner', 'beginners', 'novice', 'new to', 'introduction', 'introductory',
    'no experience', 'no prior', 'first time', 'getting started', 'basics',
    'fundamental', 'entry level', 'entry-level', 'newcomer', 'starting out',
    'unfamiliar', 'no background', 'zero experience', 'learn from scratch',
    'complete beginner', 'absolute beginner', 'newbie', 'non-technical',
    'never used', 'never worked with', 'curious about', 'exploring'
]

# Keywords indicating intermediate level
INTERMEDIATE_KEYWORDS = [
    'intermediate', 'some experience', 'familiar with', 'working knowledge',
    'basic understanding', 'have used', 'practiced', 'comfortable with',
    'moderate', 'developing', 'practitioners', 'hands-on experience',
    'some background', 'foundational knowledge', 'prior exposure',
    'build on', 'expand', 'deepen', 'enhance', 'grow', 'advance'
]

# Keywords indicating advanced level
ADVANCED_KEYWORDS = [
    'advanced', 'expert', 'experienced', 'proficient', 'senior',
    'professional', 'master', 'specialist', 'veteran', 'skilled',
    'deep knowledge', 'extensive experience', 'years of experience',
    'architect', 'lead', 'principal', 'complex', 'sophisticated',
    'cutting edge', 'cutting-edge', 'state of the art', 'research',
    'optimize', 'optimization', 'performance tuning', 'enterprise'
]


def infer_audience_level(learner_description: str) -> Tuple[str, float]:
    """Infer audience level from learner description.

    Analyzes the description for keywords indicating experience level
    and returns the most likely audience level with a confidence score.

    Args:
        learner_description: Description of target learners/audience.

    Returns:
        Tuple of (level, confidence) where:
        - level: 'beginner', 'intermediate', or 'advanced'
        - confidence: 0.0 to 1.0 indicating match strength
    """
    if not learner_description:
        return 'intermediate', 0.0

    text = learner_description.lower()

    # Count matches for each level
    beginner_count = sum(1 for kw in BEGINNER_KEYWORDS if kw in text)
    intermediate_count = sum(1 for kw in INTERMEDIATE_KEYWORDS if kw in text)
    advanced_count = sum(1 for kw in ADVANCED_KEYWORDS if kw in text)

    total_matches = beginner_count + intermediate_count + advanced_count

    if total_matches == 0:
        # No clear indicators - default to intermediate
        return 'intermediate', 0.0

    # Determine level based on highest count
    if beginner_count >= intermediate_count and beginner_count >= advanced_count:
        confidence = beginner_count / (total_matches + 1)
        return 'beginner', min(confidence, 1.0)
    elif advanced_count >= intermediate_count:
        confidence = advanced_count / (total_matches + 1)
        return 'advanced', min(confidence, 1.0)
    else:
        confidence = intermediate_count / (total_matches + 1)
        return 'intermediate', min(confidence, 1.0)


def suggest_audience_level(learner_description: str) -> dict:
    """Get audience level suggestion with detailed breakdown.

    Provides more detailed analysis for UI feedback.

    Args:
        learner_description: Description of target learners/audience.

    Returns:
        dict with:
        - suggested_level: Recommended level
        - confidence: Match confidence (0-1)
        - reasoning: Explanation of why this level was chosen
        - matches: Dict of matched keywords per level
    """
    if not learner_description:
        return {
            'suggested_level': 'intermediate',
            'confidence': 0.0,
            'reasoning': 'No learner description provided. Defaulting to intermediate level.',
            'matches': {'beginner': [], 'intermediate': [], 'advanced': []}
        }

    text = learner_description.lower()

    # Find actual matched keywords for each level
    beginner_matches = [kw for kw in BEGINNER_KEYWORDS if kw in text]
    intermediate_matches = [kw for kw in INTERMEDIATE_KEYWORDS if kw in text]
    advanced_matches = [kw for kw in ADVANCED_KEYWORDS if kw in text]

    level, confidence = infer_audience_level(learner_description)

    # Build reasoning
    if not beginner_matches and not intermediate_matches and not advanced_matches:
        reasoning = "No specific level indicators found in the description. Defaulting to intermediate level for balanced content."
    elif level == 'beginner':
        reasoning = f"Detected beginner indicators: {', '.join(beginner_matches[:3])}. Content should use accessible language and avoid assumptions of prior knowledge."
    elif level == 'advanced':
        reasoning = f"Detected advanced indicators: {', '.join(advanced_matches[:3])}. Content can assume deep familiarity and focus on sophisticated concepts."
    else:
        reasoning = f"Detected intermediate indicators: {', '.join(intermediate_matches[:3])}. Content should build on foundational knowledge while introducing new concepts."

    return {
        'suggested_level': level,
        'confidence': round(confidence, 2),
        'reasoning': reasoning,
        'matches': {
            'beginner': beginner_matches,
            'intermediate': intermediate_matches,
            'advanced': advanced_matches
        }
    }
