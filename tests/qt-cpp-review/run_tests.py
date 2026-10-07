#!/usr/bin/env python3
# Copyright (C) 2026 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
"""
Regression test for qt_review_lint.py.

Runs the linter against test files in four modes:
  1. Universal mode (no flags) — verifies all universal rules
  2. Framework mode (--framework) — verifies framework-only rules
  3. Gate mode — framework rules must stay silent without the flag
  4. Legal-code mode — a fixture of valid Qt 5.15 must raise nothing

Usage:
    python tests/run_tests.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
LINTER = REPO_ROOT / "skills" / "qt-cpp-review" / "references" / "lint-scripts" / "qt_review_lint.py"
TEST_DIR = Path(__file__).parent

# Universal-mode expected findings (no --framework flag)
EXPECTED_UNIVERSAL = {
    # --- test_all_rules.h ---
    ("test_all_rules.h", "DEP-1"): 1,
    ("test_all_rules.h", "DEP-5"): 1,
    ("test_all_rules.h", "DEP-9"): 1,
    ("test_all_rules.h", "DEP-13"): 1,
    ("test_all_rules.h", "PAT-9"): 1,
    ("test_all_rules.h", "ENM-2"): 1,
    ("test_all_rules.h", "ENM-9"): 1,
    ("test_all_rules.h", "TMO-1"): 2,  # timeout + interval
    ("test_all_rules.h", "API-5"): 2,  # getNoteTitle + getNoteStatistics

    # --- test_all_rules.cpp ---
    ("test_all_rules.cpp", "INC-2"): 1,  # std header before Qt
    ("test_all_rules.cpp", "DEP-2"): 1,
    ("test_all_rules.cpp", "DEP-3"): 1,
    ("test_all_rules.cpp", "DEP-4"): 1,
    ("test_all_rules.cpp", "DEP-6"): 1,
    ("test_all_rules.cpp", "DEP-7"): 1,
    ("test_all_rules.cpp", "DEP-8"): 1,
    ("test_all_rules.cpp", "DEP-10"): 2,
    ("test_all_rules.cpp", "DEP-11"): 1,
    ("test_all_rules.cpp", "DEP-12"): 2,
    ("test_all_rules.cpp", "HDR-3"): 3,
    ("test_all_rules.cpp", "PAT-1"): 1,
    ("test_all_rules.cpp", "PAT-2"): 1,
    ("test_all_rules.cpp", "PAT-3"): 1,
    ("test_all_rules.cpp", "TRN-3"): 1,
    ("test_all_rules.cpp", "PAT-5"): 1,
    ("test_all_rules.cpp", "PAT-7"): 1,
    ("test_all_rules.cpp", "PAT-8"): 1,
    ("test_all_rules.cpp", "VAL-5"): 1,
    ("test_all_rules.cpp", "VAR-3"): 1,
    ("test_all_rules.cpp", "ENM-9"): 1,
    ("test_all_rules.cpp", "API-5"): 1,
    ("test_all_rules.cpp", "PAT-10"): 1,
    ("test_all_rules.cpp", "PAT-11"): 1,
    ("test_all_rules.cpp", "PAT-12"): 1,
    ("test_all_rules.cpp", "PAT-14"): 1,
    ("test_all_rules.cpp", "PAT-15"): 1,
    ("test_all_rules.cpp", "MDL-2"): 1,
    ("test_all_rules.cpp", "MDL-4"): 1,
    ("test_all_rules.cpp", "MDL-5"): 1,
    ("test_all_rules.cpp", "MDL-6"): 1,
    ("test_all_rules.cpp", "MDL-7"): 1,
    ("test_all_rules.cpp", "ERR-1"): 1,
    ("test_all_rules.cpp", "ERR-2"): 1,
    ("test_all_rules.cpp", "ERR-3"): 1,
    ("test_all_rules.cpp", "ERR-4"): 1,
    ("test_all_rules.cpp", "ERR-5"): 1,
    ("test_all_rules.cpp", "ERR-6"): 1,
    ("test_all_rules.cpp", "ERR-7"): 1,
    ("test_all_rules.cpp", "ERR-9"): 1,
    ("test_all_rules.cpp", "LCY-1"): 1,
    ("test_all_rules.cpp", "LCY-2"): 1,
    ("test_all_rules.cpp", "LCY-3"): 1,
    ("test_all_rules.cpp", "LCY-4"): 1,
    ("test_all_rules.cpp", "LCY-5"): 2,
    ("test_all_rules.cpp", "LCY-6"): 1,

    # --- DEP: Qt 5 deprecations that still compile ---
    ("test_all_rules.cpp", "DEP-14"): 1,
    ("test_all_rules.cpp", "DEP-15"): 1,
    ("test_all_rules.cpp", "DEP-16"): 1,
    ("test_all_rules.cpp", "DEP-17"): 1,
    ("test_all_rules.cpp", "DEP-18"): 1,

    # --- QT6: Qt 6-only API surfaced in Qt 5 code ---
    ("test_all_rules.h", "PAT-2"): 1,
    ("test_all_rules.h", "QT6-2"): 2,
    ("test_all_rules.h", "QT6-3"): 1,  # typeId() only; fromType() is legal, see below
    ("test_all_rules.h", "QT6-9"): 1,
    ("test_all_rules.h", "QT6-10"): 1,
    ("test_all_rules.h", "QT6-11"): 1,
    ("test_all_rules.h", "QT6-12"): 2,
    ("test_all_rules.h", "QT6-13"): 1,
    ("test_all_rules.cpp", "QT6-1"): 1,
    ("test_all_rules.cpp", "QT6-2"): 1,
    ("test_all_rules.cpp", "QT6-4"): 2,
    ("test_all_rules.cpp", "QT6-5"): 1,
    ("test_all_rules.cpp", "QT6-6"): 1,
    ("test_all_rules.cpp", "QT6-7"): 1,
    ("test_all_rules.cpp", "QT6-8"): 1,

    # --- separate test files ---
    ("test_mdl1.cpp", "MDL-1"): 1,
    ("test_mdl6.cpp", "MDL-6"): 1,
    ("test_mdl6.cpp", "LCY-5"): 1,

    # --- CMake negative fixture (Qt 6 build syntax in a Qt 5 project) ---
    ("CMakeLists.txt", "QT6-14"): 4,
    ("CMakeLists.txt", "QT6-15"): 2,
    ("CMakeLists.txt", "QT6-16"): 2,
    ("CMakeLists.txt", "QT6-17"): 1,
}

# Framework-mode expected findings (--framework flag)
# Only the framework-specific rules from dedicated test files.
# Rules that fire regardless of --framework, exercised on the framework fixture.
# ids here are the FW- ids of references/qt-framework-checklist.md.
EXPECTED_FRAMEWORK_ALWAYS = {
    ("test_framework.h", "QT6-1"): 1,
    ("test_framework.h", "FW-INC-3"): 1,
}

EXPECTED_FRAMEWORK = {
    ("test_framework.h", "FW-INC-6"): 1,
    ("test_framework.h", "FW-INC-1"): 1,
    ("test_framework.h", "FW-VAL-5"): 1,
    ("test_framework.cpp", "FW-CND-2"): 1,
    ("test_framework.cpp", "FW-PRF-1"): 1,
}

# A fixture of code this repository calls legal Qt 5.15, which must raise nothing.
# A rule firing on legal code is worse than a missing rule: Phase 1 of the skill
# tells the agent the linter is authoritative and to re-derive nothing from it.
TEST_LEGAL = "test_legal_qt5.cpp"


def parse_output(output: str) -> dict[tuple[str, str], int]:
    """Parse linter output into {(filename, rule): count}."""
    counts: dict[tuple[str, str], int] = {}
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        file_loc = parts[0]
        rule = parts[1]
        colon_idx = file_loc.rfind(":")
        filepath = file_loc[:colon_idx] if colon_idx > 0 else file_loc
        basename = Path(filepath).name
        key = (basename, rule)
        counts[key] = counts.get(key, 0) + 1
    return counts


def run_linter(files: list[str], extra_args: list[str] | None = None) -> str:
    """Run the linter and return combined stdout+stderr."""
    cmd = [sys.executable, str(LINTER)] + (extra_args or []) + files
    result = subprocess.run(cmd, capture_output=True)
    return ((result.stdout or b"").decode("utf-8", errors="replace") +
            (result.stderr or b"").decode("utf-8", errors="replace"))


def check_legal_fixture(actual: dict[tuple[str, str], int]) -> bool:
    """The legal-code fixture must raise no finding at all."""
    if not actual:
        print(f"Results: 0 findings against {TEST_LEGAL}")
        print("LEGAL Qt 5.15 CODE PASSED")
        return True
    print(f"FAIL: findings against code this repository documents as legal Qt 5.15:")
    for (fname, rule), count in sorted(actual.items()):
        print(f"  {fname} {rule} x{count}")
    return False


def check_expectations(
    actual: dict[tuple[str, str], int],
    expected: dict[tuple[str, str], int],
    label: str,
) -> tuple[int, int, list[str]]:
    """Check actual findings against expected. Returns (passed, total, errors)."""
    errors: list[str] = []
    passed = 0
    for key, min_count in sorted(expected.items()):
        actual_count = actual.get(key, 0)
        if actual_count == 0:
            errors.append(f"  FAIL  {key[0]} {key[1]} — expected >= {min_count}, got 0")
        elif actual_count < min_count:
            errors.append(
                f"  FAIL  {key[0]} {key[1]} — expected >= {min_count}, got {actual_count}")
        else:
            passed += 1

    # Unexpected findings (only check against expected keys)
    for key, count in sorted(actual.items()):
        if key not in expected:
            errors.append(f"  WARN  {key[0]} {key[1]} x{count} (unexpected)")

    return passed, len(expected), errors


def main() -> int:
    all_ok = True

    # --- Test 1: Universal mode ---
    print("=" * 60)
    print("Test 1: Universal mode (no --framework)")
    print("=" * 60)

    universal_files = [
        str(TEST_DIR / "test_all_rules.h"),
        str(TEST_DIR / "test_all_rules.cpp"),
        str(TEST_DIR / "test_mdl1.cpp"),
        str(TEST_DIR / "test_mdl6.cpp"),
        str(TEST_DIR / "test_qt6_cmake" / "CMakeLists.txt"),
    ]
    output = run_linter(universal_files)
    actual = parse_output(output)
    passed, total, errors = check_expectations(
        actual, EXPECTED_UNIVERSAL, "Universal")

    if errors:
        for e in errors:
            print(e)
        print()
    print(f"Results: {passed}/{total} expected rules triggered")
    if passed == total and not any("FAIL" in e for e in errors):
        print("ALL UNIVERSAL RULES PASSED")
    else:
        all_ok = False
    print()

    # --- Test 2: Framework mode ---
    print("=" * 60)
    print("Test 2: Framework mode (--framework)")
    print("=" * 60)

    framework_files = [
        str(TEST_DIR / "test_framework.h"),
        str(TEST_DIR / "test_framework.cpp"),
    ]
    output = run_linter(framework_files, extra_args=["--framework"])
    actual = parse_output(output)
    fw_expected = dict(EXPECTED_FRAMEWORK)
    fw_expected.update(EXPECTED_FRAMEWORK_ALWAYS)
    passed, total, errors = check_expectations(
        actual, fw_expected, "Framework")

    if errors:
        for e in errors:
            print(e)
        print()
    print(f"Results: {passed}/{total} expected framework rules triggered")
    if passed == total and not any("FAIL" in e for e in errors):
        print("ALL FRAMEWORK RULES PASSED")
    else:
        all_ok = False
    print()

    # --- Test 3: Framework rules must NOT fire without flag ---
    print("=" * 60)
    print("Test 3: Framework rules silent without --framework")
    print("=" * 60)

    output = run_linter(framework_files)  # no --framework
    actual = parse_output(output)
    fw_leaked = {k: v for k, v in actual.items()
                 if k in EXPECTED_FRAMEWORK}
    if fw_leaked:
        print("FAIL: Framework rules fired without --framework flag:")
        for (fname, rule), count in fw_leaked.items():
            print(f"  {fname} {rule} x{count}")
        all_ok = False
    else:
        print("PASSED: No framework rules fired without flag")
    print()

    # --- Test 4: legal Qt 5.15 code must raise nothing ---
    print("=" * 60)
    print("Test 4: no false positives on legal Qt 5.15 code")
    print("=" * 60)

    if not check_legal_fixture(parse_output(run_linter([str(TEST_DIR / TEST_LEGAL)]))):
        all_ok = False
    print()

    # --- Summary ---
    print("=" * 60)
    if all_ok:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
