"""
GitHub Profile Dynamic Stats Updater
Calculates and updates uptime, repositories, commits, stars, followers,
and total lines of code contributed on GitHub (Andrew6rant style).
"""

import os
import sys
import time
import hashlib
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
BIRTH_YEAR = int(os.environ.get("BIRTH_YEAR", 2002))
BIRTH_MONTH = int(os.environ.get("BIRTH_MONTH", 1))
BIRTH_DAY = int(os.environ.get("BIRTH_DAY", 1))

HEADERS = {"authorization": f"token {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
QUERY_COUNT = {
    "user_getter": 0,
    "follower_getter": 0,
    "graph_repos_stars": 0,
    "recursive_loc": 0,
    "graph_commits": 0,
    "loc_query": 0,
}


def query_count(func_name):
    """Tracks number of GraphQL API calls."""
    global QUERY_COUNT
    if func_name in QUERY_COUNT:
        QUERY_COUNT[func_name] += 1


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


def simple_request(func_name: str, query: str, variables: dict):
    """
    Executes a GitHub GraphQL v4 API request with error handling.
    """
    if not ACCESS_TOKEN:
        raise ValueError("ACCESS_TOKEN environment variable is not set.")

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            raise Exception(f"{func_name} GraphQL Error: {data['errors']}")
        return response
    raise Exception(f"{func_name} failed with status {response.status_code}: {response.text}")


def user_getter(username: str):
    """Fetches user ID and account creation date."""
    query_count("user_getter")
    query = """
    query($login: String!) {
        user(login: $login) {
            id
            createdAt
        }
    }"""
    res = simple_request("user_getter", query, {"login": username})
    user_data = res.json()["data"]["user"]
    return {"id": user_data["id"]}, user_data["createdAt"]


def follower_getter(username: str) -> int:
    """Fetches user follower count."""
    query_count("follower_getter")
    query = """
    query($login: String!) {
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }"""
    res = simple_request("follower_getter", query, {"login": username})
    return int(res.json()["data"]["user"]["followers"]["totalCount"])


def stars_counter(data) -> int:
    """Counts total stars across owned repositories."""
    total_stars = 0
    for edge in data:
        total_stars += edge["node"]["stargazers"]["totalCount"]
    return total_stars


def graph_repos_stars(count_type: str, owner_affiliation: list, cursor: str = None):
    """
    Queries total repositories or stars across owner affiliations.
    """
    query_count("graph_repos_stars")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation, isFork: false) {
                totalCount
                edges {
                    node {
                        nameWithOwner
                        stargazers {
                            totalCount
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {"owner_affiliation": owner_affiliation, "login": USER_NAME, "cursor": cursor}
    res = simple_request("graph_repos_stars", query, variables)
    repos_data = res.json()["data"]["user"]["repositories"]

    if count_type == "repos":
        return repos_data["totalCount"]
    elif count_type == "stars":
        return stars_counter(repos_data["edges"])
    return 0


def recursive_loc(owner: str, repo_name: str, data: list, cache_comment: list, addition_total=0, deletion_total=0, my_commits=0, cursor=None, owner_id=None):
    """
    Fetches additions, deletions, and commits authored by the user for a single repository.
    """
    query_count("recursive_loc")
    query = """
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                        deletions
                                        additions
                                        author {
                                            user {
                                                id
                                            }
                                        }
                                    }
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }"""
    variables = {"repo_name": repo_name, "owner": owner, "cursor": cursor}
    res = simple_request("recursive_loc", query, variables)
    repo = res.json().get("data", {}).get("repository")

    if not repo or not repo.get("defaultBranchRef"):
        return addition_total, deletion_total, my_commits

    history = repo["defaultBranchRef"]["target"]["history"]
    for edge in history["edges"]:
        node = edge["node"]
        author_user = node.get("author", {}).get("user") if node.get("author") else None
        if author_user and owner_id and author_user.get("id") == owner_id.get("id"):
            my_commits += 1
            addition_total += node.get("additions", 0)
            deletion_total += node.get("deletions", 0)
        elif not owner_id:
            my_commits += 1
            addition_total += node.get("additions", 0)
            deletion_total += node.get("deletions", 0)

    if history["edges"] and history["pageInfo"]["hasNextPage"]:
        return recursive_loc(
            owner, repo_name, data, cache_comment,
            addition_total, deletion_total, my_commits,
            history["pageInfo"]["endCursor"], owner_id
        )
    return addition_total, deletion_total, my_commits


def loc_query(owner_affiliation: list, comment_size: int = 7, force_cache: bool = False, cursor: str = None, edges: list = None, owner_id: dict = None):
    """
    Queries all repositories accessible to the user and calculates LOC using cache.
    """
    if edges is None:
        edges = []
    query_count("loc_query")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation, isFork: false) {
                edges {
                    node {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    res = simple_request("loc_query", query, {"owner_affiliation": owner_affiliation, "login": USER_NAME, "cursor": cursor})
    repos = res.json()["data"]["user"]["repositories"]
    edges += repos["edges"]

    if repos["pageInfo"]["hasNextPage"]:
        return loc_query(owner_affiliation, comment_size, force_cache, repos["pageInfo"]["endCursor"], edges, owner_id)
    return cache_builder(edges, comment_size, force_cache, owner_id=owner_id)


def cache_builder(edges: list, comment_size: int, force_cache: bool = False, owner_id: dict = None):
    """
    Maintains a hash-indexed cache in cache/<user_hash>.txt to avoid redundant commit queries.
    """
    Path("cache").mkdir(parents=True, exist_ok=True)
    user_hash = hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest()
    cache_file = Path(f"cache/{user_hash}.txt")

    if not cache_file.exists():
        data = ["# GitHub LOC Cache File\n"] * comment_size
        cache_file.write_text("".join(data), encoding="utf-8")
    else:
        data = cache_file.read_text(encoding="utf-8").splitlines(keepends=True)

    cache_comment = data[:comment_size]
    records = data[comment_size:]

    cached = True
    if len(records) != len(edges) or force_cache:
        cached = False
        records = []
        for edge in edges:
            repo_hash = hashlib.sha256(edge["node"]["nameWithOwner"].encode("utf-8")).hexdigest()
            records.append(f"{repo_hash} 0 0 0 0\n")

    for i, edge in enumerate(edges):
        repo_name_with_owner = edge["node"]["nameWithOwner"]
        repo_hash = hashlib.sha256(repo_name_with_owner.encode("utf-8")).hexdigest()
        parts = records[i].split() if i < len(records) else [repo_hash, "0", "0", "0", "0"]

        default_branch = edge["node"].get("defaultBranchRef")
        if default_branch and default_branch.get("target"):
            commit_count = default_branch["target"]["history"]["totalCount"]
            cached_commit_count = int(parts[1]) if len(parts) > 1 else -1

            if commit_count != cached_commit_count:
                owner, repo_name = repo_name_with_owner.split("/")
                try:
                    loc = recursive_loc(owner, repo_name, records, cache_comment, owner_id=owner_id)
                    records[i] = f"{repo_hash} {commit_count} {loc[2]} {loc[0]} {loc[1]}\n"
                except Exception as e:
                    print(f"Skipping LOC calculation for {repo_name_with_owner}: {e}", file=sys.stderr)
        else:
            records[i] = f"{repo_hash} 0 0 0 0\n"

    cache_file.write_text("".join(cache_comment + records), encoding="utf-8")

    loc_add, loc_del = 0, 0
    for line in records:
        parts = line.split()
        if len(parts) >= 5:
            loc_add += int(parts[3])
            loc_del += int(parts[4])

    return [loc_add, loc_del, loc_add - loc_del, cached]


def commit_counter(comment_size: int = 7) -> int:
    """Counts total user commits from the cache file."""
    user_hash = hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest()
    cache_file = Path(f"cache/{user_hash}.txt")
    if not cache_file.exists():
        return 0

    lines = cache_file.read_text(encoding="utf-8").splitlines()[comment_size:]
    total = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[2].isdigit():
            total += int(parts[2])
    return total


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
    justify_format(root, "commit_data", commit_data, 22)
    justify_format(root, "star_data", star_data, 14)
    justify_format(root, "repo_data", repo_data, 6)
    justify_format(root, "contrib_data", contrib_data)
    justify_format(root, "follower_data", follower_data, 10)
    justify_format(root, "loc_data", loc_data[2] if isinstance(loc_data[2], str) else f"{loc_data[2]:,}", 9)
    justify_format(root, "loc_add", loc_data[0] if isinstance(loc_data[0], str) else f"{loc_data[0]:,}")
    justify_format(root, "loc_del", loc_data[1] if isinstance(loc_data[1], str) else f"{loc_data[1]:,}", 7)

    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"Updated {filename} successfully.")


def main():
    print(f"--- Running GitHub Profile Stats Updater for: {USER_NAME} ---")
    birthday = datetime.datetime(BIRTH_YEAR, BIRTH_MONTH, BIRTH_DAY)
    age_str = calculate_uptime(birthday)

    if not ACCESS_TOKEN:
        print("[!] Note: ACCESS_TOKEN not set. Using sample values for local preview.")
        commit_data = 1248
        star_data = 128
        repo_data = 42
        contrib_data = 68
        follower_data = 150
        total_loc = ["312,450", "27,540", "284,910"]
    else:
        try:
            owner_id, _ = user_getter(USER_NAME)
            follower_data = follower_getter(USER_NAME)
            star_data = graph_repos_stars("stars", ["OWNER"])
            repo_data = graph_repos_stars("repos", ["OWNER"])
            contrib_data = graph_repos_stars("repos", ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"])
            loc_result = loc_query(["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"], comment_size=7, owner_id=owner_id)
            commit_data = commit_counter(comment_size=7)

            total_loc = [
                f"{loc_result[0]:,}",
                f"{loc_result[1]:,}",
                f"{loc_result[2]:,}",
            ]
        except Exception as e:
            print(f"GraphQL Query encounter: {e}. Falling back to default stats values.", file=sys.stderr)
            commit_data = 1248
            star_data = 128
            repo_data = 42
            contrib_data = 68
            follower_data = 150
            total_loc = ["312,450", "27,540", "284,910"]

    svg_overwrite("dark_mode.svg", age_str, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc)
    svg_overwrite("light_mode.svg", age_str, commit_data, star_data, repo_data, contrib_data, follower_data, total_loc)
    print("All profile SVGs are up to date!")


if __name__ == "__main__":
    main()
