---
phase: 04
plan: 03
subsystem: content-generation
tags: [reading-generator, apa-citations, tdd, anthropic-api, structured-output]
requires: [04-01]
provides: [ReadingGenerator, APA-7-citations, reading-metadata]
affects: [04-06, 04-07]
tech-stack:
  added: []
  patterns: [TDD-red-green-refactor, generic-base-class, pydantic-validation]
decisions:
  - id: reading-238-wpm
    desc: Use 238 WPM for reading duration estimates (adult non-fiction average)
    rationale: Industry standard from ContentMetadata utility
  - id: apa-7-format
    desc: Enforce APA 7 citation format in system prompt with examples
    rationale: Academic credibility and standardization
  - id: 1200-word-target
    desc: Default max_words to 1200 for readings
    rationale: Balances depth with learner attention span
key-files:
  created:
    - src/generators/reading_generator.py
    - tests/test_reading_generator.py
  modified: []
metrics:
  tests-added: 7
  tests-total: 211
  duration: 3 minutes
  completed: 2026-02-04
---

# Phase 04 Plan 03: ReadingGenerator with APA 7 Citations Summary

**One-liner:** ReadingGenerator extending BaseGenerator to produce structured readings with introduction, body sections, conclusion, and APA 7 formatted references using 238 WPM duration estimates.

## What Was Built

Implemented `ReadingGenerator` class using TDD methodology (RED-GREEN-REFACTOR):

### Core Functionality
- **ReadingGenerator class** extending `BaseGenerator[ReadingSchema]`
- **System prompt** with APA 7 citation format examples (book, journal, website)
- **build_user_prompt()** accepting learning_objective, topic, audience_level, max_words
- **extract_metadata()** calculating:
  - word_count: Sum of introduction + all section bodies + conclusion
  - estimated_duration_minutes: Using ContentMetadata.estimate_reading_duration() at 238 WPM
  - content_type: "reading"
  - section_count: Number of ReadingSection items
  - reference_count: Number of Reference items
- **generate_reading()** convenience method for simplified API

### TDD Process
1. **RED phase** (commit 721ef04): Created 7 failing tests
   - test_generate_returns_valid_schema
   - test_system_prompt_contains_apa7
   - test_build_user_prompt_includes_max_words
   - test_extract_metadata_calculates_correctly
   - test_metadata_duration_uses_238_wpm
   - test_api_called_with_output_config
   - test_metadata_includes_section_and_reference_counts

2. **GREEN phase** (commit 60a3219): Implemented ReadingGenerator to pass all tests

3. **REFACTOR phase**: No changes needed - code clean and well-structured

## Technical Implementation

### System Prompt Design
Includes:
- Role definition as expert educational content writer
- Structural requirements (introduction, 2-6 sections, conclusion)
- APA 7 format examples with concrete patterns
- 1200-word guideline for total length
- Section length guidance (50-100 words intro/conclusion, 150-300 words per section)

### Metadata Calculation
```python
# Concatenates all text content
full_text = introduction + all_section_bodies + conclusion
word_count = ContentMetadata.count_words(full_text)
duration = ContentMetadata.estimate_reading_duration(word_count)  # 238 WPM
```

### Integration Points
- Extends `BaseGenerator[ReadingSchema]` from plan 04-01
- Uses `ReadingSchema`, `ReadingSection`, `Reference` from plan 04-01
- Uses `ContentMetadata` utility from plan 04-01
- Follows same pattern as other Wave 2 generators (VideoScript, Quiz, Rubric)

## Test Coverage

**7 tests added** covering:
- Schema validation and structure
- System prompt content (APA 7 guidance)
- User prompt formatting (max_words inclusion)
- Metadata calculation accuracy
- Duration calculation (238 WPM verification)
- API call structure (output_config parameter)
- Extended metadata (section_count, reference_count)

**All tests pass** - 0 failures, 211 total tests in suite.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| reading-238-wpm | Use 238 WPM for reading duration estimates | Industry standard for adult non-fiction (from ContentMetadata) |
| apa-7-format | Enforce APA 7 citation format with examples in system prompt | Academic credibility and standardization for educational content |
| 1200-word-target | Default max_words to 1200 for readings | Balances content depth with learner attention span (~5 min read) |
| convenience-method | Include generate_reading() helper method | Simplifies API usage for common case |

## Deviations from Plan

None - plan executed exactly as written. TDD process followed precisely with RED-GREEN-REFACTOR phases.

## Files Changed

### Created
- `src/generators/reading_generator.py` (153 lines)
  - ReadingGenerator class with system_prompt, build_user_prompt, extract_metadata
  - Full docstrings and type hints
  - APA 7 citation examples embedded in system prompt

- `tests/test_reading_generator.py` (180 lines)
  - 7 comprehensive tests with pytest-mock
  - Mock Anthropic API client
  - Sample reading response fixture

### Modified
None

## Validation Results

**Test execution:**
```
tests/test_reading_generator.py::test_generate_returns_valid_schema PASSED
tests/test_reading_generator.py::test_system_prompt_contains_apa7 PASSED
tests/test_reading_generator.py::test_build_user_prompt_includes_max_words PASSED
tests/test_reading_generator.py::test_extract_metadata_calculates_correctly PASSED
tests/test_reading_generator.py::test_metadata_duration_uses_238_wpm PASSED
tests/test_reading_generator.py::test_api_called_with_output_config PASSED
tests/test_reading_generator.py::test_metadata_includes_section_and_reference_counts PASSED

7 passed in 0.07s
```

**Regression check:** 211 tests pass, 0 regressions

## Integration Notes

ReadingGenerator is ready for use in:
- **Plan 04-06** (Content Writer): Will use ReadingGenerator.generate_reading()
- **Plan 04-07** (E2E Tests): Will test full pipeline including reading generation

**Usage pattern:**
```python
generator = ReadingGenerator()
reading, metadata = generator.generate_reading(
    learning_objective="Understand machine learning basics",
    topic="Introduction to Machine Learning",
    audience_level="beginner",
    max_words=1200
)
# reading: ReadingSchema instance with title, intro, sections, conclusion, references
# metadata: dict with word_count, duration, section_count, reference_count
```

## Next Phase Readiness

**Ready for Phase 4 continuation:**
- ✅ ReadingGenerator fully tested and operational
- ✅ No blocking issues or concerns
- ✅ Consistent with other Wave 2 generators (VideoScript, Quiz, Rubric)
- ✅ APA 7 citation format embedded in prompts
- ✅ Metadata calculation uses industry-standard 238 WPM

**Dependencies satisfied:**
- Plan 04-01 (BaseGenerator, schemas, utilities) ✅

**Next steps:**
- Implement remaining Wave 2 generators if any
- Proceed to Plan 04-06 (Content Writer orchestration)
- E2E testing in Plan 04-07

## Commit Summary

| Commit | Type | Description |
|--------|------|-------------|
| 721ef04 | test | Add failing tests for ReadingGenerator (RED phase) |
| 60a3219 | feat | Implement ReadingGenerator with APA 7 citations (GREEN phase) |

**Total duration:** ~3 minutes
**Lines added:** 333 (153 implementation + 180 tests)
**Test success rate:** 100% (7/7 new tests pass, 0 regressions)
