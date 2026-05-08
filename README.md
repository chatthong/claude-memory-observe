<div align="center">

# 🧠 claude-memory-observe

**A colorful TUI for inspecting and managing Claude Code's auto-memory.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](#)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](#)
[![Single file](https://img.shields.io/badge/single--file-yes-orange)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

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

Commands are grouped into four sections in the menu:

#### 📖 &nbsp;Read

|   | Command | What it does |
|---|---|---|
| `[1]` | **List** | Entries grouped by type, color-coded |
| `[2]` | **View** | Render a single entry as a card |
| `[3]` | **Search** | Substring match across filename + name + description + body |

#### ✏️ &nbsp;Modify

|   | Command | What it does |
|---|---|---|
| `[4]` | **Add** | Guided new-entry flow with a frontmatter template |
| `[5]` | **Edit** | Open in your OS's default app |
| `[6]` | **Delete** | With confirmation, auto-strips the index line |

#### 🔧 &nbsp;Maintain

|   | Command | What it does |
|---|---|---|
| `[7]` | **Rebuild** | Regenerate `MEMORY.md` from frontmatter |
| `[8]` | **Stats** | Counts per type, orphan / missing index refs, recent edits |

#### 🔥 &nbsp;Danger zone

|   | Command | What it does |
|---|---|---|
| `[w]` | **Wipe** | Wipe the **currently-selected** project's memory only |
| `[n]` | **Nuke** | Wipe memory across **every** Claude Code project on this machine |

> Both Wipe and Nuke require typed confirmation and offer a timestamped
> backup by default. See [Caveats](#%EF%B8%8F-caveats) for the full safety design.

## 🚀 Quickstart

**Run it from inside your Claude Code project directory** — that's how the
script finds the right memory store automatically:

```bash
cd ~/code/your-claude-project
curl -O https://raw.githubusercontent.com/chatthong/claude-memory-observe/main/claude-memory-observe.py
chmod +x claude-memory-observe.py
./claude-memory-observe.py
```

That's it. No `pip install`, no virtualenv, no third-party deps. Just **Python 3.10+**.

If you'd rather keep the script in a shared location:

```bash
# Once — install
git clone https://github.com/chatthong/claude-memory-observe.git ~/tools/claude-memory-observe
ln -s ~/tools/claude-memory-observe/claude-memory-observe.py /usr/local/bin/claude-memory-observe

# Then — from any project dir
cd ~/code/your-claude-project
claude-memory-observe
```

## 🆕 First run

If you launch the script from a directory that has no Claude memory yet
(e.g. a brand-new project, or just from your home dir), you get a friendly
picker that surfaces every memory dir already on your machine and lets you
hop into one — or exit cleanly:

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                           ✗  No Claude memory directory found                            ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  💡 Tip:  Launch this from inside your Claude Code project dir so it                     ║
║          auto-detects that project's memory. The picker below is a fallback.             ║
║          Example: cd ~/code/myproject && ./claude-memory-observe.py                      ║
║                                                                                          ║
║  Looked at:                                                                              ║
║    /Users/me/.claude/projects/-Users-me-Desktop/memory                                   ║
║                                                                                          ║
║  Why:                                                                                    ║
║    Claude Code keys auto-memory by the directory it was launched from.                   ║
║    The current working dir doesn't have a memory store yet.                              ║
║                                                                                          ║
║  Existing memory dirs on this machine:                                                   ║
║    [ 1]  -Users-me-code-myproject       42 entries  ·  2026-05-08                        ║
║    [ 2]  -Users-me-code-otherproject     5 entries  ·  2026-04-12                        ║
║    [ x]  Exit                                                                            ║
║                                                                                          ║
║  Or override explicitly:                                                                 ║
║    ./claude-memory-observe.py --memory-dir <path>                                        ║
║    CLAUDE_MEMORY_DIR=<path> ./claude-memory-observe.py                                   ║
║                                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
→ Pick:
```

## 📺 Main menu

```
╔════════════════════════════════════════════════════════════════════╗
║                       Claude Memory Observer                       ║
║             -Users-me-code-myproject  ·  46 entries                ║
╠════════════════════════════════════════════════════════════════════╣
║  READ                                                              ║
║     [1]  List all (grouped by type)                                ║
║     [2]  View entry                                                ║
║     [3]  Search                                                    ║
║                                                                    ║
║  MODIFY                                                            ║
║     [4]  Add new entry                                             ║
║     [5]  Edit entry                                                ║
║     [6]  Delete entry                                              ║
║                                                                    ║
║  MAINTAIN                                                          ║
║     [7]  Rebuild MEMORY.md                                         ║
║     [8]  Stats / index sanity                                      ║
║                                                                    ║
║  DANGER ZONE                                                       ║
║     [w]  Wipe memory (-Users-me-code-myproject)                    ║
║     [n]  Nuke ALL Claude memory (every project, system-wide)       ║
║                                                                    ║
║     [q]  Quit                                                      ║
╚════════════════════════════════════════════════════════════════════╝
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
- **"Wipe" is _very_ destructive — but scoped to one project.** It deletes
  every entry **in the currently-selected memory dir only**. Other projects'
  memory dirs (anything else under `~/.claude/projects/`) are untouched.
  The menu label spells out which dir will be wiped, e.g.
  `[w]  Wipe memory (-Users-me-code-myproject)`. To prevent accidental
  triggering, the command then asks you to type the project key exactly
  — a y/N prompt would be too easy. By default it offers to move the
  existing memory dir to a timestamped backup
  (`memory.bak.<YYYYMMDD-HHMMSS>/`) before recreating an empty one.
- **"Nuke" is the maximum-blast option.** It wipes memory across **every
  Claude Code project** on this machine, leaving you with a 'fresh Claude'
  state for memory specifically. To confirm you must type the literal
  phrase `NUKE ALL` — no project-key shortcut, since the operation isn't
  scoped to one project. By default each project's `memory/` dir is moved
  aside to `memory.bak.<YYYYMMDD-HHMMSS>/` before being recreated empty,
  so a recovery is one `mv` away. Other Claude Code state under
  `~/.claude/` (settings, conversation history, caches) is untouched.
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

[MIT](LICENSE) © chatthong
