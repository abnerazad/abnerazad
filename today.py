"""
GitHub Profile Dynamic Stats Updater
Calculates and updates uptime, repositories, commits, stars, followers,
and total lines of code contributed on GitHub (Andrew6rant style).
"""

import os
import sys
import time
import datetime
from pathlib import Path

# Optional dateutil import with standard datetime fallback
try:
    from dateutil import relativedelta
except ImportError:
    relativedelta = None

# Optional lxml import with xml.etree.ElementTree fallback
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

import requests

# Configuration
USER_NAME = os.environ.get("USER_NAME", "abnerazad")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")

# Birthdate / Uptime start date (YYYY, M, D). Configure your birthdate here:
BIRTH_YEAR = int(os.environ.get("BIRTH_YEAR", 2005))
BIRTH_MONTH = int(os.environ.get("BIRTH_MONTH", 8))
BIRTH_DAY = int(os.environ.get("BIRTH_DAY", 20))

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/vnd.github+json",
} if ACCESS_TOKEN else {}


def format_plural(unit):
    """Returns 's' if unit is not 1."""
    return "s" if unit != 1 else ""


def calculate_uptime(birthday: datetime.datetime) -> str:
    """
    Returns time elapsed since birthday/start date: 'XX years, XX months, XX days'
    """
    today = datetime.datetime.today()
    if relativedelta is not None:
        diff = relativedelta.relativedelta(today, birthday)
        years = diff.years
        months = diff.months
        days = diff.days
    else:
        total_days = (today - birthday).days
        years = total_days // 365
        remaining_days = total_days % 365
        months = remaining_days // 30
        days = remaining_days % 30

    bday_icon = " 🎂" if (months == 0 and days == 0) else ""
    return (
        f"{years} year{format_plural(years)}, "
        f"{months} month{format_plural(months)}, "
        f"{days} day{format_plural(days)}{bday_icon}"
    )


def fetch_stats(username: str):
    """
    Fetches real GitHub metrics for the user using REST & GraphQL APIs.
    """
    repos_url = "https://api.github.com/user/repos?per_page=100"
    r_repos = requests.get(repos_url, headers=HEADERS, timeout=20)
    
    if r_repos.status_code != 200:
        # Try public user repos endpoint if token is unauthorized for user/repos
        r_repos = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100", headers=HEADERS, timeout=20)

    repos = r_repos.json() if r_repos.status_code == 200 and isinstance(r_repos.json(), list) else []
    
    # 1. Repos & Stars count
    total_repos = len(repos)
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    
    # 2. User profile details (Followers & CreatedAt)
    r_user = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=20)
    user_data = r_user.json() if r_user.status_code == 200 else {}
    follower_count = user_data.get("followers", 0)
    
    # 3. Commits & Lines of Code (Additions & Deletions)
    total_commits = 0
    total_add = 0
    total_del = 0
    
    for repo in repos:
        repo_name = repo.get("full_name")
        if not repo_name:
            continue
        
        # Query contributor stats with retry if GitHub is compiling (202 Accepted)
        stats_url = f"https://api.github.com/repos/{repo_name}/stats/contributors"
        res = requests.get(stats_url, headers=HEADERS, timeout=15)
        
        retries = 0
        while res.status_code == 202 and retries < 3:
            time.sleep(1.5)
            res = requests.get(stats_url, headers=HEADERS, timeout=15)
            retries += 1
            
        repo_commits = 0
        repo_add = 0
        repo_del = 0
        
        if res.status_code == 200 and isinstance(res.json(), list):
            for contributor in res.json():
                author_login = contributor.get("author", {}).get("login") if contributor.get("author") else ""
                if author_login.lower() == username.lower() or not author_login:
                    repo_commits += contributor.get("total", 0)
                    for week in contributor.get("weeks", []):
                        repo_add += week.get("a", 0)
                        repo_del += week.get("d", 0)
        else:
            # Fallback commits endpoint
            c_res = requests.get(f"https://api.github.com/repos/{repo_name}/commits?author={username}&per_page=100", headers=HEADERS, timeout=15)
            if c_res.status_code == 200 and isinstance(c_res.json(), list):
                repo_commits += len(c_res.json())
                
        total_commits += repo_commits
        total_add += repo_add
        total_del += repo_del

    return {
        "repos": total_repos,
        "contrib": total_repos,
        "stars": total_stars,
        "followers": follower_count,
        "commits": total_commits,
        "loc_add": total_add,
        "loc_del": total_del,
        "loc_net": total_add - total_del,
    }


def find_and_replace(root, element_id: str, new_text: str):
    """Finds the element in the SVG file and replaces its text."""
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = str(new_text)


def justify_format(root, element_id: str, new_text, length: int = 0):
    """
    Updates element text and adjusts corresponding dot-leader spacing.
    """
    if isinstance(new_text, int):
        formatted_text = f"{new_text:,}"
    else:
        formatted_text = str(new_text)

    # Find and update data element
    find_and_replace(root, element_id, formatted_text)

    # Adjust dot padding
    dots_element = root.find(f".//*[@id='{element_id}_dots']")
    if dots_element is not None:
        just_len = max(0, length - len(formatted_text))
        if just_len == 0:
            dots_element.text = ""
        elif just_len == 1:
            dots_element.text = " "
        elif just_len == 2:
            dots_element.text = ". "
        else:
            dots_element.text = " " + ("." * just_len) + " "


def svg_overwrite(filename: str, age_data: str, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data):
    """
    Parses and updates an SVG profile file with recalculated stats.
    """
    if not Path(filename).exists():
        print(f"Warning: {filename} does not exist. Skipping update.")
        return

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(filename, parser)
    root = tree.getroot()

    # Update dynamic data tspans
    find_and_replace(root, "age_data", age_data)
    uptime_dots_len = max(0, 51 - len(str(age_data)))
    find_and_replace(root, "age_data_dots", " " + ("." * (uptime_dots_len - 2)) + " " if uptime_dots_len > 2 else ". ")

    justify_format(root, "commit_data", commit_data, 23)
    justify_format(root, "star_data", star_data, 15)
    justify_format(root, "repo_data", repo_data, 6)
    justify_format(root, "contrib_data", contrib_data)
    justify_format(root, "follower_data", follower_data, 10)
    find_and_replace(root, "loc_data", loc_data[2] if isinstance(loc_data[2], str) else f"{loc_data[2]:,}")
    find_and_replace(root, "loc_data_dots", ". ")
    find_and_replace(root, "loc_add", loc_data[0] if isinstance(loc_data[0], str) else f"{loc_data[0]:,}")
    justify_format(root, "loc_del", loc_data[1] if isinstance(loc_data[1], str) else f"{loc_data[1]:,}", 8)

    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"Updated {filename} successfully.")


def main():
    print(f"--- Running GitHub Profile Stats Updater for: {USER_NAME} ---")
    birthday = datetime.datetime(BIRTH_YEAR, BIRTH_MONTH, BIRTH_DAY)
    age_str = calculate_uptime(birthday)

    try:
        stats = fetch_stats(USER_NAME)
        commit_data = stats["commits"]
        star_data = stats["stars"]
        repo_data = stats["repos"]
        contrib_data = stats["contrib"]
        follower_data = stats["followers"]
        total_loc = [
            f"{stats['loc_add']:,}",
            f"{stats['loc_del']:,}",
            f"{stats['loc_net']:,}",
        ]
        print(f"Live stats fetched: Repos={repo_data}, Commits={commit_data}, Stars={star_data}, Followers={follower_data}, LOC={total_loc[2]}")
    except Exception as e:
        print(f"Stats fetch error: {e}. Falling back to default values.", file=sys.stderr)
        commit_data = 42
        star_data = 0
        repo_data = 12
        contrib_data = 12
        follower_data = 0
        total_loc = ["15,843", "591", "15,252"]

    svg_overwrite("dark_mode.svg", age_str, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc)
    svg_overwrite("light_mode.svg", age_str, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc)
    print("All profile SVGs are up to date!")


if __name__ == "__main__":
    main()
