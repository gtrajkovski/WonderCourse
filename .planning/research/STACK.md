# Stack Research

**Domain:** AI-powered course authoring/development platform (Coursera short courses)
**Researched:** 2026-02-02
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10+ | Runtime environment | ScreenCast Studio uses 3.9+; 3.10+ recommended for modern Flask apps (3.9 is EOL, pytest 9.x dropped support). Supports all required libraries. |
| Flask | 3.1.2 | Web framework | Industry standard micro-framework for Python web apps. Lightweight, flexible, perfect for small-to-medium projects. Excellent extension ecosystem. Battle-tested in production. |
| Jinja2 | 3.1.6 | Template engine | Flask's default templating engine. Auto-escaping prevents XSS. Supports template inheritance (DRY principle). Compiled to optimized Python code. AsyncIO support for future needs. |
| Werkzeug | 3.1.5+ | WSGI toolkit | Required dependency for Flask 3.1+. Handles HTTP request/response cycle. Production-ready WSGI implementation. |
| Anthropic SDK | 0.77.0+ | Claude API client | Official Python SDK for Claude API. Handles auth, request formatting, error handling, retries. Supports sync/async, streaming, tool use, prompt caching. 200K context window. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0.1+ | Environment variable management | Load API keys and config from .env files. Flask CLI auto-loads .env and .flaskenv. Essential for 12-factor app principles. |
| python-docx | 1.2.0+ | Word document generation | Generate .docx files for readings, assignments, textbook chapters. Industry standard library for programmatic DOCX creation. |
| docxtpl | 0.18.0+ | DOCX templating | Template-based DOCX generation. Built on python-docx + Jinja2. Ideal for structured content with variable substitution. Use when templates are more maintainable than code. |
| mistune | 3.0.2+ | Markdown parsing | Parse imported markdown content. Fast, spec-compliant (CommonMark), extensible with plugins. Outperforms alternatives in benchmarks. |
| Markdown | 3.10.1+ | Markdown generation | Generate markdown exports of course content. Python's reference implementation. Extension system for custom syntax. Requires Python 3.10+. |
| Flask-CORS | 6.0.2+ | CORS support | Handle cross-origin requests if frontend moves to separate domain. Supports blueprints, per-resource configuration. Set `supports_credentials=True` for session cookies. |
| dataclasses | stdlib | Data models | Python 3.10+ stdlib. Fast, simple data containers with type hints. Use for internal trusted data structures (Project, Segment, etc.). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | 9.0.2+ | Testing framework | Requires Python 3.10+ (9.x dropped 3.9 support). Less boilerplate than unittest. Fixture system for reusable test setup. Auto-discovery with test_*.py naming. |
| pytest-flask | 1.3.0+ | Flask testing utilities | Provides app and client fixtures for Flask tests. Simplifies test organization. Compatible with Flask 3.0+. |
| pytest-mock | 3.15.1+ | Mocking in pytest | Thin wrapper around unittest.mock. Auto-undoes mocking after tests. Provides spy and stub utilities. Essential for mocking Claude API calls. |
| ruff | 0.10.0+ | Linter + formatter | 10-100x faster than Black/Flake8. Written in Rust. Can replace Black, Flake8, isort, pyupgrade, autoflake. 800+ built-in rules. >99.9% Black-compatible. Single tool for entire Python toolchain. |
| black | 24.0.0+ | Code formatter (alternative) | If team prefers established tool over Ruff. Highly opinionated, enforces consistency. De facto standard for years. Use if compatibility is concern. |

## Installation

```bash
# Core dependencies
pip install Flask==3.1.2 anthropic python-dotenv

# Document generation
pip install python-docx docxtpl mistune Markdown

# Supporting libraries
pip install Flask-CORS

# Dev dependencies
pip install pytest pytest-flask pytest-mock ruff

# Or install from requirements.txt:
pip install -r requirements.txt
```

**requirements.txt:**
```
# Core
Flask>=3.1.2
anthropic>=0.77.0
python-dotenv>=1.0.1

# Document generation
python-docx>=1.2.0
docxtpl>=0.18.0
mistune>=3.0.2
Markdown>=3.10.1

# Optional
Flask-CORS>=6.0.2

# Dev
pytest>=9.0.2
pytest-flask>=1.3.0
pytest-mock>=3.15.1
ruff>=0.10.0
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Flask | FastAPI | If API-first design is priority. FastAPI has automatic OpenAPI docs, better async support. But adds complexity for server-rendered HTML apps. |
| Flask | Django | If you need admin panel, ORM, batteries-included framework. Overkill for JSON-based persistence and AI content generation workflows. |
| dataclasses | Pydantic | If receiving untrusted external data requiring runtime validation. Dataclasses 6.46x faster and use 50% less memory for trusted internal data. Course Builder controls all data inputs (no public API). |
| Ruff | Black + Flake8 + isort | If team is conservative about adopting Rust-based tools. Stick with established Python-native tools. Ruff is drop-in replacement (>99.9% compatible). |
| python-docx | python-docx-template | Both should be installed. Use python-docx for programmatic control, docxtpl for template-based generation. |
| mistune | markdown-it-py | If you need markdown-it ecosystem compatibility. markdown-it-py is CommonMark compliant, pluggable. Mistune is faster. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SQLAlchemy/Database | Unnecessary complexity for disk-based JSON persistence. Adds migration overhead, deployment dependencies. | ProjectStore pattern with JSON serialization (proven in ScreenCast Studio). |
| Flask-SQLAlchemy | Same as above. Project constraints explicitly state "no database". | Dataclasses + to_dict/from_dict + JSON files. |
| React/Vue frontend (Phase 1) | Project constraints defer React to later. Adds build complexity, tooling overhead. | Jinja2 templates + vanilla JavaScript (migrate to React in later milestone). |
| Python 3.9 | Reached EOL October 2025. pytest 9.x dropped support. | Python 3.10+ (3.11 or 3.12 recommended for performance). |
| Flask-WTF | Designed for HTML forms with CSRF protection. Course Builder is JSON API-driven with AI content generation, not user form input. | Dataclass validation for JSON payloads. Flask's request.get_json() built-in parsing. |
| Old markdown libraries (markdown2, mistletoe) | Outdated or less maintained. | mistune (fastest, actively maintained) or Markdown (reference implementation). |

## Stack Patterns by Use Case

**If building content type generators (scripts, readings, quizzes, etc.):**
- Use conversational AI client pattern (src/ai/client.py) for interactive workflows
- Use one-shot AI client pattern (src/utils/ai_client.py) for batch generation
- Store prompts in src/ai/prompts/ organized by content type
- Return dataclass results with metadata (word count, duration, difficulty)

**If generating Word documents:**
- Use docxtpl for structured templates (readings, textbook chapters with predictable layout)
- Use python-docx for dynamic programmatic generation (HOL activities with code blocks)
- Store templates in templates/content_types/

**If handling markdown import/export:**
- Use mistune for parsing (faster, benchmarks prove superiority)
- Use Markdown library for generation (extension system for custom syntax)
- Validate structure with regex patterns (similar to WWHAA parser in ScreenCast Studio)

**If testing API endpoints:**
- Use pytest-flask's client fixture for Flask test client
- Use pytest-mock to mock Anthropic API calls (avoid real API calls in tests)
- Use tmp_path fixture for isolated file operations
- Test serialization round-trips: to_dict() → from_dict() → assert equality

**If building dual app pattern (v5/v6 style):**
- Share ProjectStore and data models across apps
- Use separate v6_data.json for v6-specific features
- Run apps on different ports (5003 for main, 5004 for experimental)
- Templates in templates_v1/, templates_v2/ etc. Static in static_v1/, static_v2/

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Flask 3.1.2 | Werkzeug >= 3.1 | Flask 3.1 requires Werkzeug 3.1+. Version pinning important. |
| Flask 3.1.2 | Python 3.10+ | Dropped Python 3.8 support. Requires 3.9+ but 3.10+ recommended (pytest 9.x compatibility). |
| pytest 9.0.2 | Python 3.10+ | Dropped Python 3.9 support (EOL). Use pytest 8.x if stuck on 3.9. |
| Markdown 3.10.1 | Python 3.10+ | Explicitly requires Python 3.10+. Use older version or mistune for 3.9. |
| anthropic 0.77.0 | Python 3.7+ | Wide compatibility. Supports async with httpx. |
| python-docx 1.2.0 | Python 3.6+ | Stable, mature library. No known compatibility issues. |
| Jinja2 3.1.6 | Python 3.7+ | Flask bundles compatible version. Auto-installed with Flask. |

## Anti-Patterns to Avoid

**Don't mix validation approaches:**
- BAD: Using Pydantic for some models, dataclasses for others
- GOOD: Use dataclasses consistently for all internal models (ProjectStore pattern)
- Exception: If adding public API later, introduce Pydantic at API boundary only

**Don't over-engineer early:**
- BAD: Building separate frontend + backend with GraphQL/REST for localhost app
- GOOD: Server-rendered Jinja2 templates, progressive enhancement with vanilla JS
- Later: Migrate to React when scale demands it

**Don't skip prompt versioning:**
- BAD: Hardcoding prompts in endpoint handlers
- GOOD: Centralize in src/ai/prompts/ with version comments, allowing A/B testing

**Don't test against live Claude API:**
- BAD: Integration tests calling real Anthropic API (slow, costs money, flaky)
- GOOD: Mock with pytest-mock, test prompt construction logic separately

**Don't forget Windows compatibility:**
- BAD: Using UNIX-only path separators, assuming bash commands
- GOOD: Use pathlib.Path, os.path.join, py -3 command in docs (project constraint)

## Claude API Best Practices (2026)

Based on official Anthropic SDK documentation and recent 2026 guidance:

**1. Use streaming for better UX:**
```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        yield text
```

**2. Enable prompt caching for 70-80% cost savings:**
```python
# Cache system prompts, content type templates
messages = [
    {"role": "system", "content": cached_system_prompt, "cache_control": {"type": "ephemeral"}},
    {"role": "user", "content": user_input}
]
```

**3. Use tool use for structured outputs:**
```python
# Define content type schemas as tools
# Claude returns JSON matching schema
# No regex parsing needed
```

**4. Leverage 200K context window:**
```python
# Send entire course outline + previous segments
# Claude maintains consistency across 12 content types
# No need for separate context management
```

**5. Handle errors properly:**
```python
from anthropic import APIError, APIConnectionError, RateLimitError

try:
    response = client.messages.create(...)
except RateLimitError:
    # Implement backoff
except APIConnectionError:
    # Retry with exponential backoff
except APIError as e:
    # Log and return user-friendly error
```

**6. Use async for parallel generation:**
```python
async with AsyncAnthropic() as client:
    tasks = [generate_script(...), generate_quiz(...), generate_reading(...)]
    results = await asyncio.gather(*tasks)
```

## Security Considerations

**Environment variables:**
- NEVER commit .env to git (add to .gitignore)
- Use .env.example with dummy values for setup docs
- Flask CLI auto-loads .env (python-dotenv integration)

**Path traversal protection:**
- ProjectStore pattern sanitizes IDs (strips /, \, ..)
- Use safe_filename() for user-provided names
- Validate against projects/{id}/ directory structure

**XSS prevention:**
- Jinja2 autoescaping enabled by default
- Use |safe filter cautiously (only for trusted AI-generated HTML)
- Sanitize any user input before rendering

**API key exposure:**
- Read ANTHROPIC_API_KEY from environment only
- Never log API keys or include in error messages
- Use Flask's config.from_prefixed_env() pattern

## Sources

### High Confidence (Official Documentation, Context7, PyPI)
- [Flask 3.1.2 on PyPI](https://pypi.org/project/Flask/) — Current version, Python requirements
- [Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/) — Official docs, installation guide, changelog
- [Anthropic Python SDK (GitHub)](https://github.com/anthropics/anthropic-sdk-python) — v0.77.0 release, SDK features
- [Anthropic Python API (PyPI)](https://pypi.org/project/anthropic/) — Package versions, installation
- [Jinja2 Documentation (3.1.x)](https://jinja.palletsprojects.com/) — Official docs, template designer guide
- [python-docx Documentation](https://python-docx.readthedocs.io/) — v1.2.0 docs, API reference
- [pytest Documentation](https://docs.pytest.org/) — v9.0.2 changelog, backwards compatibility
- [Ruff Documentation](https://docs.astral.sh/ruff/) — Formatter, linter, FAQ

### Medium Confidence (Multiple Credible Sources, WebSearch Verified)
- [Testing Flask Applications with Pytest | TestDriven.io](https://testdriven.io/blog/flask-pytest/) — Best practices, fixture patterns
- [Flask Best Practices (Auth0)](https://auth0.com/blog/best-practices-for-flask-api-development/) — Production patterns
- [Python markdown library recommendations (Python.org Discussions)](https://discuss.python.org/t/markdown-module-recommendations/65125) — mistune vs alternatives
- [Pydantic vs Dataclasses comparison (Medium, SoftwareLogic)](https://softwarelogic.co/en/blog/pydantic-vs-dataclasses-which-excels-at-python-data-validation) — Performance benchmarks
- [Jinja2 2026 Best Practices (OreateAI)](https://www.oreateai.com/blog/comprehensive-practical-guide-to-jinja2-template-engine/) — Variable design, whitespace management

### Ecosystem Discovery (WebSearch)
- [Top Python Web Frameworks 2026 (Reflex Blog)](https://reflex.dev/blog/2026-01-09-top-python-web-frameworks-2026/) — Flask positioning
- [Ruff vs Black comparison (PacketCoders)](https://www.packetcoders.io/whats-the-difference-black-vs-ruff/) — Performance, compatibility
- [python-dotenv best practices (GeeksforGeeks)](https://www.geeksforgeeks.org/python/using-python-environment-variables-with-python-dotenv/) — Flask integration
- [Anthropic Claude API Guide (Anthropic Academy)](https://www.anthropic.com/learn/build-with-claude) — Official learning resources

---
*Stack research for: AI-powered Coursera course development platform*
*Researched: 2026-02-02*
*Confidence: HIGH — All versions verified with PyPI/official docs via WebSearch in Feb 2026*
