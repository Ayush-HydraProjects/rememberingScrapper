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

# from app import scraping_active

# Load spaCy NLP Model for Named Entity Recognition (NER)
nlp = spacy.load("en_core_web_sm")

import json
import os

# STATE_FILE = "state.json"  <- Removed STATE_FILE constant

# def load_state():  <- Removed load_state function
#     """Load the saved state from a file"""
#     if os.path.exists(STATE_FILE):
#         with open(STATE_FILE, 'r') as file:
#             return json.load(file)
#     return {}

# def save_state(state):  <- Removed save_state function
#     """Save the current state to a file"""
#     with open(STATE_FILE, 'w') as file:
#         json.dump(state, file, indent=4)


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
"calgary": ("Calgary", "Alberta"),
"cochranetimes": ("Cochrane", "Alberta"),
"coldlakesun": ("Cold Lake", "Alberta"),
"devondispatch": ("Edmonton", "Alberta"),
"draytonvalleywesternreview": ("Edmonton", "Alberta"),
"edmonton": ("Edmonton", "Alberta"),
"edmontonjournal": ("Edmonton", "Alberta"),
"edmontonsun": ("Edmonton", "Alberta"),
"edson": ("Edson", "Alberta"),
"fairviewpost": ("Grande Prairie", "Alberta"),
"fortmcmurraytoday": ("Fort McMurray", "Alberta"),
"fortsaskatchewanrecord": ("Fort Saskatchewan", "Alberta"),
"peacecountrysun": ("Grande Prairie", "Alberta"),
"hannaherald": ("Drumheller", "Alberta"),
"highrivertimes": ("High River", "Alberta"),
"hinton": ("Edmonton", "Alberta"),
"lacombe": ("Lacombe", "Alberta"),
"leducrep": ("Leduc", "Alberta"),
"mayerthorpefreelancer": ("Edmonton", "Alberta"),
"nantonnews": ("Calgary", "Alberta"),
"prrecordgazette": ("Grande Prairie", "Alberta"),
"pinchercreekecho": ("Lethbridge", "Alberta"),
"sherwoodparknews": ("Edmonton", "Alberta"),
"sprucestony": ("Spruce Grove", "Alberta"),
"vermilionstandard": ("Lloydminster", "Alberta"),
"vulcanadvocate": ("Lethbridge", "Alberta"),
"wetaskiwintimes": ("Wetaskiwin", "Alberta"),
"whitecourtstar": ("Whitecourt", "Alberta"),
"princegeorgepost": ("Prince George", "British Columbia"),
"vancouversunandprovince": ("Vancouver", "British Columbia"),
"altona": ("Altona", "Manitoba"),
"beausejour": ("Beausejour", "Manitoba"),
"carman": ("Carman", "Manitoba"),
"gimli": ("Winnipeg", "Manitoba"),
"lacdubonnet": ("Lac du Bonnet", "Manitoba"),
"morden": ("Morden", "Manitoba"),
"thegraphicleader": ("Portage la Prairie", "Manitoba"),
"selkirk": ("Selkirk", "Manitoba"),
"stonewall": ("Stonewall", "Manitoba"),
"winkler": ("Winkler", "Manitoba"),
"winnipegsun": ("Winnipeg", "Manitoba"),
"northernlight": ("Bathurst", "New Brunswick"),
"thetribune": ("Campbellton", "New Brunswick"),
"dailygleaner": ("Fredericton", "New Brunswick"),
"tjnews": ("Grand Falls & Edmundston", "New Brunswick"),
"miramichileader": ("Miramichi", "New Brunswick"),
"timesandtranscript": ("Moncton", "New Brunswick"),
"letoile": ("Régions Acadiennes", "New Brunswick"), # Assuming 'obituaries' subdomain maps to "Régions Acadiennes" as per your earlier mapping for L'etoile
"telegraph-journal": ("Saint John", "New Brunswick"),
"kingscountyrecord": ("Sussex", "New Brunswick"),
"bugleobserver": ("Woodstock", "New Brunswick"),
"thetelegram": ("St. John's", "Newfoundland and Labrador"),
"thenewglasgownews": ("New Glasgow", "Nova Scotia"),
"intelligencer": ("Belleville", "Ontario"),
"brantfordexpositor": ("Brantford", "Ontario"),
"recorder": ("Brockville", "Ontario"),
"chathamdailynews": ("Chatham", "Ontario"),
"clintonnewsrecord": ("Clinton", "Ontario"),
"cochranetimespost": ("Cochrane", "Ontario"),
"standard-freeholder": ("Cornwall", "Ontario"),
"norfolkandtillsonburgnews": ("Delhi", "Ontario"),
"elliotlakestandard": ("Elliot Lake", "Ontario"),
"midnorthmonitor": ("Sudbury", "Ontario"),
"lakeshoreadvance": ("London", "Ontario"),
"gananoquereporter": ("Kingston", "Ontario"),
"goderichsignalstar": ("Goderich", "Ontario"),
"thepost": ("Durham", "Ontario"),
"kenoraminerandnews": ("Kenora", "Ontario"),
"kincardinenews": ("Port Elgin", "Ontario"),
"thewhig": ("Kingston", "Ontario"),
"northernnews": ("Kirkland Lake", "Ontario"),
"lfpress": ("London", "Ontario"),
"lucknowsentinel": ("Lucknow", "Ontario"),
"mitchelladvocate": ("Mitchell", "Ontario"),
"napaneeguide": ("Kingston", "Ontario"),
"nationalpost": ("National Post", "Ontario"),
"nugget": ("North Bay", "Ontario"),
"ottawa": ("Ottawa", "Ontario"),
"owensoundsuntimes": ("Owen Sound", "Ontario"),
"parisstaronline": ("Brantford", "Ontario"),
"pembrokeobserver": ("Pembroke", "Ontario"),
"countyweeklynews": ("Belleville", "Ontario"),
"shorelinebeacon": ("Port Elgin", "Ontario"),
"theobserver": ("Sarnia", "Ontario"),
"saultstar": ("Sault Ste. Marie", "Ontario"),
"seaforthhuronexpositor": ("Huron County", "Ontario"),
"simcoereformer": ("Simcoe", "Ontario"),
"stthomastimesjournal": ("St. Thomas", "Ontario"),
"communitypress": ("Stirling", "Ontario"),
"stratfordbeaconherald": ("Stratford", "Ontario"),
"strathroyagedispatch": ("London", "Ontario"),
"thesudburystar": ("Sudbury", "Ontario"),
"timminspress": ("Timmins", "Ontario"),
"torontosun": ("Toronto", "Ontario"),
"trentonian": ("Trenton", "Ontario"),
"wallaceburgcourierpress": ("Wallaceburg", "Ontario"),
"thechronicle-online": ("St. Thomas", "Ontario"),
"wiartonecho": ("Owen Sound", "Ontario"),
"windsorstar": ("Windsor", "Ontario"),
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
    city_province = CITY_PROVINCE_MAPPING.get(subdomain.lower())

    if city_province:
        city, province = city_province
        return city, province
    else:
        return None  # Return None if subdomain is not found in mapping



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


def process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries, stop_event):
    """Fetch obituary pages with integrated first obituary check"""
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_url = f"{base_url}/obituaries/all-categories/search?search_type=advanced&ap_search_keyword={SEARCH_KEYWORD}&sort_by=date&order=desc"

    page = 1
    max_pages = 200
    first_page_processed = False

    while page <= max_pages and not stop_event.is_set():
        current_url = f"{search_url}&p={page}" if page > 1 else search_url

        if current_url in visited_search_pages:
            break

        try:
            # Track visited pages
            visited_search_pages.add(current_url)
            logging.info(f"Processing page {page}: {current_url}")

            response = session.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Get all obituary links
            obit_links = soup.select('a[href^="/obituary/"]')
            if not obit_links:
                break

            base_page_urls = [urljoin(base_url, link["href"]) for link in obit_links]

            page_urls = []  # List to hold URLs for current page to yield later

            # Fetch publication date of the first obituary link to check city relevance
            if obit_links:
                first_obit_url = urljoin(base_url, obit_links[0]["href"])
                first_pub_date_str, _ = get_publication_date_and_soup(session, first_obit_url)

                if first_pub_date_str:
                    if not is_current_month_and_year(first_pub_date_str):
                        logging.info(f"First obituary's publication date {first_pub_date_str} is not current month and year. Skipping city {subdomain}.")
                        return  # Skip the rest of the city
                else:
                    logging.warning(f"Could not fetch publication date for first obituary on page, continuing page processing.") # Continue if date fetch fails, to not skip city prematurely


            # Prepare for sorting by fetching publication dates and current month check
            obituary_data_for_sort = []
            for link in obit_links:
                url = urljoin(base_url, link["href"])
                pub_date_str, _ = get_publication_date_and_soup(session, url)  # Fetch once here
                if pub_date_str:
                    if is_current_month_and_year(pub_date_str): # Only process current month obituaries
                        try:
                            pub_datetime = parser.parse(pub_date_str, fuzzy=True)
                            obituary_data_for_sort.append({
                                'url': url,
                                'pub_datetime': pub_datetime,
                                'pub_date_str': pub_date_str  # Store the string for later use
                            })
                        except Exception as date_parse_err:
                            logging.warning(f"Date parsing error for sorting {url}: {date_parse_err}. Skipping in sort.")
                    else:
                        logging.info(f"Obituary publication date {pub_date_str} is not current month and year. Skipping obituary.")
                else:
                    logging.warning(f"No publication date found for {url}. Skipping in sort.")


            # Sort obituaries by publication date (most recent first)
            obituary_data_for_sort.sort(key=lambda item: item['pub_datetime'], reverse=True)

            # Create sorted page_urls from sorted data
            page_urls = [item['url'] for item in obituary_data_for_sort]


            if not page_urls: # If no current month obituaries on this page, stop pagination for this city
                logging.info(f"No current month obituaries found on page {page}. Stopping pagination for city {subdomain}.")
                return # Stop pagination for this city


            yield page_urls

            # Check for next page
            next_page = soup.find("a", class_="next") or soup.find("a", string="Next")
            if not next_page:
                break
            page += 1
            time.sleep(random.uniform(0.5, 1.5))

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error on page {page}: {e}")
            break
        except Exception as e:
            logging.error(f"Unexpected error on page {page}: {e}")
            break

def get_publication_date_and_soup(session, url):
    try:
        response = session.get(url, timeout=10)  # Add timeout
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        publication_date = get_publication_date_from_soup(soup)
        return publication_date, soup
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None, None

def process_city(session, subdomain, stop_event):
    """Process city with integrated pagination and error handling"""
    logging.info(f"\nProcessing city: {subdomain.upper()}\n" + "=" * 50)

    total_alumni = 0
    visited_search_pages = set()
    visited_obituaries = set()

    try:
        # Get pagination generator
        page_generator = process_search_pagination(
            session, subdomain, visited_search_pages, visited_obituaries, stop_event
        )

        for page_urls in page_generator:
            if stop_event.is_set():
                break

            for url in page_urls:
                if stop_event.is_set():
                    break

                if url in visited_obituaries:
                    continue

                # Process obituary with retries
                success = False
                for attempt in range(3):
                    try:
                        result = process_obituary(session, db.session, url, visited_obituaries, stop_event)
                        if result and result["is_alumni"]:
                            total_alumni += 1
                        success = True
                        break
                    except requests.exceptions.RequestException as e:
                        logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                        time.sleep(2 ** attempt)

                if not success:
                    logging.error(f"Failed to process obituary after 3 attempts: {url}")

                time.sleep(random.uniform(0.7, 1.3))

    except Exception as e:
        logging.error(f"Critical error processing {subdomain}: {e}")
    finally:
        logging.info(f"Completed {subdomain}. Alumni found: {total_alumni}")



def is_current_publication_date(publication_date_str):
    if not publication_date_str:
        return False
    try:
        now = datetime.now()
        pub_date = parser.parse(publication_date_str, fuzzy=True).date()
        return pub_date.year == now.year and pub_date.month == now.month
    except Exception as e:
        logging.error(f"Date check error: {e}")
        return False

def is_current_month_and_year(publication_date_str):
    if not publication_date_str:
        return False
    try:
        now = datetime.now()
        pub_date = parser.parse(publication_date_str, fuzzy=True).date()
        return pub_date.year == now.year and pub_date.month == now.month
    except Exception as e:
        logging.error(f"Date check error: {e}")
        return False


def extract_dates(soup):
    """
    Extracts birth and death dates from the obituary details, takes soup as argument.
    Handles HTML with spans and accounts for missing information and no-year cases.
    """
    birth_date = None
    death_date = None

    obit_dates_tag = soup.find("h2", class_="obit-dates")
    if obit_dates_tag:
        date_strings = [s.strip() for s in obit_dates_tag.strings if s.strip()]  # Account for empty strings

        if len(date_strings) == 1:
            death_date = date_strings[0]  # Keep the date exactly as it is without appending a year
        elif len(date_strings) >= 2:
            birth_date = date_strings[0]
            death_date = date_strings[-1]

        # Basic data validation to handle invalid dates (empty strings or 'N/A')
        if birth_date == "N/A" or not birth_date:
            birth_date = None
        if death_date == "N/A" or not death_date:
            death_date = None

    return birth_date, death_date

def parse_date(date_str):
    """Try parsing date using dateutil.parser and return 'Month dd, yyyy' format."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True).date()
        # Format the date to 'Month dd, yyyy'
        return parsed_date.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return None

# def extract_death_and_birth_dates(text):
#     """
#     Extracts death and birth dates from the given text using spaCy NLP and relative keywords.
#     Returns:
#         A tuple containing the extracted death date and birth date (or None if not found).
#     """
#     death_date = None
#     birth_date = None
#
#     doc = nlp(text)
#
#     # Find the first death indicator to cut down on processing
#     death_index = -1  # If no indicator, still run full search
#     for i, sent in enumerate(doc.sents):
#         death_keywords = ["passing", "passed away", "death", "died", "rested", "passed", "at the age of"]
#         if any(keyword in sent.text.lower() for keyword in death_keywords):
#             death_index = i
#             break
#
#     for i, sent in enumerate(doc.sents):  # Process each sentence separately
#         death_keywords = ["passing", "passed away", "death", "died", "rested", "passed", "at the age of"]
#         birth_keywords = ["born", "birth", "born in"]
#
#         # Check for death dates and limit to the first event with the code.
#         if any(keyword in sent.text.lower() for keyword in death_keywords) and i == death_index:
#             for ent in sent.ents:
#                 if ent.label_ == "DATE":
#                     death_date = ent.text
#                     break  # Take the first date found in the sentence
#
#         # Check for birth dates at all sections.
#         if any(keyword in sent.text.lower() for keyword in birth_keywords):
#             for ent in sent.ents:
#                 if ent.label_ == "DATE":
#                     birth_date = ent.text
#                     break  # Take the first date found in the sentence
#
#     # Parse dates found in the text and format them
#     if birth_date:
#         birth_date = parse_date(birth_date)
#     if death_date:
#         death_date = parse_date(death_date)
#
#     return death_date, birth_date

def extract_year_from_date(date_string):
    """
    Extracts the year from a date string in various formats.
    Returns the year as an integer if found and valid, otherwise None.
    """
    year_match = re.search(r'\b(\d{4})\b', date_string)
    if year_match:
        year = int(year_match.group(1))
        return year
    else:
        # Handle cases where year might be in 2-digit format and assume 21st century if ambiguous, otherwise None
        year_match_2digit = re.search(r'/(\d{2})$|[-](\d{2})$|,?\s+(\d{2})$', date_string) # check for 2 digit year at end after /,- or space, comma
        if year_match_2digit:
            year_str = next((item for item in year_match_2digit.groups() if item is not None), None) # get the first non-None group
            if year_str:
                year = int(year_str)
                if 0 <= year <= 99: # Basic 2-digit year handling, assuming 21st century
                    return 2000 + year
        return None


def extract_birth_and_death_dates_from_obituary(text):
        """
        Extracts the first date found in the obituary text as the death date,
        only if the year of the date is greater than 2000. Birth date is always set to None.
        This is a simplified approach and may not be accurate in all cases.
        Returns:
            A tuple containing None as birth_date and the extracted death date string
            (or None if not found or year is not > 2000).
        """
        dates_found = []
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b',
            r'\b\d{4}\b'
        ]

        for pattern in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dates_found.append(match.group(0))
                if len(dates_found) == 1: # Only need the first date for death date check
                    break
            if len(dates_found) == 1:
                break

        death_date = None
        if dates_found:
            first_date_found = dates_found[0]
            year = extract_year_from_date(first_date_found)
            if year and year > 2000:
                death_date = first_date_found
            else:
                death_date = None # Set to None if year is not > 2000 or year extraction failed

        return None, death_date

def extract_text(tag):
    return tag.get_text(strip=True) if tag else "N/A"


def get_publication_date_from_soup(soup):
    """
    Extracts ONLY the date part from the publication line in the BeautifulSoup object,
    ignoring all other text content in the line.  Relies on date parsing to isolate the date.

    Args:
        soup: BeautifulSoup object of the obituary page.

    Returns:
        The publication date string in 'Month DD, YYYY' format if a valid date is found,
        or None if no valid date is extracted.
    """
    publication_date = None
    published_div = soup.find('div', class_='details-published')
    if published_div:
        p_tag = published_div.find('p')
        if p_tag:
            text_content = p_tag.text.strip()
            prefixes = ["Published online ", "Published on "]
            date_string_to_parse = None

            for prefix in prefixes:
                if text_content.startswith(prefix):
                    date_string_to_parse = text_content[len(prefix):].strip()
                    break
            if date_string_to_parse is None:
                date_string_to_parse = text_content # If no prefix, try to parse the whole text

            if date_string_to_parse:
                try:
                    # Parse the entire string, relying on dateutil to find the date
                    parsed_date = parser.parse(date_string_to_parse, fuzzy=True).date()
                    publication_date = parsed_date.strftime("%B %d, %Y") # Format to Month DD, YYYY
                except (ValueError, TypeError):
                    logging.warning(f"Could not parse date from text: '{text_content}'")
                    publication_date = None # Parsing failed, return None
            else:
                logging.warning(f"No date-like content found after prefix removal in: '{text_content}'")
                publication_date = None # No date-like content found, return None
    return publication_date

def process_obituary(session, db_session, url, visited_obituaries, stop_event):
    time.sleep(0.2)
    if stop_event.is_set():
        logging.info("Scraping stopped by user request (obituary level - before processing).")
        return None

    """Extract obituary details, check for alumni keywords, and store in both tables."""
    if url in visited_obituaries:
        return None
    visited_obituaries.add(url)

    logging.info(f"Processing obituary: {url}")
    try:
        response = session.get(url)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, "html.parser")

        publication_date_text = get_publication_date_from_soup(soup)

        # Extract name components
        obit_name_tag = soup.find("h1", class_="obit-name")
        last_name_tag = soup.find("span", class_="obit-lastname-upper")

        if not obit_name_tag: # Check if obit_name_tag is found
            logging.warning(f"Could not find obit-name tag for {url}")
            return None # Exit early if critical tag is missing

        if not last_name_tag: # Check if last_name_tag is found
            logging.warning(f"Could not find obit-lastname-upper tag for {url}")
            return None # Exit early if critical tag is missing

        first_name = extract_text(obit_name_tag).replace(extract_text(last_name_tag), "").strip() if obit_name_tag and last_name_tag else None
        last_name = extract_text(last_name_tag).capitalize() if last_name_tag else None

        if not first_name or not last_name:
            logging.error(f"Missing name components for obituary: {url}. First Name: {first_name}, Last Name: {last_name}")
            return None

        content = soup.select_one("span.details-copy")
        if not content: # Check if content tag is found
            logging.warning(f"Could not find details-copy tag for {url}")
            content_text = "" # Assign empty string to avoid AttributeError later
        else:
            content_text = content.get_text(strip=True)

        donation_keywords = ["donation", "charity", "memorial fund", "contributions"]
        donation_mentions = [sentence for sentence in content_text.split(". ") if
                             any(keyword in sentence.lower() for keyword in donation_keywords)]
        donation_info = "; ".join(donation_mentions)

        funeral_home_tag = soup.find("span", class_="obit-fh")  # Example selector - adjust as needed
        funeral_home = extract_text(funeral_home_tag) if funeral_home_tag else None

        tags = None # Or tags = "" if you prefer empty string

        # Extract dates and location
        obit_dates_tag = soup.find("h2", class_="obit-dates")

        if obit_dates_tag:
            tag_content = obit_dates_tag.get_text(strip=True)
            if tag_content:
                birth_date, death_date = extract_dates(soup)
            else:
                birth_date, death_date = extract_birth_and_death_dates_from_obituary(content_text)
        else:
            birth_date, death_date = extract_birth_and_death_dates_from_obituary(content_text)

        city_province_result = extract_city_and_province(url)
        if city_province_result is None:
            logging.warning(f"City and province not found for URL: {url}. Skipping obituary.")
            return None # Skip processing this obituary

        city, province = city_province_result


        # Check for alumni status
        is_alumni = any(keyword in content_text for keyword in ALUMNI_KEYWORDS)

        if is_alumni:
            from app import app
            with app.app_context():
                # Save to Obituary table
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
                    family_information=content_text,
                    funeral_home=funeral_home,  # Save funeral home
                    tags=tags,  # Save tags (initially None)
                    publication_date=publication_date_text,
                )
                db.session.add(obituary_entry)
                db.session.flush()

                # Check if DistinctObituary entry already exists
                distinct_entry_exists = DistinctObituary.query.filter_by(name=f"{first_name} {last_name}").first()
                if distinct_entry_exists:
                    logging.info(f"Duplicate alumni obituary found: {first_name} {last_name}. Skipping DistinctObituary entry.")
                else:
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
                        family_information=content_text,
                        funeral_home=funeral_home,  # Save funeral home
                        tags=tags,  # Save tags (initially None)
                        publication_date=publication_date_text,
                    )
                    db.session.add(distinct_obituary_entry)
                    db.session.commit()
                    logging.info(f"Distinct Alumni Obituary saved: {first_name} {last_name}") # Moved inside else block

        logging.info(f"Obituary saved: {first_name} {last_name} {'✅ (Alumni)' if is_alumni else '❌ (Not Alumni)'}")
        return {"name": f"{first_name} {last_name}", "is_alumni": is_alumni, "url": url, "publication_date": publication_date_text}

    except Exception as e:
        logging.error(f"Error processing obituary {url}: {e}")
        return None

def main(stop_event):
    time.sleep(15)


    session = configure_session()


    subdomains = get_city_subdomains(session)

    if not subdomains:
        logging.error("No city subdomains found.")
        return

    for idx, subdomain in enumerate(subdomains, 1):
        if stop_event.is_set():  # Check stop_event - CHANGED from scraping_active check
            logging.info("Scraping stopped by user request (city level).")
            break  # Exit city loop if event is set

        logging.info(f"\nProcessing city {idx}/{len(subdomains)}: {subdomain}")
        process_city(session, subdomain, stop_event)

    logging.info("\nScraping completed or stopped.")

if __name__ == "__main__":
    pass