"""Full link check across all repos: relative files, cross-repo GitHub links (incl. pinned
commits and branches), and #anchors against GitHub's heading slugs. External URLs are listed."""
import os, re, subprocess, urllib.parse, json, collections

ROOT = "/home/claude/repos"
OWNER = "Jim-dc95811"
repos = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d, ".git")))
lower = {r.lower(): r for r in repos}


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=os.path.join(ROOT, repo), capture_output=True, text=True).stdout


files = {r: set(git(r, "ls-files").split("\n")) - {""} for r in repos}


def slugs(repo, path, ref="HEAD"):
    """GitHub-style anchors for every markdown heading (and explicit id/name anchors)."""
    text = git(repo, "show", f"{ref}:{path}")
    out, seen = set(), collections.Counter()
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            h = re.sub(r"<[^>]+>", "", m.group(2))
            h = re.sub(r"[`*_~\[\]()]", "", h) if False else h
            s = h.strip().lower()
            s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE).replace(" ", "-")
            n = seen[s]; seen[s] += 1
            out.add(s if n == 0 else f"{s}-{n}")
    for m in re.finditer(r'(?:id|name)="([^"]+)"', text):
        out.add(m.group(1))
    return out


def exists(repo, path, ref="HEAD"):
    if path in ("", "."):
        return True
    t = git(repo, "cat-file", "-t", f"{ref}:{path}").strip()
    return t in ("blob", "tree")


link_re = re.compile(r'\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)|(?:src|href)\s*=\s*"([^"]+)"')
problems, external, checked = [], collections.defaultdict(set), 0

for r in repos:
    for f in sorted(files[r]):
        if not f.endswith((".md", ".html", ".txt")):
            continue
        text = open(os.path.join(ROOT, r, f), encoding="utf-8", errors="replace").read()
        for m in link_re.finditer(text):
            url = (m.group(1) or m.group(2)).strip()
            if url.startswith("mailto:"):
                continue
            checked += 1
            where = f"{r}/{f}"
            gh = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)(?:/(blob|tree|raw)/([^/]+)/?([^#?]*))?(?:#(.*))?$", url)
            if gh and gh.group(1).lower() == OWNER.lower():
                repo = lower.get(gh.group(2).lower())
                if not repo:
                    problems.append((where, url, "repository not found")); continue
                ref = gh.group(4) or "HEAD"
                if ref not in ("HEAD", "main"):
                    if not git(repo, "cat-file", "-t", ref).strip():
                        subprocess.run(["git", "fetch", "-q", "origin", ref], cwd=os.path.join(ROOT, repo))
                    if not git(repo, "cat-file", "-t", ref).strip():
                        problems.append((where, url, f"ref {ref} not found")); continue
                path = urllib.parse.unquote(gh.group(5) or "")
                if not exists(repo, path, ref if ref != "main" else "HEAD"):
                    problems.append((where, url, f"file not in {repo}@{ref}")); continue
                anchor = gh.group(6)
                target = path if path.endswith(".md") else ("README.md" if path in ("", ) else None)
                if anchor and target and anchor not in slugs(repo, target, ref if ref != "main" else "HEAD"):
                    problems.append((where, url, f"no heading #{anchor}"))
                continue
            if re.match(r"^[a-z]+://", url) or url.startswith("//"):
                external[url].add(where); continue
            # relative link
            path, _, anchor = url.partition("#")
            path = urllib.parse.unquote(path.split("?")[0])
            target = os.path.normpath(os.path.join(os.path.dirname(f), path)) if path else f
            if target.startswith(".."):
                problems.append((where, url, "points outside the repo")); continue
            if not exists(r, target):
                problems.append((where, url, "file missing")); continue
            if anchor and target.endswith(".md") and anchor not in slugs(r, target):
                problems.append((where, url, f"no heading #{anchor}"))

print(f"links checked: {checked}  internal problems: {len(problems)}  external URLs: {len(external)}")
for p in problems:
    print("PROBLEM", " | ".join(p))
json.dump({u: sorted(w) for u, w in external.items()}, open("/tmp/claude-0/-home-claude/0538666f-0b95-5128-958e-e4b3b04f84fa/scratchpad/external_urls.json", "w"), indent=1)
