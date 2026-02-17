"""Text humanization utilities for reducing AI-sounding patterns.

Detects and fixes common AI writing telltales:
- Em-dashes replaced with commas/periods
- Formal vocabulary simplified to plain words
- Three-adjective lists reduced
- AI transition phrases removed
- Overly parallel structures varied
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class PatternType(Enum):
    """Types of AI patterns that can be detected."""
    EM_DASH = "em_dash"
    FORMAL_VOCABULARY = "formal_vocabulary"
    ADJECTIVE_LIST = "adjective_list"
    AI_TRANSITION = "ai_transition"
    PARALLEL_STRUCTURE = "parallel_structure"
    FILLER_PHRASE = "filler_phrase"
    # v1.2.0: New Coursera v3.0 patterns
    REPEAT_OPENER = "repeat_opener"       # Same word starts consecutive sentences
    ENSURES_OPENER = "ensures_opener"     # "This ensures/enables/allows..."
    NOT_ONLY_BUT = "not_only_but"         # "Not only X, but also Y"
    LONG_COMMA_LIST = "long_comma_list"   # 4+ comma-separated items
    ADVERB_TRIPLET = "adverb_triplet"     # 3+ adverbs in proximity


@dataclass
class PatternMatch:
    """A detected AI pattern in text."""
    pattern_type: PatternType
    original: str
    suggestion: str
    start: int
    end: int

    def to_dict(self):
        return {
            "pattern_type": self.pattern_type.value,
            "original": self.original,
            "suggestion": self.suggestion,
            "start": self.start,
            "end": self.end
        }


@dataclass
class HumanizationResult:
    """Result of humanizing text."""
    original: str
    humanized: str
    patterns_found: List[PatternMatch]
    pattern_count: int

    def to_dict(self):
        return {
            "original": self.original,
            "humanized": self.humanized,
            "patterns_found": [p.to_dict() for p in self.patterns_found],
            "pattern_count": self.pattern_count
        }


class TextHumanizer:
    """Service for detecting and fixing AI-sounding text patterns."""

    # Formal vocabulary replacements
    FORMAL_VOCAB = {
        "utilize": "use",
        "utilizes": "uses",
        "utilizing": "using",
        "utilization": "use",
        "facilitate": "help",
        "facilitates": "helps",
        "facilitating": "helping",
        "facilitation": "help",
        "comprehensive": "complete",
        "comprehensively": "fully",
        "implement": "build",
        "implements": "builds",
        "implementing": "building",
        "implementation": "setup",
        "leverage": "use",
        "leverages": "uses",
        "leveraging": "using",
        "optimize": "improve",
        "optimizes": "improves",
        "optimizing": "improving",
        "optimization": "improvement",
        "demonstrate": "show",
        "demonstrates": "shows",
        "demonstrating": "showing",
        "establish": "set up",
        "establishes": "sets up",
        "establishing": "setting up",
        "incorporate": "add",
        "incorporates": "adds",
        "incorporating": "adding",
        "subsequently": "then",
        "consequently": "so",
        "furthermore": "also",
        "additionally": "also",
        "nevertheless": "but",
        "nonetheless": "still",
        "prior to": "before",
        "in order to": "to",
        "due to the fact that": "because",
        "in the event that": "if",
        "at this point in time": "now",
        "in close proximity to": "near",
        "a large number of": "many",
        "the vast majority of": "most",
        "in spite of the fact that": "although",
        "for the purpose of": "to",
        "with regard to": "about",
        "in reference to": "about",
        "pertaining to": "about",
        "commence": "start",
        "commences": "starts",
        "commencing": "starting",
        "terminate": "end",
        "terminates": "ends",
        "terminating": "ending",
        "endeavor": "try",
        "endeavors": "tries",
        "endeavoring": "trying",
        "ascertain": "find out",
        "ascertains": "finds out",
        "sufficient": "enough",
        "insufficient": "not enough",
        "methodology": "method",
        "methodologies": "methods",
        "functionality": "features",
        "capabilities": "features",
        "paradigm": "model",
        "synergy": "teamwork",
        "synergies": "benefits",
        "holistic": "complete",
        "robust": "strong",
        "seamless": "smooth",
        "seamlessly": "smoothly",
        "streamline": "simplify",
        "streamlines": "simplifies",
        "streamlining": "simplifying",
        "empower": "help",
        "empowers": "helps",
        "empowering": "helping",
    }

    # AI transition phrases to remove or simplify
    AI_TRANSITIONS = [
        (r"Here'?s where it gets (?:really |truly )?(?:powerful|interesting|exciting)[.!]?\s*", ""),
        (r"Let'?s (?:bring this together|dive (?:in|deeper)|explore this further)[.!]?\s*", ""),
        (r"Now,? here'?s the (?:thing|key|secret)[.:]\s*", ""),
        (r"This is where (?:the magic happens|things get interesting)[.!]?\s*", ""),
        (r"(?:But |And )?wait,? there'?s more[.!]?\s*", ""),
        (r"The (?:beauty|power) of this (?:approach |solution )?is that\s*", ""),
        (r"What makes this (?:really |truly )?(?:special|unique|powerful) is\s*", ""),
        (r"Think of it (?:like |as )this[.:]\s*", ""),
        (r"(?:Simply|Just) put[,:]?\s*", ""),
        (r"In essence[,:]?\s*", ""),
        (r"At its core[,:]?\s*", ""),
        (r"The bottom line is[,:]?\s*", ""),
        (r"(?:First and foremost|Last but not least)[,:]?\s*", ""),
        (r"It'?s worth (?:noting|mentioning) that\s*", ""),
        (r"(?:Interestingly|Importantly|Notably|Crucially)[,:]?\s*", ""),
        (r"As (?:you can see|we can see|mentioned earlier)[,:]?\s*", ""),
        (r"Without further ado[,:]?\s*", ""),
        (r"That being said[,:]?\s*", "However, "),
        (r"Having said that[,:]?\s*", "However, "),
        (r"With that in mind[,:]?\s*", "So "),
        (r"All things considered[,:]?\s*", "Overall, "),
        (r"When all is said and done[,:]?\s*", "In the end, "),
        (r"At the end of the day[,:]?\s*", "Ultimately, "),
    ]

    # Filler phrases that add no value
    FILLER_PHRASES = [
        (r"\b(?:very|really|truly|actually|basically|essentially|literally|absolutely|completely|totally|extremely|incredibly|amazingly)\s+", " "),
        (r"\bquite\s+(?=\w)", ""),
        (r"\bpretty\s+much\s+", ""),
        (r"\bit is important to note that\s+", ""),
        (r"\bit should be noted that\s+", ""),
        (r"\bneedless to say[,]?\s*", ""),
        (r"\bof course[,]?\s*", ""),
        (r"\bobviously[,]?\s*", ""),
        (r"\bclearly[,]?\s*", ""),
        (r"\bundoubtedly[,]?\s*", ""),
        (r"\bwithout a doubt[,]?\s*", ""),
    ]

    def __init__(self):
        """Initialize the humanizer with compiled patterns."""
        # Compile formal vocab pattern (case-insensitive word boundaries)
        vocab_pattern = r'\b(' + '|'.join(re.escape(word) for word in self.FORMAL_VOCAB.keys()) + r')\b'
        self._vocab_regex = re.compile(vocab_pattern, re.IGNORECASE)

        # Compile AI transition patterns
        self._transition_patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in self.AI_TRANSITIONS]

        # Compile filler patterns
        self._filler_patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in self.FILLER_PHRASES]

        # Em-dash patterns
        self._em_dash_pattern = re.compile(r'\s*[—–]\s*')

        # Three-adjective list pattern: "word, word, and word"
        self._adj_list_pattern = re.compile(
            r'\b(\w+),\s+(\w+),\s+and\s+(\w+)\b',
            re.IGNORECASE
        )

        # v1.2.0: New Coursera v3.0 patterns

        # REPEAT_OPENER: Detect 2+ consecutive sentences starting with same word
        # Matches: "Python is great. Python is fast." but not across paragraphs
        self._repeat_opener_pattern = re.compile(
            r'(?:^|[.!?]\s+)([A-Z][a-z]+)\s+[^.!?]+[.!?]\s+\1\s+',
            re.MULTILINE
        )

        # ENSURES_OPENER: "This ensures...", "This enables...", etc.
        self._ensures_opener_pattern = re.compile(
            r'(?:^|[.!?]\s+)(?:This|That|It)\s+(?:ensures?|enables?|allows?|provides?|creates?|offers?)\b',
            re.IGNORECASE | re.MULTILINE
        )

        # NOT_ONLY_BUT: "Not only X, but also Y" construction
        self._not_only_pattern = re.compile(
            r'\bnot\s+only\b[^.!?]*?\bbut\s+(?:also\s+)?',
            re.IGNORECASE
        )

        # LONG_COMMA_LIST: 4+ items in comma-separated list
        self._long_list_pattern = re.compile(
            r'\b(\w+(?:\s+\w+)?),\s+(\w+(?:\s+\w+)?),\s+(\w+(?:\s+\w+)?),\s+(?:and\s+)?(\w+(?:\s+\w+)?)\b',
            re.IGNORECASE
        )

        # ADVERB_TRIPLET: Three -ly adverbs within close proximity (50 chars)
        self._adverb_triplet_pattern = re.compile(
            r'\b(\w+ly)\b[^.!?]{0,50}\b(\w+ly)\b[^.!?]{0,50}\b(\w+ly)\b',
            re.IGNORECASE
        )

    def detect_patterns(self, text: str) -> List[PatternMatch]:
        """Detect AI patterns in text without modifying it.

        Args:
            text: Text to analyze.

        Returns:
            List of detected patterns with suggestions.
        """
        patterns = []

        # Detect em-dashes
        for match in self._em_dash_pattern.finditer(text):
            patterns.append(PatternMatch(
                pattern_type=PatternType.EM_DASH,
                original=match.group(),
                suggestion=", ",
                start=match.start(),
                end=match.end()
            ))

        # Detect formal vocabulary
        for match in self._vocab_regex.finditer(text):
            word = match.group().lower()
            replacement = self.FORMAL_VOCAB.get(word, word)
            # Preserve original case
            if match.group()[0].isupper():
                replacement = replacement.capitalize()
            patterns.append(PatternMatch(
                pattern_type=PatternType.FORMAL_VOCABULARY,
                original=match.group(),
                suggestion=replacement,
                start=match.start(),
                end=match.end()
            ))

        # Detect AI transitions
        for regex, replacement in self._transition_patterns:
            for match in regex.finditer(text):
                patterns.append(PatternMatch(
                    pattern_type=PatternType.AI_TRANSITION,
                    original=match.group(),
                    suggestion=replacement,
                    start=match.start(),
                    end=match.end()
                ))

        # Detect three-adjective lists
        for match in self._adj_list_pattern.finditer(text):
            # Suggest keeping first two adjectives
            suggestion = f"{match.group(1)} and {match.group(3)}"
            patterns.append(PatternMatch(
                pattern_type=PatternType.ADJECTIVE_LIST,
                original=match.group(),
                suggestion=suggestion,
                start=match.start(),
                end=match.end()
            ))

        # Detect filler phrases
        for regex, replacement in self._filler_patterns:
            for match in regex.finditer(text):
                patterns.append(PatternMatch(
                    pattern_type=PatternType.FILLER_PHRASE,
                    original=match.group(),
                    suggestion=replacement.strip(),
                    start=match.start(),
                    end=match.end()
                ))

        # v1.2.0: Detect new Coursera v3.0 patterns

        # Detect repeat openers (same word starting consecutive sentences)
        for match in self._repeat_opener_pattern.finditer(text):
            word = match.group(1)
            patterns.append(PatternMatch(
                pattern_type=PatternType.REPEAT_OPENER,
                original=match.group(),
                suggestion=f"[Vary sentence opener - '{word}' appears twice]",
                start=match.start(),
                end=match.end()
            ))

        # Detect "This ensures/enables/allows" openers
        for match in self._ensures_opener_pattern.finditer(text):
            patterns.append(PatternMatch(
                pattern_type=PatternType.ENSURES_OPENER,
                original=match.group(),
                suggestion="[Rephrase without 'This ensures/enables/allows']",
                start=match.start(),
                end=match.end()
            ))

        # Detect "Not only...but also" constructions
        for match in self._not_only_pattern.finditer(text):
            patterns.append(PatternMatch(
                pattern_type=PatternType.NOT_ONLY_BUT,
                original=match.group(),
                suggestion="[Simplify to plain 'X and Y' structure]",
                start=match.start(),
                end=match.end()
            ))

        # Detect 4+ item comma lists
        for match in self._long_list_pattern.finditer(text):
            patterns.append(PatternMatch(
                pattern_type=PatternType.LONG_COMMA_LIST,
                original=match.group(),
                suggestion="[Break into shorter list or bullet points]",
                start=match.start(),
                end=match.end()
            ))

        # Detect adverb triplets (3+ -ly words in proximity)
        for match in self._adverb_triplet_pattern.finditer(text):
            adverbs = [match.group(1), match.group(2), match.group(3)]
            patterns.append(PatternMatch(
                pattern_type=PatternType.ADVERB_TRIPLET,
                original=match.group(),
                suggestion=f"[Reduce adverbs: keep strongest of {', '.join(adverbs)}]",
                start=match.start(),
                end=match.end()
            ))

        # Sort by position
        patterns.sort(key=lambda p: p.start)

        return patterns

    def humanize(self, text: str, detect_only: bool = False) -> HumanizationResult:
        """Humanize text by applying all pattern fixes.

        Args:
            text: Text to humanize.
            detect_only: If True, only detect patterns without applying fixes.

        Returns:
            HumanizationResult with original, humanized text, and patterns found.
        """
        patterns = self.detect_patterns(text)

        if detect_only:
            return HumanizationResult(
                original=text,
                humanized=text,
                patterns_found=patterns,
                pattern_count=len(patterns)
            )

        # Apply fixes
        humanized = text

        # Replace em-dashes
        humanized = self._replace_em_dashes(humanized)

        # Replace formal vocabulary
        humanized = self._replace_formal_vocab(humanized)

        # Remove AI transitions
        humanized = self._remove_ai_transitions(humanized)

        # Remove filler phrases
        humanized = self._remove_fillers(humanized)

        # Simplify three-adjective lists
        humanized = self._simplify_adj_lists(humanized)

        # v1.2.0: Apply new pattern fixes
        # Remove "This ensures/enables" openers
        humanized = self._remove_ensures_openers(humanized)

        # Simplify "not only...but also" constructions
        humanized = self._simplify_not_only(humanized)

        # Note: REPEAT_OPENER, LONG_COMMA_LIST, and ADVERB_TRIPLET are
        # detected but require manual intervention - they are flagged
        # in the patterns_found list for user review

        # Clean up extra whitespace
        humanized = self._clean_whitespace(humanized)

        return HumanizationResult(
            original=text,
            humanized=humanized,
            patterns_found=patterns,
            pattern_count=len(patterns)
        )

    def _replace_em_dashes(self, text: str) -> str:
        """Replace em-dashes with commas or periods based on context."""
        # Simple replacement with comma for now
        # More sophisticated logic could analyze sentence structure
        return self._em_dash_pattern.sub(', ', text)

    def _replace_formal_vocab(self, text: str) -> str:
        """Replace formal vocabulary with plain alternatives."""
        def replace_match(match):
            word = match.group().lower()
            replacement = self.FORMAL_VOCAB.get(word, word)
            # Preserve original case
            if match.group()[0].isupper():
                replacement = replacement.capitalize()
            return replacement

        return self._vocab_regex.sub(replace_match, text)

    def _remove_ai_transitions(self, text: str) -> str:
        """Remove or simplify AI transition phrases."""
        result = text
        for regex, replacement in self._transition_patterns:
            result = regex.sub(replacement, result)
        return result

    def _remove_fillers(self, text: str) -> str:
        """Remove filler phrases and unnecessary intensifiers."""
        result = text
        for regex, replacement in self._filler_patterns:
            result = regex.sub(replacement, result)
        return result

    def _simplify_adj_lists(self, text: str) -> str:
        """Reduce three-adjective lists to two adjectives."""
        def replace_match(match):
            # Keep first and third adjective for variety
            return f"{match.group(1)} and {match.group(3)}"

        return self._adj_list_pattern.sub(replace_match, text)

    def _clean_whitespace(self, text: str) -> str:
        """Clean up extra whitespace from replacements."""
        # Multiple spaces to single
        text = re.sub(r'  +', ' ', text)
        # Space before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        # Multiple newlines to double
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Trim lines
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)

    # v1.2.0: New pattern fix methods

    def _remove_ensures_openers(self, text: str) -> str:
        """Remove 'This ensures/enables/allows' patterns.

        These patterns require manual rewriting, so we remove the
        'This ensures' part and leave the rest for the author to rework.
        """
        # Replace "This ensures that X" -> "X" (remove the opener)
        result = re.sub(
            r'(?:^|(?<=[.!?]\s))(?:This|That|It)\s+(?:ensures?|enables?|allows?|provides?|creates?|offers?)\s+(?:that\s+)?',
            '',
            text,
            flags=re.IGNORECASE | re.MULTILINE
        )
        return result

    def _simplify_not_only(self, text: str) -> str:
        """Simplify 'not only X but also Y' to 'X and Y'.

        Example: "not only fast but also reliable" -> "fast and reliable"
        """
        def replace_match(match):
            # Get the text between "not only" and "but also"
            full = match.group()
            # Try to extract the X and Y parts
            inner_match = re.search(
                r'not\s+only\s+(.+?)\s*,?\s*but\s+(?:also\s+)?(.+)',
                full,
                re.IGNORECASE | re.DOTALL
            )
            if inner_match:
                x_part = inner_match.group(1).strip()
                y_part = inner_match.group(2).strip()
                return f"{x_part} and {y_part}"
            return full

        return re.sub(
            r'\bnot\s+only\b[^.!?]*?\bbut\s+(?:also\s+)?[^.!?]*',
            replace_match,
            text,
            flags=re.IGNORECASE
        )

    def get_score(self, text: str) -> dict:
        """Calculate a humanization score for text.

        Args:
            text: Text to score.

        Returns:
            Dict with score (0-100) and breakdown by pattern type.
        """
        patterns = self.detect_patterns(text)

        # Count words for normalization
        word_count = len(text.split())
        if word_count == 0:
            return {"score": 100, "breakdown": {}, "patterns_per_100_words": 0}

        # Count by type
        breakdown = {}
        for pattern in patterns:
            ptype = pattern.pattern_type.value
            breakdown[ptype] = breakdown.get(ptype, 0) + 1

        # Calculate patterns per 100 words
        patterns_per_100 = (len(patterns) / word_count) * 100

        # Score: 100 minus penalty for patterns
        # Rough heuristic: each pattern per 100 words costs ~5 points
        penalty = min(patterns_per_100 * 5, 100)
        score = max(0, 100 - penalty)

        return {
            "score": round(score),
            "breakdown": breakdown,
            "patterns_per_100_words": round(patterns_per_100, 2),
            "total_patterns": len(patterns),
            "word_count": word_count
        }


# Module-level instance for convenience
_humanizer = None


def get_humanizer() -> TextHumanizer:
    """Get or create the singleton humanizer instance."""
    global _humanizer
    if _humanizer is None:
        _humanizer = TextHumanizer()
    return _humanizer


def humanize_text(text: str, detect_only: bool = False) -> HumanizationResult:
    """Convenience function to humanize text.

    Args:
        text: Text to humanize.
        detect_only: If True, only detect patterns.

    Returns:
        HumanizationResult with original, humanized text, and patterns.
    """
    return get_humanizer().humanize(text, detect_only)


def get_humanization_score(text: str) -> dict:
    """Convenience function to get humanization score.

    Args:
        text: Text to score.

    Returns:
        Dict with score and breakdown.
    """
    return get_humanizer().get_score(text)
