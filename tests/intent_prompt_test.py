#!/usr/bin/env python3
# Checks INTENT-PROMPT.md: it holds intent_scan.py unchanged, states its hash (as SHA256SUMS does), is up to date with
# build_intent_prompt.py, and its extractor copies the script byte for byte out of a Claude Code log and a Codex log that
# hold the pasted prompt, even when the free scan's prompt sits in the same log. Then runs the prompt's own steps (save,
# hash, run) in a fake home and checks they print no path and no account name. Writes only under a temp folder.
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    ok or fails.append(what)


md = open(os.path.join(ROOT, "INTENT-PROMPT.md"), encoding="utf-8").read()
prompt = md.split("````text\n", 1)[1].rsplit("````", 1)[0]
script = open(os.path.join(ROOT, "intent_scan.py"), "rb").read()
want = hashlib.sha256(script).hexdigest()
sums = open(os.path.join(ROOT, "SHA256SUMS"), encoding="utf-8").read()
check(want in prompt and want + "  intent_scan.py" in sums, "prompt and SHA256SUMS state intent_scan.py's hash")
check(hashlib.sha256(md.encode()).hexdigest() + "  INTENT-PROMPT.md" in sums, "SHA256SUMS lists INTENT-PROMPT.md's hash")
check(sums.startswith("913ca0407d7e7b0d7e38707a8c438b8d50383430a95f7e09632edf0018984cb7  scan.py\n"), "the free scan's line in SHA256SUMS is unchanged")
embedded = re.search(r"# EXCELLENT-FREE-INTENT-SCAN-BEGIN\n(#!/usr/bin/env python3\n.*?\n)# EXCELLENT-FREE-INTENT-SCAN-END", prompt, re.S)
check(embedded is not None and embedded.group(1).encode() == script, "the prompt holds intent_scan.py unchanged")
check(not re.search(r"/Users/(?!…)", prompt.split("# EXCELLENT-FREE-INTENT-SCAN-BEGIN")[0]), "prompt text asks for no /Users/ path")
tmp = tempfile.mkdtemp(prefix="free-intent-prompt-")
try:  # the builder writes the same file
    shutil.copy(os.path.join(ROOT, "build_intent_prompt.py"), tmp)
    shutil.copy(os.path.join(ROOT, "intent_scan.py"), tmp)
    subprocess.run([sys.executable, os.path.join(tmp, "build_intent_prompt.py")], capture_output=True, check=True)
    check(open(os.path.join(tmp, "INTENT-PROMPT.md"), encoding="utf-8").read() == md, "INTENT-PROMPT.md is up to date (python3 build_intent_prompt.py)")
    ext = re.search(r"python3 - <<'EOF'\n.*?\nEOF", prompt, re.S).group(0)
    free = open(os.path.join(ROOT, "PROMPT.md"), encoding="utf-8").read().split("````text\n", 1)[1].rsplit("````", 1)[0]
    free_ext = re.search(r"python3 - <<'EOF'\n.*?\nEOF", free, re.S).group(0)
    records = {
        "claude": (".claude/projects/-Users-x-proj/s.jsonl", lambda p: {"type": "user", "message": {"role": "user", "content": p}}),
        "codex": (".codex/sessions/2026/11/28/rollout-x.jsonl", lambda p: {"timestamp": "2026-11-28T15:00:01Z", "type": "response_item",
                  "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": p}]}}),
    }
    for agent, (rel, rec) in records.items():
        home = os.path.join(tmp, agent, "Users", "janedoe")
        os.makedirs(os.path.dirname(os.path.join(home, rel)))
        with open(os.path.join(home, rel), "w", encoding="utf-8") as f:
            f.write(json.dumps(rec(free), ensure_ascii=False, separators=(",", ":")) + "\n")  # the free scan pasted earlier
            f.write(json.dumps(rec(prompt), ensure_ascii=False, separators=(",", ":")) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": ext}}]}}) + "\n")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home, "LANG": "en_US.UTF-8", "GIT_CONFIG_GLOBAL": os.devnull}
        out = subprocess.run(["bash", "-c", ext], env=env, capture_output=True, text=True).stdout.strip()
        got = hashlib.sha256(open(os.path.join(home, "excellent-free-scan", "intent_scan.py"), "rb").read()).hexdigest() if out == "saved" else out
        check(got == want, agent + ": the extractor saves intent_scan.py byte for byte")
        out = subprocess.run(["bash", "-c", free_ext], env=env, capture_output=True, text=True).stdout.strip()
        check(out == "saved" and open(os.path.join(home, "excellent-free-scan", "scan.py"), "rb").read() == open(os.path.join(ROOT, "scan.py"), "rb").read(),
              agent + ": the free scan's extractor still saves scan.py from the same log")
        sha = re.search(r"`(shasum [^`]+)`", prompt).group(1)
        r = subprocess.run(["bash", "-c", sha.replace("shasum -a 256", "sha256sum") if not shutil.which("shasum") else sha], env=env, capture_output=True, text=True)
        check(r.stdout.strip() == want and "janedoe" not in r.stdout + r.stderr, agent + ": the hash step prints the hash alone")
        run = re.search(r"`(python3 ~/excellent-free-scan/intent_scan.py)`", prompt).group(1)
        r = subprocess.run(["bash", "-c", run], env=env, capture_output=True, text=True)
        check(r.returncode == 0 and "janedoe" not in r.stdout + r.stderr and "Report: ~/excellent-free-scan/intent-report.html" in r.stdout,
              agent + ": the run step prints no account name and the report as ~/…")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
