#!/usr/bin/env python3
# Writes share-format.json from scan.py's CHECKS, so the share link's spec and the code can't drift. The site lane reads it.
# Usage: python3 build_share_format.py   (tests/share_test.py fails if the file is out of date)
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan


EX_META = {"calls": 340, "days": 18, "agents": "Claude Code + Codex", "sessions": 12, "split": [200, 140]}
EX_THREE = {"calls": 1204, "days": 31, "agents": "Claude Code + Codex + Grok Build", "sessions": 87, "split": [700, 380, 124]}
EX_NONE = {"calls": 0, "days": 0, "agents": "no agent logs found", "sessions": 0, "split": []}
EX_FOUND = {"secrets_in_logs": {"count": 4}, "force_push": {"count": 1}}
EX_THREE_FOUND = {"email_out": {"count": 17}, "secrets_in_logs": {"count": 3}, "written_rules": {"count": 5}, "secret_files": {"count": 12}, "publish_deploy": {"count": 2}}


def example(f, meta=EX_META):
    links = scan.share_links(f, meta)
    canon = links["copy"].split("?", 1)[1].split("&c=")[0]
    return {"canonical": canon, "c": scan.checksum(canon), "links": links}


def build():
    return {
        "format": "excellent-free-scan share link",
        "version": 1,
        "url": "https://excellent.so/r",
        "link_template": "https://excellent.so/r?v=1&a=<a>&n=<n>&d=<d>&k=<k>&s=<s>&p=<p>&c=<c>&utm_source=free-scan&utm_medium=share&utm_campaign=launch&utm_content=<x|linkedin|copy|video|image>",
        "params": {
            "v": "format version, always 1",
            "a": "agent letters in card order: c = Claude Code, x = Codex, g = Grok Build. Empty when no agent logs were found",
            "n": "agent actions read (integer)",
            "d": "days the logs span, first and last day included (integer; 0 when no dates)",
            "k": "the 10 counts in CHECKS order (the order of the 'checks' list below, NOT the card's display order), dot-separated",
            "s": "sessions read (integer). Added with p; the card's footer shows it. Optional: links without s and p stay valid",
            "p": "agent actions per agent, dot-separated, in the same order as the letters in a, so it has one number per letter and the numbers sum to n. Empty when a is empty (then n is 0). s and p come together or not at all. The card's footer shows the split when two or more agents were read",
            "c": "4-character checksum, see 'checksum'. Catches truncated or mangled links. It is not security and must never be described as security: the scan holds no secret, so anyone can make a valid link",
            "utm_source": "free-scan", "utm_medium": "share", "utm_campaign": "launch",
            "utm_content": "which share button made the link: x (Post on X), copy (Copy share link), video, image, linkedin. The report page today uses x and copy; the others are reserved for the site and later buttons"},
        "no_name": "There is no name parameter. Nothing in the link, the card, the video or the image carries a name.",
        "checksum": {
            "canonical": "v=1&a=<a>&n=<n>&d=<d>&k=<k>&s=<s>&p=<p> (a link without s and p, the first v1 links, uses v=1&a=<a>&n=<n>&d=<d>&k=<k>): this param order, the values exactly as they appear in the link, no URL-encoding (every character is already URL-safe)",
            "c": "zlib.crc32(canonical.encode()) % 36**4, written in base36 with digits 0-9a-z, lowercase, left-padded with '0' to 4 characters",
            "python": "n = zlib.crc32(canonical.encode()) % 36**4; c = ''.join('0123456789abcdefghijklmnopqrstuvwxyz'[(n // 36**i) % 36] for i in (3, 2, 1, 0))"},
        "examples": {
            "with_findings": dict(example(EX_FOUND), meta={"agents": "Claude Code + Codex", "actions": 340, "days": 18, "sessions": 12, "actions_per_agent": [200, 140], "counts_by_id": {"secrets_in_logs": 4, "force_push": 1}}),
            "all_zero": dict(example({}), meta={"agents": "Claude Code + Codex", "actions": 340, "days": 18, "sessions": 12, "actions_per_agent": [200, 140], "counts_by_id": {}}),
            "three_agents": dict(example(EX_THREE_FOUND, EX_THREE), meta={"agents": "Claude Code + Codex + Grok Build", "actions": 1204, "days": 31, "sessions": 87, "actions_per_agent": [700, 380, 124], "counts_by_id": {k: v["count"] for k, v in EX_THREE_FOUND.items()}}),
            "no_agents": dict(example({}, EX_NONE), meta={"agents": "none", "actions": 0, "days": 0, "sessions": 0, "actions_per_agent": [], "counts_by_id": {}}),
            "first_v1_without_s_and_p": {"canonical": "v=1&a=cx&n=340&d=18&k=0.0.4.0.1.0.0.0.0.0", "c": scan.checksum("v=1&a=cx&n=340&d=18&k=0.0.4.0.1.0.0.0.0.0"), "note": "The first v1 links had no s and p. The site keeps accepting them and shows no session count or agent split for them. The scan no longer makes them."}},
        "agents": {"c": "Claude Code", "x": "Codex", "g": "Grok Build"},
        "checks": [{"index": i, "id": c[0], "severity": c[1], "title": c[2], "label": c[3], "label_one": scan.TILE_ONE[c[0]]}
                   for i, c in enumerate(scan.CHECKS)],
        "notes": ["label is the card tile's text for any count except 1; label_one is the text for a count of 1.",
                  "The card shows tiles with a count first, by severity, then the rest; the link always uses the CHECKS order.",
                  "Nothing in the link is an account name, path, email, command, project name or time of day. s and p are counts too: no dates of findings, no per-day activity, no hours."],
        "x_post_text": scan.X_TEXTS,
    }


if __name__ == "__main__":
    with open(os.path.join(HERE, "share-format.json"), "w", encoding="utf-8") as f:
        json.dump(build(), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("share-format.json written")
