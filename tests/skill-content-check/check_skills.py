#!/usr/bin/env python3
"""Static conformance check for the skills in this repository.

Verifies that each skill is Qt 5 / Qt Widgets-only, tool-agnostic,
self-contained and structurally valid. Python 3.6+; PyYAML is used when
available and a fallback parser is used otherwise.

    python3 tests/skill-content-check/check_skills.py [repo_root] [--isolate] [--qt-sweep]

  --isolate   additionally copy each skill into a temporary directory on its own
              and re-scan it there, which proves nothing resolves outside the
              skill directory.

  --qt-sweep  advisory: print Qt-like tokens from the skills that appear in no
              header of the Qt 5 installation. Never a finding, never an exit
              code change — it exists to point a human at claims worth adding
              to the registers below.

Checks that are derived from source rather than from prose
---------------------------------------------------------
Several statements in this repository are facts about other files in it: how
many rule ids the linter registers, which rule categories exist, which files a
skill contains, which Qt version the source actually requires, whether the four
"Core bans" blocks are still identical. Prose that restates them drifts, so each
is computed here and compared with the text that claims it (COUNTS, CATEGORY,
FILESBLOCK, PYFLOOR, BANSYNC, SEVERITY, IDSPACE).

The existence registers (QT5REG / QT6REG / QTPRESENT / QTBAN) are the executable
form of the rule "every Qt 5 / Qt 6 existence claim is checked against a real
Qt 5 installation". `qt5-symbols.txt` lists what the skills assert Qt 5 has, and
must be verifiable in its public headers (plus `lib/cmake` for build-file
symbols); `qt6-symbols.txt` lists what they assert Qt 5 does not have. The
installation is read from $QT5_DIR, else from a few well-known prefixes; when no
installation is found the existence checks are skipped with a message, and the
exit code is unaffected. CMake/tool behaviour claims that need running a
compiler or a build stay manual — see R4 in README.

Design of the content checks
----------------------------
Prose in this repository deliberately *names* Qt 6 and QML constructs in order
to forbid them, so a plain text search would be all false positives. The Qt 6 /
QML checks therefore fire only where the name would actually be emitted:

  * inside a fenced code block whose info string is a build/source language
    (cmake, cpp, c, h, bat, sh, xml, qmake, pro, qml), or
  * on a prose line that uses the construct as code — a call form like
    `qt_add_qml_module(`, a link target like `Qt6::Widgets`, or a file path
    ending in `.qml` / `qmldir`.

Names appearing in backticks or in ordinary sentences are treated as
documentation about the ban and are not findings.

Exit code: 0 clean, 1 findings, 2 usage problem.
Output lines: FILE:LINE CHECK message
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml  # optional; a fallback parser is used when absent
except Exception:  # pragma: no cover
    yaml = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Skills that used to exist here and must never be referenced again.
REMOVED_SKILLS = [
    "qt-canvas2d", "qt-qml", "qt-qml-docs", "qt-qml-profiler", "qt-qml-review",
    "qt-qml-test", "qt-qml-test-run", "qt-figma-token-extraction",
    "qt-figma-component-generation",
]

# Qt 6 CMake commands / targets, Qt 6-only C++ symbols, QML plumbing.
QT6_CODE_TOKENS = [
    (r"\bqt_standard_project_setup\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_executable\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_library\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_qml_module\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_translations?\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_shaders\s*\(", "Qt 6 CMake command"),
    (r"\bqt_add_plugin\s*\(", "Qt 6 CMake command"),
    (r"\bqt_deploy_qml_imports\s*\(", "Qt 6 CMake command"),
    (r"\bqt_finalize_(project|target)\s*\(", "Qt 6 CMake command"),
    (r"\bqt_import_qml_plugins\s*\(", "Qt 6 CMake command"),
    (r"\bqt_policy\s*\(|\bQTP000\d\b", "Qt 6 CMake policy"),
    (r"\bQt6::\w+", "Qt 6 link target"),
    (r"find_package\s*\(\s*Qt6\b", "Qt 6 find_package"),
    (r"NAMES\s+Qt6", "Qt5/Qt6 version probe"),
    (r"\bQML_FILES\b", "Qt 6 QML CMake argument"),
    (r"\bQML_IMPORT_PATH\b", "QML import path property"),
    (r"\bqmldir\b", "QML module descriptor"),
    (r"[\w/\-.]+\.qml\b", "QML source file"),
    (r"\bQML_(ELEMENT|NAMED_ELEMENT|EXTENDED|UNCREATABLE|SINGLETON|FOREIGN|INTERFACE|ANONYMOUS)\b",
     "QML type-registration macro (QtQml; out of scope for Widgets-only code)"),
    (r"\bq20::|\bq20_\w+|<q20\w*>", "Qt 6 q20 shim (absent in Qt 5)"),
    (r"\bqmltestrunner\b|\bqmlprofiler\b|\bqmllint\b|\bqmlscene\b",
     "Qt Quick tooling"),
    (r"\bQQuick[A-Z]\w*|\bQQml[A-Z]\w*", "Qt Quick class"),
    (r"\bQQmlApplicationEngine\b", "Qt Quick engine class"),
]

# Languages whose fenced blocks are treated as emitted output.
CODE_FENCE_LANGS = {
    "cmake", "cpp", "c++", "cxx", "c", "h", "hpp", "h++", "bat", "batch", "sh",
    "bash", "powershell", "ps1", "xml", "pro", "qmake", "qml", "js", "python",
    "py", "console", "text", "json",
}
RE_FENCE = re.compile(r"^\s*(```|~~~)\s*([A-Za-z0-9+#._-]*)\s*$")

RE_QT6_PROSE_USAGE = re.compile(
    r"(?:^|[^`\w])(qt_add_\w+|qt_standard_project_setup|qt_deploy_qml_imports|"
    r"qt_finalize_\w+|qt_policy)\s*\(|\bQt6::\w+|find_package\s*\(\s*Qt6\b")

# Harness / product names. Generic words (agent, tool, assistant, skill) are fine.
HARNESS_PATTERNS = [
    (r"\bclaude\b", "Claude"), (r"\bcodex\b", "Codex"), (r"\bcopilot\b", "Copilot"),
    (r"\bcursor\s+ide\b", "Cursor"), (r"\bwindsurf\b", "Windsurf"),
    (r"\bgemini\b", "Gemini"), (r"\bantigravity\b", "Antigravity"),
    (r"\bqoder\b", "Qoder"), (r"\bkilo\b", "Kilo"), (r"\bqwen\b", "Qwen"),
    (r"\bopencode\b", "opencode"), (r"\baider\b", "Aider"), (r"\bdevin\b", "Devin"),
    (r"\bpi\b(?!\w)", "Pi"),
    (r"\.claude\b", "~/.claude"), (r"\.codex\b", "~/.codex"), (r"\.copilot\b", "copilot dir"),
    (r"\.cursor\b", "cursor dir"), (r"\.agents/skills", ".agents/skills"),
    (r"gemini\.md", "GEMINI.md"), (r"agents\.md", "AGENTS.md"),
    (r"npx skills add", "skill installer"), (r"gh skill install", "skill installer"),
    (r"plugin marketplace", "plugin marketplace"), (r"/plugin install", "plugin install"),
    (r"claude code", "Claude Code"), (r"github copilot", "GitHub Copilot"),
]
# Words that legitimately contain the two-letter harness name.
PI_EXCUSE = re.compile(r"pixel|dpi|reply|input|copy|api|pipe|spindle|typing|pilot|topic", re.I)

REPO_LEVEL_PATHS = [
    (r"\btests/skill-content-check\b", "this repo's test directory"),
    (r"\btests/qt-cpp-review\b", "this repo's test directory"),
    (r"\.claude-plugin\b", "packaging artifact"),
    (r"\bmkdocs\b", "docs site"),
    (r"\bmarketplace\b", "packaging artifact"),
    (r"\bgemini-extension\b", "packaging artifact"),
    (r"\bgen_skills\b", "docs site generator"),
    (r"\boverrides/", "docs site theme"),
    (r"\brequirements-docs\b", "docs site deps"),
    (r"\bdocs/mcp\b", "docs site page"),
    (r"\bdocs/skills\b", "docs site page"),
]

RE_CROSS_SKILL_PATH = re.compile(r"\.\./\s*qt-|\bskills/qt-|/skills/")
RE_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
RE_MD_RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!https?:|#|mailto:)([^)\s]+)")
RE_PATH_MENTION = re.compile(r"(?:references|lint-scripts)/[\w\-./]*\.(?:md|py|txt|json|sh)")

REQUIRED_TOP_KEYS = ["name", "description", "license", "compatibility",
                     "disable-model-invocation", "metadata"]
ALLOWED_TOP_KEYS = set(REQUIRED_TOP_KEYS) | {"allowed-tools"}
REQUIRED_META_KEYS = ["author", "version", "qt-version", "category"]
ALLOWED_META_KEYS = set(REQUIRED_META_KEYS) | {"argument-hint", "changelog"}
PRODUCT_KEY_NAMES = ("compatibility", "description")

MAX_DESCRIPTION_CHARS = 1024
MIN_DESCRIPTION_CHARS = 60
MAX_SKILL_LINES = 320
ALLOWED_SKILL_SUBDIRS = {"references"}

# A file may declare itself a counter-example catalogue (the mistake checklists and
# the delta tables). Its fenced blocks may show Qt 6 syntax; every other check still
# applies to it.
COUNTEREXAMPLE_MARKER = "<!-- check-skills: allows-qt6-counterexamples -->"

# Prose that names a forbidden construct in order to forbid it.
PROSE_BAN_WORDS = re.compile(
    r"\bnever\b|\bno\b|\bnot\b|\babsent\b|\bundefined\b|\bavoid\b|"
    r"\bban(?:ned)?\b|\bforbid(?:den)?\b|\bremoved\b|\bdeprecated\b|"
    r"\bmust not\b|\bcannot\b|\bout of scope\b|\bdo not\b|\bdon.t\b|"
    r"\bwrong\b|\binstead\b|\breplacement\b|\bworkaround\b|\blegacy\b",
    re.I,
)

# Skill invocation syntax is harness packaging, not a skill content concern.
RE_SLASH_INVOCATION = re.compile(r"(?<![\w/.])/qt-[a-z-]+\s+\w")

# ---------------------------------------------------------------------------
# Derived-consistency configuration
# ---------------------------------------------------------------------------

LINTER_REL = "qt-cpp-review/references/lint-scripts/qt_review_lint.py"
FRAMEWORK_CHECKLIST_REL = "qt-cpp-review/references/qt-framework-checklist.md"
# A rule id has to be documented somewhere a reviewer will read.
RULE_ID_DOCS = [
    "qt-cpp-review/SKILL.md",
    "qt-cpp-review/references/qt-review-checklist.md",
    "qt-cpp-review/references/qt-framework-checklist.md",
    "qt-cpp-review/references/qt515-deltas.md",
    "qt-cpp-review/references/model-view-checklist.md",
    "qt-cpp-review/references/qt-deprecated-classes.md",
    "qt-cpp-review/references/agent-missions.md",
]

RE_RULE_ID = re.compile(r'Rule\(\s*"([A-Za-z0-9._-]+)"')
RE_EMIT_ID = re.compile(r'emit\(\s*[^,]+,\s*"([A-Za-z0-9._-]+)"')
RE_FRAMEWORK_TABLE = re.compile(r"RULES_FRAMEWORK: list\[Rule\] = \[(.*?)^\]", re.S | re.M)
RE_CATEGORY_BLOCK = re.compile(r"Rule categories:\n(.*?)\n\n", re.S)
RE_README_CATEGORY_LIST = re.compile(
    r"across the categories ((?:[A-Z0-9]+(?:[ ,\n]+| and ))*[A-Z0-9]+)")
RE_SKILL_CATEGORY_BULLET = re.compile(r"^- \*\*([A-Z0-9 /]+)\*\*", re.M)
RE_QT6_SUBCOUNT = re.compile(r"(\d+)\s+of them")
RE_STATED_TOTAL = re.compile(r"\b(\d{2,3})(\+)?\s+(?:rule ids?|rules)\b")
RE_EXPECTATIONS = re.compile(r"(\d+) universal \+ (\d+) framework")
RE_TEST_KEY = re.compile(r'\("[^"]+",\s*"([A-Za-z0-9._-]+)"\)')
RE_PY_FLOOR = re.compile(r"Python 3\.(\d+)\+?")
# Feature -> first Python minor version that requires it. Only the dataclasses
# floor is derived here; a walrus or a match statement inside a regex literal is
# indistinguishable from real code by text, so those stay manual.
PY_FEATURES = [
    (re.compile(r"^\s*(?:from dataclasses import|import dataclasses|@dataclass)", re.M), 7),
]
ALLOWED_SEVERITIES = {"compile", "configure", "metatype-runtime"}
CORE_BANS_HEADING = "## Core bans"
# Ban rows whose subject is a *combination*, not a symbol: QT6-9 bans
# Q_PROPERTY of a std::optional, and both halves are legal Qt 5 on their own.
BANNED_COMBINATIONS = {"QT6-9"}
# A ban row may declare itself a scope claim instead of an existence claim, which is
# the correct framing for API Qt 5 ships in a module this skill set does not link (the
# QML type-registration macros live in <QtQml/qqml.h>). Scope is owned by
# qt5-scope-symbols.txt, which asserts the other direction: these DO exist.
SCOPE_ROW_MARKER = "<!-- check-skills: scope claim -->"

# ---------------------------------------------------------------------------
# Qt 5 existence registers
# ---------------------------------------------------------------------------

REGISTER_DIR = Path(__file__).resolve().parent
QT5_REGISTER = "qt5-symbols.txt"
QT6_REGISTER = "qt5-absent-symbols.txt"
SCOPE_REGISTER = "qt5-scope-symbols.txt"
CMAKE_REGISTER = "qt5-cmake.txt"
QT5_PREFIXES = [
    os.environ.get("QT5_DIR", ""),
    "/mnt/d/devsoft/Qt/5.15.2/msvc2019_64", "D:/devsoft/Qt/5.15.2/msvc2019_64",
    str(Path.home() / "Qt/5.15.2/gcc_64"), "/usr/include/x86_64-linux-gnu/qt5",
]
# A Qt-like token as it appears in prose: macro, Class::member, or class name
# (Q followed by at least one more upper-case letter, so "Qt" itself never matches).
RE_QT_TOKEN = re.compile(
    r"\b(?:QT_[A-Z][A-Z0-9_]+|Q_[A-Z][A-Z0-9_]+"
    r"|Q[A-Za-z0-9]+::[A-Za-z_][A-Za-z0-9_]*"
    r"|Q[A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)\b")
# CMake target names and prose placeholders are not header symbols.
QT_TOKEN_SKIP = re.compile(r"^(?:Qt[56]::|QUIP|QT$|QFoo|QtFoo|QtModule|QHeader|Core5Compat)")
# A lowerCamel function name as prose writes it (`sizeIgnoringMargins()`). Matched
# only on rows that assert presence, where a name the kit does not declare is a bug;
# English prose like "doNot" or "typedef" has no internal capital, so it never lands.
RE_FN_TOKEN = re.compile(r"\b[a-z][A-Za-z0-9_]*(?:[A-Z][A-Za-z0-9_]*)+\b")
FN_SKIP = {"doNot", "isNot", "toBytes"}



# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str):
    m = RE_FRONTMATTER.match(text)
    if not m:
        return None
    blob = m.group(1)
    if yaml is not None:
        try:
            data = yaml.safe_load(blob)
            return data if isinstance(data, dict) else None
        except Exception:
            pass
    return _fallback_parse(blob)


def _fallback_parse(blob: str) -> dict:
    fm: dict = {}
    container = fm
    block_key = None
    for raw in blob.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0 and ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            block_key = key
            if val == "":
                fm[key] = {}
                container = fm[key]
            elif val in ("|", ">", ">-", "|-", ">+", "|+"):
                fm[key] = ""
                container = fm
            else:
                fm[key] = val.strip("'\"")
                container = fm
            continue
        if container is not fm and ":" in line:
            k, _, v = line.partition(":")
            container[k.strip()] = v.strip().strip("'\"")
            continue
        if block_key and isinstance(fm.get(block_key), str):
            fm[block_key] = (fm[block_key] + " " + line).strip()
    return fm


def flatten(value) -> str:
    return " ".join(str(value).split()) if value is not None else ""


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

class Reporter:
    def __init__(self) -> None:
        self.findings: list[str] = []

    def add(self, path, line, check, message) -> None:
        self.findings.append(f"{path}:{line} {check} {message}")


def split_fences(text: str):
    """Yield (line_number, line, in_code_fence_of_emittable_language)."""
    out = []
    inside = False
    lang_ok = False
    for i, line in enumerate(text.splitlines(), 1):
        m = RE_FENCE.match(line)
        if m:
            if not inside:
                inside = True
                lang = (m.group(2) or "").lower()
                lang_ok = lang in CODE_FENCE_LANGS or lang == ""
            else:
                inside = False
                lang_ok = False
            out.append((i, line, inside and lang_ok))
            continue
        out.append((i, line, inside and lang_ok))
    return out


def scan_text(path: Path, text: str, rep: Reporter, skill_names=(), own_name: str = "",
              allow_repo_paths: bool = False) -> None:
    counterexample_file = COUNTEREXAMPLE_MARKER in text
    for lineno, line, in_code in split_fences(text):
        low = line.lower()

        # 1. Qt 6 / QML emitted content: fenced emittable blocks, or prose that
        #    uses the construct as code.
        if not counterexample_file:
            if in_code:
                for pat, why in QT6_CODE_TOKENS:
                    if re.search(pat, line, re.I):
                        rep.add(path, lineno, "QT6",
                                f"{why} in emitted content: {line.strip()[:72]}")
            elif not PROSE_BAN_WORDS.search(line) and not line.strip().startswith("|"):
                # Outside a fence, flag only a line that uses a Qt 6 construct as
                # code, is not a prohibition, and is not a table row.
                if RE_QT6_PROSE_USAGE.search(line):
                    rep.add(path, lineno, "QT6", f"Qt 6 construct used as code: {line.strip()[:72]}")

        # 2. references to removed or sibling skills
        for name in REMOVED_SKILLS:
            if re.search(rf"\b{re.escape(name)}\b", line):
                rep.add(path, lineno, "XSKILL", f"names a removed skill '{name}'")
        for name in skill_names:
            if name == own_name:
                continue
            if re.search(rf"\b{re.escape(name)}\b", line):
                rep.add(path, lineno, "XSKILL", f"names a sibling skill '{name}'")

        # 3. self-containment
        if RE_CROSS_SKILL_PATH.search(line):
            rep.add(path, lineno, "SELFCONTAIN", f"cross-skill path: {line.strip()[:72]}")
        if not allow_repo_paths:
            for pat, why in REPO_LEVEL_PATHS:
                if re.search(pat, line):
                    rep.add(path, lineno, "SELFCONTAIN", f"{why}: {line.strip()[:72]}")

        # 4. tool-agnosticism
        for pat, label in HARNESS_PATTERNS:
            if label == "Pi":
                if RE_PI_WITH_EXCUSE(line):
                    continue
            if re.search(pat, low):
                rep.add(path, lineno, "TOOLAGNOSTIC", f"{label}: {line.strip()[:72]}")
        if RE_SLASH_INVOCATION.search(line):
            rep.add(path, lineno, "TOOLAGNOSTIC",
                    f"slash-command invocation syntax, which is packaging not content: "
                    f"{line.strip()[:72]}")


def RE_PI_WITH_EXCUSE(line: str) -> bool:
    """True when the only 'pi' hit is inside a harmless word."""
    for m in re.finditer(r"(?<![A-Za-z0-9_])pi(?![A-Za-z0-9_])", line, re.I):
        window = line[max(0, m.start() - 12): m.end() + 12]
        if not PI_EXCUSE.search(window):
            return False
    return True


def resolve_target(path: Path, skill: Path, target: str) -> bool:
    bases = [path.parent, skill, skill / "references", skill / "references" / "lint-scripts"]
    if any((b / target).exists() for b in bases):
        return True
    name = Path(target).name
    return any(p.name == name for p in skill.rglob("*") if p.is_file())


def check_links(path: Path, skill: Path, text: str, rep: Reporter) -> None:
    targets = set(RE_MD_RELATIVE_LINK.findall(text))
    targets |= {t.strip() for t in RE_PATH_MENTION.findall(text)}
    for target in sorted(targets):
        target = target.split("#")[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if resolve_target(path, skill, target):
            continue
        rep.add(path, 0, "BROKENLINK", f"unresolved reference: {target}")


def check_frontmatter(skill: Path, rep: Reporter) -> None:
    sk = skill / "SKILL.md"
    text = sk.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        rep.add(sk, 0, "FM", "missing or malformed frontmatter")
    else:
        for key in REQUIRED_TOP_KEYS:
            if key not in fm:
                rep.add(sk, 0, "FM", f"missing required key: {key}")
        for key in fm:
            if key not in ALLOWED_TOP_KEYS:
                rep.add(sk, 0, "FM",
                        f"non-standard top-level key '{key}' (belongs under metadata)")
        name = flatten(fm.get("name"))
        if name != skill.name:
            rep.add(sk, 0, "FM", f"name '{name}' != directory '{skill.name}'")
        if not re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?", name):
            rep.add(sk, 0, "FM", f"name is not lowercase/digits/hyphens: '{name}'")
        desc = flatten(fm.get("description"))
        if len(desc) > MAX_DESCRIPTION_CHARS:
            rep.add(sk, 0, "FM", f"description {len(desc)} chars > {MAX_DESCRIPTION_CHARS}")
        if len(desc) < MIN_DESCRIPTION_CHARS:
            rep.add(sk, 0, "FM", f"description too short to route ({len(desc)} chars)")
        meta = fm.get("metadata")
        if not isinstance(meta, dict):
            rep.add(sk, 0, "FM", "metadata must be a mapping")
        else:
            for key in REQUIRED_META_KEYS:
                if key not in meta:
                    rep.add(sk, 0, "FM", f"metadata missing: {key}")
            for key in meta:
                if key not in ALLOWED_META_KEYS:
                    rep.add(sk, 0, "FM", f"metadata key outside the contract: {key}")
        for key in PRODUCT_KEY_NAMES:
            value = flatten(fm.get(key))
            if re.search(r"claude|codex|copilot|cursor|windsurf|gemini|kilo|qoder", value, re.I):
                rep.add(sk, 0, "FM", f"'{key}' names a harness product")
    lines = text.count("\n")
    if lines > MAX_SKILL_LINES:
        rep.add(sk, 0, "SIZE", f"SKILL.md {lines} lines > {MAX_SKILL_LINES}")


def check_skill(skill: Path, rep: Reporter, skill_names=()) -> None:
    if not (skill / "SKILL.md").is_file():
        rep.add(skill, 0, "STRUCT", "SKILL.md missing")
        return
    if not (skill / "README.md").is_file():
        rep.add(skill, 0, "STRUCT", "README.md missing")
    if not (skill / "LICENSE.txt").is_file():
        rep.add(skill, 0, "STRUCT", "LICENSE.txt missing")

    for path in sorted(skill.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue        # a byproduct of running the linter, not skill content
        rel = path.relative_to(skill)
        if len(rel.parts) > 1 and rel.parts[0] not in ALLOWED_SKILL_SUBDIRS:
            rep.add(path, 0, "STRUCT", f"unexpected top-level entry: {rel}")
        if path.suffix not in (".md", ".py", ".txt"):
            rep.add(path, 0, "STRUCT", f"unexpected file type: {rel}")
            continue
        if path.name == "LICENSE.txt":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            rep.add(path, 0, "READ", f"unreadable: {exc}")
            continue
        scan_text(path, text, rep, skill_names, own_name=skill.name)
        check_links(path, skill, text, rep)

    check_frontmatter(skill, rep)


def check_repo(root: Path, rep: Reporter) -> list:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        rep.add(skills_dir, 0, "STRUCT", "skills/ directory missing")
        return []
    for gone in (".claude-plugin", "gemini-extension.json", "mkdocs.yml", "docs",
                 "overrides", "tools", "mcp", "gen_skills.py", "requirements-docs.txt"):
        if (root / gone).exists():
            rep.add(root / gone, 0, "PACKAGING", "harness or docs-site artifact present")
    skills = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    for skill in skills:
        if not (skill / "SKILL.md").is_file():
            rep.add(skill, 0, "STRUCT", "directory without SKILL.md")
    return [s for s in skills if (s / "SKILL.md").is_file()]


def check_root_readme(root: Path, rep: Reporter) -> None:
    readme = root / "README.md"
    if not readme.is_file():
        rep.add(readme, 0, "STRUCT", "root README.md missing")
        return
    # The root README legitimately documents the repository layout and its checks.
    scan_text(readme, readme.read_text(encoding="utf-8"), rep, allow_repo_paths=True)


# ---------------------------------------------------------------------------
# Derived consistency: prose must match the files it describes
# ---------------------------------------------------------------------------

def lint_model(root: Path) -> dict:
    """Compute the linter's real rule inventory from its source."""
    path = root / "skills" / LINTER_REL
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    registered = RE_RULE_ID.findall(text)
    emitted = RE_EMIT_ID.findall(text)
    ids = set(registered) | {e for e in emitted if e not in registered}
    fw_match = RE_FRAMEWORK_TABLE.search(text)
    framework = set(RE_RULE_ID.findall(fw_match.group(1))) if fw_match else set()
    cats = {i.split("-")[0] for i in ids}
    declared = []
    block = RE_CATEGORY_BLOCK.search(text)
    if block:
        declared += re.findall(r"^\s+([A-Z0-9]+)\s", block.group(1), re.M)
    return {
        "path": path, "text": text, "ids": ids, "registered": registered,
        "framework": framework, "categories": cats, "declared_categories": set(declared),
        "qt6": {i for i in ids if i.startswith("QT6")},
    }


def ids_by_category(ids) -> dict:
    grouped: dict = {}
    for i in sorted(ids):
        grouped.setdefault(i.split("-")[0], []).append(i)
    return grouped


def md_files(root: Path) -> list:
    out = []
    for p in [root / "README.md"] + sorted((root / "skills").rglob("*.md")):
        if p.is_file():
            out.append(p)
    return out


def check_derived(root: Path, skills: list, model: dict, rep: Reporter) -> None:
    if not model:
        rep.add(root / "skills" / LINTER_REL, 0, "COUNTS", "linter not found; cannot derive rule inventory")
        return

    dupes = sorted({i for i in model["registered"] if model["registered"].count(i) > 1})
    for d in dupes:
        rep.add(model["path"], 0, "DUPID",
                f"rule id {d} is registered {model['registered'].count(d)} times; "
                "output cannot distinguish the patterns and stated counts drift")

    for i in sorted(model["framework"]):
        if not i.startswith("FW"):
            rep.add(model["path"], 0, "IDSPACE",
                    f"framework rule {i} is outside the FW- id space used by "
                    f"references/{Path(FRAMEWORK_CHECKLIST_REL).name}")
        fw_doc = root / "skills" / FRAMEWORK_CHECKLIST_REL
        if fw_doc.is_file() and i not in fw_doc.read_text(encoding="utf-8"):
            rep.add(fw_doc, 0, "IDSPACE", f"framework rule {i} is not in the framework checklist")

    doc_text = ""
    for rel in RULE_ID_DOCS:
        p = root / "skills" / rel
        if p.is_file():
            doc_text += p.read_text(encoding="utf-8")
    for i in sorted(model["ids"]):
        if i not in doc_text:
            rep.add(model["path"], 0, "IDOC", f"rule {i} is emitted but documented in no review reference")

    for c in sorted(model["categories"] - model["declared_categories"]):
        rep.add(model["path"], 0, "CATEGORY",
                f"category {c} ({', '.join(ids_by_category(model['ids']).get(c, []))}) "
                "is emitted but not in the docstring's 'Rule categories' list")

    review_readme = root / "skills" / "qt-cpp-review" / "README.md"
    review_skill = root / "skills" / "qt-cpp-review" / "SKILL.md"
    for label, path in (("README", review_readme), ("SKILL", review_skill)):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        listed = set()
        m = RE_README_CATEGORY_LIST.search(text)
        if m:
            listed = {x for x in re.split(r"[ ,\n]+| and ", m.group(1)) if x and x != "and"}
        for bullet in RE_SKILL_CATEGORY_BULLET.findall(text):
            listed |= {x.strip() for x in bullet.split("/") if x.strip()}
        if listed and listed != model["categories"]:
            rep.add(path, 0, "CATEGORY",
                    f"{label} category set differs from the linter: "
                    f"missing {sorted(model['categories'] - listed)}, "
                    f"extra {sorted(listed - model['categories'])}")

    derived = len(model["ids"])
    for path in md_files(root):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for num, plus in RE_STATED_TOTAL.findall(line):
                if plus:
                    if int(num) >= derived:
                        rep.add(path, lineno, "COUNTS",
                                f"'{num}+ rules' but the linter registers {derived}")
                elif int(num) != derived and "expectation" not in line:
                    rep.add(path, lineno, "COUNTS",
                            f"line states {num} rule ids; the linter registers {derived}")
            for num in RE_QT6_SUBCOUNT.findall(line):
                if int(num) != len(model["qt6"]):
                    rep.add(path, lineno, "COUNTS",
                            f"line states {num} Qt 6-isms; the QT6 category has {len(model['qt6'])} ids")

    runner = root / "tests/qt-cpp-review/run_tests.py"
    readme = root / "README.md"
    if runner.is_file() and readme.is_file():
        rtext = runner.read_text(encoding="utf-8")
        counts = {}
        for name in ("EXPECTED_UNIVERSAL", "EXPECTED_FRAMEWORK", "EXPECTED_FRAMEWORK_ALWAYS"):
            m = re.search(rf"^{name} = \{{(.*?)^\}}", rtext, re.S | re.M)
            counts[name] = len(RE_TEST_KEY.findall(m.group(1))) if m else 0
        want = (counts["EXPECTED_UNIVERSAL"],
                counts["EXPECTED_FRAMEWORK"] + counts["EXPECTED_FRAMEWORK_ALWAYS"])
        for lineno, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
            m = RE_EXPECTATIONS.search(line)
            if m and (int(m.group(1)), int(m.group(2))) != want:
                rep.add(readme, lineno, "COUNTS",
                        f"claims {m.group(1)} universal + {m.group(2)} framework expectations; "
                        f"run_tests.py declares {want[0]} + {want[1]}")


def check_files_block(skill: Path, rep: Reporter) -> None:
    readme = skill / "README.md"
    if not readme.is_file():
        return
    text = readme.read_text(encoding="utf-8")
    present = sorted(p.name for p in skill.rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    for name in present:
        if name not in text:
            rep.add(readme, 0, "FILESBLOCK", f"skill contains {name} but README.md never names it")
    # Only the fenced "Files" tree is a claim about this directory; elsewhere a
    # README legitimately names CMakeLists.txt, main.cpp and other project files.
    named = set()
    for block in re.findall(r"^```\n(.*?)^```", text, re.S | re.M):
        named.update(re.findall(r"\b([A-Za-z0-9_.-]+\.(?:md|py|txt|json))\b", block))
    for name in sorted(named):
        if name not in present and name not in ("index.md", "main.md"):
            rep.add(readme, 0, "FILESBLOCK",
                    f"README.md file tree lists {name}, which is not in this skill directory")


def check_python_floor(root: Path, rep: Reporter) -> None:
    need = 6
    for rel in ("skills/" + LINTER_REL, "tests/skill-content-check/check_skills.py"):
        p = root / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        for probe, version in PY_FEATURES:
            if probe.search(text):
                need = max(need, version)
    for path in md_files(root):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            m = RE_PY_FLOOR.search(line)
            if m and int(m.group(1)) < need:
                rep.add(path, lineno, "PYFLOOR",
                        f"claims Python 3.{m.group(1)}+; the source needs 3.{need}+ "
                        "(dataclasses arrived in 3.7)")


def check_bans_sync(skills: list, rep: Reporter) -> None:
    digests = {}
    for skill in skills:
        path = skill / "references" / "qt515-deltas.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        i = text.find(CORE_BANS_HEADING)
        if i < 0:
            rep.add(path, 0, "BANSYNC", "no '## Core bans' block to compare")
            continue
        rest = text[i + len(CORE_BANS_HEADING):]
        j = rest.find("\n## ")
        block = rest[:j] if j > 0 else rest
        digests[path] = re.sub(r"\s+", " ", block).strip()
    if len(set(digests.values())) > 1:
        # The block is deliberately repeated verbatim so that one installed
        # directory still carries every ban. Divergence means a skill lost a rule.
        for path, blob in digests.items():
            rep.add(path, 0, "BANSYNC",
                    f"'Core bans' block differs from the other skills ({len(blob)} chars)")


def check_severity(skills: list, rep: Reporter) -> None:
    for skill in skills:
        path = skill / "references" / "qt515-deltas.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 4 and re.fullmatch(r"[A-Z0-9]+-[0-9]+", cells[1] or ""):
                sev = cells[3].rstrip(".").lower()
                if sev and not sev.startswith("-") and sev not in ALLOWED_SEVERITIES:
                    rep.add(path, lineno, "SEVERITY",
                            "severity '" + cells[3] + "' is outside the taxonomy "
                            "{compile, configure, metatype-runtime}")


def check_severity_definition(skills: list, rep: Reporter) -> None:
    """A file that defines the Severity column must name all three failure classes."""
    for skill in skills:
        path = skill / "references" / "qt515-deltas.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "Severity" in text and not ALLOWED_SEVERITIES <= set(re.findall(r"[\w-]+", text)):
            rep.add(path, 0, "SEVERITY",
                    "the Severity column is defined without naming all three failure classes")


# ---------------------------------------------------------------------------
# Qt 5 existence registers
# ---------------------------------------------------------------------------

def find_qt5():
    for cand in QT5_PREFIXES:
        if not cand:
            continue
        p = Path(cand)
        if (p / "include").is_dir() or (p / "QtCore").is_dir():
            return p
    return None


def public_headers(qt5) -> list:
    if qt5 is None:
        return []
    base = qt5 / "include" if (qt5 / "include").is_dir() else qt5
    out = []
    for mod in sorted(base.iterdir()):
        if not mod.is_dir():
            continue
        out.extend(sorted(mod.glob("*.h")))
    return out


def qt_word_set(qt5) -> set:
    words = set()
    for hdr in public_headers(qt5):
        try:
            words.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*",
                                    hdr.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass
    return words


def cmake_blob(qt5) -> str:
    out = []
    if qt5 is None:
        return ""
    for cmake in (qt5 / "lib" / "cmake", qt5 / "share" / "cmake"):
        if not cmake.is_dir():
            continue
        for f in cmake.rglob("*.cmake"):
            try:
                out.append(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        out.extend(f.name for f in cmake.iterdir())
    return "\n".join(out)


def load_register(name: str) -> list:
    path = REGISTER_DIR / name
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            out.append(line)
    return out


def token_symbol(token: str) -> str:
    """The part of `Class::member()` a header has to declare."""
    token = token.strip("`").split("(")[0].strip()
    return token.split("::")[-1] if "::" in token else token


def qt_classes(qt5) -> dict:
    """class name -> its header bodies and base classes, for this Qt 5 kit.

    Presence has to be class-scoped: the same member name can be legal on one class
    and Qt 6-only on another, so `QWheelEvent::position()` is Qt 5.15 while
    `QMouseEvent::position()` is not. Bases are recorded because a claim can be made
    through a derived class — `QApplication::setHighDpiScaleFactorRoundingPolicy()`
    is declared on QGuiApplication and is still callable that way.
    """
    classes: dict = {}
    for hdr in public_headers(qt5):
        try:
            text = hdr.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(
                r"\b(?:class|struct)\s+(?:[A-Z][A-Z0-9_]*\s+)?([A-Za-z_][A-Za-z0-9_]*)"
                r"([^;{]{0,300})\{", text):
            name, head = m.group(1), m.group(2)
            i = text.index("{", m.start())
            depth, j = 0, i
            while j < len(text):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j <= i:
                continue
            entry = classes.setdefault(name, {"bodies": [], "bases": set()})
            entry["bodies"].append(text[i:j])
            entry["bases"] |= set(re.findall(
                r"(?:public|protected|private)\s+([A-Za-z_][A-Za-z0-9_]*)", head))
    return classes


def class_bodies(name: str, classes: dict, seen=None) -> list:
    """The bodies of a class and, transitively, of its base classes."""
    seen = seen or set()
    if name in seen or name not in classes:
        return []
    seen.add(name)
    out = list(classes[name]["bodies"])
    for base in classes[name]["bases"]:
        out.extend(class_bodies(base, classes, seen))
    return out


def declares_member(member: str, bodies: list) -> bool:
    """Is `member` declared in one of these bodies?

    An occurrence is a declaration unless it is a use (`x->member(`, `x.member(`) or
    something inside the argument list of its own line — that is what keeps the
    parameter `typeId` in `QVariant(int typeId, const void *copy)` from making
    `QVariant::typeId()` look like Qt 5 API.
    """
    pattern = re.compile(rf"\b{re.escape(member)}\b")
    for body in bodies:
        for m in pattern.finditer(body):
            before = body[:m.start()]
            if re.search(r"[.>]\s*$", before[-3:]):
                continue
            line_start = before.rfind("\n") + 1
            line_end = body.find("\n", m.start())
            line = body[line_start:line_end if line_end != -1 else len(body)]
            paren = line.find("(")
            if paren != -1 and (m.start() - line_start) > paren:
                continue
            return True
    return False


def declares(qt_symbol: str, words: set, classes: dict) -> bool:
    """Does this Qt 5 kit declare `Class::member` / `Class` / `MACRO`?

    Unknown classes fall back to the whole-header word set, which is the
    conservative direction for a ban and the reason `Qt::` enumerators (namespace,
    not class) still resolve.
    """
    s = qt_symbol.strip("`").split("(")[0].strip()
    if "::" in s:
        cls, member = s.split("::", 1)
        member = member.split("<")[0].strip()
        bodies = class_bodies(cls, classes)
        if bodies:
            return declares_member(member, bodies)
        return member in words
    return s in words


def register_mentioned(token: str, text: str) -> bool:
    """A register line is live if the prose names it, qualified or bare.

    Skills legitimately write `PlaceholderText` inside a list of `QPalette` roles;
    requiring the fully qualified spelling everywhere would force prose churn for no
    gain. A name that appears in neither form is a stale register line.
    """
    if token in text:
        return True
    member = token.split("::")[-1] if "::" in token else token
    return member in text and len(member) > 5


def check_registers(root: Path, skills: list, rep: Reporter, qt5) -> None:
    if qt5 is None:
        print("note: no Qt 5 installation found (set QT5_DIR); existence checks skipped",
              file=sys.stderr)
        return
    words = qt_word_set(qt5)
    if not words:
        rep.add(qt5, 0, "QT5REG", f"no headers found under {qt5}")
        return
    classes = qt_classes(qt5)
    cblob = cmake_blob(qt5)
    skill_text = ""
    for skill in skills:
        for p in skill.rglob("*.md"):
            skill_text += p.read_text(encoding="utf-8", errors="replace")
    for path in md_files(root):
        skill_text += path.read_text(encoding="utf-8")

    for token in load_register(QT5_REGISTER):
        if not register_mentioned(token, skill_text):
            rep.add(REGISTER_DIR / QT5_REGISTER, 0, "REGSTALE",
                    f"{token} is registered as Qt 5 API but no skill mentions it")
        if token.startswith(("Qt5::", "qt_", "qt5_")):
            if token not in cblob:
                rep.add(REGISTER_DIR / QT5_REGISTER, 0, "QT5CMAKE",
                        f"{token} asserted present but not found under {qt5}/lib/cmake")
        elif not declares(token, words, classes):
            rep.add(REGISTER_DIR / QT5_REGISTER, 0, "QT5REG",
                    f"{token} asserted present in Qt 5 but absent from {qt5} public headers")

    for token in load_register(QT6_REGISTER):
        if not register_mentioned(token, skill_text):
            rep.add(REGISTER_DIR / QT6_REGISTER, 0, "REGSTALE",
                    f"{token} is registered as Qt 6-only but no skill mentions it")
        if declares(token, words, classes):
            rep.add(REGISTER_DIR / QT6_REGISTER, 0, "QT6REG",
                    f"{token} asserted absent from Qt 5 but {qt5} declares it — "
                    "banning it is a false positive against valid Qt 5 code")

    for token in load_register(SCOPE_REGISTER):
        if not register_mentioned(token, skill_text):
            rep.add(REGISTER_DIR / SCOPE_REGISTER, 0, "REGSTALE",
                    f"{token} is registered as out-of-scope but no skill mentions it")
        if not declares(token, words, classes):
            rep.add(REGISTER_DIR / SCOPE_REGISTER, 0, "QTSCOPE",
                    f"{token} is treated as Qt 5 API that Widgets-only code must not use, "
                    f"but {qt5} does not declare it — the correct claim is then 'does not "
                    "exist', which is a different sentence (existence vs scope, R3)")

    for token in load_register(CMAKE_REGISTER):
        absent = token.startswith("!")
        name = token[1:] if absent else token
        if not register_mentioned(name, skill_text):
            rep.add(REGISTER_DIR / CMAKE_REGISTER, 0, "REGSTALE",
                    f"{name} is registered but no skill mentions it")
        found = name in cblob
        if found == bool(absent):
            rep.add(REGISTER_DIR / CMAKE_REGISTER, 0, "QT5CMAKE",
                    f"{name} expected {'absent from' if absent else 'in'} "
                    f"{qt5}/lib/cmake, the opposite is true")


def claim_rows(path: Path):
    """Yield (lineno, tokens, polarity) for ban tables and do-not-flag tables.

    Only two row shapes are sound to read as existence claims: a `QT6-n` row, whose
    second column is by definition absent from Qt 5, and a row of a "do not flag"
    table, whose status column asserts presence. Any other table is a comparison
    and carries no existence claim.
    """
    text = path.read_text(encoding="utf-8")
    in_do_not_flag = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_do_not_flag = bool(re.search(r"do not flag|legal in qt 5", line, re.I))
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 3 and re.fullmatch(r"QT6-[0-9]+", cells[1] or ""):
            if cells[1] in BANNED_COMBINATIONS:
                continue
            if SCOPE_ROW_MARKER in line:
                continue    # an explicit scope claim; qt5-scope-symbols.txt owns it
            yield lineno, RE_QT_TOKEN.findall(cells[2]), "absent"
            continue
        if in_do_not_flag and line.lstrip().startswith("|"):
            yield lineno, RE_QT_TOKEN.findall(line) + RE_FN_TOKEN.findall(line), "present"
            continue
        if re.match(r"^\s*-\s+No Qt 6-only C\+\+ API", line):
            yield lineno, RE_QT_TOKEN.findall(line.split(":")[-1]), "absent"


def check_claims(root: Path, skills: list, rep: Reporter, qt5) -> None:
    if qt5 is None:
        return
    words = qt_word_set(qt5)
    if not words:
        return
    classes = qt_classes(qt5)
    for skill in skills:
        for path in sorted(skill.rglob("*.md")):
            for lineno, tokens, polarity in claim_rows(path):
                for token in tokens:
                    if QT_TOKEN_SKIP.search(token) or token in FN_SKIP:
                        continue
                    present = declares(token, words, classes)
                    if polarity == "present" and not present:
                        rep.add(path, lineno, "QTPRESENT",
                                f"{token} is claimed available in Qt 5 (do-not-flag row) but "
                                f"{qt5} does not declare it — the suppression entry hides a "
                                "real Qt 6 API")
                    elif polarity == "absent" and present:
                        rep.add(path, lineno, "QTBAN",
                                f"{token} is banned as Qt 6-only but {qt5} declares it — the "
                                "claim must become a scope claim (Widgets-only) or the ban goes")


def qt_sweep(root: Path, skills: list, qt5) -> None:
    words = qt_word_set(qt5)
    if not words:
        print("qt-sweep: no Qt 5 headers found, nothing to compare", file=sys.stderr)
        return
    classes = qt_classes(qt5)
    hits = {}
    for skill in skills:
        for path in sorted(skill.rglob("*.md")):
            for span in re.findall(r"`([^`\n]{2,80})`", path.read_text(encoding="utf-8")):
                for token in RE_QT_TOKEN.findall(span):
                    if QT_TOKEN_SKIP.search(token):
                        continue
                    if not declares(token, words, classes):
                        hits.setdefault(token, set()).add(path.name)
    print(f"qt-sweep: Qt-like tokens with no match in {qt5} public headers — triage "
          f"(ban context = fine, used as Qt 5 API = a defect; verified ones belong in "
          f"the registers):", file=sys.stderr)
    for token in sorted(hits):
        print(f"  {token:34s} {'; '.join(sorted(hits[token]))}", file=sys.stderr)


def isolate(skills: list, rep: Reporter) -> None:
    names = tuple(s.name for s in skills)
    for skill in skills:
        with tempfile.TemporaryDirectory(prefix="skilliso-") as tmp:
            solo = Path(tmp) / skill.name
            shutil.copytree(str(skill), str(solo))
            sub = Reporter()
            for path in sorted(solo.rglob("*")):
                if not path.is_file() or path.name == "LICENSE.txt":
                    continue
                if "__pycache__" in path.parts:
                    continue
                if path.suffix not in (".md", ".py", ".txt"):
                    continue
                text = path.read_text(encoding="utf-8")
                scan_text(path, text, sub, names, own_name=solo.name)
                check_links(path, solo, text, sub)
            check_frontmatter(solo, sub)
            for f in sub.findings:
                if any(tag in f for tag in ("BROKENLINK", "SELFCONTAIN", "XSKILL")):
                    rep.add(skill, 0, "ISOLATE", f"fails when installed alone: {f}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_isolate = "--isolate" in sys.argv
    do_sweep = "--qt-sweep" in sys.argv
    root = Path(args[0]) if args else Path(__file__).resolve().parents[2]
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    rep = Reporter()
    skills = check_repo(root, rep)
    names = tuple(s.name for s in skills)
    for skill in skills:
        check_skill(skill, rep, names)
        check_files_block(skill, rep)
    check_root_readme(root, rep)
    check_derived(root, skills, lint_model(root), rep)
    check_python_floor(root, rep)
    check_bans_sync(skills, rep)
    check_severity(skills, rep)
    check_severity_definition(skills, rep)
    qt5 = find_qt5()
    check_registers(root, skills, rep, qt5)
    check_claims(root, skills, rep, qt5)
    if do_sweep:
        qt_sweep(root, skills, qt5)
    if do_isolate:
        isolate(skills, rep)

    for f in rep.findings:
        print(f)
    scope = f"{len(skills)} skill(s) under {root}" + (" (isolated)" if do_isolate else "")
    scope += f"; Qt 5 evidence: {qt5}" if qt5 else "; Qt 5 evidence: not available"
    print(f"\n{len(rep.findings)} finding(s) across {scope}", file=sys.stderr)
    return 1 if rep.findings else 0


if __name__ == "__main__":
    sys.exit(main())
