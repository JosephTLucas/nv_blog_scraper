# Updated scraper.py using webdriver-manager for robust chromedriver handling
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://developer.nvidia.com"
AUTHOR_PAGE = "https://developer.nvidia.com/blog/author/jolucas/"
OUTPUT_DIR = "posts"

def slugify(text):
    return "".join(x if x.isalnum() else "-" for x in text.lower()).strip("-")

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def load_all_blog_links(driver, max_clicks=20):
    print("Navigating to author page...")
    driver.get(AUTHOR_PAGE)
    time.sleep(3)

    clicks = 0
    while clicks < max_clicks:
        try:
            load_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more')]")
            print(f"Clicking 'Load more' ({clicks + 1}/{max_clicks})...")
            driver.execute_script("arguments[0].click();", load_more)
            time.sleep(2)
            clicks += 1
        except NoSuchElementException:
            print("No more 'Load more' button found.")
            break
    else:
        print("Reached max click limit. Some posts may not have loaded.")

    print("Parsing page for blog links...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = set()
    for card in soup.select(".post-card a.post--image"):
        href = card.get("href")
        if href:
            links.add(href)

    print(f"Found {len(links)} blog posts.")
    return sorted(links)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def fetch_and_save_post(url):
    print(f"Archiving: {url}")
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"Failed to fetch {url} (status: {res.status_code})")
        return

    soup = BeautifulSoup(res.text, "html.parser")

    title_tag = soup.find("h1")
    date_tag = soup.select_one("div.blog-post--meta time")
    content_div = soup.find("div", class_="field--name-body")

    if not title_tag or not date_tag or not content_div:
        print(f"Skipping (missing fields): {url}")
        return

    title = title_tag.get_text(strip=True)
    date_str = date_tag.get_text(strip=True)
    try:
        date = datetime.strptime(date_str, "%B %d, %Y").date()
    except ValueError:
        print(f"Invalid date format: {date_str}")
        return

    slug = "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")
    filename = f"{date.isoformat()}-{slug}.md"
    filepath = os.path.join("posts", filename)

    if os.path.exists(filepath):
        print(f"Already archived: {filename}")
        return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Original post: [{url}]({url})*\n\n")
        f.write(content_div.get_text("\n", strip=True))

    print(f"Archived: {filename}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = setup_driver()
    try:
        links = load_all_blog_links(driver)
        for i, url in enumerate(links):
            print(f"({i}/{len(links)}) Archiving: {url}")
            fetch_and_save_post(url)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
