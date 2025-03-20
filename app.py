# app.py
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_migrate import Migrate
from sqlalchemy import extract, func, text
from flask import flash
from sqlalchemy.orm import aliased

import logging
from flask_sqlalchemy import SQLAlchemy
from models import Obituary, DistinctObituary, db

import csv, json
from flask import send_file
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz

# Initialize Flask app (rest remains same as before)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                       'postgresql://postgres:admin@localhost/rememberingDB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
migrate = Migrate(app, db)
db.init_app(app)

# Import models to register with SQLAlchemy
from scrapper import main

# --- Global variables to track scraper state ---
scrape_thread = None
stop_event = threading.Event()
last_scrape_time = None

# --- Flask Routes ---
@app.route('/')
def dashboard():
    """Route to display the scraper dashboard."""
    with app.app_context():
        total_alumni = DistinctObituary.query.distinct(DistinctObituary.name).count()
        total_obituaries = DistinctObituary.query.count()
        total_cities = len(set(obit.city for obit in DistinctObituary.query.all() if obit.city))
        latest_obituaries = DistinctObituary.query.limit(15).all()
        scraping_active = not stop_event.is_set()
        return render_template('dashboard.html',
                               total_alumni=total_alumni,
                               total_obituaries=total_obituaries,
                               total_cities=total_cities,
                               obituaries=latest_obituaries,
                               scraping_active= scraping_active,) # Pass scraping_active to template

@app.route('/search_obituaries')
def search_obituaries():
    """Route to return search results as JSON for dashboard filtering.""" # Updated docstring
    first_name_query = request.args.get('firstName', '').strip()
    last_name_query = request.args.get('lastName', '').strip()
    city_query = request.args.get('city', '').strip()
    province_query = request.args.get('province', '').strip()
    query_string = request.args.get('query', '').strip()

    with app.app_context():
        query_filter = DistinctObituary.query.filter(DistinctObituary.is_alumni == True)

        # Advanced Search Filters
        if first_name_query:
            query_filter = query_filter.filter(DistinctObituary.first_name.ilike(f"%{first_name_query}%"))
        if last_name_query:
            query_filter = query_filter.filter(DistinctObituary.last_name.ilike(f"%{last_name_query}%"))
        if city_query:
            query_filter = query_filter.filter(DistinctObituary.city.ilike(f"%{city_query}%"))
        if province_query and province_query != '':
            query_filter = query_filter.filter(DistinctObituary.province == province_query)


        if query_string: # Simple search - if general query is present, it takes precedence
             query_filter = DistinctObituary.query.filter(
                (DistinctObituary.first_name.ilike(f"%{query_string}%")) |
                (DistinctObituary.last_name.ilike(f"%{query_string}%")) |
                 (DistinctObituary.content.ilike(f"%{query_string}%")) # Assuming content exists in DistinctObituary
            )

        logging.info(f"Search Query: {str(query_filter)}")

        obituaries = query_filter.order_by(DistinctObituary.last_name).all()

        logging.info(f"Search Query returned {len(obituaries)} obituaries")

        obituary_list = [{  # Prepare obituary data as dictionaries for JSON response
            'id': obit.id,
            'name': obit.name,
            'first_name': obit.first_name,
            'last_name': obit.last_name,
            'obituary_url': obit.obituary_url,
            'city': obit.city,
            'province': obit.province,
            'birth_date': obit.birth_date,
            'death_date': obit.death_date,
            'publication_date': obit.publication_date,
            'is_alumni': obit.is_alumni,
            'tags': obit.tags,
        } for obit in obituaries]

        return jsonify(obituary_list)


@app.route('/get_obituaries')
def get_obituaries():
    """Route to fetch distinct alumni obituaries data, ordered by city and publication date."""
    with app.app_context():
        # Subquery to rank entries by name and publication date
        subquery = db.session.query(
            DistinctObituary,
            func.row_number().over(
                partition_by=DistinctObituary.name,  # Group by name
                order_by=DistinctObituary.publication_date.desc()  # Latest first
            ).label('row_num')
        ).subquery()

        # Create an alias to map back to our model
        ObituaryAlias = aliased(DistinctObituary, subquery)

        # Get only the latest entry per name
        obituaries = db.session.query(ObituaryAlias).\
            filter(subquery.c.row_num == 1).\
            order_by(ObituaryAlias.publication_date.desc()).\
            all()
        
        obituary_list = [{
            'id': obit.id,
            'name': obit.name,
            'first_name': obit.first_name,
            'last_name': obit.last_name,
            'obituary_url': obit.obituary_url,
            'city': obit.city,
            'province': obit.province,
            'birth_date': obit.birth_date,
            'death_date': obit.death_date,
            'publication_date': obit.publication_date, # <---- Make sure publication_date is included
            'is_alumni': obit.is_alumni,
            'tags': obit.tags,
        } for obit in obituaries]
        return jsonify(obituary_list)

@app.route('/api/publications/grouped-by-year')
def get_publications_by_year_endpoint():
    """API endpoint to get publications grouped by year."""
    publications_by_year = get_publications_grouped_by_year()
    if publications_by_year:
        return jsonify(publications_by_year)
    else:
        return jsonify({"error": "Failed to fetch publications by year"}), 500


def get_publications_grouped_by_year():
    """
+   Fetches publications from the database, grouped by publication year,
+   and categorized into year groups (2025, 2024, 2023, 2022, <2022).
+   """
    try:
        result = (
            db.session.query(
                extract('year', DistinctObituary.publication_date).label('publication_year'),
                func.json_agg(func.json_build_object(
                    'id', DistinctObituary.id,
                    'name', DistinctObituary.name,
                    'first_name', DistinctObituary.first_name,
                    'last_name', DistinctObituary.last_name,
                    'obituary_url', DistinctObituary.obituary_url,
                    'city', DistinctObituary.city,
                    'province', DistinctObituary.province,
                    'birth_date', DistinctObituary.birth_date,
                    'death_date', DistinctObituary.death_date,
                    'publication_date', DistinctObituary.publication_date,
                    'is_alumni', DistinctObituary.is_alumni,
                    'tags', DistinctObituary.tags
                )).label('publications_in_year')
            )
            .group_by(extract('year', DistinctObituary.publication_date))
            .order_by(text('publication_year DESC'))
            .all()
        )

        grouped_data = {
            "2025": [], "2024": [], "2023": [], "2022": [], "Before 2022": []
        }

        for row in result:
            year = row.publication_year
            year_str = str(int(year)) if year else None # Convert year to string for dictionary key
            if year_str in grouped_data: # Check if year_str is a key in grouped_data
                grouped_data[year_str] = list(row.publications_in_year) if row.publications_in_year else [] # Ensure it's a list
            elif year and year < 2022:
                grouped_data["Before 2022"].extend(list(row.publications_in_year) if row.publications_in_year else []) # Extend for <2022 group

        return grouped_data
    except Exception as e:
        print(f"Database error fetching publications by year: {e}")
        return None


@app.route('/update_tags/<int:obituary_id>', methods=['POST'])
def update_tags(obituary_id):
    new_tags = request.form.get('tags')

    # Update Obituary
    obituary = Obituary.query.get_or_404(obituary_id)
    obituary.tags = new_tags

    # Update DistinctObituary if exists
    distinct_obit = DistinctObituary.query.filter_by(
        obituary_url=obituary.obituary_url
    ).first()
    if distinct_obit:
        distinct_obit.tags = new_tags

    db.session.commit()
    return redirect(url_for('obituary_detail', obituary_id=obituary_id))

def is_last_day_of_month():
    logging.info("Checking is_last_day_of_month...") # Log when function is called
    tomorrow = datetime.now(pytz.utc) + timedelta(days=1)
    result = tomorrow.day == 1
    return result


def auto_scrape_job():
    logging.info("auto_scrape_job function called") # Log at start
    if is_last_day_of_month():
        logging.info("⏰ AUTOSCRAPE: is_last_day_of_month returned True") # Log when condition is met
        logging.info("⏰ AUTOSCRAPE: Last day of month detected, starting automated scrape")
        try:
            main(stop_event)  # Use your existing main function
            logging.info("✅ AUTOSCRAPE: Monthly auto-scrape completed successfully")
        except Exception as e:
            logging.error(f"❌ AUTOSCRAPE ERROR inside try block: {str(e)}") # More specific error log
        finally:
            stop_event.set()
    else:
        logging.info("auto_scrape_job: is_last_day_of_month returned False, skipping scrape.") # Log when not last day

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.utc)

    # Run auto_scrape_job every minute for testing
    scheduler.add_job(
        auto_scrape_job,  # Use auto_scrape_job again
        'cron',
        hour=0,
        minute=0,
        id='monthly_scrape'# Keep the same id or change
    )

    scheduler.start()
    logging.info("⏲️  Scheduler started - Auto-scrape job scheduled every month for testing.") # Update log message

@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    """Route to start the scraper in a background thread."""
    global scrape_thread, stop_event, last_scrape_time

    if not stop_event.is_set():
        db.session.query(Obituary).update({Obituary.tags: 'updated'})
        db.session.query(DistinctObituary).update({DistinctObituary.tags: 'updated'})
        db.session.commit() # Check event status instead of boolean flag
        return jsonify({'message': 'Scraping is already running!'}), 400

    stop_event.clear()  # Clear the stop event to start scraping

    # Overwrite CSV before starting the scraper
    csv_file_path = "obituaries_data.csv"
    if os.path.exists(csv_file_path):
        open(csv_file_path, 'w').close()  # Truncate the file (overwrite)

    scrape_thread = threading.Thread(target=run_scraper_background, args=(stop_event,)) # Pass stop_event as argument
    scrape_thread.start()

    last_scrape_time = datetime.now()

    return jsonify({
        'message': 'Scraping started in the background.',
        'scraping_active': True, # Add this line
        'last_scrape_time': last_scrape_time.isoformat()
    })


@app.route('/stop_scrape', methods=['POST'])
def stop_scrape():
    """Route to stop the scraper (set event to stop gracefully)."""
    global stop_event, last_scrape_time

    if stop_event.is_set(): # Check event status instead of boolean flag
        return jsonify({'message': 'Scraping is not currently running!'}), 400

    stop_event.set()  # Set the stop event to signal scraper to stop
    time.sleep(2)  # Keep delay for testing, can remove later

    last_scrape_time = datetime.now()

    return jsonify({
        'message': 'Stopping scraping...',
        'scraping_active': False,
        'last_scrape_time': last_scrape_time.isoformat() # Add this line
    })


@app.route('/scrape_status')
def scrape_status():
    global last_scrape_time
    """Route to get the current scraping status."""
    return jsonify({'scraping_active': not stop_event.is_set(), 'last_scrape_time': last_scrape_time.isoformat() if last_scrape_time else None})


def run_scraper_background(stop_event):
    """Function to run the scraper in the background thread."""
    logging.info("Scraper background thread started.")
    try:
        main(stop_event)  # Pass stop_event to main()
    except Exception as e:
        logging.error(f"Scraper background thread encountered an error: {e}")
    finally:
        # Automatically stop when done
        with app.app_context():
            try:
                client = app.test_client()
                client.post('/stop_scrape')
                logging.info("Automatic stop triggered after completion")
            except Exception as e:
                logging.error(f"Error triggering automatic stop: {e}")
        logging.info("Scraper background thread finished.")

@app.route('/obituary/<int:obituary_id>')
def obituary_detail(obituary_id):
    """Route to display details for a specific obituary."""
    with app.app_context():
        obituary = DistinctObituary.query.get_or_404(obituary_id) # Fetch from DistinctObituary, or Obituary if you prefer
        return render_template('obituary_detail.html', obituary=obituary)


def generate_csv():
    """Helper function to generate a fresh CSV file from the database."""
    with app.app_context():
        obituaries = DistinctObituary.query.order_by(DistinctObituary.publication_date.desc()).all()

        if not obituaries:
            return None  # No data available

        csv_file_path = "obituaries_data.csv"

        with open(csv_file_path, 'w', newline='') as csvfile:
            fieldnames = ['id', 'name', 'first_name', 'last_name', 'city', 'province', 'birth_date',
                          'death_date', 'obituary_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for obit in obituaries:
                writer.writerow({
                    'id': obit.id,
                    'name': obit.name,
                    'first_name': obit.first_name,
                    'last_name': obit.last_name,
                    'obituary_url': obit.obituary_url,
                    'city': obit.city,
                    'province': obit.province,
                    'birth_date': obit.birth_date,
                    'death_date': obit.death_date,
                    'tags': obit.tags,
                })

        return csv_file_path  # Return the file path


@app.route('/download_csv')
def download_csv():
    """Route to generate and download obituaries data as CSV."""
    csv_file = generate_csv()  # Generate CSV before downloading
    if not csv_file:
        return jsonify({'error': 'No obituaries available to download'}), 404

    return send_file(csv_file, as_attachment=True, download_name="obituaries.csv", mimetype="text/csv")


@app.route('/about')
def about():
    """Route to display the About page."""
    return render_template('about.html')


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        start_scheduler()  # Start the scheduler
        stop_event.set()
    app.run(debug=True)