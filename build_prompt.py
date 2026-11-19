#!/usr/bin/env python3
# Builds PROMPT.md from scan.py, so the pasted script, its hash and the prompt always agree. Usage: python3 build_prompt.py
import hashlib, os

HERE = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(HERE, "scan.py"), encoding="utf-8").read()
digest = hashlib.sha256(script.encode("utf-8")).hexdigest()

EXTRACTOR = r'''python3 - <<'EOF'
import glob, json, os, re
H = os.path.expanduser("~")
rx = re.compile(r"# EXCELLENT-FREE-SCAN-BEGIN\r?\n(#!/usr/bin/env python3\r?\n.*?\n)# EXCELLENT-FREE-SCAN-END", re.S)
def texts(o):
    if isinstance(o, str): yield o
    for v in (o.values() if isinstance(o, dict) else o if isinstance(o, list) else []): yield from texts(v)
logs = glob.glob(H + "/.claude/projects/*/*.jsonl") + glob.glob(H + "/.codex/sessions/*/*/*/*.jsonl")
try:
    for f in sorted(logs, key=os.path.getmtime)[::-1][:20]:
        for line in open(f, encoding="utf-8", errors="replace"):
            if "EXCELLENT-FREE-SCAN-BEGIN" in line and line.startswith("{") and line.rstrip().endswith("}"):
                for m in filter(None, map(rx.search, texts(json.loads(line)))):
                    os.makedirs(H + "/excellent-free-scan", exist_ok=True)
                    open(H + "/excellent-free-scan/scan.py", "w", encoding="utf-8").write(m.group(1).replace("\r\n", "\n"))
                    print("saved")
                    raise SystemExit
    print("not found")
except Exception as x:  # its name only: the message would show your home folder
    print("not saved:", type(x).__name__)
EOF'''

PROMPT = f"""Please run the Excellent free scan for me: a read-only check of what my AI coding agents (Claude Code, Codex, Grok Build) did on this Mac, read from their own logs. The Python script at the end of this message does all the reading and prints only a short summary (counts, agent names, dates, log size and where the report is, as a ~/ path), never a key, email or log text, so nothing private comes into this chat.

Steps:
1. Save the script. Run the extractor below as it is. It copies the script between the two EXCELLENT-FREE-SCAN lines from this conversation's own log into ~/excellent-free-scan/scan.py. If it prints anything other than "saved", create that file yourself with the script text, exactly as written.
2. Check it. Run `shasum -a 256 ~/excellent-free-scan/scan.py 2>/dev/null | cut -c1-64`. It must print {digest}. If it doesn't, stop and tell me.
3. In three short bullets, tell me what the script reads, what it writes, and whether it uses the network. You already have its text in this message, so you don't need to print the file.
4. Run it: `python3 ~/excellent-free-scan/scan.py` (usually a few seconds; a few minutes if you have many GB of logs).
5. Open the report: `open ~/excellent-free-scan/report.html 2>/dev/null || echo "not opened"`. If it prints "not opened", tell me the report is at ~/excellent-free-scan/report.html.
6. Reply with everything the script printed, in a code block exactly as printed, and nothing else from my files.

While you do this:
- Don't read, search or summarize my agent logs, keys or the report yourself. The script does the reading.
- Don't change the script, install anything or use the network.
- Write every path with ~, as in ~/excellent-free-scan/report.html, never as a full /Users/… path, so my account name stays out of this chat.
- If python3 is missing, stop and tell me to run `xcode-select --install`.

Extractor:
{EXTRACTOR}

# EXCELLENT-FREE-SCAN-BEGIN
{script}# EXCELLENT-FREE-SCAN-END
"""

DOC = f"""# Excellent free scan: the paste-in prompt

Paste everything in the box below into Claude Code or Codex, started in any folder. It runs a read-only check of the
user's own agent logs and opens a local report (`~/excellent-free-scan/report.html`).

- Script: `scan.py` in this folder, {len(script.encode()):,} bytes, Python 3.9+ standard library only.
- SHA-256 of the script: `{digest}`. The same hash is listed at excellent.so/scan and in the excellent-so/free-scan
  repo, so you can check your copy.
- The extractor copies the script out of the conversation's own log, so the agent doesn't have to retype 60 KB
  (about 17,000 output tokens and three to five minutes). If it can't, the agent writes the file itself.
- Rebuild this file after any change to `scan.py`: `python3 build_prompt.py`.

Copy from the line after the opening fence to the line before the closing fence.

````text
{PROMPT}````
"""

open(os.path.join(HERE, "PROMPT.md"), "w", encoding="utf-8").write(DOC)
print("PROMPT.md written;", digest)
