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

from sqlalchemy import exc


from models import Obituary, DistinctObituary, Metadata, db # Import DistinctObituary model
from datetime import datetime
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
"calgaryherald": ("Calgary", "Alberta"),
"calgarysun": ("Calgary", "Alberta"),
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
"theannapolisvalleyregister": ("Annapolis Royal", "Nova Scotia"),
"thecapebretonpost": ("Cape Breton", "Nova Scotia"),
"thetricountyvanguard": ("Digby, Shelburne and Yarmouth Counties", "Nova Scotia"),
"thechronicleherald": ("Halifax", "Nova Scotia"),
"thevalleyjournaladvertiser": ("Hantsport", "Nova Scotia"),
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
"ottawacitizen": ("Ottawa", "Ontario"),
"ottawasun": ("Ottawa", "Ontario"),
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

def process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries, stop_event, new_entries_processed, new_entries_count): # <- Removed state params
    """Fetch obituary pages for a city"""
    time.sleep(0.5)
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_url = f"{base_url}/obituaries/all-categories/search?search_type=advanced&ap_search_keyword={SEARCH_KEYWORD}&sort_by=date&order=desc"

    page = 1
    max_pages = 200
            
    while page <= max_pages:
        
        if new_entries_processed >= new_entries_count:
            logging.info("All new entries have been processed. Skipping remaining pages.")
            return  # Exit pagination loop

        if stop_event.is_set():  # Check stop_event - CHANGED from scraping_active check
            logging.info("Scraping stopped by user request (pagination level).")
            return  # Exit page loop if event is set

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


new_records_count = 0  # To track new records
new_entries_processed = 0 # To track the actual new entries that are processed
visited_obituaries = set()
total_alumni = 0

def process_city(session, subdomain, stop_event):
    """Process all obituary pages in a city"""

    logging.info(f"\nProcessing city: {subdomain.upper()}\n" + "=" * 50)
    global total_alumni, new_records_count, new_entries_processed, visited_obituaries

    # total_alumni = 0
    visited_search_pages = set()
    # visited_obituaries = set()
    latest_publication_date = None
    latest_publication_date_str = None
    # new_records_count = 0  # To track new records
    # new_entries_processed = 0 # To track the actual new entries that are processed
   

    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_url = f"{base_url}/obituaries/all-categories/search?search_type=advanced&ap_search_keyword={SEARCH_KEYWORD}&sort_by=date&order=desc"

    city_scraped_successfully = False  # Flag to track if the city was fully scraped

    try:
        from app import app
        with app.app_context():
            db.create_all() 
            db_data = db.session.execute(db.text("SELECT * FROM metadata WHERE city = :city"), {"city": subdomain}).fetchone()
            logging.info(f"DDDDDDDBBBBBBBBBB DAAAAAATTAA  {db_data}")
            if db_data:
                last_record_count = db_data[4]  # Assuming the correct column index for last_record_count
                last_publication_date_str = db_data[5]  # Assuming the correct column index for last_publication_date
                last_publication_date = datetime.strptime(last_publication_date_str, "%B %d, %Y") if last_publication_date_str else None
            else:
                logging.info(f"No existing record found for city {subdomain}. Setting last_record_count to 0.")
                last_record_count = 0
                last_publication_date = None

            # try:
            #     db_data = db.session.execute(db.text("SELECT * FROM Metadata WHERE city = :city"), {"city": subdomain}).fetchone()
            #     if db_data:
            #         last_record_count = db_data[4]  # Assuming the correct column index for last_record_count
            #         last_publication_date_str = db_data[5]  # Assuming the correct column index for last_publication_date
            #         last_publication_date = datetime.strptime(last_publication_date_str, "%B %d, %Y") if last_publication_date_str else None
            #     else:
            #         logging.info(f"No existing record found for city {subdomain}. Setting last_record_count to 0.")
            #         last_record_count = 0
            #         last_publication_date = None
            # except exc.NoSuchTableError as e: #or exc.UndefinedTable as e:  # Capture the specific error
            #     logging.warning(f"Table 'Metadata' does not exist: {e}.  Continuing with scraping assuming no previous data.")
            #     last_record_count = 0
            #     last_publication_date = None

            response = session.get(search_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            number_of_stories_element = soup.find("p", class_="notices-counter")
            if number_of_stories_element:
                number_text = number_of_stories_element.get_text(strip=True)
                number_of_stories = int(''.join(filter(str.isdigit, number_text)))
            else:
                number_of_stories = 0

            logging.info(f"Total number of stories found: {number_of_stories}")

            # Skip processing if no new records based on total count and date.
            if number_of_stories <= last_record_count and last_publication_date:
                logging.info(f"No new records found for city {subdomain} based on total count. Checking publication date.")

                # Check if the latest publication date on the site is older or the same as the last scraped date.
                # latest_date_element = soup.find("div", class_="obituary-date") # Adapt selector to your HTML
                # if latest_date_element:
                #     latest_date_str_on_site = latest_date_element.get_text(strip=True)
                # try:
                    # latest_date_on_site = datetime.strptime(latest_date_str_on_site, "%B %d, %Y")  # Adjust format if necessary
                    # if latest_date_on_site <= last_publication_date:
                logging.info(f"No new records found for {subdomain}. Skipping city.")
                return None  # Skip processing
                # except ValueError:
                #     logging.warning(f"Could not parse date: {latest_date_str_on_site}")
                # else:
                #     logging.warning("Could not find latest date on the site.  Skipping date check.")


            new_entries_count = number_of_stories - last_record_count
            logging.info(f"New entries to scrape: {new_entries_count}")

        for page_urls in process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries, stop_event, new_entries_processed, new_entries_count):
            logging.info(f"New Entries Processed: {new_entries_processed}, new_entries_count : {new_entries_count}")
            new_entries_processed = new_entries_processed
            if new_entries_processed >= new_entries_count:
                 break  # Exit outer loop if processed all

            if stop_event.is_set():
                logging.info("Scraping stopped by user request (city level - start of city processing).")
                return None  # Exit without updating metadata

            for url in page_urls:
                if stop_event.is_set():
                    logging.info("Scraping stopped by user request (city level - before processing URL).")
                    return None  # Exit without updating metadata

                if url in visited_obituaries:
                    continue

                result = process_obituary(session, db.session, url, visited_obituaries, stop_event)
                # logging.info(f" RESUUUUUUUUUULT {result}")

                if result and result["is_alumni"]:
                    total_alumni += 1

                pub_date_str = result.get("publication_date")
                pub_date_str = pub_date_str.split("in")[0].strip()
                if pub_date_str:
                    try:
                        logging.info(f" DDDATTTTTTTTE sttttttttttrrrrrrr {pub_date_str}.")
                        pub_date = datetime.strptime(pub_date_str, "%B %d, %Y")
                        logging.info(f"PUUUUUBBBBBBB DDDATTTTTTTTE {pub_date}.")
                        # Check if the publication date is greater than the last scraped date.
                        if last_publication_date is None or pub_date > last_publication_date:
                            new_records_count += 1 #increment the count for new records

                            new_entries_processed +=1  # Increment counter when actually processing a new entry

                            if latest_publication_date is None or pub_date > latest_publication_date:
                                latest_publication_date = pub_date
                                latest_publication_date_str = pub_date_str

                            # Check if we've processed all new entries, if so, exit loop
                            if new_entries_processed >= new_entries_count:
                                logging.info(f"Processed all new entries for {subdomain}.")
                                break # Exit inner loop

                    except ValueError:
                        logging.warning(f"Invalid date format: {pub_date_str}")
                else:
                    logging.warning(f"Publication date not found for URL: {url}")

                time.sleep(random.uniform(0.7, 1.3))

                if stop_event.is_set():
                    logging.info("Scraping stopped by user request (city level - after processing URL).")
                    return None  # Exit without updating metadata
                

        city_scraped_successfully = True  # Set flag to True only if scraping completes successfully

    except (ValueError, TypeError) as e:
        logging.error(f"Error processing {subdomain}: {e}")
        return None  # Exit without updating metadata

    finally:
        new_records_count = 0  # To track new records
        new_entries_processed = 0
        if city_scraped_successfully:  # Update metadata only if full scraping was successful
            try:
                from app import app
                with app.app_context():
                    if latest_publication_date_str:
                        latest_publication_date = datetime.strptime(latest_publication_date_str, "%B %d, %Y").date()
                        latest_publication_date_str = latest_publication_date.strftime("%B %d, %Y") if latest_publication_date else None
                    else:
                        latest_publication_date = None

                    last_scrape_epoch = int(datetime.now().timestamp())
                    last_scrape_date = datetime.now().strftime("%B %d, %Y")

                    metadata_entry = Metadata.query.filter_by(city=subdomain).first()

                    if metadata_entry:
                        metadata_entry.last_scrape_date = last_scrape_date
                        metadata_entry.last_scrape_timestamp = last_scrape_epoch
                        metadata_entry.last_record_count = number_of_stories # Use total stories, not just the 'new' ones
                        metadata_entry.last_publication_date = latest_publication_date_str
                    else:
                        new_metadata = Metadata(
                            city=subdomain,
                            last_scrape_date=last_scrape_date,
                            last_scrape_timestamp=last_scrape_epoch,
                            last_record_count=number_of_stories,
                            last_publication_date=latest_publication_date_str
                        )
                        db.session.add(new_metadata)

                    db.session.commit()
                    logging.info(f"Updated ScrapeMetadata for {subdomain}: {new_records_count} new records, last publication date: {latest_publication_date_str}")

            except (ValueError, TypeError) as e:
                logging.error(f"Error updating metadata for {subdomain}: {e}")

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
    Extracts only the date part from the publication line in the BeautifulSoup object.

    Args:
        soup: BeautifulSoup object of the obituary page.

    Returns:
        The publication date string, or None if not found or date extraction fails.
    """
    publication_date = None
    published_div = soup.find('div', class_='details-published')
    if published_div:
        p_tag = published_div.find('p')
        if p_tag:
            text_content = p_tag.text.strip()
            prefixes = ["Published online ", "Published on "]
            extracted_date = None
            for prefix in prefixes:
                if text_content.startswith(prefix):
                    extracted_date = text_content[len(prefix):].strip()
                    break # Stop after finding the first matching prefix
            if extracted_date:
                publication_date = extracted_date
                # logging.info(f"Publication date : '{publication_date}'")
            else:
                logging.warning(f"Publication date prefix not found in: '{text_content}'")
                publication_date = text_content # Or publication_date = None, or handle as needed

    return publication_date

def process_obituary(session, db_session, url, visited_obituaries, stop_event):
    time.sleep(0.2)
    if stop_event.is_set():  # Check stop_event - CHANGED from scraping_active check
        logging.info("Scraping stopped by user request (obituary level - before processing).")
        return None

    """Extract obituary details, check for alumni keywords, and store in both tables."""
    if url in visited_obituaries:
        return None
    visited_obituaries.add(url)

    logging.info(f"Processing obituary: {url}")
    try:
        response = session.get(url)
        response.raise_for_status()
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
            logging.error(f"Missing name for obituary: {url}")
            return None

        content = soup.select_one("span.details-copy").get_text(strip=True) if soup.select_one("span.details-copy") else ""

        donation_keywords = ["donation", "charity", "memorial fund", "contributions"]
        donation_mentions = [sentence for sentence in content.split(". ") if
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
                birth_date, death_date = extract_birth_and_death_dates_from_obituary(content)
        else:
            birth_date, death_date = extract_birth_and_death_dates_from_obituary(content)

        city, province = extract_city_and_province(url)

        # ********************  ADD THIS SECTION  ********************
        # Extract publication date
        # publication_date_tag = soup.find("div", class_="details-published")
        # publication_date = None
        # if publication_date_tag:
        #     # Extract the text and remove "Published on"
        #     # publication_date_text = publication_date_tag.get_text(strip=True).replace("Published on", "").strip()
        #     publication_date = publication_date_text
        logging.info(f"Pulblished on : {publication_date_text}")

        # ********************  END ADDED SECTION  ********************

        # Check for alumni status
        is_alumni = any(keyword in content for keyword in ALUMNI_KEYWORDS)

        if is_alumni:
            from app import app
            with app.app_context():
                # Save to Obituary table
                # obituary_entry = Obituary(
                #     name=f"{first_name} {last_name}",
                #     first_name=first_name,
                #     last_name=last_name,
                #     birth_date=birth_date,
                #     death_date=death_date,
                #     donation_information=donation_info,
                #     obituary_url=url,
                #     city=city,
                #     province=province,
                #     is_alumni=is_alumni,
                #     family_information=content,
                #     funeral_home=funeral_home,  # Save funeral home
                #     tags=tags,  # Save tags (initially None)
                #     publication_date=publication_date_text,
                # )
                # db.session.add(obituary_entry)
                # db.session.flush()
                existing_obituary = Obituary.query.filter_by(obituary_url=url).first()

                if not existing_obituary:  # Only insert if it doesn't exist
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
                        funeral_home=funeral_home,
                        tags=tags,  # Save tags (initially None)
                        publication_date=publication_date_text,
                    )
                    db.session.add(obituary_entry)
                    db.session.flush()
                else:
                    logging.info(f"Skipping duplicate obituary: {url}")

                # Save to DistinctObituary if not already present
                distinct_entry_exists = DistinctObituary.query.filter_by(name=f"{first_name} {last_name}").first()
                if not distinct_entry_exists:
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
                        funeral_home=funeral_home,  # Save funeral home
                        tags=tags,  # Save tags (initially None)
                        publication_date=publication_date_text,
                    )
                    db.session.add(distinct_obituary_entry)

                db.session.commit()

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