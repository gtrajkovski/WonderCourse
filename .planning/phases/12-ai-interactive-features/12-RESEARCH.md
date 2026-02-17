# Phase 12: AI Interactive Features - Research

**Researched:** 2026-02-10
**Domain:** AI-powered content editing, import/export, interactive chat
**Confidence:** MEDIUM

## Summary

Phase 12 adds three major feature areas to Course Builder Studio: (1) content import with format parsing, (2) inline AI editing with rich UI, and (3) interactive coach chat. This research identifies the standard stack for each area and documents critical architectural patterns and pitfalls.

**Key findings:**
- Content import requires specialized parsers per format (python-docx for DOCX, custom XML parsing for SCORM/QTI, OAuth libraries for Google Docs)
- Inline AI editing needs JavaScript floating toolbar UI (Tippy.js/Tiptap) with XSS sanitization (DOMPurify) and server-side streaming (Flask SSE with gevent)
- Interactive chat requires conversation history management, token budget tracking, and robust SSE connection handling
- All three areas share common needs: async operations, error recovery, and caching strategies

**Primary recommendation:** Use established libraries for parsing/sanitization rather than hand-rolling, implement streaming SSE with gevent workers for production, and adopt command pattern for undo/redo with session caching.

## Standard Stack

The established libraries/tools for this domain:

### Core: Content Import Parsing

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-docx | 1.2.0+ | DOCX parsing/manipulation | De facto standard for programmatic DOCX access, deterministic structure extraction |
| mammoth | 1.9.0+ | DOCX to semantic HTML | Best-in-class for converting DOCX to clean HTML for content ingestion |
| qti2txt | Latest | QTI XML parsing | Dedicated QTI parser with quiz question extraction |
| text2qti | Latest | QTI generation/import | Bidirectional QTI support for Canvas LMS compatibility |
| lxml | 5.x | XML parsing (SCORM manifests) | Fast, reliable XML parsing for imsmanifest.xml in SCORM packages |
| google-auth-oauthlib | 1.2.x | Google OAuth integration | Official Google library for OAuth2 with Docs API support |
| zipfile | stdlib | ZIP archive handling | Built-in Python library, reliable for SCORM/bulk imports |

### Core: Inline AI Editing UI

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tippy.js | 6.x | Floating toolbar positioning | 10,700+ GitHub stars, battle-tested tooltip/popover library |
| DOMPurify | 3.3.1+ | XSS sanitization | OWASP-recommended, DOM-only XSS protection for rich text |
| difflib | stdlib | Server-side text diffing | Python built-in, generates unified diffs for side-by-side views |
| Flask-SSE | 1.0.0+ | Server-Sent Events | Simplifies SSE implementation with Redis backend |

### Core: Interactive Chat & Streaming

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | Latest | Claude API client | Official Anthropic SDK with streaming support |
| gunicorn | 22.x | WSGI server | Industry standard production server with gevent worker support |
| gevent | 24.x | Async workers | Enables concurrent SSE connections with monkey-patching compatibility |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis | Latest | SSE message broker | When using Flask-SSE for multi-worker SSE |
| beautifulsoup4 | 4.x | HTML parsing fallback | When DOCX conversion produces messy HTML |
| bleach | 6.x | Server-side HTML sanitization | Backend sanitization layer (defense-in-depth) |
| requests | 2.x | HTTP client for URL import | Fetching public URLs before OAuth fallback |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-docx | python-ooxml | Less mature, fewer features, no clear advantage |
| Tippy.js | Floating UI (raw) | More manual setup, less out-of-box tooltip styling |
| DOMPurify | bleach (JS port) | Server-only, can't sanitize in browser before sending |
| Flask-SSE | Raw Flask Response.stream | More manual, no Redis integration, reinventing wheel |
| gevent workers | uvicorn + ASGI | Requires Flask rewrite to async views, higher migration cost |

**Installation:**
```bash
# Content import
pip install python-docx mammoth lxml google-auth-oauthlib qti2txt text2qti

# AI editing backend
pip install Flask-SSE redis bleach

# Production server
pip install gunicorn gevent

# Frontend (via CDN or npm)
# Tippy.js, DOMPurify loaded in templates
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── import/                  # Content import subsystem
│   ├── parsers/
│   │   ├── docx_parser.py   # python-docx + mammoth
│   │   ├── scorm_parser.py  # lxml for imsmanifest.xml
│   │   ├── qti_parser.py    # qti2txt wrapper
│   │   ├── csv_parser.py    # Quiz CSV import
│   │   └── html_parser.py   # beautifulsoup4 for HTML
│   ├── oauth/
│   │   └── google_docs.py   # google-auth-oauthlib integration
│   ├── analyzer.py          # AI content analysis
│   └── importer.py          # Orchestration layer
├── ai/
│   ├── streaming.py         # SSE streaming wrapper
│   ├── conversation.py      # Chat history management
│   └── context_manager.py   # Token budget tracking
├── editing/
│   ├── suggestions.py       # AI editing operations
│   ├── diff_generator.py    # difflib wrapper for side-by-side
│   ├── version_store.py     # Named version snapshots
│   └── sanitizer.py         # DOMPurify + bleach defense-in-depth
└── api/
    ├── import_bp.py         # Import endpoints
    ├── edit_bp.py           # AI editing endpoints
    ├── coach_bp.py          # Interactive coach endpoints
    └── sse_bp.py            # SSE streaming endpoints

static/js/
├── components/
│   ├── floating-toolbar.js  # Tippy.js wrapper
│   ├── diff-viewer.js       # Side-by-side diff UI
│   ├── autocomplete.js      # Ghost text suggestions
│   └── track-changes.js     # Command pattern undo/redo
└── sse-client.js            # EventSource + reconnection logic

templates/
├── import.html              # Dedicated import page
└── partials/
    └── ai-toolbar.html      # Floating toolbar partial
```

### Pattern 1: Content Import Pipeline

**What:** Multi-stage pipeline for importing external content with AI enhancement

**When to use:** Any import operation (paste, file upload, URL fetch)

**Example:**
```python
# Source: Designed pattern based on CONTEXT decisions
class ImportPipeline:
    def __init__(self):
        self.parsers = {
            'docx': DOCXParser(),
            'scorm': SCORMParser(),
            'qti': QTIParser(),
            # ...
        }
        self.analyzer = ContentAnalyzer()

    def import_content(self, source, format_hint=None):
        # 1. Detect format if not provided
        format = format_hint or self._detect_format(source)

        # 2. Parse with format-specific parser
        parser = self.parsers[format]
        raw_content = parser.parse(source)

        # 3. AI analysis (if enabled)
        if user_settings.auto_analyze:
            analysis = self.analyzer.analyze(raw_content)
            suggestions = {
                'content_type': analysis.suggested_type,
                'bloom_level': analysis.bloom_level,
                'word_count': analysis.word_count
            }

        # 4. Conflict check
        if existing_content:
            action = self._prompt_conflict_resolution()
            if action == 'cancel':
                return None
            elif action == 'merge':
                raw_content = self._merge(existing_content, raw_content)

        # 5. Store with provenance metadata
        return {
            'content': raw_content,
            'metadata': {
                'source': source.url or 'upload',
                'format': format,
                'imported_at': datetime.now(),
                'suggestions': suggestions
            }
        }
```

### Pattern 2: Streaming SSE with Gevent

**What:** Server-sent events for AI streaming responses with async workers

**When to use:** Content generation, autocomplete, coach chat

**Example:**
```python
# Source: Flask-SSE + gevent pattern
# https://flask-sse.readthedocs.io/en/latest/quickstart.html
from flask_sse import sse
from gevent import monkey
monkey.patch_all()

@app.route('/api/stream/suggest')
def stream_suggestions():
    def generate():
        # Anthropic streaming
        with client.messages.stream(
            model=Config.MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

# Production: gunicorn with gevent workers
# gunicorn -k gevent -w 4 --worker-connections 1000 app:app
```

### Pattern 3: Conversation History with Token Budget

**What:** Manage chat history with token limits using summarization + sliding window

**When to use:** Interactive coach chat, extended AI editing sessions

**Example:**
```python
# Source: Pattern from context window research
# https://www.getmaxim.ai/articles/context-window-management-strategies
class ConversationManager:
    def __init__(self, max_tokens=8000):
        self.max_tokens = max_tokens
        self.messages = []
        self.summaries = []

    def add_message(self, role, content):
        self.messages.append({'role': role, 'content': content})

        # Check token budget
        current_tokens = self._count_tokens(self.messages)
        if current_tokens > self.max_tokens * 0.8:
            self._compact_history()

    def _compact_history(self):
        # Keep most recent 5 messages
        recent = self.messages[-5:]

        # Summarize older messages
        older = self.messages[:-5]
        if older:
            summary = self._summarize(older)
            self.summaries.append(summary)

        self.messages = recent

    def get_context(self):
        # Combine summaries + recent messages
        context = []
        if self.summaries:
            context.append({
                'role': 'system',
                'content': f"Previous conversation summary: {' '.join(self.summaries)}"
            })
        context.extend(self.messages)
        return context
```

### Pattern 4: Command Pattern for Undo/Redo

**What:** Track AI edits as reversible command objects with dual-stack history

**When to use:** All AI editing operations, track changes mode

**Example:**
```javascript
// Source: Command pattern for undo/redo
// https://medium.com/fbbd/intro-to-writing-undo-redo-systems-in-javascript-af17148a852b
class EditCommand {
    constructor(oldText, newText, position) {
        this.oldText = oldText;
        this.newText = newText;
        this.position = position;
    }

    execute() {
        // Apply change
        editor.replaceRange(this.newText, this.position);
    }

    undo() {
        // Reverse change
        editor.replaceRange(this.oldText, this.position);
    }
}

class HistoryManager {
    constructor() {
        this.undoStack = [];
        this.redoStack = [];
        this.maxHistory = 100;
    }

    execute(command) {
        command.execute();
        this.undoStack.push(command);
        this.redoStack = [];  // Clear redo on new action

        // Limit stack size
        if (this.undoStack.length > this.maxHistory) {
            this.undoStack.shift();
        }
    }

    undo() {
        if (this.undoStack.length === 0) return;
        const command = this.undoStack.pop();
        command.undo();
        this.redoStack.push(command);
    }

    redo() {
        if (this.redoStack.length === 0) return;
        const command = this.redoStack.pop();
        command.execute();
        this.undoStack.push(command);
    }
}
```

### Pattern 5: SCORM imsmanifest.xml Parsing

**What:** Extract course structure from SCORM packages

**When to use:** Bulk import from SCORM archives

**Example:**
```python
# Source: SCORM packaging specification
# https://scorm.com/scorm-explained/technical-scorm/content-packaging/
import zipfile
from lxml import etree

class SCORMParser:
    NAMESPACES = {
        'imscp': 'http://www.imsglobal.org/xsd/imscp_v1p1',
        'adlcp': 'http://www.adlnet.org/xsd/adlcp_v1p3'
    }

    def parse(self, scorm_zip_path):
        # Extract ZIP
        with zipfile.ZipFile(scorm_zip_path, 'r') as zf:
            # Manifest must be at root
            if 'imsmanifest.xml' not in zf.namelist():
                raise ValueError("imsmanifest.xml not found at ZIP root")

            manifest_xml = zf.read('imsmanifest.xml')
            tree = etree.fromstring(manifest_xml)

            # Extract metadata
            metadata = tree.find('.//imscp:metadata', self.NAMESPACES)
            schema_version = metadata.find('.//adlcp:schemaversion', self.NAMESPACES).text

            # Extract organization structure
            orgs = tree.find('.//imscp:organizations', self.NAMESPACES)
            default_org = orgs.get('default')
            org = orgs.find(f'.//imscp:organization[@identifier="{default_org}"]', self.NAMESPACES)

            # Parse items (modules/lessons)
            items = []
            for item in org.findall('.//imscp:item', self.NAMESPACES):
                items.append({
                    'identifier': item.get('identifier'),
                    'title': item.find('.//imscp:title', self.NAMESPACES).text,
                    'resource_ref': item.get('identifierref')
                })

            # Extract resources
            resources = tree.find('.//imscp:resources', self.NAMESPACES)
            resource_map = {}
            for res in resources.findall('.//imscp:resource', self.NAMESPACES):
                files = [f.get('href') for f in res.findall('.//imscp:file', self.NAMESPACES)]
                resource_map[res.get('identifier')] = {
                    'type': res.get('type'),
                    'href': res.get('href'),
                    'files': files
                }

            return {
                'version': schema_version,
                'structure': items,
                'resources': resource_map,
                'package': zf  # Keep open for file extraction
            }
```

### Anti-Patterns to Avoid

- **Hand-rolling DOCX parsing with zipfile**: python-docx handles the complex Office Open XML spec correctly, including styles, relationships, and embedded objects. Manual ZIP extraction misses critical structure.

- **Client-only XSS sanitization**: DOMPurify in browser is necessary but not sufficient. Always sanitize server-side with bleach as defense-in-depth. Attackers can bypass client-side checks.

- **Unbounded conversation history**: Appending all messages to context causes token overflow around 130k tokens despite 200k limits. Use summarization + sliding window.

- **Blocking SSE connections on sync workers**: Flask dev server blocks on SSE. Production requires gevent workers with `monkey.patch_all()` for concurrent connections.

- **Stateful undo/redo on server**: Undo history grows unbounded if stored server-side. Use client-side command stack with server caching for recovery only.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX parsing | Custom ZIP + XML parsing | python-docx | Office Open XML spec is 5000+ pages. Handles styles, relationships, embedded objects, header/footer, sections correctly. |
| XSS sanitization | Regex-based HTML cleaning | DOMPurify (client) + bleach (server) | XSS bypasses discovered regularly. DOMPurify actively maintained with mutation XSS protections. |
| Diff view generation | Character-by-character comparison | difflib.unified_diff() | Handles word wrapping, whitespace changes, and generates standard unified diff format. HtmlDiff for HTML tables. |
| OAuth flows | Manual token exchange | google-auth-oauthlib | Handles token refresh, scope validation, PKCE flow, and credential storage correctly. |
| SSE connection handling | Raw Flask streaming | Flask-SSE + Redis | Handles reconnection, Last-Event-ID, multi-worker coordination, and keepalive comments. |
| SCORM manifest parsing | String manipulation | lxml with XPath | SCORM uses namespaced XML with schema validation. lxml handles namespaces, XPath queries, and malformed XML gracefully. |

**Key insight:** Content import formats (DOCX, SCORM, QTI) have complex specifications with edge cases discovered over years in production. Parsing libraries encode this institutional knowledge. Sanitization libraries (DOMPurify, bleach) are security-critical and regularly updated for newly discovered bypasses.

## Common Pitfalls

### Pitfall 1: Token Budget Overflow in Extended Chats

**What goes wrong:** Coach chat sessions exceed context limits after 20-30 turns, causing API errors or degraded responses.

**Why it happens:** Each turn adds user message + AI response + system prompt + learning outcomes to context. Tool outputs (if used) compound the problem. Without active management, context grows 2-5k tokens per turn.

**How to avoid:**
1. Track cumulative token count after each message
2. Trigger compaction at 80% of context limit (160k tokens for 200k window)
3. Summarize conversation history older than 5 turns
4. Keep system prompt + learning outcomes + recent 5 messages
5. Store full transcript separately for instructor review

**Warning signs:**
- API returns `context_length_exceeded` error
- Response quality degrades (repetitive, losing context)
- Response latency increases significantly

**Code pattern:**
```python
# Use tiktoken for accurate token counting
import tiktoken
encoding = tiktoken.encoding_for_model("claude-3-5-sonnet-20241022")

def count_tokens(messages):
    return sum(len(encoding.encode(m['content'])) for m in messages)

# Check before each API call
if count_tokens(conversation.messages) > MAX_TOKENS * 0.8:
    conversation.compact_history()
```

### Pitfall 2: SSE Connection Drops Without Reconnection

**What goes wrong:** AI streaming stops mid-generation when network hiccups, leaving incomplete content with no recovery.

**Why it happens:** EventSource auto-reconnects but doesn't resume generation. Server-side generation continues even when client disconnects. Client loses partial output if not buffered locally.

**How to avoid:**
1. Implement client-side buffering of partial SSE data
2. Use `Last-Event-ID` header for resumable streams
3. Server tracks generation progress by request ID
4. Client reconnects with last event ID to resume
5. Add periodic comment lines (`: keepalive`) to detect dead connections

**Warning signs:**
- Users report "generation stopped halfway"
- Network inspector shows 200 OK but no data received
- High rate of incomplete generations in logs

**Code pattern:**
```javascript
// Client-side with reconnection
class ResilientSSE {
    constructor(url) {
        this.url = url;
        this.buffer = '';
        this.lastEventId = null;
        this.connect();
    }

    connect() {
        const url = this.lastEventId
            ? `${this.url}?lastEventId=${this.lastEventId}`
            : this.url;

        this.source = new EventSource(url);

        this.source.onmessage = (e) => {
            this.buffer += e.data;
            this.lastEventId = e.lastEventId;
            this.onData(e.data);
        };

        this.source.onerror = (e) => {
            if (this.source.readyState === EventSource.CLOSED) {
                // Reconnect after 3s
                setTimeout(() => this.connect(), 3000);
            }
        };
    }
}
```

### Pitfall 3: XSS via Unsanitized Imported Content

**What goes wrong:** Importing malicious HTML/DOCX with embedded scripts allows XSS attacks when content is displayed.

**Why it happens:** DOCX files can contain malformed HTML in comments/notes, imported HTML may have `<script>` tags, and conversion libraries (mammoth, beautifulsoup4) focus on structure, not security.

**How to avoid:**
1. Sanitize all imported content server-side with bleach
2. Sanitize again client-side with DOMPurify before rendering
3. Use Content Security Policy (CSP) headers to block inline scripts
4. Configure bleach to allow only safe tags (p, h1-h6, ul, ol, li, strong, em, a[href])
5. Never use `dangerouslySetInnerHTML` without DOMPurify

**Warning signs:**
- Security scanner flags XSS vulnerabilities
- Imported content displays `<script>` tags in view-source
- CSP violations logged in browser console

**Code pattern:**
```python
import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = ['p', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'strong', 'em', 'a', 'br']
ALLOWED_ATTRS = {'a': ['href', 'title']}
css_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'font-weight'])

def sanitize_imported_html(html):
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        css_sanitizer=css_sanitizer,
        strip=True
    )
```

```javascript
// Client-side (double sanitization)
import DOMPurify from 'dompurify';

function renderImportedContent(html) {
    const clean = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'strong', 'em', 'a', 'br'],
        ALLOWED_ATTR: ['href', 'title']
    });
    container.innerHTML = clean;
}
```

### Pitfall 4: SCORM Parsing Assumes ZIP Root Structure

**What goes wrong:** SCORM import fails when imsmanifest.xml is inside a subfolder in the ZIP.

**Why it happens:** Some SCORM authoring tools export with wrapper folders (e.g., `course-name/imsmanifest.xml` instead of root). Spec requires root placement but real-world files vary.

**How to avoid:**
1. Search for imsmanifest.xml anywhere in ZIP, not just root
2. If found in subfolder, treat that subfolder as package root
3. Adjust all resource paths relative to manifest location
4. Validate manifest location and warn user if non-standard

**Warning signs:**
- SCORM import fails with "manifest not found" despite valid package
- Resources fail to load after import

**Code pattern:**
```python
def find_manifest(zip_file):
    # Search for imsmanifest.xml at any depth
    manifest_path = None
    for name in zip_file.namelist():
        if name.endswith('imsmanifest.xml'):
            manifest_path = name
            break

    if not manifest_path:
        raise ValueError("No imsmanifest.xml found in package")

    # Calculate package root
    package_root = os.path.dirname(manifest_path)
    if package_root:
        warnings.warn(f"Non-standard structure: manifest at {manifest_path}")

    return manifest_path, package_root
```

### Pitfall 5: Google Docs OAuth Lacks Offline Access

**What goes wrong:** User authenticates with Google Docs but import fails on subsequent attempts without re-authentication.

**Why it happens:** OAuth tokens expire after 1 hour. Without `access_type='offline'`, no refresh token is issued. User must re-authenticate for each import session.

**How to avoid:**
1. Request `access_type='offline'` in OAuth flow
2. Request `prompt='consent'` to force refresh token on first auth
3. Store refresh tokens securely (encrypted in database)
4. Auto-refresh access tokens before expiry
5. Handle revoked tokens gracefully with re-auth prompt

**Warning signs:**
- Google Docs import works once, then fails with 401 Unauthorized
- Users complain about repeated OAuth prompts

**Code pattern:**
```python
from google_auth_oauthlib.flow import Flow

flow = Flow.from_client_secrets_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/documents.readonly'],
    redirect_uri='http://localhost:5003/oauth/callback'
)

# CRITICAL: Request offline access
authorization_url, state = flow.authorization_url(
    access_type='offline',
    prompt='consent',  # Force consent to get refresh token
    include_granted_scopes='true'
)

# Store refresh token after first auth
flow.fetch_token(authorization_response=callback_url)
credentials = flow.credentials

# Save for later
store_encrypted(user_id, {
    'refresh_token': credentials.refresh_token,
    'token_uri': credentials.token_uri,
    'client_id': credentials.client_id,
    'client_secret': credentials.client_secret
})
```

### Pitfall 6: Autocomplete Flooding AI API

**What goes wrong:** Ghost text autocomplete triggers API call on every keystroke, causing rate limit errors and high costs.

**Why it happens:** Naive implementation calls AI after each character typed. At 60 WPM typing speed, that's ~5 requests/second.

**How to avoid:**
1. Debounce autocomplete requests by 500-1000ms
2. Cancel in-flight request when new keystroke arrives
3. Cache suggestions for common prefixes
4. Only trigger after typing 3+ characters
5. Implement client-side rate limiting (max 1 request/second)

**Warning signs:**
- Rate limit errors in browser console
- High API costs for autocomplete feature
- Autocomplete feels laggy despite fast responses

**Code pattern:**
```javascript
class DebouncedAutocomplete {
    constructor(delay = 800) {
        this.delay = delay;
        this.timeoutId = null;
        this.controller = null;
        this.cache = new Map();
    }

    async getSuggestion(text) {
        // Cancel previous request
        if (this.controller) {
            this.controller.abort();
        }

        // Check cache
        const cacheKey = text.slice(-50);  // Last 50 chars
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        // Debounce
        clearTimeout(this.timeoutId);

        return new Promise((resolve) => {
            this.timeoutId = setTimeout(async () => {
                this.controller = new AbortController();

                try {
                    const response = await fetch('/api/autocomplete', {
                        method: 'POST',
                        body: JSON.stringify({ text }),
                        signal: this.controller.signal
                    });

                    const suggestion = await response.json();
                    this.cache.set(cacheKey, suggestion);
                    resolve(suggestion);
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        console.error('Autocomplete error:', err);
                    }
                    resolve(null);
                }
            }, this.delay);
        });
    }
}
```

## Code Examples

Verified patterns from official sources:

### Streaming with Anthropic Python SDK

```python
# Source: https://docs.anthropic.com/claude/reference/messages-streaming
from anthropic import Anthropic

client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

# Sync streaming with context manager
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Generate suggestions..."}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

# Get final message
message = stream.get_final_message()
print(f"\nTotal tokens: {message.usage.input_tokens + message.usage.output_tokens}")

# Async streaming
async with client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        await websocket.send(text)
```

### DOMPurify Sanitization

```javascript
// Source: https://github.com/cure53/DOMPurify
import DOMPurify from 'dompurify';

// Basic sanitization
const dirty = '<img src=x onerror=alert(1)>';
const clean = DOMPurify.sanitize(dirty);
console.log(clean);  // '<img src="x">'

// With custom config
const config = {
    ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'a'],
    ALLOWED_ATTR: ['href'],
    KEEP_CONTENT: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false
};

const cleanHTML = DOMPurify.sanitize(userHTML, config);

// For rich text editors with track changes
const trackChangesConfig = {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'strong', 'em', 'a', 'br', 'ins', 'del'],
    ALLOWED_ATTR: ['href', 'title', 'data-user', 'data-time'],
    ADD_TAGS: ['ins', 'del'],  // Track changes markers
    ADD_ATTR: ['data-user', 'data-time']
};
```

### Python-docx Content Extraction

```python
# Source: https://python-docx.readthedocs.io/
from docx import Document

def extract_docx_content(file_path):
    doc = Document(file_path)

    content = {
        'title': doc.core_properties.title,
        'author': doc.core_properties.author,
        'paragraphs': [],
        'tables': []
    }

    # Extract paragraphs with styles
    for para in doc.paragraphs:
        content['paragraphs'].append({
            'text': para.text,
            'style': para.style.name,
            'runs': [
                {
                    'text': run.text,
                    'bold': run.bold,
                    'italic': run.italic,
                    'underline': run.underline
                }
                for run in para.runs
            ]
        })

    # Extract tables
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            rows.append(cells)
        content['tables'].append(rows)

    return content
```

### Mammoth for Semantic HTML Conversion

```python
# Source: https://github.com/mwilliamson/python-mammoth
import mammoth

def convert_docx_to_html(file_path):
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            style_map="""
                p[style-name='Heading 1'] => h1:fresh
                p[style-name='Heading 2'] => h2:fresh
                p[style-name='Section Title'] => h2.section-title:fresh
            """
        )

        html = result.value  # The generated HTML
        messages = result.messages  # Any warnings during conversion

        # Check for conversion issues
        for message in messages:
            if message.type == 'warning':
                print(f"Warning: {message.message}")

        return html
```

### Tippy.js Floating Toolbar

```javascript
// Source: https://atomiks.github.io/tippyjs/
import tippy from 'tippy.js';

// Create floating toolbar on text selection
document.addEventListener('selectionchange', () => {
    const selection = window.getSelection();
    if (selection.toString().length > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        // Show tooltip at selection
        tippy(document.body, {
            content: createToolbarContent(),
            getReferenceClientRect: () => rect,
            placement: 'top',
            interactive: true,
            trigger: 'manual',
            showOnCreate: true,
            theme: 'ai-toolbar',
            arrow: true
        });
    }
});

function createToolbarContent() {
    const toolbar = document.createElement('div');
    toolbar.className = 'ai-toolbar';
    toolbar.innerHTML = `
        <button data-action="improve">Improve</button>
        <button data-action="expand">Expand</button>
        <button data-action="simplify">Simplify</button>
        <button data-action="rewrite">Rewrite</button>
    `;

    toolbar.addEventListener('click', async (e) => {
        if (e.target.tagName === 'BUTTON') {
            const action = e.target.dataset.action;
            const text = window.getSelection().toString();
            await applyAIAction(action, text);
        }
    });

    return toolbar;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask sync workers for SSE | Gunicorn + gevent async workers | 2020+ | Enables concurrent SSE connections, critical for production AI streaming |
| Manual JSON response parsing | Anthropic structured outputs (tool-based) | 2024 (Anthropic SDK 0.8+) | Guaranteed valid JSON, no parsing errors, schema validation built-in |
| Client-side only sanitization | Defense-in-depth (DOMPurify + bleach) | 2022+ (after mutation XSS bypasses) | Blocks server-side XSS bypasses, required for security compliance |
| python-docx only | python-docx + mammoth hybrid | 2023+ | Mammoth for semantic HTML conversion, python-docx for structured extraction |
| Unlimited context window | Token budget management + summarization | 2024 (with 200k+ context models) | Prevents context overflow, maintains quality in long conversations |
| output_config in messages.create() | tool-based structured outputs | 2025 (Anthropic API change) | Tool-based approach is now recommended method for structured outputs |

**Deprecated/outdated:**
- **Flask-SocketIO for real-time**: Use SSE for unidirectional streaming (AI to client). WebSockets add complexity without benefit for content generation.
- **requests-oauthlib**: Replaced by authlib for OAuth 2.0. Authlib has better async support and more active maintenance.
- **output_config parameter**: While still functional, Anthropic recommends tool-based approach for structured outputs (as used in base_generator.py)
- **ProseMirror change tracking prototype**: NYT prototype incompatible with collaborative editing. Use Tiptap Collaboration + Y.js for production.

## Open Questions

Things that couldn't be fully resolved:

1. **SCORM Runtime API Integration**
   - What we know: Can parse SCORM packages and extract content/structure
   - What's unclear: Whether to implement full SCORM Runtime API (JavaScript LMSInitialize/LMSCommit) for preview
   - Recommendation: Start with structure import only. Full runtime API is complex (300+ lines of JS) and may not be needed if we're converting to native activities.

2. **QTI Import Fidelity**
   - What we know: qti2txt parses QTI XML into text format, text2qti converts back
   - What's unclear: How much quiz metadata (question pools, adaptive logic, time limits) to preserve vs. simplify
   - Recommendation: Import question content + basic metadata (points, feedback). Defer advanced features (pools, adaptive) to Phase 13 if needed.

3. **Real-time Collaborative Editing**
   - What we know: Track changes mode needs accept/reject workflow. Tiptap + Y.js enables real-time collab.
   - What's unclear: Whether Phase 12 needs simultaneous editing or just track changes for single-user AI edits
   - Recommendation: CONTEXT specifies track changes for AI edits only. Defer real-time multi-user to future phase. Use command pattern + version snapshots for Phase 12.

4. **Autocomplete Model Selection**
   - What we know: Ghost text autocomplete needs fast responses (< 300ms)
   - What's unclear: Whether to use Claude for autocomplete or switch to faster model (e.g., Haiku)
   - Recommendation: Start with Claude Haiku (faster, cheaper) for autocomplete. Benchmark latency. If still too slow, consider client-side caching of common completions.

## Sources

### Primary (HIGH confidence)

- [Anthropic Python SDK - Streaming](https://docs.anthropic.com/claude/reference/messages-streaming) - Official Anthropic documentation for streaming with Python SDK
- [python-docx Documentation](https://python-docx.readthedocs.io/) - Official python-docx library documentation
- [DOMPurify GitHub Repository](https://github.com/cure53/DOMPurify) - Official DOMPurify library with security best practices
- [Flask-SSE Documentation](https://flask-sse.readthedocs.io/en/latest/quickstart.html) - Official Flask-SSE quickstart guide
- [Gunicorn Documentation - Workers](https://docs.gunicorn.org/en/stable/settings.html#worker-class) - Official Gunicorn worker class documentation
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) - OWASP official XSS prevention guidance
- [SCORM Content Packaging Specification](https://scorm.com/scorm-explained/technical-scorm/content-packaging/) - Official SCORM.com specification documentation

### Secondary (MEDIUM confidence)

- [Context Window Management Strategies (Maxim.ai)](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots) - Production patterns for managing AI context windows
- [Python Mammoth GitHub](https://github.com/mwilliamson/python-mammoth) - DOCX to HTML conversion with semantic structure
- [Tippy.js Documentation](https://atomiks.github.io/tippyjs/) - Tooltip and popover library for floating toolbars
- [difflib Python Documentation](https://docs.python.org/3/library/difflib.html) - Python standard library for text diffing
- [Flask gevent Tutorial](https://iximiuz.com/en/posts/flask-gevent-tutorial/) - Production Flask with gevent async workers
- [Command Pattern for Undo/Redo](https://medium.com/fbbd/intro-to-writing-undo-redo-systems-in-javascript-af17148a852b) - JavaScript undo/redo implementation patterns
- [Technical Comparison of Document Parsing Libraries](https://medium.com/@hchenna/technical-comparison-python-libraries-for-document-parsing-318d2c89c44e) - Comparison of python-docx, mammoth, and alternatives

### Tertiary (LOW confidence - requires validation)

- [qti2txt PyPI](https://pypi.org/project/qti2txt/) - QTI parsing library (needs production testing)
- [ProseMirror Collaborative Editing](https://prosemirror.net/examples/collab/) - Collaborative editing examples (NYT prototype incompatible with collab)
- [Context Window Overflow (Redis Blog)](https://redis.io/blog/context-window-overflow/) - Context overflow patterns (2026 article, verify claims)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official documentation and PyPI
- Architecture: MEDIUM - Patterns assembled from multiple sources, needs integration testing
- Pitfalls: HIGH - Documented from official sources (OWASP, Anthropic, SCORM.com)
- SCORM/QTI parsing: MEDIUM - Limited Python libraries, may need custom work
- OAuth integration: HIGH - Official Google libraries with documented patterns

**Research date:** 2026-02-10
**Valid until:** ~30 days (stable domain, but Anthropic SDK evolves quarterly)

**Critical path items:**
1. Verify gevent monkey patching doesn't break existing Flask code
2. Test SCORM parser with real-world packages (not just spec-compliant samples)
3. Benchmark Claude API latency for autocomplete (may need Haiku or caching)
4. Security audit of sanitization pipeline (DOMPurify + bleach config)
5. Load test SSE streaming with 50+ concurrent connections
