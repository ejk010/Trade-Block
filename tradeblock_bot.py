import os
import re
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
BASE_URL = "https://www.pennantchase.com"
LEAGUE_URL = f"{BASE_URL}/league/baseball/home?lgid=691"
WEBHOOK_URL = os.environ.get("DISCORD_TRADEBLOCK_WEBHOOK_URL")
LOG_FILE = "last_tradeblock.txt"

# Team mention map using full "City Nickname" format
TEAM_NAME_MAP = {
    "Arizona Diamondbacks": "<@&773898276940152833>",
    "Atlanta Braves": "<@&622615242978885632>",
    "Baltimore Orioles": "<@&728717530096468149>",
    "Boston Red Sox": "<@&1180931211858809023>",
    "Chicago Cubs": "<@&773897833211625473>",
    "Chicago White Sox": "<@&622615457299693578>",
    "Cincinnati Reds": "<@&773898419143442432>",
    "Cleveland Indians": "<@&773898193041358879>",
    "Colorado Rockies": "<@&773898540321079316>",
    "Detroit Tigers": "<@&622615931625144341>",
    "Houston Astros": "<@&962525228636987402>",
    "Kansas City Royals": "<@&622614419486015510>",
    "Los Angeles Angels": "<@&622613488824483840>",
    "Los Angeles Dodgers": "<@&962525782977150996>",
    "Miami Marlins": "<@&752626736125968474>",
    "Milwaukee Brewers": "<@&622613398701604865>",
    "Minnesota Twins": "<@&728718027645780018>",
    "New York Mets": "<@&622613734896041994>",
    "New York Yankees": "<@&622952290428387329>",
    "Oakland Athletics": "<@&773898540321079316>",
    "Philadelphia Phillies": "<@&622614284979011595>",
    "Pittsburgh Pirates": "<@&622615936234684416>",
    "St. Louis Cardinals": "<@&622613261841596426>",
    "San Diego Padres": "<@&622618093868548097>",
    "San Francisco Giants": "<@&622615034157203469>",
    "Seattle Mariners": "<@&622612991413714975>",
    "Tampa Bay Rays": "<@&623340295517634560>",
    "Texas Rangers": "<@&622613054642978817>",
    "Toronto Blue Jays": "<@&622615298322989070>",
    "Washington Nationals": "<@&1180930959642722404>",
}

def format_mentions(text):
    for team, mention in TEAM_NAME_MAP.items():
        text = re.sub(rf'\b{re.escape(team)}\b', mention, text)
    return text

def get_current_block_events():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(LEAGUE_URL, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, 'html.parser')
        events = []

        timeline_items = soup.find_all("div", class_="timeline-item")

        for item in timeline_items:
            header_span = item.find("span", class_="fw-bold")
            if not header_span:
                continue

            event_type = header_span.get_text(strip=True).lower()
            details_div = item.find("div", class_="font-16")
            if not details_div:
                continue

            # Remove commissioner links
            for commish in details_div.find_all("div", class_="commishLink"):
                commish.decompose()

            # Convert links to Discord markdown
            for a_tag in details_div.find_all("a", href=True):
                href = a_tag["href"]
                if not href.startswith("http"):
                    href = f"{BASE_URL}{href}"
                name = a_tag.get_text(strip=True)
                a_tag.replace_with(f"[{name}]({href})")

            for br in details_div.find_all("br"):
                br.replace_with("\n")

            text = details_div.get_text().strip()
            cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
            normalized_text = "\n".join(cleaned_lines)

            if "placed on trade block" in event_type:
                events.append(("ADD", normalized_text))
            elif "removed from trade block" in event_type:
                events.append(("REMOVE", normalized_text))

        return events
    except Exception as e:
        print(f"Error fetching page: {e}")
        return []

def read_seen_events():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        return set(item.strip() for item in content.split("\n---\n") if item.strip())

def append_seen_events(new_event_texts):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        for item in new_event_texts:
            f.write(item + '\n---\n')

def send_discord_notification(message):
    try:
        r = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        r.raise_for_status()
        print("Discord notification sent.")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

# --- Main Execution ---
if not WEBHOOK_URL:
    print("Error: DISCORD_TRADEBLOCK_WEBHOOK_URL is not set.")
    exit(1)

current_events = get_current_block_events()
seen_events = read_seen_events()

unseen_events = [(category, text) for category, text in current_events if text not in seen_events]

if unseen_events:
    new_event_texts = []
    for category, text in unseen_events:
        formatted = format_mentions(text)
        if category == "ADD":
            send_discord_notification(f"📥 **Added to Trade Block:**\n{formatted}")
        elif category == "REMOVE":
            send_discord_notification(f"📤 **Removed from Trade Block:**\n{formatted}")
        new_event_texts.append(text)

    append_seen_events(new_event_texts)
    print(f"Posted {len(unseen_events)} trade block update(s).")
else:
    print("No new trade block activity detected.")
