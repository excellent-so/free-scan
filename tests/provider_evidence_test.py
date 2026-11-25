#!/usr/bin/env python3
"""Check the published local report with an inert path-only tool call and no key value."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
prompt = (ROOT / "PROMPT.md").read_text()
script = re.search(r"# EXCELLENT-FREE-SCAN-BEGIN\n(#!/usr/bin/env python3\n.*?\n)# EXCELLENT-FREE-SCAN-END", prompt, re.S)[1]
assert script.encode() == (ROOT / "scan.py").read_bytes()
with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp)
    saved = home / "scan.py"
    saved.write_text(script)
    logs = home / ".claude/projects/sample"
    logs.mkdir(parents=True)
    path = str(home / "sample/.env")
    call = {"type": "assistant", "timestamp": "2026-11-20T10:00:00Z", "cwd": str(home / "sample"),
            "message": {"content": [{"type": "tool_use", "id": "sample-call", "name": "Read", "input": {"file_path": path}}]}}
    (logs / "fixture.jsonl").write_text(json.dumps(call, separators=(",", ":")) + "\n")
    env = dict(os.environ, HOME=tmp, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run([sys.executable, str(saved)], cwd=home, env=env, capture_output=True, check=True)
    report = (home / "excellent-free-scan/report.html").read_text()
    assert "A recorded tool call named a .env file" in report
    assert "A matching key value in a transcript is a separate finding." in report
    assert "what they read goes to the model provider" not in report
    card = json.loads(re.search(r'<script type="application/json" id="card-data">(.*?)</script>', report, re.S)[1])
    assert [t["n"] for t in card["tiles"] if t["n"]] == [1]
    assert "action on .env" in card["tiles"][0]["label"]
print("path-only tool input produced one file action, with no claim of key content or provider receipt")
