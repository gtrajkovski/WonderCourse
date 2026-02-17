# Project Research Summary

**Project:** Course Builder Studio
**Domain:** AI-Powered Course Authoring Platform (Coursera Short Courses)
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

Course Builder Studio is an AI-powered platform for generating comprehensive Coursera short courses from learning outcomes. Research shows this is a specialized educational content generation domain requiring a robust tech stack (Flask + Claude API), comprehensive content suite (11 content types), and rigorous quality validation to address AI hallucination risks. The recommended approach is a phased build starting with core infrastructure and basic content types, then expanding to the full suite of 11 content types, followed by holistic validation and export capabilities.

The product differentiates by validating against Coursera-specific requirements (30-180 min duration, specific content distribution, outcome coverage) and generating ALL required content types (scripts, readings, quizzes, HOL activities, coach dialogues, labs, discussions, assignments, projects, rubrics, textbooks) versus competitors who generate only scripts and quizzes. The human-in-the-loop quality gates are essential given 15%+ AI hallucination rates in educational content.

Key risks center on AI quality issues (hallucinations, prompt inconsistency, quiz distractor quality, Bloom's misalignment) and technical challenges (state management race conditions, SCORM export validation, textbook coherence). Mitigation requires building validation infrastructure early, implementing file locking for concurrent operations, using low temperature for consistency, and enforcing human review gates before export. Research indicates a 6-8 week build following a foundation-first approach with incremental content type additions.

## Key Findings

### Recommended Stack

Python 3.10+ with Flask 3.1.2 provides the foundation for this web-based content generation platform. The stack prioritizes proven libraries optimized for AI orchestration and document generation. Critical version note: Python 3.9 reached EOL in October 2025 and pytest 9.x dropped support, making 3.10+ mandatory.

**Core technologies:**
- **Flask 3.1.2**: Lightweight web framework with excellent extension ecosystem, perfect for server-rendered HTML with progressive enhancement before React migration
- **Anthropic SDK 0.77.0+**: Official Claude API client with streaming, tool use, and prompt caching support for 70-80% cost savings on repeated system prompts
- **python-docx 1.2.0+ / docxtpl 0.18.0+**: Document generation for readings, textbook chapters, and instructor packages using template-based and programmatic approaches
- **mistune 3.0.2+**: Fast CommonMark-compliant markdown parsing for imported content
- **dataclasses (stdlib)**: Fast, type-safe data containers for Project/Course/Module/Activity models without runtime validation overhead

**Supporting stack:**
- **pytest 9.0.2+** with pytest-flask and pytest-mock for testing (800+ tests expected)
- **ruff 0.10.0+**: 10-100x faster than Black/Flake8, single-tool replacement for entire Python toolchain
- **Flask-CORS 6.0.2+**: Cross-origin support if frontend migrates to separate domain

**What NOT to use:**
- SQLAlchemy/databases (unnecessary for disk-based JSON persistence)
- Pydantic (6.46x slower than dataclasses for trusted internal data)
- Python 3.9 (EOL, pytest incompatibility)
- React in Phase 1 (defer to later milestone per constraints)

### Expected Features

**Must have (table stakes):**
- **AI Content Generation (11 types)**: Video scripts (WWHAA), readings, quizzes, HOL activities, coach dialogues, labs, discussions, assignments, projects, rubrics, textbook chapters — bulk generation must work in single workflow
- **Learning Outcome Management**: ABCD model support, Bloom's taxonomy levels, outcome-to-content mapping, coverage tracking
- **Coursera Validation Engine**: Duration (30-180 min), module count (4-8), content distribution ratios, outcome coverage verification
- **Build State Management**: Draft→generating→generated→reviewed→approved→published workflow with validation gates preventing premature publishing
- **Human Review Interface**: Approve/reject/edit per content block, commenting, regeneration requests to address AI hallucination risk
- **LMS Export (SCORM/xAPI)**: Package content for LMS delivery with manifest validation and resource reference checking
- **Version Control & Audit Trail**: Change tracking for compliance/accreditation, rollback capability, approval workflow history
- **Accessibility Compliance (WCAG 2.1 AA)**: Captions/transcripts, audio descriptions, ARIA labels (US DOJ 2024 rule mandates April 2026)
- **Multi-User Collaboration**: Team-based workflows (SMEs, instructional designers, reviewers) with role-based permissions
- **Template Library**: Reusable course structure and content block templates for rapid creation
- **Content Reusability**: Segment library with tagging/search, cross-project import, template creation from existing content

**Should have (competitive differentiators):**
- **Coursera-Specific Validation**: Only platform validating actual Coursera requirements vs generic SCORM export
- **Instructional Design AI Coach**: Proactive pedagogical suggestions during development, not just content generation
- **Comprehensive Content Suite**: All 11 Coursera content types vs competitors' 2-3 types
- **APA 7 Citation Engine**: Automated citation generation for readings with proper formatting
- **Rubric Generation**: Auto-generate scoring rubrics for assignments and HOL activities
- **Human-in-the-Loop Quality Gates**: Structured review with quality thresholds before advancement
- **Outcome Coverage Validation**: Ensures every learning outcome is covered with appropriate Bloom's alignment
- **Instructor Package Export**: Complete export for instructors (guides, answer keys, rubrics, solutions) separate from student content
- **Cross-Content Consistency Validation**: Term consistency, tone consistency, complexity level alignment across all content types

**Defer (v2+):**
- **Analytics & Learner Insights**: Requires learner data from LMS integration
- **AI Instructional Design Coach**: High complexity, requires deep knowledge base (start with validation first)
- **Custom AI Models per Organization**: Expensive, increases hallucination risk (address with style guides and prompt engineering)
- **Video Production Integration**: Scope creep into production (focus on content, partner with video platforms)
- **Textbook Generator**: High complexity (~3000 words per outcome, academic quality bar) — may be P2 vs P3
- **Mobile App**: Course authoring is desktop work

### Architecture Approach

A layered architecture with plugin-based generators supports the 11 content types while maintaining separation of concerns. The web layer (Flask routes/templates) sits above a generation orchestration layer that coordinates multi-step workflows using a state machine. Individual generator plugins (VideoScriptGenerator, ReadingGenerator, etc.) implement a common interface with generate(), validate(), and improve() methods. An AI orchestration layer routes requests to appropriate models (fast vs capable) based on complexity, reducing costs by 60-70%. Holistic validators run after generation to check cross-content properties like outcome coverage and Bloom's distribution.

**Major components:**
1. **Generator Plugin Layer**: Each of 11 content types has dedicated generator implementing BaseGenerator interface — enables independent development and testing
2. **AI Orchestration with Model Routing**: Route simple tasks to fast/cheap models (Haiku), complex tasks to capable models (Sonnet 4) based on heuristics
3. **Two-Phase Validation**: Individual validators (WWHAA structure, quiz format) run during generation; holistic validators (outcome coverage, cognitive load, accessibility) run on full course
4. **RAG-Enhanced Generation**: Inject Coursera style guides, instructional design best practices, and example content to reduce hallucinations and improve consistency
5. **Build State Machine**: Explicit state transitions (draft→generating→generated→reviewed→approved→published) with rollback capability and audit logging
6. **ProjectStore with File Locking**: Disk-based JSON persistence with file locking to prevent race conditions during concurrent writes

**Key patterns:**
- Generator plugin architecture for extensibility (add content types without modifying existing code)
- Incremental validation (check partial coverage during generation to guide toward valid state, not just validate at end)
- Transactional builds (write to temporary directory, commit only on full success with rollback capability)
- Prompt versioning and metadata storage (store prompt_template_id, variables, model with each generation for reproducibility)
- Async job pattern for long-running operations (textbook generation, blueprint creation) with progress tracking

### Critical Pitfalls

1. **AI Hallucination in Educational Content** — LLMs generate plausible but factually incorrect information. In education, this is catastrophic. **Avoid by:** implementing hallucination detection (GPTZero or similar), using RAG to ground in verified sources, two-stage validation (static + LLM-as-judge), never publishing without human expert review, and adding fact-check phase before export. Address in Phase 1 (validation hooks) and Phase 3 (automated detection).

2. **Prompt Inconsistency Leading to Quality Drift** — Different prompts produce wildly inconsistent quality across learning outcomes. **Avoid by:** using low temperature (0.2-0.4) and low top-p (<0.5) for consistency, creating versioned prompt library, implementing prompt regression testing, using Chain-of-Thought for transparency, and freezing prompt versions during build cycles. Address in Phase 1 (prompt engineering foundation) and Phase 2 (consistency checks across 11 types).

3. **Quiz Distractor Quality Issues** — AI generates distractors that are either obviously wrong or technically correct, destroying assessment validity. **Avoid by:** implementing distractor quality checker, using student mistake modeling (distractors reflect common errors), validating answer distribution, enforcing option-level feedback requirements, and testing Bloom's alignment. Address in Phase 2 (quiz generation) and Phase 3 (automated quality checks).

4. **Bloom's Taxonomy Misalignment** — Learning outcomes claim "Analyze" level but quizzes only test "Remember" level. **Avoid by:** using RoBERTa classifier for validation (87%+ accuracy), implementing outcome→assessment mapping, building taxonomy ladder (explicit question generation at each level), and requiring human review of alignment. Address in Phase 1 (content generation) and Phase 3 (alignment validation).

5. **State Management Race Conditions** — Parallel generation of 11 content types causes file write collisions, corrupting project.json. **Avoid by:** implementing file locking (fcntl.flock on Unix, msvcrt.locking on Windows), using advisory locking protocol, implementing write-ahead logging, serializing writes via queue, adding integrity checks, and retry logic with exponential backoff. Address in Phase 1 (core infrastructure).

**Additional risks:**
- SCORM/LMS export validation failures (manifest structure, resource references, schema versions) — address in Phase 4 (export & packaging)
- Textbook coherence collapse over 3000-word sections (repetition, contradictions, broken cross-references) — address in Phase 2 (hierarchical generation with memory)
- Build pipeline failure without rollback (partial writes, no resume capability) — address in Phase 1 (transactional builds)

## Implications for Roadmap

Based on research, suggested phase structure with 6-8 week timeline:

### Phase 1: Foundation & Core Infrastructure (Week 1)
**Rationale:** All generators depend on models, storage, AI client, and state tracking. Must be rock-solid before content generation. File locking critical to prevent race conditions from parallel generation.

**Delivers:**
- Core models (Course, Module, Lesson, Activity dataclasses with to_dict/from_dict)
- ProjectStore with path safety and file locking
- Flask app skeleton (routes structure, templates)
- AI client abstraction with prompt versioning
- Build state tracker (draft→generating→generated)
- Validation hooks infrastructure

**Addresses features:**
- Build State Management (table stakes)
- Learning Outcome Management foundation
- Multi-User Collaboration data model

**Avoids pitfalls:**
- State Management Race Conditions (file locking implementation)
- Prompt Inconsistency (versioned prompts, temperature/top-p enforcement)

**Research flag:** Standard Flask patterns, low research needed

### Phase 2: Basic Content Generation (Week 2-4)
**Rationale:** Start with 4 core types (scripts, readings, quizzes, rubrics) covering 80% of course content before expanding to all 11. Proves AI generation workflow and validation before scaling complexity.

**Delivers:**
- BaseGenerator abstract class
- VideoScriptGenerator (WWHAA structure validation)
- ReadingGenerator (APA 7 citations)
- QuizGenerator (MCQ with distractor quality checks)
- RubricGenerator
- UI for generation triggers and results viewing

**Addresses features:**
- AI Content Generation core types (table stakes)
- APA 7 Citation Engine (differentiator)
- Rubric Generation (differentiator)

**Avoids pitfalls:**
- AI Hallucination (validation hooks in place)
- Quiz Distractor Quality (distractor quality checker)
- Prompt Inconsistency (consistent temperature/top-p across generators)

**Research flag:** WWHAA structure parsing, APA 7 citation formatting may need specific research

### Phase 3: Expanded Content Types (Week 3-4, parallel with Phase 2)
**Rationale:** Remaining 7 content types (HOL, coach, lab, discussion, assignment, project, textbook) can be built in parallel once BaseGenerator exists. Textbook is most complex (3000 words, coherence risk).

**Delivers:**
- HOLGenerator (scenario-based activities)
- CoachGenerator (8-section AI conversations)
- LabGenerator
- DiscussionGenerator
- AssignmentGenerator
- ProjectMilestoneGenerator
- TextbookGenerator (hierarchical generation with chapter memory)

**Addresses features:**
- AI Content Generation full suite (table stakes + differentiator)
- Comprehensive Content Suite (differentiator)

**Avoids pitfalls:**
- Textbook Coherence Collapse (hierarchical generation, cross-reference validation)

**Research flag:** Textbook generation needs deep research on coherence patterns and chunking strategies

### Phase 4: Blueprint & Orchestration (Week 5)
**Rationale:** Blueprint generates full course structure from high-level input, requiring all Activity generators to exist. AI router optimizes costs. Orchestrator coordinates multi-step workflows.

**Delivers:**
- BlueprintGenerator (course structure from learning outcomes)
- AI Router (model selection: Haiku for simple, Sonnet for complex)
- Generation orchestrator (multi-step workflow coordination)
- RAG context injection (style guides, examples)

**Addresses features:**
- Bulk Content Generation (table stakes)
- Coursera Validation Engine foundation

**Avoids pitfalls:**
- Prompt Inconsistency (AI router ensures consistent model selection)

**Research flag:** Blueprint generation patterns need research — complex orchestration

### Phase 5: Holistic Validation (Week 6)
**Rationale:** Cannot validate outcome coverage until all content exists. Validation dashboard shows gaps before export. This is the key differentiator vs competitors.

**Delivers:**
- OutcomeMapper (coverage analysis, Bloom's distribution)
- CognitiveLoadAnalyzer
- AccessibilityChecker (WCAG 2.1 AA)
- DistractorQualityChecker
- WWHAAValidator (distribution across course)
- Validation dashboard UI

**Addresses features:**
- Coursera Validation Engine (table stakes + differentiator)
- Outcome Coverage Validation (differentiator)
- Cross-Content Consistency Validation (differentiator)
- Accessibility Compliance (table stakes)

**Avoids pitfalls:**
- Bloom's Taxonomy Misalignment (RoBERTa classifier validation)
- AI Hallucination (fact-check phase before export)

**Research flag:** RoBERTa classifier integration, WCAG 2.1 AA compliance testing may need specific research

### Phase 6: Export & Polish (Week 7-8)
**Rationale:** Export depends on validated content. SCORM manifests have strict requirements — must validate before ZIP creation. Background jobs needed for long-running textbook generation.

**Delivers:**
- InstructorPackageExporter (ZIP with syllabus, rubrics, answer keys)
- LMSManifestExporter (SCORM 1.2, xAPI with manifest validation)
- Background job system (Celery + Redis for async generation)
- Iterative improver (feedback→regenerate→rescore loop)
- Final UI polish (progress indicators, dark theme)

**Addresses features:**
- LMS Export (table stakes)
- Instructor Package Export (differentiator)
- Version Control foundation

**Avoids pitfalls:**
- SCORM Validation Failures (pre-export manifest checks)
- Build Pipeline Failure (transactional builds, rollback)

**Research flag:** SCORM manifest validation, Coursera-specific packaging requirements need research

### Phase Ordering Rationale

**Foundation-first approach:** Core models and ProjectStore enable all generators. Building infrastructure before content generation prevents rework when architectural issues emerge.

**Incremental content expansion:** Start with 4 core types (Week 2) to prove generation workflow, then add remaining 7 types (Week 3-4) once pattern is established. Reduces risk of building 11 generators before validating approach.

**Validation after content:** Holistic validators (outcome coverage, cognitive load) require full course to analyze. Building these before generators would mean no test data.

**Export last:** Requires all content types generated, validated, and approved. SCORM packaging depends on content stability.

**Parallel opportunities:** HOL/coach/lab/discussion/assignment/project generators can be built simultaneously once BaseGenerator exists (Week 3-4). Validation components can be built in parallel (Week 6).

**Critical path:** Models → ProjectStore → AI client → BaseGenerator → VideoScriptGenerator → Blueprint → Validation → Export. Everything else branches from this spine.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 3 (Textbook Generator):** Complex coherence requirements, 3000-word generation chunking strategies, cross-reference validation patterns — sparse documentation
- **Phase 4 (Blueprint Generator):** Course structure generation from minimal input, orchestration patterns for 11 content types — niche domain
- **Phase 5 (RoBERTa Bloom's Classifier):** Integration with HuggingFace models, accuracy tuning, training data requirements — specialized ML integration
- **Phase 6 (SCORM/Coursera Export):** Coursera-specific manifest requirements beyond standard SCORM, validation testing with actual Coursera upload — proprietary platform

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Flask Infrastructure):** Well-documented patterns, ProjectStore similar to ScreenCast Studio
- **Phase 2 (Basic Generators):** Straightforward AI client usage, documented in ScreenCast Studio
- **Phase 5 (Accessibility Checker):** WCAG 2.1 AA is well-documented standard
- **Phase 6 (Background Jobs):** Celery + Redis is established pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI/official docs, established patterns, proven in ScreenCast Studio |
| Features | HIGH | Multiple competitor analysis sources, Coursera official docs, feature matrix validated |
| Architecture | HIGH | Established patterns (plugin architecture, RAG, state machines), research from credible sources |
| Pitfalls | HIGH | Backed by academic research on AI hallucination, distractor generation, practical SCORM troubleshooting |

**Overall confidence:** HIGH

### Gaps to Address

**During planning/execution:**

1. **Coursera-specific export requirements:** Research identified general SCORM patterns but Coursera may have proprietary requirements beyond standard. **Handle by:** requesting Coursera documentation during Phase 6 planning or testing with actual Coursera upload before production.

2. **RoBERTa classifier accuracy for domain-specific content:** 87%+ accuracy cited for general education, but accuracy on Coursera short courses unknown. **Handle by:** evaluate classifier during Phase 5 planning, potentially train on Coursera examples if accuracy insufficient.

3. **Optimal chunk size for textbook generation:** Research suggests hierarchical approach but doesn't specify token limits per section. **Handle by:** experiment during Phase 3 development, test coherence at 500/1000/1500 word chunks.

4. **Concurrent file operations on Windows vs Unix:** File locking patterns differ (fcntl.flock vs msvcrt.locking). **Handle by:** implement cross-platform locking in Phase 1, test on both dev (Windows) and potential production (Linux) environments.

5. **Distractor quality threshold calibration:** Research defines concept but doesn't specify numeric threshold (e.g., "score >80%"). **Handle by:** calibrate threshold during Phase 2 testing with sample quizzes, potentially use Coursera quiz quality benchmarks.

**Validation items:**
- Test SCORM packages with actual Coursera upload (not just validators) before Phase 6 completion
- Verify prompt caching delivers promised 70-80% cost savings with actual Claude API usage patterns
- Benchmark file locking overhead with 11 concurrent generators to ensure acceptable performance
- Validate accessibility checker catches all WCAG 2.1 AA violations via automated testing tools

## Sources

### Primary (HIGH confidence)
- Flask 3.1.2, Anthropic SDK 0.77.0, pytest 9.0.2 official documentation and PyPI pages
- WCAG 2.1 AA official specification
- ScreenCast Studio codebase (CLAUDE.md) — proven ProjectStore pattern, dual AI client pattern
- Coursera Course Builder official announcements and learning resources
- Academic research on AI hallucination detection (GPTZero), distractor generation, Bloom's taxonomy alignment

### Secondary (MEDIUM confidence)
- AI course authoring platform comparisons (Coursebox AI, CourseAI, Mini Course Generator)
- Flask architecture best practices (TestDriven.io, Auth0)
- RAG best practices (Level Up Coding, DEV Community articles)
- SCORM troubleshooting guides (Doctor eLearning, Regex.global)

### Tertiary (LOW confidence)
- AI learning platform roundups (360learning, Docebo) — used for market context, not technical decisions
- Prompt engineering guides (Analytics Vidhya, Lakera) — principles verified but specific techniques need validation
- Platform engineering anti-patterns (InfoWorld, Jellyfish) — general patterns applied to education domain

---
*Research completed: 2026-02-02*
*Ready for roadmap: yes*
