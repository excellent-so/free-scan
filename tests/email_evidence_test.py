#!/usr/bin/env python3
"""Run the released Python entry point against inert native records. No fixture command is executed."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit
import zlib

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
LABELS = ("local script input", "result unknown", "tool reported failure", "blocked", "tool reported success")
agents = {
    "claude-code": (".claude/projects/fixture", [1, 3, 2, 1, 1], [0, 3, 2, 1, 1]),
    "codex": (".codex/sessions/2026/11/22", [0, 4, 1, 1, 1], [0, 4, 1, 1, 1]),
}


def verify(script, agent, spec):
    folder, requests, forms = spec
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        logs = home / folder
        logs.mkdir(parents=True)
        fixture = (FIXTURES / ("email-evidence-" + agent + ".jsonl")).read_bytes()
        (logs / "fixture.jsonl").write_bytes(fixture)
        env = dict(os.environ, HOME=tmp, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, str(script), "--email", "synthetic-review@example.com"],
                                cwd=home, env=env, check=True, capture_output=True, text=True)
        page = (home / "excellent-free-scan/report.html").read_text()
        x_text = unquote(html.unescape(re.search(r'href="https://x.com/intent/post\?text=([^"]+)"', page)[1]))
        card_html = re.search(r'<section class="score" id="card">(.*?)</section>', page, re.S)[1]
        card = json.loads(re.search(r'<script type="application/json" id="card-data">(.*?)</script>', page, re.S)[1])
        for index, counts in enumerate((requests, forms)):
            detail = ", ".join("%s %s" % (n, label) for n, label in zip(counts, LABELS) if n)
            assert detail in result.stdout and detail in html.unescape(page), (agent, detail, result.stdout)
            assert detail in card["evidence"][index] and detail in html.unescape(card_html) and detail in x_text
        query = urlsplit(card["links"]["copy"]).query
        params = parse_qs(query)
        assert params["e"] == [".".join(str(n) for n in requests + forms)]
        assert [int(x) for x in params["k"][0].split(".")[:2]] == [sum(requests), sum(forms)]
        code = int(params["c"][0], 36)
        assert code == zlib.crc32(query.split("&c=", 1)[0].encode()) % 36**4
        assert "synthetic-review@example.com" not in page + result.stdout
        assert "Your email was sent" not in page + result.stdout
        assert "do not establish receipt" in page
        assert (logs / "fixture.jsonl").read_bytes() == fixture


def verify_silent_result(script):
    # Anthropic permits empty content; a matching explicit is_error=false is a tool-reported success.
    fixture = [json.loads(line) for line in (FIXTURES / "email-evidence-claude-code.jsonl").read_text().splitlines()]
    call = next(r for r in fixture if r["type"] == "assistant" and r["message"]["content"][0]["id"] == "request-unrecognized_result")
    result = next(r for r in fixture if r["type"] == "user" and isinstance(r["message"]["content"], list)
                  and r["message"]["content"][0].get("tool_use_id") == "request-unrecognized_result")
    for flagged, expected in [(False, "1 result unknown"), (True, "1 tool reported success")]:
        if flagged:
            result["message"]["content"][0]["is_error"] = False
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            log = home / ".claude/projects/fixture/silent.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in (call, result)))
            env = dict(os.environ, HOME=tmp, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
            observed = subprocess.check_output([sys.executable, str(script), "--email", "synthetic-review@example.com"],
                                               cwd=home, env=env, text=True)
            assert expected in observed, observed


if __name__ == "__main__":
    prompt = (ROOT / "PROMPT.md").read_text()
    embedded = re.search(r"# EXCELLENT-FREE-SCAN-BEGIN\n(#!/usr/bin/env python3\n.*?\n)# EXCELLENT-FREE-SCAN-END", prompt, re.S)[1]
    assert embedded.encode() == (ROOT / "scan.py").read_bytes()
    digest = hashlib.sha256(embedded.encode()).hexdigest()
    assert digest in prompt and digest + "  scan.py" in (ROOT / "SHA256SUMS").read_text()
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "scan.py"
        script.write_text(embedded)
        for agent, spec in agents.items():
            verify(script, agent, spec)
            print(agent + " native fixtures passed")
        verify_silent_result(script)
        print("silent matched result with and without explicit status passed")
