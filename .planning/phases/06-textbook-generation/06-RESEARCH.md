# Phase 6: Textbook Generation - Research

**Researched:** 2026-02-04
**Domain:** Long-form educational content generation with LLMs
**Confidence:** MEDIUM (verified core techniques; async job implementation needs validation)

## Summary

Phase 6 implements textbook chapter generation (~3000 words per learning outcome) with hierarchical expansion, coherence validation, glossary term extraction, image placeholder generation, and APA 7 citations. The phase builds on the established BaseGenerator pattern while adding new capabilities for long-form content management and job progress tracking.

**Key challenges addressed:**
1. **Token limits**: 3000-word chapters (~4000 tokens) can exceed some model limits; requires hierarchical generation strategy
2. **Coherence**: Long-form content needs cross-section consistency checks to prevent contradictions
3. **Progress tracking**: Multi-minute generation jobs need user feedback via async task queues
4. **Glossary extraction**: Automated term identification and definition generation for educational content
5. **Image placeholders**: Structured suggestions for visual aids with captions and accessibility considerations

**Primary recommendation:** Use hierarchical expansion (outline → section-by-section generation) with Claude's structured outputs, implement simple in-memory job queue for progress tracking (defer full Celery until Phase 8+), and leverage existing ReadingGenerator patterns for APA 7 citations and structured content.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.77.0+ | Claude API with structured outputs | Native support for output_config with JSON schemas |
| pydantic | 2.10.0+ | Schema validation | Type-safe content validation, already used for all 11 generators |
| Flask | 3.1.0+ | Web framework | Already serving API, blueprint pattern established |

### New Dependencies (None Required)
All functionality can be implemented with existing dependencies. Consider future additions:

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| celery | 5.4.0+ | Distributed task queue | Phase 8+ (batch generation, multi-user) |
| redis | 5.0.0+ | Message broker for Celery | Phase 8+ (if Celery adopted) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory queue | Celery + Redis | Celery adds complexity (broker setup, worker management) but enables distributed processing. Use in-memory for Phase 6, migrate to Celery in Phase 8+ if multi-user load requires it. |
| Hierarchical expansion | Single-shot 3000-word generation | Single-shot risks token limits (~4000 tokens) and coherence issues. Hierarchical expansion proven effective (OpenCredo 2025, academic research). |
| Custom glossary extraction | spaCy NER + terminology extraction | Could add spaCy for advanced term extraction, but LLM-based extraction sufficient for educational content with high recall. |

**Installation:**
No new dependencies required for Phase 6.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── generators/
│   ├── textbook_generator.py           # NEW: TextbookGenerator with hierarchical expansion
│   ├── schemas/
│   │   └── textbook.py                 # NEW: TextbookSchema with sections, glossary, images
├── api/
│   ├── textbook.py                      # NEW: Textbook generation endpoints
│   ├── job_tracker.py                   # NEW: In-memory job progress tracking
├── utils/
│   ├── coherence_validator.py           # NEW: Cross-section consistency checking
│   ├── glossary_extractor.py            # NEW: Term extraction and definition generation
```

### Pattern 1: Hierarchical Expansion for Long-Form Content
**What:** Generate long content in stages: (1) outline, (2) section-by-section expansion, (3) glossary/images, (4) coherence check
**When to use:** Content >1500 words or requiring internal consistency
**How it works:**
1. **Outline generation**: Generate structured TOC with section titles and 1-sentence descriptions
2. **Section expansion**: Generate each section independently with context from outline
3. **Post-processing**: Extract glossary terms, suggest image placements
4. **Validation**: Check cross-section consistency (no contradictions, term usage)

**Research basis:**
- [Hierarchical Expansion technique](https://www.opencredo.com/blogs/how-to-use-llms-to-generate-coherent-long-form-content-using-hierarchical-expansion) (OpenCredo 2025)
- [LLM hierarchical memory systems](https://medium.com/@vforqa/llm-development-in-2026-transforming-ai-with-hierarchical-memory-for-deep-context-understanding-32605950fa47) (2026 research)
- Academic papers on long-text coherence maintenance (ArXiv 2025)

**Example workflow:**
```python
# Step 1: Generate outline
outline_schema = TextbookOutlineSchema  # titles + descriptions
outline, _ = generator.generate(schema=outline_schema, learning_outcome=lo)

# Step 2: Generate each section with context
sections = []
for section_title, section_desc in outline.sections:
    section_prompt = f"Chapter: {chapter_title}\nOutline: {outline}\nWrite section: {section_title} ({section_desc})"
    section, _ = generator.generate(schema=TextbookSectionSchema, prompt=section_prompt)
    sections.append(section)

# Step 3: Generate glossary from all sections
glossary_prompt = f"Extract key terms from:\n{all_sections_text}"
glossary, _ = generator.generate(schema=GlossarySchema, prompt=glossary_prompt)

# Step 4: Validate coherence
coherence_issues = validator.check_consistency(sections)
```

**Token budget planning:**
- Outline: ~500 tokens (5-8 sections with descriptions)
- Per-section: ~500-600 words = ~650-800 tokens each
- Glossary: ~200 tokens (10-15 terms)
- Total input+output per chapter: ~6000-8000 tokens (well within Claude's limits)

### Pattern 2: In-Memory Job Tracking (Phase 6 Simplification)
**What:** Dictionary-based job status tracking with task_id lookup
**When to use:** Single-user, low-concurrency workload (Phase 6-7)
**Why defer Celery:** Adds complexity (Redis setup, worker processes, deployment overhead) premature for current scope

**Implementation:**
```python
# src/api/job_tracker.py
from dataclasses import dataclass
from typing import Dict, Optional
import uuid
from datetime import datetime

@dataclass
class JobStatus:
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    current_step: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

class JobTracker:
    _jobs: Dict[str, JobStatus] = {}

    @classmethod
    def create_job(cls, task_type: str) -> str:
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        cls._jobs[task_id] = JobStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            current_step="Initializing",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        return task_id

    @classmethod
    def update_job(cls, task_id: str, **kwargs):
        if task_id in cls._jobs:
            job = cls._jobs[task_id]
            for key, value in kwargs.items():
                setattr(job, key, value)
            job.updated_at = datetime.now().isoformat()

    @classmethod
    def get_job(cls, task_id: str) -> Optional[JobStatus]:
        return cls._jobs.get(task_id)
```

**API endpoints:**
```python
# POST /api/courses/<id>/textbook/generate
# Returns: {"task_id": "textbook_a3f2c1b4"}

# GET /api/jobs/<task_id>
# Returns: {
#   "status": "running",
#   "progress": 0.6,
#   "current_step": "Generating section 3 of 5"
# }
```

**Pattern basis:**
- [Python async job tracking patterns](https://testdriven.io/blog/developing-an-asynchronous-task-queue-in-python/) (2025)
- [Background task status tracking](https://help.pythonanywhere.com/pages/AsyncInWebApps/) (common web pattern)

**Migration path to Celery (Phase 8+):**
When multi-user load requires distributed processing, replace JobTracker with Celery tasks:
1. Install celery + redis
2. Define Celery tasks with @app.task decorator
3. Replace JobTracker.create_job() with task.delay()
4. Keep same API surface (task_id, status polling)

### Pattern 3: Section-Level Coherence Validation
**What:** Validate generated sections for contradictions, term consistency, redundancy
**When to use:** After generating all sections, before returning final chapter
**Techniques:**
1. **Term consistency**: Check glossary term definitions match usage in sections
2. **Fact checking**: No contradictory statements across sections (use LLM to check)
3. **Redundancy detection**: Flag near-duplicate content (sentence embeddings)

**Implementation approach:**
```python
# src/utils/coherence_validator.py
class CoherenceValidator:
    def check_consistency(self, sections: List[TextbookSection], glossary: List[GlossaryTerm]) -> List[str]:
        issues = []

        # Check 1: Term usage matches glossary definitions
        issues.extend(self._check_term_consistency(sections, glossary))

        # Check 2: No contradictions (LLM-based)
        issues.extend(self._check_contradictions(sections))

        # Check 3: No excessive redundancy
        issues.extend(self._check_redundancy(sections))

        return issues

    def _check_contradictions(self, sections: List[TextbookSection]) -> List[str]:
        # Use Claude to check for contradictions
        prompt = f"""Review these textbook sections for contradictions:

        {format_sections(sections)}

        List any contradictory statements between sections."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse response for contradictions
        return parse_contradictions(response.content[0].text)
```

**Research basis:**
- [G-Eval for LLM coherence evaluation](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation) (2026)
- [Coreference resolution for entity consistency](https://neurosys.com/blog/intro-to-coreference-resolution-in-nlp) (NLP technique)

### Pattern 4: Glossary Term Extraction
**What:** Automatically identify key terms and generate definitions from chapter content
**When to use:** After all sections generated, extract domain-specific terminology
**Approach:** LLM-based extraction (simpler and more accurate than NLP pipelines for educational content)

**Implementation:**
```python
# src/utils/glossary_extractor.py
from pydantic import BaseModel, Field
from typing import List

class GlossaryTerm(BaseModel):
    term: str = Field(description="The term or concept")
    definition: str = Field(description="Clear, concise definition (1-2 sentences)")
    context: str = Field(description="Example usage from the chapter")

class GlossarySchema(BaseModel):
    terms: List[GlossaryTerm] = Field(
        min_length=5,
        max_length=20,
        description="Key terms from the chapter"
    )

def extract_glossary(chapter_text: str, learning_outcome: str) -> GlossarySchema:
    """Extract glossary terms from chapter using LLM."""
    prompt = f"""Analyze this textbook chapter and extract key terms that students should know.

Learning Outcome: {learning_outcome}

Chapter Text:
{chapter_text}

Extract 10-15 important terms that are:
1. Domain-specific (not common words)
2. Central to understanding the learning outcome
3. Used multiple times in the chapter
4. Require definition for clarity

For each term, provide a clear definition and example from the text."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": GlossarySchema.model_json_schema()
            }
        }
    )

    return GlossarySchema.model_validate_json(response.content[0].text)
```

**Research basis:**
- [Automatic glossary extraction using NLP](https://blog.paperspace.com/adaptive-testing-and-debugging-of-nlp-models-research-paper-explained/) (domain-independent models)
- [Terminology extraction from textbooks](https://en.wikipedia.org/wiki/Terminology_extraction) (established NLP subtask)

### Pattern 5: Image Placeholder Generation
**What:** Suggest strategic image placements with captions and accessibility descriptions
**When to use:** After section generation, identify where visuals would enhance learning
**Output:** Structured placeholders with figure numbers, captions, alt text

**Implementation:**
```python
class ImagePlaceholder(BaseModel):
    figure_number: str = Field(description="Figure number (e.g., 'Figure 6.1')")
    caption: str = Field(description="1-2 sentence caption describing the figure")
    alt_text: str = Field(description="Accessibility description for screen readers")
    suggested_type: str = Field(description="Type: diagram, chart, photo, screenshot, illustration")
    placement_after: str = Field(description="Place after this paragraph (first 20 chars)")

class ImageSuggestionSchema(BaseModel):
    suggestions: List[ImagePlaceholder] = Field(
        min_length=2,
        max_length=8,
        description="Image placement suggestions for the chapter"
    )
```

**Caption format (educational best practices):**
- Figure number + chapter prefix (e.g., "Figure 6.1")
- One to two sentences contextualizing the image
- No punctuation between label and description
- Alt text separately for accessibility (screen readers)

**Research basis:**
- [Educational textbook caption guidelines](https://ecampusontario.pressbooks.pub/authoringguide/chapter/images-adding-captions-attributions-and-citations/) (Queen's Open Textbook Guide)
- [Figure captions vs alt text](https://openoregon.pressbooks.pub/dothework/chapter/3-2-strategies-and-examples/) (accessibility best practices)

### Anti-Patterns to Avoid
- **Single-shot 3000-word generation**: Risks token limits and poor coherence. Use hierarchical expansion instead.
- **No progress feedback**: Multi-minute jobs frustrate users. Implement job tracking from start.
- **Ignoring coherence validation**: Long-form content needs consistency checks. Use LLM-based validation.
- **Hard-coding glossary extraction**: Let Claude identify domain terms dynamically based on learning outcome.
- **Skipping image suggestions**: Visual aids critical for learning; include placeholders even if not generating actual images.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| APA 7 citation formatting | Custom citation parser | Existing ReadingGenerator pattern + prompt guidance | APA 7 format well-documented; Claude follows guidelines reliably with examples in system prompt |
| Token counting for chunking | Custom tokenizer | Anthropic's official token counter (anthropic.count_tokens) | Official counter matches Claude's internal tokenization |
| Distributed task queues (Phase 8+) | Custom queue implementation | Celery + Redis | Battle-tested, handles retries, failure recovery, distributed workers |
| Glossary term extraction | spaCy NER + custom rules | LLM-based extraction with structured output | Educational terms are context-dependent; LLM understands pedagogical relevance better than NER |
| Section similarity detection (for redundancy) | Manual TF-IDF cosine similarity | sentence-transformers (if needed in future) | Pre-trained embeddings better capture semantic similarity than TF-IDF |

**Key insight:** For Phase 6, maximize use of established patterns (BaseGenerator, structured outputs, simple job tracking). Defer complex infrastructure (Celery, Redis, advanced NLP) until proven necessary in Phase 8+ with multi-user load.

## Common Pitfalls

### Pitfall 1: Token Limit Exceeded on Single-Shot Generation
**What goes wrong:** Attempting to generate entire 3000-word chapter in one API call hits token limits (~4000 tokens) or produces poor coherence
**Why it happens:** 3000 words ≈ 4000 tokens; some models have 4096 token limits; even with higher limits, long outputs lose coherence
**How to avoid:**
- Use hierarchical expansion (outline first, then sections)
- Keep per-section generation to 500-600 words (~650-800 tokens)
- Budget total chapter as 5-8 sections, not single blob
**Warning signs:** API errors about token limits, rambling or repetitive content in long outputs

### Pitfall 2: No User Feedback During Long Generation
**What goes wrong:** User waits 2-3 minutes with no progress indication, assumes app is frozen, refreshes page and loses work
**Why it happens:** Textbook generation is 5-8 API calls sequentially; each takes 20-40 seconds
**How to avoid:**
- Return task_id immediately on POST /generate
- Provide GET /jobs/<task_id> endpoint for status polling
- Update progress after each major step (outline, each section, glossary, validation)
- Client polls every 1-2 seconds and shows progress bar
**Warning signs:** User complaints about app "hanging", frequent page refreshes during generation

### Pitfall 3: Glossary Terms Don't Match Usage
**What goes wrong:** Glossary defines "machine learning" but chapter uses "ML" abbreviation; inconsistent terminology confuses students
**Why it happens:** Separate glossary generation doesn't validate term usage in sections
**How to avoid:**
- Extract glossary AFTER sections are generated (not in parallel)
- Validate term consistency: check each glossary term appears in chapter text
- Prompt Claude to include both full term and common abbreviations
- CoherenceValidator checks term definitions match actual usage
**Warning signs:** Glossary has terms never used in chapter; students report confusing terminology

### Pitfall 4: Contradictory Statements Across Sections
**What goes wrong:** Section 2 says "X is always true" but Section 5 says "X is false in certain cases"; students get conflicting information
**Why it happens:** Each section generated independently without awareness of other sections' content
**How to avoid:**
- Pass full outline + previous sections as context for each new section
- Run coherence validation step after all sections generated
- Use LLM to check for contradictions: "Review these sections and identify any contradictory claims"
- Flag issues for human review before returning chapter
**Warning signs:** High refine/regeneration rate, user feedback about contradictions

### Pitfall 5: Image Placeholders Too Generic
**What goes wrong:** Suggestions like "Add diagram here" without specific caption or context; instructor can't tell what image would be useful
**Why it happens:** Treating image suggestions as afterthought; not grounding in chapter content
**How to avoid:**
- Generate image suggestions WITH specific captions based on chapter content
- Include figure number, caption, alt text, and suggested type (diagram vs photo vs chart)
- Reference specific paragraph for placement (anchor text)
- Prompt Claude to suggest images that support learning outcome, not just decoration
**Warning signs:** Generic placeholders ignored by users; no images added to final materials

### Pitfall 6: Excessive Redundancy Between Sections
**What goes wrong:** Introduction repeats in Section 1; Section 3 and Section 5 say the same thing differently; chapter feels padded
**Why it happens:** Each section prompt doesn't constrain scope; no deduplication check
**How to avoid:**
- Outline prompt specifies distinct sub-topics for each section
- Pass "covered so far" summary when generating later sections
- Coherence validator checks for near-duplicate content (sentence similarity)
- Aim for 400-600 words per section (not 800+) to prevent padding
**Warning signs:** Chapters consistently exceed 3500 words, user complaints about repetitive content

## Code Examples

Verified patterns from Claude API documentation and established codebase patterns:

### Hierarchical Outline Generation
```python
# src/generators/textbook_generator.py
from pydantic import BaseModel, Field
from typing import List

class SectionOutline(BaseModel):
    title: str = Field(description="Section heading")
    description: str = Field(description="1-2 sentence overview of section content")
    estimated_words: int = Field(description="Target word count (400-600)")

class TextbookOutlineSchema(BaseModel):
    chapter_title: str = Field(description="Chapter title aligned to learning outcome")
    introduction_summary: str = Field(description="What the introduction will cover")
    sections: List[SectionOutline] = Field(
        min_length=5,
        max_length=8,
        description="Main content sections"
    )
    conclusion_summary: str = Field(description="What the conclusion will summarize")
    estimated_total_words: int = Field(description="Sum of all section estimates")

class TextbookGenerator(BaseGenerator[TextbookChapterSchema]):
    def generate_outline(self, learning_outcome: LearningOutcome, topic: str) -> TextbookOutlineSchema:
        """Generate structured outline before writing sections."""
        prompt = f"""Create a detailed outline for a textbook chapter on this learning outcome:

Learning Outcome: {learning_outcome.behavior} (Bloom's: {learning_outcome.bloom_level.value})
Topic: {topic}
Target Length: ~3000 words total

Create 5-8 main sections that:
1. Build progressively from foundational to advanced concepts
2. Each section covers ONE distinct sub-topic
3. No overlap or redundancy between sections
4. Support the learning outcome with relevant examples
5. Total to approximately 3000 words

Provide section titles, descriptions, and estimated word counts."""

        outline, _ = self.generate(
            schema=TextbookOutlineSchema,
            learning_objective=str(learning_outcome),
            topic=topic
        )
        return outline
```

### Section-by-Section Generation with Context
```python
class TextbookSection(BaseModel):
    heading: str = Field(description="Section heading from outline")
    content: str = Field(description="Section body text (400-600 words)")
    key_concepts: List[str] = Field(description="Main concepts covered in this section")

def generate_section(
    self,
    section_outline: SectionOutline,
    chapter_context: str,
    previous_sections: List[TextbookSection]
) -> TextbookSection:
    """Generate single section with full chapter context."""

    # Build context from previous work
    covered_concepts = []
    for prev in previous_sections:
        covered_concepts.extend(prev.key_concepts)

    prompt = f"""Write the following section for a textbook chapter:

Chapter Context:
{chapter_context}

Section to Write:
Title: {section_outline.title}
Description: {section_outline.description}
Target Length: {section_outline.estimated_words} words

Already Covered: {', '.join(covered_concepts)}

Requirements:
1. Write ONLY this section, not introduction or other sections
2. Build on concepts already covered
3. Do NOT repeat information from previous sections
4. Include specific examples relevant to this section
5. Target {section_outline.estimated_words} words (no padding)
6. Write at appropriate academic level
7. Use clear topic sentences and transitions"""

    section, _ = self.generate(
        schema=TextbookSection,
        section_outline=section_outline,
        chapter_context=chapter_context,
        covered_concepts=covered_concepts
    )
    return section
```

### Progress Tracking During Generation
```python
# src/api/textbook.py
from src.api.job_tracker import JobTracker

@textbook_bp.route("/courses/<course_id>/textbook/generate", methods=["POST"])
def generate_textbook_chapter(course_id):
    """Generate textbook chapter with progress tracking."""
    data = request.get_json()
    learning_outcome_id = data.get("learning_outcome_id")
    topic = data.get("topic")

    # Create job for tracking
    task_id = JobTracker.create_job("textbook")

    # Start generation in background (simple threading for Phase 6)
    def generate_with_progress():
        try:
            JobTracker.update_job(
                task_id,
                status="running",
                progress=0.1,
                current_step="Generating chapter outline"
            )

            # Step 1: Outline
            outline = generator.generate_outline(learning_outcome, topic)

            JobTracker.update_job(
                task_id,
                progress=0.2,
                current_step="Writing introduction"
            )

            # Step 2: Introduction
            intro = generator.generate_introduction(outline)

            # Step 3: Sections (update progress incrementally)
            sections = []
            section_count = len(outline.sections)
            for i, section_outline in enumerate(outline.sections):
                JobTracker.update_job(
                    task_id,
                    progress=0.2 + 0.5 * (i / section_count),
                    current_step=f"Writing section {i+1} of {section_count}: {section_outline.title}"
                )
                section = generator.generate_section(section_outline, outline, sections)
                sections.append(section)

            JobTracker.update_job(
                task_id,
                progress=0.7,
                current_step="Extracting glossary terms"
            )

            # Step 4: Glossary
            glossary = glossary_extractor.extract_glossary(
                chapter_text=format_chapter(intro, sections),
                learning_outcome=str(learning_outcome)
            )

            JobTracker.update_job(
                task_id,
                progress=0.8,
                current_step="Suggesting image placements"
            )

            # Step 5: Image placeholders
            images = generator.suggest_images(intro, sections)

            JobTracker.update_job(
                task_id,
                progress=0.9,
                current_step="Validating coherence"
            )

            # Step 6: Coherence check
            issues = coherence_validator.check_consistency(sections, glossary)
            if issues:
                # Log issues but don't fail; include in metadata
                pass

            # Step 7: Finalize
            chapter = TextbookChapter(
                title=outline.chapter_title,
                sections=[{
                    "heading": s.heading,
                    "body": s.content
                } for s in sections],
                glossary_terms=[{
                    "term": t.term,
                    "definition": t.definition
                } for t in glossary.terms],
                word_count=calculate_word_count(intro, sections),
                learning_outcome_id=learning_outcome_id
            )

            # Save to course
            course = project_store.load_course(course_id)
            course.textbook_chapters.append(chapter)
            project_store.save_course(course)

            JobTracker.update_job(
                task_id,
                status="completed",
                progress=1.0,
                current_step="Chapter generation complete",
                result=chapter.to_dict()
            )

        except Exception as e:
            JobTracker.update_job(
                task_id,
                status="failed",
                error=str(e)
            )

    # Run in background thread (simple for Phase 6)
    import threading
    thread = threading.Thread(target=generate_with_progress)
    thread.start()

    return jsonify({"task_id": task_id}), 202


@textbook_bp.route("/jobs/<task_id>", methods=["GET"])
def get_job_status(task_id):
    """Poll job status for progress updates."""
    job = JobTracker.get_job(task_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "task_id": job.task_id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "result": job.result,
        "error": job.error
    })
```

### APA 7 Citation Integration (Reuse Existing Pattern)
```python
# Already implemented in ReadingGenerator - reuse directly
# src/generators/schemas/textbook.py
from src.generators.schemas.reading import Reference  # Reuse existing Reference model

class TextbookChapterSchema(BaseModel):
    chapter_number: int = Field(description="Chapter number in sequence")
    title: str = Field(description="Chapter title")
    introduction: str = Field(description="Opening section (100-150 words)")
    sections: List[TextbookSection]
    conclusion: str = Field(description="Closing summary (100-150 words)")
    references: List[Reference] = Field(  # Reuse from ReadingSchema
        min_length=3,
        max_length=10,
        description="APA 7 references for chapter"
    )
    glossary_terms: List[GlossaryTerm]
    image_placeholders: List[ImagePlaceholder]
    learning_outcome_id: str

# System prompt includes APA 7 examples (copy from ReadingGenerator)
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-shot long-form generation | Hierarchical expansion (outline → sections) | 2025 research | Better coherence, avoids token limits, proven by OpenCredo |
| Manual glossary creation | LLM-based term extraction with structured outputs | 2025-2026 | Automated, context-aware term identification |
| Hard-coded progress tracking | Dynamic job status with polling | Standard web pattern | User feedback during long operations |
| Numeric rubrics (5-point scales) | 3-level rubrics (Below/Meets/Exceeds) | Phase 4 decision | Already established in codebase |
| Custom NLP pipelines for term extraction | LLM-based structured outputs | 2025+ | Simpler, more accurate for educational content |

**Deprecated/outdated:**
- **response_format parameter**: Replaced by output_config.format in Anthropic SDK 0.77.0+
- **Single-shot 3000-word generation**: Hierarchical expansion now standard for long-form content
- **Celery for all async tasks**: Overkill for single-user Phase 6; in-memory queue sufficient

## Open Questions

Things that couldn't be fully resolved:

1. **Image generation integration**
   - What we know: Phase 6 generates placeholders with captions; actual image generation deferred to future phase
   - What's unclear: Will future phase use DALL-E, Midjourney, or stock photo recommendations?
   - Recommendation: Keep placeholder format generic (figure_number, caption, alt_text, suggested_type); don't couple to specific image generation API

2. **Coherence validation threshold**
   - What we know: LLM can identify contradictions between sections
   - What's unclear: Should generation fail if contradictions found, or just flag for review?
   - Recommendation: Log issues in metadata but don't block generation in Phase 6; add blocking validation in Phase 7 QA if needed

3. **Glossary term count heuristic**
   - What we know: Educational best practice is 10-15 terms per chapter
   - What's unclear: Should term count scale with chapter length (3000 vs 5000 words)?
   - Recommendation: Start with fixed 10-15 range; adjust based on user feedback in Phase 7

4. **Job queue persistence**
   - What we know: In-memory dictionary works for Phase 6 single-user
   - What's unclear: When to migrate to Redis-backed Celery (Phase 8? Phase 9?)
   - Recommendation: Add to Phase 8 scope when multi-user collaboration requires distributed task processing

5. **Section chunking strategy for very long chapters**
   - What we know: 5-8 sections works well for 3000-word chapters
   - What's unclear: If future requirements allow 5000-word chapters, how many sections?
   - Recommendation: Enforce 3000-word target in Phase 6; revisit chunking strategy if requirements change

## Sources

### Primary (HIGH confidence)
- [Claude Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Official API documentation for output_config parameter
- Existing codebase patterns - BaseGenerator, ReadingGenerator, all 11 content type schemas (verified working)
- [State of the Art 2026 LLM Content](https://medium.com/@vforqa/llm-development-in-2026-transforming-ai-with-hierarchical-memory-for-deep-context-understanding-32605950fa47) - Hierarchical memory research

### Secondary (MEDIUM confidence)
- [Hierarchical Expansion Technique](https://www.opencredo.com/blogs/how-to-use-llms-to-generate-coherent-long-form-content-using-hierarchical-expansion) - OpenCredo 2025 blog post (403 error on fetch, but content found via WebSearch)
- [LLM Content Strategy 2026](https://fibr.ai/geo/llm-content-optimization-best-practices-2026) - Best practices for long-form generation
- [Chunking Strategies Guide](https://www.pinecone.io/learn/chunking-strategies/) - Comprehensive chunking approaches
- [Python Async Task Queue Development](https://testdriven.io/blog/developing-an-asynchronous-task-queue-in-python/) - Implementation patterns
- [Educational Textbook Caption Guidelines](https://ecampusontario.pressbooks.pub/authoringguide/chapter/images-adding-captions-attributions-and-citations/) - Queen's Open Textbook Guide
- [Figure Captions vs Alt Text](https://openoregon.pressbooks.pub/dothework/chapter/3-2-strategies-and-examples/) - Accessibility best practices

### Tertiary (LOW confidence - marked for validation)
- [G-Eval for LLM Coherence](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation) - Modern evaluation techniques (vendor blog, cross-verify)
- [Automatic Glossary Extraction](https://blog.paperspace.com/adaptive-testing-and-debugging-of-nlp-models-research-paper-explained/) - NLP techniques (paper summary, not primary source)
- [Terminology Extraction Wikipedia](https://en.wikipedia.org/wiki/Terminology_extraction) - General overview (Wikipedia, verify with academic sources)

### Not Accessible (403 errors)
- OpenCredo hierarchical expansion blog (found via search, content unavailable via WebFetch)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already in project; no new libraries required
- Architecture: MEDIUM - Hierarchical expansion verified in research; job tracking pattern standard but not tested in this codebase
- Pitfalls: MEDIUM - Based on LLM content generation research and common async job issues; not specific to textbook generation
- Coherence validation: LOW - LLM-based validation approach sound but not empirically tested for this use case

**Research date:** 2026-02-04
**Valid until:** 60 days (stable domain - long-form generation patterns mature; no rapid API changes expected)

**Next steps for planner:**
1. Create 06-01-PLAN: TextbookGenerator with hierarchical expansion (outline → sections → assembly)
2. Create 06-02-PLAN: Coherence validation and cross-reference checking
3. Create 06-03-PLAN: Glossary generation and term extraction
4. Create 06-04-PLAN: Image placeholder generation with captions
5. Create 06-05-PLAN: APA 7 citation integration (reuse ReadingGenerator patterns)
6. Create 06-06-PLAN: Job tracking API with progress updates

**Key architectural decisions for planner:**
- Reuse BaseGenerator pattern with Generic[T] type safety
- Reuse Reference model from ReadingSchema for APA 7 citations
- Implement simple in-memory JobTracker (defer Celery to Phase 8+)
- Use threading.Thread for background generation (single-user sufficient for Phase 6)
- Schema validation via Pydantic with output_config.format (established pattern)
- Follow TDD RED-GREEN-REFACTOR with mocked Anthropic API (established pattern)
