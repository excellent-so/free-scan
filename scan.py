#!/usr/bin/env python3
# Excellent free scan 1.0 (excellent.so): a read-only check of what your AI coding agents did, from their own logs.
# Reads:  agent logs in ~/.claude/projects, ~/.codex/sessions, ~/.codex/archived_sessions, ~/.grok/sessions; the
#         CLAUDE.md, AGENTS.md, CLAUDE.local.md and .claude/rules files of the folders agents worked in and the folders
#         above them up to your home folder, plus ~/.claude/CLAUDE.md, ~/.claude/rules and ~/.codex/AGENTS.md; hook
#         settings in ~/.claude/settings.json and ~/.codex/hooks.json; your email from ~/.claude.json and
#         `git config --global user.email` (what to look for).
# Writes: one file, ~/excellent-free-scan/report.html. No network. Prints only a short summary (counts, agent names,
#         dates, log size and where the report is, as ~/…), never a key, email, log text or your account name.
# Never opens Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos
# data or app containers in Library, other drives, or a folder your rules name (in backticks) as never to open or
# read, once it has read that rule. Same rules as the Excellent app, simplified. Python 3.9+, standard library.
import hashlib, html, json, os, posixpath as pp, re, subprocess, sys, time
from datetime import datetime
from urllib.parse import unquote

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


# ---------- keys: kind, pattern, the exact shape a real one has (a fingerprint is kept, never the key) ----------
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
KEYS = {t: (re.compile(rb"(?:" + rx + rb")(?![\w-])", re.A), re.compile(shape, re.A)) for t, rx, shape in KEY_PATTERNS}
STARTS = {b"sk-": ["claude_login", "anthropic_key", "openrouter_key", "openai_key"], b"github_pat_": ["github_token"],
          **{s: ["github_token"] for s in (b"ghp_", b"gho_", b"ghs_", b"ghu_")}, b"glpat-": ["gitlab_token"],
          b"xox": ["slack_token"], b"AKIA": ["aws_key"], b"AIza": ["google_key"], b"sk_live_": ["stripe_key"],
          b"rk_live_": ["stripe_key"], b"xai-": ["xai_key"]}
WORD = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
FAKE = ("fake", "test", "dummy", "example", "xxxx", "0000", "abcd", "sample", "placeholder", "redact", "yourkey",
        "your_key", "your-key", "...")
KEY_NAMES = {"claude_login": "Claude sign-in token", "anthropic_key": "Anthropic", "openai_key": "OpenAI",
             "github_token": "GitHub", "gitlab_token": "GitLab", "slack_token": "Slack", "aws_key": "AWS",
             "google_key": "Google Cloud", "stripe_key": "Stripe", "openrouter_key": "OpenRouter", "xai_key": "xAI"}


def keys_in(b, acc):
    seen = set()
    for lit, kinds in STARTS.items():
        i = b.find(lit)
        while i >= 0:
            j, i = i, b.find(lit, i + 1)
            if j and b[j - 1] in WORD:
                continue
            for ty in kinds:
                m = KEYS[ty][0].match(b, j)
                if m:
                    v = m.group(0).decode("ascii", "replace")
                    if v not in seen and not any(k in v.lower() for k in FAKE) and len(set(v[-20:])) >= 8 and KEYS[ty][1].fullmatch(v):
                        seen.add(v)
                        acc[hashlib.sha256(v.encode()).hexdigest()[:12]] = ty
                    break


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


# ---------- shell commands: a small POSIX tokenizer, as the app has ----------
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


def resolve(tok, cwd):
    t = tok[1:] if tok[:1] in "\"'" else tok
    t = t[:-1] if t[-1:] in "\"'" else t
    t = re.sub(r"^\$\{?HOME\}?(?=/|$)", lambda m: HOME, t)
    t = HOME + t[1:] if t == "~" or t.startswith("~/") else t
    if "$" in t or not (t.startswith("/") or cwd):
        return None
    t = t if t.startswith("/") else cwd.rstrip("/") + "/" + t
    return fold(pp.normpath(t)).rstrip("/") or "/"


# ---------- the checks (the app's rules) ----------
META = set("ls stat test [ du find file mkdir touch readlink realpath dirname basename echo printf chmod chown git grep rg "
           "wc ssh scp sftp rsync ssh-add ssh-keygen mosh".split())
NET = {"curl", "wget", "http", "https", "xh", "httpie", "aria2c"}
CODE_NET = re.compile(r"requests\.(get|post|put|patch|Session|request)|urllib\.request|urlopen\(|\bfetch\(|http\.client|"
                      r"httpx\.|axios|URLSession|Net::HTTP|open-uri|HttpClient")
CODE_READ = re.compile(r"\b(?:open|fopen|readFileSync|readFile|read_text|read_bytes|File\.read|IO\.read|File\.open)\s*\(\s*[\"']([^\"'\n]{1,300})[\"']")
TRIGGER = re.compile(r"push|commit|merge|rebase|--no-verify|\b(rm|trash|unlink|rmdir|srm|mv|find)\b|publish|vercel|netlify|wrangler"
                     r"|\bfly|\.env|/\.ssh/|credentials|\.netrc|cookies|login data|keyrings|password-store|\bsecurity\b"
                     r"|secret-tool|\bpass\b|@|hookspath|include(if)?\.", re.I)
SECRET_FILE = re.compile(r"(/\.ssh/id_\w+|(^|/)\.env(\.(local|production|prod|development|dev|staging))?|/\.aws/credentials|/\.netrc"
                         r"|/Cookies|cookies\.sqlite|/Login Data|/\.claude/\.credentials\.json|/\.password-store/.*\.gpg)$|/\.local/share/keyrings/")


def is_secret_file(t):
    t = t.strip("\"'")
    t = HOME + t[1:] if t.startswith("~/") else t
    return not t.endswith((".example", ".sample", ".template", ".dist")) and bool(SECRET_FILE.search(t))


def has_email(t):
    return "@" in t and any(e in t.lower() for e in EMAILS)


def email_in_header(text):  # your email as a contact in a User-Agent or From header, as API docs ask for
    for e in EMAILS:
        for m in re.finditer(re.escape(e), text, re.I):
            pre = text[max(0, m.start() - 160):m.start()]
            if re.search(r"user-agent|[\"']from[\"']\s*:", pre, re.I) or re.search(r"/\d[\d.]*\s*\(\s*$", pre) \
                    or re.search(r"\bUA\s*=\s*[\"'{]?[^\n]*$", pre[-80:]):
                return True
    return False


def hosts_in(text):
    hs = {m.group(1).lower() for m in re.finditer(r"https?://([A-Za-z0-9.\-]+)", text)}
    return sorted(h for h in hs if not re.match(r"localhost|127\.|0\.0\.0\.0|.*\.(local|localhost|internal)$", h))


def foreign(hs):
    return [h for h in hs if not any(h == e.split("@")[1] or h.endswith("." + e.split("@")[1]) for e in EMAILS)]


def in_scope(scope, cwd):
    return not scope or bool(cwd) and (fold(cwd) + "/").startswith(fold(scope) + "/")


def delete_hit(target, recursive, cwd):
    for p in RULES["protected"]:
        if in_scope(p["scope"], cwd):
            q = p["path"]
            if (target.endswith(q[1:]) if q.startswith("*.") else target == q or (p["contents"] and target.startswith(q + "/"))
                    or (recursive and (q.startswith(target + "/") or target == "/"))):
                return p


def moves_hooks(rest):  # git config core.hooksPath / include.path: git hooks then run from somewhere else
    pos, k = [], 0
    while k < len(rest):
        if rest[k] in ("-f", "--file", "--blob", "--type", "--default", "--comment", "--value"):
            k += 2
            continue
        if not rest[k].startswith("-"):
            pos.append(rest[k])
        k += 1
    if any(x in rest for x in ("--get", "--get-all", "--get-regexp", "--list", "-l", "--unset", "--unset-all")) \
            or pos[:1] in (["get"], ["list"], ["unset"], ["edit"]):
        return False
    pos = pos[1:] if pos[:1] == ["set"] else pos
    return len(pos) > 1 and bool(re.fullmatch(r"core\.hookspath|include\.path|includeif\..*\.path", pos[0].lower()))


def shell_events(cmd, cwd, out):
    if not TRIGGER.search(cmd) and not any(n in cmd.lower() for n in RULES["names"]):
        return
    wd, email_vars = cwd, set()
    if has_email(cmd):
        email_vars = {m.group(1) for m in re.finditer(r"([A-Za-z_]\w*)=(\"[^\"\n]*\"|'[^'\n]*'|[^\s;&|\"']*)", cmd) if has_email(m.group(2))}
    for a in argvs(cmd):
        p, line = a[0], " ".join(a)
        if p in ("cd", "pushd"):
            wd = resolve(a[1] if len(a) > 1 else "~", wd) if a[1:2] != ["-"] else None
            continue
        if p == "git":
            i = 1
            while i < len(a) and a[i].startswith("-"):
                i += 2 if a[i] in ("-C", "-c") else 1
            sub, rest = (a[i] if i < len(a) else ""), a[i + 1:]
            if sub == "push" and any(x in ("-f", "--force") or x.startswith("--force") or x[:1] == "+" and len(x) > 1 for x in rest):
                main = any(re.search(r"(^|[:+/])(main|master)$|--force-with-lease=(refs/heads/)?(main|master)\b", x) for x in rest)
                out.append(("force_push", line, "main" if main else "branch", None))
            if sub in ("commit", "push", "merge", "rebase") and ("--no-verify" in rest or sub == "commit" and "-n" in rest):
                out.append(("no_verify", line, None, None))
            if sub == "config" and moves_hooks(rest):
                out.append(("no_verify", line, "moved git hooks", None))
        targets, rec = [], True
        if p in ("rm", "trash", "unlink", "rmdir", "srm"):
            targets = [x for x in a[1:] if not x.startswith("-")]
            rec = p == "trash" or any(re.match(r"-[A-Za-z]*[rR]", x) or x == "--recursive" for x in a[1:])
        elif p == "mv":
            args = [x for x in a[1:] if not x.startswith("-")]
            dest = resolve(args[-1], wd) if args else None
            for t in args[:-1]:  # a rename inside the same protected folder deletes nothing
                h = delete_hit(resolve(t, wd) or "\0", True, cwd)
                if not (h and dest and not h["path"].startswith("*.") and (dest + "/").startswith(h["path"] + "/")):
                    targets.append(t)
        elif p == "find" and ("-delete" in a or "-exec" in a and ("rm" in a or "/bin/rm" in a)):
            targets = a[1:next((i for i, x in enumerate(a) if i and x.startswith("-")), len(a))]
        for t in targets:
            ab = resolve(t, wd)
            h = ab and "/worktrees/" not in ab and delete_hit(ab, rec, cwd)
            if h:
                out.append(("protected_delete", line, h["label"], None))
                break
        verb = next((x for x in a[1:] if not x.startswith("-")), None)
        if p in ("npm", "pnpm", "yarn", "bun") and "publish" in a[1:3] or p == "vercel" and (verb in ("deploy", "redeploy", "promote")
                or verb is None and "--prod" in a) or p == "netlify" and "deploy" in a and "--prod" in a \
                or p == "wrangler" and ("deploy" in a or "publish" in a) or p in ("fly", "flyctl") and "deploy" in a:
            out.append(("publish_deploy", line, None, None))
        if p not in META and (any(len(t) < 300 and is_secret_file(t) for t in a[1:])
                              or p == "security" and re.match(r"(find|dump)-(generic|internet)-password|dump-keychain", verb or "")
                              and ("-w" in a or verb == "dump-keychain")
                              or (p, verb) in (("secret-tool", "lookup"), ("secret-tool", "search"), ("pass", "show"))
                              or p in ("node", "python", "python3", "perl", "ruby", "bun", "deno", "php") and any(
                                  x in ("-e", "-c", "-p", "--eval", "--print", "eval", "-r") and any(is_secret_file(m.group(1)) for m in CODE_READ.finditer(y))
                                  for x, y in zip(a[1:], a[2:]))):
            out.append(("secret_files", line, None, None))
        for r in RULES["no_open"] if p not in META or p == "git" else []:
            q = r["fpath"]
            if not in_scope(r["scope"], cwd) or (bool(wd) and (fold(wd) + "/").startswith(q + "/")):
                continue  # (a session working inside the folder may)
            if any(len(t) < 300 and "/worktrees/" not in t and (fold(t).endswith(q[1:]) if q.startswith("*.")
                   else ((resolve(t, wd) or "\0") + "/").startswith(q + "/")) for t in a[1:]):
                out.append(("written_rules", line, "never open " + r["path"], None))
                break
        for r in RULES["no_command"]:
            want = r["cmd"].split()
            if in_scope(r["scope"], cwd) and a[:len(want)] == want and not (want[:2] == ["git", "stash"] and len(a) > 2):
                out.append(("written_rules", line, "never `" + r["cmd"] + "`", None))
        if p in NET and EMAILS:
            kind = None
            for i in range(1, len(a)):
                v, flag = a[i], a[i - 1]
                if not (has_email(v) or any("$" + n in v or "${" + n + "}" in v for n in email_vars)):
                    continue
                if flag in ("-A", "--user-agent", "-H", "--header", "-e", "--referer", "-U") or re.match(r"(user-agent|from):", v, re.I):
                    kind = "header"
                elif re.fullmatch(r"-d|--data.*|-F|--form|--json|--post-data|--body-data", flag):
                    kind = kind or "post"
                elif re.match(r"https?://", v):
                    kind = kind or "url"
            if kind:
                hs = [h for i, x in enumerate(a) if re.match(r"https?://", x) and a[i - 1] not in ("-H", "--header", "-e", "--referer", "-A", "--user-agent") for h in hosts_in(x)]
                if foreign(hs) or not hs:
                    out.append(("public_submit" if kind == "post" else "email_out", line, None, foreign(hs)))
    if has_email(cmd) and CODE_NET.search(cmd) and email_in_header(cmd) and not any(e[0] == "email_out" for e in out):
        out.append(("email_out", cmd, None, foreign(hosts_in(cmd))))


def classify(tool, inp, cwd):
    out = []
    inp = inp if isinstance(inp, dict) else {"command": " ".join(map(str, inp))} if isinstance(inp, list) else {}
    if tool in ("Bash", "shell", "exec_command", "local_shell"):
        cmd = inp.get("command") if inp.get("command") is not None else inp.get("cmd")
        cmd = " ".join(map(str, cmd)) if isinstance(cmd, list) else cmd
        d = inp.get("dir_path") or inp.get("directory")
        if isinstance(cmd, str) and cmd:
            shell_events(cmd, resolve(d, cwd) if isinstance(d, str) and d else cwd, out)
    fp = inp.get("file_path") or inp.get("notebook_path")
    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit") and isinstance(fp, str) and fp:
        if is_secret_file(fp):
            out.append(("secret_files", tool + " " + fp, None, None))
        ab = resolve(fp, cwd) or fold(fp)
        for r in RULES["no_open"]:
            q = r["fpath"]
            if in_scope(r["scope"], cwd) and "/worktrees/" not in fp and (ab.endswith(q[1:]) if q.startswith("*.") else (ab + "/").startswith(q + "/")) \
                    and not (cwd and fold(cwd).startswith(q)):
                out.append(("written_rules", tool + " " + fp, "never open " + r["path"], None))
                break
        text = "\n".join([inp[k] for k in ("content", "new_string") if isinstance(inp.get(k), str)]
                         + [e["new_string"] for e in inp.get("edits") or [] if isinstance(e, dict) and isinstance(e.get("new_string"), str)])
        if tool != "Read" and text and (CODE_NET.search(text) or re.search(r"\b(curl|wget)\b", text)) and has_email(text) and email_in_header(text):
            out.append(("email_out", text, None, foreign(hosts_in(text))))
    if tool == "WebFetch" and isinstance(inp.get("url"), str) and has_email(inp["url"]) and foreign(hosts_in(inp["url"])[:1] or [""]):
        out.append(("email_out", inp["url"], None, hosts_in(inp["url"])))
    if EMAILS and any(k in tool.lower() for k in ("chrome", "browser", "playwright", "puppeteer", "computer")):
        flat = json.dumps(inp, ensure_ascii=False)
        if any(not re.search(r"(authuser=|mailto:|/u/\d/?)$", flat[max(0, m.start() - 12):m.start()], re.I)
               for e in EMAILS for m in re.finditer(re.escape(e), flat, re.I)):
            hs = foreign(hosts_in(flat))
            sent = re.search(r"submit|\"key\":\s*\"(Return|Enter)\"|\.requestSubmit|\.submit\(", flat, re.I)
            out.append(("public_submit", "Browser agent typed your email " + ("on " + ", ".join(hs) if hs else "into a web page")
                        + (" and submitted the form" if sent else ""), None, hs))
    return out


# ---------- what each session was told: a rule break counts only if the session had loaded that rule ----------
TOLD = {}


def told_add(told, texts):
    told["n"] += 1
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()
        if h not in TOLD:
            TOLD[h] = {"o:" + x for u, _, k in md_units(t) if k != "h" for x in unit_paths(u)[1]} | \
                      {"c:" + m.group(1).strip() for m in CMD_RULE.finditer(t)}
        for k in TOLD[h]:
            told["first"].setdefault(k, told["n"])


def told_line(agent, line, told):
    try:
        if agent == "claude" and (b'"attachment":{"type":"instructions"' in line or b'"attachment":{"type":"nested_memory"' in line):
            a = json.loads(line).get("attachment") or {}
            c = a.get("content")
            texts = [f.get("content") for f in a.get("files") or [] if isinstance(f, dict)] if a.get("type") == "instructions" \
                else [c.get("content") if isinstance(c, dict) else c]
        elif agent == "codex" and (b"AGENTS.md instructions for" in line or b"<user_instructions>" in line
                                   or b'"session_meta"' in line[:200] and b'"instructions"' in line):
            o = json.loads(line)
            p = o.get("payload") or {}
            texts = [p.get("instructions")] if o.get("type") == "session_meta" else [
                c.get("text") for c in p.get("content") or [] if p.get("type") == "message" and p.get("role") in ("user", "developer")
                and isinstance(c, dict) and str(c.get("text", "")).lstrip().startswith(("# AGENTS.md instructions for", "<user_instructions>"))]
        else:
            return
    except ValueError:
        return
    texts = [t for t in texts if isinstance(t, str) and t.strip()]
    if texts:
        told_add(told, texts)


def untold(e, res, told):
    d = e["detail"]
    key = "o:" + d[11:] if d.startswith("never open ") else "c:" + d[7:-1]
    if told["n"]:
        return told["first"].get(key, 1 << 30) > max(e["at"], 1)
    if res["agent"] == "codex":  # Codex logged no AGENTS.md: it was told no rule
        return True
    return not any((r.get("path") or r.get("cmd")) == key[2:] and in_scope(r["scope"], res["cwd"])  # others: rules of the start folder
                   for r in RULES["no_open" if key[0] == "o" else "no_command"])


# ---------- reading one log (in a worker process) ----------
GROK_TOOLS = {"run_terminal_command": "Bash", "monitor": "Bash", "Shell": "Bash", "read_file": "Read", "search_replace": "Edit",
              "hashline_edit": "Edit", "StrReplace": "Edit", "write": "Write", "web_fetch": "WebFetch", "Fetch": "WebFetch"}
ALIASES = {"command": ("cmd", "command_line"), "file_path": ("path", "target_file", "absolute_path", "filePath"),
           "content": ("contents", "file_text"), "new_string": ("newString", "new_str")}
CWD_RX = re.compile(rb'"cwd":"((?:[^"\\]|\\.)*)"')
BLOCKED = {"claude": re.compile(r"hook|blocked|denied|not allowed|refus|permission", re.I),
           "codex": re.compile(r"rejected by (the )?user|sandbox (denied|blocked)|not permitted by policy|blocked by (?:\w+ )?hook", re.I),
           "grok": re.compile(r"denied by (a |the )?(pretooluse )?hook|blocked by (a |the )?(\w+ )?hook|permission (was )?denied|rejected by (the )?user", re.I)}


def jstr(t):
    try:
        return json.loads(t)
    except ValueError:
        return None


def init_worker(rules, emails, never_open):
    RULES.update(rules)
    EMAILS[:], NEVER_OPEN[:] = emails, never_open


def scan_file(job):
    path, agent, cwd = job
    res = {"path": path, "agent": agent, "cwd": cwd, "keys": {}, "events": [], "calls": 0, "start": "", "end": "", "bytes": 0}
    told, pend = {"n": 0, "first": {}}, {}

    def add(cid, found, ts):
        evs = [{"rule": r, "ts": ts, "text": mask(t, 220), "detail": d, "hosts": (h or [])[:4], "outcome": "ran", "at": told["n"]}
               for r, t, d, h in found]
        res["events"] += evs
        if cid is not None and evs:
            pend[cid] = evs

    def result(cid, text, failed=True):
        for e in pend.pop(cid, []):
            e["outcome"] = "blocked" if BLOCKED[agent].search(text) else "failed" if failed else "ran"
    try:
        f = open(path, "rb")
    except OSError:
        return res
    with f:
        for line in f:
            res["bytes"] += len(line)
            keys_in(line, res["keys"])
            told_line(agent, line, told)
            try:
                if agent == "claude":
                    i = line.rfind(b'"timestamp":"')
                    if i >= 0:
                        res["end"] = line[i + 13:i + 37].decode("ascii", "replace")
                        res["start"] = res["start"] or res["end"]
                    m = not res["cwd"] and CWD_RX.search(line, 0, 4000)
                    if m:
                        res["cwd"] = json.loads(b'"' + m.group(1) + b'"')
                    if b'"tool_use"' in line and b'"type":"assistant"' in line:
                        o = json.loads(line)
                        for x in (o.get("message") or {}).get("content") or [] if o.get("type") == "assistant" else []:
                            if isinstance(x, dict) and x.get("type") == "tool_use":  # (api-request-blob records repeat calls)
                                res["calls"] += 1
                                add(x.get("id"), classify(x.get("name") or "", x.get("input") or {}, o.get("cwd") or res["cwd"]), o.get("timestamp") or "")
                    elif pend and b'"is_error":true' in line and b'"tool_result"' in line:
                        for x in (json.loads(line).get("message") or {}).get("content") or []:
                            if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in pend:
                                c = x.get("content")
                                result(x["tool_use_id"], (c if isinstance(c, str) else " ".join(str(y.get("text", "")) for y in c or [] if isinstance(y, dict)))[:300])
                elif agent == "codex":
                    if line.startswith(b'{"timestamp":"'):
                        res["end"] = line[14:38].decode("ascii", "replace")
                        res["start"] = res["start"] or res["end"]
                    if b'"session_meta"' in line[:200]:
                        res["cwd"] = res["cwd"] or (json.loads(line).get("payload") or {}).get("cwd") or ""
                    elif (b'"function_call' in line or b'"custom_tool_call' in line) and (pend or b'_output"' not in line):
                        p = json.loads(line).get("payload") or {}
                        pty, cid = p.get("type"), p.get("call_id")
                        if pty in ("function_call", "custom_tool_call"):
                            res["calls"] += 1
                            raw = p.get("input") if pty == "custom_tool_call" else p.get("arguments")
                            text, found = raw if isinstance(raw, str) else json.dumps(raw or {}), []
                            cmds = [m.group(1) for m in re.finditer(r'cmd\s*:\s*"((?:[^"\\]|\\.)*)"', text)]  # exec: tools.exec_command({cmd:"…"})
                            for c in [jstr('"' + c + '"') for c in cmds] + ([jstr(text)] if p.get("name") in ("shell", "exec_command") else []):
                                found += classify("Bash", c if isinstance(c, dict) else {"command": c}, res["cwd"]) if c else []
                            add(cid, found, line[14:38].decode("ascii", "replace"))
                        elif cid in pend:
                            o = p.get("output")
                            t = (o if isinstance(o, str) else json.dumps(o))[:3000]
                            result(cid, t, bool(re.search(r"exit(?:ed)?(?: with)?(?: code)?[: ]+[1-9]\d*\b|process exited with code [1-9]", t, re.I)))
                elif agent == "grok":
                    if line.startswith(b'{"type":"assistant"') and b'"tool_calls"' in line:
                        for c in json.loads(line).get("tool_calls") or []:
                            res["calls"] += 1
                            args = c.get("arguments") or {}
                            args = json.loads(args) if isinstance(args, str) else args
                            for k, al in ALIASES.items() if isinstance(args, dict) else []:
                                args.setdefault(k, next((args[x] for x in al if args.get(x) is not None), None))
                            add(c.get("id"), classify(GROK_TOOLS.get(c.get("name") or "", c.get("name") or ""), args, res["cwd"]), "")
                    elif pend and line.startswith(b'{"type":"tool_result"'):
                        m = re.search(rb'"tool_call_id"\s*:\s*"([^"]{1,200})"', line)
                        if m and m.group(1).decode() in pend:
                            result(m.group(1).decode(), line[:4000].decode("utf-8", "replace"), False)
            except ValueError:  # a line that isn't whole JSON (a log still being written)
                continue
    for e in res["events"]:
        e["untold"] = e["rule"] == "written_rules" and untold(e, res, told)
    return res


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


def build_rules(w):
    fp = lambda p: p if p.startswith("*.") else fold(pp.normpath(expand(p)))
    prot = [{"path": fold(HOME + p), "contents": c, "scope": "", "label": "~" + p} for p, c in (
        ("/.ssh", True), ("/.aws", True), ("/.gnupg", True), ("/Library/Keychains", True), ("/Documents", False), ("/Desktop", False), ("", False))]
    prot += [{"path": fp(r["path"]), "contents": True, "scope": r["scope"], "label": r["path"]} for r in w["no_delete"]]
    names = {fold(r["path"].rsplit("/", 1)[-1].lstrip("*")) for r in w["no_open"]} | {r["cmd"].split()[0] for r in w["no_command"]}
    return {"protected": prot, "no_open": [dict(r, fpath=fp(r["path"])) for r in w["no_open"]], "no_command": w["no_command"],
            "names": [n for n in names if len(n) > 1]}


def broken_hooks():  # hooks whose program is gone fail silently on every action
    out = []
    for agent, f in (("claude", HOME + "/.claude/settings.json"), ("codex", HOME + "/.codex/hooks.json")):
        try:
            hooks = json.loads(read(f) or "{}").get("hooks") or {}
        except (ValueError, AttributeError):
            continue
        for event, lst in hooks.items() if isinstance(hooks, dict) else []:
            for h in [h for e in lst if isinstance(e, dict) for h in e.get("hooks") or [] if isinstance(h, dict)] if isinstance(lst, list) else []:
                c = h.get("command")
                q = re.findall(r"[\"']([^\"']+)[\"']", c) if isinstance(c, str) else []
                for p in ((q[:1] if c[:1] in "\"'" else c.split()[:1]) + q) if isinstance(c, str) else []:
                    if p.startswith("/") and "excellent-engine" not in p and not closed(p) and not os.path.exists(p):
                        out.append({"agent": agent, "event": event, "file": f, "missing": p})
                        break
    return out


# ---------- the report ----------
CHECKS = [  # id, severity, title, score-card label, why it matters, what you can do yourself
    ("email_out", "high", "Your email was sent to websites", "requests carried my email to websites",
     "Agents put your email address into requests to other sites, or into scripts that make them, most often as the contact in a User-Agent header. Sites that got those requests have it in their logs.",
     "Ask your agents to use a project URL as the contact instead, and check your scripts for your address."),
    ("public_submit", "medium", "Your email was typed into web forms", "times my email went into a web form",
     "A browser agent or a command put your email into a web page, a form or a request body.", "Check each signup or form was one you meant."),
    ("secrets_in_logs", "high", "API keys are sitting in your agent logs", "API keys sitting in plain-text logs",
     "Agent logs keep everything an agent saw, in plain text. Anything that can read your home folder (a backup, a sync tool, another agent) can read these keys.",
     "Make a new key at each provider and retire the old one. Then delete those log files or take the keys out."),
    ("secret_files", "low", "Agents opened keys and secrets files", "actions on .env, SSH or keychain secrets",
     "Agents read, edited or ran commands on .env files, SSH keys or your keychain. Often that is part of the job, but what they read goes to the model provider and stays in the log.",
     "Keep real keys out of the folders agents work in; give agents environment variables or a secrets manager."),
    ("force_push", "high", "Agents force-pushed", "force pushes",
     "Agents force-pushed, which replaces history on the server. On a shared branch that can erase other people's work.",
     "Turn on branch protection for main on GitHub or GitLab, so force pushes there are refused."),
    ("no_verify", "medium", "Safety checks were skipped", "git commands that skipped or moved git hooks",
     "Agents used --no-verify or moved your git hooks, which skips the tests, linters and secret scanners you set up.",
     "Write \"never use --no-verify\" in your CLAUDE.md and AGENTS.md, and run the same checks in CI."),
    ("protected_delete", "high", "Never-delete folders were touched", "deletes of folders I marked never-delete",
     "Agents ran commands that delete or move folders you marked never-delete, or files in folders like ~/.ssh. Some may have failed.", "Check those folders and your backups now."),
    ("publish_deploy", "low", "Things were published or deployed", "publishes or deploys",
     "Agents published packages or ran deploys (Vercel, Netlify, Cloudflare, Fly).", "Check each one was meant."),
    ("written_rules", "medium", "Your own rules were broken", "breaks of rules I wrote for my agents",
     "Agents opened a path or ran a command your CLAUDE.md or AGENTS.md forbids, in sessions that had that rule (when a log doesn't record its rules, the rules of the folder the session started in). Agents read those files, but nothing enforces them.",
     "Keep the rule short and specific, and put it where every agent you use reads it (Codex doesn't read CLAUDE.md)."),
    ("broken_hooks", "high", "Your hooks fail silently", "hooks failing silently",
     "Hooks in your agent settings point to a program that no longer exists, so they fail each time they run.",
     "Open the settings file and fix the path."),
]
TILE_ONE = {"email_out": "request carried my email to a website", "public_submit": "time my email went into a web form",
            "secrets_in_logs": "API key sitting in a plain-text log", "secret_files": "action on .env, SSH or keychain secrets",
            "force_push": "force push", "no_verify": "git command that skipped or moved git hooks",
            "protected_delete": "delete of a folder I marked never-delete", "publish_deploy": "publish or deploy",
            "written_rules": "break of a rule I wrote for my agents", "broken_hooks": "hook failing silently"}  # a tile's label for 1
AGENT_NAMES = {"claude": "Claude Code", "codex": "Codex", "grok": "Grok Build"}
CSS = """:root{--bg:#f5f5f7;--card:#fff;--fg:#1d1d1f;--mut:#6e6e73;--line:#0000001a;--acc:#06c;--hi:#c4321c;--md:#a05a00;--ok:#1f7a35;--tile:#f2f2f4}
@media (prefers-color-scheme:dark){:root{--bg:#161617;--card:#232325;--fg:#f5f5f7;--mut:#a1a1a6;--line:#ffffff1c;--acc:#4aa3ff;--hi:#ff7a66;--md:#ffb648;--ok:#4fd27a;--tile:#2c2c2f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;overflow-wrap:anywhere}
main{max-width:760px;margin:0 auto;padding:40px 16px 64px}h1{font-size:30px;margin:0 0 6px}h2{font-size:19px;margin:40px 0 4px}
.mut,small{color:var(--mut)}a{color:var(--acc)}code{font:12.5px/1.45 ui-monospace,Menlo,monospace;word-break:break-all}
.card,.score,.cta{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:6px 20px 14px;margin:12px 0}
.score{padding:24px;margin-top:28px}.score h2{margin:0;font-size:21px;line-height:1.3}.need{margin:6px 0 0;color:var(--mut)}.need b{color:var(--fg)}
.score small a{font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:18px 0}
.tile{background:var(--tile);border-radius:12px;padding:12px 14px;font-size:13px;color:var(--mut);line-height:1.3}
.tile b{display:block;font-size:28px;color:var(--fg);font-variant-numeric:tabular-nums}.tile.ok b{color:var(--ok)}.score small{font-size:12px}
summary{display:flex;gap:10px;align-items:center;cursor:pointer;list-style:none;padding:10px 0 0}summary h3{font-size:16px;margin:0;flex:1}
summary i{width:9px;height:9px;border-radius:50%;background:var(--mut)}.high i{background:var(--hi)}.medium i{background:var(--md)}
.card p{margin:8px 0}.n{color:var(--mut);font-weight:600}.ex{list-style:none;padding:0;margin:0}.ex li{border-top:1px solid var(--line);padding:7px 0}
.ex small{display:block;font-size:12px}.tag{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 9px;color:var(--mut);font-weight:500}
.clean{columns:2;color:var(--mut)}.cta{padding:20px 22px;margin-top:40px}.cta h2{margin:0 0 6px}.fine{font-size:13px;color:var(--mut);margin-top:32px}
@media (max-width:520px){.clean{columns:1}.grid{grid-template-columns:1fr 1fr}}
.back{display:none}body:has(#card:target) main{max-width:1232px;padding:16px}body:has(#card:target) main>:not(#card):not(.back){display:none}
body:has(#card:target) .back{display:inline-block;margin-bottom:10px;font-size:13px}#card:target{max-width:1200px;aspect-ratio:16/9;margin:0;
padding:44px 52px;display:flex;flex-direction:column}#card:target h2{font-size:34px}#card:target .need{font-size:20px}#card:target .grid{flex:1;
align-content:center;grid-template-columns:repeat(5,1fr);gap:14px}#card:target .tile{font-size:15px;padding:16px}#card:target .tile b{font-size:40px}
#card:target small{font-size:16px}@media (max-width:900px){#card:target{aspect-ratio:auto;padding:24px}#card:target .grid{grid-template-columns:1fr 1fr}}"""


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


SHARE = "https://excellent.so/scan?utm_source=free-scan&utm_medium=share&utm_campaign=launch"


def summary(f, meta):  # the block your agent shows you: agent names, counts and dates only, nothing from your files
    head = " · ".join(filter(None, ["Excellent free scan", meta["agents"], meta["span"], plural(meta["calls"], "action")]))
    rows = ["  %-40s %7s" % (c[2], fmt(f[c[0]]["count"]) if c[0] in f else "0") for c in CHECKS]
    return "\n".join([head] + rows + ["Run yours free: excellent.so/scan"])


def render(f, meta, anon=None):  # anon: replaces every real name, for a sample report (not used in a scan)
    e = lambda s: html.escape(shown(s))
    tiles = "".join('<div class="tile%s"><b>%s</b>%s</div>' % ("" if c[0] in f else " ok", fmt(f[c[0]]["count"]) if c[0] in f else "0",
                    e(TILE_ONE[c[0]] if c[0] in f and f[c[0]]["count"] == 1 else c[3]))
                    for c in sorted(CHECKS, key=lambda c: (c[0] not in f, ["high", "medium", "low"].index(c[1]))))
    cards = ""
    for c in sorted([c for c in CHECKS if c[0] in f], key=lambda c: ["high", "medium", "low"].index(f[c[0]]["severity"])):
        x, ex = f[c[0]], ""
        for s in x["examples"]:
            txt = anon.text(s) if anon else s["text"]
            proj = anon.name("project", s["project"]) if anon and s["project"] else s["project"]
            if txt:
                ex += "<li><code>%s</code><small>%s</small></li>" % (e(txt), e(" · ".join(filter(None, [
                    AGENT_NAMES[s["agent"]], day(s["ts"]), proj, "" if s["outcome"] == "ran" else s["outcome"]]))))
        cards += ('<details class="card %s" open><summary><i></i><h3>%s</h3><span class="n">%s</span></summary><p><b>%s</b></p><p>%s</p>'
                  '<p><b>What you can do now:</b> %s</p>%s</details>') % (x["severity"], e(c[2]), fmt(x["count"]),
                  e(anon.detail(x["detail"]) if anon else x["detail"]), e(c[4]), e(c[5]), '<ul class="ex">%s</ul>' % ex if ex else "")
    clean = "".join("<li>%s</li>" % e(c[2]) for c in CHECKS if c[0] not in f) or "<li>None</li>"
    who = "you@example.com" if anon else ", ".join(re.sub(r"^(.).*@(.).*?(\.\w+)$", r"\1•••@\2•••\3", x) for x in EMAILS) or "no email found"
    m = {k: e(fmt(v) if isinstance(v, int) else v) for k, v in meta.items()}
    lead = e("My %s check-up · %s%s" % (meta["agents"] if meta["sessions"] else "AI agent", plural(meta["calls"], "agent action"),
                                                       ", " + meta["span"] if meta["span"] else ""))
    need = "<b>%d of %d</b> checks %s a look" % (len(f), len(CHECKS), "needs" if len(f) == 1 else "need") if f else "<b>All %d checks clean</b>" % len(CHECKS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Agent check-up</title><style>{CSS}</style></head><body><main>
<h1>Your agent check-up</h1><p class="mut">What your AI coding agents did on this Mac, read from their own logs on {m['date']}. This script showed your agent only a short summary: counts, agent names, dates and where this page is. Nothing else it read left this Mac.</p>
<a class="back" href="#">← Back to the full report</a>
<section class="score" id="card"><h2>{lead}</h2><p class="need">{need}</p><div class="grid">{tiles}</div>
<small>{e(plural(meta['sessions'], 'session'))} · Free check by Excellent<br><a href="{html.escape(SHARE)}">Run yours free: excellent.so/scan</a></small></section>
<p class="mut" style="font-size:13px"><a href="#card"><b>Show only the card</b></a>, sized for a screenshot. Safe to share: the card holds counts, agent names and dates only: no emails, sites, folders, commands or keys. Everything below is just for you.</p>
<h2>What we found <span class="tag">Private</span></h2><p class="mut">What happened, why it matters, and what you can do yourself. Examples are masked: your email shows as ‹your email›.</p>
{cards or '<p>Nothing to flag. Your agents passed every check.</p>'}<h2>Checks that came back clean</h2><ul class="clean">{clean}</ul>
<section class="cta"><h2>Want this check running all the time?</h2><p>This page is a one-time look back. Excellent for Mac shows the same findings whenever you scan, for free. The free scan shows the leak; Pro stops it. With Pro, the check runs in the background and tells you when an agent sends your email to a website, deletes a never-delete folder, force-pushes main or leaves a key in a log, and each time it blocks or asks. The app also fixes some in a click (keys in logs, broken Node hooks):</p>
<ul><li>with Pro, blocks agent commands that send your email to websites, and asks you before force pushes to main and --no-verify (Codex, Cursor, Gemini CLI and Devin refuse instead of asking)</li><li>takes keys out of your agent logs and shows you where to replace them</li>
<li>with Pro, checks each agent action from outside the agent against the never-delete, never-open and never-run rules you already wrote in CLAUDE.md and AGENTS.md</li></ul><p class="mut">Excellent for Mac runs on Apple silicon Macs with macOS 14 or later, with no account needed, for Claude Code, Codex and other agents. Pro is $6 a month or $60 a year. Pro is sold in the US for now.</p>
<a href="https://excellent.so"><b>See how it works at excellent.so →</b></a></section>
<section class="fine"><p><b>How this check worked.</b> Your agent saved a Python script where you could read it (~/excellent-free-scan/scan.py), checked it, and ran it. It read {e(plural(meta['sessions'], 'session'))} ({m['gb']} of logs) in {m['secs']}, {e(plural(meta['rulefiles'], 'instruction file'))} with {e(plural(meta['rules'], 'rule'))} it can check (never delete, never open, never run), and your hook settings. It looked for {e(who)} as your email.</p>
<p><b>What it never did.</b> It used no network and changed no file except this page. It kept no key or email, and never opened Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos data or app containers in Library, other drives, or a folder your rules name as never to open or read, once it had read that rule. This page loads nothing.</p>
<p><b>Limits.</b> Logs go back only as far as your agents keep them (Claude Code: 30 days unless you change it). Keys count only when they have a known shape; test and example keys are left out. The rules are the Excellent app's, simplified, so counts can differ a little.</p>
<p>To delete this page: <code>rm -r ~/excellent-free-scan</code></p></section></main></body></html>"""


def run(args):
    t0 = time.time()
    EMAILS[:] = owner_emails([args[i + 1] for i, a in enumerate(args[:-1]) if a == "--email"])
    logs = find_logs()
    heads = {p: head_cwd(p, a) for p, a in logs}
    written, nfiles = parse_rules([h[0] for h in heads.values()])
    RULES.update(build_rules(written))
    jobs = sorted(((p, a, heads[p][0]) for p, a in logs if not closed(p)), key=lambda j: -(os.stat(j[0]).st_size if os.path.exists(j[0]) else 0))
    try:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max(1, min(8, (os.cpu_count() or 2) - 1)), initializer=init_worker,
                                 initargs=(dict(RULES), list(EMAILS), list(NEVER_OPEN))) as ex:
            results = list(ex.map(scan_file, jobs, chunksize=4))
    except Exception:  # no process pool in some sandboxes: one log at a time
        results = [scan_file(j) for j in jobs]
    by, f = {}, {}
    for r in results:
        if r["agent"] == "grok":
            r["start"], r["end"] = heads[r["path"]][1:]
        for ev in r["events"]:
            if ev["outcome"] != "blocked" and not ev["untold"]:
                ev.update(agent=r["agent"], project=project_of(r["cwd"]), ts=ev["ts"] or r["start"])
                by.setdefault(ev["rule"], []).append(ev)
    n = plural
    last = lambda l: day(max(x["ts"] for x in l)) or "recently"

    def add(rid, evs, detail, sev=None, examples=None):
        seen, ex = set(), []
        for x in sorted(evs, key=lambda x: x["ts"], reverse=True) if examples is None else []:
            if x["text"][:70] not in seen and len(ex) < 3:
                seen.add(x["text"][:70])
                ex.append(x)
        f[rid] = {"count": len(evs), "detail": detail, "examples": ex if examples is None else examples,
                  "severity": sev or next(c[1] for c in CHECKS if c[0] == rid)}
    l = by.get("email_out")
    if l:
        hs = sorted({h for x in l for h in x["hosts"]})
        add("email_out", l, "%s put your email in requests to %s, most recently on %s.%s" % (n(len(l), "command"), n(max(1, len(hs)), "website"),
            last(l), " Sites: " + ", ".join(hs[:8]) + (" and more." if len(hs) > 8 else ".") if hs else ""))
    keys, kex = {}, []
    for r in sorted(results, key=lambda r: r["end"], reverse=True):
        if r["keys"]:
            keys.update(r["keys"])
            kinds = sorted(KEY_NAMES[t] for t in r["keys"].values())
            kex.append({"text": "~" + r["path"][len(HOME):] + " (" + ", ".join(kinds) + ")", "agent": r["agent"], "ts": r["end"],
                        "project": project_of(r["cwd"]), "outcome": "ran", "kinds": kinds})
    if keys:
        kinds = sorted(KEY_NAMES[t] for t in keys.values())
        add("secrets_in_logs", [{}] * len(keys), "%s that %s in plain text in %s: %s." % (n(len(keys), "key"), "looks real is" if len(keys) == 1 else "look real are",
            n(len(kex), "log file"), ", ".join("%s ×%d" % (k, kinds.count(k)) for k in dict.fromkeys(kinds))), examples=kex[:5])
    summaries = {
        "public_submit": lambda l: "%s your email went into a website form or request, most recently on %s." % (n(len(l), "time"), last(l)),
        "secret_files": lambda l: "%s touched SSH keys, .env files or your keychain." % n(len(l), "agent action"),
        "force_push": lambda l: "%s, most recently on %s." % (n(len(l), "force push", "force pushes"), last(l)),
        "no_verify": lambda l: "%s skipped or moved your git hooks." % n(len(l), "git command"),
        "protected_delete": lambda l: "%s touched folders marked never-delete, e.g. %s." % (n(len(l), "delete"), l[0]["detail"]),
        "publish_deploy": lambda l: "%s." % n(len(l), "publish or deploy", "publishes or deploys"),
        "written_rules": lambda l: "%s broke rules you wrote, most often \"%s\"." % (n(len(l), "action"), max(
            [x["detail"] for x in l], key=[x["detail"] for x in l].count)),
    }
    for rid, s in summaries.items():
        if by.get(rid):
            add(rid, by[rid], s(by[rid]), "medium" if rid == "force_push" and not any(x["detail"] == "main" for x in by[rid]) else None)
    bh = broken_hooks()
    if bh:
        add("broken_hooks", [{}] * len(bh), "%s in your agent settings %s to a program that is gone (%s)." % (n(len(bh), "hook"), "points" if len(bh) == 1 else "point",
            bh[0]["missing"].replace(HOME, "~")), examples=[{"text": "%s hook in %s needs %s" % (b["event"], b["file"].replace(HOME, "~"),
            b["missing"].replace(HOME, "~")), "agent": b["agent"], "ts": "", "project": "", "outcome": "ran", "event": b["event"]} for b in bh[:3]])
    days = sorted(d[:10] for r in results for d in (r["start"], r["end"]) if re.match(r"\d{4}-\d\d-\d\d", d))
    meta = {"date": datetime.now().strftime("%B %-d, %Y"), "sessions": len(results), "calls": sum(r["calls"] for r in results),
            "agents": " + ".join(AGENT_NAMES[a] for a in AGENT_NAMES if any(r["agent"] == a for r in results)) or "no agent logs found",
            "span": "%s – %s" % (day(days[0]), day(days[-1])) if days else "", "secs": n(round(time.time() - t0), "second"),
            "gb": "%.1f GB" % (sum(r["bytes"] for r in results) / 1e9), "rules": sum(map(len, written.values())), "rulefiles": nfiles}
    return f, meta, results


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else HOME + "/excellent-free-scan/report.html"
    f, meta, _ = run(args)
    os.makedirs(pp.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(f, meta))
    print("Read %s (%s of logs) in %s. Your email: %s." % (plural(meta["sessions"], "session"), meta["gb"], meta["secs"],
          "found (checked, not shown)" if EMAILS else "not found, so email checks were skipped (add --email you@example.com)"))
    print("Report: " + shown(out))  # ~/excellent-free-scan/report.html: your account name stays out of the chat
    print("\n" + summary(f, meta))


if __name__ == "__main__":
    main()
