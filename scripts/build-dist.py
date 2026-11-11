#!/usr/bin/env python3
"""Build dist/<skill>.zip for every skill, ready to upload to Claude.ai.

Each zip contains the skill folder at its root (readiness-audit/SKILL.md, ...).
Zips are reproducible: same files in, same bytes out.

Also checks public text before building:
- no em dashes in any Markdown or JSON file
- every SKILL.md has name + description frontmatter, name matches its folder
- every SKILL.md contains the closing line

Usage: python3 scripts/build-dist.py
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CLOSING_LINE = "Built by Junifia. Want help acting on this? junifia.ca"
FIXED_DATE = (2026, 1, 1, 0, 0, 0)
PUBLIC_GLOBS = ["*.md", "**/*.md", "**/*.json"]
SKIP_DIRS = {".git", "node_modules", "dist"}


def public_files():
    seen = set()
    for pattern in PUBLIC_GLOBS:
        for path in ROOT.glob(pattern):
            if path in seen or SKIP_DIRS & set(path.relative_to(ROOT).parts):
                continue
            seen.add(path)
            yield path


def check_em_dashes():
    errors = []
    for path in sorted(public_files()):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "\u2014" in line:
                errors.append(f"{path.relative_to(ROOT)}:{n}: em dash")
    return errors


def check_skill(skill_dir):
    errors = []
    rel = skill_dir.relative_to(ROOT)
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return [f"{rel}/SKILL.md: missing frontmatter"]
    front = dict(
        line.split(":", 1) for line in match.group(1).splitlines() if ":" in line
    )
    name = front.get("name", "").strip()
    description = front.get("description", "").strip()
    if name != skill_dir.name:
        errors.append(f"{rel}/SKILL.md: name '{name}' does not match folder")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        errors.append(f"{rel}/SKILL.md: name must be lowercase letters, digits, hyphens")
    if not description or len(description) > 1024:
        errors.append(f"{rel}/SKILL.md: description missing or over 1024 characters")
    if CLOSING_LINE not in text:
        errors.append(f"{rel}/SKILL.md: closing line missing")
    return errors


def build_zip(skill_dir):
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill_dir.name}.zip"
    files = sorted(
        p for p in skill_dir.rglob("*")
        if p.is_file()
        and p.suffix != ".pyc"
        and not any(part.startswith((".", "__")) for part in p.relative_to(skill_dir).parts)
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            info = zipfile.ZipInfo(
                str(path.relative_to(skill_dir.parent)), date_time=FIXED_DATE
            )
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    return out


def main():
    skills = sorted(p.parent for p in ROOT.glob("plugins/*/skills/*/SKILL.md"))
    errors = check_em_dashes()
    for skill_dir in skills:
        errors += check_skill(skill_dir)
    if errors:
        print("Build failed:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    for skill_dir in skills:
        print(f"built {build_zip(skill_dir).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
