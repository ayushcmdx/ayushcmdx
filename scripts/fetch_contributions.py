#!/usr/bin/env python3
"""
Scrape real daily contribution counts and account metrics from GitHub's public endpoints:
- Calendar & Streak data: https://github.com/users/<username>/contributions
- Account metrics: GitHub REST & Search APIs (unauthenticated)
  - Commits (365 days): search/commits?q=author:{username}+committer-date:>{since_date}
  - Merged PRs: search/issues?q=author:{username}+type:pr+is:merged
  - Total PRs: search/issues?q=author:{username}+type:pr
  - Code Reviews: search/issues?q=reviewed-by:{username}+type:pr
  - Issues: search/issues?q=author:{username}+type:issue
  - Public Repositories: users/{username} (public_repos field)
  - Stars Earned: users/{username}/repos (sum of stargazers_count across public repos)

Outputs to data/contributions.json.
Gracefully preserves existing metrics if API rate limits or network issues occur.
"""
import datetime
import json
import os
import re
import sys
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(__file__)
USERNAME = os.environ.get("GH_PROFILE_USER", "ayushcmdx")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(HERE, "..", "data", "contributions.json")


def fetch_days(username=USERNAME, timeout=25):
    """Fetch and parse calendar days from GitHub public contributions HTML."""
    target_url = f"https://github.com/users/{username}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error fetching contributions for {username}: {exc}", file=sys.stderr)
        raise

    soup = BeautifulSoup(resp.text, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        msg = f"No calendar cells found for user '{username}' - GitHub markup may have changed or user not found."
        print(msg, file=sys.stderr)
        raise ValueError(msg)

    days = []
    for td in cells:
        date_str = td.get("data-date")
        if not date_str:
            continue

        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else (td.get("aria-label") or "")

        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            match = re.search(r"(\d+)\s+contribution", text, re.I)
            if not match:
                match = re.match(r"(\d+)", text)
            count = int(match.group(1)) if match else 0

        days.append({"date": date_str, "count": count})

    # Sort deterministically by date
    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days):
    """
    Compute current streak:
    - If today has 0 contributions, but yesterday had >0, streak continues through yesterday.
    - If today has >0 contributions, streak includes today.
    """
    if not days:
        return 0, None, None

    idx = len(days) - 1
    # Check if today is empty; if so, start evaluation from yesterday
    if days[idx]["count"] == 0:
        idx -= 1

    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1

    start_idx = idx + 1
    if streak == 0 or end_idx < 0:
        return 0, None, None

    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days):
    """Compute longest consecutive run of days with count > 0."""
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None

    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0

    return longest, longest_start, longest_end


def fetch_account_stats(username=USERNAME, existing_stats=None, timeout=12):
    """
    Fetch public account metrics via GitHub public API:
    - Commits in last 365 days (search/commits)
    - Total PRs created (search/issues?q=author:{username}+type:pr)
    - Merged PRs authored (search/issues?q=author:{username}+type:pr+is:merged)
    - Code reviews submitted (search/issues?q=reviewed-by:{username}+type:pr)
    - Issues created (search/issues?q=author:{username}+type:issue)
    - Public repositories (users/{username})
    - Stars earned (sum across repos?per_page=100)

    If a request fails (e.g. rate limit), falls back to existing_stats rather than 0.
    """
    stats = existing_stats.copy() if existing_stats else {
        "public_repos": None,
        "total_stars": None,
        "total_prs": None,
        "merged_prs": None,
        "commits_365d": None,
        "code_reviews": None,
        "total_issues": None,
        "scope": "public activity",
        "counting_method": "GitHub Search API (trailing 365 days for commits; public repos and PRs)",
    }
    headers = {
        "User-Agent": "profile-readme-bot/1.0",
        "Accept": "application/vnd.github.cloak-preview+json, application/vnd.github.v3+json",
    }
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    # 1. User info for public repos
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["public_repos"] = r.json().get("public_repos", stats.get("public_repos"))
        else:
            print(f"Notice: GitHub users API returned {r.status_code}, retaining previous repo count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch public repos: {exc}", file=sys.stderr)

    # 2. Public repositories for star count
    try:
        r = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100&type=owner", headers=headers, timeout=timeout)
        if r.status_code == 200:
            repos = r.json()
            if isinstance(repos, list):
                stats["total_stars"] = sum(repo.get("stargazers_count", 0) for repo in repos)
        else:
            print(f"Notice: GitHub repos API returned {r.status_code}, retaining previous star count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch total stars: {exc}", file=sys.stderr)

    # 3. Pull requests created (Total)
    try:
        r = requests.get(f"https://api.github.com/search/issues?q=author:{username}+type:pr", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["total_prs"] = r.json().get("total_count", stats.get("total_prs"))
        else:
            print(f"Notice: GitHub PR search returned {r.status_code}, retaining previous PR count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch PR count: {exc}", file=sys.stderr)

    # 4. Merged Pull Requests authored by user
    try:
        r = requests.get(f"https://api.github.com/search/issues?q=author:{username}+type:pr+is:merged", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["merged_prs"] = r.json().get("total_count", stats.get("merged_prs"))
        else:
            print(f"Notice: GitHub merged PR search returned {r.status_code}, retaining previous merged PR count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch merged PR count: {exc}", file=sys.stderr)

    # 5. Commits in last 365 days (trailing window)
    try:
        since_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
        r = requests.get(f"https://api.github.com/search/commits?q=author:{username}+committer-date:>{since_date}", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["commits_365d"] = r.json().get("total_count", stats.get("commits_365d"))
        else:
            print(f"Notice: GitHub commit search returned {r.status_code}, retaining previous commit count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch commits count: {exc}", file=sys.stderr)

    # 6. Code reviews submitted on public PRs
    try:
        r = requests.get(f"https://api.github.com/search/issues?q=reviewed-by:{username}+type:pr", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["code_reviews"] = r.json().get("total_count", stats.get("code_reviews"))
        else:
            print(f"Notice: GitHub reviews search returned {r.status_code}, retaining previous review count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch reviews count: {exc}", file=sys.stderr)

    # 7. Issues created
    try:
        r = requests.get(f"https://api.github.com/search/issues?q=author:{username}+type:issue", headers=headers, timeout=timeout)
        if r.status_code == 200:
            stats["total_issues"] = r.json().get("total_count", stats.get("total_issues"))
        else:
            print(f"Notice: GitHub issue search returned {r.status_code}, retaining previous issue count", file=sys.stderr)
    except Exception as exc:
        print(f"Warning: Failed to fetch issue count: {exc}", file=sys.stderr)

    stats["scope"] = "public activity"
    stats["counting_method"] = "GitHub Search API (trailing 365 days for commits; public repos and PRs)"
    return stats


def build_data(days, username=USERNAME, account_stats=None):
    """Aggregate contribution counts, streaks, and monthly breakdowns."""
    if not days:
        raise ValueError("Cannot build data from empty calendar list.")

    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)

    # Best contribution day (in case of tie, pick latest date)
    best_candidate = max(days, key=lambda d: (d["count"], d["date"]))
    best_day = {"date": best_candidate["date"], "count": best_candidate["count"]}

    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    # Monthly breakdown (last 12 months)
    monthly_map = {}
    for d in days:
        ym = d["date"][:7]  # YYYY-MM
        monthly_map[ym] = monthly_map.get(ym, 0) + d["count"]

    sorted_months = sorted(monthly_map.keys())
    monthly_list = []
    for ym in sorted_months:
        dt = datetime.datetime.strptime(ym, "%Y-%m")
        monthly_list.append({
            "key": ym,
            "label": dt.strftime("%b"),
            "year": dt.strftime("%Y"),
            "total": monthly_map[ym],
        })

    avg_active = round(total / active_days, 1) if active_days > 0 else 0.0

    return {
        "username": username,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {
            "start": days[0]["date"],
            "end": days[-1]["date"],
        },
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": avg_active,
        "current_streak": {
            "length": cur_len,
            "start": cur_start,
            "end": cur_end,
        },
        "longest_streak": {
            "length": long_len,
            "start": long_start,
            "end": long_end,
        },
        "best_day": best_day,
        "monthly": monthly_list,
        "github_stats": account_stats or {},
        "days": days,
    }


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    existing_stats = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                existing_stats = prev_data.get("github_stats", {})
        except Exception:
            existing_stats = {}

    try:
        days = fetch_days(USERNAME)
        account_stats = fetch_account_stats(USERNAME, existing_stats)
        data = build_data(days, USERNAME, account_stats)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Successfully wrote {OUT_PATH}: {data['total_contributions']} contributions, "
              f"current streak {data['current_streak']['length']} days, "
              f"longest streak {data['longest_streak']['length']} days, "
              f"stats: {data['github_stats']}")
    except Exception as err:
        print(f"Failed to fetch and write contributions: {err}", file=sys.stderr)
        if not os.path.exists(OUT_PATH):
            sys.exit(1)
        print("Preserving existing data/contributions.json file.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
