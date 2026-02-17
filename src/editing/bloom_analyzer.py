"""Cognitive taxonomy level detection and alignment checking.

Analyzes text to detect cognitive level based on verb patterns and provides
alignment checking against target levels with actionable suggestions.

Supports multiple taxonomies (Bloom's, SOLO, Webb's DOK, Marzano, Fink's)
and custom user-defined taxonomies.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
from src.core.models import BloomLevel, CognitiveTaxonomy, TaxonomyType


@dataclass
class BloomAnalysis:
    """Result of Bloom's level analysis.

    Attributes:
        detected_level: The detected cognitive level
        confidence: Confidence score (0.0 to 1.0)
        evidence: List of verbs/phrases that indicate the level
        verb_counts: Count of verbs detected per Bloom level
    """
    detected_level: BloomLevel
    confidence: float
    evidence: List[str]
    verb_counts: Dict[str, int]


@dataclass
class AlignmentResult:
    """Result of Bloom's level alignment check.

    Attributes:
        aligned: Whether content aligns with target level
        current_level: Detected cognitive level
        target_level: Target cognitive level
        gap: Level difference (negative if below target, positive if above)
        suggestions: List of actionable suggestions for adjustment
    """
    aligned: bool
    current_level: BloomLevel
    target_level: BloomLevel
    gap: int
    suggestions: List[str]


class BloomAnalyzer:
    """Analyze text for Bloom's Taxonomy cognitive level.

    Uses rule-based verb detection to identify cognitive level. Fast, deterministic,
    and doesn't require API calls.

    Bloom's Taxonomy Levels (lowest to highest):
    1. REMEMBER: define, list, recall, identify, name, recognize, state
    2. UNDERSTAND: explain, describe, summarize, interpret, paraphrase, classify
    3. APPLY: use, implement, solve, demonstrate, calculate, execute, apply
    4. ANALYZE: compare, contrast, examine, differentiate, analyze, distinguish
    5. EVALUATE: assess, critique, judge, justify, evaluate, argue, defend
    6. CREATE: design, develop, construct, propose, create, plan, formulate

    Example:
        analyzer = BloomAnalyzer()
        analysis = analyzer.analyze("Compare the advantages of REST vs GraphQL")
        # analysis.detected_level = BloomLevel.ANALYZE
        # analysis.evidence = ["compare"]
    """

    # Bloom's level verb patterns (in order from lowest to highest)
    BLOOM_VERBS = {
        BloomLevel.REMEMBER: [
            "define", "list", "recall", "identify", "name", "recognize",
            "state", "label", "match", "memorize", "repeat", "record",
            "select", "tell", "recite", "retrieve"
        ],
        BloomLevel.UNDERSTAND: [
            "explain", "describe", "summarize", "interpret", "paraphrase",
            "classify", "discuss", "express", "illustrate", "review",
            "translate", "restate", "clarify", "demonstrate understanding"
        ],
        BloomLevel.APPLY: [
            "use", "implement", "solve", "demonstrate", "calculate",
            "execute", "apply", "practice", "operate", "employ",
            "construct", "prepare", "produce", "show", "sketch",
            "perform", "complete"
        ],
        BloomLevel.ANALYZE: [
            "compare", "contrast", "examine", "differentiate", "analyze",
            "distinguish", "investigate", "categorize", "organize",
            "deconstruct", "test", "experiment", "infer", "diagnose",
            "relate", "separate"
        ],
        BloomLevel.EVALUATE: [
            "assess", "critique", "judge", "justify", "evaluate",
            "argue", "defend", "support", "rate", "prioritize",
            "conclude", "decide", "recommend", "appraise", "criticize",
            "validate", "verify"
        ],
        BloomLevel.CREATE: [
            "design", "develop", "construct", "propose", "create",
            "plan", "formulate", "invent", "compose", "build",
            "generate", "hypothesize", "devise", "synthesize",
            "assemble", "arrange"
        ]
    }

    def analyze(self, text: str) -> BloomAnalysis:
        """Analyze text to detect Bloom's cognitive level.

        Args:
            text: Text to analyze (question, prompt, or content)

        Returns:
            BloomAnalysis with detected level, confidence, and evidence
        """
        # Normalize text for verb matching
        normalized_text = text.lower()

        # Count verbs per level
        verb_counts = {}
        evidence = []

        for level, verbs in self.BLOOM_VERBS.items():
            count = 0
            for verb in verbs:
                # Use word boundary matching to avoid partial matches
                pattern = r'\b' + re.escape(verb) + r'\b'
                matches = re.findall(pattern, normalized_text)
                if matches:
                    count += len(matches)
                    evidence.append(verb)

            if count > 0:
                verb_counts[level.value] = count

        # Determine detected level (highest level with verbs found)
        detected_level = BloomLevel.REMEMBER  # Default to lowest
        max_level_order = 0

        level_order = {
            BloomLevel.REMEMBER: 1,
            BloomLevel.UNDERSTAND: 2,
            BloomLevel.APPLY: 3,
            BloomLevel.ANALYZE: 4,
            BloomLevel.EVALUATE: 5,
            BloomLevel.CREATE: 6
        }

        for level, count in verb_counts.items():
            level_enum = BloomLevel(level)
            if level_order[level_enum] > max_level_order:
                max_level_order = level_order[level_enum]
                detected_level = level_enum

        # Calculate confidence based on verb count
        total_verbs = sum(verb_counts.values())
        if total_verbs == 0:
            confidence = 0.3  # Low confidence when no verbs detected
        elif total_verbs == 1:
            confidence = 0.6  # Medium confidence for single verb
        else:
            confidence = min(0.7 + (total_verbs * 0.05), 0.95)

        return BloomAnalysis(
            detected_level=detected_level,
            confidence=confidence,
            evidence=evidence,
            verb_counts=verb_counts
        )

    def check_alignment(
        self,
        text: str,
        target_level: BloomLevel
    ) -> AlignmentResult:
        """Check if text aligns with target Bloom's level.

        Args:
            text: Text to analyze
            target_level: Target Bloom's level

        Returns:
            AlignmentResult with alignment status and suggestions
        """
        # Analyze text
        analysis = self.analyze(text)
        current_level = analysis.detected_level

        # Calculate gap (levels difference)
        level_order = {
            BloomLevel.REMEMBER: 1,
            BloomLevel.UNDERSTAND: 2,
            BloomLevel.APPLY: 3,
            BloomLevel.ANALYZE: 4,
            BloomLevel.EVALUATE: 5,
            BloomLevel.CREATE: 6
        }

        current_order = level_order[current_level]
        target_order = level_order[target_level]
        gap = current_order - target_order

        # Determine if aligned (within 1 level is acceptable)
        aligned = abs(gap) <= 1

        # Generate suggestions
        suggestions = self._generate_suggestions(
            current_level,
            target_level,
            gap,
            analysis.evidence
        )

        return AlignmentResult(
            aligned=aligned,
            current_level=current_level,
            target_level=target_level,
            gap=gap,
            suggestions=suggestions
        )

    def _generate_suggestions(
        self,
        current_level: BloomLevel,
        target_level: BloomLevel,
        gap: int,
        evidence: List[str]
    ) -> List[str]:
        """Generate actionable suggestions for level adjustment.

        Args:
            current_level: Current detected level
            target_level: Target level
            gap: Level difference
            evidence: Verbs found in text

        Returns:
            List of suggestion strings
        """
        suggestions = []

        if gap == 0:
            # Perfect alignment
            suggestions.append(f"Content is well-aligned with {target_level.value} level.")
            return suggestions

        if gap < 0:
            # Current level is below target - need to elevate
            diff = abs(gap)
            suggestions.append(
                f"Content is {diff} level(s) below target. "
                f"Current: {current_level.value}, Target: {target_level.value}"
            )

            # Specific suggestions based on target
            target_verbs = self.BLOOM_VERBS[target_level][:5]  # Show 5 example verbs
            suggestions.append(
                f"Use higher-order verbs like: {', '.join(target_verbs)}"
            )

            # Level-specific advice
            if target_level == BloomLevel.ANALYZE:
                suggestions.append(
                    "Ask students to compare, contrast, or examine relationships between concepts."
                )
            elif target_level == BloomLevel.EVALUATE:
                suggestions.append(
                    "Ask students to critique, assess, or justify their reasoning."
                )
            elif target_level == BloomLevel.CREATE:
                suggestions.append(
                    "Ask students to design, develop, or construct something new."
                )

        else:
            # Current level is above target - might be too complex
            suggestions.append(
                f"Content is {gap} level(s) above target. "
                f"Current: {current_level.value}, Target: {target_level.value}"
            )

            # Suggest simplification
            target_verbs = self.BLOOM_VERBS[target_level][:5]
            suggestions.append(
                f"Simplify by using verbs like: {', '.join(target_verbs)}"
            )

            if target_level == BloomLevel.REMEMBER:
                suggestions.append(
                    "Focus on factual recall: ask students to list, identify, or define."
                )
            elif target_level == BloomLevel.UNDERSTAND:
                suggestions.append(
                    "Focus on comprehension: ask students to explain or summarize."
                )
            elif target_level == BloomLevel.APPLY:
                suggestions.append(
                    "Focus on application: ask students to use or demonstrate concepts."
                )

        return suggestions


@dataclass
class TaxonomyAnalysis:
    """Result of taxonomy-aware cognitive level analysis.

    Attributes:
        detected_level: The detected cognitive level value
        detected_level_name: Display name of the detected level
        confidence: Confidence score (0.0 to 1.0)
        evidence: List of verbs/phrases that indicate the level
        verb_counts: Count of verbs detected per level
        taxonomy_name: Name of the taxonomy used
    """
    detected_level: str
    detected_level_name: str
    confidence: float
    evidence: List[str]
    verb_counts: Dict[str, int]
    taxonomy_name: str


@dataclass
class TaxonomyAlignmentResult:
    """Result of taxonomy-aware alignment check.

    Attributes:
        aligned: Whether content aligns with target level
        current_level: Detected cognitive level value
        current_level_name: Display name of detected level
        target_level: Target cognitive level value
        target_level_name: Display name of target level
        gap: Level difference (negative if below target, positive if above)
        suggestions: List of actionable suggestions for adjustment
        taxonomy_name: Name of the taxonomy used
    """
    aligned: bool
    current_level: str
    current_level_name: str
    target_level: str
    target_level_name: str
    gap: int
    suggestions: List[str]
    taxonomy_name: str


class TaxonomyAnalyzer:
    """Analyze text for cognitive level using any taxonomy.

    Uses rule-based verb detection to identify cognitive level. Fast, deterministic,
    and doesn't require API calls. Works with any CognitiveTaxonomy.

    Example:
        from src.core.taxonomy_store import TaxonomyStore
        store = TaxonomyStore()
        webb = store.load("tax_webb")

        analyzer = TaxonomyAnalyzer(webb)
        analysis = analyzer.analyze("Analyze the security implications of...")
        # analysis.detected_level = "strategic"
        # analysis.taxonomy_name = "Webb's Depth of Knowledge"
    """

    def __init__(self, taxonomy: CognitiveTaxonomy):
        """Initialize analyzer with a taxonomy.

        Args:
            taxonomy: CognitiveTaxonomy to use for analysis
        """
        self.taxonomy = taxonomy
        self._build_verb_patterns()

    def _build_verb_patterns(self):
        """Build verb pattern dictionary from taxonomy levels."""
        self.verb_patterns: Dict[str, List[str]] = {}
        for level in self.taxonomy.levels:
            self.verb_patterns[level.value] = level.example_verbs

    def analyze(self, text: str) -> TaxonomyAnalysis:
        """Analyze text to detect cognitive level.

        For LINEAR taxonomies: returns the highest-order level with matching verbs.
        For CATEGORICAL taxonomies: returns the level with the most verb matches.

        Args:
            text: Text to analyze (question, prompt, or content)

        Returns:
            TaxonomyAnalysis with detected level, confidence, and evidence
        """
        normalized_text = text.lower()

        # Count verbs per level
        verb_counts: Dict[str, int] = {}
        evidence: List[str] = []

        for level_value, verbs in self.verb_patterns.items():
            count = 0
            for verb in verbs:
                # Use word boundary matching to avoid partial matches
                pattern = r'\b' + re.escape(verb.lower()) + r'\b'
                matches = re.findall(pattern, normalized_text)
                if matches:
                    count += len(matches)
                    evidence.append(verb)

            if count > 0:
                verb_counts[level_value] = count

        # Determine detected level based on taxonomy type
        if self.taxonomy.taxonomy_type == TaxonomyType.LINEAR:
            detected_level = self._detect_linear(verb_counts)
        else:
            detected_level = self._detect_categorical(verb_counts)

        # Get level name
        detected_level_name = detected_level
        level_obj = self.taxonomy.get_level(detected_level)
        if level_obj:
            detected_level_name = level_obj.name

        # Calculate confidence
        total_verbs = sum(verb_counts.values())
        if total_verbs == 0:
            confidence = 0.3
        elif total_verbs == 1:
            confidence = 0.6
        else:
            confidence = min(0.7 + (total_verbs * 0.05), 0.95)

        return TaxonomyAnalysis(
            detected_level=detected_level,
            detected_level_name=detected_level_name,
            confidence=confidence,
            evidence=evidence,
            verb_counts=verb_counts,
            taxonomy_name=self.taxonomy.name
        )

    def _detect_linear(self, verb_counts: Dict[str, int]) -> str:
        """Detect level for linear taxonomies (return highest order with verbs).

        Args:
            verb_counts: Dictionary of level_value -> count

        Returns:
            Detected level value
        """
        # Get ordered levels
        ordered_levels = self.taxonomy.get_ordered_levels()

        # Find highest level with verbs
        detected_level = ordered_levels[0].value if ordered_levels else ""
        max_order = 0

        for level_value, count in verb_counts.items():
            order = self.taxonomy.get_level_order(level_value)
            if order > max_order:
                max_order = order
                detected_level = level_value

        return detected_level

    def _detect_categorical(self, verb_counts: Dict[str, int]) -> str:
        """Detect level for categorical taxonomies (return most matched category).

        Args:
            verb_counts: Dictionary of level_value -> count

        Returns:
            Detected level value
        """
        if not verb_counts:
            # Return first level as default
            levels = self.taxonomy.levels
            return levels[0].value if levels else ""

        # Return level with most verbs
        return max(verb_counts, key=verb_counts.get)

    def check_alignment(
        self,
        text: str,
        target_level: str
    ) -> TaxonomyAlignmentResult:
        """Check if text aligns with target cognitive level.

        Args:
            text: Text to analyze
            target_level: Target cognitive level value

        Returns:
            TaxonomyAlignmentResult with alignment status and suggestions
        """
        analysis = self.analyze(text)
        current_level = analysis.detected_level

        # Get level orders
        current_order = self.taxonomy.get_level_order(current_level)
        target_order = self.taxonomy.get_level_order(target_level)

        # Calculate gap
        if current_order == -1 or target_order == -1:
            gap = 0
        else:
            gap = current_order - target_order

        # For categorical taxonomies, alignment means matching the category
        if self.taxonomy.taxonomy_type == TaxonomyType.CATEGORICAL:
            aligned = current_level == target_level
            gap = 0 if aligned else 1  # Simplified gap for categorical
        else:
            # For linear, within 1 level is acceptable
            aligned = abs(gap) <= 1

        # Get level names
        current_level_obj = self.taxonomy.get_level(current_level)
        target_level_obj = self.taxonomy.get_level(target_level)

        current_name = current_level_obj.name if current_level_obj else current_level
        target_name = target_level_obj.name if target_level_obj else target_level

        # Generate suggestions
        suggestions = self._generate_suggestions(
            current_level,
            target_level,
            gap,
            analysis.evidence
        )

        return TaxonomyAlignmentResult(
            aligned=aligned,
            current_level=current_level,
            current_level_name=current_name,
            target_level=target_level,
            target_level_name=target_name,
            gap=gap,
            suggestions=suggestions,
            taxonomy_name=self.taxonomy.name
        )

    def _generate_suggestions(
        self,
        current_level: str,
        target_level: str,
        gap: int,
        evidence: List[str]
    ) -> List[str]:
        """Generate actionable suggestions for level adjustment.

        Args:
            current_level: Current detected level value
            target_level: Target level value
            gap: Level difference
            evidence: Verbs found in text

        Returns:
            List of suggestion strings
        """
        suggestions = []

        current_obj = self.taxonomy.get_level(current_level)
        target_obj = self.taxonomy.get_level(target_level)

        current_name = current_obj.name if current_obj else current_level
        target_name = target_obj.name if target_obj else target_level

        if gap == 0 or (self.taxonomy.taxonomy_type == TaxonomyType.CATEGORICAL and current_level == target_level):
            suggestions.append(
                f"Content is well-aligned with {target_name} level "
                f"({self.taxonomy.name})."
            )
            return suggestions

        if gap < 0 or (self.taxonomy.taxonomy_type == TaxonomyType.CATEGORICAL and current_level != target_level):
            # Below target or different category
            suggestions.append(
                f"Content may not match target level. "
                f"Current: {current_name}, Target: {target_name}"
            )

            # Suggest target level verbs
            if target_obj and target_obj.example_verbs:
                target_verbs = target_obj.example_verbs[:5]
                suggestions.append(
                    f"Use verbs associated with {target_name}: {', '.join(target_verbs)}"
                )

            # Add level description as guidance
            if target_obj and target_obj.description:
                suggestions.append(f"Goal: {target_obj.description}")

        else:
            # Above target for linear taxonomies
            suggestions.append(
                f"Content is {gap} level(s) above target. "
                f"Current: {current_name}, Target: {target_name}"
            )

            # Suggest simplification with target verbs
            if target_obj and target_obj.example_verbs:
                target_verbs = target_obj.example_verbs[:5]
                suggestions.append(
                    f"Simplify by using verbs like: {', '.join(target_verbs)}"
                )

        return suggestions
