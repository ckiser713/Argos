# Cursor SSH Workspace Best Practices

Guidelines for writing `.cursor/rules` (or similar guardrails) when operating this repo over SSH with Cursor. The aim is to keep the workspace safe, predictable, and low-latency.

## Baseline rules to include in `.cursor/rules`
- Stay scoped to `/home/nexus/Argos_Chatgpt` unless explicitly told otherwise; do not touch `/etc`, `/var`, or other home directories.
- Never run `sudo`, `systemctl`, `shutdown/reboot`, `chown`, or `chmod -R` without written approval.
- Never run destructive deletes (`rm -rf /`, `rm -rf ~`, `rm -rf /home/nexus/Argos_Chatgpt`). For deletions, keep them targeted and confirm anything affecting large sets of files.
- Protect git state: no `git reset --hard`, `git clean -fd`, or force pushes; do not auto-switch branches or stash without approval.
- Use absolute paths in tool/command calls; note the current working directory before running commands that depend on it.
- Prefer `read_file`/`rg` over `cat` for large files; if a log is big, sample with `head -n 200`/`tail -n 200` instead of reading the whole file.
- Use `apply_patch` for single-file edits; avoid blanket search/replace across the repo unless explicitly requested.
- Keep long-running commands in the background (`is_background: true`) and state that they are running; avoid `watch`/infinite loops that hold the SSH session.
- Do not touch secrets, `.env` files, kube/cloud configs, or credential stores without explicit approval; if encountered unexpectedly, stop and ask.

## SSH-specific operational tips
- Be mindful of resource usage (CPU/GPU/disk); call out when a command may be heavy and prefer dry-runs (`--dry-run`, `--check`, `--diff`) first.
- Avoid spawning extra daemons or ports; clean up background jobs you start.
- Keep terminal output small to reduce latency; prefer concise commands and filtered output.
- If you need temporary files, place them under `/home/nexus/Argos_Chatgpt/tmp` (create if needed) and delete them when finished.

## Suggested `.cursor/rules` block (copy/paste)
- Operate only under `/home/nexus/Argos_Chatgpt` unless instructed otherwise.
- Do not run `sudo`, `systemctl`, `shutdown`, `reboot`, `chown`, or `chmod -R`.
- Do not run `rm -rf /`, `rm -rf ~`, or bulk deletes; ask before removing more than a handful of files.
- Do not use `git reset --hard`, `git clean -fd`, or force pushes without explicit approval; avoid switching branches automatically.
- Use absolute paths; background long commands and announce them; avoid `watch` loops.
- Prefer `read_file`/`rg`; for large logs, sample with `head`/`tail` instead of full reads.
- Use `apply_patch` for targeted edits; avoid repo-wide search/replace unless requested.
- Stop and ask if a command touches secrets, env files, or unfamiliar system paths.

