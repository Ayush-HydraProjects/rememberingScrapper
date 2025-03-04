import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import spacy
import re
from datetime import datetime
from dateutil import parser

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from urllib.parse import urlparse

from models import Obituary, DistinctObituary, db # Import DistinctObituary model


# Load spaCy NLP Model for Named Entity Recognition (NER)
nlp = spacy.load("en_core_web_sm")

import json
import os

STATE_FILE = "state.json"

def load_state():
    """Load the saved state from a file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_state(state):
    """Save the current state to a file"""
    with open(STATE_FILE, 'w') as file:
        json.dump(state, file, indent=4)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Constants
BASE_DOMAIN = "remembering.ca"
SEARCH_KEYWORD = "Windsor", "University"
ALUMNI_KEYWORDS = {"University of Windsor", "UWindsor", "Windsor University"}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

def configure_session():
    """Configure HTTP session with retries and user-agent rotation"""
    session = requests.Session()
    retries = Retry(total=100, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

CITY_PROVINCE_MAPPING = {
"airdrieecho": ("Airdrie", "Alberta"),
"thecragandcanyon": ("Banff", "Alberta"),
"thebeaumontnews": ("Beaumont", "Alberta"),
"thecragandcanyon": ("Bow Valley", "Alberta"),
"calgary": ("Calgary", "Alberta"),
"calgaryherald": ("Calgary Herald", "Alberta"),
"calgarysun": ("Calgary Sun", "Alberta"),
"cochranetimes": ("Cochrane", "Alberta"),
"coldlakesun": ("Cold Lake", "Alberta"),
"devondispatch": ("Devon", "Alberta"),
"draytonvalleywesternreview": ("Drayton Valley", "Alberta"),
"edmonton": ("Edmonton", "Alberta"),
"edmontonjournal": ("Edmonton Journal", "Alberta"),
"edmontonsun": ("Edmonton Sun", "Alberta"),
"edson": ("Edson", "Alberta"),
"fairviewpost": ("Fairview", "Alberta"),
"fortmcmurraytoday": ("Fort McMurray", "Alberta"),
"fortsaskatchewanrecord": ("Fort Saskatchewan", "Alberta"),
"peacecountrysun": ("Grande Prairie", "Alberta"),
"hannaherald": ("Hanna", "Alberta"),
"highrivertimes": ("High River", "Alberta"),
"hinton": ("Hinton", "Alberta"),
"lacombe": ("Lacombe", "Alberta"),
"leducrep": ("Leduc", "Alberta"),
"mayerthorpefreelancer": ("Mayerthorpe", "Alberta"),
"nantonnews": ("Nanton", "Alberta"),
"prrecordgazette": ("Peace River", "Alberta"),
"pinchercreekecho": ("Pincher Creek", "Alberta"),
"sherwoodparknews": ("Sherwood Park", "Alberta"),
"sprucestony": ("Spruce Grove", "Alberta"),
"vermilionstandard": ("Vermilion", "Alberta"),
"vulcanadvocate": ("Vulcan", "Alberta"),
"wetaskiwintimes": ("Wetaskiwin", "Alberta"),
"whitecourtstar": ("Whitecourt", "Alberta"),
"princegeorgepost": ("Prince George", "British Columbia"),
"vancouversunandprovince": ("Vancouver", "British Columbia"),
"altona": ("Altona", "Manitoba"),
"beausejour": ("Beausejour", "Manitoba"),
"carman": ("Carman", "Manitoba"),
"gimli": ("Gimli (Interlake)", "Manitoba"),
"lacdubonnet": ("Lac du Bonnet", "Manitoba"),
"morden": ("Morden", "Manitoba"),
"thegraphicleader": ("Portage la Prairie", "Manitoba"),
"selkirk": ("Selkirk", "Manitoba"),
"stonewall": ("Stonewall", "Manitoba"),
"winkler": ("Winkler", "Manitoba"),
"winnipegsun": ("Winnipeg", "Manitoba"),
"northern-light": ("Bathurst", "New Brunswick"),
"tribune": ("Campbellton", "New Brunswick"),
"greater-saint-john": ("Edmundston Area", "New Brunswick"), # Corrected this line to use "Edmundston Area" as per HTML
"daily-gleaner": ("Fredericton", "New Brunswick"),
"victoria-star": ("Grand Falls", "New Brunswick"),
"miramichi-leader": ("Miramichi", "New Brunswick"),
"times-transcript": ("Moncton", "New Brunswick"),
"obituaries": ("Régions Acadiennes", "New Brunswick"), # Assuming 'obituaries' subdomain maps to "Régions Acadiennes" as per your earlier mapping for L'etoile
"kings-county-record": ("Sussex", "New Brunswick"),
"bugle-observer": ("Woodstock", "New Brunswick"),
"thetelegram": ("St. John's", "Newfoundland and Labrador"),
"theannapolisvalleyregister": ("Annapolis and Kings Counties", "Nova Scotia"),
"thecapebretonpost": ("Cape Breton", "Nova Scotia"),
"thetricountyvanguard": ("Digby, Shelburne and Yarmouth Counties", "Nova Scotia"),
"thechronicleherald": ("Halifax", "Nova Scotia"),
"thevalleyjournaladvertiser": ("Hants and Kings Counties", "Nova Scotia"),
"thenewglasgownews": ("New Glasgow", "Nova Scotia"),
"thetruronews": ("Truro", "Nova Scotia"),
"intelligencer": ("Belleville", "Ontario"),
"brantfordexpositor": ("Brantford", "Ontario"),
"recorder": ("Brockville", "Ontario"),
"chathamdailynews": ("Chatham", "Ontario"),
"clintonnewsrecord": ("Clinton", "Ontario"),
"cochranetimespost": ("Cochrane", "Ontario"),
"standard-freeholder": ("Cornwall", "Ontario"),
"norfolkandtillsonburgnews": ("Delhi", "Ontario"),
"elliotlakestandard": ("Elliot Lake", "Ontario"),
"midnorthmonitor": ("Espanola", "Ontario"),
"lakeshoreadvance": ("Exeter", "Ontario"),
"gananoquereporter": ("Gananoque", "Ontario"),
"goderichsignalstar": ("Goderich", "Ontario"),
"thepost": ("Hanover", "Ontario"),
"kenoraminerandnews": ("Kenora", "Ontario"),
"kincardinenews": ("Kincardine", "Ontario"),
"thewhig": ("Kingston", "Ontario"),
"northernnews": ("Kirkland Lake", "Ontario"),
"lfpress": ("London", "Ontario"),
"lucknowsentinel": ("Lucknow", "Ontario"),
"mitchelladvocate": ("Mitchell", "Ontario"),
"napaneeguide": ("Napanee", "Ontario"),
"nationalpost": ("National Post", "Ontario"),
"nugget": ("North Bay", "Ontario"),
"ottawa": ("Ottawa", "Ontario"),
"ottawacitizen": ("Ottawa Citizen", "Ontario"),
"ottawasun": ("Ottawa Sun", "Ontario"),
"owensoundsuntimes": ("Owen Sound", "Ontario"),
"parisstaronline": ("Paris", "Ontario"),
"pembrokeobserver": ("Pembroke", "Ontario"),
"countyweeklynews": ("Picton County", "Ontario"),
"shorelinebeacon": ("Port Elgin", "Ontario"),
"theobserver": ("Sarnia", "Ontario"),
"saultstar": ("Sault Ste. Marie", "Ontario"),
"seaforthhuronexpositor": ("Seaforth", "Ontario"),
"simcoereformer": ("Simcoe", "Ontario"),
"stthomastimesjournal": ("St. Thomas", "Ontario"),
"communitypress": ("Stirling", "Ontario"),
"stratfordbeaconherald": ("Stratford", "Ontario"),
"strathroyagedispatch": ("Strathroy", "Ontario"),
"thesudburystar": ("Sudbury", "Ontario"),
"timminspress": ("Timmins", "Ontario"),
"torontosun": ("Toronto", "Ontario"),
"trentonian": ("Trenton", "Ontario"),
"wallaceburgcourierpress": ("Wallaceburg", "Ontario"),
"thechronicle-online": ("West Lorne", "Ontario"),
"wiartonecho": ("Wiarton", "Ontario"),
"windsorstar": ("Windsor Star", "Ontario"),
"woodstocksentinelreview": ("Woodstock", "Ontario"),
"theguardian": ("Charlottetown", "Prince Edward Island"),
"thejournalpioneer": ("Summerside", "Prince Edward Island"),
"montrealgazette": ("Montreal", "Quebec"),
"melfortnipawinjournal": ("Melfort", "Saskatchewan"),
"leaderpost": ("Regina", "Saskatchewan"),
"thestarphoenix": ("Saskatoon", "Saskatchewan"),
}

def extract_city_and_province(url):
    """
    Extracts city and province from the subdomain of the given URL.
    Example URL: 'windsor.remembering.ca'
    """
    # Parse the URL to get the subdomain
    parsed_url = urlparse(url)
    subdomain = parsed_url.hostname.split('.')[0]

    # Look up city and province based on the subdomain
    city, province = CITY_PROVINCE_MAPPING.get(subdomain.lower(), (None, None))

    return city, province


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

        save_state({
            'processed_cities': list(processed_cities),
            'visited_search_pages': list(visited_search_pages),
            'visited_obituaries': list(visited_obituaries)
        })

        for url in page_urls:
            if url in visited_obituaries:
                continue


            # ✅ Now correctly passing db.session
            result = process_obituary(session, db.session, url, visited_obituaries)
            if result and result["is_alumni"]:
                total_alumni += 1

            time.sleep(random.uniform(0.7, 1.3))

    logging.info(f"City {subdomain} completed. Alumni found: {total_alumni}")

def extract_dates(soup):
    """
    Extracts birth and death dates from the obituary details, takes soup as argument.
    Handles HTML with spans and accounts for missing information and no-year cases.
    """
    birth_date = None
    death_date = None

    obit_dates_tag = soup.find("h2", class_="obit-dates")
    if obit_dates_tag:
        # Get a list of date strings by parsing through all the code that isn't a span
        date_strings = [s.strip() for s in obit_dates_tag.strings if s.strip()]  # Account for empty strings

        if len(date_strings) == 1:
            # If only one date is found, treat it as the death date by default
            death_date = date_strings[0]  # Keep the date exactly as it is without appending a year
        elif len(date_strings) >= 2:
            # If two or more dates are found, assign the first as birth date and last as death date
            birth_date = date_strings[0]
            death_date = date_strings[-1]

        # Basic data validation to handle invalid dates (empty strings or 'N/A')
        if birth_date == "N/A" or not birth_date:
            birth_date = None
        if death_date == "N/A" or not death_date:
            death_date = None

    return birth_date, death_date

def parse_date(date_str):
    """Try parsing the date using dateutil.parser and return in the 'Month dd, yyyy' format."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True).date()
        # Format the date to 'Month dd, yyyy'
        return parsed_date.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return None

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
        death_keywords = ["passing", "passed away", "death", "died", "rested", "passed", "at the age of"]
        if any(keyword in sent.text.lower() for keyword in death_keywords):
            death_index = i
            break

    for i, sent in enumerate(doc.sents):  # Process each sentence separately
        death_keywords = ["passing", "passed away", "death", "died", "rested", "passed", "at the age of"]
        birth_keywords = ["born", "birth", "born in"]

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

    # Parse dates found in the text and format them
    if birth_date:
        birth_date = parse_date(birth_date)
    if death_date:
        death_date = parse_date(death_date)

    return death_date, birth_date

def extract_text(tag):
    return tag.get_text(strip=True) if tag else "N/A"

def process_obituary(session, db_session, url, visited_obituaries):
    """Extract obituary details, check for alumni keywords, and store in both Obituary and DistinctObituary tables."""
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

        donation_keywords = ["donation", "charity", "memorial fund", "contributions"]
        donation_mentions = [sentence for sentence in content.split(". ") if
                             any(keyword in sentence.lower() for keyword in donation_keywords)]
        donation_info = "; ".join(donation_mentions)

        # Extract birth and death dates
        birth_date, death_date = extract_dates(soup)

        # Extract city and province from the subdomain of the URL
        city, province = extract_city_and_province(url)

        # Check for alumni keywords in content
        is_alumni = any(keyword in content for keyword in ALUMNI_KEYWORDS)

        if is_alumni:
            from app import app
            with app.app_context():
                # Create Obituary object and save to Obituary table
                obituary_entry = Obituary(
                    name=f"{first_name} {last_name}",
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    death_date=death_date,
                    donation_information=donation_info,
                    obituary_url=url,
                    city=city,
                    province=province,
                    is_alumni=is_alumni,
                    family_information=content,
                )
                db.session.add(obituary_entry)
                db.session.flush() # Flush to get the obituary_entry.id if needed (though not used here)

                # Check if DistinctObituary entry with the same name exists
                distinct_entry_exists = DistinctObituary.query.filter_by(name=f"{first_name} {last_name}").first()

                if not distinct_entry_exists:
                    # Create DistinctObituary object and save to DistinctObituary table
                    distinct_obituary_entry = DistinctObituary(
                        name=f"{first_name} {last_name}",
                        first_name=first_name,
                        last_name=last_name,
                        birth_date=birth_date,
                        death_date=death_date,
                        donation_information=donation_info,
                        obituary_url=url,
                        city=city,
                        province=province,
                        is_alumni=is_alumni,
                        family_information=content,
                    )
                    db.session.add(distinct_obituary_entry)

                db.session.commit() # Commit session to save to both tables (or just Obituary if distinct exists)


        logging.info(f"Obituary saved: {first_name} {last_name} {'✅ (Alumni)' if is_alumni else '❌ (Not Alumni)'}")
        return {"name": f"{first_name} {last_name}", "is_alumni": is_alumni, "url": url}

    except Exception as e:
        logging.error(f"Error processing obituary {url}: {e}")
        return None

def main():

    state = load_state()

    session = configure_session()

    # Initialize variables based on the saved state
    processed_cities = set(state.get('processed_cities', []))
    visited_search_pages = set(state.get('visited_search_pages', []))
    visited_obituaries = set(state.get('visited_obituaries', []))

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