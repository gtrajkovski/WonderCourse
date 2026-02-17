# Phase 1 Research: Foundation & Infrastructure

**Phase:** 01 - Foundation & Infrastructure
**Researched:** 2026-02-02
**Confidence:** HIGH (patterns proven in ScreenCast Studio)

## Executive Summary

Phase 1 establishes the foundation for Course Builder Studio by implementing core data models, disk persistence, AI client abstraction, and Flask app skeleton. This phase copies proven patterns from ScreenCast Studio (C:\ScreencastHelper) which has 800 tests and runs in production. Research shows this is low-risk, well-understood work with clear implementation paths.

**Key insight:** File locking is critical for concurrent write safety but ScreenCast Studio currently lacks it. We must implement it from day one using platform-specific approaches (fcntl on Unix, msvcrt on Windows). Dataclasses are 6.46x faster than Pydantic for trusted internal data, making them the right choice for course models.

**Timeline estimate:** 5-7 plans over 3-4 days (1 day per plan for models, store, AI client, Flask skeleton, config).

## What You Need to Know

### 1. Data Model Design Pattern

**Copy from:** `C:\ScreencastHelper\src\core\models.py`

The proven pattern uses Python dataclasses with to_dict/from_dict serialization:

```python
@dataclass
class Course:
    id: str = field(default_factory=lambda: f"course_{uuid.uuid4().hex[:12]}")
    title: str = "Untitled Course"
    # ... fields ...

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            # Nested objects: [seg.to_dict() for seg in self.modules]
            # Enums: self.status.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Course":
        data = dict(data)  # Defensive copy
        # Extract nested lists for separate processing
        modules_data = data.pop("modules", [])
        # Enum conversion
        if "status" in data and isinstance(data["status"], str):
            data["status"] = BuildState(data["status"])
        # Filter to known fields (schema evolution tolerance)
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        course = cls(**filtered)
        course.modules = [Module.from_dict(m) for m in modules_data]
        return course
```

**Key patterns:**
- Default factory for ID generation (uuid4 hex, first 12 chars)
- Defensive copy in from_dict (`data = dict(data)`)
- Schema evolution tolerance (filter to known fields)
- Nested object serialization (extract lists, recursively call from_dict)
- Enum value serialization (`.value` on export, constructor on import)
- ISO datetime strings for timestamps (`datetime.now().isoformat()`)

**Course Builder specific models needed:**
- `Course` - Root container (title, description, learning_outcomes, modules)
- `Module` - Grouping container (title, lessons)
- `Lesson` - Content container (title, activities)
- `Activity` - Atomic content unit (type, wwhaa_phase, content, build_state)
- `LearningOutcome` - ABCD model (audience, behavior, condition, degree, bloom_level, tags)
- `TextbookChapter` - Long-form content (title, sections, word_count)

**Enums needed:**
- `ContentType` - VIDEO, READING, QUIZ, HOL, COACH, LAB, DISCUSSION, ASSIGNMENT, PROJECT, RUBRIC
- `ActivityType` - Granular types (GRADED_QUIZ, PRACTICE_QUIZ, etc.)
- `BuildState` - DRAFT, GENERATING, GENERATED, REVIEWED, APPROVED, PUBLISHED
- `BloomLevel` - REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE
- `WWHAAPhase` - HOOK, OBJECTIVE, CONTENT, IVQ, SUMMARY, CTA

### 2. ProjectStore Persistence Pattern

**Copy from:** `C:\ScreencastHelper\src\core\project_store.py` (94 lines)

The proven pattern:
- Base directory: `projects/` (created on init)
- Project structure: `projects/{id}/course_data.json` (mirroring project.json and v6_data.json pattern)
- Subdirectories: `projects/{id}/exports/`, `projects/{id}/textbook/`
- Path traversal protection: `_sanitize_id()` strips `/`, `\`, `..`
- Auto-create directories on save
- Auto-update `updated_at` timestamp on save

**CRITICAL ADDITION - File Locking:**

ScreenCast Studio lacks file locking, which Phase 1 must add. Platform-specific implementations:

```python
import sys
import json
from pathlib import Path

class ProjectStore:
    def save(self, course: Course) -> Path:
        path = self._course_file(course.id)
        path.parent.mkdir(parents=True, exist_ok=True)

        course.updated_at = datetime.now().isoformat()
        data = course.to_dict()

        # Platform-specific file locking
        if sys.platform == "win32":
            import msvcrt
            with open(path, "w", encoding="utf-8") as f:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                finally:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            with open(path, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return path
```

**Why file locking matters:**
- Success Criterion 5: "File locking prevents race conditions during concurrent write operations"
- Web apps have concurrent requests (user saves while AI generation updates status)
- Without locking: corrupted JSON, lost writes, inconsistent state
- With locking: atomic writes, serialized access, data integrity

**Store methods needed:**
- `save(course: Course) -> Path` - Write course_data.json with locking
- `load(course_id: str) -> Optional[Course]` - Read and deserialize
- `list_courses() -> List[dict]` - Return metadata for dashboard (id, title, module count, updated_at)
- `delete(course_id: str) -> bool` - Remove directory tree
- `_sanitize_id(course_id: str) -> str` - Path traversal protection
- `_course_dir(course_id: str) -> Path` - Base directory
- `_course_file(course_id: str) -> Path` - course_data.json path

### 3. AI Client Abstraction

**Copy from:** `C:\ScreencastHelper\src\ai\client.py` (75 lines)

ScreenCast Studio uses dual AI client pattern:

**Conversational client** (`src/ai/client.py`) - For interactive features:
- `chat(user_message, system_prompt) -> str` - Single request with history
- `chat_stream(user_message, system_prompt) -> Generator` - Streaming response
- `generate(system_prompt, user_prompt, max_tokens) -> str` - One-shot, no history
- `clear_history()` - Reset conversation
- Instance maintains `conversation_history: List[Dict[str, str]]`

**One-shot client** (`src/utils/ai_client.py`) - For batch generation:
- `generate(system_prompt, user_prompt, max_tokens, temperature) -> str` - Simple wrapper
- Hardcoded methods like `generate_script()`, `generate_demo_code()` with prompts
- Stateless, reusable across projects

**Course Builder needs both:**
- Conversational for: Blueprint refinement, content improvement, interactive Q&A
- One-shot for: Bulk content generation, validation, batch operations

**Implementation pattern:**
```python
import anthropic
from typing import Generator, List, Dict
from ..config import Config

class AIClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = Config.MODEL
        self.conversation_history: List[Dict[str, str]] = []

    def chat(self, user_message: str, system_prompt: str = None) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "You are a helpful course authoring assistant.",
            messages=self.conversation_history
        )
        assistant_message = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
```

**Best practices (from STACK.md):**
- Use low temperature (0.2-0.4) for consistency across content types
- Enable prompt caching for 70-80% cost savings on repeated system prompts
- Handle errors: `APIError`, `APIConnectionError`, `RateLimitError`
- Version prompts (store in `src/ai/prompts/` with metadata)
- Mock API calls in tests (pytest-mock)

### 4. Flask App Skeleton

**Copy from:** `C:\ScreencastHelper\app_v5.py` and `C:\ScreencastHelper\app_v6.py`

Proven pattern for dual-app architecture:
- Port 5003 for Course Builder (5001 = v5, 5002 = v6, 5003 = CB)
- Template folder: `templates/` (can create versioned folders later if needed)
- Static folder: `static/` (CSS, JS, images)
- Module-level singletons: `project_store = ProjectStore(Path('projects'))`
- Module-level client: `ai_client = AIClient()`

**Basic structure:**
```python
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for
from src.config import Config
from src.core.models import Course
from src.core.project_store import ProjectStore
from src.ai.client import AIClient

app = Flask(__name__,
            template_folder='templates',
            static_folder='static',
            static_url_path='/static')

project_store = ProjectStore(Path('projects'))
ai_client = AIClient()

# Page routes
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    courses = project_store.list_courses()
    return render_template('dashboard.html', courses=courses)

# API routes
@app.route('/api/courses', methods=['GET'])
def list_courses():
    return jsonify(project_store.list_courses())

@app.route('/api/courses', methods=['POST'])
def create_course():
    data = request.get_json()
    course = Course(title=data.get('title', 'Untitled Course'))
    project_store.save(course)
    return jsonify(course.to_dict()), 201

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5003))
    app.run(host='127.0.0.1', port=port, debug=True)
```

**Route structure to establish:**
- `/` - Redirect to dashboard
- `/dashboard` - Course list
- `/api/courses` - GET (list), POST (create)
- `/api/courses/<id>` - GET (detail), PUT (update), DELETE (remove)
- `/api/system/health` - Health check (ping DB, check API key)

**Success validation:**
- App starts on http://127.0.0.1:5003
- Routes return 200 OK
- Templates render without error
- API endpoints return valid JSON

### 5. Configuration System

**Copy from:** `C:\ScreencastHelper\src\config.py` (187 lines)

Proven configuration pattern using dataclasses and enums:

```python
import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class BloomLevel(Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"

class Config:
    # API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    MODEL = os.getenv("MODEL", "claude-sonnet-4-20250514")
    MAX_TOKENS = 4096

    # Paths
    PROJECTS_DIR = Path("projects")
    TEMPLATES_DIR = Path("templates")

    # Content rules
    MAX_READING_WORDS = 1200
    MAX_TEXTBOOK_WORDS_PER_OUTCOME = 3000
    COURSE_MIN_DURATION_MINUTES = 30
    COURSE_MAX_DURATION_MINUTES = 180

    @classmethod
    def ensure_dirs(cls):
        """Create required directories."""
        cls.PROJECTS_DIR.mkdir(exist_ok=True)
        return cls.PROJECTS_DIR
```

**Environment variables (.env):**
```
ANTHROPIC_API_KEY=sk-ant-...
MODEL=claude-sonnet-4-20250514
PORT=5003
```

**Configuration priorities:**
1. Global constants (MAX_TOKENS, content limits)
2. Enums for type safety (BloomLevel, ContentType, BuildState)
3. Dataclasses for structured config (future: per-course settings)
4. Environment variable overrides (API key, model, port)

### 6. Testing Strategy

**Copy from:** `C:\ScreencastHelper\tests\test_v6_models.py` and `C:\ScreencastHelper\tests\conftest_v6.py`

Proven test patterns:

**Serialization round-trip tests:**
```python
def test_course_round_trip():
    course = Course(
        id="course_123",
        title="Python Fundamentals",
        modules=[Module(title="Module 1")]
    )
    d = course.to_dict()
    restored = Course.from_dict(d)
    assert restored.id == course.id
    assert restored.title == course.title
    assert len(restored.modules) == 1
```

**ProjectStore tests with tmp_path:**
```python
def test_save_and_load(tmp_path):
    store = ProjectStore(tmp_path)
    course = Course(id="test_001", title="Test")
    store.save(course)
    loaded = store.load("test_001")
    assert loaded.title == "Test"
    assert (tmp_path / "test_001" / "course_data.json").exists()
```

**Flask endpoint tests:**
```python
@pytest.fixture
def client(tmp_path):
    import app
    app.project_store = ProjectStore(tmp_path)
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client

def test_create_course(client):
    response = client.post('/api/courses', json={"title": "New Course"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "New Course"
```

**File locking tests:**
```python
import threading
import time

def test_concurrent_writes(tmp_path):
    """Verify file locking prevents corruption."""
    store = ProjectStore(tmp_path)
    course = Course(id="test_concurrent")
    store.save(course)

    def update_course(field_name, value):
        loaded = store.load("test_concurrent")
        setattr(loaded, field_name, value)
        time.sleep(0.01)  # Simulate processing
        store.save(loaded)

    t1 = threading.Thread(target=update_course, args=("title", "Thread 1"))
    t2 = threading.Thread(target=update_course, args=("description", "Thread 2"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    final = store.load("test_concurrent")
    # Both writes should succeed without corruption
    assert final.title == "Thread 1" or final.description == "Thread 2"
    # JSON should be valid (not corrupted)
    assert final.id == "test_concurrent"
```

**Test coverage targets (from ScreenCast Studio):**
- Models: 100% (simple serialization, high value)
- ProjectStore: 95%+ (critical path, file operations)
- AI client: 60-70% (mock API calls, test prompt construction)
- Flask routes: 80%+ (integration style, test happy + error paths)

### 7. Directory Structure

Establish this structure in Phase 1:

```
C:\CourseBuilder\
├── .env.example
├── .env (gitignored)
├── .gitignore
├── requirements.txt
├── app.py                      # Flask app (port 5003)
├── pytest.ini
├── projects/                   # Created by ProjectStore
│   └── {course_id}/
│       ├── course_data.json
│       ├── exports/
│       └── textbook/
├── src/
│   ├── __init__.py
│   ├── config.py              # Config constants and enums
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py          # Course, Module, Lesson, Activity, LearningOutcome
│   │   └── project_store.py   # Disk persistence with file locking
│   ├── ai/
│   │   ├── __init__.py
│   │   └── client.py          # Conversational AI client
│   └── utils/
│       ├── __init__.py
│       └── ai_client.py       # One-shot AI client
├── templates/
│   ├── base.html              # Layout template
│   └── dashboard.html         # Course list
├── static/
│   └── css/
│       └── main.css           # Basic styles
└── tests/
    ├── __init__.py
    ├── conftest.py            # Shared fixtures
    ├── test_models.py         # Serialization round-trips
    ├── test_project_store.py  # Save/load/list/delete + file locking
    ├── test_ai_client.py      # Prompt construction (mocked API)
    └── test_app.py            # Flask endpoint tests
```

## Critical Decisions

### 1. Dataclasses vs Pydantic

**Decision:** Use dataclasses exclusively.

**Rationale:**
- 6.46x faster serialization (research from STACK.md)
- 50% less memory usage
- All data is trusted (internal generation, no public API)
- Proven in ScreenCast Studio (800 tests, production stable)
- Pydantic only needed if accepting untrusted external data

**Exception:** If v2 adds public REST API, introduce Pydantic at API boundary only.

### 2. File Locking Implementation

**Decision:** Platform-specific file locking (fcntl on Unix, msvcrt on Windows).

**Rationale:**
- Success Criterion 5 requires it
- ScreenCast Studio lacks it (technical debt we avoid)
- Web apps have concurrent requests (race condition risk is real)
- Simple implementation (~10 lines in save/load methods)

**Alternative considered:** SQLite for transactional guarantees. Rejected because requirements explicitly state "no database" and ProjectStore pattern is proven.

### 3. Flask vs FastAPI

**Decision:** Flask 3.1.2.

**Rationale:**
- ScreenCast Studio uses Flask successfully
- Server-rendered templates (Jinja2) prioritized over API-first
- Lower complexity for small-to-medium app
- Can add FastAPI later if API performance becomes bottleneck

### 4. Single App vs Dual App (v5/v6 pattern)

**Decision:** Single app initially (`app.py` on port 5003).

**Rationale:**
- No experimental features to isolate yet
- Can split later if needed (proven pattern exists)
- Simpler mental model for Phase 1
- Easier testing with single test client

### 5. Prompt Storage Strategy

**Decision:** Centralized prompts in `src/ai/prompts/` (deferred to Phase 3/4).

**Rationale:**
- Phase 1 has minimal AI usage (health checks, basic validation)
- Phase 3-4 add content generators (where prompts matter)
- Establish directory now, populate later
- Version prompts with comments (not separate files initially)

## Dependencies & Requirements

**Python requirements (requirements.txt):**
```
# Core
Flask>=3.1.2
anthropic>=0.77.0
python-dotenv>=1.0.1

# Dev
pytest>=9.0.2
pytest-flask>=1.3.0
pytest-mock>=3.15.1
ruff>=0.10.0
```

**System requirements:**
- Python 3.10+ (pytest 9.x requires 3.10+, 3.9 is EOL)
- Windows 10/11 (dev machine is Windows, use `py -3` command)
- ANTHROPIC_API_KEY environment variable

**ScreenCast Studio files to reference:**
- `C:\ScreencastHelper\src\core\models.py` - Data model pattern
- `C:\ScreencastHelper\src\core\project_store.py` - Persistence pattern
- `C:\ScreencastHelper\src\ai\client.py` - Conversational AI client
- `C:\ScreencastHelper\src\utils\ai_client.py` - One-shot AI client
- `C:\ScreencastHelper\src\config.py` - Configuration pattern
- `C:\ScreencastHelper\app_v5.py` - Flask app structure
- `C:\ScreencastHelper\tests\conftest_v6.py` - Test fixtures
- `C:\ScreencastHelper\tests\test_v6_models.py` - Serialization tests

## Success Criteria Validation

How to verify each success criterion:

**1. Course, Module, Lesson, Activity dataclasses serialize/deserialize correctly**
- Write round-trip tests: `to_dict()` → JSON → `from_dict()` → assert equality
- Test with nested objects (Course → Modules → Lessons → Activities)
- Test enum conversion (BuildState, ContentType, BloomLevel)
- Test schema evolution (from_dict ignores unknown fields)

**2. ProjectStore persists course data with path traversal protection**
- Test save/load cycle with tmp_path fixture
- Test `_sanitize_id()` strips `/`, `\`, `..`
- Test ValueError on empty/invalid IDs
- Test directory creation (exports/, textbook/)
- Test list_courses returns metadata

**3. AI client completes chat requests with conversation history**
- Mock API with pytest-mock
- Test conversation history accumulation
- Test system prompt override
- Test streaming (generator yields text chunks)
- Test one-shot generate (no history pollution)

**4. Flask app runs on port 5003 with basic routes**
- Start app: `py -3 app.py`
- Visit http://127.0.0.1:5003/dashboard
- Test API: `curl http://127.0.0.1:5003/api/courses`
- Verify templates render
- Verify JSON responses parse

**5. File locking prevents race conditions**
- Run concurrent write test (threading)
- Verify final JSON is valid (not corrupted)
- Verify both writes succeed (not one lost)
- Test on Windows (msvcrt.locking)
- Test on Unix/WSL if available (fcntl.flock)

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| File locking doesn't work on Windows | High | Low | Test with msvcrt.locking early; fallback to filesystem-level advisory locking if needed |
| Dataclass schema evolution breaks | Medium | Low | Write tests for unknown field tolerance; version schema_version field |
| AI client API changes | Medium | Low | Pin anthropic>=0.77.0; monitor changelog; abstract behind interface |
| Course model too complex initially | Low | Medium | Start minimal (title, modules), add fields incrementally in later phases |
| Test coverage too low | Medium | Low | Run pytest --cov=src; require 80%+ before merging |

## Open Questions

None. Phase 1 is well-understood, standard Flask patterns with proven implementations to copy.

## Next Steps (For Planning)

When creating PLAN.md files:

1. **Plan 01-01 - Core Data Models:**
   - Define Course, Module, Lesson, Activity dataclasses
   - Define LearningOutcome, TextbookChapter
   - Define all enums (ContentType, BuildState, BloomLevel, WWHAAPhase, ActivityType)
   - Implement to_dict/from_dict with tests
   - Target: 200-300 lines in models.py, 100-150 lines in test_models.py

2. **Plan 01-02 - ProjectStore with File Locking:**
   - Implement ProjectStore (save, load, list_courses, delete)
   - Add platform-specific file locking (fcntl/msvcrt)
   - Path traversal protection (_sanitize_id)
   - Target: 120-150 lines in project_store.py, 80-100 lines in test_project_store.py

3. **Plan 01-03 - AI Client Abstraction:**
   - Conversational client (src/ai/client.py)
   - One-shot client (src/utils/ai_client.py)
   - Error handling (APIError, RateLimitError)
   - Target: 80-100 lines per client, 60-80 lines tests (mocked)

4. **Plan 01-04 - Flask App Skeleton:**
   - app.py with module-level singletons
   - Routes: /, /dashboard, /api/courses, /api/system/health
   - base.html and dashboard.html templates
   - Target: 100-150 lines in app.py, 50-80 lines tests

5. **Plan 01-05 - Configuration System:**
   - src/config.py with Config class
   - .env.example and .gitignore
   - ensure_dirs() method
   - Target: 80-100 lines in config.py, 30-50 lines tests

Each plan should:
- Reference specific ScreenCast Studio files to copy
- Include test strategy (round-trip, fixtures, mocking)
- Define acceptance criteria (run app, call API, verify output)
- Estimate lines of code (reality check scope)

## Research Confidence

**HIGH** - All patterns proven in ScreenCast Studio with 800 tests in production. Only addition is file locking (standard library, well-documented). Stack is stable (Flask 3.1.2, Anthropic SDK 0.77.0, Python 3.10+).

## Sources

1. **ScreenCast Studio Codebase** (C:\ScreencastHelper):
   - `src/core/models.py` - Dataclass pattern (149 lines)
   - `src/core/project_store.py` - Persistence pattern (94 lines)
   - `src/ai/client.py` - Conversational AI client (75 lines)
   - `src/utils/ai_client.py` - One-shot AI client (120 lines)
   - `src/config.py` - Configuration pattern (187 lines)
   - `app_v5.py` - Flask app structure (lines 1-149 examined)
   - `tests/conftest_v6.py` - Test fixtures (149 lines)
   - `tests/test_v6_models.py` - Serialization tests (first 100 lines examined)

2. **Course Builder Planning Docs** (C:\CourseBuilder\.planning):
   - `ROADMAP.md` - Phase 1 success criteria, dependencies
   - `REQUIREMENTS.md` - INFRA-01 through INFRA-04
   - `research/STACK.md` - Python 3.10+, Flask 3.1.2, dataclasses vs Pydantic
   - `research/SUMMARY.md` - File locking requirement, validation strategy

3. **Python Documentation**:
   - fcntl module (Unix file locking)
   - msvcrt module (Windows file locking)
   - dataclasses module (stdlib, Python 3.10+)

---

**Phase 1 Research Complete** - Ready for planning with high confidence in implementation approach.
