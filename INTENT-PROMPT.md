# Excellent free Intent scan: the paste-in prompt

Paste everything in the box below into Claude Code or Codex, started in any folder. It runs a read-only check of the
user's own agent logs and opens a local report (`~/excellent-free-scan/intent-report.html`).

- Script: `intent_scan.py` in this folder, 114,191 bytes, Python 3.9+ standard library only.
- SHA-256 of the script: `ee8acf3df71e2ede9b527ace11f9e1fdd30da6e80729eacfd7f3be60c22b57cd`. The same hash is listed in this repository's `SHA256SUMS`, so you can check your
  copy.
- The extractor copies the script out of the conversation's own log, so the agent doesn't have to retype
  114 KB (about 34,000 output tokens and three to six minutes). If it can't, the agent
  writes the file itself.
- Rebuild this file after any change to `intent_scan.py`: `python3 build_intent_prompt.py`.

Copy from the line after the opening fence to the line before the closing fence.

````text
Please run the Excellent free Intent scan for me: a read-only check of whether my AI coding agents (Claude Code with its sub-agents, Codex, Grok Build) reported what they did on this Mac, read from their own logs. The Python script at the end of this message does all the reading and prints only a short summary (counts, agent names, dates, log size and where the report is, as a ~/ path), never a key, email or log text, so nothing private comes into this chat.

Steps:
1. Save the script. Run the extractor below as it is. It copies the script between the two EXCELLENT-FREE-INTENT-SCAN lines from this conversation's own log into ~/excellent-free-scan/intent_scan.py. If it prints anything other than "saved", create that file yourself with the script text, exactly as written.
2. Check it. Run `shasum -a 256 ~/excellent-free-scan/intent_scan.py 2>/dev/null | cut -c1-64`. It must print ee8acf3df71e2ede9b527ace11f9e1fdd30da6e80729eacfd7f3be60c22b57cd. If it doesn't, stop and tell me.
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
python3 - <<'EOF'
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
EOF

# EXCELLENT-FREE-INTENT-SCAN-BEGIN
#!/usr/bin/env python3
# Excellent free Intent scan 1.0 (excellent.so): did your AI coding agents report what they did, from their own logs?
# Reads:  agent logs in ~/.claude/projects (sub-agents included), ~/.codex/sessions, ~/.codex/archived_sessions and
#         ~/.grok/sessions; the CLAUDE.md, AGENTS.md, CLAUDE.local.md and .claude/rules files of the folders agents
#         worked in and the folders above them up to your home folder, plus ~/.claude/CLAUDE.md, ~/.claude/rules and
#         ~/.codex/AGENTS.md, only for their never-open rules; your email from ~/.claude.json and
#         `git config --global user.email` (to mask it).
# Writes: one file, ~/excellent-free-scan/intent-report.html. No network. Prints only a short summary (counts, agent
#         names, dates, log size and where the report is, as ~/…), never a key, email, log text or your account name.
# Never opens Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos
# data or app containers in Library, other drives, or a folder your rules name (in backticks) as never to open or
# read, once it has read that rule. It reports what was unauthorized or undisclosed, never why. The Excellent app's
# intent rules, logs-only. Python 3.9+, standard library. Shares scan.py's privacy code, copied so it stays one file.
import html, json, os, posixpath as pp, re, subprocess, sys, time
from datetime import datetime
from urllib.parse import unquote

# ---------- privacy: the same code as scan.py (copied) ----------
HOME = os.path.expanduser("~").rstrip("/")
USER = pp.basename(HOME)  # your account name: never printed or shown
HOME_RX = re.compile(r"(?<![\w.-])" + re.escape(HOME) + r"(?![\w-]|\.[\w-])", re.I) if HOME else None
USER_RX = re.compile(r"(?:(?<![A-Za-z0-9])|(?<=%2F))" + re.escape(USER) + r"(?![A-Za-z0-9])", re.I) if USER else None
fold = (lambda p: p.lower()) if sys.platform == "darwin" else (lambda p: p)  # macOS paths ignore case


def shown(s):  # what is printed or shown: your home folder as ~, and your account name in no path (‹you›)
    s = HOME_RX.sub("~", s) if HOME_RX else s
    return re.sub(r"\S*[/~%]\S*", lambda m: USER_RX.sub("‹you›", m.group(0)), s) if USER_RX else s


class Shown:  # errors and tracebacks go out the same way, here and in the worker processes
    def __init__(self, f):
        self.f = f

    def write(self, s):
        self.f.write(shown(s))
        return len(s)

    def __getattr__(self, k):
        return getattr(self.f, k)


sys.stderr = Shown(sys.stderr) if sys.stderr else sys.stderr
PRIVATE = re.compile(r"(documents|desktop|downloads|pictures|movies|music|public|library/(mobile documents|mail|messages"
                     r"|safari|calendars|reminders|photos|cloudstorage|containers|group containers))(/|$)", re.I)
NEVER_OPEN, EMAILS = [], []  # folders your rules close; your email addresses
RULES = {"protected": [], "no_open": [], "no_command": [], "names": []}


def closed(p):
    p, h = pp.normpath(p), fold(HOME) + "/"
    f = fold(p)
    return (p.startswith("/Volumes/") or (f.startswith(h) and bool(PRIVATE.match(p[len(h):])))
            or any(f == c or f.startswith(c + "/") for c in NEVER_OPEN))


def read(p, limit=4 << 20):
    if closed(p) or not os.path.isfile(p):
        return None
    try:
        with open(p, "rb") as f:
            return f.read(limit).decode("utf-8", "replace")
    except OSError:
        return None


def owner_emails(extra=()):
    out = []
    try:
        out.append(json.loads(read(HOME + "/.claude.json", 1 << 26) or "{}")["oauthAccount"]["emailAddress"])
    except Exception:
        pass
    try:
        out.append(subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True, timeout=5).stdout)
    except Exception:
        pass
    return list(dict.fromkeys(e.strip().lower() for e in out + list(extra) if "@" in e and "noreply" not in e))


KEY_PATTERNS = [
    ("claude_login", rb"sk-ant-o[ar]t\d{2}-[\w-]{20,}", r"sk-ant-(oat|ort)\d\d-[\w-]{80,}"),
    ("anthropic_key", rb"sk-ant-(?!o[ar]t\d)[\w-]{20,}", r"sk-ant-(api|admin)\d\d-[\w-]{80,}"),
    ("openrouter_key", rb"sk-or-v1-[a-f0-9]{40,}", r"sk-or-v1-[0-9a-f]{64}"),
    ("openai_key", rb"sk-(?!or-v1-|ant-)(?:proj-)?[\w-]{32,}", r"sk-((proj|svcacct|admin)-[\w-]{80,}|[A-Za-z0-9]{48})"),
    ("github_token", rb"gh[posu]_[A-Za-z0-9]{30,}|github_pat_\w{40,}", r"gh[posu]_[A-Za-z0-9]{36}|github_pat_\w{80,}"),
    ("gitlab_token", rb"glpat-[\w-]{20,}(?:\.\d{2}\.[a-z0-9]{9})?", r"glpat-[\w-]{20,}(\.\d\d\.[a-z0-9]{9})?"),
    ("slack_token", rb"xox[abposr]-[A-Za-z0-9-]{10,}", r"xox[abpr]-\d{6,}-[A-Za-z0-9-]{10,}"),
    ("aws_key", rb"AKIA[0-9A-Z]{16}", r"AKIA[0-9A-Z]{16}"),
    ("google_key", rb"AIza[\w-]{35}", r"AIza[\w-]{35}"),
    ("stripe_key", rb"[sr]k_live_[A-Za-z0-9]{20,}", r"[sr]k_live_[A-Za-z0-9]{24,}"),
    ("xai_key", rb"xai-[A-Za-z0-9]{40,}", r"xai-[A-Za-z0-9]{70,}"),
]
EMAIL_RX = re.compile(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}")
MASK_KEYS = [(t, re.compile(rx.decode())) for t, rx, _ in KEY_PATTERNS]
SECRETISH = re.compile(r"((?:api[_-]?key|x-api-key|authorization|bearer|token|secret|password|passwd|pwd|access[_-]?key|"
                       r"private[_-]?key)[\"']?\s*[:=]\s*[\"']?|\bbearer\s+)(?!‹)([^\s\"'&,;)}]{6,})", re.I)


def mask(s, n=200):  # for the report's examples: emails, keys, passwords and long tokens hidden
    for e in EMAILS:
        s = re.sub(re.escape(e), "‹your email›", s, flags=re.I)
    s = EMAIL_RX.sub("‹email›", s)
    for t, rx in MASK_KEYS:
        s = rx.sub("‹" + t.replace("_", " ", 1) + "›", s)
    s = SECRETISH.sub(r"\1‹hidden›", s)
    s = re.sub(r"(\s-u\s+[\"']?[^\s\"':]+):[^\s\"']+", r"\1:‹hidden›", s)
    s = re.sub(r"(https?://[^\s:@/]+):[^\s@/]+@", r"\1:‹hidden›@", s)
    s = re.sub(r"\b[\w+-]{40,}={0,2}", "‹token›", s)
    s = re.sub(r"\s+", " ", s.replace(HOME, "~")).strip()
    return s[:n] + "…" if len(s) > n else s



# ---------- reading what agents wrote (the engine's text.rs, ported; every rule is a fixed false positive) ----------
# Precision over recall: a sentence counts only when its wording is unambiguous. Quoted examples, fenced code,
# questions, future intentions, negations, hedges and someone else's words relayed are not claims.
def sentences(text):  # text without fenced code and quoted lines, split into sentences (bullets and lines count)
    out, fence = [], False
    for line in text.split("\n"):
        t = line.strip()
        if t.startswith(("```", "~~~")):
            fence = not fence
            continue
        if fence or t.startswith(">") or not t:
            continue
        t = t.lstrip("-*• ").strip()
        for p in ("[x] ", "[X] ", "[ ] ", "✅ ", "✔ ", "☑ "):
            if t.startswith(p):
                t = t[len(p):]
                break
        cur = ""
        for i, c in enumerate(t):
            cur += c
            if c in ".!?;" and (i + 1 == len(t) or t[i + 1].isspace()):
                push_sentence(out, cur)
                cur = ""
        push_sentence(out, cur)
    return out


def push_sentence(out, s):
    s = s.strip()
    if sum(1 for c in s if c.isalnum()) >= 3:
        out.append(s)


def unquoted(s):  # "…" and `…` spans removed: quoted examples are not assertions
    out, q = [], None
    for c in s:
        if q is None and c in "\"“`":
            q = "”" if c == "“" else c
        elif q is not None and c == q:
            q = None
        elif q is None:
            out.append(c)
    return "".join(out)


I = re.I
NEGATION = re.compile(r"\b(not|no|never|n't|cannot|can't|isn't|aren't|wasn't|weren't|didn't|doesn't|don't|won't|without|fail(?:s|ed|ing)?|unable|broken|still\s+fail)\b|n't\b", I)
FUTURE = re.compile(r"\b(will|going to|i'll|we'll|let me|next,? i|plan to|need to|needs to|should|once|after i|before i|to make sure|try to|attempt to|would|could|if|so that|so\s+(?:the\s+)?(?:tests?|checks?|ci|builds?)|to\s+get|in\s+order\s+to|until|unless)\b", I)
HEDGE = re.compile(r"\b(might|may|probably|likely|appears? to|seems? to|i think|i believe|hopefully|expected to|most|some|mostly)\b", I)
REPORTED = re.compile(r"\b(says?|said|saying|reports?|reported|alleg\w*|claim(?:s|ed)|according\s+to|describ\w*|wrote|writes|argu\w*|notes?|noted|suggests?|suggested|recommends?|found|finds|shows?|showed|accus\w*|told|asserts?|asserted|cites?|cited|quotes?|quoted|mentions?|mentioned|postmortems?|the\s+(?:paper|study|post|article|snippet|report|coverage|thread|tweet|author|ceo|engineer|company|incident|allegation|timeline))\b", I)


def is_reported(s):  # someone else's words relayed ("the post says", "he alleges"): never this agent's own
    return bool(REPORTED.search(s))


def assertive(s):  # a completed fact: not a question, intention, negation or hedge
    return not s.rstrip().endswith("?") and not NEGATION.search(s) and not FUTURE.search(s) and not HEDGE.search(s)


C_CHECKS = re.compile(r"\b(all\s+)?(\d+\s+)?(unit\s+|integration\s+|e2e\s+|acceptance\s+)?(tests?|specs?|checks?|test\s+suite|suite|build|ci|lint(?:ing)?|type\s*-?check(?:s|ing)?|clippy)\b[^.;]{0,40}\b(pass(?:es|ed|ing)?|green|succeed(?:s|ed)?|ok)\b|\b(passing|green)\s+(tests|build|ci|checks)\b|\btests?\s+are\s+(all\s+)?green\b", I)
C_DONE = re.compile(r"\b(i(?:'ve| have)?|we(?:'ve| have)?|it(?:'s| is)|this\s+is|everything\s+is|all\s+(?:done|set)|the\s+(?:task|feature|change|fix|work|implementation)\s+is)\b[^.;]{0,40}\b(done|complete[d]?|finished|implemented|fixed|resolved|all\s+set|ready\s+(?:to|for)\s+(?:merge|review|ship))\b|^(done|completed|implemented|fixed)\b", I)
C_APPROVAL = re.compile(r"\b(approved|signed\s+off|sign-off\s+(?:given|received)|lgtm|given\s+the\s+go-ahead)\b[^.;]{0,40}\b(by|from)\b|\b(reviewer|owner|lead|leadership|manager|review\s+agent|product)\b[^.;]{0,30}\b(approved|signed\s+off|agreed|ok'd|okayed)\b", I)
NOUN_PASS = re.compile(r"\b(?:a|an|another|one|second|first|final|last|systematic|quick|single|careful)\s+(?:\w+\s+)?pass(?:es)?\b", I)
GENERIC = re.compile(r"^\W*(?:an?|any|each|empty|zero)\b|\bcounts?\s+as\s+a\s+pass\b|\b(?:is|are)\s+an?\s+pass\b", I)
MODAL_APPROVAL = re.compile(r"\b(can|cannot|could|may|might|must|should|would|will|to)\s+(?:be\s+|get\s+)?(?:approved|signed\s+off)\b", I)
C_PRESERVED = re.compile(r"\b(every|all|each)\b[^.;]{0,50}\b(is|are)\s+(?:now\s+|still\s+)?(live|in|working|honou?red|preserved|kept|unchanged|intact|supported|applied)\b|\bnothing\s+else\s+(?:has\s+)?changed\b|\bno\s+(?:behaviou?r(?:al)?|functional|user-facing)\s+changes?\b|\bbehaviou?r\s+is\s+unchanged\b", I)


def claims_in(s):  # "checks", "approval", "done" (a hedge, negation or intention makes none of them a claim)
    u = unquoted(s)
    if is_reported(u) or not assertive(u):
        return []
    out = []
    if C_CHECKS.search(NOUN_PASS.sub(" ", u)) and not GENERIC.search(u):  # "a systematic pass over", "a check that runs zero tests is a pass"
        out.append("checks")
    if C_APPROVAL.search(u) and not MODAL_APPROVAL.search(u):  # "can be approved from the app" says what is possible
        out.append("approval")
    if C_DONE.search(u) and "checks" not in out:
        out.append("done")
    return out


R_RULE = re.compile(r"\b(must\s+not|must\s+never|never\s+(?:allow|use|show|match|include|return|expose|filter|rank|let)|do\s+not\s+(?:allow|use|show|match|include|return|expose|filter|rank|let)|don't\s+(?:allow|use|show|match|include|return|expose|filter|rank|let)|is\s+(?:not\s+allowed|forbidden|prohibited|disallowed)|(?:are|is)\s+blocked|block(?:ed|s)?\s+by\s+default|deny(?:-?list)?|blocklist|block-?list|exclude[sd]?\s+from|prohibit(?:ed|s)?|forbid(?:den|s)?|protected\s+(?:trait|attribute|class|characteristic|category|categories|traits|attributes)|off\s+by\s+default|disabled\s+by\s+default|unless\s+(?:\w+\s+){0,4}(?:approv\w*|sign\w*\s+off|confirm\w*))\b", I)


def is_rule(s):  # a sentence that restricts what the product or an agent may do
    u = unquoted(s)
    return bool(R_RULE.search(u)) and not u.rstrip().endswith("?") and not is_reported(u)


R_PENDING = re.compile(r"\b(pending\s+(?:\w+\s+){0,2}(?:approval|review|sign-?off|decision|confirmation)|awaiting\s+(?:\w+\s+){0,2}(?:approval|review|sign-?off|decision|confirmation)|unless\s+(?:\w+\s+){0,4}(?:approv\w*|sign\w*\s+off)|needs?\s+(?:\w+\s+){0,2}(?:approval|sign-?off|a\s+decision)|(?:requires?|until)\s+(?:\w+\s+){0,3}(?:approval|sign-?off)|(?:lead|leadership|owner|manager|product|legal|pm|team)\s+(?:needs?\s+to|should|must|has\s+to|to)\s+(?:approve|decide|confirm|sign\s+off)|to\s+be\s+(?:approved|confirmed|decided)|tbd\s+by|confirm\s+with\s+(?:the\s+)?(?:lead|owner|leadership|product|legal))\b", I)
R_DECIDER = re.compile(r"\b(lead|leads|leadership|owner|manager|product|legal|pm|team|someone|reviewer|human|you|ceo|cto|stakeholder|compliance|approver|sign-?off)\b", I)
R_NARRATED = re.compile(r"\bunless\s+(?:\w+\s+){0,4}(?:approved|signed\s+off|had\s+approved)\b", I)


def is_pending_decision(s):  # a decision left to someone else, now (not a story about one, not talk about the idea)
    u = R_NARRATED.sub("", unquoted(s))
    return bool(R_PENDING.search(u)) and bool(R_DECIDER.search(u)) and not is_reported(u) and not u.rstrip().endswith("?")


R_OBJECTION = re.compile(r"\b(i\s+(?:won't|will\s+not|can't|cannot|am\s+not\s+(?:able|comfortable|going)\s+to|decline[ds]?|am\s+declining|refuse[ds]?|chose\s+not\s+to|did\s+not|didn't|have\s+not|haven't)\s+(?:\w+\s+){0,6}?(?:implement|add|build|include|make|do|apply|write|ship|change)|i(?:'ve| have)\s+(?:left|kept)\s+(?:\w+\s+){0,6}(?:out|unchanged|as\s+(?:it\s+)?(?:was|is))\s+because|instead\s+of\s+(?:\w+\s+){0,6}i\s+(?:implemented|added|used|did))\b", I)
R_DECLINE = re.compile(r"\b(won't|will\s+not|decline[ds]?|declining|refuse[ds]?|refusing|chose\s+not\s+to|am\s+not\s+(?:comfortable|going)\s+to|instead\s+of)\b", I)


def objection_in(s):  # an agent saying openly that it won't do, or didn't do, part of the task
    u = unquoted(s)
    return bool(R_OBJECTION.search(u)) and not u.rstrip().endswith("?") and not is_reported(u)


R_CONSTRAINT = re.compile(r"\b(do\s+not|don't|never|must\s+not|avoid|no)\s+((?:make|take|change|modify|edit|touch|alter|add|remove|delete|introduce|rewrite|decide|alter)\b[^.;]{0,80})", I)
R_DESIGN = re.compile(r"\b(design|product|policy|behaviou?r(?:al)?|scope)\s+(?:calls?|decisions?|choices?|changes?)\b|\bdecide\b|\bscope\s+creep\b", I)
IMPERATIVE = re.compile(r"^$|(^|\W)(please|and|but|also|just|so|then|you|we|agents?|sub-?agents?|you\s+should)$|[,:;(\u2014\u2013-]$", I)
RELATIVE = re.compile(r"\b(other|others|else|except|besides|beyond|outside|unless|anything|everything)\b", I)
TOUCH = ("change", "modify", "edit", "touch", "alter", "rewrite", "delete", "remove")
FILE_TOKEN = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-]+(?:\.[\w-]+)*\.[A-Za-z][A-Za-z0-9]{1,6})(?![\w])")


def constraint_in(s):  # ("decisions", []) for "don't make design calls"; ("touch", terms, files) for "don't touch X"
    u = unquoted(s)
    m = R_CONSTRAINT.search(u)
    if not m or not IMPERATIVE.search(re.sub(r"[*_#>]+", "", u[:m.start()]).strip()):
        return None  # "filters must not remove valid records" is a requirement, not an instruction to an agent
    rest = m.group(2)
    if R_DESIGN.search(rest):
        return ("decisions", [], [])
    verb = (rest.split() or [""])[0].lower()
    t = [w for w in terms(rest) if w not in TOUCH + ("file", "files", "code")]
    if verb in TOUCH and t and not RELATIVE.search(rest):  # "any other file" names nothing the logs can check  # named files (scan.py, PROMPT.md) match by name: "scan" alone is not intent_scan.py
        o = R_CONSTRAINT.search(s)
        files = [x.lower() for x in FILE_TOKEN.findall(s[o.start(2):o.start(2) + 200] if o else "")]
        return ("touch", t, files)
    return None


R_FLAG = re.compile(r"\b(high[-\s]severity|critical|blocker|blocking\s+issue|must\s+(?:be\s+)?fix(?:ed)?\s+before|violat(?:es|ion|ing)|do\s+not\s+(?:merge|ship)|not\s+safe\s+to\s+(?:merge|ship)|regression|breaks?\s+(?:the\s+)?(?:requirement|spec|contract))\b|🚨|❌", I)


def is_reviewer_flag(s):
    u = unquoted(s)
    return bool(R_FLAG.search(u)) and not FUTURE.search(u) and not u.rstrip().endswith("?")


def is_review_role(role):  # an agent whose job is review: its warnings are flags someone should answer
    r = (role or "").lower()
    return any(k in r for k in ("review", "critic", "audit", "verif", "qa", "check"))


STOP = set("""the a an and or of to in on for by with is are be been it its this that these those as at from not no never must do don't
does unless until any all each every we i you they should will can may if then than so but into out only default by-default allowed
blocked block allow approve approval approved pending lead leadership owner use using used user users our their them there here now
also just still when which who what make made add added keep kept new rule rules treat treated has have had was were via per""".split())


def blen(s):
    return len(s.encode("utf-8"))


def terms(s):  # lower-case content words, a plural "s" removed, for matching one rule across texts
    out = []
    for w in re.split(r"[^\w-]+", s):
        w = w.strip("-").lower()
        if blen(w) < 3 or w in STOP or w.isdigit():
            continue
        for part in re.split(r"[_-]", w):
            if blen(part) < 3 or part in STOP:
                continue
            p = part[:-1] if part.endswith("s") and blen(part) - 1 >= 3 and not part.endswith("ss") else part
            if p not in out:
                out.append(p)
    return out


def overlap(rule, other):
    return sum(1 for t in rule if t in other) / len(rule) if rule else 0.0


def same_rule(a, b):  # at least half of the smaller set shared, and at least two terms
    shared = sum(1 for t in a if t in b)
    return shared >= 2 and min(len(a), len(b)) > 0 and shared * 2 >= min(len(a), len(b))


FLAG_TERMS = set(terms("high severity critical blocker blocking issue must fix fixed before merge ship violates violation violating regression "
                        "break breaks requirement spec contract safe this that problem bug one two three four five six first second both"))


RULE_IDENT = re.compile(r"""
    \b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_?(?:BLOCKED|BLOCK_?LIST|DENY_?LIST|DENIED|BANNED|EXCLUDED|EXCLUDE|PROTECTED_(?:TRAITS?|ATTRIBUTES?|CLASS(?:ES)?)|FORBIDDEN|DISALLOWED|SUPPRESSED|RESTRICTED|IGNORED)(?:_[A-Z0-9]+)*\b
  | \b(?:BLOCKED|BLOCK_?LIST|DENY_?LIST|DENIED|BANNED|EXCLUDED|PROTECTED|FORBIDDEN|DISALLOWED|SUPPRESSED|RESTRICTED|IGNORED)_[A-Z0-9_]+\b
  | \b(?:blocked|banned|excluded|forbidden|disallowed|suppressed|restricted|ignored|denied|protected)_(?:traits?|attributes?|attrs|fields?|keys|prefs|preferences|classes|categories|terms|words|users|values|features)\b
  | \b(?:block|deny|ban)_?list\b""", re.X)


def without_strings(l):  # string literals emptied, so words inside a regex or a message don't count as code
    out, q, esc = [], None, False
    for c in l:
        if q:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == q:
                q = None
                out.append(c)
        elif c in "\"'`":
            q = c
            out.append(c)
        else:
            out.append(c)
    return "".join(out)


def is_comment(l):
    return l.lstrip().startswith(("#", "//", "--", "/*", "*", '"""'))


def code_rule_line(line):  # a code line that encodes a restriction; doc comments describe code, they are not rules
    l = line.strip()
    if not l or l.startswith(("///", "//!", "/**", '"""', "*")):
        return False
    for p in ("//", "#", "--"):
        if l.startswith(p):
            c = l[len(p):]
            return is_rule(c) and (is_pending_decision(c) or bool(RULE_IDENT.search(c)))
    code = without_strings(l).split(" #")[0].split(" //")[0]
    return bool(RULE_IDENT.search(code))


def classify(path):  # what a file is to an agent (the engine's git.rs classes the intent checks need)
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[1] if "." in name else ""
    in_dir = lambda d: p.startswith(d + "/") or ("/" + d + "/") in p
    if name in ("claude.md", "claude.local.md", "agents.md", "agents.override.md", "gemini.md", ".cursorrules", ".windsurfrules",
                "copilot-instructions.md", "skill.md") or in_dir(".claude") and (ext == "md" or name in ("settings.json", "settings.local.json")) \
            or in_dir(".cursor/rules") or in_dir(".codex") or in_dir(".github/instructions") or in_dir("memory") and ext == "md":
        return "instruction"
    if name.startswith("plan") and ext == "md" or name == "todo.md" or name.startswith("design") and ext == "md" or in_dir("plans") \
            or in_dir(".plans") or name.endswith(".plan.md"):
        return "plan"
    if in_dir("test") or in_dir("tests") or in_dir("__tests__") or in_dir("spec") or in_dir("e2e") or name.startswith("test_") \
            or re.search(r"_tests?\.(go|py|rs)$|\.(test|spec)\.|tests?\.swift$", name) or in_dir("fixtures") or in_dir("testdata"):
        return "test"
    words = ("prompt", "preset", "harness", "feature-flag", "feature_flag", "flags", "policy", "policies", "blocklist", "denylist", "deny-list",
             "block-list", "allowlist", "weights", "thresholds", "guardrail", "moderation", "filters")
    if any(w in name for w in words) and ext in ("json", "yaml", "yml", "toml", "txt", "md", "jinja", "j2", "tmpl", "prompt", "ini", "csv") \
            or in_dir("prompts") or in_dir("presets") or in_dir("harnesses") or in_dir("flags"):
        return "config"
    if ext in ("md", "rst", "adoc") or in_dir("docs"):
        return "docs"
    if ext in ("rs", "py", "ts", "tsx", "js", "jsx", "mjs", "cjs", "go", "java", "kt", "swift", "rb", "php", "c", "cc", "cpp", "h", "hpp", "cs",
               "scala", "sql", "sh"):
        return "source"
    return "other"


# ---------- shell commands: scan.py's tokenizer (copied), so text inside a heredoc or a quote is never a command ----------
OPS = (";;", "&&", "||", "|&", ";", "|", "&", "(", ")")
SKIP = {"sudo", "command", "time", "nohup", "exec", "builtin", "caffeinate", "noglob", "env", "xargs",
        "then", "do", "else", "elif", "if", "while", "until", "{", "!"}
WRAPPERS = {"timeout", "gtimeout", "nice", "ionice", "stdbuf", "setsid"}
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n[\s\S]*?\n\s*\1\b")
ASSIGN = re.compile(r"[A-Za-z_]\w*=")


def tokenize(line):
    toks, cur, has, i, n = [], [], False, 0, len(line)
    while i < n:
        c = line[i]
        if c == "'" or c == '"':
            j, buf = i + 1, []
            while j < n and line[j] != c:
                if c == '"' and line[j] == "\\" and j + 1 < n and line[j + 1] in '"\\$`':
                    j += 1
                buf.append(line[j])
                j += 1
            if j >= n:
                return None
            cur.append("".join(buf)); has = True; i = j + 1
        elif c == "\\" and i + 1 < n:
            cur.append(line[i + 1]); has = True; i += 2
        elif c in " \t\n\r" or c in ";|&()":
            op = next((o for o in OPS if line.startswith(o, i)), None) if c not in " \t\n\r" else None
            if op == "&" and ("".join(cur).endswith(">") or line[i + 1:i + 2] == ">"):
                cur.append("&"); has = True; i += 1
                continue
            if has:
                toks.append("".join(cur))
            cur, has = [], False
            if op:
                toks.append(op)
            i += len(op) if op else 1
        elif c == "#" and not has:
            nl = line.find("\n", i)
            if nl < 0:
                break
            i = nl
        else:
            cur.append(c); has = True; i += 1
    if has:
        toks.append("".join(cur))
    return toks


def argvs(cmd, depth=0):
    text = HEREDOC.sub("<<HEREDOC", cmd).replace("\\\n", " ")
    whole = tokenize(text.replace("\n", "\n ; "))
    segs, out = [], []
    for toks in [whole] if whole is not None else [tokenize(l) for l in text.split("\n") if not l.strip().startswith("#")]:
        cur = []
        for t in (toks or []) + [";"]:
            if t in OPS:
                if cur and cur[0]:
                    segs.append(cur)
                cur = []
            elif t:
                cur.append(t.strip("\n"))
    for seg in segs:
        a, i = [], 0
        while i < len(seg):  # drop redirections (2>/dev/null, > out.txt)
            t = seg[i]
            r = ("<" in t or ">" in t) and re.match(r"(\d|&)?(>>?|<<?<?)(&\d?)?", t)
            i += (2 if r.end() == len(t) else 1) if r else 1
            if not r:
                a.append(t)
        while a:
            k = 0
            while k < len(a) and (ASSIGN.match(a[k]) or a[k] in SKIP or (a[k].startswith("-") and len(a) - k > 1)):
                k += 1
            if k < len(a) and a[k] in WRAPPERS:  # timeout 300 git push …, nice -n 5 rm …
                k += 1
                while k < len(a) - 1 and a[k].startswith("-"):
                    k += 2 if a[k] in ("-n", "-s", "-k", "-c", "-p", "-t", "-i", "-o", "-e") else 1
                k += 1 if a[k - 1] in ("timeout", "gtimeout") and k < len(a) and a[k][:1].isdigit() else 0
                a = a[k:]
                continue
            a = a[k:]
            break
        if len(a) >= 3 and a[0].rsplit("/", 1)[-1] in ("bash", "sh", "zsh") and a[1] in ("-c", "-lc"):
            out += argvs(a[2], depth + 1) if depth < 2 else []
        elif a:
            out.append([a[0].rsplit("/", 1)[-1]] + a[1:])
    return out


# ---------- which tool calls ran tests, and which edited files ----------
TEST_RUNNER = re.compile(r"(^|[\s;&|(])(cargo\s+(?:\+\S+\s+)?(?:test|nextest)|pytest|py\.test|python3?\s+-m\s+(?:pytest|unittest)|(?:npm|pnpm|yarn)\s+(?:run\s+)?test|bun\s+test|deno\s+test|go\s+test|jest|vitest|mocha|rspec|mvn\s+(?:\S+\s+)*test|gradlew?\s+test|swift\s+test|xcodebuild\s+(?:\S+\s+)*test|make\s+(?:check|test)|ctest|tox|phpunit|dotnet\s+test)\b", I)
TEST_SCRIPT = re.compile(r"(^|[\s;&|(])(?:python3?|node|bun|bash|sh)\s+\S*(?:\btests?/\S*|\btest_\w*|\w*_tests?)\.(?:py|js|mjs|ts|sh)\b", I)  # a test script run directly
FILTERED = re.compile(r"(\s-k\s|\s--filter[\s=]|\s-t\s|\s--grep[\s=]|\s-run[\s=]|::\w|\s--testNamePattern|\s--test-name-pattern|\s--only\b|pytest\s+(?:\S+\s+)*-m\s|cargo\s+test\s+(?:-p\s+\S+\s+)?[a-z_][\w:]*\b|\s\S*tests?/\S+\.(?:py|ts|js|rs)\b|\s\S+\.(?:test|spec)\.\w+\b)", I)
RUNNER_AT = re.compile(r"(?:(?:npx|bunx|pnpm\s+exec|uv\s+run|poetry\s+run|pipenv\s+run|hatch\s+run)\s+)?" + TEST_RUNNER.pattern[len(r"(^|[\s;&|(])"):], I)
SCRIPT_AT = re.compile(TEST_SCRIPT.pattern[len(r"(^|[\s;&|(])"):], I)
FOR_TESTS = re.compile(r"\bfor\s+(\w+)\s+in\s+[^;\n]*test[^;\n]*[;\n]\s*do\b[^;\n]*?\b(?:python3?|node|bun|bash|sh)\s+[\"']?\$\{?\1\b", I)
TESTY = re.compile(r"\b(tests?|specs?|test\s+suite|suite)\b", I)
EXCEPT = re.compile(r"\b(except|apart\s+from|other\s+than|aside\s+from|besides|save\s+for|excluding|pre-?existing|known\s+(?:failures?|issues?)|environment(?:al)?\s+(?:failures?|reasons?)|unrelated)\b|\bbut\s+(?:the\s+)?\d+", I)
BROAD = re.compile(r"\b(all|every|entire|full|whole|complete)\b|\btest\s+suite\b|\bthe\s+tests\b", I)


def command_of(tool, inp):
    t = (tool or "").lower()
    if not (t == "bash" or "shell" in t or "exec" in t or t in ("run_terminal_cmd", "terminal")) or not isinstance(inp, dict):
        return None
    c = inp.get("command") if inp.get("command") is not None else inp.get("cmd")
    return " ".join(x for x in c if isinstance(x, str)) if isinstance(c, list) else c if isinstance(c, str) else None


def test_run(cmd):  # None, or whether the run was narrowed to some tests (-k, --filter, one file or test name)
    if not (RUNNER_AT.search(cmd) or SCRIPT_AT.search(cmd) or FOR_TESTS.search(cmd)):
        return None
    out = False if FOR_TESTS.search(cmd) else None  # for t in tests/*_test.py; do python3 "$t"; done
    for a in argvs(cmd):  # each command the line runs (a heredoc's text, or `grep "cargo test"`, runs nothing)
        line = " ".join(a)
        if RUNNER_AT.match(line):
            out = bool(out) or bool(FILTERED.search(" " + line + " "))
        elif SCRIPT_AT.match(line):
            out = bool(out)  # (a test script run directly is the whole script, not a filter)
    return out


VERIFY = re.compile(r"(cargo\s+(?:build|check|clippy|fmt\s+--check)|(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:build|lint|typecheck|type-check|check|tsc)|tsc|mypy|pyright|ruff|flake8|pylint|eslint|prettier\s+--check|swift\s+build|xcodebuild|go\s+(?:build|vet)|golangci-lint|make|gradlew?\s+(?:build|check)|mvn\s+(?:\S+\s+)*(?:verify|package|compile)|dotnet\s+build|shellcheck|gh\s+(?:pr\s+checks|run\s+(?:view|watch|list))|glab\s+ci\s+(?:status|view)|python3?\s+-m\s+(?:py_compile|compileall|mypy|ruff|flake8))\b", I)


def verify_run(cmd):  # a build, lint, type check or CI status look: it backs "the build passes" or "CI is green"
    return VERIFY.search(cmd) is not None and any(VERIFY.match(" ".join(a)) for a in argvs(cmd))


def piped(cmd):  # `cargo test | grep FAILED` exits with grep's status: a failure there says nothing about the tests
    t = HEREDOC.sub("<<HEREDOC", cmd)
    m = RUNNER_AT.search(t) or SCRIPT_AT.search(t)
    return bool(m) and bool(re.search(r"(?<!\|)\|(?![|&])", re.split(r"&&|\|\||;|\n", t[m.end():])[0]))


def patch_edits(body, workdir=None):  # (path, added lines, removed lines) per file an apply_patch body touches
    at = lambda p: (workdir.rstrip("/") + "/" + p.strip()) if workdir and not p.strip().startswith("/") else p.strip()
    out = []
    for line in body.split("\n"):
        h = next((line[len(x):] for x in ("*** Update File: ", "*** Add File: ", "*** Delete File: ", "*** Move to: ") if line.startswith(x)), None)
        if h is not None:
            out.append([at(h), "", ""])
        elif out and line.startswith("+"):
            out[-1][1] += line[1:] + "\n"
        elif out and line.startswith("-"):
            out[-1][2] += line[1:] + "\n"
    return [tuple(x) for x in out]


def shell_patch(inp):  # a shell call Codex runs as apply_patch: argv, bash -lc, or `[cd dir &&] apply_patch <<'EOF'`
    cmd = inp.get("command") if inp.get("command") is not None else inp.get("cmd")
    wd = inp.get("workdir") or inp.get("working_directory")
    wd = wd if isinstance(wd, str) else None
    apply = ("apply_patch", "applypatch")
    if isinstance(cmd, list):
        a = [x for x in cmd if isinstance(x, str)]
        if len(a) == 2 and a[0] in apply:
            return a[1], wd
        if not (len(a) == 3 and a[0].rsplit("/", 1)[-1] in ("bash", "sh", "zsh") and a[1] in ("-lc", "-c")):
            return None
        cmd = a[2]
    if not isinstance(cmd, str):
        return None
    t, d = cmd.lstrip(), None
    if t.startswith("cd ") and "&&" in t:
        d, t = t[3:].split("&&", 1)
        d, t = d.strip().strip("'\""), t.lstrip()
    if re.split(r"[\s<]", t, maxsplit=1)[0] not in apply or "<<" not in t or "*** Begin Patch" not in t:
        return None
    s = t.index("*** Begin Patch")
    e = t.find("*** End Patch", s)
    d = (wd.rstrip("/") + "/" + d) if d and wd and not d.startswith("/") else d or wd
    return t[s:e + 13 if e >= 0 else len(t)], d


def edits_of(tool, inp):  # (path, added text, removed text) for each file a tool call writes
    if isinstance(inp, str) and tool in ("apply_patch", "applypatch"):
        return patch_edits(inp)
    if not isinstance(inp, dict):
        return []
    s = lambda *ks: next((inp[k] for k in ks if isinstance(inp.get(k), str) and inp[k]), "")
    if tool in ("Edit", "str_replace_editor", "str_replace_based_edit_tool"):
        return [(s("file_path", "path"), s("new_string", "new_str"), s("old_string", "old_str"))]
    if tool == "MultiEdit":
        es = [e for e in inp.get("edits") or [] if isinstance(e, dict)]
        return [(s("file_path"), "\n".join(str(e.get("new_string") or "") for e in es), "\n".join(str(e.get("old_string") or "") for e in es))]
    if tool in ("Write", "NotebookEdit", "create_file", "write_file"):
        return [(s("file_path", "path", "notebook_path"), s("content", "new_source"), "")]
    if tool in ("apply_patch", "applypatch"):
        return patch_edits(s("input", "patch"))
    sp = shell_patch(inp)
    return patch_edits(*sp) if sp else []


def added_lines(new, old):  # what an edit added: its lines that weren't there before
    before = set(l.strip() for l in old.split("\n"))
    return [l for l in new.split("\n") if l.strip() and l.strip() not in before]


def is_message_tool(tool):  # tools that send a status update to people: their text is the agent's report too
    t = (tool or "").lower()
    return any(k in t for k in ("slack", "send_message", "post_message", "chat_postmessage", "email", "teams", "discord", "notify"))


GROK_TOOLS = {"run_terminal_command": "Bash", "monitor": "Bash", "Shell": "Bash", "read_file": "Read", "search_replace": "Edit",
              "hashline_edit": "Edit", "StrReplace": "Edit", "write": "Write", "web_fetch": "WebFetch", "Fetch": "WebFetch"}
ALIASES = {"command": ("cmd", "command_line"), "file_path": ("path", "target_file", "absolute_path", "filePath"),
           "content": ("contents", "file_text"), "new_string": ("newString", "new_str")}
CWD_RX = re.compile(rb'"cwd":"((?:[^"\\]|\\.)*)"')
BLOCKED = {"claude": re.compile(r"^(?:error:\s*)?(?:command blocked|blocked by|rejected by (?:the )?user|permission requested|user (?:denied|rejected)|this (?:tool use|command) was (?:denied|blocked)|pretooluse:.*(?:block|denied))", re.I),
           "codex": re.compile(r"(?:command )?blocked by (?:\w+ )?hook|rejected by (the )?user|sandbox (denied|blocked)|not permitted by policy|blocked by (?:\w+ )?hook", re.I),
           "grok": re.compile(r"denied by (a |the )?(pretooluse )?hook|blocked by (a |the )?(\w+ )?hook|permission (was )?denied|rejected by (the )?user", re.I)}

def codex_outcome(output):
    # Only the terminal wrapper can establish process completion. Its stdout may quote a different exit code.
    if isinstance(output, str):
        parsed = jstr(output)
        if isinstance(parsed, dict):
            output = parsed
    if isinstance(output, dict):
        code = (output.get("metadata") or {}).get("exit_code") if isinstance(output.get("metadata"), dict) else None
        if type(code) is int:
            return "ran" if code == 0 else "failed"
        output = output.get("output")
    if not isinstance(output, str):
        return "unknown"
    header = re.split(r"(?im)^(?:final output|output):", output, maxsplit=1)[0].strip()
    if BLOCKED["codex"].match(header):
        return "blocked"
    m = re.search(r"(?im)^(?:process exited with code|exit code:) (-?\d+)\s*$", header)
    return ("ran" if int(m[1]) == 0 else "failed") if m else "unknown"


def jstr(t):
    try:
        return json.loads(t)
    except ValueError:
        return None


def init_worker(emails, never_open):
    EMAILS[:], NEVER_OPEN[:] = emails, never_open


# ---------- reading one session tree (in a worker process): the main session and every sub-agent it started ----------
AGENT_TOOLS = ("Agent", "Task", "SubagentHandback", "SendMessage", "TaskOutput")
HARNESS = re.compile(r"^\s*(<|\[Request interrupted|Stop hook feedback|This session's worker|Base directory for this skill|Caveat:)")


def norm_ts(ts):  # sortable across agents: 2026-11-27T20:40:00.1230Z
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?", ts or "")
    return m.group(1) + (m.group(2) or ".0").ljust(5, "0")[:5] if m else ""


class Tree:
    def __init__(self, vendor):
        self.vendor, self.agents, self.texts, self.users, self.instr = vendor, {}, [], [], []
        self.calls, self.ok, self.edits, self.spawned, self.reports, self.heard = {}, {}, [], {}, {}, {}
        self.missing, self.bytes, self.ncalls, self.start, self.end, self.cwd, self.seen = set(), 0, 0, "", "", "", set()
        self.approvals, self.read_rules = [], []  # when a tool showed an approval (a PR review); rules in what agents read

    def output(self, at, text):  # a tool's output: kept only as these two facts, never as text
        if APPROVED_OUT.search(text):
            self.approvals.append(at)
        if R_RULE.search(text):
            self.read_rules += [(at, terms(x)) for x in sentences(text[:200000]) if is_rule(x)]

    def agent(self, aid, **kw):
        a = self.agents.setdefault(aid, {"parent": None, "role": "", "desc": "", "prompt": None, "prompt_at": None, "handback": None, "hb_at": None, "sub": False})
        a.update(kw)
        return a

    def stamp(self, ts):
        if ts:
            self.end = max(self.end, ts)
            self.start = min(self.start, ts) if self.start else ts


def text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x if isinstance(x, str) else str(x.get("text", "")) for x in c if isinstance(x, (str, dict)) and (isinstance(x, str) or isinstance(x.get("text"), str)))
    return ""


def read_claude(T, path, fi, aid, sub):
    last, n, first_user = "", 0, True
    try:
        f = open(path, "rb")
    except OSError:
        return
    with f:
        for n, line in enumerate(f):
            T.bytes += len(line)
            if b'"user"' not in line and b'"assistant"' not in line and b'"attachment"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if not isinstance(o, dict) or o.get("uuid") in T.seen:
                continue  # (a record a copy of this session already gave)
            T.seen.add(o.get("uuid") or (fi, n))
            ts = o.get("timestamp") if isinstance(o.get("timestamp"), str) else ""
            T.stamp(ts)
            last = norm_ts(ts) or last
            at, ty = (last, fi, n), o.get("type")
            T.cwd = T.cwd or (o.get("cwd") if isinstance(o.get("cwd"), str) and not sub else "")
            who = aid + ":side" if o.get("isSidechain") is True and not sub else aid  # (older logs kept sub-agents in the main log)
            if who != aid:
                T.agent(who, parent=aid, sub=True, desc="sub-agent")
            if ty == "attachment":  # the instruction files the session loaded: what it was told before it started
                a = o.get("attachment") or {}
                if isinstance(a, dict) and a.get("type") in ("instructions", "nested_memory"):
                    c = a.get("content")
                    T.instr += [x for x in ([f.get("content") for f in a.get("files") or [] if isinstance(f, dict)] if a.get("type") == "instructions"
                                            else [c.get("content") if isinstance(c, dict) else c]) if isinstance(x, str)]
                continue
            if ty not in ("user", "assistant"):
                continue
            content = (o.get("message") or {}).get("content") if isinstance(o.get("message"), dict) else None
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content if isinstance(content, list) else []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and isinstance(b.get("text"), str) and b["text"].strip():
                    if ty == "assistant":
                        T.texts.append((at, who, "said", b["text"]))
                    elif not o.get("isMeta"):
                        if sub or who != aid:  # a sub-agent hears only its parent
                            a = T.agents[who]
                            if first_user and a["prompt"] is None and sub:
                                a["prompt"], a["prompt_at"] = b["text"], at
                            first_user = False
                        else:
                            T.users.append((at, b["text"], not HARNESS.match(b["text"]) and not b["text"].startswith("Another Claude session")))
                elif bt == "tool_use" and ty == "assistant":
                    T.ncalls += 1
                    cid, tool, inp = str(b.get("id") or ""), str(b.get("name") or ""), b.get("input")
                    T.calls[(who, cid)] = (at, tool, inp)
                elif bt == "tool_result" and ty == "user":
                    cid = str(b.get("tool_use_id") or "")
                    tur = o.get("toolUseResult") if isinstance(o.get("toolUseResult"), dict) else {}
                    e = b.get("is_error")
                    T.ok[(who, cid)] = None if tur.get("interrupted") is True or not isinstance(e, bool) else not e
                    call = T.calls.get((who, cid))
                    if not (call and call[1] in AGENT_TOOLS):  # (what a sub-agent reported is its own words, not something read)
                        T.output(at, text_of(b.get("content")))
                    if call and call[1] in ("Agent", "Task") and isinstance(tur.get("agentId"), str):
                        T.spawned[(who, cid)] = tur["agentId"]
                        rep = text_of(tur.get("handbackReport")) if tur.get("handbackReport") else ""
                        if rep:
                            T.reports[tur["agentId"]] = (at, who, rep)
                    elif call and call[1] == "Read" and isinstance(call[2], dict) and classify(str(call[2].get("file_path") or "")) == "instruction":
                        T.instr.append(text_of(b.get("content")))  # an instruction file as it was when an agent read it


def read_claude_tree(files):
    T = Tree("claude")
    roots = sorted((p for p in files if "/subagents/" not in p), key=lambda p: -(os.path.getsize(p) if os.path.exists(p) else 0))
    root = roots[0] if roots else None
    rid = pp.basename(root)[:-6] if root else "orphan"
    T.agent(rid)
    for i, r in enumerate(roots):
        read_claude(T, r, i, rid, False)
    for i, p in enumerate(sorted(f for f in files if f not in roots), len(roots)):
        sid = pp.basename(p)[6:-6] if pp.basename(p).startswith("agent-") else pp.basename(p)[:-6]
        try:
            meta = json.loads(read(p[:-6] + ".meta.json") or "{}")
        except ValueError:
            meta = {}
        meta = meta if isinstance(meta, dict) else {}
        T.agent(sid, sub=True, role=str(meta.get("agentType") or ""), desc=str(meta.get("description") or ""), tuid=meta.get("toolUseId"))
        read_claude(T, p, i, sid, True)
    for sid, a in T.agents.items():  # link each sub-agent to the call that started it (its meta's toolUseId)
        if not a["sub"] or a["parent"]:
            continue
        hit = next(((k, c) for k, c in T.calls.items() if k[1] == a.get("tuid")), None) or \
            next(((k, T.calls.get(k)) for k, v in T.spawned.items() if v == sid and T.calls.get(k)), None)
        if hit:
            (pa, _), (at, _, inp) = hit
            a["parent"] = pa
            if isinstance(inp, dict) and isinstance(inp.get("prompt"), str):
                a["prompt"], a["prompt_at"] = inp["prompt"], at
        else:
            a["parent"] = rid if root else None
    for sid, a in list(T.agents.items()):  # what each sub-agent reported: its handback, else its last words
        if a["sub"]:
            hb = [(at, x) for (w, cid), (at, tool, x) in T.calls.items() if w == sid and tool == "SubagentHandback"]
            hb = [(at, x.get("message")) for at, x in hb if isinstance(x, dict) and isinstance(x.get("message"), str)]
            said = [(at, t) for at, w, ch, t in T.texts if w == sid]
            got = max(hb) if hb else max(said) if said else None
            if got:
                a["hb_at"], a["handback"] = got
                if hb:
                    T.texts.append((got[0], sid, "handback", got[1]))
    for child, (at, pa, rep) in T.reports.items():  # started, but its log is missing: what the parent heard is all there is
        if child not in T.agents:
            T.missing.add(child)
            T.agent(child, parent=pa, sub=True, desc="sub-agent (log missing)", handback=rep, hb_at=at)
            T.texts.append((at, child, "handback", rep))
    return T


def read_codex_tree(files):
    T = Tree("codex")
    for fi, path in enumerate(files):
        aid, last, codes, first_user = path, "", {}, True
        try:
            f = open(path, "rb")
        except OSError:
            continue
        with f:
            for n, line in enumerate(f):
                T.bytes += len(line)
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(o, dict):
                    continue
                ts = o.get("timestamp") if isinstance(o.get("timestamp"), str) else ""
                T.stamp(ts)
                last = norm_ts(ts) or last
                at, ty = (last, fi, n), o.get("type")
                p = o.get("payload") if isinstance(o.get("payload"), dict) else {}
                if ty == "session_meta" and aid == path:
                    aid = str(p.get("id") or path)
                    src = p.get("source") if isinstance(p.get("source"), dict) else {}
                    sp = (src.get("subagent") or {}).get("thread_spawn") if isinstance(src.get("subagent"), dict) else None
                    sp = sp if isinstance(sp, dict) else {}
                    T.agent(aid, parent=sp.get("parent_thread_id"), sub=bool(sp.get("parent_thread_id")), role=str(sp.get("agent_role") or sp.get("role") or ""))
                    T.cwd = T.cwd or (p.get("cwd") if isinstance(p.get("cwd"), str) and not sp else "")
                    if isinstance(p.get("instructions"), str):
                        T.instr.append(p["instructions"])
                    continue
                a = T.agent(aid)
                if ty == "event_msg" and p.get("type") == "exec_command_end" and isinstance(p.get("exit_code"), int):
                    codes[str(p.get("call_id"))] = p["exit_code"]
                if ty != "response_item":
                    continue
                pt = p.get("type")
                if pt == "message":
                    text = text_of(p.get("content"))
                    if not text.strip():
                        continue
                    if p.get("role") == "user":
                        if text.lstrip().startswith(("# AGENTS.md instructions for", "<user_instructions>")):
                            T.instr.append(text)
                        elif not text.lstrip().startswith("<"):
                            if a["sub"]:
                                if first_user:
                                    a["prompt"], a["prompt_at"] = text, at
                                first_user = False
                            else:
                                T.users.append((at, text, True))
                    elif p.get("role") == "assistant":
                        T.texts.append((at, aid, "said", text))
                elif pt in ("function_call", "custom_tool_call", "local_shell_call"):
                    T.ncalls += 1
                    raw = p.get("arguments") if p.get("arguments") is not None else p.get("input") if p.get("input") is not None else p.get("action")
                    inp = jstr(raw) if isinstance(raw, str) else raw
                    inp = raw if inp is None else inp
                    tool = str(p.get("name") or ("local_shell" if pt == "local_shell_call" else ""))
                    T.calls[(aid, str(p.get("call_id") or p.get("id") or ""))] = (at, tool, inp)
                elif pt in ("function_call_output", "custom_tool_call_output"):
                    cid, out = str(p.get("call_id") or ""), p.get("output")
                    if "agent" not in (T.calls.get((aid, cid)) or ("", ""))[1]:
                        T.output(at, out if isinstance(out, str) else json.dumps(out))
                    oc = codex_outcome(out)
                    T.ok[(aid, cid)] = True if oc == "ran" else False if oc == "failed" else (out.get("success") if isinstance(out, dict) and isinstance(out.get("success"), bool) else None)
                    v = jstr(out) if isinstance(out, str) else out
                    call = T.calls.get((aid, cid))
                    if isinstance(v, dict) and call:
                        if call[1].endswith("spawn_agent") and isinstance(v.get("agent_id"), str):
                            T.spawned[(aid, cid)] = v["agent_id"]
                        for child, st in (v.get("status") or {}).items() if isinstance(v.get("status"), dict) else []:
                            if isinstance(st, dict) and isinstance(st.get("completed"), str):
                                T.heard[child] = (at, st["completed"])
        for k in [k for k in T.ok if k[0] == aid and k[1] in codes]:
            T.ok[k] = codes[k[1]] == 0
    for (pa, cid), child in T.spawned.items():
        if child in T.agents:
            T.agents[child]["prompt_at"] = T.agents[child]["prompt_at"] or T.calls[(pa, cid)][0]
        else:
            T.missing.add(child)
    for aid, a in T.agents.items():
        if a["sub"]:
            said = [(at, t) for at, w, ch, t in T.texts if w == aid]
            got = T.heard.get(aid) or (max(said) if said else None)
            if got:
                a["hb_at"], a["handback"] = got
    return T


def read_grok_tree(files):
    T, aid = Tree("grok"), "grok"
    T.agent(aid)
    try:
        f = open(files[0], "rb")
    except OSError:
        return T
    with f:
        for n, line in enumerate(f):
            T.bytes += len(line)
            try:
                o = json.loads(line)
            except ValueError:
                continue
            at, ty = ("", 0, n), o.get("type") if isinstance(o, dict) else None
            if ty == "user" and text_of(o.get("content")).strip():
                T.users.append((at, text_of(o.get("content")), not HARNESS.match(text_of(o.get("content")))))
            elif ty == "assistant":
                if text_of(o.get("content")).strip():
                    T.texts.append((at, aid, "said", text_of(o.get("content"))))
                for c in o.get("tool_calls") or []:
                    if isinstance(c, dict):
                        T.ncalls += 1
                        args = jstr(c["arguments"]) if isinstance(c.get("arguments"), str) else c.get("arguments")
                        args = dict(args) if isinstance(args, dict) else {}
                        for k, al in ALIASES.items():
                            args.setdefault(k, next((args[x] for x in al if args.get(x) is not None), None))
                        T.calls[(aid, str(c.get("id") or ""))] = (at, GROK_TOOLS.get(c.get("name") or "", c.get("name") or ""), args)
            elif ty == "tool_result":
                st = o.get("status")
                T.output(at, text_of(o.get("content")))
                T.ok[(aid, str(o.get("tool_call_id") or ""))] = True if st in ("completed", "success") else False if st in ("failed", "error") else None
    return T


# ---------- the checks (the engine's detect.rs, logs-only) ----------
def lineage(T, aid):  # agent ids from the main session down to this one
    out = []
    while aid and aid not in out:
        out.append(aid)
        aid = (T.agents.get(aid) or {}).get("parent")
    return out[::-1]


def below(T, aid):  # this agent and every agent it started, at any depth
    return {x for x in T.agents if aid in lineage(T, x)}


def describe(T, aid):
    a = T.agents.get(aid) or {}
    if not a.get("sub"):
        return "main session"
    d = (a.get("desc") or a.get("role") or "").strip()
    return "sub-agent" + (" \u201c%s\u201d" % mask(d, 60) if d and d != "sub-agent" else "")


APPROVED_OUT = re.compile(r"\bAPPROVED\b|reviewDecision|\bapproved\s+(?:these|this|the)\s+changes\b|\bLGTM\b")  # a PR review a tool showed
APPROVE_WORDS = re.compile(r"\b(approv\w*|lgtm|sign(?:ed)?[\s-]?off|go[\s-]ahead|ship\s+it|yes|yep|ok(?:ay)?|sure|agreed?|fine|proceed|do\s+it|confirm\w*)\b|👍", I)
REVIEW_WORDS = re.compile(r"\b(review\w*|critic|audit\w*|verif\w*|qa)\b", I)


def analyze(T):  # {check: [example]}: every finding, with its masked sentence; and the open objections
    found = {c[0]: [] for c in CHECKS}
    runs, checked = [], []
    for (aid, cid), (at, tool, inp) in T.calls.items():
        cmd = command_of(tool, inp)
        f = test_run(cmd) if cmd else None
        if f is not None:
            ok = T.ok.get((aid, cid))
            runs.append({"at": at, "agent": aid, "ok": None if ok is False and piped(cmd) else ok, "filtered": f, "cmd": cmd})
        if f is not None or cmd and verify_run(cmd):
            checked.append(at)
    runs.sort(key=lambda r: r["at"])
    edits = []
    for (aid, cid), (at, tool, inp) in sorted(T.calls.items(), key=lambda kv: kv[1][0]):
        for path, new, old in edits_of(tool, inp):
            if path:
                edits.append({"at": at, "agent": aid, "path": path, "cls": classify(path), "added": added_lines(new, old), "old": old})
        if is_message_tool(tool) and isinstance(inp, dict):
            body = next((inp[k] for k in ("text", "message", "content", "body") if isinstance(inp.get(k), str)), "")
            if body:
                T.texts.append((at, aid, "status", body))
    T.texts.sort(key=lambda x: x[0])
    humans = sorted((at, t) for at, t, h in T.users if h)

    def ex(at, aid, text, extra=""):
        return {"text": mask(text, 240), "extra": mask(extra, 160) if extra else "", "ts": at[0], "who": describe(T, aid)}

    def human_between(a, b):
        return any(a < at < b for at, _ in humans)

    claims, seen = [], set()
    for at, aid, ch, text in T.texts:
        for s in sentences(text):
            for k in claims_in(s):
                if (aid, s, k) not in seen:
                    seen.add((aid, s, k))
                    claims.append({"at": at, "agent": aid, "kind": k, "text": s})
    # 1-3: claims that checks pass, against the test runs the logs hold (D01, D02, D04)
    for c in [c for c in claims if c["kind"] == "checks"]:
        before = [r for r in runs if r["at"] < c["at"]]
        if not any(at < c["at"] for at in checked):
            if not T.missing and not any(at < c["at"] and C_CHECKS.search(unquoted(t)) for at, t, _ in T.users):
                found["unbacked_pass"].append(ex(c["at"], c["agent"], c["text"]))  # (no missing sub-agent log, no message that said so first)
            continue
        if not before or not TESTY.search(unquoted(c["text"])) or EXCEPT.search(c["text"]):
            continue  # only a report about tests is held to the test runs; one that names its exceptions disclosed them
        mine = below(T, c["agent"])  # what this agent can cite: its own runs and its sub-agents'; else the session's
        own = [r for r in before if r["agent"] in mine] or before
        last = own[-1]
        if last["ok"] is False:
            found["failed_pass"].append(ex(c["at"], c["agent"], c["text"], "last test run before it failed: " + last["cmd"][:200]))
        elif BROAD.search(c["text"]) and not any(not r["filtered"] and r["ok"] is not False for r in own) and any(r["filtered"] for r in own):
            found["narrow_pass"].append(ex(c["at"], c["agent"], c["text"], "every test run before it was narrowed; the last: " + [r for r in own if r["filtered"]][-1]["cmd"][:200]))
    # 4: approval claimed with no message of yours that gives one (D07)
    reviewers = {a for a, x in T.agents.items() if x["sub"] and (is_review_role(x["role"]) or is_review_role(x["desc"]) or (x["prompt"] or "").lower().startswith("review"))}
    for c in [c for c in claims if c["kind"] == "approval"]:
        prompt = (T.agents.get(c["agent"]) or {}).get("prompt") or ""
        if any(at < c["at"] and APPROVE_WORDS.search(t) for at, t, _ in T.users) or APPROVE_WORDS.search(prompt) or any(at < c["at"] for at in T.approvals) \
                or reviewers and REVIEW_WORDS.search(c["text"]):
            continue
        found["approval"].append(ex(c["at"], c["agent"], c["text"], "no message of yours in this session approves anything"))
    # 5: a rule an agent introduced that reached a sub-agent's prompt or an instruction file or plan (D09)
    authority = [terms(s) for t in [t for _, t, _ in T.users] + T.instr for s in sentences(t)]
    authority += [terms(s) for e in edits if e["cls"] in ("instruction", "plan") for s in sentences(e["old"])]
    rules = []
    for at, aid, ch, text in T.texts:
        rules += [{"at": at, "agent": aid, "where": ch, "text": s} for s in sentences(text) if is_rule(s)]
    for aid, a in T.agents.items():
        if a["sub"] and a["prompt"] and a["parent"]:
            rules += [{"at": a["prompt_at"] or ("", 0, 0), "agent": a["parent"], "where": "prompt", "text": s, "to": aid} for s in sentences(a["prompt"]) if is_rule(s)]
    for e in edits:
        if e["cls"] in ("instruction", "plan"):
            rules += [{"at": e["at"], "agent": e["agent"], "where": "file", "text": s, "path": e["path"]} for s in sentences("\n".join(e["added"])) if is_rule(s)]
    clusters = []
    for r in sorted(rules, key=lambda r: r["at"]):
        r["terms"] = terms(r["text"])
        if not r["terms"] or any(same_rule(a, r["terms"]) for a in authority) or any(at < r["at"] and same_rule(t, r["terms"]) for at, t in T.read_rules):
            continue  # you, an instruction file, or something an agent read before said it first
        c = next((c for c in clusters if any(same_rule(x["terms"], r["terms"]) for x in c)), None)
        c.append(r) if c is not None else clusters.append([r])
    for c in clusters:
        places = {(x["agent"], x["where"]) for x in c}
        if not any(x["where"] == "file" for x in c) and not (any(x["where"] == "prompt" for x in c) and (len({p[0] for p in places}) > 1 or len({p[1] for p in places}) > 1)):
            continue  # a rule that stayed in one message of one agent is a statement, not something that spread
        o, to = c[0], [x for x in c if x["where"] in ("file", "prompt")][-1]
        where = ("then written to " + shown(to["path"])) if to["where"] == "file" else "then in the prompt of " + describe(T, to["to"])
        found["agent_rule"].append(dict(ex(o["at"], o["agent"], o["text"], where), sev="high" if any(x["where"] == "file" for x in c) else "medium"))
    # 6: a decision marked as someone else's, then edits about it and a report that the work is done (D14)
    pend = []
    for at, aid, ch, text in T.texts:
        pend += [(at, aid, s) for s in sentences(text) if is_pending_decision(s)]
    for aid, a in T.agents.items():
        if a["sub"] and a["prompt"] and a["parent"]:
            pend += [(a["prompt_at"] or ("", 0, 0), a["parent"], s) for s in sentences(a["prompt"]) if is_pending_decision(s)]
    for e in edits:
        if e["cls"] in ("instruction", "plan"):
            pend += [(e["at"], e["agent"], s) for s in sentences("\n".join(e["added"])) if is_pending_decision(s)]
        elif e["cls"] in ("source", "config"):
            pend += [(e["at"], e["agent"], l.strip().lstrip("/#*-! ")) for l in e["added"] if is_comment(l) and is_pending_decision(l.strip().lstrip("/#*-! "))]
    done_terms = []
    for at, aid, s in sorted(pend):
        pt = terms(s)
        if any(same_rule(x, pt) for x in done_terms):
            continue
        done_terms.append(pt)
        hit = next((e for e in edits if e["at"] > at and e["cls"] in ("source", "config") and not human_between(at, e["at"]) and any(
            not is_comment(l) and overlap(pt, terms(l)) >= 0.25 and sum(1 for t in terms(l) if t in pt) >= 2 for l in e["added"])), None)
        told = hit and next((c for c in claims if c["kind"] in ("done", "checks") and c["at"] > hit["at"]), None)
        if told:
            found["open_decision"].append(ex(at, aid, s, "then %s edited %s, and %s reported it done" % (
                describe(T, hit["agent"]), shown(hit["path"]), describe(T, told["agent"]))))
    # 7: told not to make design calls, or not to touch something, then did (D15)
    cons = []
    for aid, a in T.agents.items():
        if a["sub"] and a["prompt"]:
            cons += [(a["prompt_at"] or ("", 0, 0), {aid}, s, None) for s in sentences(a["prompt"])]
    roots = [a for a, x in T.agents.items() if not x["sub"]]
    for at, t in humans:  # your own words bind the main session and every agent below it, until you write again
        nxt = next((h for h, _ in humans if h > at), None)
        cons += [(at, set().union(*[below(T, r) for r in roots]) if roots else set(), s, nxt) for s in sentences(t)]
    seen = set()
    for at, bound, s, until in cons:
        k = constraint_in(s)
        if not k:
            continue
        hits = []
        for e in edits:
            if e["agent"] not in bound or e["at"] < at or until and e["at"] > until:
                continue
            if k[0] == "decisions":
                rl = next((l for l in e["added"] if code_rule_line(l) or is_rule(l)), None) if e["cls"] in ("source", "config", "instruction", "plan") else None
                if e["cls"] == "config":
                    hits.append((e, "changed product configuration " + shown(e["path"])))
                elif rl:
                    hits.append((e, "added a restriction to %s: %s" % (shown(e["path"]), rl.strip()[:120])))
            else:
                name = e["path"].lower().rsplit("/", 1)[-1]
                if k[2]:
                    ok = any(name == f.rsplit("/", 1)[-1] and ("/" not in f or e["path"].lower().endswith("/" + f)) for f in k[2])
                else:
                    pt = terms(e["path"].replace("/", " ").replace(".", " "))
                    ok = sum(1 for t in k[1] if t in pt) >= max(1, len(k[1]) // 2)
                if ok:
                    hits.append((e, "edited " + shown(e["path"])))
        if hits and (s, hits[0][0]["agent"]) not in seen:
            seen.add((s, hits[0][0]["agent"]))
            found["constraint"].append(ex(hits[0][0]["at"], hits[0][0]["agent"], s, "; ".join(dict.fromkeys(h[1] for h in hits[:3]))))
    # 8: a review sub-agent's high-severity warning that nothing after its report answers (D16)
    later = [(at, aid, t) for at, aid, ch, t in T.texts if aid not in reviewers]
    later += [(e["at"], e["agent"], "\n".join(e["added"]) + " " + e["path"]) for e in edits]
    later += [(at, aid, cmd) for (aid, _), (at, tool, inp) in T.calls.items() for cmd in [command_of(tool, inp)] if cmd]
    later += [(at, "you", t) for at, t, _ in T.users]
    for aid in sorted(reviewers):
        a = T.agents[aid]
        if not a["handback"]:
            continue
        sents, prev = list(dict.fromkeys(sentences(a["handback"]))), False
        for i, s in enumerate(sents):
            if not is_reviewer_flag(s):
                prev = False
                continue
            if len([t for t in terms(s) if t not in FLAG_TERMS]) < 2 and i:  # "This must be fixed before merge." goes with the sentence before
                if prev:
                    continue
                s = sents[i - 1] + " " + s
            prev = True
            ft = [t for t in terms(s) if t not in FLAG_TERMS] or terms(s)  # what the warning is about, not that it is one
            need = max(2, min(3, (len(ft) + 2) // 3))
            names = [x.lower().rsplit("/", 1)[-1] for x in FILE_TOKEN.findall(s)]
            if any(at > a["hb_at"] and who != aid and (sum(1 for t in ft if t in set(terms(t2))) >= need or any(n in t2.lower() for n in names))
                   for at, who, t2 in later):
                continue
            found["reviewer_flag"].append(ex(a["hb_at"], aid, s, "from " + describe(T, aid)))
    # 9: open objections: an agent said no, or didn't do part of it, and said so (the transparent path)
    seen = set()
    for at, aid, ch, text in T.texts:
        for s in sentences(text):
            if objection_in(s) and (aid, s) not in seen:
                seen.add((aid, s))
                found["objection"].append(ex(at, aid, s))
    return found


def scan_tree(job):
    vendor, files = job
    T = {"claude": read_claude_tree, "codex": read_codex_tree, "grok": read_grok_tree}[vendor](files)
    if vendor == "grok":
        T.cwd, T.start, T.end = head_cwd(files[0], "grok")
    found = analyze(T)
    proj = project_of(T.cwd) if T.cwd else ""
    for lst in found.values():
        for x in lst:
            x.update(agent=vendor, project=proj, ts=x["ts"] or T.start)
    return {"agent": vendor, "subs": sum(1 for a in T.agents.values() if a["sub"]), "calls": T.ncalls, "bytes": T.bytes,
            "start": T.start, "end": T.end, "found": found, "missing": len(T.missing)}


# ---------- finding the logs: the same code as scan.py (copied), then grouped into session trees ----------
# ---------- finding the logs ----------
def walk(d, depth=0):
    out = []
    try:
        for e in os.scandir(d):
            if e.is_dir(follow_symlinks=False):
                out += walk(e.path, depth + 1) if depth < 6 else []
            elif e.name.endswith(".jsonl") and e.is_file():
                out.append(e.path)
    except OSError:
        pass
    return out


def subdirs(d):
    try:
        return sorted(e.path for e in os.scandir(d) if e.is_dir())
    except OSError:
        return []


def find_logs():
    logs = [(p, "claude") for p in walk(HOME + "/.claude/projects")]
    logs += [(p, "codex") for d in ("/.codex/sessions", "/.codex/archived_sessions") for p in walk(HOME + d)]
    logs += [(s + "/chat_history.jsonl", "grok") for g in subdirs(HOME + "/.grok/sessions") for s in subdirs(g)
             if os.path.isfile(s + "/chat_history.jsonl")]
    return [(p, a) for p, a in logs if not closed(p)]


def head_cwd(path, agent):  # the folder a session started in, and (Grok) its times
    if agent == "grok":
        try:
            s = json.loads(read(pp.dirname(path) + "/summary.json") or "{}")
        except ValueError:
            s = {}
        d = (s.get("info") or {}).get("cwd") or unquote(pp.basename(pp.dirname(pp.dirname(path))))
        return (d if d.startswith("/") else ""), s.get("created_at") or "", s.get("last_active_at") or s.get("updated_at") or ""
    try:
        with open(path, "rb") as f:
            for n, line in zip(range(200), f):
                if agent == "codex" and b'"session_meta"' in line[:200]:
                    return (json.loads(line).get("payload") or {}).get("cwd") or "", "", ""
                m = agent == "claude" and CWD_RX.search(line, 0, 4000)
                if m:
                    return json.loads(b'"' + m.group(1) + b'"'), "", ""
    except (OSError, ValueError):
        pass
    return "", "", ""



def trees(logs):  # [(vendor, [files])]: a Claude Code session with its sub-agents; a Codex thread with the ones it spawned
    out, claude = [], {}
    for p, a in logs:
        if a == "claude":
            m = re.match(r"(.*)/subagents/[^/]+\.jsonl$", p)  # (a resumed session can be logged in two project folders: one tree)
            claude.setdefault(pp.basename(m.group(1)) if m else pp.basename(p)[:-6], []).append(p)
        elif a == "grok":
            out.append(("grok", [p]))
    out += [("claude", sorted(v)) for k, v in sorted(claude.items())]
    meta = {}
    for p, a in logs:
        if a == "codex":
            try:
                with open(p, "rb") as f:
                    line = f.readline(1 << 20)
                o = json.loads(line) if b'"session_meta"' in line[:200] else {}
            except (OSError, ValueError):
                o = {}
            pl = o.get("payload") if isinstance(o, dict) and isinstance(o.get("payload"), dict) else {}
            src = pl.get("source") if isinstance(pl.get("source"), dict) else {}
            sp = (src.get("subagent") or {}).get("thread_spawn") if isinstance(src.get("subagent"), dict) else None
            meta[p] = (str(pl.get("id") or p), (sp or {}).get("parent_thread_id") if isinstance(sp, dict) else None)
    by_id = {i: p for p, (i, _) in meta.items()}
    top = lambda p, n=0: top(by_id[meta[p][1]], n + 1) if meta[p][1] in by_id and n < 20 else p
    groups = {}
    for p in meta:
        groups.setdefault(top(p), []).append(p)
    out += [("codex", sorted(v, key=lambda x: x != k)) for k, v in sorted(groups.items())]
    return out


# ---------- your never-open rules: the same code as scan.py (copied) ----------
# ---------- your written rules: "never delete / open / read `path`", "never run `git …`" ----------
TICK = re.compile(r"`([^`]+)`")
VERB = re.compile(r"\b(?:never|don['’]t|do not)\s+(delete|open|read)\b", re.I)
CMD_RULE = re.compile(r"\b(?:never|don['’]t|do not)\s+(?:use\s+|run\s+|do\s+)?(?:a\s+|an\s+|bare\s+)?`([^`]+)`", re.I)


def is_rule_path(t):
    return bool(re.match(r"(~/|/Users/|/home/|\$HOME/|\*\.)", t)) and not re.search(r"[\s<>{}*?](?!age$)", t[2:] if t[:2] == "*." else t)


def outermost(v):
    v = [x.rstrip("/") for x in v]
    return list(dict.fromkeys(p for p in v if not any(o != p and not o.startswith("*.") and p.startswith(o + "/") for o in v)))


def unit_paths(t):  # (never-delete paths, never-open paths) in one bullet or paragraph, clause by clause
    ticks = [(m.start(), m.group(1).strip()) for m in TICK.finditer(t)]
    spans = [(m.start(), m.end()) for m in TICK.finditer(t)]
    ends = [i for i, c in enumerate(t) if c in ";.!?" and not any(s <= i < e for s, e in spans)
            and (c == ";" or i + 1 == len(t) or t[i + 1].isspace() or t[i + 1] in ')*"')]
    dele, opn = [], []
    for m in VERB.finditer(t):
        vs, ve = m.start(), m.end()
        if any(s <= vs < e for s, e in spans):
            continue
        cs = max([i + 1 for i in ends if i < vs] or [0])
        ce = next((i for i in ends if i >= ve), len(t))
        got = [x for s, x in ticks if ve <= s < ce and is_rule_path(x)]
        if not got and ce < len(t) and t[ce] != ";" and re.match(r"\s*(it|they|that|this|these|those|its|their)\b", t[ce + 1:], re.I):
            nxt = next((i for i in ends if i > ce), len(t))
            got = [x for s, x in ticks if ce < s < nxt and is_rule_path(x)]
        before = t[cs:vs]
        if before.lstrip().lstrip("*").startswith("`") and not re.search(r"\b(but|may|can|could|freely|except|fine|ok|okay|allowed|unless)\b", before, re.I):
            got += [x for s, x in ticks if cs <= s < vs and is_rule_path(x)]
        (dele if m.group(1).lower() == "delete" else opn).extend(got)
    return outermost(dele), outermost(opn)


def md_units(text):  # headings, bullets and paragraphs; code, comments and retired sections left out
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    units, cur, fence, retired = [], None, None, False
    for i, raw in enumerate(text.split("\n")):
        s = raw.strip()
        if fence or s.startswith(("```", "~~~")):
            fence = None if fence and s.startswith(fence * 3) else fence or s[0]
            continue
        b = re.match(r"\s*([-*+]|\d+[.)])\s+(.*)", raw)
        if not s or re.match(r"#{1,6}\s", s) or b or not (cur and (cur[2] == "p" or raw[:1] in " \t")):
            units += [cur] if cur else []
            cur = None
        if not s or raw.startswith("    ") and cur is None and not b:
            continue
        if re.match(r"#{1,6}\s", s):
            retired = bool(re.search(r"\b(dropped|deprecated|retired|obsolete|no longer)\b", s, re.I))
            units += [] if retired else [[s, i, "h"]]
        elif not retired:
            if cur:
                cur[0] += " " + s
            else:
                cur = [b.group(2), i, "b"] if b else [s, i, "p"]
    return units + ([cur] if cur else [])


def expand(p):
    return HOME + p[5:] if p.startswith("$HOME") else HOME + p[1:] if p.startswith("~") else p


def parse_rules(cwds):
    def rules_dir(d):
        return sorted(pp.join(r, n) for r, _, fs in os.walk(d) for n in fs if n.endswith(".md"))[:200]

    def hidden(d):
        return not (d + "/").startswith(HOME + "/") or "/." in d[len(HOME):]
    files = [HOME + "/.claude/CLAUDE.md", HOME + "/.codex/AGENTS.md", HOME + "/.codex/AGENTS.override.md"] + rules_dir(HOME + "/.claude/rules")
    dirs = set()
    for c in {c for c in cwds if c.startswith("/")}:
        d = pp.normpath(c).rstrip("/") or "/"
        while not closed(d):  # the folder and those above it, up to home (agents read instructions from all of them)
            dirs.add(d)
            if hidden(d) or d == HOME or d == "/":
                break
            d = pp.dirname(d)
    for d in sorted(dirs, key=lambda d: (hidden(d), d)):
        files += [d + n for n in ("/CLAUDE.md", "/AGENTS.md", "/CLAUDE.local.md", "/AGENTS.override.md", "/.claude/CLAUDE.md")]
        files += rules_dir(d + "/.claude/rules") if os.path.isdir(d + "/.claude/rules") else []
    rules, seen, nread = {"no_delete": [], "no_open": [], "no_command": []}, set(), 0
    for f in dict.fromkeys(files):
        text = read(f)  # (a never-open rule read so far closes what comes after it)
        if text is None:
            continue
        nread += 1
        text = re.sub(r"<!-- excellent:shared-rules[^\n]*-->[\s\S]*?<!-- /excellent:shared-rules -->", "", text)
        scope = "" if f.startswith((HOME + "/.claude/", HOME + "/.codex/")) else re.sub(r"(/\.claude/rules|/\.claude)$", "", pp.dirname(f))
        until = -1
        for t, line, kind in md_units(text):
            if kind == "h":  # a "never delete" heading makes the next bullets never-delete paths
                until = line + 40 if re.search(r"never delete|do not delete|do-not-delete", t, re.I) else -1
                continue
            dele, opn = unit_paths(t)
            if kind == "b" and line < until:
                dele = outermost(dele + [x.strip() for x in TICK.findall(t) if is_rule_path(x.strip())])
            for k, lst in (("no_delete", dele), ("no_open", opn)):
                for p in lst:
                    if (k, scope, p) not in seen:
                        seen.add((k, scope, p))
                        rules[k].append({"path": p, "scope": scope})
                        if k == "no_open" and not p.startswith("*."):
                            NEVER_OPEN.append(fold(pp.normpath(expand(p))))
            for m in CMD_RULE.finditer(t):
                c = m.group(1).strip()
                if re.match(r"(git|rm|npm|pnpm|yarn|curl|docker|kubectl|gh|glab)\s+\S", c) and len(c) < 40 \
                        and not re.search(r"[<>{}'\"]", c) and ("c", scope, c) not in seen:
                    seen.add(("c", scope, c))
                    rules["no_command"].append({"cmd": c, "scope": scope})
    return rules, nread



# ---------- the report: scan.py's design (copied), with the intent checks ----------
CHECKS = [  # id, severity, title, score-card label (many, one), what it means, what you can do yourself
    ("failed_pass", "high", "Checks reported passing after a failed run", ("reports that checks pass, after the last run failed", "report that checks pass, after the last run failed"),
     "An agent wrote that tests or checks pass, but the last test run before that report, by it or its sub-agents, ended with an error. The report and the record disagree.",
     "Run the tests yourself and read the result before you merge or ship."),
    ("approval", "high", "Approvals claimed that no message of yours gives", ("approvals claimed that no message of mine gives", "approval claimed that no message of mine gives"),
     "An agent wrote that someone approved or signed off (\u201capproved by the lead\u201d), and no message you sent in that session gives an approval. Logs can't show approvals given elsewhere, like a review on GitHub.",
     "Check who approved it. If no one did, correct the record before anyone relies on it."),
    ("constraint", "high", "Agents did what they were told not to", ("instructions not to do something, then done", "instruction not to do something, then done"),
     "An agent was told not to make design calls, or not to touch a file, by you or by the agent that started it. Its own edits then touched that file or added a restriction.",
     "Look at those edits. Undo them, or keep them as your own decision."),
    ("reviewer_flag", "high", "Reviewer warnings with no answer", ("reviewer warnings with no answer after them", "reviewer warning with no answer after it"),
     "A review sub-agent reported a high-severity problem, and nothing the session wrote, edited or ran after that report mentions it.",
     "Read the warning. Fix it, or decide it doesn't apply."),
    ("agent_rule", "medium", "Rules an agent introduced reached other agents or files", ("rules an agent introduced, passed on", "rule an agent introduced, passed on"),
     "An agent stated a rule (\u201cnever \u2026\u201d, \u201cblock by default\u201d) that no message of yours and no instruction file it read says, then put it in a sub-agent's instructions or wrote it into CLAUDE.md, AGENTS.md or a plan. Later agents follow it as if you had decided it.",
     "Read the rule. Keep it by writing it yourself, or take it out of the prompt and the files."),
    ("open_decision", "medium", "Decisions left open, then reported done", ("decisions left open, then reported done", "decision left open, then reported done"),
     "An agent wrote that a decision was someone else's (\u201cpending approval from a lead\u201d). Later in the same session, code about it was edited and the work was reported done, with no message from you in between. The logs can't show what shipped.",
     "Make the decision yourself, then check what the code does now."),
    ("unbacked_pass", "medium", "Checks reported passing with no test run", ("reports that checks pass, with no test run before them", "report that checks pass, with no test run before it"),
     "An agent wrote that tests or checks pass, but no test command ran in that session, its sub-agents included, before it said so. Nothing in the logs backs the report.",
     "Ask for the command and its output, or run the tests yourself."),
    ("narrow_pass", "medium", "A narrow test run reported as the whole suite", ("narrow test runs reported as the whole suite", "narrow test run reported as the whole suite"),
     "An agent wrote that all the tests pass, but every test run before that was narrowed to some tests (-k, --filter, one file or one test name).",
     "Run the full suite, or ask the agent to say exactly which tests ran."),
]
GOOD = ("objection", "Agents said no openly", ("open objections: said, not hidden", "open objection: said, not hidden"),
        "An agent declined, or didn't do, part of the task and said so in its report. That is the transparent path: you can see it and decide. These are not problems.")
CHECKS.append((GOOD[0], "ok", GOOD[1], GOOD[2], GOOD[3], "Read what it said, then accept it or ask again with what you want."))
PROBLEMS = [c for c in CHECKS if c[1] != "ok"]
FULL = {  # what the full Intent check adds, for each finding (coming to Excellent for Mac; not in this free script)
    "failed_pass": "The full Intent check runs your tests itself, on the actual change, and holds the release until they pass.",
    "unbacked_pass": "The full Intent check runs your tests itself, on the actual change, so a report doesn't have to be taken on trust.",
    "narrow_pass": "The full Intent check runs the whole suite itself, on the actual change, and says what ran.",
    "approval": "In the full Intent check, only an approval you record counts. A message saying someone approved never does.",
    "agent_rule": "The full Intent check also finds the rule in the changed code, and holds the release until you approve it.",
    "open_decision": "The full Intent check compares the change with your base branch, finds where the decision shipped, and holds the release until you decide.",
    "constraint": "The full Intent check reads the actual change, not only the edits in the logs, and holds the release until you approve it.",
    "reviewer_flag": "The full Intent check holds the release until you answer every reviewer warning.",
}
DOWNLOAD = "https://www.excellent.so/download?utm_source=free-scan&utm_medium=intent-report&utm_campaign=launch"
SCAN = "https://excellent.so/scan?utm_source=free-scan&utm_medium=intent-report&utm_campaign=launch"
TIER = {"high": ("Fix now", "to fix now"), "medium": ("Review", "to review"), "low": ("Good to know", "good to know")}
AGENT_NAMES = {"claude": "Claude Code", "codex": "Codex", "grok": "Grok Build"}
MARK_D = "M76.1 0L110.7 67.2L171 21.7L140 90.7L248 109.5L140 128.3L171 197.3L110.7 151.8L76.1 219L74.1 143.4L0 158.1L57.7 109.5L0 60.9L74.1 75.6ZM110.7 0H196V219H110.7Z"
WORDS_D = ("M437.5 15.8L438.2 22.9L442.7 63.6L436 64.3C432.5 31.9 427 26.5 410.3 26.5H376.4C369.1 26.5 365.3 30.5 365.3 37"
           ".6V102.6H394.6C408.6 102.6 412.6 99.1 412.6 74.7H418.1V138.8H412.6C412.6 114.7 408.6 111.2 394.6 111.2H365.3V1"
           "80.9C365.3 192 367.2 194.4 376.4 194.4H410C427.8 194.4 434.6 187.5 444.1 151.4L450.7 153.3L439.1 198.2L437.2 2"
           "05.1H313.5V199.4C335.5 199.4 338.6 195.1 338.6 180.7V40.2C338.6 25.8 335.5 21.5 313.5 21.5V15.8H437.5ZM521 138"
           ".4L543.7 183.3C550.6 197 556.3 199.4 566.2 199.4V205.1H512V199.4C527.2 199.4 525.8 197 518.7 183.3L503.5 153.5"
           "L489.1 183.1C482.5 196.8 481.1 199.4 496.7 199.4V205.1H454.8V199.4C465.9 199.4 471.6 197 478.5 183.3L498.6 143"
           ".3L477.5 101.5C470.6 87.7 465 85.4 456 85.4V79.7H508V85.4C493.6 85.4 495.2 87.7 502.3 101.5L516.1 128.4L530 10"
           "1.5C537.1 87.7 539 85.4 524.1 85.4V79.7H563.1V85.4C553.7 85.4 547.8 87.7 540.7 101.2L521 138.4ZM608.6 208.8C58"
           "1 208.8 564.9 182.3 564.9 144.5C564.9 105.2 582.2 75.4 612.7 75.4C632.5 75.4 646 88.4 646 106.2C646 116.1 641."
           "5 122 633.5 122C626.1 122 622.4 117.1 622.4 111.2C622.4 107.1 624 102.4 624 97.4C624 89.4 619.5 85.4 612.4 85."
           "4C595.4 85.4 588.3 108.8 588.3 135.5C588.3 166.3 597.8 190.9 617.2 190.9C627.8 190.9 639.9 182.8 644.1 153H649"
           ".8C647.2 192.3 629.9 208.8 608.6 208.8ZM742.1 154.4H747.8C742.8 192.5 726.7 208.8 704.5 208.8C677.8 208.8 661 "
           "183.5 661 144.5C661 107.1 677.5 75.4 705.7 75.4C733.3 75.4 746.4 101.5 746.4 136H683.9V136.5C683.9 168.6 693.8"
           " 191.3 713.5 191.3C724.1 191.3 736.4 183.1 742.1 154.4ZM705.7 85.4C691.5 85.4 685.6 102.6 684.1 126.3H723.6C72"
           "3.6 103.6 719.6 85.4 705.7 85.4ZM796 13.5V180.7C796 195.8 798.2 199.4 812.6 199.4V205.1H756.3V199.4C770.7 199."
           "4 773.1 195.8 773.1 180.7V44C773.1 28.8 773.1 25.8 758.9 32.9L756.5 27.7L792.5 10.2L796 13.5ZM861.2 13.5V180.7"
           "C861.2 195.8 863.3 199.4 877.7 199.4V205.1H821.4V199.4C835.9 199.4 838.2 195.8 838.2 180.7V44C838.2 28.8 838.2"
           " 25.8 824 32.9L821.7 27.7L857.6 10.2L861.2 13.5ZM967.3 154.4H973C968 192.5 951.9 208.8 929.7 208.8C903 208.8 8"
           "86.2 183.5 886.2 144.5C886.2 107.1 902.7 75.4 930.9 75.4C958.5 75.4 971.5 101.5 971.5 136H909.1V136.5C909.1 16"
           "8.6 919 191.3 938.7 191.3C949.3 191.3 961.6 183.1 967.3 154.4ZM930.9 85.4C916.7 85.4 910.8 102.6 909.3 126.3H9"
           "48.8C948.8 103.6 944.8 85.4 930.9 85.4ZM984.1 205.1V199.4C997.8 199.4 1000.2 195.8 1000.2 180.7V107.8C1000.2 9"
           "2 1000.2 88.7 986 94.6L983.6 89.2L1002.5 81.6L1018.6 75L1023.1 78.5V100.3H1023.8C1034.5 85.6 1045.1 75.4 1061."
           "2 75.4C1078 75.4 1087.2 87.5 1087.2 109.7V180.7C1087.2 195.8 1089.3 199.4 1102.8 199.4V205.1H1049.8V199.4C1062"
           ".4 199.4 1064.2 195.8 1064.2 180.7V111.2C1064.2 98.1 1059.3 92 1050.3 92C1040.6 92 1032.1 98.6 1023.1 110.2V18"
           "0.7C1023.1 195.8 1025 199.4 1037.5 199.4V205.1H984.1ZM1174.5 152.1H1181.1C1181.1 189 1173.8 208.8 1150.6 208.8"
           "C1132.2 208.8 1122.5 197.7 1122.5 164.6V89.4H1105.9V80.6C1123.2 80.2 1134.1 67.4 1136.4 45.2H1145V79.7H1173.3V"
           "89.4H1145.4V158.5C1145.4 179.5 1147.6 193.5 1158.7 193.5C1169.3 193.5 1174.5 180.2 1174.5 152.1Z")
LOCKUP = ('<svg class="lockup" viewBox="0 0 1153 219" role="img" aria-label="Excellent"><path fill-rule="evenodd" d="%s"/>'
          '<path transform="translate(-28.3)" d="%s"/></svg>') % (MARK_D, WORDS_D)
MARK = '<svg class="mark" viewBox="0 0 248 219" aria-hidden="true"><path fill-rule="evenodd" d="%s"/></svg>' % MARK_D
ARROW = '<svg class="arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9.5M8.5 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
LIGHT = ("--paper:#f1f1f2;--paper2:#ebebed;--card:#fff;--ink:#111316;--ink2:#2f3237;--quiet:#676d74;--faint:#a1a6ac;--rule:#0000000f;"
         "--fill:#f5f5f6;--fill2:#0000000d;--accent:#3d7bd9;--ok:#2e9457;--hi:#c9301f;--hi-bg:#c9301f14;--md:#b26b0e;--md-bg:#d9a44124;"
         "--edge:#00000013;--btn:#111316;--on-btn:#fff;--shadow:0 1px 2px #0000000a,0 8px 24px -12px #0000001f")
# The Mac app's look (excellent-watch Theme.swift; the site's home demo): a light grey or graphite canvas, panels with a
# hairline edge and 12 px corners, Inter for the interface, a display serif for page titles, pill buttons, and severity
# drawn as the app draws it (octagon, triangle, info) in red, amber and grey.
CSS = """:root{color-scheme:light dark;""" + LIGHT + """;
--serif:Fraunces,"New York",ui-serif,"Iowan Old Style",Georgia,serif;--sans:Inter,-apple-system,BlinkMacSystemFont,system-ui,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Monaco,monospace}
@media screen and (prefers-color-scheme:dark){:root{--paper:#1b1c1f;--paper2:#161719;--card:#232428;--ink:#ececee;--ink2:#c9cace;--quiet:#9b9ca2;
--faint:#75767c;--rule:#ffffff12;--fill:#2a2b2f;--fill2:#ffffff14;--accent:#5ea0ff;--ok:#3f9f62;--hi:#ef5b4f;--hi-bg:#ef5b4f1f;--md:#d9a441;--md-bg:#d9a4411f;
--edge:#ffffff13;--btn:#f4f4f5;--on-btn:#151517;--shadow:0 1px 2px #0000004d,0 16px 40px -20px #000000b3}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 var(--sans);-webkit-font-smoothing:antialiased;overflow-wrap:anywhere}
h1,h2,h3,p,ul,dl,dd{margin:0}ul{padding:0;list-style:none}svg{display:block;fill:currentColor}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--fill2);text-underline-offset:3px}a:hover{text-decoration-color:currentColor}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
code{font:12px/1.55 var(--mono);color:var(--ink2);word-break:break-all}
.wrap{max-width:920px;margin:0 auto;padding:0 clamp(16px,4vw,32px)}
.top{position:sticky;top:0;z-index:2;background:color-mix(in srgb,var(--paper) 86%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--rule)}
.top .wrap,footer .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px 24px;flex-wrap:wrap}
.top .wrap{min-height:52px}.lockup{flex:none;height:18px;width:auto;aspect-ratio:1153/219}.nw{white-space:nowrap}
.label{font:600 11px/1.3 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--quiet)}
.hero{padding:clamp(32px,6vw,56px) 0 22px}
h1{font:600 clamp(30px,4.6vw,40px)/1.1 var(--serif);letter-spacing:-.015em;text-wrap:balance}
.lede{margin-top:10px;max-width:42em;font-size:15px;line-height:1.6;color:var(--quiet);text-wrap:pretty}
.si{display:inline-block;flex:none;width:16px;height:16px;vertical-align:-3px}.si .g{fill:var(--card)}.si.high{color:var(--hi)}.si.medium{color:var(--md)}.si.low{color:var(--faint)}.si.ok{color:var(--ok)}
.score{margin:0}
.score-in{display:flex;flex-direction:column;gap:18px;padding:clamp(18px,3vw,26px);border:1px solid var(--edge);border-radius:12px;background:var(--card);box-shadow:var(--shadow)}
.score .lockup{align-self:flex-start;height:16px}.score h2{font:600 clamp(20px,2.8vw,26px)/1.2 var(--serif);letter-spacing:-.01em;text-wrap:balance}.sub{display:block;margin-top:2px;font:400 14px/1.5 var(--sans);color:var(--quiet)}.sep{display:none}
.need{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:13.5px;color:var(--quiet)}.need span{display:inline-flex;align-items:center;gap:7px}.need b{color:var(--ink);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
.tile{position:relative;display:flex;flex-direction:column;padding:12px 14px 13px;border:1px solid var(--edge);border-radius:10px;background:var(--fill);font-size:12.5px;line-height:1.35;color:var(--quiet)}
.tile b{display:block;margin-bottom:6px;font:600 26px/1.1 var(--sans);letter-spacing:-.02em;color:var(--ink);font-variant-numeric:tabular-nums}
.tile .si{position:absolute;top:13px;right:12px}.tile.ok b{color:var(--quiet)}
.tile em{display:block;margin-top:auto;padding-top:8px;font:600 10.5px/1.2 var(--sans);font-style:normal;letter-spacing:.05em;text-transform:uppercase}.tile.high em{color:var(--hi)}.tile.medium em{color:var(--md)}.tile.low em{color:var(--quiet)}
.foot{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 24px;padding-top:14px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--quiet)}
.foot small{font-size:inherit}.foot a,.btn,.btn2{display:inline-flex;align-items:center;gap:7px;text-decoration:none;white-space:nowrap}.foot a{font-weight:600;color:var(--ink)}.arrow{width:14px;height:14px}
.share{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;margin-top:14px;font-size:12.5px;line-height:1.5;color:var(--quiet)}.share span{flex:1;min-width:18em}
.btn2{height:30px;padding:0 13px;border-radius:99px;background:var(--fill);box-shadow:inset 0 0 0 1px var(--edge);font:600 12.5px/1 var(--sans);color:var(--ink)}.btn2:hover{background:var(--fill2)}
[hidden]{display:none!important}
.tools{margin-top:12px;padding:16px 18px;border:1px solid var(--edge);border-radius:12px;background:var(--card)}.tools .row{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
button.btn2{border:0;cursor:pointer}button.btn2:disabled{opacity:.6;cursor:progress}.hint{margin-top:6px;font-size:12.5px;line-height:1.5;color:var(--quiet)}
#lnk{display:block;margin-top:8px;font-size:11px;color:var(--quiet)}#vid{display:block;width:100%;max-width:640px;margin-top:12px;border-radius:8px}
.sec{padding-top:clamp(40px,6vw,64px)}.head{margin-bottom:18px}
.sec h2,.cta h2{margin-top:6px;font:600 clamp(24px,3.4vw,30px)/1.15 var(--serif);letter-spacing:-.012em;text-wrap:balance}
.pill{display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:6px;box-shadow:inset 0 0 0 1px var(--edge);font:600 10.5px/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;color:var(--quiet)}
.label .pill{margin-left:8px;vertical-align:1px}
.tgroup{display:flex;align-items:baseline;gap:6px;margin:28px 0 8px;font-size:14px}.tgroup:first-child{margin-top:4px}.tgroup h3{font:600 14px/1.3 var(--sans);color:var(--ink)}.tgroup .c{color:var(--quiet)}.tgroup p{margin-left:auto;font-size:12.5px;color:var(--quiet)}
.find{margin:0 0 10px;border:1px solid var(--edge);border-radius:12px;background:var(--card);box-shadow:var(--shadow)}
.find summary{display:grid;grid-template-columns:auto 1fr auto;grid-template-areas:"i t n" "i s n";gap:4px 12px;align-items:center;padding:16px 18px;cursor:pointer;list-style:none}
.find summary::-webkit-details-marker{display:none}.find summary>.si{grid-area:i;align-self:start;width:20px;height:20px;margin-top:1px}
.find h3{grid-area:t;font:600 15px/1.35 var(--sans);letter-spacing:-.005em}
.n{grid-area:n;font:600 22px/1 var(--sans);letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.sev{grid-area:s;justify-self:start;display:inline-flex;align-items:center;height:20px;padding:0 7px;border-radius:6px;font:600 10.5px/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;box-shadow:inset 0 0 0 1px var(--edge);color:var(--quiet)}
.sev i{display:none}.high .sev{color:var(--hi);background:var(--hi-bg);box-shadow:none}.medium .sev{color:var(--md);background:var(--md-bg);box-shadow:none}
.fb{display:grid;gap:14px;padding:0 18px 18px 50px}.what{padding-top:14px;border-top:1px solid var(--rule);color:var(--ink2)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px 28px}.pair dt{margin-bottom:4px}.pair dd{font-size:13.5px;line-height:1.55;color:var(--quiet)}
.mark{flex:none;width:16px;height:14px;margin-top:2px}
.fix{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 20px;padding:14px 16px;border:1px solid var(--edge);border-radius:10px;background:var(--fill)}
.fix .ft{display:flex;gap:11px;align-items:flex-start;flex:1;min-width:16em}.fix b{display:block;font:600 13.5px/1.4 var(--sans)}.fix span{display:block;margin-top:1px;font-size:13px;line-height:1.5;color:var(--quiet)}
.btn{min-height:32px;padding:0 15px;border-radius:99px;background:var(--btn);color:var(--on-btn);font:600 13px/1 var(--sans)}.btn:hover{opacity:.88}
.exs .label{margin-bottom:6px}
.ex{display:grid;gap:6px}.ex li{padding:9px 11px;border-radius:8px;background:var(--fill)}.ex small{display:block;margin-top:3px;font-size:11.5px;color:var(--quiet)}
.cleanbox{margin-top:22px}.cleanbox .label{margin-bottom:8px}.clean{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));overflow:hidden;border:1px solid var(--edge);border-radius:12px;background:var(--card)}
.clean li{display:flex;align-items:center;gap:10px;min-height:40px;padding:0 14px;border-bottom:1px solid var(--rule);font-size:13.5px;color:var(--ink2)}
.clean li:before{content:"";flex:none;width:9px;height:5px;margin:-3px 3px 0;border:solid var(--ok);border-width:0 0 1.8px 1.8px;transform:rotate(-45deg)}
.clean.na li:before{border:0;width:9px;height:1.8px;margin:0 3px;background:var(--faint);transform:none}
.cta{margin-top:clamp(48px,7vw,72px);padding:clamp(22px,4vw,36px);border-radius:14px;background:#1b1c1f;color:#ececee;
box-shadow:0 0 0 1px #ffffff17,0 1px 0 #ffffff0f inset,0 30px 80px -30px #00000099}
.cta .lede{max-width:36em;color:#9b9ca2}.go{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;margin-top:22px}.go .fine{margin:0;max-width:26em}.cta .label{display:flex;align-items:center;gap:9px;color:#9b9ca2}.cta .mark{margin:0;color:#f2f2f3}
.cta .btn{min-height:38px;padding:0 18px;background:#f4f4f5;color:#151517;font-size:14px}
.fine{margin-top:12px;font-size:12.5px;line-height:1.5;color:#9b9ca2}.tiers{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:28px}
.tiers li{padding:16px 18px;border:1px solid #ffffff13;border-radius:12px;background:#232428}
.tiers b{display:block;margin:10px 0 4px;font:600 15px/1.3 var(--sans);color:#f4f4f5}.tiers p{font-size:13px;line-height:1.55;color:#9b9ca2}.tiers p+p{margin-top:6px}.tiers .req{grid-column:1/-1;padding:2px 2px 0;border:0;background:none}.tiers .req p{font-size:12.5px}
.cta .pill{color:#c9cace;box-shadow:inset 0 0 0 1px #ffffff24}.pill.solid{background:#f4f4f5;color:#151517;box-shadow:none}
.method{display:grid;grid-template-columns:1fr 1fr;gap:12px}.method>div{padding:16px 18px;border:1px solid var(--edge);border-radius:12px;background:var(--card)}.method h3{margin-bottom:4px;font:600 13.5px/1.4 var(--sans)}.method p{font-size:13px;line-height:1.6;color:var(--quiet)}
footer{margin-top:clamp(48px,7vw,72px);border-top:1px solid var(--rule)}footer .wrap{padding-top:20px;padding-bottom:36px;font-size:12.5px;color:var(--quiet)}footer .lockup{height:15px}
.back{display:none}body:has(#card:target) :is(.top,footer),body:has(#card:target) main>:not(#card):not(.back){display:none}
body:has(#card:target) main{max-width:1264px;padding:24px 32px}body:has(#card:target) .back{display:inline-block;margin-bottom:12px;font-size:13px;color:var(--quiet)}
#card:target{display:flex;width:1200px;max-width:100%;aspect-ratio:16/9;padding:32px;border-radius:16px;background:var(--paper2)}#card:target .score-in{flex:1;justify-content:space-between;gap:0;padding:36px 44px 30px}
#card:target .lockup{height:22px}#card:target h2{font-size:36px;line-height:1.14}#card:target .need{margin:0;font-size:18px}#card:target .grid{gap:10px}
#card:target .tile{padding:16px 18px 18px;font-size:14.5px}#card:target .tile b{font-size:40px;margin-bottom:10px}#card:target .foot{padding-top:16px;font-size:15px}
@media (max-width:900px){#card:target{aspect-ratio:auto;padding:12px}#card:target .score-in{padding:24px}#card:target h2{font-size:28px}
#card:target .grid{grid-template-columns:1fr 1fr}#card:target .tile b{font-size:32px}}
@media (max-width:860px){.grid{grid-template-columns:1fr 1fr}}
@media (max-width:700px){.pair,.method,.tiers{grid-template-columns:1fr}.fb{padding:0 16px 16px}.find summary{padding:14px 16px}.top .label{display:none}.tgroup p{display:none}}
@media print{:root{""" + LIGHT + """}body{font-size:12px;background:#fff}.top{position:static}.share,.back,.tools{display:none}.find,.score-in,.method>div{box-shadow:none}
.grid{grid-template-columns:repeat(5,minmax(0,1fr))}.score,.cta,.method>div,.ex li,.find summary,.pair,.fix{break-inside:avoid}.find summary,.head{break-after:avoid}.si,.sev,.tile em{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.cta{background:none;color:var(--ink);box-shadow:none;border:1px solid var(--edge)}.cta :is(.label,.lede,.fine,.tiers p){color:var(--quiet)}.tiers b{color:var(--ink)}.tiers li{background:none;border-color:var(--edge)}
.btn{border:1px solid var(--ink);background:none;color:var(--ink)}.btn:after{content:": excellent.so/download"}.pill.solid{border:1px solid var(--ink)}}"""
# the app's severity marks (Shared.swift Severity.symbol: exclamationmark.octagon.fill, .triangle.fill, info.circle.fill)
ICON = {
    "high": '<svg class="si high" viewBox="0 0 16 16" aria-hidden="true"><path d="M5.3 1h5.4L15 5.3v5.4L10.7 15H5.3L1 10.7V5.3z"/><path class="g" d="M7.2 4h1.6l-.25 5.2h-1.1zM8 10.4a.95.95 0 1 1 0 1.9.95.95 0 0 1 0-1.9z"/></svg>',
    "medium": '<svg class="si medium" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.2c.4 0 .77.2.97.56l6.2 10.9c.42.75-.12 1.64-.97 1.64H1.8c-.85 0-1.39-.9-.97-1.64l6.2-10.9c.2-.36.57-.56.97-.56z"/><path class="g" d="M7.25 5h1.5l-.23 4.6H7.48zM8 10.6a.9.9 0 1 1 0 1.8.9.9 0 0 1 0-1.8z"/></svg>',
    "low": '<svg class="si low" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7"/><path class="g" d="M7.3 7h1.4v4.8H7.3zM8 4a.9.9 0 1 1 0 1.8A.9.9 0 0 1 8 4z"/></svg>',
    "ok": '<svg class="si ok" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7"/><path class="g" d="M6.9 10.9 4.3 8.3l1-1 1.6 1.6 3.8-3.8 1 1z"/></svg>',
}
CSS += """
.find.ok .sev{color:var(--ok)}.tile.ok.good b{color:var(--ink)}.tile.good em{color:var(--ok)}.ex li .x{display:block;margin-top:4px;font-size:12px;color:var(--ink2)}"""


def fmt(n):
    return "{:,}".format(n)


def plural(k, one, many=None):  # "1 session", "2 sessions"
    return "%s %s" % (fmt(k), one if k == 1 else many or one + "s")


def day(ts):
    try:
        return datetime.strptime(ts[:10], "%Y-%m-%d").strftime("%b %-d")
    except ValueError:
        return ""


def project_of(cwd):  # a label for the report: your account name shows as ‹you› even in a project's name
    c = shown(cwd)
    m = re.match(r"~/(?:(?:sites|code|src|dev|developer|projects|repos|git|github|work|workspace)/)*([^/]+)", c, re.I)  # past folders that hold projects
    return m.group(1) if m else "temp" if re.match(r"(/private)?/tmp|/var/folders", c) else "home" if c == "~" else c[:40]


def label(c, n):
    return c[3][1] if n == 1 else c[3][0]


def tiers(f):  # [(severity, checks that fired at it)], highest first
    return [(v, n) for v in ("high", "medium", "low") for n in [sum(1 for c in PROBLEMS if f.get(c[0]) and f[c[0]]["severity"] == v)] if n]


def tier_text(f):
    good = f.get("objection", {}).get("count", 0)
    parts = ["%d %s" % (n, TIER[v][1]) for v, n in tiers(f)] or ["All %d checks clean" % len(PROBLEMS)]
    return " \u00b7 ".join(parts + (["%s said openly" % plural(good, "objection")] if good else []))


def summary(f, meta):  # the block your agent shows you: agent names, counts and dates only, nothing from your files
    head = " \u00b7 ".join(filter(None, ["Excellent free Intent scan", meta["agents"], meta["span"], plural(meta["sessions"], "session")]))
    rows = ["  %-56s %5s" % (c[2], fmt(f[c[0]]["count"]) if c[0] in f else "0") for c in CHECKS]
    return "\n".join([head, tier_text(f)] + rows + ["More free checks: excellent.so/scan"])


def render(f, meta):
    e = lambda s: html.escape(shown(s))
    def tile(c):  # scan.py's tiles: a check that fired shows its tier; one that didn't is a quiet 0
        x = f.get(c[0])
        if not x:
            return '<div class="tile ok"><b>0</b>%s</div>' % e(label(c, 0))
        sev = x["severity"]
        return '<div class="tile %s">%s<b>%s</b>%s<em>%s</em></div>' % ("ok good" if sev == "ok" else sev, ICON[sev], fmt(x["count"]), e(label(c, x["count"])),
                                                                  "Said openly" if sev == "ok" else TIER[sev][0])
    shown_order = sorted(PROBLEMS, key=lambda c: (c[0] not in f, ["high", "medium", "low"].index(f[c[0]]["severity"] if c[0] in f else c[1])))
    tiles = "".join(tile(c) for c in shown_order + [CHECKS[-1]])

    def card(c, x):
        ex = "".join("<li><code>%s</code>%s<small>%s</small></li>" % (e(s["text"]), '<span class="x">%s</span>' % e(s["extra"]) if s["extra"] else "", e(" \u00b7 ".join(filter(None, [
            AGENT_NAMES[s["agent"]], s["who"], day(s["ts"]), s["project"]])))) for s in x["examples"])
        sev = x["severity"]
        fix = '<div class="fix"><div class="ft">%s<p><b>Coming to Excellent for Mac</b><span>%s</span></p></div><a class="btn" href="%s">Get Excellent for Mac%s</a></div>' % (
            MARK, e(FULL[c[0]]), html.escape(DOWNLOAD + "&utm_content=" + c[0]), ARROW) if c[0] in FULL else ""
        return ('<details class="find %s" open><summary>%s<span class="sev">%s</span><h3>%s</h3><span class="n">%s</span></summary>'
                '<div class="fb"><p class="what">%s</p><dl class="pair"><div><dt class="label">What this means</dt><dd>%s</dd></div>'
                '<div><dt class="label">What to do</dt><dd>%s</dd></div></dl>%s%s</div></details>\n') % (
                sev, ICON[sev], "Said openly" if sev == "ok" else TIER[sev][0], e(c[2]), fmt(x["count"]), e(x["detail"]), e(c[4]), e(c[5]), fix,
                '<div class="exs"><p class="label">Recent examples</p><ul class="ex">%s</ul></div>' % ex if ex else "")
    cards, group = "", None
    for c in sorted([c for c in PROBLEMS if c[0] in f], key=lambda c: ["high", "medium", "low"].index(f[c[0]]["severity"])):
        if f[c[0]]["severity"] != group:
            group = f[c[0]]["severity"]
            cards += '<div class="tgroup"><h3>%s</h3><span class="c">%d</span><p>%s</p></div>\n' % (TIER[group][0], dict(tiers(f))[group], {
                "high": "Check these first.", "medium": "Worth checking before you rely on the work.", "low": "Check they were meant."}[group])
        cards += card(c, f[c[0]])
    good = card(CHECKS[-1], f["objection"]) if "objection" in f else '<p class="lede">No agent declined part of a task in these logs.</p>'
    clean = "".join("<li>%s</li>" % e(c[2]) for c in PROBLEMS if c[0] not in f)
    m = {k: e(fmt(v) if isinstance(v, int) else v) for k, v in meta.items()}
    title = e("My %s" % (meta["agents"] if meta["sessions"] else "AI agent"))
    sub = e("%s, %s%s" % (plural(meta["sessions"], "session"), plural(meta["subs"], "sub-agent"), ", " + meta["span"] if meta["span"] else ""))
    need = "".join('<span class="%s">%s<b>%d</b> %s</span>' % (v, ICON[v], n, TIER[v][1]) for v, n in tiers(f)) or '<span class="ok">%s<b>All %d checks clean</b></span>' % (ICON["ok"], len(PROBLEMS))
    if "objection" in f:
        need += '<span class="ok">%s<b>%d</b> said openly</span>' % (ICON["ok"], f["objection"]["count"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>Your agents' intent check · Excellent</title>
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap">{LOCKUP}<span class="label">Free Intent check · {m['date']}</span></div></header>
<main class="wrap"><a class="back" href="#">← Back to the full report</a>
<section class="hero"><h1>Did your agents report what they did?</h1><p class="lede">What your AI coding agents said, set against what their own logs show they did, read on {m['date']}. It counts what was unauthorized or undisclosed, never why an agent did it. This script showed your agent only a short summary: counts, agent names, dates and where this page is. Nothing else it read left this Mac.</p></section>
<section class="score" id="card"><div class="score-in">{LOCKUP}<h2>{title} <span class="nw">intent check</span><span class="sub"><span class="sep"> · </span>{sub}</span></h2><p class="need">{need}</p>
<div class="grid">{tiles}</div><div class="foot"><small>{e(plural(meta['calls'], 'agent action'))} · Free Intent check by Excellent</small><a href="{html.escape(SCAN)}">More free checks: excellent.so/scan{ARROW}</a></div></div></section>
<p class="share"><a class="btn2" href="#card">Show only the card{ARROW}</a><span>Sized for a screenshot: the card holds counts, agent names and dates only. This version has no share link. Everything below is just for you.</span></p>
<section class="sec" id="found"><div class="head"><p class="label">Just for you <span class="pill">Private</span></p><h2>What we found</h2><p class="lede">Each one is a place where what an agent reported and what its logs record don't match, or where something was decided that you didn't decide. Each says what the logs show and what you can do. Examples are masked: emails and keys are hidden.</p></div>
{cards or '<p class="lede">Nothing to flag. What your agents reported matches what their logs record, on every check.</p>'}
{'<div class="cleanbox"><p class="label">Came back clean</p><ul class="clean">%s</ul></div>' % clean if clean else ''}</section>
<section class="sec" id="open"><div class="head"><p class="label">The transparent path</p><h2>Said openly</h2><p class="lede">When an agent won't do part of a task, the good outcome is that it says so and you decide. These are those moments.</p></div>
{good}</section>
<section class="cta" id="mac"><div><p class="label">{MARK}Excellent for Mac</p><h2>Check the change, not only the logs</h2><p class="lede">This page reads what your agents wrote. The full Intent check, coming to Excellent for Mac, also checks the work itself before it ships.</p>
<div class="go"><a class="btn" href="{html.escape(DOWNLOAD)}">Get Excellent for Mac{ARROW}</a><p class="fine">Scanning with Excellent for Mac is free today. The Intent check is being built into it.</p></div></div>
<ul class="tiers"><li><span class="pill">Coming</span><b>The change against your base branch</b><p>It compares what the change does with what your base branch does, and finds behavior that changed with nothing saying so.</p></li>
<li><span class="pill">Coming</span><b>Your protected checks, run by Excellent</b><p>It runs the checks you choose itself, sandboxed, on the actual change, so a report that tests pass is never taken on trust.</p></li>
<li><span class="pill">Coming</span><b>A release gate</b><p>It holds a release until you answer each open decision, reviewer warning and rule an agent introduced, and records what you approved.</p></li>
<li class="req"><p>For Macs with Apple silicon and macOS 14 or later.</p></li></ul></section>
<section class="sec" id="how"><div class="head"><p class="label">Method and privacy</p><h2>It all ran on your Mac</h2><p class="lede">This page sends nothing and loads nothing: it has no script. The script printed a short summary for your agent.</p></div><div class="method">
<div><h3>How this check worked</h3><p>The script read {e(plural(meta['sessions'], 'session'))} with {e(plural(meta['subs'], 'sub-agent'))} ({m['gb']} of logs) in {m['secs']}. It read each session with the sub-agents it started, set what each agent wrote (its reports, its sub-agents' instructions, the files it edited) against the test runs, edits and messages in those logs, and kept a sentence only when its wording is unambiguous: questions, plans, negations, hedges, quoted text and other people's words are left out.</p></div>
<div><h3>What it never did</h3><p>It used no network and changed no file except this page. It kept no key or email, and never opened Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos data or app containers in Library, other drives, or a folder your rules name as never to open or read, once it had read that rule. It reports what was unauthorized or undisclosed, never why.</p></div>
<div><h3>Limits</h3><p>Logs go back only as far as your agents keep them (Claude Code: 30 days unless you change it). It sees only what the logs record: an approval given elsewhere, or a test run outside these sessions, doesn't show. Wording it can't read for sure is left out, so it misses some. The rules are the Excellent app's intent rules, logs-only, so counts can differ from the full check.</p></div>
<div><h3>To delete this page</h3><p><code>rm ~/excellent-free-scan/intent-report.html</code></p></div></div></section></main>
<footer><div class="wrap">{LOCKUP}<span>A free check by Excellent · {m['date']}</span></div></footer></body></html>"""


DETAIL = {  # what was found, for one and for many
    "failed_pass": ("1 report that checks pass came after the last test run before it had failed.",
                    "%s reports that checks pass came after the last test run before each had failed."),
    "unbacked_pass": ("1 report that checks pass had no test run before it in its session.", "%s reports that checks pass had no test run before them in their session."),
    "narrow_pass": ("1 report that the whole suite passes came after test runs that were all narrowed.",
                    "%s reports that the whole suite passes came after test runs that were all narrowed."),
    "approval": ("1 report claims an approval that no message of yours in that session gives.", "%s reports claim approvals that no message of yours in those sessions gives."),
    "agent_rule": ("1 rule an agent introduced reached a sub-agent's instructions, an instruction file or a plan.",
                   "%s rules agents introduced reached sub-agents' instructions, instruction files or plans."),
    "open_decision": ("1 decision an agent marked as someone else's was then edited and reported done.",
                      "%s decisions agents marked as someone else's were then edited and reported done."),
    "constraint": ("1 instruction not to do something was followed by edits that did it.", "%s instructions not to do something were followed by edits that did it."),
    "reviewer_flag": ("1 warning from a review sub-agent had nothing after it that answers it.", "%s warnings from review sub-agents had nothing after them that answers them."),
    "objection": ("1 objection was said openly.", "%s objections were said openly."),
}


def detail(rid, n):
    one, many = DETAIL[rid]
    return one if n == 1 else many % fmt(n)


def run(args):
    t0 = time.time()
    EMAILS[:] = owner_emails([args[i + 1] for i, a in enumerate(args[:-1]) if a == "--email"])
    logs = find_logs()
    parse_rules([head_cwd(p, a)[0] for p, a in logs if "/subagents/" not in p])  # never-open rules close what they name
    jobs = [(v, [p for p in fs if not closed(p)]) for v, fs in trees([(p, a) for p, a in logs if not closed(p)])]
    jobs = sorted([j for j in jobs if j[1]], key=lambda j: -sum(os.path.getsize(p) if os.path.exists(p) else 0 for p in j[1]))
    try:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max(1, min(8, (os.cpu_count() or 2) - 1)), initializer=init_worker, initargs=(list(EMAILS), list(NEVER_OPEN))) as ex:
            results = list(ex.map(scan_tree, jobs, chunksize=2))
    except Exception:  # no process pool in some sandboxes: one session at a time
        results = [scan_tree(j) for j in jobs]
    f = {}
    for c in CHECKS:
        evs = [x for r in results for x in r["found"][c[0]]]
        if evs:
            evs.sort(key=lambda x: x["ts"], reverse=True)
            seen, ex = set(), []
            for x in evs:
                if x["text"][:80] not in seen and len(ex) < 3:
                    seen.add(x["text"][:80])
                    ex.append(x)
            sev = "ok" if c[1] == "ok" else min((x.get("sev", c[1]) for x in evs), key=["high", "medium", "low"].index)
            f[c[0]] = {"count": len(evs), "detail": detail(c[0], len(evs)), "examples": ex, "severity": sev}
    days = sorted(d[:10] for r in results for d in (r["start"], r["end"]) if re.match(r"\d{4}-\d\d-\d\d", d))
    meta = {"date": datetime.now().strftime("%B %-d, %Y"), "sessions": len(results), "subs": sum(r["subs"] for r in results),
            "calls": sum(r["calls"] for r in results), "span": "%s \u2013 %s" % (day(days[0]), day(days[-1])) if days else "",
            "agents": " + ".join(AGENT_NAMES[a] for a in AGENT_NAMES if any(r["agent"] == a for r in results)) or "no agent logs found",
            "secs": plural(round(time.time() - t0), "second"), "gb": "%.1f GB" % (sum(r["bytes"] for r in results) / 1e9)}
    return f, meta, results


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else HOME + "/excellent-free-scan/intent-report.html"
    f, meta, _ = run(args)
    os.makedirs(pp.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(f, meta))
    print("Read %s with %s (%s of logs) in %s." % (plural(meta["sessions"], "session"), plural(meta["subs"], "sub-agent"), meta["gb"], meta["secs"]))
    print("Report: " + shown(out))  # ~/excellent-free-scan/intent-report.html: your account name stays out of the chat
    print("\n" + summary(f, meta))


if __name__ == "__main__":
    main()
# EXCELLENT-FREE-INTENT-SCAN-END
````
