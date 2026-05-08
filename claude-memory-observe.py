#!/usr/bin/env python3
"""Interactive Claude Code auto-memory manager for the Bonfire workspace."""

import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

def _encode_cwd(cwd: Path | None = None) -> str:
    """Mirror Claude Code's auto-memory key: absolute path with / -> -"""
    p = (cwd or Path.cwd()).resolve()
    return str(p).replace("/", "-")


def _resolve_memory_dir() -> tuple[Path, bool]:
    """Returns (path, was_overridden). Override = user passed --memory-dir
    or set $CLAUDE_MEMORY_DIR. Otherwise the path is derived from cwd."""
    if "--memory-dir" in sys.argv:
        i = sys.argv.index("--memory-dir")
        if i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1]).expanduser().resolve(), True
    env = os.environ.get("CLAUDE_MEMORY_DIR")
    if env:
        return Path(env).expanduser().resolve(), True
    return Path.home() / ".claude" / "projects" / _encode_cwd() / "memory", False


MEMORY_DIR, MEMORY_DIR_OVERRIDDEN = _resolve_memory_dir()
INDEX_FILE = MEMORY_DIR / "MEMORY.md"
TYPES = ["user", "feedback", "project", "reference"]
EDITOR = os.environ.get("EDITOR", "vim")
UI_WIDTH = 88

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def open_in_default_app(path: Path) -> None:
    """Open file in the OS default app (TextEdit on macOS, etc.)."""
    if sys.platform == "darwin":
        subprocess.call(["open", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.call(["xdg-open", str(path)])

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    return len(ANSI_RE.sub("", s))


def display_width(s: str) -> int:
    """Approximate terminal display columns. Strips ANSI; treats supplementary-plane
    emojis as 2 cols, drops variation selectors / ZWJ / combining marks. Good enough
    for menu alignment without pulling in wcwidth as a dependency."""
    s = ANSI_RE.sub("", s)
    w = 0
    for ch in s:
        cp = ord(ch)
        if cp in (0xFE0F, 0x200D) or unicodedata.combining(ch):
            continue
        if 0x1F300 <= cp <= 0x1FAFF:
            w += 2
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w


def c(code: str, s: str) -> str:
    if not USE_COLOR:
        return s
    return f"\033[{code}m{s}\033[0m"


def bold(s):    return c("1", s)
def dim(s):     return c("2", s)
def red(s):     return c("31", s)
def green(s):   return c("32", s)
def yellow(s):  return c("33", s)
def blue(s):    return c("34", s)
def magenta(s): return c("35", s)
def cyan(s):    return c("36", s)


TYPE_META = {
    "user":      ("👤", cyan,    "USER"),
    "feedback":  ("💬", yellow,  "FEEDBACK"),
    "project":   ("📁", green,   "PROJECT"),
    "reference": ("📚", magenta, "REFERENCE"),
    "?":         ("❓", red,     "UNKNOWN"),
}


def term_width() -> int:
    try:
        return shutil.get_terminal_size((100, 20)).columns
    except Exception:
        return 100


def truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: max(1, n - 1)] + "…"


def parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text()
    except Exception as e:
        return {"_error": str(e)}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {"_no_frontmatter": True, "_body": text}
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.splitlines():
        kv = re.match(r"^([\w-]+):\s*(.*)$", line)
        if kv:
            fm[kv.group(1).strip()] = kv.group(2).strip()
    fm["_body"] = body
    return fm


def load_all() -> list[dict]:
    entries = []
    if not MEMORY_DIR.exists():
        return entries
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        fm = parse_frontmatter(f)
        entries.append({
            "file": f.name,
            "path": f,
            "name": fm.get("name", "(no name)"),
            "description": fm.get("description", "(no description)"),
            "type": fm.get("type", "?").lower(),
            "_fm": fm,
        })
    return entries


def group_by_type(entries: list[dict]) -> dict:
    grouped = {t: [] for t in list(TYPE_META.keys())}
    for e in entries:
        t = e["type"] if e["type"] in grouped else "?"
        grouped[t].append(e)
    return grouped


def render_table(rows: list[tuple], widths: tuple, header: tuple, color_fn=None) -> None:
    """Render an aligned table with Unicode borders."""
    top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    mid = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

    def fmt_row(cells, paint=None):
        parts = []
        for cell, w in zip(cells, widths):
            text = truncate(str(cell), w)
            padded = text + " " * (w - len(text))
            if paint:
                padded = paint(padded)
            parts.append(" " + padded + " ")
        return dim("│") + dim("│").join(parts) + dim("│")

    print(dim(top))
    print(fmt_row(header, paint=bold))
    print(dim(mid))
    for r in rows:
        print(fmt_row(r, paint=color_fn))
    print(dim(bot))


def cmd_list(entries: list[dict]) -> None:
    """Vertical card list — readable on narrow terminals, no table wrapping."""
    grouped = group_by_type(entries)
    width = min(term_width() - 2, 120)
    text_w = max(40, width - 10)

    idx = 1
    print()
    for t in TYPE_META.keys():
        items = grouped[t]
        if not items:
            continue
        emoji, color, label = TYPE_META[t]
        print()
        print(color(bold(f"  {emoji}  {label}  ({len(items)})")))
        print(color("  " + "─" * (width - 4)))
        for e in items:
            e["_idx"] = idx
            num = color(bold(f"[{idx:>2}]"))
            print(f"  {num}  {bold(e['file'])}")
            print(f"        {dim('name:')} {e['name']}")
            print(f"        {dim('desc:')} {truncate(e['description'], text_w)}")
            idx += 1
        print()
    print(dim(f"  Total: {len(entries)} entries\n"))


def pick_entry(entries: list[dict]) -> dict | None:
    cmd_list(entries)
    raw = input(cyan("→ Entry # (or blank to cancel): ")).strip()
    if not raw:
        return None
    if not raw.isdigit():
        print(red("✗ Not a number."))
        return None
    n = int(raw)
    for e in entries:
        if e.get("_idx") == n:
            return e
    print(red(f"✗ No entry #{n}."))
    return None


def render_card(e: dict) -> None:
    emoji, color, label = TYPE_META.get(e["type"], TYPE_META["?"])
    width = min(100, term_width() - 4)
    print()
    print(color("╔" + "═" * (width - 2) + "╗"))
    title = f" {emoji}  {e['name']} "
    title_t = truncate(title, width - 2)
    print(color("║") + bold(title_t.ljust(width - 2)) + color("║"))
    print(color("╠" + "═" * (width - 2) + "╣"))
    meta = f"  type: {label}    file: {e['file']}"
    print(color("║") + truncate(meta, width - 2).ljust(width - 2) + color("║"))
    print(color("╚" + "═" * (width - 2) + "╝"))
    body = e["_fm"].get("_body", "").rstrip()
    print(body)
    print()


def cmd_view(entries: list[dict]) -> None:
    e = pick_entry(entries)
    if not e:
        return
    render_card(e)


def cmd_edit(entries: list[dict]) -> None:
    e = pick_entry(entries)
    if not e:
        return
    open_in_default_app(e["path"])
    print(green(f"✓ Opened in default app: {e['file']}"))
    input(cyan("→ Press Enter when done editing... "))


def remove_index_lines(file_basename: str) -> int:
    if not INDEX_FILE.exists():
        return 0
    lines = INDEX_FILE.read_text().splitlines(keepends=True)
    pattern = re.compile(rf"\]\({re.escape(file_basename)}\)")
    kept = [ln for ln in lines if not pattern.search(ln)]
    removed = len(lines) - len(kept)
    if removed:
        INDEX_FILE.write_text("".join(kept))
    return removed


def cmd_delete(entries: list[dict]) -> None:
    e = pick_entry(entries)
    if not e:
        return
    print()
    print(red(bold(f"⚠  About to delete: {e['file']}")))
    print(f"   name: {e['name']}")
    print(f"   type: {e['type']}")
    confirm = input(red("→ Confirm delete? (y/N): ")).strip().lower()
    if confirm != "y":
        print(yellow("✗ Cancelled."))
        return
    e["path"].unlink()
    removed = remove_index_lines(e["file"])
    print(green(f"✓ Deleted: {e['file']} (removed {removed} index line(s))"))


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "entry"


def cmd_add() -> None:
    print()
    print(green(bold("➕  Add new memory entry")))
    print(dim(f"   Types: {', '.join(TYPES)}"))
    t = input(cyan("→ Type: ")).strip().lower()
    if t not in TYPES:
        print(red(f"✗ Invalid type. Must be one of: {TYPES}"))
        return
    name = input(cyan("→ Name (one-line title): ")).strip()
    if not name:
        print(red("✗ Name required."))
        return
    desc = input(cyan("→ Description (one-line, used for index): ")).strip()
    if not desc:
        print(red("✗ Description required."))
        return

    default_filename = f"{t}_{slugify(name)}.md"
    fname_input = input(cyan(f"→ Filename [{default_filename}]: ")).strip()
    fname = fname_input or default_filename
    if not fname.endswith(".md"):
        fname += ".md"
    target = MEMORY_DIR / fname
    if target.exists():
        print(red(f"✗ File already exists: {fname}"))
        return

    template = f"""---
name: {name}
description: {desc}
type: {t}
---

[Body — fill in. For feedback/project, lead with the rule/fact, then **Why:** and **How to apply:** lines.]
"""
    target.write_text(template)
    print(green(f"✓ Created: {fname}"))
    open_now = input(cyan("→ Open in default app now? (Y/n): ")).strip().lower()
    if open_now in ("", "y"):
        open_in_default_app(target)
        input(cyan("→ Press Enter when done editing... "))

    if INDEX_FILE.exists():
        existing = INDEX_FILE.read_text()
        if not existing.endswith("\n"):
            existing += "\n"
        line = f"- [{name}]({fname}) — {desc}\n"
        INDEX_FILE.write_text(existing + line)
        print(green("✓ Appended to MEMORY.md index."))


def cmd_search(entries: list[dict]) -> None:
    q = input(cyan("→ Search keyword: ")).strip().lower()
    if not q:
        return
    hits = []
    for e in entries:
        hay = (
            e["file"] + " " + e["name"] + " " + e["description"] + " "
            + (e["_fm"].get("_body") or "")
        ).lower()
        if q in hay:
            hits.append(e)
    if not hits:
        print(yellow("∅ No matches."))
        return

    width = min(term_width() - 2, 120)
    text_w = max(40, width - 10)
    print()
    print(green(bold(f"  🔎  {len(hits)} match(es) for '{q}'")))
    print(green("  " + "─" * (width - 4)))
    for i, e in enumerate(hits, 1):
        e["_idx"] = i
        emoji, color, label = TYPE_META.get(e["type"], TYPE_META["?"])
        num = color(bold(f"[{i:>2}]"))
        print(f"  {num}  {emoji} {color(label)}  {bold(e['file'])}")
        print(f"        {dim('name:')} {e['name']}")
        print(f"        {dim('desc:')} {truncate(e['description'], text_w)}")
    print()
    raw = input(cyan("→ View one? Entry # (or blank to skip): ")).strip()
    if raw.isdigit():
        n = int(raw)
        for e in hits:
            if e.get("_idx") == n:
                render_card(e)
                return


def cmd_rebuild(entries: list[dict]) -> None:
    print()
    print(yellow(bold("🔧  Rebuild MEMORY.md")))
    print()
    print(f"  {bold('What this does:')}")
    print(f"    1. Reads frontmatter ({dim('name:')}, {dim('description:')}, {dim('type:')}) from every .md file")
    print(f"    2. Groups entries by type ({cyan('USER')} → {yellow('FEEDBACK')} → {green('PROJECT')} → {magenta('REFERENCE')})")
    print(f"    3. {red('OVERWRITES')} {bold('MEMORY.md')} with a freshly generated index")
    print()
    print(f"  {bold('When to use:')}")
    print(f"    • Files added/deleted outside this script → re-sync the index")
    print(f"    • Edited a {dim('description:')} in frontmatter → reflect new text in index")
    print(f"    • Index has drift (run option 8 first to check)")
    print()
    print(f"  {red(bold('What gets LOST:'))}")
    print(f"    • Manual sub-groupings ({dim('e.g. current ## bfg-swt / ## td-rep sections')})")
    print(f"    • Custom ordering inside groups (will be alphabetical)")
    print(f"    • Any free-form notes/commentary you wrote in MEMORY.md")
    print()
    print(f"  {dim('Source of truth = each file frontmatter.  Destination = MEMORY.md.')}")
    print()
    confirm = input(yellow(bold("→ Proceed with rebuild? (y/N): "))).strip().lower()
    if confirm != "y":
        print(yellow("✗ Cancelled."))
        return
    grouped = group_by_type(entries)
    out = ["# Memory Index", ""]
    for t in TYPE_META.keys():
        items = grouped[t]
        if not items:
            continue
        emoji, _, label = TYPE_META[t]
        out.append(f"## {emoji} {label}")
        out.append("")
        for e in items:
            out.append(f"- [{e['name']}]({e['file']}) — {e['description']}")
        out.append("")
    INDEX_FILE.write_text("\n".join(out).rstrip() + "\n")
    print(green(f"✓ Rebuilt {INDEX_FILE.name} with {len(entries)} entries."))


def cmd_wipe() -> None:
    entries = load_all()
    print()
    print(red(bold(f"🔥  Wipe memory: {MEMORY_DIR.parent.name}")))
    print(dim("    (only this project's memory — other projects' memory dirs are untouched)"))
    print()
    print(f"  Target dir : {bold(str(MEMORY_DIR))}")
    print(f"  Entries    : {bold(str(len(entries)))} files")
    if entries:
        print(f"  Includes   :")
        for e in entries[:5]:
            print(f"    {dim('-')} {e['file']}")
        if len(entries) > 5:
            print(dim(f"    ... and {len(entries) - 5} more"))
    if INDEX_FILE.exists():
        print(f"  Index file : {INDEX_FILE.name} ({INDEX_FILE.stat().st_size} bytes)")
    print()
    print(red(bold("  ⚠  THIS CANNOT BE UNDONE.")))
    project_key = MEMORY_DIR.parent.name
    print(f"  To confirm, type the project key exactly: {bold(project_key)}")
    typed = input(red("→ Confirm (or blank to cancel): ")).strip()
    if typed != project_key:
        print(yellow("✗ Cancelled (project key didn't match)."))
        return

    backup_choice = input(cyan("→ Move current memory to a timestamped backup first? (Y/n): ")).strip().lower()
    if backup_choice in ("", "y"):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = MEMORY_DIR.parent / f"memory.bak.{ts}"
        shutil.move(str(MEMORY_DIR), str(backup_dir))
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        print(green(f"✓ Backed up to: {backup_dir}"))
    else:
        deleted = 0
        for f in MEMORY_DIR.glob("*.md"):
            f.unlink()
            deleted += 1
        print(green(f"✓ Deleted {deleted} files (no backup)."))

    INDEX_FILE.write_text("# Memory Index\n")
    print(green("✓ Recreated empty MEMORY.md."))


def cmd_nuke() -> None:
    dirs = _list_existing_memory_dirs()
    print()
    print(red(bold("☢  NUKE — wipe memory across EVERY Claude Code project")))
    print(dim("    Resets you to a 'fresh Claude' state for memory specifically."))
    print(dim("    Other Claude Code state under ~/.claude/ (settings, history, etc) is untouched."))
    print()
    if not dirs:
        print(yellow("  No memory dirs found anywhere — nothing to nuke."))
        return

    total = sum(d["count"] for d in dirs)
    print(f"  Projects affected : {bold(str(len(dirs)))}")
    print(f"  Total entries     : {bold(str(total))}")
    print(f"  Will affect:")
    for d in dirs:
        ts = datetime.fromtimestamp(d["mtime"]).strftime("%Y-%m-%d")
        print(f"    {dim('-')} {d['encoded']:<45}  {d['count']:>3} entries  ·  {dim(ts)}")
    print()
    print(red(bold("  ⚠  THIS CANNOT BE UNDONE without restoring from the backup option below.")))
    confirm_phrase = "NUKE ALL"
    print(f"  To confirm, type: {bold(confirm_phrase)}")
    typed = input(red("→ Confirm (or blank to cancel): ")).strip()
    if typed != confirm_phrase:
        print(yellow(f"✗ Cancelled (didn't type {confirm_phrase!r})."))
        return

    backup_choice = input(
        cyan("→ Move each memory dir to a timestamped backup first? (Y/n): ")
    ).strip().lower()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if backup_choice in ("", "y"):
        for d in dirs:
            backup_path = d["path"].parent / f"memory.bak.{ts}"
            shutil.move(str(d["path"]), str(backup_path))
            d["path"].mkdir(parents=True, exist_ok=True)
            (d["path"] / "MEMORY.md").write_text("# Memory Index\n")
        print(green(f"✓ Backed up {len(dirs)} memory dirs to memory.bak.{ts}/ inside each project."))
    else:
        wiped = 0
        for d in dirs:
            for f in d["path"].glob("*.md"):
                f.unlink()
                wiped += 1
            (d["path"] / "MEMORY.md").write_text("# Memory Index\n")
        print(green(f"✓ Wiped {wiped} memory files across {len(dirs)} projects (no backup)."))

    print()
    print(yellow("  All memory dirs are now empty. The currently-loaded dir was reset too;"))
    print(yellow("  the menu will show 0 entries until you add new ones."))


def cmd_stats(entries: list[dict]) -> None:
    grouped = group_by_type(entries)
    print()
    print(blue(bold("📊  Memory Stats")))
    print(dim(f"    {MEMORY_DIR}"))
    print()
    print(f"    {bold(str(len(entries)).rjust(4))}   {bold('TOTAL')}")
    for t in TYPE_META.keys():
        items = grouped[t]
        if items:
            emoji, color, label = TYPE_META[t]
            count = color(str(len(items)).rjust(4))
            print(f"    {count}   {emoji}  {color(label)}")

    print()
    if INDEX_FILE.exists():
        index_text = INDEX_FILE.read_text()
        index_refs = set(re.findall(r"\]\(([\w./-]+\.md)\)", index_text))
        files_on_disk = {e["file"] for e in entries}
        orphan_refs = index_refs - files_on_disk
        missing_refs = files_on_disk - index_refs
        print(blue(bold(f"🔗  Index sanity ({INDEX_FILE.name})")))
        print(f"    {str(len(index_refs)).rjust(4)}   referenced files")
        if orphan_refs:
            print(f"    {red(str(len(orphan_refs)).rjust(4))}   {red('orphan refs (in index, missing on disk)')}")
            for f in sorted(orphan_refs):
                print(red(f"         - {f}"))
        else:
            print(f"    {green('   0')}   orphan refs")
        if missing_refs:
            print(f"    {yellow(str(len(missing_refs)).rjust(4))}   {yellow('files on disk not in index')}")
            for f in sorted(missing_refs):
                print(yellow(f"         - {f}"))
        else:
            print(f"    {green('   0')}   files on disk not in index")
    else:
        print(red(f"    ✗ No index file at {INDEX_FILE}"))

    print()
    print(blue(bold("🕒  Most recently modified")))
    last_modified = sorted(entries, key=lambda e: e["path"].stat().st_mtime, reverse=True)[:5]
    for e in last_modified:
        ts = datetime.fromtimestamp(e["path"].stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        emoji = TYPE_META.get(e["type"], TYPE_META["?"])[0]
        print(f"    {dim(ts)}  {emoji}  {e['file']}")
    print()


def render_menu() -> None:
    width = min(term_width() - 2, UI_WIDTH)
    inner = width - 2

    # Subtitle: encoded project key + entry count
    encoded_full = MEMORY_DIR.parent.name
    try:
        n_entries = sum(1 for f in MEMORY_DIR.glob("*.md") if f.name != "MEMORY.md")
    except OSError:
        n_entries = 0
    encoded_sub = encoded_full
    subtitle_plain = f"{encoded_sub}  ·  {n_entries} entries"
    if display_width(subtitle_plain) > inner - 4:
        suffix = f"…  ·  {n_entries} entries"
        max_enc = inner - 4 - display_width(suffix)
        if max_enc > 5:
            encoded_sub = encoded_full[: max_enc] + "…"
            subtitle_plain = f"{encoded_sub}  ·  {n_entries} entries"
        else:
            subtitle_plain = f"{n_entries} entries"

    # Wipe label: show which memory dir gets wiped (truncate if needed)
    wipe_prefix = "Wipe memory ("
    wipe_overhead = display_width(f"     [w]  {wipe_prefix})")
    wipe_avail = inner - wipe_overhead - 1
    wipe_name = encoded_full
    if len(wipe_name) > wipe_avail and wipe_avail > 5:
        wipe_name = wipe_name[: wipe_avail - 1] + "…"
    wipe_label = f"{wipe_prefix}{wipe_name})"

    print()
    print(blue("╔" + "═" * inner + "╗"))
    _box_print(bold("Claude Memory Observer".center(inner)), inner)
    _box_print(dim(subtitle_plain.center(inner)), inner)
    print(blue("╠" + "═" * inner + "╣"))

    sections = [
        (cyan,   "READ", [
            ("1", "List all (grouped by type)"),
            ("2", "View entry"),
            ("3", "Search"),
        ]),
        (green,  "MODIFY", [
            ("4", "Add new entry"),
            ("5", "Edit entry"),
            ("6", "Delete entry"),
        ]),
        (yellow, "MAINTAIN", [
            ("7", "Rebuild MEMORY.md"),
            ("8", "Stats / index sanity"),
        ]),
        (red,    "DANGER ZONE", [
            ("w", wipe_label),
            ("n", "Nuke ALL Claude memory (every project, system-wide)"),
        ]),
    ]
    for color, header, items in sections:
        _box_print("  " + color(bold(header)), inner)
        for key, label in items:
            _box_print(f"     {bold(f'[{key}]')}  {label}", inner)
        _box_print("", inner)

    _box_print(f"     {bold('[q]')}  Quit", inner)
    print(blue("╚" + "═" * inner + "╝"))


def _list_existing_memory_dirs() -> list[dict]:
    """Discover all Claude Code memory dirs under ~/.claude/projects/*/memory/."""
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return []
    out: list[dict] = []
    for proj in sorted(base.iterdir()):
        memdir = proj / "memory"
        if not memdir.is_dir():
            continue
        try:
            md_files = [f for f in memdir.glob("*.md") if f.name != "MEMORY.md"]
            count = len(md_files)
            mtime = max(
                (f.stat().st_mtime for f in md_files),
                default=memdir.stat().st_mtime,
            )
        except OSError:
            continue
        out.append({
            "path": memdir,
            "encoded": proj.name,
            "count": count,
            "mtime": mtime,
        })
    out.sort(key=lambda d: d["mtime"], reverse=True)
    return out


def _box_print(content: str, inner_w: int) -> None:
    """Print one line inside the blue box; pad based on display width (handles emoji)."""
    pad = inner_w - display_width(content)
    print(blue("║") + content + " " * max(0, pad) + blue("║"))


def render_launcher_screen(default_path: Path) -> Path | None:
    """Always-on launcher: lets the user confirm the cwd-detected memory dir
    or hop to a different one. Returns chosen Path, or None to exit."""
    width = min(term_width() - 2, UI_WIDTH)
    inner = width - 2

    all_dirs = _list_existing_memory_dirs()
    default_entry: dict | None = None
    other_entries: list[dict] = []
    for d in all_dirs:
        if d["path"] == default_path:
            default_entry = d
        else:
            other_entries.append(d)

    print()
    print(blue("╔" + "═" * inner + "╗"))
    _box_print(bold("Claude Memory Observer".center(inner)), inner)
    _box_print(dim("Select a memory store".center(inner)), inner)
    print(blue("╠" + "═" * inner + "╣"))

    _box_print("", inner)
    _box_print("  " + yellow("💡 Tip:") + "  Run from inside your Claude Code project dir so the", inner)
    _box_print("          cwd-detected memory shows up as the default option below.", inner)
    _box_print("", inner)

    options: list[tuple[int, Path]] = []
    idx = 1

    # Section: detected (cwd-derived) default
    if default_entry:
        _box_print("  " + bold("Detected for current working dir:"), inner)
        ts = datetime.fromtimestamp(default_entry["mtime"]).strftime("%Y-%m-%d")
        marker = green(bold("← default"))
        encoded = default_entry["encoded"]
        count = default_entry["count"]
        line = (
            f"     {bold(f'[{idx}]')}  {cyan(encoded)}  "
            f"{dim('·')}  {green(f'{count} entries')}  "
            f"{dim('·')}  {dim(ts)}   {marker}"
        )
        _box_print(line, inner)
        options.append((idx, default_entry["path"]))
        idx += 1
        _box_print("", inner)
    else:
        _box_print("  " + bold("Detected for current working dir:"), inner)
        cwd_str = str(default_path)
        if len(cwd_str) > inner - 8:
            cwd_str = "…" + cwd_str[-(inner - 9):]
        _box_print(f"     {dim(cwd_str)}", inner)
        _box_print(f"     {yellow('(empty / not found — pick from list below or Exit)')}", inner)
        _box_print("", inner)

    # Section: other dirs
    if other_entries:
        section_label = "Other memory dirs on this machine:" if default_entry else "Memory dirs on this machine:"
        _box_print("  " + bold(section_label), inner)
        for d in other_entries:
            ts = datetime.fromtimestamp(d["mtime"]).strftime("%Y-%m-%d")
            encoded = d["encoded"]
            count = d["count"]
            line = (
                f"     {bold(f'[{idx}]')}  {cyan(encoded)}  "
                f"{dim('·')}  {green(f'{count} entries')}  "
                f"{dim('·')}  {dim(ts)}"
            )
            _box_print(line, inner)
            options.append((idx, d["path"]))
            idx += 1
        _box_print("", inner)

    if not options:
        _box_print("  " + yellow("No Claude memory dirs found anywhere on this machine."), inner)
        _box_print("  " + dim("Override with --memory-dir <path> or $CLAUDE_MEMORY_DIR."), inner)
        _box_print("", inner)

    _box_print(f"     {bold('[x]')}  Exit", inner)
    _box_print("", inner)
    print(blue("╚" + "═" * inner + "╝"))
    print()

    if not options:
        return None

    prompt = "→ Pick"
    if default_entry:
        prompt += " (Enter for default)"
    prompt += ": "
    raw = input(cyan(prompt)).strip().lower()

    if raw == "" and default_entry:
        return default_entry["path"]
    if raw == "x" or raw == "":
        print(green("✓ Bye."))
        return None
    if not raw.isdigit():
        print(red("✗ Not a number — exiting."))
        return None
    n = int(raw)
    for opt_idx, opt_path in options:
        if opt_idx == n:
            print(green(f"✓ Using {opt_path}"))
            return opt_path
    print(red(f"✗ No option #{n} — exiting."))
    return None


def main() -> int:
    global MEMORY_DIR, INDEX_FILE
    if MEMORY_DIR_OVERRIDDEN:
        # User explicitly chose via --memory-dir or $CLAUDE_MEMORY_DIR.
        # Respect their choice and skip the launcher; just bail clean if missing.
        if not MEMORY_DIR.exists():
            print(red(f"✗ ERROR: memory dir not found: {MEMORY_DIR}"), file=sys.stderr)
            print(dim("  (resolved from --memory-dir or $CLAUDE_MEMORY_DIR)"), file=sys.stderr)
            return 1
    else:
        # Default cwd-derived path. Always show the launcher so the user can
        # confirm or hop to a different project's memory.
        chosen = render_launcher_screen(MEMORY_DIR)
        if chosen is None:
            return 0
        MEMORY_DIR = chosen
        INDEX_FILE = MEMORY_DIR / "MEMORY.md"
    cmd_stats(load_all())
    while True:
        entries = load_all()
        render_menu()
        choice = input(cyan("→ Choose: ")).strip().lower()
        if choice == "q":
            print(green("✓ Bye."))
            return 0
        elif choice == "1":
            cmd_list(entries)
        elif choice == "2":
            cmd_view(entries)
        elif choice == "3":
            cmd_edit(entries)
        elif choice == "4":
            cmd_delete(entries)
        elif choice == "5":
            cmd_add()
        elif choice == "6":
            cmd_search(entries)
        elif choice == "7":
            cmd_rebuild(entries)
        elif choice == "8":
            cmd_stats(entries)
        elif choice == "w":
            cmd_wipe()
        elif choice == "n":
            cmd_nuke()
        else:
            print(red("✗ Unknown choice."))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(yellow("\n✗ Interrupted."))
        sys.exit(130)
