import os
import requests
import json
from datetime import datetime

# Load token from .env or env vars
def load_token():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.strip().startswith("GITHUB_TOKEN="):
                    return line.strip().split("=")[1].strip()
    return os.environ.get("GITHUB_TOKEN")

TOKEN = load_token()
USERNAME = "Sujay-Patel-GitHub"

if not TOKEN:
    print("ERROR: GITHUB_TOKEN not found in .env or environment!")
    exit(1)

# GraphQL query to fetch all required statistics
query = """
query($username: String!) {
  user(login: $username) {
    name
    login
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    pullRequests {
      totalCount
    }
    issues {
      totalCount
    }
    repositories(first: 100, ownerAffiliations: OWNER) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
  }
}
"""

def fetch_data():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.post("https://api.github.com/graphql", json={"query": query, "variables": {"username": USERNAME}}, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Query failed with status {r.status_code}: {r.text}")
    res = r.json()
    if "errors" in res:
        raise Exception(f"GraphQL Errors: {res['errors']}")
    return res["data"]["user"]

def calculate_streaks(calendar):
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append((datetime.strptime(day["date"], "%Y-%m-%d").date(), day["contributionCount"]))
    
    # Sort days chronologically
    days.sort(key=lambda x: x[0])
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    # Calculate streaks
    today = datetime.now().date()
    for date, count in days:
        if count > 0:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            # Only break current streak if it is before yesterday (give 1 day buffer for timezone/today contributions)
            temp_streak = 0
            
    # Calculate current streak active right now (working backward)
    active_streak = 0
    has_contributed_recently = False
    
    # Check if user contributed today or yesterday
    for date, count in reversed(days):
        days_diff = (today - date).days
        if days_diff <= 1:
            if count > 0:
                has_contributed_recently = True
                break
        else:
            break
            
    if has_contributed_recently:
        for date, count in reversed(days):
            if count > 0:
                active_streak += 1
            else:
                # If we hit 0 contributions, but it's today (and yesterday had > 0), don't break yet
                days_diff = (today - date).days
                if days_diff == 0:
                    continue
                break
                
    return active_streak, longest_streak, calendar["totalContributions"]

def process_languages(repos):
    lang_sizes = {}
    lang_colors = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"]["color"] or "#858585"
            lang_sizes[name] = lang_sizes.get(name, 0) + size
            lang_colors[name] = color
            
    total_size = sum(lang_sizes.values())
    if total_size == 0:
        return []
        
    langs = []
    for name, size in lang_sizes.items():
        pct = (size / total_size) * 100
        langs.append({"name": name, "pct": pct, "color": lang_colors[name]})
        
    langs.sort(key=lambda x: x["pct"], reverse=True)
    return langs[:5]  # Top 5 languages

# SVG Generators with a sleek cyber dark theme
def generate_stats_svg(stats):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="200" viewBox="0 0 450 200">
    <style>
        .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1; rx: 8; }}
        .title {{ font: bold 16px "Segoe UI", Ubuntu, sans-serif; fill: #00ff88; }}
        .label {{ font: 14px "Segoe UI", Ubuntu, sans-serif; fill: #ffffff; }}
        .value {{ font: bold 14px "Segoe UI", Ubuntu, sans-serif; fill: #00ccff; text-anchor: end; }}
        .icon {{ fill: #7d8590; }}
    </style>
    <rect width="448" height="198" x="1" y="1" class="bg"/>
    <text x="25" y="35" class="title">Sujay's GitHub Diagnostics</text>
    
    <!-- Commits -->
    <path d="M25 65 h 15 v 15 h -15 z" class="icon" fill="#00ff88"/>
    <text x="50" y="77" class="label">Total Commits</text>
    <text x="425" y="77" class="value">{stats['commits']}</text>
    
    <!-- Stars -->
    <path d="M25 95 l 3 6 h 6 l -5 4 l 2 6 l -6 -4 l -6 4 l 2 -6 l -5 -4 h 6 z" class="icon" fill="#ffbd2e"/>
    <text x="50" y="107" class="label">Total Stars Earned</text>
    <text x="425" y="107" class="value">{stats['stars']}</text>
    
    <!-- PRs -->
    <text x="25" y="137" class="label">Pull Requests</text>
    <text x="425" y="137" class="value">{stats['prs']}</text>
    
    <!-- Issues -->
    <text x="25" y="167" class="label">Total Issues</text>
    <text x="425" y="167" class="value">{stats['issues']}</text>
</svg>"""
    return svg

def generate_languages_svg(langs):
    bars = []
    legends = []
    
    # Generate progress bar and legend
    total_pct = 0
    current_x = 25
    bar_width = 400
    
    for i, lang in enumerate(langs):
        w = (lang["pct"] / 100) * bar_width
        bars.append(f'<rect x="{current_x:.1f}" y="65" width="{w:.1f}" height="10" fill="{lang["color"]}" />')
        current_x += w
        
        # Legend coordinates
        row = i // 2
        col = i % 2
        lx = 25 + col * 200
        ly = 100 + row * 25
        legends.append(f"""
            <circle cx="{lx}" cy="{ly}" r="6" fill="{lang['color']}" />
            <text x="{lx + 15}" y="{ly + 5}" font-family="Segoe UI, Ubuntu" font-size="13" fill="#ffffff">{lang['name']} ({lang['pct']:.1f}%)</text>
        """)
        
    bars_svg = "".join(bars)
    legends_svg = "".join(legends)
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="200" viewBox="0 0 450 200">
    <style>
        .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1; rx: 8; }}
        .title {{ font: bold 16px "Segoe UI", Ubuntu, sans-serif; fill: #00ff88; }}
    </style>
    <rect width="448" height="198" x="1" y="1" class="bg"/>
    <text x="25" y="35" class="title">Most Used Languages</text>
    
    <!-- Progress Bar -->
    <g rx="5" clip-path="url(#bar-clip)">
        <clipPath id="bar-clip">
            <rect x="25" y="65" width="400" height="10" rx="5" />
        </clipPath>
        {bars_svg}
    </g>
    
    <!-- Legend -->
    {legends_svg}
</svg>"""
    return svg

def generate_streak_svg(current_streak, longest_streak, total_contribs):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="200" viewBox="0 0 450 200">
    <style>
        .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1; rx: 8; }}
        .title {{ font: bold 16px "Segoe UI", Ubuntu, sans-serif; fill: #00ff88; text-anchor: middle; }}
        .metric-title {{ font: 12px "Segoe UI", Ubuntu, sans-serif; fill: #7d8590; text-anchor: middle; }}
        .metric-value {{ font: bold 26px "Segoe UI", Ubuntu, sans-serif; fill: #00ccff; text-anchor: middle; }}
    </style>
    <rect width="448" height="198" x="1" y="1" class="bg"/>
    
    <!-- Total Contributions -->
    <g transform="translate(75, 0)">
        <text x="0" y="80" class="metric-value">{total_contribs}</text>
        <text x="0" y="110" class="metric-title">Total Contributions</text>
    </g>
    
    <!-- Current Streak -->
    <g transform="translate(225, 0)">
        <text x="0" y="80" class="metric-value" fill="#00ff88">{current_streak} Days</text>
        <text x="0" y="110" class="metric-title">Current Streak</text>
    </g>
    
    <!-- Longest Streak -->
    <g transform="translate(375, 0)">
        <text x="0" y="80" class="metric-value">{longest_streak} Days</text>
        <text x="0" y="110" class="metric-title">Longest Streak</text>
    </g>
</svg>"""
    return svg

def main():
    print("Fetching statistics from GitHub...")
    try:
        user_data = fetch_data()
    except Exception as e:
        print(e)
        return
        
    # Calculate metrics
    commits = (user_data["contributionsCollection"]["totalCommitContributions"] +
               user_data["contributionsCollection"]["restrictedContributionsCount"])
    prs = user_data["pullRequests"]["totalCount"]
    issues = user_data["issues"]["totalCount"]
    
    stars = sum(repo["stargazerCount"] for repo in user_data["repositories"]["nodes"])
    
    stats = {
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "stars": stars
    }
    
    # Calculate streak
    calendar = user_data["contributionsCollection"]["contributionCalendar"]
    current_streak, longest_streak, total_contribs = calculate_streaks(calendar)
    
    # Calculate Top Languages
    langs = process_languages(user_data["repositories"]["nodes"])
    
    # Ensure asset directory exists
    os.makedirs("profile-assets", exist_ok=True)
    
    # Write SVGs
    with open("profile-assets/github-stats.svg", "w", encoding="utf-8") as f:
        f.write(generate_stats_svg(stats))
    print("Generated profile-assets/github-stats.svg")
        
    with open("profile-assets/top-langs.svg", "w", encoding="utf-8") as f:
        f.write(generate_languages_svg(langs))
    print("Generated profile-assets/top-langs.svg")
        
    with open("profile-assets/streak-stats.svg", "w", encoding="utf-8") as f:
        f.write(generate_streak_svg(current_streak, longest_streak, total_contribs))
    print("Generated profile-assets/streak-stats.svg")

if __name__ == "__main__":
    main()
