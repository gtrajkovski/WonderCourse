# Phase 7: Validation & Quality - Research

**Researched:** 2026-02-06
**Domain:** Educational content quality validation and accessibility compliance
**Confidence:** MEDIUM

## Summary

Phase 7 focuses on comprehensive quality validation for generated courses before publishing. The phase covers six distinct validation domains: structural validation (Coursera requirements), outcome coverage analysis, Bloom's taxonomy alignment, accessibility compliance (WCAG 2.1 AA), quiz distractor quality, and aggregate validation reporting.

The existing CourseraValidator in `src/validators/course_validator.py` already handles basic structural validation (duration, module count, content distribution) against Coursera requirements. This phase extends validation capabilities to cover learning quality dimensions not yet implemented: outcome-activity alignment gaps, Bloom's distribution warnings, accessibility compliance checks, and quiz distractor quality analysis.

The codebase already has outcome-activity mapping infrastructure (`LearningOutcome.mapped_activity_ids`) and a basic coverage score calculation (percentage of outcomes with at least one mapped activity). Phase 7 needs to extend this with gap detection (activities not mapped, outcomes with insufficient coverage) and Bloom's alignment validation.

**Primary recommendation:** Build validation as deterministic Python validators (no AI), extend existing CourseraValidator pattern, use axe-selenium-python for WCAG validation, implement distractor quality checks using educational psychometrics patterns.

## Standard Stack

### Core Validation
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Built-in Python | 3.9+ | Deterministic validation logic | All validation should be pure Python, not AI |
| Existing CourseraValidator | Current | Structural validation | Already validates duration, module count, content distribution |
| collections.Counter | stdlib | Content distribution analysis | Efficient counting for Bloom's distribution |

### Accessibility Testing
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axe-selenium-python | 2.1.6+ | WCAG 2.1 AA automated testing | For HTML content accessibility validation |
| selenium | 4.0+ | Browser automation for axe-core | Required by axe-selenium-python |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| beautifulsoup4 | 4.12+ | HTML parsing | For pre-validation content structure checks |
| html5lib | 1.1+ | HTML5 validation | For well-formedness checks before accessibility testing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| axe-selenium-python | pa11y (Node.js) | Pa11y requires Node.js runtime, adds cross-language complexity |
| Deterministic validators | AI-based validation | AI adds non-determinism and hallucination risk for quality gates |
| Built-in patterns | python-psychometrics library | Psychometrics library is overkill for simple distractor checks |

**Installation:**
```bash
pip install axe-selenium-python selenium beautifulsoup4 html5lib
```

## Architecture Patterns

### Recommended Project Structure
```
src/validators/
├── course_validator.py          # [EXISTS] Structural validation
├── outcome_validator.py          # NEW: Outcome coverage & gap detection
├── blooms_validator.py          # NEW: Bloom's taxonomy alignment
├── accessibility_validator.py   # NEW: WCAG 2.1 AA compliance
├── distractor_validator.py      # NEW: Quiz distractor quality
└── validation_report.py         # NEW: Aggregate validation report

src/api/
├── validation.py                # NEW: Validation API endpoints
```

### Pattern 1: Validator Result Objects

**What:** Consistent validation result structure across all validators
**When to use:** All validators return this structure for uniform reporting

**Example:**
```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    """Validation result for any validation check."""
    is_valid: bool              # Overall pass/fail
    errors: List[str]           # Blockers (prevent publishing)
    warnings: List[str]         # Non-blocking issues
    suggestions: List[str]      # Optional improvements
    metrics: Dict[str, Any]     # Computed metrics for display

# Already exists as BlueprintValidation in course_validator.py
# Reuse this pattern for consistency
```

### Pattern 2: Validator Classes with validate() Method

**What:** Each validator is a class with a single public `validate()` method
**When to use:** All validators follow this pattern (CourseraValidator already does)

**Example:**
```python
class OutcomeValidator:
    """Validates learning outcome coverage and alignment."""

    def validate(self, course: Course) -> ValidationResult:
        """Run all outcome validation checks."""
        errors = []
        warnings = []
        suggestions = []
        metrics = {}

        # Validation logic here

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )
```

### Pattern 3: Hierarchical Validation Reporting

**What:** Aggregate validator that runs all validators and combines results
**When to use:** For comprehensive validation report endpoint

**Example:**
```python
class ValidationReport:
    """Aggregates all validation results into single report."""

    def __init__(self, project_store):
        self.validators = [
            CourseraValidator(),
            OutcomeValidator(),
            BloomsValidator(),
            AccessibilityValidator(),
            DistractorValidator()
        ]

    def validate_course(self, course: Course) -> Dict[str, ValidationResult]:
        """Run all validators and return combined report."""
        results = {}
        for validator in self.validators:
            validator_name = validator.__class__.__name__
            results[validator_name] = validator.validate(course)
        return results

    def is_publishable(self, course: Course) -> bool:
        """Check if course passes all critical validation checks."""
        results = self.validate_course(course)
        # Only errors block publishing (not warnings or suggestions)
        return all(result.is_valid for result in results.values())
```

### Pattern 4: Accessibility Validation with Headless Browser

**What:** Use Selenium headless mode with axe-core for WCAG validation
**When to use:** For generated HTML content (readings, video scripts as HTML previews)

**Example:**
```python
from selenium import webdriver
from axe_selenium_python import Axe

def validate_html_accessibility(html_content: str) -> ValidationResult:
    """Validate HTML content against WCAG 2.1 AA."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    try:
        # Load HTML content
        driver.get(f"data:text/html;charset=utf-8,{html_content}")

        # Run axe accessibility checks
        axe = Axe(driver)
        axe.inject()
        results = axe.run()

        # Parse violations
        errors = []
        warnings = []
        for violation in results.get('violations', []):
            impact = violation.get('impact')
            message = f"{violation['help']} ({impact})"
            if impact in ['critical', 'serious']:
                errors.append(message)
            else:
                warnings.append(message)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=[],
            metrics={'wcag_version': '2.1', 'level': 'AA'}
        )
    finally:
        driver.quit()
```

### Anti-Patterns to Avoid

- **AI-based validation:** Quality gates must be deterministic. AI validation introduces non-determinism and hallucination risk. Use pure Python logic.
- **Monolithic validator:** Don't put all validation in CourseraValidator. Separate concerns by validation domain (structure, outcomes, Bloom's, accessibility, distractors).
- **Synchronous accessibility checks in request:** axe-selenium-python with headless Chrome takes 2-3 seconds per page. Run asynchronously or cache results.
- **Failing on warnings:** Only errors should block publishing. Warnings are informational. Build state should allow publishing with warnings.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WCAG compliance checking | Custom HTML parsers for alt text, contrast, etc. | axe-selenium-python with axe-core | Axe-core finds ~57% of WCAG issues automatically, actively maintained by Deque Systems, standard industry tool |
| HTML well-formedness | Regex-based HTML validation | html5lib parser | HTML5 parsing is complex (void elements, optional closing tags, CDATA), html5lib is spec-compliant |
| Content distribution analysis | Manual counting loops | collections.Counter | Counter is optimized, readable, handles missing keys gracefully |
| Bloom's taxonomy mapping | String matching on verbs | Existing BloomLevel enum + explicit activity.bloom_level field | Activity already has bloom_level from generation; validate distribution not mapping |

**Key insight:** Accessibility validation is a solved problem with mature tooling. Don't rebuild axe-core's rule engine. Focus effort on domain-specific validation (outcome coverage, Bloom's alignment, distractor quality) where no standard tools exist.

## Common Pitfalls

### Pitfall 1: Over-reliance on Automated Accessibility Testing
**What goes wrong:** Automated tools like axe-core detect only ~30% of accessibility issues. The remaining ~70% require manual testing with assistive technology.
**Why it happens:** Developers assume automation catches everything. WCAG has complex subjective requirements (meaningful alt text, logical heading structure, keyboard navigation patterns).
**How to avoid:** Document that accessibility validation is "automated checks only" and recommend manual audit before publishing to production. Frame Phase 7 as "catching obvious issues" not "full compliance certification."
**Warning signs:** Requirements claiming "full WCAG 2.1 AA compliance" without manual testing budget.

### Pitfall 2: Treating Warnings as Errors
**What goes wrong:** Publishing is blocked by non-critical issues. Users can't publish courses with minor Bloom's imbalances or content distribution variations.
**Why it happens:** Confusion between errors (blockers) and warnings (suggestions). Overly strict validation gates.
**How to avoid:** Clear three-tier system: errors block publishing, warnings show in report but allow publishing, suggestions are optional improvements. Build state APPROVED → PUBLISHED transition checks only errors.
**Warning signs:** User complaints about "can't publish despite valid content" or "validation too strict."

### Pitfall 3: Synchronous Validation Blocking UI
**What goes wrong:** User clicks "Validate Course" and UI hangs for 30+ seconds while accessibility checks run on all content.
**Why it happens:** Each axe-selenium-python check takes 2-3 seconds. Course with 20 HTML content items = 40-60 seconds total.
**How to avoid:** Run validation asynchronously using JobTracker pattern (already exists from Phase 6). Return task_id, poll for results. Cache validation results until content changes.
**Warning signs:** Frontend timeout errors, user complaints about "loading forever."

### Pitfall 4: Non-Functioning Distractors False Positives
**What goes wrong:** Distractor validator flags "non-functioning" distractors before quiz is tested with real students.
**Why it happens:** Non-functioning distractor (NFD) is defined as "selected by <5% of students" but validation runs before any students take the quiz.
**How to avoid:** Distractor quality checks should focus on detectible issues: obviously correct distractors (duplicate correct answer), technically incorrect distractors (contradicts question), implausible distractors (nonsense text). Don't try to predict student selection rates.
**Warning signs:** Distractor validator using statistical thresholds without student response data.

### Pitfall 5: Bloom's Alignment Over-Validation
**What goes wrong:** Validator requires exact distribution percentages (e.g., "must have 20% Apply, 30% Analyze") that don't match learning goals.
**Why it happens:** Misunderstanding Bloom's taxonomy. Not all courses need all six levels. Technical courses emphasize Apply/Analyze, foundational courses emphasize Remember/Understand.
**How to avoid:** Validate minimum diversity (at least 2-3 levels represented) and flag imbalances (>80% single level) but don't enforce specific percentages. Warnings, not errors.
**Warning signs:** Requirements specifying exact Bloom's distribution percentages.

### Pitfall 6: Outcome Coverage Calculation Errors
**What goes wrong:** Coverage score doesn't match user's understanding. Activities mapped to outcomes that were deleted still count as "covered."
**Why it happens:** Stale data in `outcome.mapped_activity_ids` (activity IDs that no longer exist in course structure).
**How to avoid:** Validate mapped activity IDs still exist before counting coverage. Filter out stale references. Consider cascading cleanup on activity delete (already done for outcome delete in Phase 2).
**Warning signs:** Coverage score doesn't match visible mappings in UI, "ghost" activity IDs in alignment matrix.

## Code Examples

Verified patterns from codebase and official sources:

### Example 1: Existing Coverage Score Calculation

```python
# Source: src/api/learning_outcomes.py lines 427-431
# Current implementation (reuse this pattern)

# Calculate coverage score
if len(course.learning_outcomes) > 0:
    coverage_score = (
        len(course.learning_outcomes) - len(unmapped_outcomes)
    ) / len(course.learning_outcomes)
else:
    coverage_score = 0.0

# Coverage score = percentage of outcomes with at least one mapped activity
# Phase 7 extension: Add gap detection for insufficient coverage
```

### Example 2: Bloom's Distribution Analysis

```python
# Source: Adapted from CourseraValidator._flatten_activities pattern
# New code for BloomsValidator

from collections import Counter
from src.core.models import BloomLevel, Course

class BloomsValidator:
    """Validates Bloom's taxonomy level distribution."""

    MIN_DIVERSITY = 2  # At least 2 different levels
    IMBALANCE_THRESHOLD = 0.80  # Warn if >80% single level

    def validate(self, course: Course) -> ValidationResult:
        errors = []
        warnings = []
        suggestions = []

        # Get all activities
        all_activities = self._flatten_activities(course)
        if not all_activities:
            return ValidationResult(
                is_valid=True, errors=[], warnings=[],
                suggestions=["Add activities to analyze Bloom's levels"],
                metrics={}
            )

        # Count Bloom's levels
        bloom_levels = [a.bloom_level for a in all_activities if a.bloom_level]
        level_counts = Counter(bloom_levels)
        unique_levels = len(level_counts)

        # ERROR: Must have at least 2 levels (too narrow for learning)
        if unique_levels < self.MIN_DIVERSITY:
            errors.append(
                f"Only {unique_levels} Bloom's level(s) used "
                f"(minimum {self.MIN_DIVERSITY} for diverse learning)"
            )

        # WARNING: Imbalanced distribution (>80% single level)
        if unique_levels > 0:
            max_count = max(level_counts.values())
            total = len(bloom_levels)
            if max_count / total > self.IMBALANCE_THRESHOLD:
                dominant_level = max(level_counts, key=level_counts.get)
                warnings.append(
                    f"Bloom's distribution imbalanced: "
                    f"{max_count/total:.0%} {dominant_level.value} "
                    f"(consider more variety)"
                )

        # SUGGESTION: Missing higher-order thinking
        has_higher_order = any(
            level in [BloomLevel.ANALYZE, BloomLevel.EVALUATE, BloomLevel.CREATE]
            for level in level_counts.keys()
        )
        if not has_higher_order:
            suggestions.append(
                "Consider adding higher-order thinking activities "
                "(Analyze, Evaluate, Create)"
            )

        # Metrics for display
        distribution = {
            level.value: count / total
            for level, count in level_counts.items()
        }

        metrics = {
            "unique_levels": unique_levels,
            "total_activities": total,
            "distribution": distribution,
            "dominant_level": max(level_counts, key=level_counts.get).value
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, course):
        """Extract all activities from course structure."""
        activities = []
        for module in course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
```

### Example 3: Distractor Quality Analysis

```python
# Source: Educational research on distractor quality
# Based on BMC Medical Education 2009, Sage Review 2017
# New code for DistractorValidator

from src.generators.schemas.quiz import QuizSchema
import json

class DistractorValidator:
    """Validates quiz distractor quality."""

    def validate_quiz_content(self, quiz_content: str) -> ValidationResult:
        """Validate distractors in quiz JSON content."""
        errors = []
        warnings = []
        suggestions = []
        metrics = {}

        try:
            quiz_data = json.loads(quiz_content)
            quiz = QuizSchema.model_validate(quiz_data)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid quiz content: {e}"],
                warnings=[], suggestions=[], metrics={}
            )

        total_questions = len(quiz.questions)
        flagged_questions = []

        for i, question in enumerate(quiz.questions, 1):
            question_issues = []

            # Check 1: Multiple correct answers (duplicate correct)
            correct_count = sum(1 for opt in question.options if opt.is_correct)
            if correct_count > 1:
                question_issues.append(
                    f"Q{i}: Multiple correct answers ({correct_count})"
                )
            elif correct_count == 0:
                question_issues.append(f"Q{i}: No correct answer marked")

            # Check 2: Distractors too similar to correct answer
            correct_option = next(
                (opt for opt in question.options if opt.is_correct), None
            )
            if correct_option:
                correct_text = correct_option.text.lower()
                for opt in question.options:
                    if not opt.is_correct:
                        similarity = self._calculate_similarity(
                            correct_text, opt.text.lower()
                        )
                        if similarity > 0.85:
                            question_issues.append(
                                f"Q{i}: Distractor too similar to correct answer "
                                f"('{opt.text[:30]}...')"
                            )

            # Check 3: Not enough distractors (should be 2-3)
            distractor_count = len(question.options) - 1
            if distractor_count < 2:
                warnings.append(
                    f"Q{i}: Only {distractor_count} distractor(s) "
                    f"(recommended 2-3)"
                )

            # Check 4: Implausible distractors (very short, nonsense)
            for opt in question.options:
                if not opt.is_correct and len(opt.text.strip()) < 5:
                    question_issues.append(
                        f"Q{i}: Implausible distractor too short ('{opt.text}')"
                    )

            if question_issues:
                flagged_questions.append(question_issues)

        # Aggregate errors
        if flagged_questions:
            for issues in flagged_questions:
                errors.extend(issues)

        # Metrics
        metrics = {
            "total_questions": total_questions,
            "flagged_questions": len(flagged_questions),
            "distractor_quality_score": (
                1.0 - len(flagged_questions) / total_questions
                if total_questions > 0 else 0.0
            )
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (0.0 to 1.0)."""
        # Simple character-level Jaccard similarity
        set1 = set(text1.split())
        set2 = set(text2.split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
```

### Example 4: Outcome Gap Detection

```python
# Source: Extension of existing alignment endpoint pattern
# New code for OutcomeValidator

from src.core.models import Course

class OutcomeValidator:
    """Validates learning outcome coverage and gap detection."""

    MIN_ACTIVITIES_PER_OUTCOME = 2  # Each outcome should have 2+ activities

    def validate(self, course: Course) -> ValidationResult:
        errors = []
        warnings = []
        suggestions = []

        # Get all activities
        all_activities = self._flatten_activities(course)
        activity_ids = {a.id for a in all_activities}

        # Check each outcome
        low_coverage_outcomes = []
        unmapped_outcomes = []

        for outcome in course.learning_outcomes:
            # Filter out stale activity IDs (activities that no longer exist)
            valid_mappings = [
                aid for aid in outcome.mapped_activity_ids
                if aid in activity_ids
            ]

            if len(valid_mappings) == 0:
                unmapped_outcomes.append(outcome)
            elif len(valid_mappings) < self.MIN_ACTIVITIES_PER_OUTCOME:
                low_coverage_outcomes.append((outcome, len(valid_mappings)))

        # ERROR: Unmapped outcomes
        if unmapped_outcomes:
            errors.append(
                f"{len(unmapped_outcomes)} learning outcome(s) not mapped "
                f"to any activities: {', '.join(o.behavior[:30] for o in unmapped_outcomes[:3])}"
            )

        # WARNING: Low coverage outcomes
        for outcome, count in low_coverage_outcomes:
            warnings.append(
                f"Outcome '{outcome.behavior[:50]}...' only mapped to "
                f"{count} activity(ies) (recommended {self.MIN_ACTIVITIES_PER_OUTCOME}+)"
            )

        # Check for unmapped activities
        mapped_activity_ids = set()
        for outcome in course.learning_outcomes:
            mapped_activity_ids.update(outcome.mapped_activity_ids)

        unmapped_activities = [
            a for a in all_activities if a.id not in mapped_activity_ids
        ]

        if unmapped_activities and course.learning_outcomes:
            warnings.append(
                f"{len(unmapped_activities)} activity(ies) not mapped to "
                f"any learning outcomes"
            )

        # Calculate coverage metrics
        if course.learning_outcomes:
            coverage_score = (
                len(course.learning_outcomes) - len(unmapped_outcomes)
            ) / len(course.learning_outcomes)

            avg_activities_per_outcome = sum(
                len([aid for aid in o.mapped_activity_ids if aid in activity_ids])
                for o in course.learning_outcomes
            ) / len(course.learning_outcomes)
        else:
            coverage_score = 0.0
            avg_activities_per_outcome = 0.0

        metrics = {
            "coverage_score": round(coverage_score, 2),
            "unmapped_outcomes": len(unmapped_outcomes),
            "low_coverage_outcomes": len(low_coverage_outcomes),
            "unmapped_activities": len(unmapped_activities),
            "avg_activities_per_outcome": round(avg_activities_per_outcome, 1),
            "total_outcomes": len(course.learning_outcomes),
            "total_activities": len(all_activities)
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, course):
        """Extract all activities from course structure."""
        activities = []
        for module in course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
```

### Example 5: Validation API Endpoint Pattern

```python
# Source: Existing Blueprint API pattern from src/api/blueprint.py
# New code for src/api/validation.py

from flask import Blueprint, jsonify
from src.validators.course_validator import CourseraValidator
from src.validators.outcome_validator import OutcomeValidator
from src.validators.blooms_validator import BloomsValidator
from src.validators.validation_report import ValidationReport

validation_bp = Blueprint('validation', __name__)
_project_store = None
_validation_report = None

def init_validation_bp(project_store):
    """Initialize validation blueprint with dependencies."""
    global _project_store, _validation_report
    _project_store = project_store
    _validation_report = ValidationReport(project_store)
    return validation_bp

@validation_bp.route('/api/courses/<course_id>/validate', methods=['GET'])
def validate_course(course_id):
    """Run all validation checks and return comprehensive report.

    Returns:
        JSON validation report with results from all validators:
        {
            "is_publishable": bool,
            "validators": {
                "CourseraValidator": ValidationResult,
                "OutcomeValidator": ValidationResult,
                "BloomsValidator": ValidationResult,
                ...
            },
            "summary": {
                "total_errors": int,
                "total_warnings": int,
                "total_suggestions": int
            }
        }

    Errors:
        404 if course not found.
        500 if validation fails.
    """
    try:
        course = _project_store.load(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Run all validators
        results = _validation_report.validate_course(course)
        is_publishable = _validation_report.is_publishable(course)

        # Convert ValidationResult objects to dicts
        results_dict = {
            name: {
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "suggestions": result.suggestions,
                "metrics": result.metrics
            }
            for name, result in results.items()
        }

        # Summary counts
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        total_suggestions = sum(len(r.suggestions) for r in results.values())

        return jsonify({
            "is_publishable": is_publishable,
            "validators": results_dict,
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_suggestions": total_suggestions
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual WCAG checks | Automated with axe-core/axe DevTools | 2015-2020 | ~57% of WCAG issues detectable automatically |
| String-based Bloom's verb matching | Explicit bloom_level field per activity | Phase 4 (2024) | Activities have Bloom's level from generation, not inferred |
| Simple coverage (mapped Y/N) | Gap detection with minimum activities threshold | Phase 7 (2026) | Identifies under-mapped outcomes, not just unmapped |
| Separate accessibility tools (WAVE, Lighthouse, Pa11y) | Consolidated on axe-core ecosystem | 2018-2024 | Axe-core is industry standard, most comprehensive rule engine |
| Distractor analysis post-deployment | Pre-deployment quality checks | Phase 7 (2026) | Catch obvious issues before student testing |

**Deprecated/outdated:**
- **Pa11y for Python projects**: Requires Node.js, adds cross-language complexity. Use axe-selenium-python instead.
- **Manual HTML validation with regex**: Use html5lib parser for spec-compliant parsing.
- **AI-based validation**: Non-deterministic, hallucination risk. Use deterministic Python logic.
- **Accessibility-only validation focus**: Modern validation includes learning quality dimensions (outcome coverage, Bloom's alignment) not just technical compliance.

## Open Questions

Things that couldn't be fully resolved:

1. **Accessibility validation scope for non-HTML content**
   - What we know: axe-selenium-python validates HTML. Video scripts and readings are stored as JSON, not HTML.
   - What's unclear: Should Phase 7 validate HTML rendering of content, or defer to Phase 11 (UI Polish)? Video scripts will eventually be rendered as HTML in UI.
   - Recommendation: Phase 7 validates content structure (headings, lists, references) via JSON schema. Phase 11 validates HTML rendering accessibility. Document this split clearly in requirements.

2. **Threshold for "publishable" with warnings**
   - What we know: Errors block publishing, warnings don't. But how many warnings is "too many"?
   - What's unclear: Should there be a warning count threshold (e.g., max 10 warnings) or severity threshold (e.g., no critical warnings)?
   - Recommendation: Start permissive (warnings never block), add threshold only if user feedback indicates "too many warnings ignored." Track warning counts in metrics.

3. **Distractor quality validation without student data**
   - What we know: True NFD detection requires student response rates (selected by <5%). We don't have student data pre-deployment.
   - What's unclear: What proxy metrics predict NFD? Research shows quality matters more than count, but specific detectible patterns vary by domain.
   - Recommendation: Focus on structural issues (duplicate correct, implausible text, extreme similarity). Mark as "distractor quality warnings" not "NFD detection." User can refine based on pilot testing.

4. **Caching strategy for validation results**
   - What we know: Validation is expensive (accessibility checks 2-3 sec/page). Re-running on every request is slow.
   - What's unclear: Cache key (course_id + updated_at?), cache invalidation (on content change?), cache storage (in-memory or Redis?).
   - Recommendation: Phase 7 implements no caching (run validation on-demand). Phase 8+ adds caching if performance becomes issue. Use JobTracker pattern for async validation.

5. **Build state transition on validation failure**
   - What we know: Build state workflow is DRAFT → GENERATING → GENERATED → REVIEWED → APPROVED → PUBLISHED. QA-02 says validation prevents publishing.
   - What's unclear: Can user transition APPROVED → PUBLISHED with validation warnings? Should validation run automatically on APPROVED transition or only on explicit "Validate" button?
   - Recommendation: Validation runs on explicit user request (/api/courses/:id/validate endpoint). APPROVED → PUBLISHED transition checks is_publishable() (errors only, warnings OK). User sees validation report before publishing.

## Sources

### Primary (HIGH confidence)
- [CourseraValidator implementation](file://C:\CourseBuilder\src\validators\course_validator.py) - Existing structural validation patterns
- [Learning outcomes API](file://C:\CourseBuilder\src\api\learning_outcomes.py) - Coverage score calculation and alignment matrix
- [axe-selenium-python on PyPI](https://pypi.org/project/axe-selenium-python/) - Python package for WCAG testing
- [Axe-core by Deque](https://www.deque.com/axe/axe-core/) - Official axe-core documentation
- [BMC Medical Education: Distractor Analysis](https://bmcmededuc.biomedcentral.com/articles/10.1186/1472-6920-9-40) - NFD research (38.73% NFD rate)

### Secondary (MEDIUM confidence)
- [W3C WCAG 2.1 AA Overview](https://www.w3.org/WAI/standards-guidelines/wcag/) - Official WCAG standards (verified multiple sources)
- [Sage Review: Developing Distractors for MCQs](https://journals.sagepub.com/doi/abs/10.3102/0034654317726529) - Comprehensive distractor review
- [Curriculum Mapping Best Practices](https://www.scu.edu/provost/institutional-effectiveness/assessment/foundations/curriculum-matrix-page/) - I/R/M proficiency framework
- [Higher Education Studies 2026: 5Ps Distractor Typology](https://ccsenet.org/journal/index.php/hes/article/download/0/0/52840/57604) - Recent distractor classification research

### Tertiary (LOW confidence - needs validation)
- Python psychometrics libraries (python-psychometrics, pypsy) - Exist but unclear if maintained, overkill for simple checks
- Bloom's taxonomy verb mapping approaches - Multiple contradictory approaches in community, explicit field more reliable

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - axe-selenium-python is industry standard, well-documented
- Architecture: HIGH - Pattern matches existing CourseraValidator, validation API follows blueprint pattern
- Accessibility validation: MEDIUM - Axe-core verified but 30/70 automated/manual split requires documentation
- Distractor quality: MEDIUM - Research-backed patterns but no standard library, custom implementation needed
- Outcome coverage: HIGH - Existing infrastructure from Phase 2, extension patterns clear
- Bloom's alignment: HIGH - BloomLevel enum exists, Counter pattern standard

**Research date:** 2026-02-06
**Valid until:** 2026-04-06 (60 days - stable domain, WCAG standards don't change frequently)
