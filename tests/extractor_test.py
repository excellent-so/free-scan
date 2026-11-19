#!/usr/bin/env python3
# Checks the prompt's extractor: it must copy scan.py byte for byte out of a Claude Code log and a Codex log that hold
# the pasted prompt, and the copy must match the hash the prompt states. Writes only under tests/tmp (deleted after).
import hashlib, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(HERE, "..", "PROMPT.md"), encoding="utf-8").read()
prompt = md.split("````text\n", 1)[1].rsplit("````", 1)[0]
want = hashlib.sha256(open(os.path.join(HERE, "..", "scan.py"), "rb").read()).hexdigest()
assert want in prompt, "the prompt states a different hash than scan.py has"
ext = re.search(r"python3 - <<'EOF'\n.*?\nEOF", prompt, re.S).group(0)
records = {
    "claude": (".claude/projects/-Users-x-proj/s.jsonl", {"type": "user", "message": {"role": "user", "content": prompt}}),
    "codex": (".codex/sessions/2026/11/18/rollout-x.jsonl", {"timestamp": "2026-11-18T15:00:01Z", "type": "response_item",
              "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}}),
}
ok = True
for agent, (rel, rec) in records.items():
    home = os.path.join(HERE, "tmp", agent)
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(os.path.dirname(os.path.join(home, rel)))
    with open(os.path.join(home, rel), "w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
        # the agent's own call that runs the extractor (it must not be mistaken for the script)
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": ext}}]}}) + "\n")
    out = subprocess.run(["bash", "-c", ext], env=dict(os.environ, HOME=home), capture_output=True, text=True).stdout.strip()
    got = hashlib.sha256(open(os.path.join(home, "excellent-free-scan", "scan.py"), "rb").read()).hexdigest() if out == "saved" else out
    print(agent, out, "hash ok" if got == want else "HASH MISMATCH")
    ok &= got == want
shutil.rmtree(os.path.join(HERE, "tmp"), ignore_errors=True)
sys.exit(0 if ok else 1)
