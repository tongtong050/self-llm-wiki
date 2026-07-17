"""
Shared utilities for LLM Wiki tools.

Centralizes functions that were previously copy-pasted across tool files:
read_file, write_file, call_llm, sha256, extract_wikilinks, all_wiki_pages, append_log.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────

def _resolve_root() -> Path:
    """Resolve REPO_ROOT from env var or auto-detect from script location."""
    env = os.getenv("LLM_WIKI_ROOT", "")
    if env:
        p = Path(env)
        if not p.is_absolute():
            # Relative path → resolve against script location's parent
            script_parent = Path(__file__).resolve().parent.parent
            p = (script_parent / p).resolve()
        return p
    return Path(__file__).resolve().parent.parent

REPO_ROOT = _resolve_root()

def _resolve_subdir(env_var: str, default_rel: str) -> Path:
    """Resolve a subdirectory from env var, relative to REPO_ROOT."""
    env = os.getenv(env_var, "")
    if env:
        p = Path(env)
        if not p.is_absolute():
            return (REPO_ROOT / p).resolve()
        return Path(p)
    return REPO_ROOT / default_rel

WIKI_DIR = _resolve_subdir("LLM_WIKI_WIKI_DIR", "06-Wiki")
GRAPH_DIR = _resolve_subdir("LLM_WIKI_GRAPH_DIR", "06-Wiki/graph")
SCHEMA_FILE = REPO_ROOT / "CLAUDE.md"

# 产出目录下的关键文件
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
OVERVIEW_FILE = WIKI_DIR / "overview.md"
HOT_FILE = WIKI_DIR / "hot.md"

# review 与缓存放 07-系统（系统运行文件区）
_SYS_DIR = REPO_ROOT / "07-系统"
REVIEW_FILE = _SYS_DIR / "review.md"
CACHE_FILE = _SYS_DIR / ".ingest-cache.json"
PIPELINE_LOG_FILE = _SYS_DIR / "pipeline-log.md"
COLLISION_FILE = _SYS_DIR / ".collision-candidates.json"
EMBED_CACHE_FILE = _SYS_DIR / ".embed-cache.json"

# Default metadata files to exclude from wiki page listings.
_META_EXCLUDE = {"index.md", "log.md", "lint-report.md", "hot.md"}


# ── Source directory configuration ─────────────────────────────────────

# 素材目录映射表
# key: 目录名, value: (模板名, frontmatter type 值)
_SOURCE_DIR_MAP: dict[str, tuple[str, str]] = {
    "00-灵感库":    ("Inspiration", "inspiration"),
    "01-项目":      ("Card",        "card"),
    "02-长期关注":  ("Card",        "card"),
    "03-参考资料":  ("Reference",   "reference"),
}

# 排除的目录名
_EXCLUDE_DIR_NAMES = {"04-归档", "05-Skills", "06-Wiki", "07-系统", "08-创作", ".obsidian", ".claude", ".git"}


def get_source_dirs() -> list[Path]:
    """Return source directories to scan for ingest material.

    Priority: LLM_WIKI_SOURCE_DIRS env var (comma-separated) > REPO_ROOT traversal.
    """
    env = os.getenv("LLM_WIKI_SOURCE_DIRS", "")
    if env:
        return [Path(d.strip()) for d in env.split(",") if d.strip()]
    # Default: look for numbered directories under REPO_ROOT
    candidates = []
    for name in _SOURCE_DIR_MAP:
        p = REPO_ROOT / name
        if p.is_dir():
            candidates.append(p)
    return candidates or [REPO_ROOT / "raw"]


def get_exclude_dirs() -> set[str]:
    """Return directory names to exclude from scanning."""
    env = os.getenv("LLM_WIKI_EXCLUDE_DIRS", "")
    if env:
        return set(d.strip() for d in env.split(",") if d.strip())
    return _EXCLUDE_DIR_NAMES


def identify_template(file_path: str | Path,
                      frontmatter: dict | None = None) -> str:
    """Identify which Domain template to use for a source file.

    Priority:
      1. frontmatter 'type' field → direct map
      2. parent directory name → directory map
      3. fallback → "General"
    """
    path = Path(file_path)

    # Priority 1: frontmatter type
    if frontmatter and frontmatter.get("type"):
        fm_type = str(frontmatter["type"]).strip().lower()
        for _name, (_tmpl, _type_val) in _SOURCE_DIR_MAP.items():
            if _type_val == fm_type:
                return _tmpl

    # Priority 2: directory-based
    for part in path.parts:
        if part in _SOURCE_DIR_MAP:
            return _SOURCE_DIR_MAP[part][0]

    # Priority 3: fallback
    return "General"


def should_exclude(file_path: str | Path, exclude_dirs: set[str] | None = None) -> bool:
    """Check if a file is under an excluded directory."""
    if exclude_dirs is None:
        exclude_dirs = get_exclude_dirs()
    path = Path(file_path)
    parts = set(path.parts)
    return bool(parts & exclude_dirs)


# ── File I/O ───────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    """Read file contents as UTF-8. Returns empty string if file doesn't exist."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_file(path: Path, content: str):
    """Write UTF-8 content to file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    print(f"  wrote: {rel}")


# ── LLM ────────────────────────────────────────────────────────────────

def call_llm(
    prompt: str,
    model_env: str = "LLM_MODEL",
    default_model: str = "anthropic/claude-3-5-sonnet-latest",
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> str:
    """Call an LLM via litellm.

    Args:
        prompt: The user prompt.
        model_env: Environment variable name for model selection.
        default_model: Fallback model if env var is unset.
        max_tokens: Maximum response tokens.  0 or None to omit the limit.
        temperature: Sampling temperature.  None to omit (litellm default).
    """
    try:
        from litellm import completion
    except ImportError:
        print("Error: litellm not installed. Run: pip install litellm")
        sys.exit(1)

    model = os.getenv(model_env, default_model)

    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = completion(**kwargs)
    return response.choices[0].message.content


# ── Hashing ────────────────────────────────────────────────────────────

def sha256(text: str, truncate: int = 0) -> str:
    """SHA-256 hex digest of *text*, optionally truncated to *truncate* chars.

    Default is the full 64-char hash.  Pass truncate=16 for the short form
    used by ingest.py and refresh.py.
    """
    h = hashlib.sha256(text.encode()).hexdigest()
    return h[:truncate] if truncate else h


# ── Wiki helpers ───────────────────────────────────────────────────────

def extract_wikilinks(content: str, unique: bool = False) -> list[str]:
    """Extract all [[WikiLink]] targets from page content.

    Args:
        unique: Deduplicate results (used by build_graph.py).
    """
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    return list(set(links)) if unique else links


def all_wiki_pages(extra_exclude: set[str] | None = None) -> list[Path]:
    """Return all .md files in wiki/, excluding metadata files.

    Args:
        extra_exclude: Additional filenames to skip (e.g. {"health-report.md"}).
    """
    exclude = _META_EXCLUDE | (extra_exclude or set())
    return [p for p in WIKI_DIR.rglob("*.md") if p.name not in exclude]


def append_log(entry: str):
    """Prepend a log entry to wiki/log.md (newest-first).

    Creates the file with a standard header if it doesn't exist.
    Preserves the prepend semantics used by ingest.py, query.py, and lint.py.
    """
    entry_text = entry.strip()

    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            "# Wiki Log\n\n"
            "> Records important additions, revisions, and clarifications in the "
            "project knowledge layer. Maintained in append-only mode for agent and "
            "human traceability.\n\n"
            f"{entry_text}\n",
            encoding="utf-8",
        )
        return

    existing = read_file(LOG_FILE).rstrip()
    if not existing:
        existing = (
            "# Wiki Log\n\n"
            "> Records important additions, revisions, and clarifications in the "
            "project knowledge layer. Maintained in append-only mode for agent and "
            "human traceability."
        )
    LOG_FILE.write_text(existing + "\n\n" + entry_text + "\n", encoding="utf-8")


# ── Ingest cache ───────────────────────────────────────────────────────

def load_ingest_cache() -> dict:
    """Load the ingest change-detection cache."""
    import json
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def save_ingest_cache(cache: dict):
    """Persist the ingest change-detection cache."""
    import json
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def is_source_changed(source_path: str | Path, content: str) -> bool:
    """Check if a source file needs (re)ingestion.

    Returns True if the file is new or its content hash changed.
    """
    cache = load_ingest_cache()
    key = str(source_path)
    current_hash = sha256(content, truncate=16)

    if key not in cache:
        return True
    entry = cache[key]
    if entry.get("hash") != current_hash:
        return True
    return False


def update_ingest_cache(source_path: str | Path, content: str):
    """Update the cache entry for a successfully ingested source."""
    import datetime
    cache = load_ingest_cache()
    key = str(source_path)
    cache[key] = {
        "hash": sha256(content, truncate=16),
        "last_ingest": datetime.datetime.now().isoformat(),
    }
    save_ingest_cache(cache)


# ── hot.md ─────────────────────────────────────────────────────────────

def update_hot_md(operation: str, details: dict | None = None):
    """Update wiki/hot.md session context cache. Keep under ~500 words."""
    from datetime import datetime

    details = details or {}
    now = datetime.now().isoformat(timespec="minutes")

    # Build new entry
    entries = [f"## Recent Operations\n- `{operation}` {now}"]
    if details.get("source"):
        entries.append(f"- Source: {details['source']}")
    if details.get("entities"):
        entities_str = ", ".join(f"[[{e}]]" for e in details["entities"][:5])
        entries.append(f"- Entities: {entities_str}")
    if details.get("concepts"):
        concepts_str = ", ".join(f"[[{c}]]" for c in details["concepts"][:5])
        entries.append(f"- Concepts: {concepts_str}")

    # Read existing to preserve non-recent-ops sections
    existing = read_file(HOT_FILE)
    recent_section = "\n".join(entries)

    # Keep overview section if present
    overview = ""
    if existing and "## Wiki Overview" in existing:
        parts = existing.split("## Recent Operations")
        overview = parts[0].strip()

    # Assemble — keep under 500 words
    body = recent_section
    if overview:
        body = overview + "\n\n" + body
    words = body.split()
    if len(words) > 500:
        body = " ".join(words[-450:])  # keep last ~450 words

    frontmatter = f"---\nupdated: {now}\nlast_operation: {operation}\n---\n\n"
    write_file(HOT_FILE, frontmatter + body + "\n")


# ── File locking ───────────────────────────────────────────────────────

def acquire_lock(file_path: str | Path, timeout: int = 60) -> bool:
    """Acquire a file-level write lock. Returns False on timeout."""
    import time
    lock_path = Path(str(file_path) + ".lock")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except (FileExistsError, OSError):
            try:
                lock_mtime = lock_path.stat().st_mtime
                if time.time() - lock_mtime > 60:
                    lock_path.unlink()
                    continue
            except (FileNotFoundError, PermissionError):
                continue
            time.sleep(0.5)
    return False


def release_lock(file_path: str | Path):
    """Release a file-level write lock."""
    lock_path = Path(str(file_path) + ".lock")
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def safe_write(file_path: str | Path, content: str, timeout: int = 60) -> bool:
    """Lock → write → unlock. Returns False if lock acquisition failed."""
    p = Path(file_path)
    if not acquire_lock(p, timeout=timeout):
        print(f"  ⚠️  Lock timeout: {p}")
        return False
    try:
        write_file(p, content)
        return True
    finally:
        release_lock(p)


def write_page_safe(path: str | Path, content: str, timeout: int = 60) -> bool:
    """Write a wiki page under WIKI_DIR with lock safety."""
    return safe_write(WIKI_DIR / path, content, timeout=timeout)


# ── Frontmatter helpers ────────────────────────────────────────────────

def read_frontmatter(file_path: str | Path) -> dict | None:
    """Read YAML frontmatter from a markdown file. Returns None on failure."""
    import yaml
    content = read_file(Path(file_path))
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(content[3:end]) or {}
    except Exception:
        return None


def write_frontmatter_field(file_path: str | Path, field: str, value):
    """Add or update a field in a markdown file's YAML frontmatter.
    Only writes if the file exists and has valid frontmatter.
    """
    p = Path(file_path)
    content = read_file(p)
    if not content.startswith("---"):
        return
    end = content.find("---", 3)
    if end == -1:
        return

    import yaml
    try:
        fm = yaml.safe_load(content[3:end]) or {}
    except Exception:
        return

    fm[str(field)] = value
    new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False).strip()
    new_content = "---\n" + new_fm + "\n---" + content[end + 3:]
    safe_write(p, new_content)


def mark_as_ingested(source_path: str | Path):
    """Add wiki: true and last_wiki_update to a source file's frontmatter."""
    from datetime import date
    write_frontmatter_field(source_path, "wiki", True)
    write_frontmatter_field(source_path, "last_wiki_update", date.today().isoformat())


# ── Page merge ─────────────────────────────────────────────────────────

MERGE_PROMPT_TEMPLATE = """You are merging two versions of the same wiki page. Both versions contain valid information about the same subject from different sources.

## Existing page (on disk)
{existing_content}

## Incoming page (from new source: {source_file})
{incoming_content}

## Page path
{page_path}

## Merge Rules (STRICT)

1. **Preserve ALL facts** — Do not drop any factual claim from either version.
2. **Deduplicate** — When both versions state the same fact, keep it once (keep the better-written version).
3. **Mark conflicts** — When claims are contradictory, keep BOTH and wrap in:
   ```
   > [!conflict] 以下来源对同一主题的描述不一致
   > - 来源 A: {{claim_a}}
   > - 来源 B: {{claim_b}}
   ```
   Never silently choose one side.
4. **Reorganize** — Restructure sections logically. Do not just concatenate.
5. **Keep [[wikilinks]]** — Preserve all cross-references.
6. **Merge frontmatter** — Combine tags[], sources[], related[] arrays and deduplicate. Keep the earlier `created` date. Set `last_updated` to today.

## Output

Output the COMPLETE merged page (frontmatter + body). No preamble, no explanation.
The FIRST character must be `---` (start of frontmatter)."""


def merge_pages(existing_content: str, incoming_content: str,
                page_path: str, source_file: str,
                model_env: str = "LLM_MODEL") -> str:
    """LLM merge two versions of the same wiki page. Returns merged content."""
    prompt = MERGE_PROMPT_TEMPLATE.format(
        existing_content=existing_content,
        incoming_content=incoming_content,
        page_path=page_path,
        source_file=source_file,
    )
    raw = call_llm(prompt, model_env=model_env, max_tokens=4096)
    return raw


# ── Context budget helpers ─────────────────────────────────────────────

def clip_page_content(content: str, max_chars: int = 3000) -> str:
    """Truncate page content at a word boundary for context budget control."""
    if len(content) <= max_chars:
        return content
    clipped = content[:max_chars - 3].rsplit(" ", 1)[0].rstrip()
    return clipped + "..."
