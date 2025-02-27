import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import spacy
import re
from datetime import datetime

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from models import Obituary, db

# Load spaCy NLP Model for Named Entity Recognition (NER)
nlp = spacy.load("en_core_web_sm")

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

            # ✅ Now correctly passing db.session
            result = process_obituary(session, db.session, url, visited_obituaries)
            if result and result["is_alumni"]:
                total_alumni += 1

            time.sleep(random.uniform(0.7, 1.3))

    logging.info(f"City {subdomain} completed. Alumni found: {total_alumni}")

def parse_date(date_string):
    """Parse different date formats into a standard date string."""
    try:
        # Try to parse common formats like "July 4, 2014" or "Saturday, October 27, 2018"
        return datetime.strptime(date_string, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_string, "%A, %B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

def extract_dates(soup):
    """
    Extracts birth and death dates from the obituary details, takes soup as argument.
    Handles HTML with spans and accounts for missing information
    """
    birth_date = None
    death_date = None

    obit_dates_tag = soup.find("h2", class_="obit-dates")
    if obit_dates_tag:
        # Get a list of date strings by parsing through all the code that isn't a span
        date_strings = [s.strip() for s in obit_dates_tag.strings if s.strip()]  # Account for empty strings

        if len(date_strings) >= 1:
            if len(date_strings) == 1:  # Set the single one string
                birth_date = parse_date(date_strings[0])
            elif len(date_strings) >= 2:
                birth_date = parse_date(date_strings[0])
                death_date = parse_date(date_strings[-1])

        # Basic data validation
        if birth_date == "N/A":  # Account for dates that are N/A or are empty
            birth_date = None
        if death_date == "N/A":  # Account for dates that are N/A or are empty
            death_date = None

    return birth_date, death_date

def extract_death_and_birth_dates(text):
    """
    Extracts death and birth dates from the given text using spaCy NLP and relative keywords.
    Returns:
        A tuple containing the extracted death date and birth date (or None if not found).
    """
    death_date = None
    birth_date = None

    doc = nlp(text)

    # Find the first death indicator to cut down on processing
    death_index = -1  # If no indicator, still run full search
    for i, sent in enumerate(doc.sents):
        death_keywords = ["passing", "passed away", "death", "died"]
        if any(keyword in sent.text.lower() for keyword in death_keywords):
            death_index = i
            break

    for i, sent in enumerate(doc.sents):  # Process each sentence separately
        death_keywords = ["passing", "passed away", "death", "died"]
        birth_keywords = ["born", "birth"]

        # Check for death dates and limit to the first event with the code.
        if any(keyword in sent.text.lower() for keyword in death_keywords) and i == death_index:
            for ent in sent.ents:
                if ent.label_ == "DATE":
                    death_date = ent.text
                    break  # Take the first date found in the sentence

        # Check for birth dates at all sections.
        if any(keyword in sent.text.lower() for keyword in birth_keywords):
            for ent in sent.ents:
                if ent.label_ == "DATE":
                    birth_date = ent.text
                    break  # Take the first date found in the sentence

    # Parse dates found in the text
    if birth_date:
        birth_date = parse_date(birth_date)
    if death_date:
        death_date = parse_date(death_date)

    return death_date, birth_date

def extract_text(tag):
    return tag.get_text(strip=True) if tag else "N/A"

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

        # Extract first and last name using the provided sample method
        obit_name_tag = soup.find("h1", class_="obit-name")
        last_name_tag = soup.find("span", class_="obit-lastname-upper")  # Specific last name tag

        first_name = extract_text(obit_name_tag).replace(extract_text(last_name_tag), "").strip() if obit_name_tag and last_name_tag else None
        last_name = extract_text(last_name_tag).capitalize() if last_name_tag else None

        if not first_name or not last_name:  # Handle missing name components
            logging.error(f"Missing first or last name for obituary: {url}")
            return None

        content = soup.select_one("span.details-copy").get_text(strip=True) if soup.select_one("span.details-copy") else ""

        # Extract birth and death dates
        birth_date, death_date = extract_dates(soup)

        # Check for alumni keywords in content
        is_alumni = any(keyword in content for keyword in ALUMNI_KEYWORDS)

        # ✅ Wrap database operations inside Flask's app context
        from app import app
        with app.app_context():
            obituary_entry = Obituary(
                name=f"{first_name} {last_name}",
                first_name=first_name,
                last_name=last_name,
                obituary_url=url,
                is_alumni=is_alumni,
                content=content,
                birth_date=birth_date,
                death_date=death_date,
            )
            db.session.add(obituary_entry)
            db.session.commit()

        logging.info(f"Obituary saved: {first_name} {last_name} {'✅ (Alumni)' if is_alumni else '❌ (Not Alumni)'}")
        return {"name": f"{first_name} {last_name}", "is_alumni": is_alumni, "url": url}

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
