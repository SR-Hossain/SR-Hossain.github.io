"""Refresh stats.json with current Codeforces and LeetCode numbers.

Run daily by .github/workflows/stats.yml. If a platform can't be reached,
its previous numbers are kept so the site never shows empty values.
"""
import collections
import datetime
import json
import pathlib
import urllib.request

CF_HANDLE = "ssh.rezvi"
LC_USER = "sshrezvi"
OUT = pathlib.Path(__file__).with_name("stats.json")


def fetch(url, payload=None):
    headers = {"User-Agent": "sshrezvi-portfolio-stats"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers.update({"Content-Type": "application/json", "Referer": "https://leetcode.com"})
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def codeforces():
    base = "https://codeforces.com/api/"
    info = fetch(f"{base}user.info?handles={CF_HANDLE}")["result"][0]
    contests = fetch(f"{base}user.rating?handle={CF_HANDLE}")["result"]
    subs = fetch(f"{base}user.status?handle={CF_HANDLE}")["result"]
    solved = {}
    for s in subs:
        if s.get("verdict") == "OK":
            p = s["problem"]
            solved[(p.get("contestId"), p.get("index"))] = p
    rated = [p for p in solved.values() if p.get("rating")]
    hist = collections.Counter(p["rating"] for p in rated)
    top = sorted(rated, key=lambda p: (-p["rating"], -(p.get("contestId") or 0)))[:6]
    return {
        "handle": CF_HANDLE,
        "rank": info.get("rank", ""),
        "rating": info.get("rating", 0),
        "maxRank": info.get("maxRank", ""),
        "maxRating": info.get("maxRating", 0),
        "contests": len(contests),
        "solved": len(solved),
        "solved1700": sum(1 for p in rated if p["rating"] >= 1700),
        "solved2000": sum(1 for p in rated if p["rating"] >= 2000),
        "hist": [[r, hist[r]] for r in range(800, max(hist or [800]) + 100, 100)],
        "hardest": [
            {
                "rating": p["rating"],
                "name": p["name"],
                "url": f"https://codeforces.com/problemset/problem/{p.get('contestId')}/{p.get('index')}",
                "tags": p.get("tags", [])[:3],
            }
            for p in top
        ],
    }


def leetcode():
    q = """query($u:String!){matchedUser(username:$u){submitStatsGlobal{acSubmissionNum{difficulty count}}}
    userContestRanking(username:$u){rating attendedContestsCount}}"""
    d = fetch("https://leetcode.com/graphql", {"query": q, "variables": {"u": LC_USER}})["data"]
    counts = {x["difficulty"]: x["count"] for x in d["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]}
    out = {
        "user": LC_USER,
        "solved": counts.get("All", 0),
        "easy": counts.get("Easy", 0),
        "medium": counts.get("Medium", 0),
        "hard": counts.get("Hard", 0),
    }
    rank = d.get("userContestRanking")
    if rank and rank.get("attendedContestsCount"):
        out["contestRating"] = round(rank["rating"])
        out["contests"] = rank["attendedContestsCount"]
    return out


def main():
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    new = dict(old)
    for key, fn in (("codeforces", codeforces), ("leetcode", leetcode)):
        try:
            new[key] = fn()
        except Exception as e:  # keep last good numbers
            print(f"{key}: kept previous data ({e})")
    new["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    OUT.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: new[k] for k in new if k != "codeforces"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
