#!/usr/bin/env python3
# Checks that counts of one read as one in the card, the printed summary and the report: "1 session", "1 action",
# "1 force push", "1 of 10 checks needs a look". Renders in memory with every count at 1; reads no logs, writes nothing.
import html, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import scan
meta = {"date": "November 18, 2026", "sessions": 1, "calls": 1, "agents": "Claude Code", "span": "Nov 18 – Nov 18",
        "secs": scan.plural(1, "second"), "gb": "0.0 GB", "rules": 1, "rulefiles": 1}
one = {"email_out": {"count": 1, "detail": "", "examples": [], "severity": "high"}}
every = {c[0]: {"count": 1, "detail": "", "examples": [], "severity": c[1]} for c in scan.CHECKS}
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    ok or fails.append(what)


def text(page):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", "", page, flags=re.S))))


card = lambda page: text(re.search(r'<section class="score" id="card">(.*?)</section>', page, re.S).group(1))
block = scan.summary(every, meta)
check(block.splitlines()[0].endswith("· 1 action"), "summary header says '1 action'")
c1 = card(scan.render(one, meta))
check("1 agent action," in c1 and "1 session ·" in c1, "card says '1 agent action' and '1 session'")
check("1 of 10 checks needs a look" in c1, "card says '1 of 10 checks needs a look'")
page = text(scan.render(every, meta))
check(all(t in page for t in ("1 force push ", "1 hook failing silently", "1 API key sitting in a plain-text log")), "tiles at 1 are singular")
check("It read 1 session (" in page and "1 instruction file with 1 rule it can check" in page and "in 1 second," in page,
      "fine print says '1 session', '1 instruction file', '1 rule', '1 second'")
bad = re.findall(r"(?<![\d,.])1 (?:agent )?(?:sessions|actions|seconds|instruction files|rules|requests|times|API keys|force pushes|"
                 r"git commands|deletes|publishes|breaks|hooks|keys|log files|commands|websites)\b", page + "\n" + block + "\n" + c1)
check(not bad, "no '1 <plural>' anywhere (%s)" % bad)
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
