<div align="center">

# 🧠 claude-memory-observe

**A colorful TUI for inspecting and managing Claude Code's auto-memory.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](#)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)
[![Single file](https://img.shields.io/badge/single--file-yes-orange)](#)

*One file. Zero dependencies. Just `python3 claude-memory-observe.py`.*

</div>

---

## What is this?

[Claude Code](https://claude.ai/code) keeps a per-project **auto-memory** at
`~/.claude/projects/<encoded-cwd>/memory/` — a folder of markdown files plus
an index (`MEMORY.md`).

After a few weeks you have 40+ entries, the index drifts from the files on
disk, you forget what's in there, and editing them by hand becomes a chore.

**`claude-memory-observe` is a single-file Python TUI to inspect, edit, and
reorganize that memory** — without leaving the terminal.

## ✨ Features

| | |
|---|---|
| 📋 **List** | Entries grouped by type, color-coded |
| 👁 &nbsp;**View** | Render a single entry as a card |
| ✏️ &nbsp;**Edit** | Open in your OS's default app |
| ➕ **Add** | Guided new-entry flow with a frontmatter template |
| 🗑 &nbsp;**Delete** | With confirmation, auto-strips the index line |
| 🔎 **Search** | Substring match across filename + name + description + body |
| 🔧 **Rebuild** | Regenerate `MEMORY.md` from frontmatter |
| 📊 **Stats** | Counts per type, orphan / missing index refs, recent edits |

## 🚀 Quickstart

```bash
curl -O https://raw.githubusercontent.com/chatthong/claude-memory-observe/main/claude-memory-observe.py
chmod +x claude-memory-observe.py
./claude-memory-observe.py
```

That's it. No `pip install`, no virtualenv, no third-party deps. Just **Python 3.10+**.

Or clone:

```bash
git clone https://github.com/chatthong/claude-memory-observe.git
cd claude-memory-observe
./claude-memory-observe.py
```

## 📺 What it looks like

```
╔══════════════════════════════════════════════════════════╗
║         Claude Memory Observer — Bonfire workspace       ║
╠══════════════════════════════════════════════════════════╣
║  [1]  📋  List all (grouped by type)                     ║
║  [2]  👁   View entry                                     ║
║  [3]  ✏️   Edit entry                                     ║
║  [4]  🗑   Delete entry                                   ║
║  [5]  ➕  Add new entry                                   ║
║  [6]  🔎  Search                                          ║
║  [7]  🔧  Rebuild MEMORY.md                              ║
║  [8]  📊  Stats / index sanity                           ║
║  [q]  🚪  Quit                                           ║
╚══════════════════════════════════════════════════════════╝
→ Choose:
```

## ⚙️ Configuration

The memory directory is resolved with this precedence (highest first):

1. `--memory-dir <path>` CLI flag
2. `$CLAUDE_MEMORY_DIR` environment variable
3. Default: `~/.claude/projects/<encoded-cwd>/memory`

`<encoded-cwd>` is your absolute working directory with `/` replaced by `-`.

> **Example** — running from `/Users/me/code/myproject` resolves to:
> ```
> ~/.claude/projects/-Users-me-code-myproject/memory
> ```

This mirrors how Claude Code itself keys auto-memory by `cwd`. The flag and
env-var overrides are your safety valves if the convention changes.

```bash
# Explicit path
./claude-memory-observe.py --memory-dir ~/.claude/projects/-Users-me-code-myproject/memory

# Or via env var
CLAUDE_MEMORY_DIR=~/.claude/projects/-Users-me-code-myproject/memory ./claude-memory-observe.py
```

## 📝 Memory file format

Each entry is a markdown file with YAML frontmatter:

```markdown
---
name: One-line title
description: One-line description used in the index
type: user | feedback | project | reference
---

Body. For `feedback` and `project` types, lead with the rule/fact,
then **Why:** and **How to apply:** lines.
```

The four types:

| Type | Purpose |
|---|---|
| `user` | Who you are — role, expertise, preferences |
| `feedback` | Behavioral guidance — corrections and validated approaches |
| `project` | Ongoing work — decisions, deadlines, motivation |
| `reference` | Pointers to external systems (Linear, dashboards, docs) |

The index (`MEMORY.md`) is generated from these. **Rebuilding overwrites it.**

## ⚠️ Caveats

- **Interactive only.** Not designed for piping or `curl | bash` execution —
  download the file and run it.
- **Edit opens the OS default app:** `open` on macOS, `xdg-open` on Linux,
  `os.startfile` on Windows.
- **"Rebuild MEMORY.md" is destructive.** Manual sub-groupings, custom
  ordering inside groups, and any free-form notes you wrote in the index
  will be lost. The script warns first and asks for confirmation.
- **Frontmatter parsing is regex-based**, not a full YAML parser. Stick to
  one-key-per-line `key: value` — no nested objects or multi-line strings.

## 🤔 Why does this exist?

Because Claude Code's auto-memory is just a folder of markdown files, and a
folder of markdown files deserves a tool that respects that: no database, no
daemon, no Electron app, no SaaS sign-up.

Just `python3 claude-memory-observe.py`.

## 🤝 Contributing

PRs welcome. The script is intentionally one file — keep it that way unless
there's a strong reason. No third-party deps unless absolutely necessary.

## License

TBD.
