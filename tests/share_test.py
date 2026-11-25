#!/usr/bin/env python3
# Checks the share link, the card's JSON block, the CSP and the page's URLs. Renders in memory from made-up numbers and
# reads no logs. (home_test.py checks the same link and block for a leak of the fake home's names.)
import hashlib, base64, json, os, re, sys, zlib
from urllib.parse import parse_qs, unquote, urlparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import scan, build_share_format
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    ok or fails.append(what)


meta = {"date": "November 18, 2026", "sessions": 12, "calls": 340, "agents": "Claude Code + Grok Build", "span": "Nov 1 – Nov 18", "days": 18,
        "secs": "2 seconds", "gb": "0.1 GB", "rules": 2, "rulefiles": 1, "split": [300, 40]}
f = {"secrets_in_logs": {"count": 4, "detail": "x", "examples": [], "severity": "high"}, "force_push": {"count": 1, "detail": "x", "examples": [], "severity": "medium"},
     "secret_files": {"count": 1200, "detail": "x", "examples": [], "severity": "low"}}
LINK = re.compile(r"^https://excellent\.so/r\?v=1&a=[cxg]{0,3}&n=\d+&d=\d+&k=\d+(\.\d+){9}&s=\d+&p=(\d+(\.\d+)*)?&c=[0-9a-z]{4}&utm_source=free-scan&utm_medium=share&utm_campaign=launch&utm_content=(x|linkedin|copy|video|image)$")
links = scan.share_links(f, meta)
link = links["copy"]
check(set(links) == {"x", "linkedin", "copy", "video", "image"} and all(LINK.match(l) for l in links.values()), "share links match the v1 format, one per route (%s)" % link)
check(all(l.endswith("&utm_content=" + r) for r, l in links.items()), "utm_content is the route")
q = parse_qs(urlparse(link).query, keep_blank_values=True)
check(q["a"] == ["cg"] and q["n"] == ["340"] and q["d"] == ["18"], "agents in card order, actions, days")
check(q["s"] == ["12"] and q["p"] == ["300.40"] and sum(int(x) for x in q["p"][0].split(".")) == 340 and len(q["p"][0].split(".")) == len(q["a"][0]), "s is the sessions; p is agent actions per agent in a's order and sums to n")
check(link.index("&k=") < link.index("&s=") < link.index("&p=") < link.index("&c="), "param order is v, a, n, d, k, s, p, c")
check("by" not in q and "&by=" not in link, "no name parameter")


def b36(n):  # a second, independent way to write the checksum (see share-format.json)
    return "".join("0123456789abcdefghijklmnopqrstuvwxyz"[(n // 36 ** i) % 36] for i in (3, 2, 1, 0))


canon = "v=1&a=cg&n=340&d=18&k=0.0.4.1200.1.0.0.0.0.0&s=12&p=300.40"
check(q["c"] == [b36(zlib.crc32(canon.encode()) % 36 ** 4)] and q["c"] == [scan.checksum(canon)], "c is base36 of CRC32 over v,a,n,d,k, mod 36**4, 4 characters (%s)" % q["c"][0])
check(all(re.fullmatch(r"[0-9a-z]{4}", scan.checksum("x%d" % i)) for i in range(2000)), "checksum is always 4 lowercase base36 characters")
fmt = json.load(open(os.path.join(os.path.dirname(os.path.abspath(scan.__file__)), "share-format.json"), encoding="utf-8"))
for name in ("with_findings", "all_zero", "three_agents", "no_agents", "first_v1_without_s_and_p"):
    e = fmt["examples"][name]
    check(e["c"] == b36(zlib.crc32(e["canonical"].encode()) % 36 ** 4) and (name.startswith("first") or ("&c=" + e["c"] + "&") in e["links"]["copy"]), "share-format.json example %s: checksum recomputes" % name)
    if "links" in e:
        qq = parse_qs(urlparse(e["links"]["copy"]).query, keep_blank_values=True)
        check(sum(int(x) for x in qq["p"][0].split(".") if x) == int(qq["n"][0]) and len(qq["a"][0]) == len([x for x in qq["p"][0].split(".") if x]), "share-format.json example %s: p sums to n, one number per agent" % name)
check([c["id"] for c in fmt["checks"]] == ["email_out", "public_submit", "secrets_in_logs", "secret_files", "force_push", "no_verify", "protected_delete", "publish_deploy", "written_rules", "broken_hooks"],
      "CHECKS order is the frozen k order")
ids = [c[0] for c in scan.CHECKS]
check(q["k"][0].split(".") == [str(f[i]["count"]) if i in f else "0" for i in ids], "k holds the counts in CHECKS order (%s)" % q["k"][0])
check(scan.share_links({}, dict(meta, agents="no agent logs found", calls=0, days=0, sessions=0, split=[]))["copy"].startswith("https://excellent.so/r?v=1&a=&n=0&d=0&k=0.0.0.0.0.0.0.0.0.0&s=0&p=&c="), "empty scan: empty a, zeros")
check(json.load(open(os.path.join(os.path.dirname(os.path.abspath(scan.__file__)), "share-format.json"), encoding="utf-8")) == build_share_format.build(),
      "share-format.json is up to date (python3 build_share_format.py)")

page = scan.render(f, meta)
m = re.search(r'<script type="application/json" id="card-data">(.*?)</script>', page, re.S)
data = json.loads(m.group(1))
check(set(data) == {"title", "actions", "sub", "tiers", "ok", "foot", "tiles", "links"}, "card JSON has only the card's fields")
check([(t["n"], t["sev"]) for t in data["tiles"]] == [(4, "high"), (1, "medium"), (1200, "low")] + [(0, "ok")] * 7, "10 tiles in display order: counts and severities")
check(data["tiles"][1]["label"] == "force push" and data["tiles"][2]["label"] == "actions on .env, SSH or keychain secrets", "tile labels: singular for 1")
check(data["foot"] == "12 sessions \u00b7 300 Claude Code and 40 Grok Build actions \u00b7 Free check by Excellent", "card foot shows the sessions and the agent split (the link's s and p)")
check(data["links"] == links and sum(t["n"] for t in data["tiers"]) == 3 and data["actions"] == 340, "JSON link, need line and actions match")
shown = re.sub(r"<[^>]+>", " ", re.search(r'<section class="score" id="card">(.*?)</section>', page, re.S).group(1))
check(all(t["label"] in shown for t in data["tiles"]), "every tile label is on the card")
check("12 sessions" in shown and "300 Claude Code" in shown and "40 Grok Build" in shown, "the HTML card shows s and p")
check("<" not in m.group(1) and "&" not in m.group(1), "JSON block escapes < > &")

# CSP
csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', page).group(1)
dirs = {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}
body = re.search(r"<script>(.*?)</script>", page, re.S).group(1)
check(dirs["default-src"] == ["'none'"] and "connect-src" not in dirs and "frame-src" not in dirs, "CSP: default-src 'none', no connect-src")
check(dirs["script-src"] == ["'sha256-%s'" % base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()], "CSP: script only by the hash of the inline script")
check("'unsafe-inline'" not in dirs["script-src"] and "'unsafe-eval'" not in csp and "*" not in csp and "http" not in csp, "CSP: no unsafe-inline script, no eval, no hosts")
check(dirs["img-src"] == ["blob:"] and dirs["media-src"] == ["blob:"] and dirs["style-src"] == ["'unsafe-inline'"], "CSP: blob: images and media, inline styles")
check(len(re.findall(r"<script\b", page)) == 2, "two script tags only")
# the script
check(not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts|eval|Worker|localStorage|sessionStorage|indexedDB|import)\b|document\.cookie|new Function", body),
      "script has no network, eval, worker or storage calls")
check(not re.search(r"https?:|//[a-z]", body), "script holds no URL")
# every URL on the page
urls = set(re.findall(r"https?://[^\s\"'<>)]+", page))
ok = all(u.startswith(("https://excellent.so/", "https://www.excellent.so/", "https://x.com/intent/post?text=")) for u in urls)
check(ok, "the only URLs are excellent.so and the x.com post link (%s)" % sorted({u.split("?")[0] for u in urls}))
check(all(not re.search(r"\b(vulnerabilit)", t, re.I) for t in (page,)), "never says vulnerabilities")
xt = unquote(scan.x_post(f, meta).split("text=", 1)[1])
want = "My AI coding agents' check-up: 4 API keys sitting in plain-text logs and 1 force push. A free check counted it from my own Mac's logs. Run yours: " + links["x"]
check(xt == want, "X text: top two non-zero checks in the card's labels (%r)" % xt[:120])
check(xt.endswith(links["x"]) and xt.count("http") == 1, "X text ends with the share link (utm_content=x), and holds only that link")
zt = unquote(scan.x_post({}, meta).split("text=", 1)[1])
check(zt.startswith("I ran a free check on my AI coding agents' logs: all 10 checks came back clean across 340 agent actions. Run yours: https://excellent.so/r?v=1&"), "zero case text")
check(len(page.encode()) < 250_000, "under 250 KB (%d bytes)" % len(page.encode()))
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
