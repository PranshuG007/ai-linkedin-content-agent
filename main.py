import os
import time
import random
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
from playwright.sync_api import sync_playwright

# -----------------------
# LOAD ENV
# -----------------------
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

if not OPENAI_KEY:
    print("❌ OPENAI_API_KEY missing in .env")
    exit()

if not TAVILY_KEY:
    print("❌ TAVILY_API_KEY missing in .env")
    exit()

if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
    print("❌ LinkedIn credentials missing in .env")
    exit()

# -----------------------
# CLIENTS
# -----------------------
tavily = TavilyClient(api_key=TAVILY_KEY)
openai_client = OpenAI(api_key=OPENAI_KEY)

# -----------------------
# DATA FIELDS
# -----------------------
DATA_FIELDS = [
    "Data Engineering",
    "Data Science",
    "Data Analytics",
    "Machine Learning Engineering",
    "Business Intelligence"
]

# -----------------------
# COMPANY TAGS
# -----------------------
COMPANY_TAGS = {
    "Data Engineering": ["Databricks", "Amazon Web Services", "Snowflake"],
    "Data Science": ["OpenAI", "Google DeepMind", "Microsoft"],
    "Data Analytics": ["Power BI", "Tableau", "Google Analytics"],
    "Machine Learning Engineering": ["OpenAI", "NVIDIA", "Hugging Face"],
    "Business Intelligence": ["Tableau", "Power BI", "Looker"]
}

# -----------------------
# HELPER: APPLY UNICODE BOLD
# -----------------------
def apply_unicode_bold(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    bold =   "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇" \
             "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭" \
             "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"

    table = str.maketrans(normal, bold)

    while "[[BOLD]]" in text and "[[/BOLD]]" in text:
        start = text.index("[[BOLD]]")
        end = text.index("[[/BOLD]]")

        before = text[:start]
        target = text[start + 8:end]
        after = text[end + 9:]

        target_bold = target.translate(table)
        text = before + target_bold + after

    return text

# -----------------------
# STEP 1: GET CONTENT
# -----------------------
def get_data_field_content():
    field = random.choice(DATA_FIELDS)
    print(f"🔍 Today’s topic: {field}")

    query = f"""
    practical lessons, real world use cases,
    common mistakes, tools, workflows in {field}
    """

    results = tavily.search(query=query, max_results=5)
    return results["results"], field

# -----------------------
# STEP 2: PICK BEST
# -----------------------
def choose_best_article(articles):
    return max(articles, key=lambda x: len(x.get("content", "")))

# -----------------------
# STEP 3: WRITE POST
# -----------------------
def write_linkedin_post(article, field):
    print("✍️ Writing post with emojis, selective bold & tags...")

    companies = COMPANY_TAGS.get(field, [])[:2]

    tag_sentence = ""
    if len(companies) == 2:
        tag_sentence = f"I’ve seen similar patterns while learning from teams at @{companies[0]} and @{companies[1]}."
    elif len(companies) == 1:
        tag_sentence = f"I’ve seen similar patterns while learning from teams at @{companies[0]}."

    prompt = f"""
You are an experienced {field} professional writing a LinkedIn post.

Source:
{article['content']}

TASK:
Write ONE final LinkedIn post only.

STYLE:
- Use 3–4 emojis naturally (🚀 📊 🤔 💡 ✨ 🌟)
- Start with a strong hook
- Share ONE real insight
- Give ONE concrete example
- Tone: practical, honest, human
- 120–170 words
- End with a thoughtful question

BOLD:
- Pick 2–3 short important phrases
- Wrap ONLY them like:
  [[BOLD]]important words[[/BOLD]]

TAGGING:
Include this sentence naturally in the middle:
"{tag_sentence}"

HASHTAGS:
After the post:
- Add ONE blank line
- Then add 5–7 professional hashtags

FORMAT:

<post text with [[BOLD]] markers>

#TagOne #TagTwo #TagThree #TagFour #TagFive
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_post = response.choices[0].message.content
    final_post = apply_unicode_bold(raw_post)
    return final_post

# -----------------------
# STEP 4: AUTO POST
# -----------------------
def post_to_linkedin(post_text):
    print("🚀 Opening browser to post on LinkedIn...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # LOGIN
        page.goto("https://www.linkedin.com/login")
        page.fill("#username", LINKEDIN_EMAIL)
        page.fill("#password", LINKEDIN_PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_timeout(7000)

        # FEED
        page.goto("https://www.linkedin.com/feed/")
        page.wait_for_timeout(7000)

        # START POST
        print("📝 Clicking Start a post...")
        page.get_by_role("button", name="Start a post").click()
        page.wait_for_timeout(4000)

        # TYPE POST WITH REAL TAGGING
        print("⌨️ Typing post with real tagging...")

        for line in post_text.split("\n"):
            words = line.split(" ")
            for w in words:

                # ---- HANDLE TAG WORDS ----
                if w.startswith("@"):
                    page.keyboard.type(w, delay=60)
                    page.wait_for_timeout(800)

                    # select from dropdown
                    page.keyboard.press("ArrowDown")
                    page.wait_for_timeout(300)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)

                    # FORCE SPACE AFTER TAG (fixes @googleand bug)
                    page.keyboard.type(" ")

                # ---- NORMAL WORDS ----
                else:
                    page.keyboard.type(w + " ", delay=30)

            page.keyboard.press("Enter")
            page.wait_for_timeout(300)

        page.wait_for_timeout(2000)

        # CLICK POST
        print("🚨 Clicking Post button...")
        try:
            post_button = page.locator("button.share-actions__primary-action")
            post_button.wait_for(timeout=15000)
            post_button.click()
            print("✅ Post clicked successfully!")
        except:
            print("❌ Auto-click failed.")
            print("👉 Click POST manually.")
            page.wait_for_timeout(60000)

        print("🎉 Posting step finished.")
        page.wait_for_timeout(5000)
        browser.close()

# -----------------------
# MAIN
# -----------------------
def run():
    print("\n🤖 AI Data-Field LinkedIn Agent started...\n")

    articles, field = get_data_field_content()
    best_article = choose_best_article(articles)
    post = write_linkedin_post(best_article, field)

    print("\n==============================")
    print("📢 GENERATED POST:\n")
    print(post)
    print("==============================\n")

    post_to_linkedin(post)

    print("✅ Done!")

if __name__ == "__main__":
    run()