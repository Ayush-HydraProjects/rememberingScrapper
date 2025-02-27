import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from requests.adapters import HTTPAdapter
from urllib3 import Retry

import app
from models import Obituary,db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Constants
BASE_DOMAIN = "remembering.ca"
SEARCH_KEYWORD = "Windsor"
ALUMNI_KEYWORDS = {"University of Windsor", "UWindsor", "Windsor University"}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

def configure_session():
    """Configure HTTP session with retries and user-agent rotation"""
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

def get_city_subdomains(session):
    """Fetch all city subdomains"""
    logging.info("Fetching city subdomains...")
    try:
        response = session.get(f"https://www.{BASE_DOMAIN}/location")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        subdomains = set()
        for link in soup.find_all("a", href=True):
            parsed = urlparse(link["href"])
            if parsed.netloc.endswith(BASE_DOMAIN):
                parts = parsed.netloc.split('.')
                if parts[0].lower() != "www" and len(parts) > 2:
                    subdomains.add(parts[0].lower())
        return sorted(subdomains)
    except Exception as e:
        logging.error(f"Error fetching city subdomains: {e}")
        return []

def process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries):
    """Fetch obituary pages for a city"""
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_url = f"{base_url}/obituaries/all-categories/search?search_type=advanced&ap_search_keyword={SEARCH_KEYWORD}"

    page = 1
    max_pages = 50

    while page <= max_pages:
        current_url = f"{search_url}&p={page}" if page > 1 else search_url

        if current_url in visited_search_pages:
            break
        visited_search_pages.add(current_url)

        logging.info(f"Processing page {page}: {current_url}")
        time.sleep(random.uniform(0.5, 1.5))

        try:
            response = session.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            page_urls = {urljoin(base_url, link["href"]) for link in soup.select('a[href^="/obituary/"]') if urljoin(base_url, link["href"]) not in visited_obituaries}

            if not page_urls:
                logging.info("No more obituaries found.")
                break

            logging.info(f"Found {len(page_urls)} new obituaries.")
            yield page_urls

            next_page = soup.find("a", class_="next") or soup.find("a", string=lambda t: t and "next" in t.lower())
            if not next_page:
                break

            page += 1

        except Exception as e:
            logging.error(f"Error on page {page}: {str(e)[:100]}...")
            break

def process_city(session, subdomain, processed_cities, visited_search_pages, visited_obituaries):
    """Process all obituary pages in a city"""
    if subdomain in processed_cities:
        return
    processed_cities.add(subdomain)

    logging.info(f"\nProcessing city: {subdomain.upper()}\n" + "=" * 50)

    total_alumni = 0
    for page_urls in process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries):
        for url in page_urls:
            if url in visited_obituaries:
                continue

            result = process_obituary(session, url, visited_obituaries)
            if result and result["is_alumni"]:
                total_alumni += 1

            time.sleep(random.uniform(0.7, 1.3))

    logging.info(f"City {subdomain} completed. Alumni found: {total_alumni}")

def process_obituary(session, db_session, url, visited_obituaries):
    """Extract obituary details, check for alumni keywords, and store in database."""
    if url in visited_obituaries:
        return None
    visited_obituaries.add(url)

    logging.info(f"Processing obituary: {url}")
    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        name = soup.select_one("h1.obit-name").get_text(strip=True) if soup.select_one("h1.obit-name") else "N/A"
        content = soup.select_one("span.details-copy").get_text(strip=True) if soup.select_one("span.details-copy") else ""

        is_alumni = any(keyword in content for keyword in ALUMNI_KEYWORDS)
        first_name, last_name = name.split(" ", 1) if " " in name else (name, None)

        # Prepare and store obituary entry
        obituary_entry = Obituary(
            name=name,
            first_name=first_name,
            last_name=last_name,
            obituary_url=url,
            is_alumni=is_alumni,
            content=content
        )
        db_session.add(obituary_entry)
        db_session.commit()

        logging.info(f"Obituary saved: {name} {'✅ (Alumni)' if is_alumni else '❌ (Not Alumni)'}")
        return {"name": name, "is_alumni": is_alumni, "url": url}

    except Exception as e:
        logging.error(f"Error processing obituary {url}: {e}")
        return None


def main():
    session = configure_session()
    processed_cities = set()
    visited_search_pages = set()
    visited_obituaries = set()

    subdomains = get_city_subdomains(session)
    if not subdomains:
        logging.error("No city subdomains found.")
        return


    for idx, subdomain in enumerate(subdomains, 1):
        logging.info(f"\nProcessing city {idx}/{len(subdomains)}: {subdomain}")
        process_city(session, subdomain, processed_cities, visited_search_pages, visited_obituaries)

    logging.info("\nScraping completed!")

if __name__ == "__main__":
    main()