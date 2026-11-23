#!/usr/bin/env python3
"""Static checks for this monorepo's skills and troubleshooting docs.

Usage: python3 lint_skills.py [skill-name ...]
Exit code 1 if any ERROR is found. WARN lines are advisory.
"""
import os, re, sys, glob, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
SKILLS = os.path.join(ROOT, ".claude/skills")
SUBMODULES = ["pro-iq", "anglers-log", "activity-log", "tapd", "adair-flutter-lib", "screenshots"]
TOP = tuple(s + "/" for s in SUBMODULES) + (".claude/",)
MAX_LINES = 500
MAX_DESC = 1024

problems = []

def report(level, path, msg):
    problems.append((level, os.path.relpath(path, ROOT), msg))

def skill_dirs(only):
    dirs = []
    for d in sorted(glob.glob(os.path.join(SKILLS, "*"))):
        if not os.path.isdir(d) or os.path.islink(d):
            continue  # symlinked skills are third-party
        if only and os.path.basename(d) not in only:
            continue
        dirs.append(d)
    for sub in SUBMODULES:
        for d in sorted(glob.glob(os.path.join(ROOT, sub, ".claude/skills/*"))):
            if os.path.isdir(d) and (not only or os.path.basename(d) in only):
                dirs.append(d)
    return dirs

def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(>-?|\|)?\s*\n?(.*?)(?=^\w[\w-]*:|\Z)", fm, re.M | re.S)
    d = " ".join(desc.group(2).split()) if desc else ""
    return (name.group(1).strip() if name else None), d

def headings(path):
    try:
        return open(path).read()
    except OSError:
        return ""

def ignored(p):
    """Gitignored files (keys, state, generated output) may not exist yet."""
    return subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", p]).returncode == 0

def check_paths(path, text, skill_dir):
    in_template = "/template/" in path
    for m in re.finditer(r"`([^`\n]+)`", text):
        p = m.group(1).strip()
        if any(c in p for c in "<>*{}$ |") or "..." in p or "…" in p:
            continue
        if not p.startswith(TOP) or not re.search(r"\.[a-z]{1,5}$", p.split("#")[0]):
            continue
        p = p.split(":")[0].split("#")[0]
        if not os.path.exists(os.path.join(ROOT, p)) and not in_template and not ignored(p):
            report("ERROR", path, f"path does not exist: {p}")
    for m in re.finditer(r"\]\(([^)\s]+)\)", text):
        link = m.group(1).split("#")[0]
        if not link or re.match(r"[a-z]+:", link) or link.startswith("<"):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), link))):
            report("ERROR", path, f"broken link: {link}")

def check_step_refs(path, text, names):
    for m in re.finditer(r"`([a-z0-9-]+)`\s+(Step\s+\d+)\b", text):
        skill, step = m.group(1), " ".join(m.group(2).split())
        if skill not in names:
            continue
        target = headings(names[skill])
        if not re.search(rf"^#+ .*\b{step}\b", target, re.M):
            report("ERROR", path, f"`{skill}` has no heading '{step}'")
        else:
            report("WARN", path, f"refers to `{skill}` {step} by number; prefer the section name")

def main():
    only = set(sys.argv[1:])
    dirs = skill_dirs(only)
    names = {}
    for d in skill_dirs(set()):
        if os.path.dirname(d) == SKILLS:
            names[os.path.basename(d)] = os.path.join(d, "SKILL.md")
    for d in dirs:
        sk = os.path.join(d, "SKILL.md")
        if not os.path.exists(sk):
            report("ERROR", d, "no SKILL.md")
            continue
        text = open(sk).read()
        fm = frontmatter(text)
        if fm is None:
            report("ERROR", sk, "missing frontmatter")
        else:
            name, desc = fm
            if name != os.path.basename(d):
                report("ERROR", sk, f"name '{name}' doesn't match folder")
            if not desc:
                report("ERROR", sk, "empty description")
            elif len(desc) > MAX_DESC:
                report("WARN", sk, f"description is {len(desc)} chars (> {MAX_DESC})")
        n = text.count("\n")
        if n > MAX_LINES:
            report("WARN", sk, f"{n} lines (> {MAX_LINES}); move modes/tables into sibling files")
        for md in glob.glob(os.path.join(d, "**/*.md"), recursive=True):
            if "/template/" in md or "/node_modules/" in md:
                continue
            t = open(md).read()
            check_paths(md, t, d)
            check_step_refs(md, t, names)
            for m in re.finditer(r"(?<![\w/])/tmp/[\w.-]+", t):
                report("WARN", md, f"fixed /tmp path {m.group(0)}; use the session scratchpad")
    if not only:
        for md in glob.glob(os.path.join(ROOT, ".claude/troubleshooting/*.md")):
            check_paths(md, open(md).read(), None)
    errors = 0
    for level, p, msg in sorted(set(problems)):
        print(f"{level:5} {p}: {msg}")
        errors += level == "ERROR"
    print(f"\n{errors} error(s), {len(set(problems)) - errors} warning(s)")
    sys.exit(1 if errors else 0)

main()
