# Excellent free scan

The free scan is a read-only check of what your AI coding agents did on your Mac, read from their own logs. It
covers Claude Code, Codex and Grok Build. You paste one prompt into Claude Code or Codex. Your agent saves a Python
script, checks its SHA-256, tells you what it does and runs it. The script writes one report on your Mac,
`~/excellent-free-scan/report.html`, and prints a short summary for your agent to show you.

This repository holds the script and the prompt, so you can read both before you paste anything.

- `scan.py`: the script. Python 3.9 or later, standard library only.
- `PROMPT.md`: the prompt. It holds `scan.py` unchanged, its SHA-256 and a short extractor.
- `build_prompt.py`: builds `PROMPT.md` from `scan.py`.
- `SHA256SUMS`: the SHA-256 of `scan.py` and `PROMPT.md`.
- `tests/`: tests that run in a fake home folder.

## Run it

1. Copy the prompt: the text in the box in `PROMPT.md`, or use the Copy button at
   [excellent.so/#scan](https://excellent.so/#scan). Both give the same prompt.
2. Paste it into Claude Code or Codex, started in any folder.

The prompt asks your agent to save the script to `~/excellent-free-scan/scan.py`, check its SHA-256 and stop if it
doesn't match, tell you in three bullets what the script reads, writes and whether it uses the network, run it, open
the report, and show you what the script printed. It also tells the agent not to read your logs, your keys or the
report itself, not to change the script, install anything or use the network, and to write every path with `~`. The
steps and the extractor sit above the script in the prompt. Read them before you paste.

A scan usually takes a few seconds, or a few minutes if you have many GB of logs. If `python3` is missing, run
`xcode-select --install`.

You can also run the script yourself in Terminal, with no agent and no chat:

```
python3 scan.py
python3 scan.py --email you@example.com   # also look for this address
```

## What it checks

The same rules as the Excellent app, simplified:

- your email sent to websites, for example as the contact in a User-Agent header;
- your email typed into web forms;
- API keys sitting in your agent logs (11 kinds, by their known shape);
- agents opening keys and secrets files: `.env` files, SSH keys, your keychain;
- force pushes;
- skipped safety checks: `--no-verify`, or moved git hooks;
- deletes of folders you marked never-delete, or of files in folders like `~/.ssh`;
- publishes and deploys;
- breaks of the never-open and never-run rules you wrote, in sessions that had that rule (when a log doesn't record
  its rules, the rules of the folder the session started in);
- hooks that fail silently because their program is gone.

## What it reads

- Agent logs in `~/.claude/projects`, `~/.codex/sessions`, `~/.codex/archived_sessions` and `~/.grok/sessions`.
- Your instruction files, for the rules it checks: `CLAUDE.md`, `AGENTS.md`, `CLAUDE.local.md`, `AGENTS.override.md`,
  `.claude/CLAUDE.md` and `.claude/rules` in the folder each session started in and the folders above it, up to your
  home folder; plus `~/.claude/CLAUDE.md`, `~/.claude/rules`, `~/.codex/AGENTS.md` and `~/.codex/AGENTS.override.md`.
- Hook settings in `~/.claude/settings.json` and `~/.codex/hooks.json`. It checks that each hook's program still exists.
- Your email, so it knows what to look for: from `~/.claude.json` and `git config --global user.email`.

It never opens Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos
data or app containers in Library, other drives, or a folder your rules name (in backticks) as never to open or read,
once it has read that rule.

## What it writes

One file: `~/excellent-free-scan/report.html`. The script is saved next to it, as `~/excellent-free-scan/scan.py`,
by the prompt's extractor or by your agent. To delete both: `rm -r ~/excellent-free-scan`.

The report masks emails and keys in its examples. It loads nothing: its Content-Security-Policy is
`default-src 'none'`. The share card at the top holds only counts, agent names and dates. The rest of the page is for
you, and it names sites, projects and log files. The page has two links to excellent.so; the share card's link
carries `utm_` tags.

## What it sends

The script makes no network connections and sends nothing anywhere. It prints only a short summary: counts, agent
names, dates, log size and where the report is, as a `~/` path. It never prints a key, an email, log text or your
account name.

Your agent sees that summary, and the output of the prompt's other steps: the extractor prints "saved" and the hash
check prints the hash. That goes to your agent's provider as part of your normal conversation with it, as the prompt
itself does, script included.

This is what the script printed in the tests' fake home:

```
Read 3 sessions (0.0 GB of logs) in 0 seconds. Your email: found (checked, not shown).
Report: ~/excellent-free-scan/report.html

Excellent free scan · Claude Code + Codex + Grok Build · Nov 10 – Nov 16 · 8 actions
  Your email was sent to websites                1
  Your email was typed into web forms            0
  API keys are sitting in your agent logs        2
  Agents opened keys and secrets files           1
  Agents force-pushed                            2
  Safety checks were skipped                     1
  Never-delete folders were touched              1
  Things were published or deployed              0
  Your own rules were broken                     1
  Your hooks fail silently                       1
Run yours free: excellent.so/scan
```

## Check the hashes

```
shasum -a 256 -c SHA256SUMS
```

The SHA-256 of `scan.py` is `9d60d631193cb0e796e4066d8fc4f2752c0e93c373a2919695eb2fe21c44810f`. The prompt states the
same value and has your agent check the saved script against it. excellent.so/#scan shows the same value. `SHA256SUMS`
also lists `PROMPT.md`: that is the hash of the whole file, not only the text you paste.

## How the prompt is built

`build_prompt.py` reads `scan.py`, takes its SHA-256 and writes `PROMPT.md`: a short preamble, then the prompt in a
box. The prompt holds the steps, with the hash in step 2, then the extractor, then `scan.py` unchanged between the
lines `# EXCELLENT-FREE-SCAN-BEGIN` and `# EXCELLENT-FREE-SCAN-END`.

The extractor saves your agent from retyping about 60 KB. It looks through your 20 most recently changed Claude Code
and Codex logs for the pasted prompt, copies the script between those two lines to `~/excellent-free-scan/scan.py`,
and prints only "saved", "not found" or the name of an error. If it can't, your agent writes the file itself. Either
way, step 2 checks the hash.

To check that `PROMPT.md` comes from this `scan.py`, rebuild it and compare:

```
python3 build_prompt.py
shasum -a 256 -c SHA256SUMS
git diff --exit-code PROMPT.md && echo "PROMPT.md is unchanged"
```

## Tests

```
python3 tests/extractor_test.py
python3 tests/home_test.py
python3 tests/plural_test.py
```

`extractor_test.py` checks that the extractor copies `scan.py` byte for byte out of a Claude Code log and a Codex log
that hold the prompt. `plural_test.py` builds a report in memory with every count at 1 and checks that each count
reads as one ("1 session", "1 of 10 checks needs a look"). It reads no logs. `home_test.py` runs the scan and the prompt's steps in a fake home folder with made-up logs,
rules, hooks, keys and email. It checks that the account name and the email show nowhere in what they print or in the
report, and that the share card and the printed summary hold only agent names, counts and dates. `home_test.py` and
`extractor_test.py` set `HOME` to a temporary folder and delete it afterwards.

## Limits

Logs go back only as far as your agents keep them (Claude Code: 30 days unless you change it). Keys count only when
they have a known shape; test and example keys are left out. The rules are the Excellent app's, simplified, so counts
can differ a little from the app's.

## Excellent

The free scan is made by [Excellent](https://excellent.so). [Excellent for Mac](https://excellent.so/download), an app
for Macs with Apple silicon and macOS 14 or later, runs these checks too, and scanning with it is free.

Help: help@excellent.so

© 2026 Excellent Software, LLC
