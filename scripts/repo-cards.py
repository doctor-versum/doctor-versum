import os
import requests
from datetime import datetime, timezone

USER = os.getenv("GH_USERNAME")
EXCLUDE = {"doctor-versum", "doctor-versum.github.io"}
HEADERS = {"Authorization": f'token {os.getenv("GH_PAT")}'}

def get_all_repos():
    repos = []
    page = 1
    while True:
        url = f'https://api.github.com/users/{USER}/repos?per_page=100&page={page}'
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        if not data or "message" in data:
            break
        for repo in data:
            if repo["name"] not in EXCLUDE and not repo["private"]:
                repos.append(repo)
        page += 1
    return repos

def get_contributors_count(repo_name):
    url = f"https://api.github.com/repos/{USER}/{repo_name}/contributors?per_page=100&anon=true"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return 0
    return len(r.json())

def normalize(values):
    max_val = max(values) or 1
    return [v / max_val for v in values]

def score_repos(repos):
    now = datetime.now(timezone.utc)

    updated_ages = [(now - datetime.fromisoformat(repo["updated_at"].replace('Z', '+00:00'))).total_seconds() for repo in repos]
    pushed_ages = [(now - datetime.fromisoformat(repo["pushed_at"].replace('Z', '+00:00'))).total_seconds() for repo in repos]
    stargazers = [repo["stargazers_count"] for repo in repos]
    forks = [repo["forks_count"] for repo in repos]
    contributors = [get_contributors_count(repo["name"]) for repo in repos]

    updated_scores = normalize([1 / (age + 1) for age in updated_ages])
    pushed_scores = normalize([1 / (age + 1) for age in pushed_ages])
    stargazer_scores = normalize(stargazers)
    fork_scores = normalize(forks)
    contributor_scores = normalize(contributors)

    scores = []
    for i, repo in enumerate(repos):
        total_score = (
            0.20 * updated_scores[i] +
            0.25 * pushed_scores[i] +
            0.25 * stargazer_scores[i] +
            0.10 * fork_scores[i] +
            0.20 * contributor_scores[i]
        )
        scores.append({
            "name": repo["name"],
            "score": total_score
        })

    return sorted(scores, key=lambda r: r["score"], reverse=True)[:5]

def save_card(repo_name, rank):
    url = (
        f"https://github-readme-stats.vercel.app/api/pin/"
        f"?username={USER}"
        f"&repo={repo_name}"
        f"&theme=jolly"
        f"&bg_color=00000000"
        f"&text_color=aa00ff"
        f"&description_lines_count=2"
    )
    path = f"generated/cards/repo-card-{rank}.svg"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)
    return f"https://github.com/{USER}/{repo_name}"

def update_readme(links):
    with open("README-template.md", encoding="utf-8") as f:
        template = f.read()
    for idx, link in enumerate(links, start=1):
        template = template.replace(f"<!--link-repo-{idx}-->", link)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(template)

if __name__ == "__main__":
    print("🔍 Fetching repositories...")
    all_repos = get_all_repos()

    print("📊 Scoring repositories...")
    top_repos = score_repos(all_repos)

    print("🖼️ Generating cards...")
    links = []
    for idx, repo in enumerate(top_repos, start=1):
        link = save_card(repo["name"], idx)
        links.append(link)

    print("📝 Updating README...")
    update_readme(links)

    print("✅ Done.")