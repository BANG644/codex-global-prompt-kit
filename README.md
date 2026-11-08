# Codex Global Prompt Kit

This repository packages the active global Codex instructions from one machine for a deliberate, user-level copy to another machine. It contains byte-for-byte copies of `AGENTS.md` and its `RTK.md` companion, eight related skills, and a pinned installation recipe for the Ponytail plugin. For privacy, the plain-language reporting guide uses generic illustrative examples instead of filenames or empirical results from its source materials.

## Contents

- `payload/global/AGENTS.md` and `payload/global/RTK.md`: byte-for-byte copies of the source global instruction files.
- `payload/skills/`: the eight selected skill folders, including their required helper files and HTML examples. The `review-ready-report` plain-language guide retains the reusable writing methods but uses clearly labeled generic examples.
- `MANIFEST.json` and `payload.sha256`: scope, upstream plugin pin, and SHA-256 integrity list for every installed payload file.
- `install.py`: cross-platform installer with preflight checks and local backups.
- `PROMPT.md`: the single prompt intended for sharing with another Codex user.
- `NOTICE.md`: source and license notes for bundled or remotely installed materials.

The kit does not contain the machine's full `config.toml`, MCP connection definitions, account state, API keys, personal skills outside this allowlist, or local application data. It pins the user-installed Ponytail plugin; Codex bundled and runtime plugins come from the recipient's own Codex installation and are not copied from this machine.

Git line-ending conversion is disabled for this repository so each checked payload keeps the exact bytes covered by its checksum on Windows, macOS, and Linux.

## Installation

The installer requires Python 3.10 or newer, Git, and a Codex CLI that supports `codex plugin marketplace` and `codex plugin add`. It checks these dependencies before making changes.

```sh
# Windows PowerShell
py -3 install.py --check
py -3 install.py --apply

# macOS / Linux
python3 install.py --check
python3 install.py --apply
```

Use whichever available Python launcher points to Python 3.10 or newer (`py -3`, `python3`, or `python`). `--apply` asks before writing. `--yes` skips that confirmation only after the user has authorized installation. Before replacing a same-named prompt file or skill, the installer preserves the old item under `CODEX_HOME/global-config-kit-backups/<timestamp>/`. It backs up `config.toml` locally only if the native plugin command needs to modify it. No backup is uploaded.

Global instructions go to `${CODEX_HOME:-~/.codex}/AGENTS.md` and `RTK.md`. Skills go to the official user-level location `~/.agents/skills`. If a selected skill already exists under `CODEX_HOME/skills`, that copy is preserved in the local backup and moved to the canonical user-level location to avoid loading two copies.

Ponytail is installed through Codex's native marketplace command from the exact upstream commit recorded in `MANIFEST.json`. If a different marketplace or version already occupies the name `ponytail`, the installer stops and reports the conflict rather than removing or replacing it silently.

After installing, restart Codex if the new instructions, skills, or plugin are not visible in the current session. The installer reports configured files and registered plugin state separately; successful file copies do not prove that a running Desktop session has reloaded them.

## Capabilities That Need Local Setup

- `ai-image-generation` scripts use Python's standard library and need one supported provider API key when actually generating images. The key must remain in the recipient's local environment or private project secret file.
- RTK and CodeGraph are optional external tools. Their absence does not block this kit; the global instructions describe when native commands or the CLI fallback can be used.
- Skills that use Goal automation or desktop automation can only use capabilities actually exposed by that Codex runtime. The skill files remain installed even when a particular runtime lacks those capabilities.

## Integrity

Run `python install.py --check` to compare every payload file with `payload.sha256`, verify the allowlist, check installation prerequisites, and report Ponytail's registered version and pinned marketplace commit. The SHA-256 list catches accidental changes or incomplete downloads; it is not a signature against a malicious change to this public repository.
