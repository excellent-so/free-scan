#!/usr/bin/env python3
# Runs the scan, the prompt's extractor and its hash and open steps in a fake home (…/Users/janedoe) whose logs, rules
# and hooks name that home in every form (plain, other case, Claude Code's -Users-janedoe-, Grok's %2FUsers%2Fjanedoe).
# Checks that "janedoe" and the email show nowhere in what they print (stdout and stderr, also on errors) or in the
# report, that the report path is printed as ~/…, and that the share card and the printed summary hold only agent
# names, counts and dates. Writes only in a temp folder (deleted after).
import hashlib, html, json, os, re, shutil, subprocess, sys, tempfile
from urllib.parse import quote
HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "..", "scan.py")
NAME, EMAIL = "janedoe", "janedoe@example.com"
KEY1, KEY2 = "AKIA" + "Q7RZ4M2KXW9PLT3V", "AKIA" + "Z3N8VQ5RT2LMX7WK"  # made-up keys in AWS's format, split so secret scanners skip this file
SHARE = "https://excellent.so/scan?utm_source=free-scan&utm_medium=share&utm_campaign=launch"
root = tempfile.mkdtemp(prefix="free-scan-home-")
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    ok or fails.append(what)


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def jl(*recs):
    return "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in recs)


def run(cmd, home, **kw):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home, "XDG_CONFIG_HOME": home + "/.config", "LANG": "en_US.UTF-8"}
    return subprocess.run(cmd, env=env, cwd=root, capture_output=True, text=True, **kw)


def leaks(text):
    return NAME in text.lower() or EMAIL in text.lower()


def fake_home(n):
    home = os.path.join(root, str(n), "Users", NAME)
    proj = home + "/Sites/janedoe-site"
    os.makedirs(proj + "/.git")
    put(home + "/.claude/CLAUDE.md", "# Rules\n\n- Never delete `~/keep`.\n- Never open `~/vault`.\n")
    put(home + "/.claude/settings.json", json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": home + "/bin/guard.sh"}]}]}}))
    return home, proj


def bash(i, cmd):
    return {"type": "assistant", "timestamp": "2026-11-1%dT10:00:00.000Z" % (i % 9), "message": {"content": [
        {"type": "tool_use", "id": "t%d" % i, "name": "Bash", "input": {"command": cmd}}]}}


try:
    home, proj = fake_home(1)
    cmds = ['curl -A "bot (%s)" https://api.weather.gov/points' % EMAIL, "cat %s/.env" % proj,
            "git push --force origin main", "git commit --no-verify -m wip", "rm -rf %s/keep/old" % home,
            "cat %s/vault/notes.txt" % home, "ls /Users/JaneDoe/Sites"]
    put(home + "/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", proj) + "/s1.jsonl", jl(
        {"type": "user", "cwd": proj, "timestamp": "2026-11-10T09:00:00.000Z", "message": {"role": "user", "content":
         "use %s and look in %s" % (KEY1, home)}}, *[bash(i, c) for i, c in enumerate(cmds)]))
    put(home + "/.codex/sessions/2026/11/12/rollout-x.jsonl", jl(
        {"timestamp": "2026-11-12T09:00:00.000Z", "type": "session_meta", "payload": {"cwd": proj.replace(NAME, "JaneDoe")}},
        {"timestamp": "2026-11-12T09:00:01.000Z", "type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
         "arguments": json.dumps({"cmd": "git push -f origin main"}), "call_id": "c1"}}))
    put(home + "/.grok/sessions/" + quote(proj, safe="") + "/g1/chat_history.jsonl",
        jl({"type": "user", "content": "key %s in %s/.env" % (KEY2, proj)}))

    r = run([sys.executable, SCAN, "--email", EMAIL], home)
    out = r.stdout
    check(r.returncode == 0, "scan exits 0" + ("" if r.returncode == 0 else ": " + r.stderr[-300:].replace(root, "…")))
    check(not leaks(out + r.stderr), "no account name or email in stdout or stderr")
    check("Report: ~/excellent-free-scan/report.html" in out.splitlines(), "report path printed as ~/excellent-free-scan/report.html")
    page = open(home + "/excellent-free-scan/report.html", encoding="utf-8").read()  # written at the real path
    lines = out.splitlines()
    i = next((k for k, l in enumerate(lines) if l.startswith("Excellent free scan · ")), len(lines))
    block = lines[i:]
    check(block[:1] == ["Excellent free scan · Claude Code + Codex + Grok Build · Nov 10 – Nov 16 · 8 actions"] if block else False,
          "summary header: agents, dates, actions (got %r)" % (block[:1],))
    check(block[-1:] == ["Run yours free: excellent.so/scan"] and len(block) == 12, "summary: header, 10 rows, 'Run yours free' last")
    rest = "\n".join(block).replace("excellent.so/scan", "")
    check(not re.search(r"[/~@‹]", rest) and not leaks(rest), "summary holds no path, email or account name")
    counts = {m.group(1).strip(): int(m.group(2).replace(",", "")) for m in (re.match(r"  (.+?)\s+([\d,]+)$", l) for l in block) if m}
    want = {"API keys are sitting in your agent logs": 2, "Your hooks fail silently": 1, "Never-delete folders were touched": 1,
            "Your own rules were broken": 1, "Your email was sent to websites": 1, "Agents force-pushed": 2}
    check(all(counts.get(k) == v for k, v in want.items()), "the checks that show paths fired (%s)" % counts)

    check(not leaks(page), "no account name or email anywhere in report.html")
    vis = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", "", page, flags=re.S)))
    check(all(x in vis for x in ("cat ~/vault/notes.txt", "rm -rf ~/keep/old", "~/bin/guard.sh", "-Users-‹you›-Sites-‹you›-site", "%2FUsers%2F‹you›%2FSites", "· ‹you›-site")),
          "report shows home paths as ~ and log folder names with ‹you›")
    card = re.search(r'<section class="score" id="card">(.*?)</section>', page, re.S)
    ctext = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", card.group(1)))).strip() if card else ""
    check(ctext.startswith("My Claude Code + Codex + Grok Build check-up · 8 agent actions, Nov 10 – Nov 16 8 of 10 checks need a look"),
          "card leads with agents and actions, then checks (got %r)" % ctext[:110])
    check(ctext.endswith("Run yours free: excellent.so/scan"), "card ends with 'Run yours free: excellent.so/scan'")
    check(card and re.findall(r'href="([^"]*)"', card.group(1)) == [html.escape(SHARE)], "card's one link is the utm link")
    check(not re.search(r"[/~@‹]", ctext.replace("excellent.so/scan", "")) and not leaks(ctext), "card holds no path, email or account name")
    check('href="#card"' in page and "#card:target" in page, "card-only view (#card)")

    # the share link and the card's JSON block: numbers, agent names and dates only
    blk = re.search(r'<script type="application/json" id="card-data">(.*?)</script>', page, re.S)
    cd = json.loads(blk.group(1)) if blk else {}
    links = cd.get("links", {})
    link = links.get("copy", "")
    check(re.fullmatch(r"https://excellent\.so/r\?v=1&a=cxg&n=8&d=7&k=\d+(\.\d+){9}&s=\d+&p=\d+(\.\d+){2}&c=[0-9a-z]{4}&utm_source=free-scan&utm_medium=share&utm_campaign=launch&utm_content=copy", link) is not None,
          "share link matches the v1 format, 3 agents, 8 actions, 7 days (%s)" % link)
    qs = dict(x.split("=") for x in link.split("?")[1].split("&"))
    check(sum(int(x) for x in qs.get("p", "x").split(".") if x.isdigit()) == 8 and qs.get("s", "").isdigit() and int(qs["s"]) >= 3, "link carries the session count and agent actions per agent (sum = actions)")
    check(not leaks(link) and not leaks(blk.group(1) if blk else "x") and not re.search(r"[~@‹]|/users|%2f|\\\\", (link + blk.group(1)).lower() if blk else "x"),
          "share link and card JSON hold no account name, path or email")
    check(set(cd) == {"title", "actions", "sub", "need_b", "need_r", "ok", "foot", "tiles", "links"} and all(set(t) == {"n", "label", "sev"} for t in cd.get("tiles", [])),
          "card JSON holds only the card's fields (title, counts, labels)")
    xl = re.search(r'href="(https://x\.com/intent/post\?text=[^"]*)"', page)
    check(xl is not None and not leaks(xl.group(1)) and __import__("urllib.parse").parse.unquote(xl.group(1)).endswith(links.get("x", "?")), "X post holds no name and ends with the share link")
    check(" by=" not in page and "&by=" not in page and 'id="by"' not in page, "no name field and no by= anywhere")

    # an error: the traceback names the report's folder, and must show it as ~/…
    put(home + "/afile", "")
    r = run([sys.executable, SCAN, "--out", home + "/afile/report.html"], home)
    check(r.returncode != 0 and "Traceback" in r.stderr and "~/afile" in r.stderr and not leaks(r.stdout + r.stderr),
          "an error's traceback shows ~/…, no account name")

    # the prompt's own steps: extractor (when it can't save), hash check and open, in a second fake home
    md = open(os.path.join(HERE, "..", "PROMPT.md"), encoding="utf-8").read()
    prompt = md.split("````text\n", 1)[1].rsplit("````", 1)[0]
    check(not re.search(r"/Users/(?!…)", prompt.split("# EXCELLENT-FREE-SCAN-BEGIN")[0]), "prompt text asks for no /Users/ path")
    ext = re.search(r"python3 - <<'EOF'\n.*?\nEOF", prompt, re.S).group(0)
    sha = re.search(r"`(shasum [^`]+)`", prompt).group(1)
    opn = re.search(r"`(open [^`]+)`", prompt).group(1)
    home2, proj2 = fake_home(2)
    put(home2 + "/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", proj2) + "/s.jsonl",
        jl({"type": "user", "cwd": proj2, "message": {"role": "user", "content": prompt}}))
    put(home2 + "/excellent-free-scan", "")  # a file where the folder should be: saving fails
    r = run(["bash", "-c", ext], home2)
    o = r.stdout + r.stderr
    check(o.strip().startswith("not saved:") and not leaks(o), "extractor error names no path (%r)" % o.strip())
    os.remove(home2 + "/excellent-free-scan")
    r = run(["bash", "-c", sha], home2)
    check(r.stdout + r.stderr == "" and r.returncode == 0, "hash step prints nothing when the file is missing")
    o = run(["bash", "-c", ext], home2).stdout
    r = run(["bash", "-c", sha], home2)
    want_sha = hashlib.sha256(open(SCAN, "rb").read()).hexdigest()
    check(o.strip() == "saved" and r.stdout.strip() == want_sha and not leaks(r.stdout + r.stderr), "hash step prints the hash alone")
    if sys.platform == "darwin":  # the report doesn't exist in this home: open fails, and must not say where it looked
        r = run(["bash", "-c", opn], home2)
        check(r.stdout.strip() == "not opened" and not leaks(r.stdout + r.stderr), "open step's failure names no path")
finally:
    shutil.rmtree(root, ignore_errors=True) if not os.environ.get("KEEP") else print("kept", root)
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
