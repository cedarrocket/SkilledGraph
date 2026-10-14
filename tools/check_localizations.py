"""Check bilingual coverage, syntax, local links and byte-sensitive fixtures."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools/localization_manifest.json"


def check() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = []
    for name in manifest["sources"]:
        source = ROOT / name
        if not source.is_file():
            errors.append(f"Missing compatibility source: {name}")
            continue
        for language in manifest["languages"]:
            variant = source.with_name(f"{source.stem}_{language}{source.suffix}")
            if not variant.is_file():
                errors.append(f"Missing {language} variant: {name}")
                continue
            if "/fixtures/language/" in str(source) and source.name != "README.md":
                if source.read_bytes() != variant.read_bytes():
                    errors.append(f"Changed byte-sensitive fixture: {variant.relative_to(ROOT)}")
                continue
            text = variant.read_text(encoding="utf-8")
            if variant.suffix == ".py":
                try:
                    tree = ast.parse(text, filename=str(variant))
                    for node in ast.walk(tree):
                        modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                                   else [item.name for item in node.names] if isinstance(node, ast.Import)
                                   else [])
                        for module in modules:
                            sibling = variant.parent / f"{module}_{language}.py"
                            original = variant.parent / f"{module}.py"
                            if original.is_file() and sibling.is_file():
                                errors.append(f"Unlocalized sibling import: {variant.relative_to(ROOT)} → {module}")
                except SyntaxError as exc:
                    errors.append(f"Python syntax: {variant.relative_to(ROOT)}: {exc}")
            elif variant.suffix == ".md":
                for match in re.finditer(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text):
                    target = match[1].split("#", 1)[0]
                    if not target or ":" in target or target.startswith("/"):
                        continue
                    if not (variant.parent / target).exists():
                        errors.append(f"Broken link: {variant.relative_to(ROOT)} → {target}")
    fixture_root = ROOT / "tests/fixtures/language"
    base = json.loads((fixture_root / "manifest.json").read_text(encoding="utf-8"))
    for language in manifest["languages"]:
        localized = json.loads((fixture_root / f"manifest_{language}.json").read_text(encoding="utf-8"))
        expected = json.loads(json.dumps(base))
        # Fixture content is identical; only the manifest's input filenames differ.
        for item in expected["cases"]:
            path = Path(item["file"])
            item["file"] = str(path.with_name(f"{path.stem}_{language}{path.suffix}"))
        if any(localized[key] != expected[key] for key in ("version", "stage", "cases")):
            errors.append(f"Fixture manifest drift: {language}")
    return errors


if __name__ == "__main__":
    problems = check()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    print(f"OK: {len(manifest['sources'])} sources with cn/en variants; syntax, links and fixture bytes checked.")
