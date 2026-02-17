# Pitfalls Research

**Domain:** AI-Powered Course Authoring Platform (Coursera Short Courses)
**Researched:** 2026-02-02
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: AI Hallucination in Educational Content

**What goes wrong:**
AI generates factually incorrect information that sounds plausible but is wrong. In educational content, this is catastrophic—students learn incorrect information, instructors lose credibility, and the entire course must be recalled or corrected.

**Why it happens:**
LLMs generate text based on statistical patterns, not verified facts. They will confidently state incorrect information if it "sounds right" based on training data. Educational content requires accuracy, but AI lacks inherent fact-checking capabilities.

**How to avoid:**
- Implement GPTZero's Hallucination Detector or similar tools (catches 99 out of 100 flawed citations)
- Use Retrieval-Augmented Generation (RAG) to ground content in verified sources
- Build a two-stage validation pipeline: static exact-match checks followed by LLM-as-a-judge semantic validation
- Never publish AI-generated content without human expert review of factual claims
- Implement citation tracking—every factual claim must link to a verifiable source
- For Course Builder: Add a "Fact Check" phase before export that flags unsupported claims

**Warning signs:**
- Citations that don't exist when manually checked
- Statistical claims without sources
- Technical explanations that contradict official documentation
- Historical dates or events that are slightly off
- Code examples that don't compile or run correctly

**Phase to address:**
Phase 1 (Content Generation Foundation) must include validation hooks. Phase 3 (Quality Assurance) should implement automated hallucination detection before export.

---

### Pitfall 2: Prompt Inconsistency Leading to Quality Drift

**What goes wrong:**
Different prompts or slightly modified prompts produce wildly inconsistent content quality and style. Learning outcome 1 generates excellent content, but learning outcome 7 is generic and low-quality. Students notice the inconsistency, and the course feels disjointed.

**Why it happens:**
Without careful parameter control (temperature, top-p), LLM outputs vary significantly. Each content type (quiz, textbook, slide) may use different prompts without a unified quality framework. Prompt "drift" occurs when slight modifications accumulate over time.

**How to avoid:**
- Use low temperature (0.2–0.4) and low top-p (<0.5) for consistency in factual/technical content
- Create a prompt library with versioned, tested prompts for each content type
- Implement prompt regression testing—when updating prompts, compare outputs against known-good examples
- Use Chain-of-Thought prompting for transparency and consistency in complex tasks
- Freeze prompt versions during a build cycle (don't modify prompts mid-generation)
- For Course Builder: Implement `PromptManager` that enforces temperature/top-p settings and tracks prompt versions per project

**Warning signs:**
- Content quality varies significantly between segments
- Writing style shifts (formal → casual → formal)
- Some quizzes have 3 options, others have 5 (inconsistent format)
- Textbook sections vary in depth (some 2000 words, some 4000 words)
- Code examples use different naming conventions across sections

**Phase to address:**
Phase 1 (Prompt Engineering Foundation) must establish prompt versioning and parameter controls. Phase 2 (Content Generation) should enforce consistency checks across all 12 content types.

---

### Pitfall 3: Quiz Distractor Quality - Too Easy or Invalid

**What goes wrong:**
AI-generated quiz distractors are either obviously wrong (students eliminate them instantly) or technically correct (making the question invalid). Both destroy assessment validity—you can't measure learning when quizzes are broken.

**Why it happens:**
Creating plausible distractors requires modeling student misconceptions, not just generating "wrong" answers. AI struggles to generate options that are incorrect but believable. It doesn't understand what misconceptions students actually have at different knowledge levels.

**How to avoid:**
- Implement distractor quality checker that validates plausibility (Phase 3 quality feature already planned)
- Use student mistake modeling—distractors should reflect common errors, not random wrong answers
- Validate answer distribution: avoid patterns like "C is always correct" or "longest answer is always correct"
- Enforce option-level feedback requirement—if you can't write meaningful feedback, the distractor isn't good enough
- Test questions with Bloom's taxonomy alignment—ensure correct cognitive level
- For Course Builder: Build `DistractorQualityChecker` that flags obviously wrong or technically correct distractors before export

**Warning signs:**
- Distractors contain obvious errors (typos, grammar issues, nonsense)
- All distractors are equally implausible (student sees pattern)
- Distractors are technically correct but marked wrong (ambiguous questions)
- Answer distribution is not balanced (correct answer position shows pattern)
- Feedback for distractors is generic ("This is incorrect. Try again.")

**Phase to address:**
Phase 2 (Quiz Generation) must implement distractor validation. Phase 3 (Quality Assurance) should run automated distractor quality checks before export.

---

### Pitfall 4: Bloom's Taxonomy Misalignment

**What goes wrong:**
Learning outcomes claim "Analyze" level (Bloom's level 4) but quizzes only test "Remember" level (Bloom's level 1). Students memorize facts but can't apply concepts. The course fails to deliver on promised learning outcomes.

**Why it happens:**
AI generates content that "sounds" like higher-order thinking but actually tests lower-order skills. Creating authentic higher-order assessment items is difficult—AI defaults to easier question types.

**How to avoid:**
- Use RoBERTa or similar classifier to validate Bloom's alignment (87%+ accuracy)
- Implement learning outcome → assessment mapping validation
- Build taxonomy ladder—explicitly generate questions at each level (Remember → Understand → Apply → Analyze → Evaluate → Create)
- Human review of alignment before export—automated tools aren't perfect
- Test questions against examples from Bloom's taxonomy guidelines
- For Course Builder: Add `BloomsTaxonomyValidator` that flags misalignments between stated objectives and actual assessments

**Warning signs:**
- Learning outcomes use high-level verbs ("analyze," "evaluate") but quizzes use low-level verbs ("list," "identify")
- All quiz questions are multiple-choice fact recall (no case studies, no problem-solving)
- Textbook content explains concepts but doesn't model application
- Projects require only copying code, not adapting it
- Rubrics don't assess critical thinking or analysis

**Phase to address:**
Phase 1 (Content Generation) must generate questions at specified Bloom's levels. Phase 3 (Quality Assurance) should validate alignment across learning outcomes, textbook content, and assessments.

---

### Pitfall 5: State Management Race Conditions During Batch Generation

**What goes wrong:**
Generating 12 content types for a course in parallel causes race conditions. ProjectStore writes collide, files are partially written, course data becomes corrupted. Build fails silently or produces invalid packages.

**Why it happens:**
File system operations without locking allow concurrent writes to the same file. Disk-based persistence (no database) means no ACID guarantees. Multiple generators write to `project.json` simultaneously, last write wins, data is lost.

**How to avoid:**
- Implement file locking before writing (use `fcntl.flock` on Unix, `msvcrt.locking` on Windows)
- Use advisory locking protocol—all writes must acquire lock first
- Implement write-ahead logging or journaling for critical files
- Serialize writes to `project.json`—use a write queue instead of direct writes
- Add file write integrity checks—verify JSON is valid after write
- Implement retry logic with exponential backoff for file operations
- For Course Builder: Add `ProjectStoreLock` context manager that ensures safe concurrent access

**Warning signs:**
- `project.json` becomes invalid JSON after parallel builds
- Some generated content disappears after batch generation
- Error: "The process cannot access the file because it is being used by another process"
- Builds succeed sometimes, fail sometimes (non-deterministic)
- Content appears in UI but missing from exported package

**Phase to address:**
Phase 1 (Core Infrastructure) must implement file locking. Phase 2 (Batch Generation) should add retry logic and validation.

---

### Pitfall 6: SCORM/LMS Export Package Validation Failures

**What goes wrong:**
Exported course packages fail LMS upload. Coursera rejects package due to missing manifest, incorrect schema version, or broken resource references. Hours of content generation wasted because export is invalid.

**Why it happens:**
SCORM has strict requirements: `imsmanifest.xml` must be in root, all resources must be referenced correctly, schema versions must match LMS expectations, ZIP structure must be exact. Each LMS has its own quirks.

**How to avoid:**
- Implement pre-export validation of manifest structure (syntax, nesting, required fields)
- Verify all resource paths in manifest match actual files in package
- Validate schema version matches target LMS pattern (Coursera-specific)
- Remove special characters from manifest that break parsing
- Ensure no whitespace issues in manifest (common with Moodle)
- Test package against reference SCORM validators before shipping
- For Course Builder: Add `SCORMValidator` that checks manifest integrity and resource references before ZIP creation

**Warning signs:**
- "Manifest not found" error despite file existing (wrong location or whitespace)
- "Invalid schema version" error (version mismatch)
- Course uploads but resources don't load (broken paths)
- ZIP file is corrupted (incomplete writes)
- Manifest references files that don't exist in package

**Phase to address:**
Phase 4 (Export & Packaging) must implement SCORM validation before ZIP creation. Add integration tests that actually upload packages to test LMS instances.

---

### Pitfall 7: 3000-Word Textbook Generation - Coherence Collapse

**What goes wrong:**
AI generates 3000-word textbook sections that start strong but devolve into repetition, contradictions, or tangents by page 3. Content doesn't form a coherent narrative across 12 chapters. Cross-references break because AI forgets earlier chapters.

**Why it happens:**
Long-form content generation is hard. Context window limits cause AI to "forget" earlier content. Each section is generated independently without awareness of overall narrative structure. AI can't maintain topic coherence over thousands of words.

**How to avoid:**
- Use structured generation: outline → sections → paragraphs (hierarchical approach)
- Implement content memory—pass previous chapters as context when generating new chapters
- Use chapter-level prompts that specify connections to prior content
- Break generation into chunks with validation gates (don't generate chapter 12 until 1-11 are validated)
- Implement coherence checking—flag sections that contradict earlier content
- Human review of chapter transitions and cross-references
- For Course Builder: Add `TextbookCoherenceChecker` that validates narrative flow and cross-references

**Warning signs:**
- Repetition of concepts across chapters (same explanation appears twice)
- Contradictions (chapter 3 says X, chapter 8 says not-X)
- Broken cross-references ("as we discussed in chapter 5" but chapter 5 doesn't discuss it)
- Tangential content that doesn't relate to learning outcome
- Chapters don't build on each other (flat structure, not progressive)

**Phase to address:**
Phase 2 (Textbook Generation) must implement hierarchical generation with memory. Phase 3 (Quality Assurance) should validate coherence across chapters.

---

### Pitfall 8: Build Pipeline Failure Without Rollback

**What goes wrong:**
Content generation fails halfway through (API timeout, rate limit, error). System leaves project in broken state. Re-running build causes duplicate content or skips already-generated content. Instructor can't tell what's valid.

**Why it happens:**
No atomic transaction model—builds aren't all-or-nothing. Partial writes are committed even on failure. No build state tracking to know what succeeded/failed. No rollback mechanism to undo partial builds.

**How to avoid:**
- Implement transactional builds—write to temporary directory, commit only on full success
- Add build state tracking—store which content types are complete, in-progress, failed
- Implement idempotent generation—re-running build with same input produces same output
- Add resume capability—detect partial builds and continue from last success point
- Implement retry logic with exponential backoff for transient failures (API rate limits)
- Store build logs with timestamps and error details for debugging
- For Course Builder: Add `BuildTransaction` that ensures atomic commits and supports rollback

**Warning signs:**
- Build fails and project is left in unknown state
- Re-running build creates duplicate content
- Some content types are missing but build reports success
- No way to know if content is from successful or failed build
- Instructor sees mix of old and new content after failed update

**Phase to address:**
Phase 1 (Build Infrastructure) must implement transactional builds. Phase 2 (Content Generation) should add resume capability and retry logic.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip AI validation, manually review all content | Faster initial implementation | Manual review doesn't scale; human error; bottleneck | Never—automated validation is table stakes |
| Use high temperature (0.8+) for "creativity" | More varied outputs | Inconsistent quality; unreliable facts; hard to debug | Only for creative writing (course descriptions), never for technical content |
| Store all state in memory, save on exit | Simple implementation | Data loss on crash; no concurrent access; memory bloat | Acceptable for MVP prototype, not production |
| Hard-code prompts in generator functions | Quick iteration | Prompt drift; no versioning; can't A/B test; hard to maintain | Never—prompts are core IP and must be version-controlled |
| Generate all content sequentially | Simple code flow | Slow builds (12 content types × 5min = 1 hour); poor UX | Acceptable if builds are rare, not for production use |
| Use generic error messages for AI failures | Faster error handling | Impossible to debug; users don't know what failed; support burden | Never—AI failures must provide context (prompt, model, token count) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude API | Not handling rate limits (429 errors) | Implement exponential backoff with jitter; queue requests; respect rate limit headers |
| Claude API | Ignoring context window limits | Track token usage; truncate context if needed; split large prompts; use Claude's count_tokens |
| Claude API | Not implementing retry for transient failures | Retry with exponential backoff (max 3 attempts); log failures; fallback gracefully |
| File System | Writing project.json without locking | Use file locking (`fcntl.flock`) to prevent race conditions; validate JSON after write |
| SCORM Export | Assuming all LMSs handle manifests identically | Test against target LMS; validate schema version; handle LMS-specific quirks (Coursera pattern) |
| Edge TTS | Not handling audio generation failures | Retry failed audio generation; cache successful audio; provide silent fallback |
| FFmpeg | Hard-coding capture device names | Detect available devices; fallback to software capture; handle missing FFmpeg gracefully |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Generating 3000-word textbook in single prompt | API timeouts; incomplete content; high cost | Split into outline → section → paragraph hierarchy; generate in chunks | >2000 words in single prompt |
| No caching of generated content | Regenerating same content on refresh; high API costs; slow UX | Cache generated content by hash of input; invalidate cache on input change | >10 projects with frequent regeneration |
| Loading all projects into memory on startup | Slow startup (>10 seconds); memory bloat; crashes on large installs | Lazy load projects; paginate dashboard; use project summaries not full data | >50 projects |
| No rate limit handling | 429 errors crash builds; wasted API calls; failed generations | Implement token bucket or sliding window rate limiter; queue requests | >100 API calls per minute |
| Synchronous generation of 12 content types | 1-hour build time; blocked UI; poor UX | Parallel generation with progress tracking; async/background jobs | Always—serial generation is unacceptable |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing API keys in exported packages | Key leakage; unauthorized usage; API bill shock | Never embed keys in content; use environment variables; sanitize exports |
| No path traversal validation on project IDs | Arbitrary file read/write; data corruption | Use `safe_filename()` that strips `..`, `/`, `\`; whitelist allowed characters |
| Executing instructor-provided code without sandboxing | RCE vulnerability; server compromise | Never execute untrusted code; use static analysis only; warn if code execution needed |
| Including PII in AI prompts | Privacy violation; data leakage; legal liability | Sanitize inputs before sending to Claude; never include student data in prompts |
| No authentication on v6 API endpoints | Unauthorized access; data theft; abuse | Add authentication even in localhost environment; prepare for multi-user deployment |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indicator during 12-content build | Users think app crashed; refresh and lose progress | Real-time progress: "Generating quiz questions... 3/12 complete" |
| Error message: "AI generation failed" | User doesn't know what to do; contacts support | Specific error: "Quiz generation failed: API rate limit. Retry in 2 minutes." |
| Regenerating content discards old version | Accidental loss of good content; no undo | Version history: show diff before commit; allow rollback to previous version |
| No preview before export | Instructor finds errors after submitting to Coursera | In-app preview of all content types; export validation before final ZIP |
| No indication of AI vs human content | Users don't know what's been reviewed | Visual indicator: "AI-generated (needs review)" vs "Reviewed" |

## "Looks Done But Isn't" Checklist

- [ ] **Quiz Generation:** Often missing option-level feedback — verify each distractor has meaningful explanation, not just "Incorrect"
- [ ] **Textbook Export:** Often missing cross-references validation — verify "see chapter X" actually links to correct content
- [ ] **SCORM Manifest:** Often missing resource reference validation — verify every file in manifest exists in ZIP
- [ ] **Learning Outcomes:** Often missing Bloom's alignment validation — verify assessments actually test the stated cognitive level
- [ ] **Build Pipeline:** Often missing atomic transaction handling — verify partial builds can be rolled back or resumed
- [ ] **API Rate Limiting:** Often missing retry logic — verify 429 errors are handled with exponential backoff
- [ ] **File System Operations:** Often missing file locking — verify concurrent writes don't corrupt project.json
- [ ] **Content Consistency:** Often missing temperature/top-p enforcement — verify all prompts use consistent parameters
- [ ] **Fact Checking:** Often missing hallucination detection — verify factual claims are validated before export
- [ ] **Export Validation:** Often missing pre-export validation — verify package passes SCORM validator before ZIP creation

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hallucinated content published | HIGH | 1. Identify incorrect content via fact-check 2. Regenerate with RAG grounding 3. Human expert review 4. Re-export package 5. Notify instructors of correction |
| Prompt inconsistency detected | LOW | 1. Freeze prompt version 2. Regenerate affected content 3. Run consistency validation 4. Update prompt library |
| Quiz distractor quality issues | MEDIUM | 1. Run `DistractorQualityChecker` 2. Regenerate flagged questions 3. Human review of borderline cases 4. Update distractor generation prompt |
| Bloom's misalignment discovered | MEDIUM | 1. Map learning outcomes to assessments 2. Regenerate questions at correct level 3. Validate with classifier 4. Human review of alignment |
| Build state corruption | MEDIUM | 1. Detect partial build via state tracking 2. Rollback to last good state 3. Resume build from last success point 4. Validate integrity before commit |
| SCORM validation failure | LOW | 1. Run `SCORMValidator` to identify issue 2. Fix manifest structure 3. Validate resource references 4. Re-test with validator 5. Re-export ZIP |
| Textbook coherence collapse | HIGH | 1. Re-outline chapter structure 2. Regenerate with chapter memory 3. Human review of transitions 4. Validate cross-references 5. Re-export textbook |
| API rate limit exceeded | LOW | 1. Detect 429 error 2. Queue remaining requests 3. Retry with exponential backoff 4. Resume build automatically |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| AI Hallucination | Phase 1 (Foundation) | Fact-check validation passes; citations verify; expert review conducted |
| Prompt Inconsistency | Phase 1 (Foundation) | Temperature/top-p enforced; prompt version frozen; consistency tests pass |
| Quiz Distractor Quality | Phase 2 (Quiz Generation) | Distractor quality score >80%; balance distribution validated; feedback provided |
| Bloom's Misalignment | Phase 2 (Content Generation) | Classifier validates alignment; rubric mapping correct; cognitive level verified |
| Race Conditions | Phase 1 (Infrastructure) | File locking implemented; concurrent writes tested; no JSON corruption |
| SCORM Validation | Phase 4 (Export) | Validator passes; test upload succeeds; manifest structure correct |
| Textbook Coherence | Phase 2 (Textbook Generation) | Coherence checker passes; cross-references valid; narrative flow verified |
| Build Pipeline Failure | Phase 1 (Infrastructure) | Rollback succeeds; resume works; atomic commits validated |

## Sources

### AI Content Generation Quality
- [Mistakes to Avoid When Using AI to Create eLearning Courses](https://www.shiftelearning.com/blog/mistakes-ai-elearning-courses)
- [AI Content Creation Mistakes Schools Should Try to Avoid](https://www.higher-education-marketing.com/blog/4-ai-content-creation-mistakes-for-schools-to-avoid)
- [The AI Content Explosion: What Your Learners Actually Think](https://drphilippahardman.substack.com/p/the-ai-content-explosion-what-your)

### Prompt Engineering & Consistency
- [Prompt Engineering Guide 2026](https://www.analyticsvidhya.com/blog/2026/01/master-prompt-engineering/)
- [The Ultimate Guide to Prompt Engineering in 2026](https://www.lakera.ai/blog/prompt-engineering-guide)
- [Prompt engineering in consistency and reliability](https://www.nature.com/articles/s41746-024-01029-4)

### Temperature & Sampling Parameters
- [Complete Guide to Prompt Engineering with Temperature and Top-p](https://promptengineering.org/prompt-engineering-with-temperature-and-top-p/)
- [What are Temperature, Top_p, and Top_k in AI?](https://www.f22labs.com/blogs/what-are-temperature-top_p-and-top_k-in-ai/)
- [Understanding Temperature, Top-k, and Top-p Sampling](https://codefinity.com/blog/Understanding-Temperature,-Top-k,-and-Top-p-Sampling-in-Generative-Models)

### Quiz Generation & Distractors
- [Automatic distractor generation in multiple-choice questions: systematic review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/)
- [A novel approach to generate distractors for MCQs](https://www.sciencedirect.com/science/article/abs/pii/S0957417423005249)
- [Generating Plausible Distractors via Student Choice Prediction](https://scale.stanford.edu/ai/repository/generating-plausible-distractors-multiple-choice-questions-student-choice-prediction)
- [AI-generated MCQs in health science education](https://pmc.ncbi.nlm.nih.gov/articles/PMC12340502/)

### Bloom's Taxonomy & Learning Outcomes
- [Assessing AI-Generated Questions' Alignment with Cognitive](https://arxiv.org/pdf/2504.14232)
- [Leveraging generative AI for course learning outcome categorization](https://www.sciencedirect.com/science/article/pii/S2666920X2500044X)
- [Aligning with Bloom's Taxonomy](https://gaied.org/neurips2023/files/17/17_paper.pdf)
- [Can AI Generate Questions Aligned with Bloom's Taxonomy?](https://journals.sagepub.com/doi/10.1177/1932202X251349917)

### AI Hallucination Detection
- [GPTZero uncovers 50+ Hallucinations in ICLR 2026](https://gptzero.me/news/iclr-2026/)
- [Hallucination Detection and Mitigation in Large Language Models](https://arxiv.org/pdf/2601.09929)
- [Top Tools and Plugins to Detect AI Hallucinations in Real-Time](https://www.ishir.com/blog/183214/top-tools-and-plugins-to-detect-ai-hallucinations-in-real-time.htm)
- [Hallucination to truth: review of fact-checking in LLMs](https://link.springer.com/article/10.1007/s10462-025-11454-w)

### File System & State Management
- [Race Conditions and Secure File Operations](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html)
- [How Do Filesystems Handle Concurrent Read/Write?](https://www.baeldung.com/cs/concurrent-read-write)
- [FIO45-C. Avoid TOCTOU race conditions](https://wiki.sei.cmu.edu/confluence/display/c/FIO45-C.+Avoid+TOCTOU+race+conditions+while+accessing+files)

### SCORM & LMS Export
- [Troubleshooting SCORM: Complete Guide](https://doctorelearning.com/blog/guide-for-troubleshooting-scorm/)
- [SCORM content: troubleshooting errors](https://support.learnupon.com/hc/en-us/articles/360004744477-SCORM-content-troubleshooting-errors)
- [Common SCORM Errors: Troubleshooting Tips](https://regex.global/blog/common-scorm-errors-troubleshooting-tips-for-scorm-package-issues/)
- [How to Avoid or Fix Common SCORM Packaging Errors](https://www.linkedin.com/advice/0/what-most-common-scorm-packaging-errors-skills-e-learning)

### Batch Processing & Retry Logic
- [Python Retry Logic with Tenacity and Instructor](https://python.useinstructor.com/concepts/retrying/)
- [Mastering Retry Logic Agents: Deep Dive into 2025 Best Practices](https://sparkco.ai/blog/mastering-retry-logic-agents-a-deep-dive-into-2025-best-practices)
- [Error Recovery and Fallback Strategies in AI Agent Development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development)
- [AI Batch Processing: OpenAI, Claude, and Gemini (2025)](https://adhavpavan.medium.com/ai-batch-processing-openai-claude-and-gemini-2025-94107c024a10)

### Coursera Quality Standards
- [Drivers of Quality in Online Learning](https://about.coursera.org/press/wp-content/uploads/2020/10/Coursera_DriversOfQuality_Book_MCR-1126-V4-lr.pdf)
- [Quality Online Courses - National Standards](https://nsqol.org/the-standards/quality-online-courses/)

---
*Pitfalls research for: Course Builder Studio (AI-powered Coursera course authoring platform)*
*Researched: 2026-02-02*
