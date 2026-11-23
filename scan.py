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
import base64, hashlib, html, json, os, posixpath as pp, re, subprocess, sys, time, zlib
from datetime import datetime
from urllib.parse import quote, unquote

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
            out.append(("email_out", text, "script input", foreign(hosts_in(text))))
    if tool == "WebFetch" and isinstance(inp.get("url"), str) and has_email(inp["url"]) and foreign(hosts_in(inp["url"])[:1] or [""]):
        out.append(("email_out", inp["url"], None, hosts_in(inp["url"])))
    if EMAILS and any(k in tool.lower() for k in ("chrome", "browser", "playwright", "puppeteer", "computer")):
        flat = json.dumps(inp, ensure_ascii=False)
        if any(not re.search(r"(authuser=|mailto:|/u/\d/?)$", flat[max(0, m.start() - 12):m.start()], re.I)
               for e in EMAILS for m in re.finditer(re.escape(e), flat, re.I)):
            hs = foreign(hosts_in(flat))
            sent = re.search(r"submit|\"key\":\s*\"(Return|Enter)\"|\.requestSubmit|\.submit\(", flat, re.I)
            out.append(("public_submit", "Browser tool input containing your email" + (" for " + ", ".join(hs) if hs else "")
                        + (" with a form submission instruction" if sent else ""), None, hs))
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
BLOCKED = {"claude": re.compile(r"^(?:error:\s*)?(?:command blocked|blocked by|rejected by (?:the )?user|permission requested|user (?:denied|rejected)|this (?:tool use|command) was (?:denied|blocked)|pretooluse:.*(?:block|denied))", re.I),
           "codex": re.compile(r"(?:command )?blocked by (?:\w+ )?hook|rejected by (the )?user|sandbox (denied|blocked)|not permitted by policy|blocked by (?:\w+ )?hook", re.I),
           "grok": re.compile(r"denied by (a |the )?(pretooluse )?hook|blocked by (a |the )?(\w+ )?hook|permission (was )?denied|rejected by (the )?user", re.I)}


EMAIL_RULES = ("email_out", "public_submit")
EMAIL_OUTCOMES = ("local script input", "result unknown", "tool reported failure", "blocked", "tool reported success")


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


def init_worker(rules, emails, never_open):
    RULES.update(rules)
    EMAILS[:], NEVER_OPEN[:] = emails, never_open


def scan_file(job):
    path, agent, cwd = job
    res = {"path": path, "agent": agent, "cwd": cwd, "keys": {}, "events": [], "calls": 0, "start": "", "end": "", "bytes": 0}
    told, pend = {"n": 0, "first": {}}, {}

    def add(cid, found, ts):
        evs = [{"rule": r, "ts": ts, "text": mask(t, 220), "detail": d, "hosts": (h or [])[:4], "outcome": "unknown" if r in EMAIL_RULES else "ran", "at": told["n"], "call": cid if isinstance(cid, str) else None}
               for r, t, d, h in found]
        res["events"] += evs
        if isinstance(cid, str) and cid and evs:
            pend[cid] = evs

    def result(cid, outcome):
        events = pend.get(cid, []) if outcome == "unknown" else pend.pop(cid, [])
        for e in events:
            if outcome != "unknown" or e["rule"] in EMAIL_RULES:
                e["outcome"] = outcome
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
                    if b'"tool_use"' in line:
                        o = json.loads(line)
                        for x in (o.get("message") or {}).get("content") or [] if o.get("type") == "assistant" else []:
                            if isinstance(x, dict) and x.get("type") == "tool_use":  # (api-request-blob records repeat calls)
                                res["calls"] += 1
                                add(x.get("id"), classify(x.get("name") or "", x.get("input") or {}, o.get("cwd") or res["cwd"]), o.get("timestamp") or "")
                    elif pend and b'"tool_result"' in line:
                        o = json.loads(line)
                        for x in ((o.get("message") or {}).get("content") or []) if o.get("type") == "user" else []:
                            if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in pend:
                                c = x.get("content")
                                text = c if isinstance(c, str) else " ".join(str(y.get("text", "")) for y in c or [] if isinstance(y, dict))
                                failed = x.get("is_error", False)
                                outcome = ("blocked" if BLOCKED[agent].search(text) else "failed") if failed is True else "ran" if failed is False and (x.get("is_error") is False or text.strip()) else "unknown"
                                result(x["tool_use_id"], outcome)
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
                            add(cid, found, json.loads(line).get("timestamp") or "")
                        elif pty in ("function_call_output", "custom_tool_call_output") and cid in pend:
                            result(cid, codex_outcome(p.get("output")))
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
                            record = json.loads(line)
                            text = str(record.get("content", ""))
                            status = record.get("status")
                            outcome = "blocked" if BLOCKED[agent].search(text) else "failed" if status in ("failed", "error") else "ran" if status in ("completed", "success") else "unknown"
                            result(m.group(1).decode(), outcome)
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
    ("email_out", "high", "Your email in request commands or scripts", "request or script inputs contained my email",
     "Your address appeared in a request command or in code supplied to a file-writing tool.",
     "Ask your agents to use a project URL as the contact instead, and check your scripts for your address."),
    ("public_submit", "medium", "Your email in form or request inputs", "form or request inputs contained my email",
     "A browser tool or a request command included your address in its input.", "Check each signup or form was one you meant."),
    ("secrets_in_logs", "high", "API keys are sitting in your agent logs", "API keys sitting in plain-text logs",
     "The scan found values matching known key formats in plain-text agent logs. Anyone with access to those files can read the values.",
     "Make a new key at each provider and retire the old one. Then delete those log files or take the keys out."),
    ("secret_files", "low", "Agents opened keys and secrets files", "actions on .env, SSH or keychain secrets",
     "A recorded tool call named a .env file, an SSH key or your keychain. Its input identifies the file or command. A matching key value in a transcript is a separate finding.",
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
TILE_ONE = {"email_out": "request or script input contained my email", "public_submit": "form or request input contained my email",
            "secrets_in_logs": "API key sitting in a plain-text log", "secret_files": "action on .env, SSH or keychain secrets",
            "force_push": "force push", "no_verify": "git command that skipped or moved git hooks",
            "protected_delete": "delete of a folder I marked never-delete", "publish_deploy": "publish or deploy",
            "written_rules": "break of a rule I wrote for my agents", "broken_hooks": "hook failing silently"}  # a tile's label for 1
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
DOWNLOAD = "https://www.excellent.so/download?utm_source=free-scan&utm_medium=report&utm_campaign=launch"
APP = {  # where a check needs a look: what Excellent for Mac does about it (truth/FEATURE-TRUTH.md; CLAIMS.md rulings D, G, H)
    "email_out": "With Pro, Excellent for Mac blocks agent commands that send your email to a website, before they run.",
    "public_submit": "With Pro, Excellent for Mac asks you first, or stops it, when an agent goes to put your email into a web form.",
    "secrets_in_logs": "Excellent for Mac can take these keys out of your agent logs, and opens each provider's key page so you can replace them.",
    "secret_files": "With Pro, Excellent for Mac asks you first, or stops it, before an agent reads a .env or key file.",
    "force_push": "With Pro, Excellent for Mac asks you first, or stops it, before an agent force-pushes main.",
    "no_verify": "With Pro, Excellent for Mac asks you first, or stops it, before an agent uses --no-verify.",
    "protected_delete": "With Pro, Excellent for Mac blocks agent commands that delete the folders you marked never-delete.",
    "written_rules": "With Pro, Excellent for Mac checks each action against the never-delete, never-open and never-run rules you wrote, before it runs.",
    "broken_hooks": "Excellent for Mac flags these whenever you scan, and repairs hooks that broke because Node moved.",
}
LOCKUP = ('<svg class="lockup" viewBox="0 0 1153 219" role="img" aria-label="Excellent"><path fill-rule="evenodd" d="%s"/>'
          '<path transform="translate(-28.3)" d="%s"/></svg>') % (MARK_D, WORDS_D)
MARK = '<svg class="mark" viewBox="0 0 248 219" aria-hidden="true"><path fill-rule="evenodd" d="%s"/></svg>' % MARK_D
ARROW = '<svg class="arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9.5M8.5 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
LIGHT = ("--paper:#fff;--paper2:#f1f4f6;--card:#fff;--ink:#0f1419;--ink2:#27313b;--quiet:#56616c;--faint:#7d8893;--rule:#d8dfe5;"
         "--fill:#f1f4f6;--fill2:#e2e8ed;--accent:#1d6b74;--ok:#2e8c8c;--hi:#c42a18;--hi-bg:#ce2e1c14;--edge:#0e0e0e17;"
         "--shadow:0 1px 2px #171b1f0f,0 12px 32px -12px #171b1f2e")
CSS = """:root{color-scheme:light dark;""" + LIGHT + """;
--field:radial-gradient(90% 120% at 0% 0%,#9fc3c88c,#0000 55%),radial-gradient(80% 100% at 100% 100%,#5f8a91b3,#0000 65%),linear-gradient(150deg,#3b5b66,#24363f 55%,#1e2a33);
--serif:"PP Editorial New",Fraunces,ui-serif,Baskerville,"Iowan Old Style",Georgia,serif;--sans:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Monaco,monospace}
@media screen and (prefers-color-scheme:dark){:root{--paper:#12181d;--paper2:#161d23;--card:#1a2229;--ink:#f2f6f8;--ink2:#d2dae0;--quiet:#97a4af;
--faint:#6f7b86;--rule:#2b3640;--fill:#222c34;--fill2:#2b3640;--accent:#6cc3c3;--ok:#5bb5b2;--hi:#ff8c7a;--hi-bg:#ff8c7a1a;--edge:#ffffff14;
--shadow:0 1px 2px #0000004d,0 16px 40px -16px #0009;
--field:radial-gradient(90% 120% at 0% 0%,#7fa9ae4d,#0000 55%),radial-gradient(80% 100% at 100% 100%,#3b5b66b3,#0000 65%),linear-gradient(150deg,#2f4a52,#1c2a33 55%,#161f27)}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-wrap:anywhere}
h1,h2,h3,p,ul,dl,dd{margin:0}ul{padding:0;list-style:none}svg{display:block;fill:currentColor}
a{color:inherit;text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:4px}a:hover{text-decoration-color:currentColor}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}
code{font:12.5px/1.55 var(--mono);color:var(--ink2);word-break:break-all}
.wrap{max-width:944px;margin:0 auto;padding:0 clamp(16px,5vw - 8px,40px)}
.top{border-bottom:1px dashed var(--rule)}.top .wrap,footer .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px 24px;flex-wrap:wrap}
.top .wrap{min-height:64px}.lockup{flex:none;height:20px;width:auto;aspect-ratio:1153/219}.nw{white-space:nowrap}
.label{font:500 11px/1.3 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--quiet)}
.hero{padding:clamp(40px,7vw,80px) 0 clamp(28px,4vw,40px)}
h1{font:400 clamp(38px,6vw,60px)/1.06 var(--serif);letter-spacing:-.02em;text-wrap:balance}
.lede{margin-top:18px;max-width:38em;font-size:17px;line-height:1.6;color:var(--quiet);text-wrap:pretty}
.score{border-radius:12px;padding:clamp(10px,2.6vw,28px);background:var(--field);box-shadow:inset 0 0 0 1px #ffffff1a,0 24px 60px -36px #171b1f8c}
.score-in{display:flex;flex-direction:column;gap:20px;padding:clamp(20px,3.6vw,36px);border-radius:8px;background:var(--card);box-shadow:var(--shadow)}
.score .lockup{align-self:flex-start;height:18px}.score h2{font:400 clamp(24px,3.4vw,34px)/1.16 var(--serif);letter-spacing:-.015em;text-wrap:balance}.sub{display:block;color:var(--faint)}.sep{display:none}
.need{margin-top:-4px;font-size:15px;color:var(--quiet)}.need b{color:var(--ink);font-weight:600}
.need i{display:inline-block;width:8px;height:8px;margin-right:10px;border-radius:50%;background:var(--hi);vertical-align:1px}.need.ok i{background:var(--ok)}
.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
.tile{padding:14px 14px 16px;border-radius:6px;background:var(--fill);font-size:13px;line-height:1.35;color:var(--quiet)}
.tile b{display:block;margin-bottom:10px;font:400 36px/1 var(--serif);letter-spacing:-.02em;color:var(--ink);font-variant-numeric:lining-nums tabular-nums}
.tile.ok b{color:var(--ok)}
.foot{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 24px;padding-top:18px;border-top:1px solid var(--fill2);font-size:13px;color:var(--quiet)}
.foot small{font-size:inherit}.foot a,.btn,.btn2{display:inline-flex;align-items:center;gap:8px;text-decoration:none;white-space:nowrap}.foot a{font-weight:500;color:var(--ink)}.arrow{width:15px;height:15px}
.share{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;margin-top:18px;font-size:13px;line-height:1.5;color:var(--quiet)}.share span{flex:1;min-width:18em}
.btn2{height:38px;padding:0 16px;border:1px solid var(--rule);border-radius:99px;font:500 13px/1 var(--sans);color:var(--ink)}.btn2:hover{border-color:var(--ink2)}
[hidden]{display:none!important}
.tools{margin-top:14px;padding:18px 20px;border:1px solid var(--rule);border-radius:10px}.tools .row{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
button.btn2{background:none;cursor:pointer}button.btn2:disabled{opacity:.6;cursor:progress}.hint{margin-top:8px;font-size:13px;line-height:1.5;color:var(--quiet)}
#lnk{display:block;margin-top:10px;font-size:11.5px;color:var(--quiet)}#vid{display:block;width:100%;max-width:640px;margin-top:14px;border-radius:6px}
.sec{padding-top:clamp(56px,8vw,88px)}.head{margin-bottom:28px}
.sec h2,.cta h2{margin-top:12px;font:400 clamp(30px,4vw,42px)/1.12 var(--serif);letter-spacing:-.02em;text-wrap:balance}
.pill{display:inline-flex;align-items:center;height:20px;padding:0 7px;border-radius:4px;box-shadow:inset 0 0 0 1px currentColor;font:500 10.5px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.label .pill{margin-left:8px;vertical-align:1px}
.find{margin:12px 0;border:1px solid var(--edge);border-radius:8px;background:var(--card);box-shadow:var(--shadow)}
.find summary{display:grid;grid-template-columns:1fr auto;grid-template-areas:"s n" "t n";gap:10px 20px;align-items:center;padding:22px 26px;cursor:pointer;list-style:none}
.find summary::-webkit-details-marker{display:none}.find h3{grid-area:t;font:500 19px/1.35 var(--sans);letter-spacing:-.01em}
.n{grid-area:n;font:400 40px/1 var(--serif);letter-spacing:-.02em;font-variant-numeric:lining-nums tabular-nums}
.sev{grid-area:s;justify-self:start;display:inline-flex;align-items:center;gap:7px;height:22px;padding:0 8px;border-radius:4px;font:500 10.5px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.sev i{width:6px;height:6px;border-radius:50%;background:currentColor}.high .sev{color:var(--hi);background:var(--hi-bg)}
.medium .sev{color:var(--ink2);box-shadow:inset 0 0 0 1px var(--rule)}.low .sev{color:var(--quiet);background:var(--fill)}.low .sev i{background:none;box-shadow:inset 0 0 0 1px currentColor}
.fb{display:grid;gap:20px;padding:0 26px 26px}.what{padding-top:20px;border-top:1px solid var(--fill2);color:var(--ink2)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px 36px}.pair dt{margin-bottom:6px}.pair dd{font-size:15px;line-height:1.6;color:var(--quiet)}
.app{display:flex;gap:12px;align-items:flex-start;padding:12px 16px;border-radius:6px;background:var(--fill);font-size:14px;line-height:1.5;color:var(--ink2)}
.mark{flex:none;width:17px;height:15px;margin-top:2px}.exs .label{margin-bottom:8px}
.ex{display:grid;gap:6px}.ex li{padding:10px 12px;border:1px solid var(--fill2);border-radius:6px}.ex small{display:block;margin-top:4px;font-size:12px;color:var(--quiet)}
.cleanbox{margin-top:36px}.cleanbox .label{margin-bottom:10px}.clean{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:0 36px}
.clean li{display:flex;align-items:center;gap:14px;padding:13px 0;border-top:1px solid var(--rule);font-size:15px;color:var(--ink2)}
.clean li:before{content:"";flex:none;width:10px;height:5px;margin:-4px 2px 0;border:solid var(--ok);border-width:0 0 2px 2px;transform:rotate(-45deg)}
.cta{margin-top:clamp(64px,9vw,104px);padding:clamp(28px,5.4vw,56px);
border-radius:12px;background:var(--field);color:#f2f6f8;box-shadow:inset 0 0 0 1px #ffffff1a}
.cta .lede{max-width:34em}.go{display:flex;flex-wrap:wrap;align-items:center;gap:14px 24px;margin-top:30px}.go .fine{margin:0;max-width:24em}.cta .label{display:flex;align-items:center;gap:10px;color:#c7d3dc}.cta .mark{margin:0}.cta .lede{color:#c3ced6}
.btn{min-height:48px;padding:0 24px;border-radius:99px;background:#f2f6f8;color:#12181d;font:500 15px/1 var(--sans)}.btn:hover{background:#fff}
.fine{margin-top:14px;font-size:13px;line-height:1.5;color:#aebbc5}.tiers{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:clamp(32px,4vw,44px)}
.tiers li{padding:20px 22px;border:1px solid #ffffff21;border-radius:8px;background:#0f191f59}
.tiers b{display:block;margin:12px 0 6px;font:400 23px/1.2 var(--serif);color:#fff}.tiers p{font-size:14px;line-height:1.55;color:#c3ced6}.tiers p+p{margin-top:8px;color:#aebbc5}.tiers .req{grid-column:1/-1;padding:4px 2px 0;border:0;background:none}.tiers .req p{font-size:13px;color:#aebbc5}
.pill.solid{background:#f2f6f8;color:#12181d;box-shadow:none}
.method{display:grid;grid-template-columns:1fr 1fr;gap:28px 44px}.method h3{margin-bottom:6px;font:500 15px/1.4 var(--sans)}.method p{font-size:14px;line-height:1.65;color:var(--quiet)}
footer{margin-top:clamp(64px,9vw,104px);border-top:1px dashed var(--rule)}footer .wrap{padding-top:24px;padding-bottom:44px;font-size:13px;color:var(--quiet)}footer .lockup{height:16px}
.back{display:none}body:has(#card:target) :is(.top,footer),body:has(#card:target) main>:not(#card):not(.back){display:none}
body:has(#card:target) main{max-width:1264px;padding:24px 32px}body:has(#card:target) .back{display:inline-block;margin-bottom:12px;font-size:13px;color:var(--quiet)}
#card:target{display:flex;width:1200px;max-width:100%;aspect-ratio:16/9;padding:32px}#card:target .score-in{flex:1;justify-content:space-between;gap:0;padding:36px 44px 30px}
#card:target .lockup{height:22px}#card:target h2{font-size:38px;line-height:1.14}#card:target .need{margin:0;font-size:18px}#card:target .grid{gap:10px}
#card:target .tile{padding:16px 18px 18px;font-size:14.5px}#card:target .tile b{font-size:46px;margin-bottom:10px}#card:target .foot{padding-top:16px;font-size:15px}
@media (max-width:900px){#card:target{aspect-ratio:auto;padding:12px}#card:target .score-in{padding:24px}#card:target h2{font-size:28px}
#card:target .grid{grid-template-columns:1fr 1fr}#card:target .tile b{font-size:36px}}
@media (max-width:860px){.grid{grid-template-columns:1fr 1fr}}
@media (max-width:700px){.pair,.method,.tiers{grid-template-columns:1fr}.tile b{font-size:32px}
.find summary{padding:18px 18px}.fb{padding:0 18px 18px}.n{font-size:32px}.top .label{display:none}}
@media print{:root{""" + LIGHT + """}body{font-size:13px}.share,.back,.tools{display:none}.score,.cta{padding:0;background:none;box-shadow:none}
.score-in,.tile,.find,.tiers li{border:1px solid var(--rule);box-shadow:none}.grid{grid-template-columns:repeat(5,minmax(0,1fr))}.score,.cta,.method>div,.ex li,.find summary,.pair,.app{break-inside:avoid}.find summary,.head{break-after:avoid}.need i,.sev,.sev i,.tile.ok b{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.cta{color:var(--ink);gap:24px}.cta :is(.label,.lede,.fine,.tiers p){color:var(--quiet)}.tiers b{color:var(--ink)}.tiers li{background:none}
.btn{margin-top:20px;border:1px solid var(--ink);background:none;color:var(--ink)}.btn:after{content:": excellent.so/download"}.pill.solid{border:1px solid var(--ink)}}"""


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
SHARE_R = "https://excellent.so/r"  # share link v1: share-format.json and NOTES.md say what each field means
UTM = "&utm_source=free-scan&utm_medium=share&utm_campaign=launch&utm_content="
ROUTES = ("x", "linkedin", "copy", "video", "image")  # utm_content: which share button the link came from
LETTERS = {"claude": "c", "codex": "x", "grok": "g"}  # a= in card order (AGENT_NAMES order)
X_POST = "https://x.com/intent/post?text="
X_TEXTS = {  # the prefilled X posts, first person, in the card's own labels. {top} is the top two non-zero checks. The link is IN the post (Matt, Nov 19)
    "some": "My AI coding agents' check-up: {top}. A free check counted it from my own Mac's logs. Run yours: {link}",
    "zero": "I ran a free check on my AI coding agents' logs: all {checks} checks came back clean across {actions}. Run yours: {link}"}
# No network of any kind (no connect-src), one inline script allowed by its hash, files made on this Mac (blob:) only
CSP_FMT = "default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-%s'; img-src blob:; media-src blob:"
SCRIPT_JS = r'''(function () {
"use strict";
var D = JSON.parse(document.getElementById("card-data").textContent);
var $ = function (i) { return document.getElementById(i); };
var dark = matchMedia("(prefers-color-scheme: dark)").matches;
var P = dark ? {card: "#1a2229", ink: "#f2f6f8", ink2: "#d2dae0", quiet: "#97a4af", faint: "#6f7b86", rule: "#2b3640", fill: "#222c34", ok: "#5bb5b2", hi: "#ff8c7a"}
  : {card: "#ffffff", ink: "#0f1419", ink2: "#27313b", quiet: "#56616c", faint: "#7d8893", rule: "#d8dfe5", fill: "#f1f4f6", ok: "#2e8c8c", hi: "#c42a18"};
var SEV = {high: P.hi, medium: P.ink2, low: P.faint, ok: P.ok};
var SERIF = 'ui-serif, Baskerville, "Iowan Old Style", Georgia, serif';
var SANS = 'Inter, system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif';
var lk = document.querySelectorAll(".score .lockup path");
var MARK = new Path2D(lk[0].getAttribute("d")), WORDS = new Path2D(lk[1].getAttribute("d"));
var SPLIT = 6, TOTAL = 7.5, T0 = 1.2, STEP = 0.4, DUR = 1;  // seconds: tiles start at T0 + i*STEP; the last 1.5 s hold
var clamp = function (x) { return Math.max(0, Math.min(1, x)); };
var ease = function (x) { return 1 - Math.pow(1 - x, 3); };
var num = function (n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); };
var tick = function (s, n) { return s.replace(/^[\d,]+/, num(n)); };

function rr(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
function wrap(c, text, w) {
  var words = text.split(" "), lines = [], l = "";
  words.forEach(function (x) { var n = l ? l + " " + x : x; if (l && c.measureText(n).width > w) { lines.push(l); l = x; } else l = n; });
  if (l) lines.push(l);
  return lines;
}

// One drawing for the image and the video. t is seconds into the clip; any t at or past TOTAL is the finished card.
function draw(c, W, t) {
  var s = W / 1200, i, a = function (t0, d) { return clamp((t - t0) / d); };
  c.setTransform(s, 0, 0, s, 0, 0); c.globalAlpha = 1; c.textBaseline = "alphabetic";
  var g = c.createLinearGradient(0, 0, 1200, 675); g.addColorStop(0, dark ? "#2f4a52" : "#3b5b66"); g.addColorStop(0.55, dark ? "#1c2a33" : "#24363f"); g.addColorStop(1, dark ? "#161f27" : "#1e2a33");
  c.fillStyle = g; c.fillRect(0, 0, 1200, 675);
  var r1 = c.createRadialGradient(0, 0, 0, 0, 0, 1000); r1.addColorStop(0, "rgba(159,195,200,.5)"); r1.addColorStop(0.55, "rgba(159,195,200,0)");
  c.fillStyle = r1; c.fillRect(0, 0, 1200, 675);
  var r2 = c.createRadialGradient(1200, 675, 0, 1200, 675, 800); r2.addColorStop(0, "rgba(95,138,145,.7)"); r2.addColorStop(0.65, "rgba(95,138,145,0)");
  c.fillStyle = r2; c.fillRect(0, 0, 1200, 675);
  rr(c, 32, 32, 1136, 611, 10); c.fillStyle = P.card; c.fill();
  c.save(); c.translate(76, 68); c.scale(22 / 219, 22 / 219); c.fillStyle = P.ink; c.fill(MARK, "evenodd"); c.translate(-28.3, 0); c.fill(WORDS); c.restore();
  c.globalAlpha = a(0.1, 0.5); c.fillStyle = P.ink; c.font = "400 38px " + SERIF; c.fillText(D.title + " check-up", 76, 150);
  c.globalAlpha = a(0.5, 0.5); c.fillStyle = P.faint; c.font = "400 20px " + SANS;
  c.fillText(tick(D.sub, Math.round(D.actions * ease(a(0.6, 1.8)))), 76, D.evidence ? 168 : 184);
  var shown = 0, firing = 0;
  D.tiles.forEach(function (x, k) { if (x.sev !== "ok") { firing++; if (t >= T0 + k * STEP) shown++; } });
  c.globalAlpha = a(1, 0.4); c.beginPath(); c.arc(80, 227, 4, 0, 7); c.fillStyle = D.ok ? P.ok : P.hi; c.fill();
  c.font = "600 20px " + SANS; c.fillStyle = P.ink; var b = D.need_b.charAt(0) >= "0" && D.need_b.charAt(0) <= "9" ? tick(D.need_b, shown) : D.need_b;
  c.fillText(b, 96, 233); c.font = "400 20px " + SANS; c.fillStyle = P.quiet; c.fillText(" " + D.need_r, 96 + c.measureText(b).width + 6, 233);
  var evidence = D.evidence || [];
  c.font = "400 15px " + SANS; c.fillStyle = P.quiet;
  evidence.forEach(function (line, j) { c.fillText(line, 76, 189 + j * 18, 1048); });
  var tw = (1048 - 40) / 5;
  D.tiles.forEach(function (x, k) {
    var gx = 76 + (k % 5) * (tw + 10), gy = 256 + Math.floor(k / 5) * 160, st = T0 + k * STEP, f = a(st, 0.3);
    c.globalAlpha = a(0.9, 0.5) * (1 - f); rr(c, gx + 0.5, gy + 0.5, tw - 1, 149, 6); c.strokeStyle = P.rule; c.lineWidth = 1; c.stroke();
    c.globalAlpha = f; rr(c, gx, gy, tw, 150, 6); c.fillStyle = P.fill; c.fill();
    if (x.sev !== "ok") { c.save(); rr(c, gx, gy, tw, 150, 6); c.clip(); c.fillStyle = SEV[x.sev]; c.fillRect(gx, gy, tw, 3); c.restore(); }
    c.fillStyle = x.sev === "ok" ? P.ok : P.ink; c.font = "400 46px " + SERIF;
    c.fillText(num(Math.round(x.n * ease(a(st, DUR)))), gx + 18, gy + 62);
    c.fillStyle = P.quiet; c.font = "400 14.5px " + SANS;
    wrap(c, x.label, tw - 36).forEach(function (l, j) { c.fillText(l, gx + 18, gy + 92 + j * 20); });
  });
  c.globalAlpha = 1; c.fillStyle = P.rule; c.fillRect(76, 592, 1048, 1);
  c.fillStyle = P.quiet; c.font = "400 15px " + SANS; c.fillText(D.foot, 76, 620);
  c.globalAlpha = a(SPLIT - 0.1, 0.4); c.fillStyle = P.ink; c.font = "600 20px " + SANS; c.textAlign = "right";
  c.fillText("Run yours free: excellent.so/scan", 1124, 622); c.textAlign = "left"; c.globalAlpha = 1;
}

function say(m) { $("sstat").textContent = m; }
function save(blob, name) {
  var u = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function () { URL.revokeObjectURL(u); }, 60000);
}
var MIME = "";
if (window.MediaRecorder && HTMLCanvasElement.prototype.captureStream) {
  ["video/mp4;codecs=avc1.640028", "video/mp4;codecs=avc1.42E01E", "video/mp4;codecs=avc1", "video/mp4"].some(function (m) { return MediaRecorder.isTypeSupported(m) && (MIME = m); });
}
var vb = $("bvid"), busy = false;
if (!MIME) { vb.hidden = true; say("This browser can't make an MP4, which is what X accepts, so Save video is off. Try Safari or Chrome. Save image still works."); }

vb.addEventListener("click", function () {
  if (busy) return; busy = true; vb.disabled = true;
  var cv = $("vid"), c = cv.getContext("2d"), chunks = [], rec;
  cv.width = 1280; cv.height = 720; cv.hidden = false; draw(c, 1280, 0);
  try { rec = new MediaRecorder(cv.captureStream(30), {mimeType: MIME, videoBitsPerSecond: 5000000}); } catch (x) { say("Could not start recording."); busy = false; vb.disabled = false; return; }
  rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
  rec.onstop = function () {
    var blob = new Blob(chunks, {type: "video/mp4"});
    save(blob, "excellent-check-up.mp4"); say("Saved excellent-check-up.mp4 (" + (blob.size / 1048576).toFixed(1) + " MB, " + TOTAL + " seconds). Check your Downloads.");
    cv.hidden = true; vb.disabled = false; busy = false; vb.textContent = "Save video";
  };
  rec.start(); var t0 = performance.now();
  (function frame() {
    var t = (performance.now() - t0) / 1000;
    draw(c, 1280, Math.min(t, TOTAL));
    vb.textContent = "Recording " + Math.min(100, Math.round(t / TOTAL * 100)) + "%";
    say("Recording the clip takes " + TOTAL + " seconds. Keep this tab in front.");
    if (t < TOTAL + 0.2) setTimeout(frame, 1000 / 30); else rec.stop();
  })();
});
$("bimg").addEventListener("click", function () {
  var cv = document.createElement("canvas"); cv.width = 1200; cv.height = 675; draw(cv.getContext("2d"), 1200, 99);
  cv.toBlob(function (b) { if (b) { save(b, "excellent-check-up.png"); say("Saved excellent-check-up.png (1200 x 675)."); } else say("Could not make the image."); }, "image/png");
});
$("bcopy").addEventListener("click", function () {
  var u = D.links.copy, done = function () { say("Copied the share link."); };
  var old = function () { var t = document.createElement("textarea"); t.value = u; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); done(); } catch (x) { say("Could not copy. Select the link and copy it."); } t.remove(); };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(u).then(done, old); else old();
});
})();'''


def tile_rows(f):  # the card's 10 tiles in display order: checks that fired first, by severity; (id, severity, count, label)
    out = []
    for c in sorted(CHECKS, key=lambda c: (c[0] not in f, ["high", "medium", "low"].index(c[1]))):
        n = f[c[0]]["count"] if c[0] in f else 0
        out.append((c[0], f[c[0]]["severity"] if c[0] in f else "ok", n, TILE_ONE[c[0]] if n == 1 else c[3]))
    return out


def checksum(canonical):  # c=: base36 of CRC32 over the canonical string, mod 36**4, 4 characters. Catches mangled links. Not security
    n, out = zlib.crc32(canonical.encode()) % 36 ** 4, ""
    for _ in range(4):
        n, d = divmod(n, 36)
        out = "0123456789abcdefghijklmnopqrstuvwxyz"[d] + out
    return out


def evidence_text(counts):
    return ", ".join("%s %s" % (fmt(n), label) for n, label in zip(counts, EMAIL_OUTCOMES) if n)


def email_evidence(f):
    return [(rid, f[rid]["evidence"]) for rid in EMAIL_RULES if rid in f and "evidence" in f[rid]]


def share_links(f, meta):  # the share link, v1, for each route: the card's numbers only, no name. s= sessions and p= agent actions per agent (a's order, sums to n) are on the card too
    letters = "".join(LETTERS[a] for a in AGENT_NAMES if AGENT_NAMES[a] in meta["agents"].split(" + "))
    k = ".".join(str(f[c[0]]["count"]) if c[0] in f else "0" for c in CHECKS)
    canon = "v=1&a=%s&n=%d&d=%d&k=%s&s=%d&p=%s" % (letters, meta["calls"], meta.get("days", 0), k, meta["sessions"], ".".join(str(x) for x in meta["split"]))
    if email_evidence(f):
        canon += "&e=" + ".".join(str(n) for rid in EMAIL_RULES for n in f.get(rid, {}).get("evidence", [0] * 5))
    return {r: "%s?%s&c=%s%s%s" % (SHARE_R, canon, checksum(canon), UTM, r) for r in ROUTES}


def need_parts(f):
    if not f:
        return "All %d" % len(CHECKS), "checks clean"
    return "%d of %d" % (len(f), len(CHECKS)), "check%s a look" % (" needs" if len(f) == 1 else "s need")


def x_post(f, meta):  # the prefilled X post, built from the top two non-zero checks in the card's labels, ending with the share link
    top = [" ".join((fmt(n), lab)) for _, _, n, lab in tile_rows(f) if n][:2]
    for rid, counts in email_evidence(f):
        for i, (key, _, _, _) in enumerate([row for row in tile_rows(f) if row[2]][:2]):
            if key == rid:
                top[i] += " (" + evidence_text(counts) + ")"
    text = X_TEXTS["some" if top else "zero"].format(top=" and ".join(top), checks=len(CHECKS), actions=plural(meta["calls"], "agent action"), link=share_links(f, meta)["x"])
    return X_POST + quote(text, safe="")


def foot_text(meta):  # the card's foot: sessions, the agent split when there are two or more agents, and the byline. Everything in the link's s= and p=
    names = [a for a in AGENT_NAMES.values() if a in meta["agents"].split(" + ")]
    split = ""
    if len(names) > 1 and len(meta["split"]) == len(names):
        parts = ["%s %s" % (fmt(x), nm) for nm, x in zip(names, meta["split"])]
        split = " \u00b7 " + (", ".join(parts[:-1]) + " and " + parts[-1]) + " actions"
    return "%s%s \u00b7 Free check by Excellent" % (plural(meta["sessions"], "session"), split)


def card_data(f, meta):  # what the card shows and nothing else: agents, counts, dates, the 10 tiles. No names, paths, commands or projects
    b, r = need_parts(f)
    evidence = [("Request or script" if rid == "email_out" else "Form or request") + " · " + evidence_text(counts) for rid, counts in email_evidence(f)]
    return {**({"evidence": evidence} if evidence else {}), "title": "My %s" % (meta["agents"] if meta["sessions"] else "AI agent"), "actions": meta["calls"],
            "sub": "%s%s" % (plural(meta["calls"], "agent action"), ", " + meta["span"] if meta["span"] else ""),
            "need_b": b, "need_r": r, "ok": not f, "foot": foot_text(meta),
            "tiles": [{"n": n, "label": lab, "sev": sev} for _, sev, n, lab in tile_rows(f)], "links": share_links(f, meta)}


def summary(f, meta):  # the block your agent shows you: agent names, counts and dates only, nothing from your files
    head = " · ".join(filter(None, ["Excellent free scan", meta["agents"], meta["span"], plural(meta["calls"], "action")]))
    rows = ["  %-40s %7s" % (c[2], fmt(f[c[0]]["count"]) if c[0] in f else "0") for c in CHECKS]
    evidence = [next(c[2] for c in CHECKS if c[0] == rid) + " — " + evidence_text(counts) for rid, counts in email_evidence(f)]
    return "\n".join([head] + rows + evidence + ["Run yours free: excellent.so/scan"])


def render(f, meta, anon=None):  # anon: replaces every real name, for a sample report (not used in a scan)
    e = lambda s: html.escape(shown(s))
    tiles = "".join('<div class="tile%s"><b>%s</b>%s</div>' % ("" if sev != "ok" else " ok", fmt(n), e(lab)) for _, sev, n, lab in tile_rows(f))
    card_evidence = "".join("<p>%s</p>" % e(line) for line in card_data(f, meta).get("evidence", []))
    cards = ""
    for c in sorted([c for c in CHECKS if c[0] in f], key=lambda c: ["high", "medium", "low"].index(f[c[0]]["severity"])):
        x, ex = f[c[0]], ""
        for s in x["examples"]:
            txt = anon.text(s) if anon else s["text"]
            proj = anon.name("project", s["project"]) if anon and s["project"] else s["project"]
            if txt:
                ex += "<li><code>%s</code><small>%s</small></li>" % (e(txt), e(" · ".join(filter(None, [
                    AGENT_NAMES[s["agent"]], day(s["ts"]), proj, ("local script input" if s.get("detail") == "script input" else {"ran": "tool reported success", "unknown": "result unknown", "failed": "tool reported failure"}.get(s["outcome"], s["outcome"]) if c[0] in EMAIL_RULES else "" if s["outcome"] == "ran" else s["outcome"])]))))
        cards += ('<details class="find %s" open><summary><span class="sev"><i></i>%s</span><h3>%s</h3><span class="n">%s</span></summary>'
                  '<div class="fb"><p class="what">%s</p><dl class="pair"><div><dt class="label">What this means</dt><dd>%s</dd></div>'
                  '<div><dt class="label">What to do</dt><dd>%s</dd></div></dl>%s%s</div></details>\n') % (
                  x["severity"], x["severity"], e(c[2]), fmt(x["count"]), e(anon.detail(x["detail"]) if anon else x["detail"]), e(c[4]), e(c[5]),
                  '<p class="app">%s<span>%s</span></p>' % (MARK, e(APP[c[0]])) if c[0] in APP else "",
                  '<div class="exs"><p class="label">Recent examples</p><ul class="ex">%s</ul></div>' % ex if ex else "")
    clean = "".join("<li>%s</li>" % e(c[2]) for c in CHECKS if c[0] not in f)
    who = "you@example.com" if anon else ", ".join(re.sub(r"^(.).*@(.).*?(\.\w+)$", r"\1•••@\2•••\3", x) for x in EMAILS) or "no email found"
    m = {k: e(fmt(v) if isinstance(v, int) else v) for k, v in meta.items() if k != "split"}
    title = e("My %s" % (meta["agents"] if meta["sessions"] else "AI agent"))
    sub = e("%s%s" % (plural(meta["calls"], "agent action"), ", " + meta["span"] if meta["span"] else ""))
    need = "<b>%d of %d</b> checks %s a look" % (len(f), len(CHECKS), "needs" if len(f) == 1 else "need") if f else "<b>All %d checks clean</b>" % len(CHECKS)
    data = json.dumps(card_data(f, meta), separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    sha = base64.b64encode(hashlib.sha256(SCRIPT_JS.encode("utf-8")).digest()).decode()
    CSP = CSP_FMT % sha
    xhref = html.escape(x_post(f, meta))
    copylink = html.escape(share_links(f, meta)["copy"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}"><meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>Your agents' check-up · Excellent</title>
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap">{LOCKUP}<span class="label">Free check-up · {m['date']}</span></div></header>
<main class="wrap"><a class="back" href="#">← Back to the full report</a>
<section class="hero"><h1>Your agents' check-up</h1><p class="lede">What your AI coding agents did on this Mac, read from their own logs on {m['date']}. This script showed your agent only a short summary: counts, agent names, dates and where this page is. Nothing else it read left this Mac.</p></section>
<section class="score" id="card"><div class="score-in">{LOCKUP}<h2>{title} <span class="nw">check-up</span><span class="sub"><span class="sep"> · </span>{sub}</span></h2><p class="need{'' if f else ' ok'}"><i></i>{need}</p>
<div class="grid">{tiles}</div>{card_evidence}<div class="foot"><small>{e(foot_text(meta))}</small><a href="{html.escape(SHARE)}">Run yours free: excellent.so/scan{ARROW}</a></div></div></section>
<p class="share"><a class="btn2" href="#card">Show only the card{ARROW}</a><span>Sized for a screenshot, and safe to share: the card holds counts, agent names and dates only, with no emails, sites, folders, commands or keys. Everything below is just for you.</span></p>
<section class="tools" id="share"><p class="label">Share your card</p>
<div class="row"><button type="button" class="btn2" id="bvid">Save video</button><button type="button" class="btn2" id="bimg">Save image</button><button type="button" class="btn2" id="bcopy">Copy share link</button><a class="btn2" href="{xhref}" target="_blank" rel="noopener noreferrer">Post on X{ARROW}</a></div>
<p class="hint">Attach the video you just saved. The post already has your link in it.</p>
<code id="lnk">{copylink}</code><p id="sstat" class="hint" role="status"></p><canvas id="vid" hidden></canvas>
<p class="hint">This page sends nothing. Save video and Save image make the file on your Mac. The share link holds the card's numbers only: counts, agent names, the days your logs span, your session count and your agent actions per agent. It has no name, path or email.</p></section>
<section class="sec" id="found"><div class="head"><p class="label">Just for you <span class="pill">Private</span></p><h2>What we found</h2><p class="lede">What happened, why it matters, and what you can do yourself. Examples are masked: your email shows as ‹your email›.</p></div>
{cards or '<p class="lede">Nothing to flag. Your agents passed every check.</p>'}
{'<div class="cleanbox"><p class="label">Came back clean</p><ul class="clean">%s</ul></div>' % clean if clean else ''}</section>
<section class="cta" id="mac"><div><p class="label">{MARK}Excellent for Mac</p><h2>Manage at agent speed</h2><p class="lede">Your agents run hundreds of steps you never see. Excellent holds every one to your rules, and stops the risky ones or asks you first.</p>
<div class="go"><a class="btn" href="{html.escape(DOWNLOAD)}">Get Excellent for Mac{ARROW}</a><p class="fine">Scanning is free. With Pro, it blocks or asks before the risky actions it checks for.</p></div></div>
<ul class="tiers"><li><span class="pill solid">Free</span><b>See what your agents did</b><p>This page is a one-time look back. Excellent for Mac shows the same findings whenever you scan, with no account needed.</p></li>
<li><span class="pill">Pro</span><b>Stop it as it happens</b><p>It blocks or asks before risky actions, turns your rules into the Mac's own sandbox, scans in the background and alerts you.</p><p>Pro is $6 a month or $60 a year. Pro is sold in the US for now.</p></li>
<li class="req"><p>For Macs with Apple silicon and macOS 14 or later. Excellent for Mac today; a version for Linux servers comes next, then Windows.</p></li></ul></section>
<section class="sec" id="how"><div class="head"><p class="label">Method and privacy</p><h2>It all ran on your Mac</h2><p class="lede">This page sends nothing and loads nothing. Its one small script only draws your card on this page. The script printed a short summary for your agent.</p></div><div class="method">
<div><h3>How this check worked</h3><p>Your agent saved a Python script where you could read it (~/excellent-free-scan/scan.py), checked it, and ran it. It read {e(plural(meta['sessions'], 'session'))} ({m['gb']} of logs) in {m['secs']}, {e(plural(meta['rulefiles'], 'instruction file'))} with {e(plural(meta['rules'], 'rule'))} it can check (never delete, never open, never run), and your hook settings. It looked for {e(who)} as your email.</p></div>
<div><h3>What it never did</h3><p>It used no network and changed no file except this page. It kept no key or email, and never opened Documents, Desktop, Downloads, iCloud, Pictures, Movies, Music, the Mail, Messages, Safari and Photos data or app containers in Library, other drives, or a folder your rules name as never to open or read, once it had read that rule. This page loads nothing and sends nothing: Save video and Save image make the file on your Mac, and the share link holds the card's numbers only.</p></div>
<div><h3>Limits</h3><p>Logs go back only as far as your agents keep them (Claude Code: 30 days unless you change it). Keys count only when they have a known shape; test and example keys are left out. The rules are the Excellent app's, simplified, so counts can differ a little.</p></div>
<div><h3>To delete this page</h3><p><code>rm -r ~/excellent-free-scan</code></p></div></div></section></main>
<footer><div class="wrap">{LOCKUP}<span>A free check by Excellent · {m['date']}</span></div></footer>
<script type="application/json" id="card-data">{data}</script><script>{SCRIPT_JS}</script></body></html>"""


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
    email_calls = {}
    for r in results:
        if r["agent"] == "grok":
            r["start"], r["end"] = heads[r["path"]][1:]
        for ev in r["events"]:
            if (ev["rule"] in EMAIL_RULES or ev["outcome"] != "blocked") and not ev["untold"]:
                ev.update(agent=r["agent"], project=project_of(r["cwd"]), ts=ev["ts"] or r["start"])
                if ev["rule"] in EMAIL_RULES and ev["call"] and ev["ts"]:
                    key = (r["agent"], ev["call"], ev["ts"], ev["rule"], ev["detail"])
                    old = email_calls.get(key)
                    if old is None or (old["outcome"] == "unknown" and ev["outcome"] != "unknown"):
                        email_calls[key] = ev
                else:
                    by.setdefault(ev["rule"], []).append(ev)
    for ev in email_calls.values():
        by.setdefault(ev["rule"], []).append(ev)
    n = plural
    last = lambda l: day(max(x["ts"] for x in l)) or "recently"

    def add(rid, evs, detail, sev=None, examples=None):
        seen, ex = set(), []
        for x in sorted(evs, key=lambda x: x["ts"], reverse=True) if examples is None else []:
            key = (x["text"][:70], x["outcome"])
            if key not in seen and len(ex) < 3:
                seen.add(key)
                ex.append(x)
        f[rid] = {"count": len(evs), "detail": detail, "examples": ex if examples is None else examples,
                  "severity": sev or next(c[1] for c in CHECKS if c[0] == rid)}
    for rule in EMAIL_RULES:
        events = by.get(rule, [])
        if events:
            counts = [0] * len(EMAIL_OUTCOMES)
            for ev in events:
                index = 0 if ev["detail"] == "script input" else {"failed": 2, "blocked": 3, "ran": 4}.get(ev["outcome"], 1)
                counts[index] += 1
            detail = evidence_text(counts) + ". These local records do not establish receipt by a website."
            add(rule, events, detail)
            f[rule]["evidence"] = counts
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
    span = (datetime.strptime(days[-1], "%Y-%m-%d") - datetime.strptime(days[0], "%Y-%m-%d")).days + 1 if days else 0  # the days the logs span, first and last day included
    meta = {"date": datetime.now().strftime("%B %-d, %Y"), "sessions": len(results), "calls": sum(r["calls"] for r in results),
            "agents": " + ".join(AGENT_NAMES[a] for a in AGENT_NAMES if any(r["agent"] == a for r in results)) or "no agent logs found",
            "split": [sum(r["calls"] for r in results if r["agent"] == a) for a in AGENT_NAMES if any(r["agent"] == a for r in results)],  # agent actions per agent, in the card's agent order (the link's p=)
            "span": "%s – %s" % (day(days[0]), day(days[-1])) if days else "", "days": span, "secs": n(round(time.time() - t0), "second"),
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
