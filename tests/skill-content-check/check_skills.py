#!/usr/bin/env python3
"""Static conformance check for the skills in this repository.

Verifies that each skill is Qt 5 / Qt Widgets-only, tool-agnostic,
self-contained and structurally valid. Python 3.6+; PyYAML is used when
available and a fallback parser is used otherwise.

    python3 tests/skill-content-check/check_skills.py [repo_root] [--isolate]

  --isolate   additionally copy each skill into a temporary directory on its own
              and re-scan it there, which proves nothing resolves outside the
              skill directory.

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
    (r"\bQML_(ELEMENT|EXTENDED_TYPE|NAMED|UNCREATABLE|SINGLETON|FOREIGN|INTERFACE)\b",
     "Qt 6 QML registration macro"),
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
    root = Path(args[0]) if args else Path(__file__).resolve().parents[2]
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    rep = Reporter()
    skills = check_repo(root, rep)
    names = tuple(s.name for s in skills)
    for skill in skills:
        check_skill(skill, rep, names)
    check_root_readme(root, rep)
    if do_isolate:
        isolate(skills, rep)

    for f in rep.findings:
        print(f)
    scope = f"{len(skills)} skill(s) under {root}" + (" (isolated)" if do_isolate else "")
    print(f"\n{len(rep.findings)} finding(s) across {scope}", file=sys.stderr)
    return 1 if rep.findings else 0


if __name__ == "__main__":
    sys.exit(main())
