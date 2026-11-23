#!/usr/bin/env python3
"""Digest Claude Code transcripts for skill-maintenance Sweep mode.

Usage:
  python3 sweep_transcripts.py [--since YYYY-MM-DD | --checkpoint] [--out FILE]
                               [--skills-only] [--max-errors N]

Reads this monorepo's transcripts (~/.claude/projects/-Users-...-flutter-projects*)
and prints, per session, the skills it ran, failed tool calls (with the
command that failed), and the user's own messages (where corrections show up).
Sessions with neither a skill nor an error are skipped. Read-only.
--checkpoint uses lastSweep from ../state.json; it never writes that file.
"""
import argparse, glob, json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "state.json")
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
PROJECTS = os.path.expanduser("~/.claude/projects")
SLUG = ROOT.replace("/", "-").replace(".", "-")

def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""

def clip(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"

NOISE = re.compile(r"^(<system-reminder>|<command-|<local-command|<bash-|Base directory for this skill|Caveat:|\[Request interrupted)|<(task-notification|side-sessions-event|ci-monitor-event)")

def digest(path, max_errors):
    skills, errors, user_msgs, title = [], [], [], None
    pending = {}
    first_ts = last_ts = None
    for line in open(path, errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        t = o.get("type")
        if t == "custom-title":
            title = o.get("customTitle") or title
        ts = o.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        if t not in ("user", "assistant") or o.get("isSidechain"):
            continue
        content = (o.get("message") or {}).get("content")
        if t == "assistant" and isinstance(content, list):
            for b in content:
                if b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Skill":
                    skills.append(inp.get("skill", "?"))
                pending[b.get("id")] = (b.get("name"), inp.get("command") or inp.get("file_path") or json.dumps(inp)[:200])
        elif t == "user":
            if isinstance(content, list):
                for b in content:
                    if b.get("type") == "tool_result" and b.get("is_error"):
                        name, cmd = pending.get(b.get("tool_use_id"), ("?", ""))
                        res = text_of(b.get("content")) if not isinstance(b.get("content"), str) else b.get("content")
                        if "user doesn't want to proceed" in res or "was rejected" in res:
                            continue
                        errors.append(f"{name}: `{clip(cmd, 160)}` → {clip(res, 300)}")
            txt = text_of(content)
            m = re.search(r"<command-name>/?([\w:-]+)</command-name>", txt)
            if m:
                skills.append(m.group(1))
            if txt and not NOISE.search(txt.strip()) and not (isinstance(content, list) and any(b.get("type") == "tool_result" for b in content)):
                user_msgs.append(clip(txt, 400))
    if not skills and not errors:
        return None
    sid = os.path.basename(path)[:-6]
    out = [f"## {title or '(untitled)'} — {sid}", f"{(first_ts or '')[:16]} → {(last_ts or '')[:16]}"]
    if skills:
        out.append("**Skills:** " + ", ".join(dict.fromkeys(skills)))
    if errors:
        out.append(f"**Failed tool calls ({len(errors)}):**")
        out += [f"- {e}" for e in errors[:max_errors]]
        if len(errors) > max_errors:
            out.append(f"- … {len(errors) - max_errors} more")
    if user_msgs:
        out.append("**User messages:**")
        out += [f"- {m}" for m in user_msgs[:25]]
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--checkpoint", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--skills-only", action="store_true")
    ap.add_argument("--max-errors", type=int, default=15)
    a = ap.parse_args()
    since = None
    if a.checkpoint and os.path.exists(STATE):
        since = json.load(open(STATE)).get("lastSweep")
    since = a.since or since
    cutoff = datetime.datetime.fromisoformat(since).timestamp() if since else 0
    files = []
    for d in glob.glob(os.path.join(PROJECTS, SLUG + "*")):
        files += [f for f in glob.glob(os.path.join(d, "*.jsonl")) if os.path.getmtime(f) >= cutoff]
    files.sort(key=os.path.getmtime)
    parts = []
    for f in files:
        d = digest(f, a.max_errors)
        if d and (not a.skills_only or "**Skills:**" in d):
            parts.append(d)
    body = f"# Transcript sweep since {since or 'the beginning'}\n\n{len(parts)} of {len(files)} sessions had skills or errors.\n\n" + "\n\n".join(parts) + "\n"
    if a.out:
        open(a.out, "w").write(body)
        print(f"wrote {a.out}: {len(parts)} sessions, {len(body)} chars")
    else:
        print(body)

main()
