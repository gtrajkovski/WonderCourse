"""
AI-powered content analysis for imported content.
Detects content type, Bloom's level, and provides structural suggestions.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from src.core.models import BloomLevel
from src.utils.ai_client import generate


@dataclass
class AnalysisResult:
    """Result of AI-powered content analysis.

    Attributes:
        suggested_type: Suggested content type (video_script, reading, quiz, etc.)
        bloom_level: Detected Bloom's taxonomy level
        word_count: Total word count
        estimated_duration: Estimated time to complete in minutes
        structure_issues: List of structural problems found
        suggestions: List of improvement suggestions
    """
    suggested_type: str
    bloom_level: BloomLevel
    word_count: int
    estimated_duration: int
    structure_issues: List[str]
    suggestions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'suggested_type': self.suggested_type,
            'bloom_level': self.bloom_level.value,
            'word_count': self.word_count,
            'estimated_duration': self.estimated_duration,
            'structure_issues': self.structure_issues,
            'suggestions': self.suggestions
        }


class ContentAnalyzer:
    """Analyzes imported content for type, Bloom's level, and quality."""

    # Bloom's taxonomy verb indicators
    BLOOM_VERBS = {
        BloomLevel.REMEMBER: {
            'define', 'list', 'recall', 'name', 'identify', 'state',
            'describe', 'recognize', 'label', 'match'
        },
        BloomLevel.UNDERSTAND: {
            'explain', 'summarize', 'interpret', 'classify', 'compare',
            'discuss', 'paraphrase', 'illustrate', 'translate'
        },
        BloomLevel.APPLY: {
            'apply', 'demonstrate', 'use', 'solve', 'implement',
            'execute', 'operate', 'practice', 'calculate', 'modify'
        },
        BloomLevel.ANALYZE: {
            'analyze', 'examine', 'investigate', 'differentiate',
            'compare', 'contrast', 'distinguish', 'categorize', 'organize'
        },
        BloomLevel.EVALUATE: {
            'evaluate', 'assess', 'judge', 'critique', 'justify',
            'argue', 'defend', 'rate', 'recommend', 'prioritize'
        },
        BloomLevel.CREATE: {
            'create', 'design', 'develop', 'construct', 'produce',
            'invent', 'plan', 'compose', 'formulate', 'synthesize'
        }
    }

    # Content type indicators (keywords in content)
    TYPE_INDICATORS = {
        'video_script': {
            'hook', 'objective', 'summary', 'cta', 'call to action',
            'on screen', 'visual', 'scene', 'narration'
        },
        'reading': {
            'introduction', 'conclusion', 'section', 'chapter',
            'reference', 'citation', 'figure', 'table'
        },
        'quiz': {
            'question', 'answer', 'option', 'correct', 'incorrect',
            'multiple choice', 'distractor', 'feedback'
        },
        'lab': {
            'setup', 'prerequisite', 'environment', 'exercise',
            'step', 'instruction', 'command', 'output'
        },
        'assignment': {
            'deliverable', 'submission', 'requirement', 'checklist',
            'milestone', 'deadline', 'grading criteria'
        }
    }

    def __init__(self):
        """Initialize the content analyzer."""
        pass

    def analyze(self, content: Dict[str, Any], use_ai: bool = True) -> AnalysisResult:
        """
        Analyze content for type, Bloom's level, and quality.

        Args:
            content: Parsed content dictionary
            use_ai: Whether to use AI analysis (falls back to keyword matching if False)

        Returns:
            AnalysisResult with detected attributes and suggestions
        """
        # Basic metrics
        word_count = self._count_words(content)

        # Try AI analysis first
        if use_ai:
            try:
                return self._ai_analyze(content, word_count)
            except Exception:
                # Fall back to keyword-based analysis
                pass

        # Fallback: keyword-based analysis
        return self._keyword_analyze(content, word_count)

    def _ai_analyze(self, content: Dict[str, Any], word_count: int) -> AnalysisResult:
        """
        Use Claude API to analyze content.

        Args:
            content: Content dictionary
            word_count: Pre-calculated word count

        Returns:
            AnalysisResult with AI-powered analysis
        """
        system_prompt = """You are an educational content analyzer. Analyze the provided content and return a JSON response with:
{
  "suggested_type": "video_script | reading | quiz | lab | assignment | discussion | coach | hol | project",
  "bloom_level": "remember | understand | apply | analyze | evaluate | create",
  "structure_issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"]
}

Base your analysis on:
- Content type: Look for structural markers (WWHAA sections for videos, Q&A for quizzes, exercises for labs)
- Bloom's level: Identify cognitive verbs and complexity (remember=recall, understand=explain, apply=use, analyze=examine, evaluate=judge, create=design)
- Structure issues: Missing sections, incomplete formatting, unclear organization
- Suggestions: How to improve clarity, completeness, pedagogical alignment

Respond ONLY with valid JSON, no explanations."""

        # Prepare content summary for analysis
        content_str = self._summarize_content(content)
        user_prompt = f"Analyze this educational content:\n\n{content_str}\n\nWord count: {word_count}"

        # Call AI
        response = generate(system_prompt, user_prompt, max_tokens=1000)

        # Parse JSON response
        import json
        analysis = json.loads(response.strip())

        # Estimate duration based on type and word count
        suggested_type = analysis.get('suggested_type', 'reading')
        estimated_duration = self._estimate_duration(suggested_type, word_count, content)

        # Parse Bloom's level
        bloom_str = analysis.get('bloom_level', 'apply')
        bloom_level = self._parse_bloom_level(bloom_str)

        return AnalysisResult(
            suggested_type=suggested_type,
            bloom_level=bloom_level,
            word_count=word_count,
            estimated_duration=estimated_duration,
            structure_issues=analysis.get('structure_issues', []),
            suggestions=analysis.get('suggestions', [])
        )

    def _keyword_analyze(self, content: Dict[str, Any], word_count: int) -> AnalysisResult:
        """
        Fallback keyword-based analysis when AI unavailable.

        Args:
            content: Content dictionary
            word_count: Pre-calculated word count

        Returns:
            AnalysisResult with keyword-based analysis
        """
        content_str = self._summarize_content(content).lower()

        # Detect content type by keyword matching
        suggested_type = self._detect_type_by_keywords(content_str)

        # Detect Bloom's level by verb presence
        bloom_level = self._detect_bloom_by_verbs(content_str)

        # Estimate duration
        estimated_duration = self._estimate_duration(suggested_type, word_count, content)

        # Basic structure checks
        structure_issues = []
        suggestions = []

        # Check for common issues
        if word_count < 50:
            structure_issues.append("Content is very short (under 50 words)")
            suggestions.append("Expand content to provide more detail")

        if suggested_type == 'quiz' and 'answer' not in content_str:
            structure_issues.append("Quiz content missing answer indicators")
            suggestions.append("Ensure each question has marked correct answers")

        if suggested_type == 'video_script' and 'hook' not in content_str:
            structure_issues.append("Video script missing hook section")
            suggestions.append("Add WWHAA structure: Hook, Objective, Content, IVQ, Summary, CTA")

        return AnalysisResult(
            suggested_type=suggested_type,
            bloom_level=bloom_level,
            word_count=word_count,
            estimated_duration=estimated_duration,
            structure_issues=structure_issues,
            suggestions=suggestions
        )

    def _count_words(self, content: Dict[str, Any]) -> int:
        """
        Count total words in content dictionary.

        Args:
            content: Content dictionary

        Returns:
            Total word count
        """
        def count_recursive(obj):
            if isinstance(obj, str):
                return len(obj.split())
            elif isinstance(obj, dict):
                return sum(count_recursive(v) for v in obj.values())
            elif isinstance(obj, list):
                return sum(count_recursive(item) for item in obj)
            return 0

        return count_recursive(content)

    def _summarize_content(self, content: Dict[str, Any], max_chars: int = 2000) -> str:
        """
        Create text summary of content for analysis.

        Args:
            content: Content dictionary
            max_chars: Maximum characters to include

        Returns:
            String summary of content
        """
        import json
        content_str = json.dumps(content, indent=2)
        if len(content_str) > max_chars:
            content_str = content_str[:max_chars] + "...(truncated)"
        return content_str

    def _detect_type_by_keywords(self, content_str: str) -> str:
        """
        Detect content type by keyword presence.

        Args:
            content_str: Lowercase content string

        Returns:
            Detected content type
        """
        scores = {}
        for content_type, keywords in self.TYPE_INDICATORS.items():
            score = sum(1 for keyword in keywords if keyword in content_str)
            scores[content_type] = score

        # Return type with highest score, default to 'reading'
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type

        return 'reading'

    def _detect_bloom_by_verbs(self, content_str: str) -> BloomLevel:
        """
        Detect Bloom's level by verb presence.

        Args:
            content_str: Lowercase content string

        Returns:
            Detected Bloom's level
        """
        # Count verbs for each level
        scores = {}
        for level, verbs in self.BLOOM_VERBS.items():
            score = sum(1 for verb in verbs if re.search(rf'\b{verb}\b', content_str))
            scores[level] = score

        # Return highest scoring level, default to APPLY
        if scores:
            best_level = max(scores, key=scores.get)
            if scores[best_level] > 0:
                return best_level

        return BloomLevel.APPLY

    def _parse_bloom_level(self, bloom_str: str) -> BloomLevel:
        """
        Parse Bloom's level string to enum.

        Args:
            bloom_str: Bloom level string (lowercase)

        Returns:
            BloomLevel enum
        """
        bloom_map = {
            'remember': BloomLevel.REMEMBER,
            'understand': BloomLevel.UNDERSTAND,
            'apply': BloomLevel.APPLY,
            'analyze': BloomLevel.ANALYZE,
            'evaluate': BloomLevel.EVALUATE,
            'create': BloomLevel.CREATE
        }
        return bloom_map.get(bloom_str.lower(), BloomLevel.APPLY)

    def _estimate_duration(self, content_type: str, word_count: int, content: Dict[str, Any]) -> int:
        """
        Estimate completion duration in minutes.

        Args:
            content_type: Detected content type
            word_count: Total word count
            content: Content dictionary for additional context

        Returns:
            Estimated duration in minutes
        """
        # Industry-standard rates
        if content_type == 'video_script':
            # 150 words per minute for video narration
            return max(1, round(word_count / 150))
        elif content_type == 'reading':
            # 238 words per minute for reading
            return max(1, round(word_count / 238))
        elif content_type == 'quiz':
            # 1.5 minutes per question
            question_count = self._count_quiz_questions(content)
            return max(1, round(question_count * 1.5))
        elif content_type in ['lab', 'assignment', 'hol']:
            # Estimate 10-30 minutes for hands-on work
            return max(10, min(30, word_count // 50))
        else:
            # Default to reading rate
            return max(1, round(word_count / 238))

    def _count_quiz_questions(self, content: Dict[str, Any]) -> int:
        """
        Count questions in quiz content.

        Args:
            content: Content dictionary

        Returns:
            Number of questions found
        """
        # Look for 'questions' key or count question-like structures
        if 'questions' in content and isinstance(content['questions'], list):
            return len(content['questions'])

        # Count occurrences of question indicators
        content_str = str(content).lower()
        question_count = content_str.count('question')
        return max(1, question_count)
