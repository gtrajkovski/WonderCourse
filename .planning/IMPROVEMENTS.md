# Improvements Backlog

Tracked issues and enhancements to address.

## High Priority

### Blueprint Auto-Fix ✅ IMPLEMENTED (v1.3.1)
**Status:** Complete - `src/validators/blueprint_autofix.py`

Implemented BlueprintAutoFixer with:
- Duration scaling to meet target (with min/max bounds per content type)
- Auto-assign WWHAA phases to activities missing them
- Activity balance suggestions
- Refinement feedback generator for AI regeneration

---

## Medium Priority

### Configurable Course Duration
**Issue:** Course duration defaults to 60 minutes and isn't prominently configurable before blueprint generation.

**Current behavior:** Target duration is set in course settings but not clearly surfaced when generating blueprints.

**Desired behavior:**
- Prominent duration selector on Blueprint tab (e.g., 30/60/90/120/180 min presets + custom)
- Duration passed to AI and strictly respected in generated structure
- Visual indicator showing how generated blueprint compares to target

---

### Custom Course Type Presets
**Issue:** Only hardcoded presets exist (Coursera, Flexible, Corporate). Users can't create their own.

**Current behavior:** Three system presets with fixed values for all settings.

**Desired behavior:**
- "Create Custom Preset" option in standards selector
- Save custom presets with user-defined values for:
  - Module/lesson/activity count ranges
  - Duration constraints
  - Content type distribution targets
  - Bloom's level requirements
- Import/export presets as JSON
- Share presets across courses

---

### Course-Level Audience (Not Per-Objective) ✅ IMPLEMENTED (v1.3.1)
**Status:** Complete - via Learner Profiles

Implemented via learner_profile_id on Course model:
- Course links to a LearnerProfile with detailed audience characteristics
- Profile provides prompt context for all content generation
- Learning objectives inherit course's learner profile

---

### Learner Profiles ✅ IMPLEMENTED (v1.3.1)
**Status:** Complete - `src/api/learner_profiles.py`, `src/core/models.py`

Implemented LearnerProfile model with:
- 20+ fields: prior knowledge, technical level, language proficiency, learning preferences, context, accessibility
- Enums: TechnicalLevel, LanguageProficiency, LearningPreference, LearningContext
- CRUD API at /api/learner-profiles
- 4 default profiles included
- Course assignment via learner_profile_id field
- Prompt context generation for AI content tailoring

---

### Learning Objective Bloom Validation ✅ IMPLEMENTED (v1.3.1)
**Status:** Complete - `src/editing/bloom_analyzer.py`

Implemented BloomAnalyzer with:
- Verb-based cognitive level detection
- Alignment checking with confidence scores
- Actionable suggestions for level adjustment
- TaxonomyAnalyzer for custom taxonomies (SOLO, Webb, Marzano, Fink)
- Integration with CourseAuditor for progression checks

---

### Custom Taxonomies (Beyond Bloom)
**Issue:** Only Bloom's taxonomy is supported. Some organizations use different frameworks.

**Desired behavior:**
- Support multiple taxonomy frameworks:
  - Bloom's (default)
  - SOLO Taxonomy
  - Marzano's Taxonomy
  - Webb's Depth of Knowledge
  - Custom user-defined taxonomies
- Define custom levels with names and descriptions
- Map activities to custom taxonomy levels
- Validation and progression analysis for any taxonomy

---

## Low Priority

(none yet)

---

# Coursera Master Reference v3.0 Compliance

*Analysis based on Coursera_Master_Reference_v3.md.pdf (February 2026)*

## Executive Summary

Analysis of the Coursera Master Reference v3.0 against Course Builder Studio reveals **13 improvement opportunities** across validation, AI detection, and content generation. Priority items focus on new v3.0 requirements.

---

## HIGH PRIORITY

### 1. CTA Validation (No Next-Activity Previews) [NEW v3.0]

**Reference:** Section 2.3

**Current:** CTA section generated but no content validation.

**Requirements:**
- NO next-activity previews ("Next, you'll work through a reading...")
- NO naming specific upcoming items (Coach dialogue, reading, HOL, quiz)
- NO recap-style summaries disguised as CTAs
- Keep under 35 words (~15 seconds)

**Implementation:**
```python
FORBIDDEN_CTA_PATTERNS = [
    r'\bnext\b.*?\byou\'ll\b',
    r'\bupcoming\b',
    r'\bin the next\b',
    r'\bcoach dialogue\b',
    r'\bgraded assessment\b',
    r'\bfinal quiz\b',
]
```

**Files:** `src/validators/standards_validator.py`, new `src/validators/cta_validator.py`

---

### 2. Quiz Answer Distribution Validation

**Reference:** Section 6.3-6.4

**Current:** Validates feedback presence but no distribution check.

**Requirements:**
- No letter >35% of correct answers
- No letter <15% of correct answers
- No predictable patterns (A,B,C,D,A,B,C,D)
- Options within 10-15 characters of each other
- Correct answer NOT longest/shortest option

**Files:** `src/validators/standards_validator.py`

---

### 3. Expanded AI Detection (5 New Patterns) [NEW v3.0]

**Reference:** Section 14.3

**Current patterns (5):** Em-dashes, formal vocabulary, AI transitions, filler phrases, three-adjective lists

**Missing patterns:**
| # | Pattern | Detection Method |
|---|---------|-----------------|
| 4 | Consecutive sentence openers | First-word comparison |
| 6 | "This ensures/enables/allows" openers | Regex at sentence start |
| 7 | "Not only...but also" | Co-occurrence check |
| 9 | 4+ item comma lists | Regex: 4-word comma chain |
| 10 | Adverb/frequency triplets | Co-occurrence check |

**Implementation:**
```python
# Pattern 6
THIS_ENSURES_PATTERN = re.compile(
    r'(?:^|\.\s+)This\s+(ensures|enables|allows|provides|creates|offers)\b',
    re.IGNORECASE
)

# Pattern 7
NOT_ONLY_PATTERN = re.compile(r'not only\b.*?\bbut also\b', re.IGNORECASE | re.DOTALL)

# Pattern 9
FOUR_ITEM_LIST_PATTERN = re.compile(r'(\w+),\s+(\w+),\s+(\w+),\s+and\s+(\w+)')
```

**Files:** `src/utils/text_humanizer.py`

---

### 4. Sequential Reference Detection

**Reference:** Section 1.5

**Current:** Limited detection in course auditor.

**Forbidden patterns:**
- "As we discussed in Module 1..."
- "In the previous video..."
- "Remember from last lesson..."

**Implementation:**
```python
SEQUENTIAL_REFERENCE_PATTERNS = [
    r'\b(as we|we\'ve)\s+(discussed|learned|covered)\s+(in|during)\s+(module|lesson|video)\s+\d',
    r'\b(previous|last|earlier)\s+(module|lesson|video|reading)',
    r'\bremember\s+(from|when)\s+(module|lesson)',
]
```

**Files:** `src/validators/course_auditor.py`

---

### 5. Configurable HOL Rubric System

**Reference:** Section 4.6

**Current:** Rubric generated with fixed structure, limited editability.

**Requirements:**
- **Configurable criteria count** (default 3, but allow 2-5)
- **Configurable levels per criterion** (default 3: Advanced/Intermediate/Beginner)
- **Configurable points per level** (default 5/4/2, but editable)
- **Editable like any generated text** - users can modify criteria names, descriptions, points
- Validation against standards profile (Coursera default: 3 criteria, 15 total points)

**Implementation:**

1. **Standards Profile fields:**
```python
# In ContentStandardsProfile
hol_rubric_min_criteria: int = 2
hol_rubric_max_criteria: int = 5
hol_rubric_default_criteria: int = 3
hol_rubric_levels: List[str] = ["Advanced", "Intermediate", "Beginner"]
hol_rubric_default_points: List[int] = [5, 4, 2]  # Per level
hol_rubric_total_points: Optional[int] = 15  # None = no enforcement
```

2. **Rubric Schema (editable):**
```python
class RubricLevel(BaseModel):
    name: str  # "Advanced", "Intermediate", "Beginner" or custom
    points: int
    description: str

class RubricCriterion(BaseModel):
    name: str  # e.g., "Technical Execution", "Analysis Quality"
    levels: List[RubricLevel]

class HOLRubric(BaseModel):
    criteria: List[RubricCriterion]

    def total_max_points(self) -> int:
        return sum(max(level.points for level in c.levels) for c in self.criteria)
```

3. **Validation (configurable):**
```python
def validate_hol_rubric(rubric: HOLRubric, standards: ContentStandardsProfile):
    issues = []

    # Criteria count check (against profile, not hardcoded)
    if not (standards.hol_rubric_min_criteria <= len(rubric.criteria) <= standards.hol_rubric_max_criteria):
        issues.append(...)

    # Total points check (only if profile specifies)
    if standards.hol_rubric_total_points:
        actual = rubric.total_max_points()
        if actual != standards.hol_rubric_total_points:
            issues.append(ValidationIssue(
                severity="WARNING",  # Not ERROR - allow override
                rule=f"Rubric total should be {standards.hol_rubric_total_points} points",
                actual=f"{actual} points"
            ))

    return issues
```

4. **UI: Rubric Editor** (like other content editors)
   - Add/remove criteria
   - Add/remove levels per criterion
   - Edit level names, points, descriptions
   - Real-time total points display
   - Validation warnings (non-blocking)

**Files:**
- `src/core/models.py` (ContentStandardsProfile)
- `src/generators/schemas/hol.py` (RubricCriterion, RubricLevel)
- `src/validators/standards_validator.py`
- `static/js/pages/studio.js` (rubric editor UI)
- `templates/studio.html` (rubric editor template)

---

## MEDIUM PRIORITY

### 6. Video Section Timing Validation

**Reference:** Section 2.3

**Requirements:**
| Section | Word Count (at 150 WPM) |
|---------|------------------------|
| Hook | 75-150 words |
| Objective | 75-112 words |
| Content | 450-900 words |
| IVQ | 75-150 words |
| Summary | 75-112 words |
| CTA | 37-75 words |

**Files:** `src/validators/standards_validator.py`

---

### 7. WWHAA Sequence Validation

**Reference:** Section 1.4

**Current:** WWHAA phases exist but sequence not validated.

**Requirements:** Modules must follow WHY → WHAT → HOW → APPLY → ASSESS sequence.

| Phase | Item Types | Duration |
|-------|-----------|----------|
| WHY | Coach, Video | 5-15 min |
| WHAT | Video, Reading | 10-20 min |
| HOW | Screencast | 15-20 min |
| APPLY | HOL, Practice Quiz | 20-30 min |
| ASSESS | Graded Assessment | 10-20 min |

**Files:** `src/validators/course_auditor.py`

---

### 8. Reading Author Attribution Validation

**Reference:** Section 3.6

**Requirement:** Every reading must include after Key Takeaways:
```
Trajkovski, G. (2025). Author's original work based on professional experience,
developed with the assistance of AI tools (Claude AI).
```

**Files:** `src/validators/standards_validator.py`

---

### 9. Reference Link Validation

**Reference:** Section 3.2

**Requirements:**
- 3-4 APA 7 citations minimum
- All freely accessible (NO paywalls)
- Detect known paywall domains (jstor.org, springer.com, etc.)

**Implementation:**
```python
KNOWN_PAYWALL_DOMAINS = [
    'jstor.org', 'sciencedirect.com', 'springer.com',
    'wiley.com', 'tandfonline.com'
]
```

**Files:** New `src/validators/reference_validator.py`

---

### 10. Content Distribution Validation

**Reference:** Section 1.3

**Target distribution:**
| Content Type | Target % |
|--------------|----------|
| Videos | ~30% |
| Readings | ~20% |
| HOL Activities | ~30% |
| Assessments | ~20% |

**Files:** `src/validators/course_validator.py`

---

## LOW PRIORITY

### 11. Terminal Screenshot Image Generator [NEW v3.0]

**Reference:** Section 15

**Purpose:** Generate dark terminal images for HOL code examples.

**Visual specs:**
- Background: RGB(30, 30, 30)
- Text: RGB(204, 204, 204)
- Prompt ($): RGB(78, 201, 176)
- Font: DejaVu Sans Mono, 14pt
- Min width: 600px

**Files:** New `src/utils/terminal_image_generator.py`

---

### 12. CTA Slide Generator [NEW v3.0]

**Reference:** Section 16

**Purpose:** Generate end-of-video CTA slides per Coursera specs.

**Specs:**
- Canvas: 1280x720 px (16:9 HD)
- Coursera blue: #0056D2
- Course label, video title, tagline, footer with exact positions

**Files:** New `src/utils/cta_slide_generator.py`

---

### 13. Visual Cue Validation

**Reference:** Section 2.3

**Requirement:** Visual cues every 60-90 seconds in video content section.

**Format:** `[Talking head: description | B-roll: description]`

**Files:** `src/validators/standards_validator.py`

---

## Implementation Roadmap

### Phase 1: v1.2.0 (High Priority)
1. CTA Validation
2. Quiz Answer Distribution
3. AI Detection Expansion (5 patterns)
4. Sequential Reference Detection
5. Configurable HOL Rubric System (editable criteria, levels, points)

### Phase 2: v1.2.1 (Medium Priority)
1. Video Section Timing
2. WWHAA Sequence Validation
3. Reading Attribution
4. Reference Validation
5. Content Distribution

### Phase 3: v1.3.0 (Low Priority)
1. Terminal Screenshot Generator
2. CTA Slide Generator
3. Visual Cue Validation

---

## Summary Table

| # | Feature | Priority | Effort | Section |
|---|---------|----------|--------|---------|
| 1 | CTA Validation | HIGH | LOW | 2.3 |
| 2 | Answer Distribution | HIGH | MEDIUM | 6.3-6.4 |
| 3 | AI Detection Expansion | HIGH | MEDIUM | 14.3 |
| 4 | Sequential References | HIGH | LOW | 1.5 |
| 5 | HOL Rubric (configurable) | HIGH | MEDIUM | 4.6 |
| 6 | Video Section Timing | MEDIUM | LOW | 2.3 |
| 7 | WWHAA Sequence | MEDIUM | MEDIUM | 1.4 |
| 8 | Reading Attribution | MEDIUM | LOW | 3.6 |
| 9 | Reference Validation | MEDIUM | MEDIUM | 3.2 |
| 10 | Content Distribution | MEDIUM | LOW | 1.3 |
| 11 | Terminal Images | LOW | HIGH | 15 |
| 12 | CTA Slides | LOW | MEDIUM | 16 |
| 13 | Visual Cues | LOW | LOW | 2.3 |

---

*Last updated: 2026-02-17*
*Based on Coursera Master Reference v3.0 (February 2026)*
