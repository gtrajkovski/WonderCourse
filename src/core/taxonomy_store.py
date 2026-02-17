"""Cognitive taxonomy storage with system presets.

Provides storage and CRUD operations for cognitive taxonomies.
Includes 5 predefined system taxonomies:
- Bloom's (Revised) - 6 levels, linear progression
- SOLO - 5 levels, linear progression
- Webb's DOK - 4 levels, linear progression
- Marzano - 6 levels, linear progression
- Fink's Significant Learning - 6 categories, categorical (non-linear)
"""

from pathlib import Path
import json
from typing import List, Optional

from src.core.models import (
    CognitiveTaxonomy,
    TaxonomyLevel,
    ActivityLevelMapping,
    TaxonomyType,
    ActivityType,
)


class TaxonomyStore:
    """Storage for cognitive taxonomies with system presets."""

    def __init__(self, taxonomies_dir: Path = Path("taxonomies")):
        """Initialize the taxonomy store.

        Args:
            taxonomies_dir: Path to store taxonomy JSON files.
        """
        self.taxonomies_dir = taxonomies_dir
        self.taxonomies_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_system_presets()

    def _ensure_system_presets(self):
        """Create system preset taxonomies if they don't exist."""
        presets = [
            self._blooms_taxonomy(),
            self._solo_taxonomy(),
            self._webbs_dok_taxonomy(),
            self._marzano_taxonomy(),
            self._finks_taxonomy(),
        ]

        for preset in presets:
            path = self.taxonomies_dir / f"{preset.id}.json"
            if not path.exists():
                self.save(preset)

    def _blooms_taxonomy(self) -> CognitiveTaxonomy:
        """Create Bloom's Revised Taxonomy (2001)."""
        levels = [
            TaxonomyLevel(
                id="bloom_remember",
                name="Remember",
                value="remember",
                description="Retrieve relevant knowledge from long-term memory",
                order=1,
                example_verbs=["define", "list", "recall", "identify", "name", "recognize", "state", "match"],
                color="#E57373"
            ),
            TaxonomyLevel(
                id="bloom_understand",
                name="Understand",
                value="understand",
                description="Construct meaning from instructional messages",
                order=2,
                example_verbs=["explain", "describe", "summarize", "interpret", "classify", "compare", "discuss", "paraphrase"],
                color="#FFB74D"
            ),
            TaxonomyLevel(
                id="bloom_apply",
                name="Apply",
                value="apply",
                description="Carry out or use a procedure in a given situation",
                order=3,
                example_verbs=["use", "implement", "execute", "solve", "demonstrate", "apply", "perform", "calculate"],
                color="#FFF176"
            ),
            TaxonomyLevel(
                id="bloom_analyze",
                name="Analyze",
                value="analyze",
                description="Break material into parts and determine relationships",
                order=4,
                example_verbs=["analyze", "differentiate", "organize", "examine", "compare", "contrast", "investigate", "deconstruct"],
                color="#81C784"
            ),
            TaxonomyLevel(
                id="bloom_evaluate",
                name="Evaluate",
                value="evaluate",
                description="Make judgments based on criteria and standards",
                order=5,
                example_verbs=["evaluate", "judge", "critique", "assess", "justify", "defend", "argue", "recommend"],
                color="#64B5F6"
            ),
            TaxonomyLevel(
                id="bloom_create",
                name="Create",
                value="create",
                description="Put elements together to form a coherent whole or new product",
                order=6,
                example_verbs=["create", "design", "construct", "develop", "compose", "produce", "formulate", "invent"],
                color="#BA68C8"
            ),
        ]

        activity_mappings = [
            ActivityLevelMapping(
                activity_type=ActivityType.VIDEO_LECTURE,
                compatible_levels=["remember", "understand", "apply"],
                primary_levels=["understand"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.READING_MATERIAL,
                compatible_levels=["remember", "understand", "apply", "analyze"],
                primary_levels=["understand", "remember"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.HANDS_ON_LAB,
                compatible_levels=["apply", "analyze", "evaluate", "create"],
                primary_levels=["apply", "analyze"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.GRADED_QUIZ,
                compatible_levels=["remember", "understand", "apply", "analyze"],
                primary_levels=["remember", "understand"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PRACTICE_QUIZ,
                compatible_levels=["remember", "understand", "apply"],
                primary_levels=["remember", "understand"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.ASSIGNMENT_SUBMISSION,
                compatible_levels=["apply", "analyze", "evaluate", "create"],
                primary_levels=["apply", "analyze"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PROJECT_MILESTONE,
                compatible_levels=["analyze", "evaluate", "create"],
                primary_levels=["create", "evaluate"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.DISCUSSION_PROMPT,
                compatible_levels=["understand", "apply", "analyze", "evaluate"],
                primary_levels=["analyze", "evaluate"]
            ),
        ]

        return CognitiveTaxonomy(
            id="tax_blooms",
            name="Bloom's Revised Taxonomy",
            description="Six-level cognitive hierarchy from knowledge recall to creative synthesis. The most widely used framework for educational objectives.",
            taxonomy_type=TaxonomyType.LINEAR,
            is_system_preset=True,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=True,
            allow_regression_within=1,
            minimum_unique_levels=2,
            require_higher_order=True,
            higher_order_threshold=4  # Analyze and above
        )

    def _solo_taxonomy(self) -> CognitiveTaxonomy:
        """Create SOLO Taxonomy (Structure of Observed Learning Outcomes)."""
        levels = [
            TaxonomyLevel(
                id="solo_prestructural",
                name="Prestructural",
                value="prestructural",
                description="No understanding demonstrated; may miss the point entirely",
                order=1,
                example_verbs=["misses point", "incompetent", "irrelevant"],
                color="#BDBDBD"
            ),
            TaxonomyLevel(
                id="solo_unistructural",
                name="Unistructural",
                value="unistructural",
                description="Simple, concrete understanding with one relevant aspect",
                order=2,
                example_verbs=["identify", "name", "follow", "memorize", "define", "count"],
                color="#E57373"
            ),
            TaxonomyLevel(
                id="solo_multistructural",
                name="Multistructural",
                value="multistructural",
                description="Several relevant aspects identified but not integrated",
                order=3,
                example_verbs=["describe", "list", "combine", "enumerate", "classify", "outline"],
                color="#FFB74D"
            ),
            TaxonomyLevel(
                id="solo_relational",
                name="Relational",
                value="relational",
                description="Aspects are integrated into a coherent whole",
                order=4,
                example_verbs=["analyze", "compare", "contrast", "explain causes", "relate", "apply", "integrate"],
                color="#81C784"
            ),
            TaxonomyLevel(
                id="solo_extended_abstract",
                name="Extended Abstract",
                value="extended_abstract",
                description="Understanding extends to abstract principles and new applications",
                order=5,
                example_verbs=["theorize", "generalize", "hypothesize", "reflect", "generate", "create", "predict"],
                color="#BA68C8"
            ),
        ]

        activity_mappings = [
            ActivityLevelMapping(
                activity_type=ActivityType.VIDEO_LECTURE,
                compatible_levels=["unistructural", "multistructural", "relational"],
                primary_levels=["multistructural"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.HANDS_ON_LAB,
                compatible_levels=["multistructural", "relational", "extended_abstract"],
                primary_levels=["relational"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PROJECT_MILESTONE,
                compatible_levels=["relational", "extended_abstract"],
                primary_levels=["extended_abstract"]
            ),
        ]

        return CognitiveTaxonomy(
            id="tax_solo",
            name="SOLO Taxonomy",
            description="Structure of Observed Learning Outcomes. Focuses on observable complexity of student responses rather than intended objectives.",
            taxonomy_type=TaxonomyType.LINEAR,
            is_system_preset=True,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=True,
            allow_regression_within=1,
            minimum_unique_levels=2,
            require_higher_order=True,
            higher_order_threshold=4  # Relational and above
        )

    def _webbs_dok_taxonomy(self) -> CognitiveTaxonomy:
        """Create Webb's Depth of Knowledge taxonomy."""
        levels = [
            TaxonomyLevel(
                id="webb_recall",
                name="Recall & Reproduction",
                value="recall",
                description="Recall facts, definitions, terms, or simple procedures",
                order=1,
                example_verbs=["recall", "recognize", "identify", "define", "list", "name", "state", "locate"],
                color="#E57373"
            ),
            TaxonomyLevel(
                id="webb_skills",
                name="Skills & Concepts",
                value="skills_concepts",
                description="Apply skills and concepts, compare, classify, organize",
                order=2,
                example_verbs=["summarize", "interpret", "classify", "compare", "organize", "predict", "estimate", "infer"],
                color="#FFB74D"
            ),
            TaxonomyLevel(
                id="webb_strategic",
                name="Strategic Thinking",
                value="strategic",
                description="Reasoning, planning, using evidence, complex and abstract thinking",
                order=3,
                example_verbs=["analyze", "investigate", "formulate", "construct", "assess", "revise", "critique", "hypothesize"],
                color="#81C784"
            ),
            TaxonomyLevel(
                id="webb_extended",
                name="Extended Thinking",
                value="extended",
                description="Extended investigation, real-world application, novel solutions",
                order=4,
                example_verbs=["design", "create", "synthesize", "apply concepts in new contexts", "connect ideas", "critique", "prove"],
                color="#BA68C8"
            ),
        ]

        activity_mappings = [
            ActivityLevelMapping(
                activity_type=ActivityType.GRADED_QUIZ,
                compatible_levels=["recall", "skills_concepts"],
                primary_levels=["recall"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.VIDEO_LECTURE,
                compatible_levels=["recall", "skills_concepts"],
                primary_levels=["skills_concepts"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.HANDS_ON_LAB,
                compatible_levels=["skills_concepts", "strategic", "extended"],
                primary_levels=["strategic"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PROJECT_MILESTONE,
                compatible_levels=["strategic", "extended"],
                primary_levels=["extended"]
            ),
        ]

        return CognitiveTaxonomy(
            id="tax_webb",
            name="Webb's Depth of Knowledge",
            description="Four-level framework measuring cognitive complexity required for tasks. Focuses on what students do, not content difficulty.",
            taxonomy_type=TaxonomyType.LINEAR,
            is_system_preset=True,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=True,
            allow_regression_within=1,
            minimum_unique_levels=2,
            require_higher_order=True,
            higher_order_threshold=3  # Strategic and above
        )

    def _marzano_taxonomy(self) -> CognitiveTaxonomy:
        """Create Marzano's New Taxonomy."""
        levels = [
            TaxonomyLevel(
                id="marzano_retrieval",
                name="Retrieval",
                value="retrieval",
                description="Recognize, recall, and execute basic information and procedures",
                order=1,
                example_verbs=["recognize", "recall", "execute", "identify", "determine", "select"],
                color="#E57373"
            ),
            TaxonomyLevel(
                id="marzano_comprehension",
                name="Comprehension",
                value="comprehension",
                description="Integrate and symbolize knowledge into categories and relationships",
                order=2,
                example_verbs=["integrate", "symbolize", "describe", "explain", "predict", "represent"],
                color="#FFB74D"
            ),
            TaxonomyLevel(
                id="marzano_analysis",
                name="Analysis",
                value="analysis",
                description="Match, classify, analyze errors, generalize, and specify",
                order=3,
                example_verbs=["match", "classify", "analyze", "generalize", "specify", "differentiate", "categorize"],
                color="#FFF176"
            ),
            TaxonomyLevel(
                id="marzano_knowledge_utilization",
                name="Knowledge Utilization",
                value="knowledge_utilization",
                description="Apply knowledge in decision-making, problem-solving, investigation",
                order=4,
                example_verbs=["decide", "solve", "investigate", "experiment", "test", "prove", "adapt"],
                color="#81C784"
            ),
            TaxonomyLevel(
                id="marzano_metacognition",
                name="Metacognition",
                value="metacognition",
                description="Monitor, evaluate, and regulate one's own cognitive processes",
                order=5,
                example_verbs=["monitor", "evaluate", "regulate", "plan", "reflect", "assess progress"],
                color="#64B5F6"
            ),
            TaxonomyLevel(
                id="marzano_self_system",
                name="Self-System Thinking",
                value="self_system",
                description="Examine importance, self-efficacy, emotional response, and motivation",
                order=6,
                example_verbs=["examine importance", "assess efficacy", "identify emotional response", "examine motivation"],
                color="#BA68C8"
            ),
        ]

        activity_mappings = [
            ActivityLevelMapping(
                activity_type=ActivityType.VIDEO_LECTURE,
                compatible_levels=["retrieval", "comprehension", "analysis"],
                primary_levels=["comprehension"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.HANDS_ON_LAB,
                compatible_levels=["analysis", "knowledge_utilization"],
                primary_levels=["knowledge_utilization"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PROJECT_MILESTONE,
                compatible_levels=["knowledge_utilization", "metacognition", "self_system"],
                primary_levels=["knowledge_utilization"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.DISCUSSION_PROMPT,
                compatible_levels=["comprehension", "analysis", "metacognition", "self_system"],
                primary_levels=["metacognition"]
            ),
        ]

        return CognitiveTaxonomy(
            id="tax_marzano",
            name="Marzano's New Taxonomy",
            description="Six-level taxonomy spanning three knowledge domains. Includes metacognitive and self-system levels unique to this framework.",
            taxonomy_type=TaxonomyType.LINEAR,
            is_system_preset=True,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=True,
            allow_regression_within=1,
            minimum_unique_levels=2,
            require_higher_order=True,
            higher_order_threshold=4  # Knowledge Utilization and above
        )

    def _finks_taxonomy(self) -> CognitiveTaxonomy:
        """Create Fink's Significant Learning Taxonomy."""
        levels = [
            TaxonomyLevel(
                id="fink_foundational",
                name="Foundational Knowledge",
                value="foundational",
                description="Understanding and remembering information and ideas",
                order=1,
                example_verbs=["understand", "remember", "identify", "describe", "explain"],
                color="#E57373"
            ),
            TaxonomyLevel(
                id="fink_application",
                name="Application",
                value="application",
                description="Skills, critical/creative/practical thinking, managing projects",
                order=2,
                example_verbs=["apply", "use", "perform", "manage", "create", "think critically"],
                color="#FFB74D"
            ),
            TaxonomyLevel(
                id="fink_integration",
                name="Integration",
                value="integration",
                description="Connecting ideas, people, and realms of life",
                order=3,
                example_verbs=["connect", "relate", "integrate", "compare", "link", "synthesize"],
                color="#81C784"
            ),
            TaxonomyLevel(
                id="fink_human_dimension",
                name="Human Dimension",
                value="human_dimension",
                description="Learning about oneself and others",
                order=4,
                example_verbs=["discover about self", "understand others", "interact", "collaborate", "lead"],
                color="#64B5F6"
            ),
            TaxonomyLevel(
                id="fink_caring",
                name="Caring",
                value="caring",
                description="Developing new feelings, interests, and values",
                order=5,
                example_verbs=["value", "commit", "care about", "develop interest in", "become motivated"],
                color="#F48FB1"
            ),
            TaxonomyLevel(
                id="fink_learning_how",
                name="Learning How to Learn",
                value="learning_how",
                description="Becoming a better student and self-directed learner",
                order=6,
                example_verbs=["learn", "inquire", "self-direct", "reflect on learning", "identify resources"],
                color="#BA68C8"
            ),
        ]

        activity_mappings = [
            ActivityLevelMapping(
                activity_type=ActivityType.VIDEO_LECTURE,
                compatible_levels=["foundational", "application", "integration", "human_dimension", "caring", "learning_how"],
                primary_levels=["foundational", "application"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.DISCUSSION_PROMPT,
                compatible_levels=["integration", "human_dimension", "caring"],
                primary_levels=["human_dimension", "integration"]
            ),
            ActivityLevelMapping(
                activity_type=ActivityType.PROJECT_MILESTONE,
                compatible_levels=["application", "integration", "human_dimension", "caring", "learning_how"],
                primary_levels=["application", "integration"]
            ),
        ]

        return CognitiveTaxonomy(
            id="tax_finks",
            name="Fink's Significant Learning",
            description="Six non-hierarchical categories of learning. Unlike other taxonomies, these categories are interactive and can occur simultaneously.",
            taxonomy_type=TaxonomyType.CATEGORICAL,  # Non-linear/non-hierarchical
            is_system_preset=True,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=False,  # No linear progression required
            allow_regression_within=0,
            minimum_unique_levels=2,
            require_higher_order=False,  # All categories are equally valuable
            higher_order_threshold=0
        )

    # CRUD Operations

    def load(self, taxonomy_id: str) -> Optional[CognitiveTaxonomy]:
        """Load a taxonomy by ID.

        Args:
            taxonomy_id: The taxonomy identifier.

        Returns:
            CognitiveTaxonomy if found, None otherwise.
        """
        path = self.taxonomies_dir / f"{taxonomy_id}.json"
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return CognitiveTaxonomy.from_dict(data)
        except Exception:
            return None

    def save(self, taxonomy: CognitiveTaxonomy):
        """Save a taxonomy to disk.

        Args:
            taxonomy: The taxonomy to save.
        """
        path = self.taxonomies_dir / f"{taxonomy.id}.json"
        path.write_text(json.dumps(taxonomy.to_dict(), indent=2))

    def delete(self, taxonomy_id: str) -> bool:
        """Delete a taxonomy.

        System presets cannot be deleted.

        Args:
            taxonomy_id: The taxonomy identifier.

        Returns:
            True if deleted, False if not found or is system preset.
        """
        taxonomy = self.load(taxonomy_id)
        if taxonomy is None:
            return False
        if taxonomy.is_system_preset:
            return False

        path = self.taxonomies_dir / f"{taxonomy_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> List[CognitiveTaxonomy]:
        """List all taxonomies.

        Returns:
            List of all taxonomies, system presets first.
        """
        taxonomies = []
        for path in self.taxonomies_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                taxonomies.append(CognitiveTaxonomy.from_dict(data))
            except Exception:
                continue

        # Sort: system presets first, then by name
        return sorted(
            taxonomies,
            key=lambda t: (0 if t.is_system_preset else 1, t.name)
        )

    def duplicate(self, taxonomy_id: str, new_name: str) -> Optional[CognitiveTaxonomy]:
        """Create a copy of a taxonomy with a new name.

        Args:
            taxonomy_id: The ID of the taxonomy to copy.
            new_name: The name for the new taxonomy.

        Returns:
            The new taxonomy if successful, None otherwise.
        """
        source = self.load(taxonomy_id)
        if source is None:
            return None

        # Create new taxonomy with fresh ID
        import uuid
        from datetime import datetime

        new_taxonomy = CognitiveTaxonomy(
            id=f"tax_{uuid.uuid4().hex[:8]}",
            name=new_name,
            description=source.description,
            taxonomy_type=source.taxonomy_type,
            is_system_preset=False,  # Duplicates are never system presets
            levels=[
                TaxonomyLevel(
                    id=f"tl_{uuid.uuid4().hex[:8]}",
                    name=level.name,
                    value=level.value,
                    description=level.description,
                    order=level.order,
                    example_verbs=level.example_verbs.copy(),
                    color=level.color
                )
                for level in source.levels
            ],
            activity_mappings=[
                ActivityLevelMapping(
                    activity_type=m.activity_type,
                    compatible_levels=m.compatible_levels.copy(),
                    primary_levels=m.primary_levels.copy()
                )
                for m in source.activity_mappings
            ],
            require_progression=source.require_progression,
            allow_regression_within=source.allow_regression_within,
            minimum_unique_levels=source.minimum_unique_levels,
            require_higher_order=source.require_higher_order,
            higher_order_threshold=source.higher_order_threshold,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self.save(new_taxonomy)
        return new_taxonomy

    def get_default(self) -> CognitiveTaxonomy:
        """Get the default taxonomy (Bloom's).

        Returns:
            Bloom's taxonomy.
        """
        taxonomy = self.load("tax_blooms")
        if taxonomy is None:
            # Re-create if missing
            taxonomy = self._blooms_taxonomy()
            self.save(taxonomy)
        return taxonomy

    def get_for_course(self, course) -> CognitiveTaxonomy:
        """Get the taxonomy assigned to a course.

        Falls back to Bloom's if course has no taxonomy assigned.

        Args:
            course: Course instance.

        Returns:
            The course's taxonomy or Bloom's as default.
        """
        if course.taxonomy_id:
            taxonomy = self.load(course.taxonomy_id)
            if taxonomy:
                return taxonomy
        return self.get_default()
