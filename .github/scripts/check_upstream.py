#!/usr/bin/env python3
"""
Checks MarlinFirmware/Marlin (bugfix-2.1.x) for new commits that affect
files relevant to the Kobra 2 Neo (GD32F303, FT_MOTION, bilinear ABL, TFT SPI).

Creates a GitHub Issue summarising relevant commits, with one comment per
commit containing the filtered diff.
"""

import subprocess
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

UPSTREAM_BRANCH  = "marlin-upstream/bugfix-2.1.x"
SHA_FILE         = Path(".github/upstream_sha.txt")
DIFF_LINE_LIMIT  = 450   # lines per diff comment before truncation

# Paths that matter for this printer
RELEVANT = [
    "Marlin/src/module/ft_motion",
    "Marlin/src/module/temperature",
    "Marlin/src/module/motion",
    "Marlin/src/module/stepper",
    "Marlin/src/module/planner",
    "Marlin/src/module/probe",
    "Marlin/src/module/settings",
    "Marlin/src/module/endstops",
    "Marlin/src/feature/runout",
    "Marlin/src/feature/pause",
    "Marlin/src/feature/tramming",
    "Marlin/src/feature/bedlevel",
    "Marlin/src/feature/backlash",
    "Marlin/src/feature/babystep",
    "Marlin/src/feature/hotend_idle",
    "Marlin/src/gcode/temp/",
    "Marlin/src/gcode/bedlevel/",
    "Marlin/src/gcode/calibrate/",
    "Marlin/src/gcode/feature/ft_motion/",
    "Marlin/src/gcode/feature/advance/",
    "Marlin/src/gcode/feature/pause/",
    "Marlin/src/gcode/sd/M24_M25",
    "Marlin/src/gcode/motion/",
    "Marlin/src/gcode/probe/",
    "Marlin/src/lcd/tft/",
    "Marlin/src/lcd/menu/",
    "Marlin/src/inc/",
    "Marlin/src/MarlinCore",
]

# Paths to exclude even when they match a RELEVANT prefix
EXCLUDE = [
    "Marlin/src/lcd/language/",
    "Marlin/src/lcd/dogm/fontdata/",
    "Marlin/src/lcd/extui/",
    "Marlin/src/lcd/e3v2/",
    "Marlin/src/lcd/dwin/",
    "Marlin/src/HAL/",
    "Marlin/src/pins/",
    "Marlin/src/module/scara",
    "Marlin/src/module/delta",
    "Marlin/src/module/polar",
    "Marlin/src/module/polargraph",
]

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def run(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def is_relevant(files: list[str]) -> list[str]:
    """Return the subset of files that are relevant (and not excluded)."""
    keep = []
    for f in files:
        if any(f.startswith(ex) for ex in EXCLUDE):
            continue
        if any(f.startswith(rel) or rel in f for rel in RELEVANT):
            keep.append(f)
    return keep


def commit_files(sha: str) -> list[str]:
    out = run(f"git diff-tree --no-commit-id -r --name-only {sha}")
    return out.splitlines() if out else []


def commit_diff(sha: str, files: list[str]) -> str:
    if not files:
        return "(no relevant file changes)"
    result = subprocess.run(
        ["git", "show", sha, "--"] + files,
        capture_output=True, text=True
    )
    lines = result.stdout.splitlines()
    if len(lines) > DIFF_LINE_LIMIT:
        lines = lines[:DIFF_LINE_LIMIT]
        lines.append(f"\n... (diff truncated — {len(result.stdout.splitlines()) - DIFF_LINE_LIMIT} more lines, "
                     f"view full diff at https://github.com/MarlinFirmware/Marlin/commit/{sha})")
    return "\n".join(lines)


def gh(args: list[str]) -> str:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
    return result.stdout.strip()

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    last_sha = SHA_FILE.read_text().strip() if SHA_FILE.exists() else \
               run(f"git merge-base HEAD {UPSTREAM_BRANCH}")

    new_sha = run(f"git rev-parse {UPSTREAM_BRANCH}")

    if last_sha == new_sha:
        print("Upstream has not moved. Nothing to do.")
        return

    raw = run(
        f"git log {last_sha}..{UPSTREAM_BRANCH} "
        f"--format='%H|%s|%an|%ad' --date=short --no-merges --reverse"
    )

    if not raw:
        print("No new commits upstream.")
        SHA_FILE.write_text(new_sha + "\n")
        return

    all_commits = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            all_commits.append({
                "sha":     parts[0],
                "subject": parts[1],
                "author":  parts[2],
                "date":    parts[3],
            })

    # Filter to relevant commits only
    relevant_commits = []
    for c in all_commits:
        files = is_relevant(commit_files(c["sha"]))
        if files:
            c["files"] = files
            relevant_commits.append(c)

    print(f"Upstream: {len(all_commits)} new commits, {len(relevant_commits)} relevant.")

    if not relevant_commits:
        print("No relevant commits — no issue created.")
        SHA_FILE.write_text(new_sha + "\n")
        return

    # ── Build issue body ────────────────────────────────────────────────
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n     = len(relevant_commits)

    body  = f"## {n} upstream commit{'s' if n > 1 else ''} relevant to Kobra 2 Neo\n\n"
    body += f"> Scanned `MarlinFirmware/Marlin @ bugfix-2.1.x` on {today}.  \n"
    body += f"> {len(all_commits)} total new commits upstream — {n} touch files relevant to this printer.\n\n"
    body += "| # | Hash | Date | Author | Subject |\n"
    body += "|---|------|------|--------|---------|\n"

    for i, c in enumerate(relevant_commits, 1):
        short = c["sha"][:8]
        url   = f"https://github.com/MarlinFirmware/Marlin/commit/{c['sha']}"
        body += f"| {i} | [`{short}`]({url}) | {c['date']} | {c['author']} | {c['subject']} |\n"

    body += f"\n---\n_Diffs for each commit are posted as comments below._  \n"
    body += f"_To apply a fix: `git cherry-pick -x <hash>`_\n"

    issue_url = gh([
        "issue", "create",
        "--title", f"[Marlin upstream] {n} relevant commit{'s' if n > 1 else ''} — {today}",
        "--body",  body,
        "--label", "upstream-watch",
    ])

    # If label doesn't exist yet gh will error but still create the issue —
    # retry without label
    if not issue_url:
        issue_url = gh([
            "issue", "create",
            "--title", f"[Marlin upstream] {n} relevant commit{'s' if n > 1 else ''} — {today}",
            "--body",  body,
        ])

    if not issue_url:
        print("Failed to create issue.", file=sys.stderr)
        sys.exit(1)

    SHA_FILE.write_text(new_sha + "\n")
    print(f"Issue created: {issue_url}")

    # ── One comment per relevant commit ─────────────────────────────────
    for i, c in enumerate(relevant_commits, 1):
        short = c["sha"][:8]
        url   = f"https://github.com/MarlinFirmware/Marlin/commit/{c['sha']}"
        diff  = commit_diff(c["sha"], c["files"])

        comment  = f"### [{i}/{n}] `{short}` — {c['subject']}\n\n"
        comment += f"**Author:** {c['author']} &nbsp;|&nbsp; **Date:** {c['date']}  \n"
        comment += f"**Upstream commit:** {url}\n\n"
        comment += f"**Relevant files changed:**\n"
        for f in c["files"]:
            comment += f"- `{f}`\n"
        comment += f"\n```diff\n{diff}\n```\n"

        if len(comment) > 65000:
            comment = comment[:65000] + "\n\n> _(comment truncated)_"

        gh(["issue", "comment", issue_url, "--body", comment])
        print(f"  Posted diff comment {i}/{n}")

    print("Done.")


if __name__ == "__main__":
    main()
