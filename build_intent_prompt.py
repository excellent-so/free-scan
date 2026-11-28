#!/usr/bin/env python3
# Builds INTENT-PROMPT.md from intent_scan.py, as build_prompt.py builds PROMPT.md from scan.py, so the pasted script, its
# hash and the prompt always agree. Usage: python3 build_intent_prompt.py
import hashlib, os

HERE = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(HERE, "intent_scan.py"), encoding="utf-8").read()
digest = hashlib.sha256(script.encode("utf-8")).hexdigest()

EXTRACTOR = r'''python3 - <<'EOF'
import glob, json, os, re
H = os.path.expanduser("~")
rx = re.compile(r"# EXCELLENT-FREE-INTENT-SCAN-BEGIN\r?\n(#!/usr/bin/env python3\r?\n.*?\n)# EXCELLENT-FREE-INTENT-SCAN-END", re.S)
def texts(o):
    if isinstance(o, str): yield o
    for v in (o.values() if isinstance(o, dict) else o if isinstance(o, list) else []): yield from texts(v)
logs = glob.glob(H + "/.claude/projects/*/*.jsonl") + glob.glob(H + "/.codex/sessions/*/*/*/*.jsonl")
try:
    for f in sorted(logs, key=os.path.getmtime)[::-1][:20]:
        for line in open(f, encoding="utf-8", errors="replace"):
            if "EXCELLENT-FREE-INTENT-SCAN-BEGIN" in line and line.startswith("{") and line.rstrip().endswith("}"):
                for m in filter(None, map(rx.search, texts(json.loads(line)))):
                    os.makedirs(H + "/excellent-free-scan", exist_ok=True)
                    open(H + "/excellent-free-scan/intent_scan.py", "w", encoding="utf-8").write(m.group(1).replace("\r\n", "\n"))
                    print("saved")
                    raise SystemExit
    print("not found")
except Exception as x:  # its name only: the message would show your home folder
    print("not saved:", type(x).__name__)
EOF'''

PROMPT = f"""Please run the Excellent free Intent scan for me: a read-only check of whether my AI coding agents (Claude Code with its sub-agents, Codex, Grok Build) reported what they did on this Mac, read from their own logs. The Python script at the end of this message does all the reading and prints only a short summary (counts, agent names, dates, log size and where the report is, as a ~/ path), never a key, email or log text, so nothing private comes into this chat.

Steps:
1. Save the script. Run the extractor below as it is. It copies the script between the two EXCELLENT-FREE-INTENT-SCAN lines from this conversation's own log into ~/excellent-free-scan/intent_scan.py. If it prints anything other than "saved", create that file yourself with the script text, exactly as written.
2. Check it. Run `shasum -a 256 ~/excellent-free-scan/intent_scan.py 2>/dev/null | cut -c1-64`. It must print {digest}. If it doesn't, stop and tell me.
3. In three short bullets, tell me what the script reads, what it writes, and whether it uses the network. You already have its text in this message, so you don't need to print the file.
4. Run it: `python3 ~/excellent-free-scan/intent_scan.py` (usually a few seconds; a few minutes if you have many GB of logs).
5. Open the report: `open ~/excellent-free-scan/intent-report.html 2>/dev/null || echo "not opened"`. If it prints "not opened", tell me the report is at ~/excellent-free-scan/intent-report.html.
6. Reply with everything the script printed, in a code block exactly as printed, and nothing else from my files.

While you do this:
- Don't read, search or summarize my agent logs, keys or the report yourself. The script does the reading.
- Don't change the script, install anything or use the network.
- Write every path with ~, as in ~/excellent-free-scan/intent-report.html, never as a full /Users/… path, so my account name stays out of this chat.
- If python3 is missing, stop and tell me to run `xcode-select --install`.

Extractor:
{EXTRACTOR}

# EXCELLENT-FREE-INTENT-SCAN-BEGIN
{script}# EXCELLENT-FREE-INTENT-SCAN-END
"""

DOC = f"""# Excellent free Intent scan: the paste-in prompt

Paste everything in the box below into Claude Code or Codex, started in any folder. It runs a read-only check of the
user's own agent logs and opens a local report (`~/excellent-free-scan/intent-report.html`).

- Script: `intent_scan.py` in this folder, {len(script.encode()):,} bytes, Python 3.9+ standard library only.
- SHA-256 of the script: `{digest}`. The same hash is listed in this repository's `SHA256SUMS`, so you can check your
  copy.
- The extractor copies the script out of the conversation's own log, so the agent doesn't have to retype
  {len(script.encode()) // 1000} KB (about {round(len(script.encode()) / 3.4, -3):,.0f} output tokens and three to six minutes). If it can't, the agent
  writes the file itself.
- Rebuild this file after any change to `intent_scan.py`: `python3 build_intent_prompt.py`.

Copy from the line after the opening fence to the line before the closing fence.

````text
{PROMPT}````
"""

open(os.path.join(HERE, "INTENT-PROMPT.md"), "w", encoding="utf-8").write(DOC)
print("INTENT-PROMPT.md written;", digest)
