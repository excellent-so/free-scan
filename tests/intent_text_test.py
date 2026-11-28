#!/usr/bin/env python3
# Checks intent_scan.py's reading of what agents wrote: every case from the engine's text.rs tests (each one a false
# positive fixed there), plus the rules this script adds for logs-only checks. Reads no logs, writes nothing.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import intent_scan as s
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    ok or fails.append(what)


def kinds(t):
    return [k for x in s.sentences(t) for k in s.claims_in(x)]


# text.rs check_claims
check(kinds("All tests pass.") == ["checks"], "\"All tests pass.\" is a checks claim")
check(kinds("The build is green and lint passes.") == ["checks"], "build green and lint passes is one checks claim")
for t in ("Tests are failing on CI.", "I will make sure the tests pass.", "Do the tests pass?", "The tests probably pass.",
          "Run `cargo test` and check that \"all tests pass\" appears.", "```\nall tests pass\n```"):
    check(kinds(t) == [], "not a claim: %r" % t)
# completion
check(kinds("Done — the feature is implemented.") == ["done"], "\"Done — the feature is implemented.\" is a completion claim")
check(kinds("I've implemented the parser.") == ["done"], "\"I've implemented the parser.\" is a completion claim")
check(kinds("- [x] Implemented the parser") == ["done"], "a checked box is a completion claim")
check("done" not in kinds("I haven't implemented the parser yet."), "\"I haven't implemented\" is not a completion claim")
# approval
check(kinds("Approved by the lead.") == ["approval"], "\"Approved by the lead.\" is an approval claim")
check(kinds("The review agent approved the change.") == ["approval"], "a review agent's approval is an approval claim")
check(kinds("This needs approval from the lead.") == [], "\"needs approval\" is not an approval claim")
check(kinds("Manual-review requirements can be approved from the app.") == [], "fixed here: \"can be approved from\" says what is possible")
check(kinds("Everything must be signed off by the owner first.") == [], "fixed here: \"must be signed off\" is not a claim")
# rules and pending decisions
check(s.is_rule("Attribute C is a protected trait; block by default unless a lead approves."), "a protected-trait default block is a rule")
check(s.is_rule("Never match on skin tone."), "\"Never match on skin tone.\" is a rule")
check(not s.is_rule("The matcher ranks candidates by score."), "a description is not a rule")
check(s.is_pending_decision("Block by default unless a lead approves; pending approval."), "\"unless a lead approves; pending approval\" is pending")
check(s.is_pending_decision("This needs sign-off from product."), "\"needs sign-off from product\" is pending")
check(not s.is_pending_decision("The lead approved this."), "a past approval is not pending")
# objections
check(s.objection_in("I won't implement the C filter because it raises fairness concerns."), "\"I won't implement\" is an objection")
check(s.objection_in("I can't add this filter: it may be unlawful under fair housing rules."), "\"I can't add\" is an objection")
check(s.objection_in("I didn't implement caching because the API has no ETags."), "\"I didn't implement\" is an objection (a limitation)")
check(not s.objection_in("I implemented the filter."), "\"I implemented\" is not an objection")
# constraints
check((s.constraint_in("Do not make design calls.") or [None])[0] == "decisions", "\"Do not make design calls.\" forbids decisions")
c = s.constraint_in("Don't modify the scoring weights file.")
check(c and c[0] == "touch" and "scoring" in c[1] and "weight" in c[1], "\"Don't modify the scoring weights file.\" names scoring, weight")
check(s.constraint_in("Make the tests pass.") is None, "\"Make the tests pass.\" is no constraint")
# terms
a = s.terms("Attribute C is a protected trait; block skin tone by default")
b = s.terms("BLOCKED_ATTRIBUTES = [\"skin_tone\"]  # protected trait")
check("skin" in a and "tone" in b, "terms split skin_tone and drop plurals")
check(s.same_rule(s.terms("skin tone protected trait"), s.terms("protected_traits = {skin_tone}")), "same rule across prose and code")
check(not s.same_rule(s.terms("hair colour preference"), s.terms("protected trait skin tone")), "different rules stay apart")
# relayed words (a real research sub-agent's sentences)
check(kinds("A planning sub-agent labelled ethnicity a protected trait and blocked it by default unless leadership approved, the post says.") == [], "relayed: \"the post says\"")
check(not s.is_rule("The timeline says a planner labelled the trait protected and blocked it by default."), "relayed: \"the timeline says\" is not a rule")
check(not s.is_pending_decision("He alleges Claude's notes marked the ban as pending approval from a lead."), "relayed: \"he alleges\" is not pending")
check(kinds("Many developer postmortems describe agents deleting or weakening tests to get CI green.") == [], "relayed: postmortems describe")
check(kinds("Tests or thresholds weakened so checks pass.") == [], "purpose clause: \"so checks pass\"")
check(not s.objection_in("The engineer said I won't implement it because it is unfair."), "relayed: \"the engineer said\" is not an objection")
# talking about pending decisions is not one
check(not s.is_pending_decision("Policy rules: an open objection or pending decision forces HOLD."), "talk about \"pending decision\" is not one")
check(not s.is_pending_decision("what was decided on: a rule id, finding subject, pending decision or objection"), "a field list is not pending")
check(s.is_pending_decision("Pending approval from a lead."), "\"Pending approval from a lead.\" is pending")
check(s.is_pending_decision("Block C by default unless a lead approves."), "\"unless a lead approves\" is pending")
check(not s.is_pending_decision("A planning sub-agent labelled the trait protected and blocked it by default unless leadership approved."), "narrated past is not pending")
# reviewer flags
check(s.is_reviewer_flag("HIGH severity: this violates the preference requirement."), "HIGH severity is a flag")
check(not s.is_reviewer_flag("I will check for regressions."), "\"I will check for regressions.\" is not a flag")
check(s.is_review_role("code-review") and s.is_review_role("Bug review of intent crate") and not s.is_review_role("general-purpose"), "review roles")
# code rules (artifacts.rs code_rules)
for l in ("BLOCKED_ATTRIBUTES = {\"B\", \"C\"}  # protected traits", "    if k in ATTRS and k not in BLOCKED_ATTRIBUTES}", "const PROTECTED_TRAITS: &[&str] = &[\"c\"];",
          "excluded_preferences = set(cfg.get(\"x\"))", "# block C by default unless a lead approves; pending approval from a lead"):
    check(s.code_rule_line(l), "code rule: %r" % l)
for l in ("/// globs the candidate must not change at all (D10 → BLOCK)", "//! Missing or unknown evidence is HOLD, never ALLOW.",
          r'rx!(r_rule, r"(?i)\b(block-?list|deny(?:-?list)?|DENY_LIST)\b");', "let msg = \"BLOCKED_ATTRIBUTES must not be empty\";", "# never use eval here"):
    check(not s.code_rule_line(l), "not a code rule: %r" % l)

# ---- rules this script adds (logs-only false positives, each found or foreseen on real logs) ----
check(kinds("I re-checked r7 on a fresh debug build of 59271fb, then did a systematic pass over every git command.") == [], "fixed here: \"a systematic pass over\" is a noun")
check(kinds("A check that runs zero tests and exits 0 is a PASS.") == [] and kinds("**Empty or zero-test suites pass.** Fix: a minimum count.") == [],
      "fixed here: a reviewer describing what counts as a pass is not a claim")
check(kinds("Tests I ran:** all passed.") == ["checks"] and kinds("The tests all pass.") == ["checks"], "real claims stay claims")
check(s.constraint_in("Unsupported filters must not remove otherwise valid records.") is None, "a product requirement with a subject is not an instruction")
check(s.constraint_in("Do not modify any other file.") is None and s.constraint_in("Do not touch any branch other than yours.") is None,
      "\"any other file\" names nothing the logs can check")
c = s.constraint_in("Do NOT touch scan.py, PROMPT.md, share-format.json or the existing SHA256SUMS line for scan.py.")
check(c and c[0] == "touch" and c[2][:3] == ["scan.py", "prompt.md", "share-format.json"], "named files are kept whole (scan.py, PROMPT.md)")
c = s.constraint_in("**Constraints:** you must not edit config/weights.json.")
check(c and c[2] == ["config/weights.json"], "an instruction after a label, with a path")
check(s.test_run("cat > notes.md <<'EOF'\ncargo test\nEOF") is None, "a heredoc's text is not a test run")
check(s.test_run('grep -rn "cargo test" docs') is None and s.test_run("echo pytest") is None, "a command that names a test runner is not a run")
check(s.test_run("cd x && timeout 500 bun test tests/ 2>&1 | tail -3") is False, "a whole-suite run through timeout and a pipe")
check(s.test_run('bash -lc "pytest -k parser"') is True, "bash -lc pytest -k is a narrowed run")
check(s.test_run("npx jest -t parser") is True and s.test_run("cargo test -p excellent-intent spike") is True, "a named test is a narrowed run")
check(s.test_run("cargo test --workspace") is False and s.test_run("python3 -m unittest -q tests.test_matcher") is False, "whole runs")
check(s.test_run("python3 tests/home_test.py") is False, "a test script run directly is a run, not a narrowed one")
check(s.test_run('for t in tests/*_test.py; do python3 "$t" || exit 1; done') is False, "a loop over test scripts is a run")
check(s.test_run("for f in src/*.py; do python3 $f; done") is None, "a loop over source files is not a test run")
check(s.verify_run("cargo build --release") and s.verify_run("gh pr checks 12") and s.verify_run("cd app && npm run lint"), "a build, lint or CI look backs a build or CI report")
check(not s.verify_run('grep -rn "cargo build" docs') and not s.verify_run("echo make"), "naming a build tool is not a build")
check(s.piped("cargo test 2>&1 | grep -E 'FAILED'") and not s.piped("cargo test && echo ok") and not s.piped("cargo test || true"),
      "a test run piped into grep exits with grep's status")
check(s.edits_of("exec_command", {"cmd": "cd /r && apply_patch <<'EOF'\n*** Begin Patch\n*** Update File: m.py\n+X = 1\n*** End Patch\nEOF\n"}) == [("/r/m.py", "X = 1\n", "")],
      "Codex shell apply_patch is an edit, with its directory")
check(s.added_lines("a\nBLOCKED = {1}\nb", "a\nb") == ["BLOCKED = {1}"], "an Edit adds only the lines that weren't there")
# ---- the report reads right at 1 and at 2 (rendered in memory, as plural_test.py does for scan.py) ----
import html as _html, re as _re
meta = {"date": "November 28, 2026", "sessions": 1, "subs": 1, "calls": 1, "agents": "Claude Code", "span": "Nov 28 \u2013 Nov 28", "secs": "1 second", "gb": "0.0 GB"}
for n in (1, 2):
    f = {c[0]: {"count": n, "detail": s.detail(c[0], n), "examples": [], "severity": "ok" if c[1] == "ok" else c[1]} for c in s.CHECKS}
    page = _html.unescape(_re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", _re.sub(r"<style>.*?</style>", "", s.render(f, dict(meta, sessions=n, subs=n, calls=n)), flags=_re.S))))
    text = page + "\n" + s.summary(f, dict(meta, sessions=n))
    bad = _re.findall(r"(?<![\d,.])1 (?:reports|rules|decisions|instructions|warnings|objections|sessions|sub-agents|agent actions|approvals)\b", text) if n == 1 else \
        _re.findall(r"(?<![\d,.])2 (?:report|rule|decision|instruction|warning|objection|session|sub-agent|agent action|approval)\b(?!s)", text)
    check(not bad, "counts of %d read right in the report and summary (%s)" % (n, bad))
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
