# Excellent free scan

The free scan is a read-only check of what your AI agents did on your Mac, read from their own logs. It
covers Claude Code, Codex and Grok Build. You paste one prompt into Claude Code or Codex. Your agent saves a Python
script, checks its SHA-256, tells you what it does and runs it. The script writes one report on your Mac,
`~/excellent-free-scan/report.html`, and prints a short summary for your agent to show you.

This repository holds the script and the prompt, so you can read both before you paste anything.

- `scan.py`: the script. Python 3.9 or later, standard library only.
- `PROMPT.md`: the prompt. It holds `scan.py` unchanged, its SHA-256 and a short extractor.
- `build_prompt.py`: builds `PROMPT.md` from `scan.py`.
- `share-format.json`: the share link's format (v1), with worked examples; `build_share_format.py` regenerates it.
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

- your address in request commands or local script inputs, including a User-Agent header;
- your address in form or request inputs;
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

The report masks emails and keys in its examples. It loads nothing from the network: its Content-Security-Policy is
`default-src 'none'`, plus one inline script allowed by its SHA-256 and `blob:` images and video. That script draws the
share card for Save video and Save image, on your Mac. The share card at the top holds only counts, agent names and
dates. The rest of the page is for you, and it names sites, projects and log files.

The report follows Excellent for Mac's look. It ranks what it found in three tiers: Fix now, Review and Good to know.
Each finding says what happened, what you can do yourself, and what Excellent for Mac does about it, with a Download
Excellent link.

The report page loads locally. Its share buttons work as follows. Save video and Save image save the card as a file; Copy
share link copies an excellent.so/r link that carries only the card's numbers and which agents ran; Post on X opens
x.com with the card's lines and that link. The page also links to excellent.so/scan ("Run yours free") and to "Get
Excellent for Mac". The excellent.so links carry `utm_` tags.

## What it sends

The script makes no network connections and sends nothing anywhere. It prints only a short summary: counts, agent
names, dates, log size and where the report is, as a `~/` path. It never prints a key, an email, log text or your
account name.

When you use the prompt in an agent, the summary and the verification output appear in that conversation. A hosted agent can send those outputs and the prompt (including the script) to its provider. Running the script directly in Terminal prints the summary there.

This is what the script printed in the tests' fake home:

```
Read 3 sessions (0.0 GB of logs) in 0 seconds. Your email: found (checked, not shown).
Report: ~/excellent-free-scan/report.html

Excellent free scan · Claude Code + Codex + Grok Build · Nov 10 – Nov 16 · 8 actions
5 to fix now · 2 to review · 1 good to know
  Your email in request commands or scripts                1
  Your email in form or request inputs            0
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

The SHA-256 of `scan.py` is `a90f663d2fcbb70dfa64464f84eb9d4a0d6570229e6b5f677f5210d4595b301a`. The prompt states the
same value and has your agent check the saved script against it. excellent.so/scan shows the same value. `SHA256SUMS`
also lists `PROMPT.md`: that is the hash of the whole file, not only the text you paste.

## How the prompt is built

`build_prompt.py` reads `scan.py`, takes its SHA-256 and writes `PROMPT.md`: a short preamble, then the prompt in a
box. The prompt holds the steps, with the hash in step 2, then the extractor, then `scan.py` unchanged between the
lines `# EXCELLENT-FREE-SCAN-BEGIN` and `# EXCELLENT-FREE-SCAN-END`.

The extractor saves your agent from retyping about 78 KB. It looks through your 20 most recently changed Claude Code
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

The email checks report local script input, unknown result, tool-reported failure, block and tool-reported success. Agent logs alone cannot confirm receipt by a website. Run `python3 tests/email_evidence_test.py` for the synthetic Claude Code and Codex cases, including report, summary and share counts. The test parses inert records in an isolated home.
