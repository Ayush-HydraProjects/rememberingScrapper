# app.py
import os
from flask import Flask, render_template, jsonify, request
from flask_migrate import Migrate

import logging
from flask_sqlalchemy import SQLAlchemy
from models import Obituary, DistinctObituary, db

import threading  # Import threading
import time  # For simple delay in stop function

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
scrape_thread = None  # To hold the scraping thread
stop_event = threading.Event()  # Use threading.Event instead of boolean flag # <---- CHANGED

# --- Flask Routes ---
@app.route('/')
def dashboard():
    """Route to display the scraper dashboard."""
    with app.app_context():
        total_alumni = DistinctObituary.query.filter_by(is_alumni=True).count()
        total_obituaries = DistinctObituary.query.count()
        total_cities = len(set(obit.city for obit in DistinctObituary.query.all() if obit.city))
        latest_obituaries = DistinctObituary.query.limit(15).all()
        scraping_active = not stop_event.is_set()
        return render_template('dashboard.html',
                               total_alumni=total_alumni,
                               total_obituaries=total_obituaries,
                               total_cities=total_cities,
                               obituaries=latest_obituaries,
                               scraping_active= scraping_active) # Pass scraping_active to template

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
             query_filter = DistinctObituary.query.filter( # Overwrite query_filter for simple search
                (DistinctObituary.first_name.ilike(f"%{query_string}%")) |
                (DistinctObituary.last_name.ilike(f"%{query_string}%")) |
                 (DistinctObituary.content.ilike(f"%{query_string}%")) # Assuming content exists in DistinctObituary
            )

        logging.info(f"Search Query: {str(query_filter)}") # <----- Log the query

        obituaries = query_filter.order_by(DistinctObituary.last_name).all()

        logging.info(f"Search Query returned {len(obituaries)} obituaries") # <----- Log result count

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
            'is_alumni': obit.is_alumni,
        } for obit in obituaries]

        return jsonify(obituary_list)


@app.route('/get_obituaries')
def get_obituaries():
    """Route to fetch latest distinct alumni obituaries data, limited to 15 initially."""
    with app.app_context():
        obituaries = DistinctObituary.query.all() # Limit to 15 entries
        obituary_list = [{  # Prepare distinct obituary data as dictionaries
            'id': obit.id,
            'name': obit.name,
            'first_name': obit.first_name,
            'last_name': obit.last_name,
            'obituary_url': obit.obituary_url,
            'city': obit.city,
            'province': obit.province,
            'birth_date': obit.birth_date,
            'death_date': obit.death_date,
            # 'funeral_home': obit.funeral_home,
            'is_alumni': obit.is_alumni,
        } for obit in obituaries]
        return jsonify(obituary_list)  # Return JSON response


@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    """Route to start the scraper in a background thread."""
    global scrape_thread, stop_event

    if not stop_event.is_set(): # Check event status instead of boolean flag # <---- CHANGED
        return jsonify({'message': 'Scraping is already running!'}), 400

    stop_event.clear()  # Clear the stop event to start scraping # <---- CHANGED
    scrape_thread = threading.Thread(target=run_scraper_background, args=(stop_event,)) # Pass stop_event as argument # <---- CHANGED
    scrape_thread.start()
    return jsonify({
        'message': 'Scraping started in the background.',
        'scraping_active': True  # Add this line
    })


@app.route('/stop_scrape', methods=['POST'])
def stop_scrape():
    """Route to stop the scraper (set event to stop gracefully)."""
    global stop_event

    if stop_event.is_set(): # Check event status instead of boolean flag # <---- CHANGED
        return jsonify({'message': 'Scraping is not currently running!'}), 400

    stop_event.set()  # Set the stop event to signal scraper to stop # <---- CHANGED
    time.sleep(2)  # Keep delay for testing, can remove later
    return jsonify({
        'message': 'Stopping scraping...',
        'scraping_active': False  # Add this line
    })


@app.route('/scrape_status')
def scrape_status():
    """Route to get the current scraping status."""
    return jsonify({'scraping_active': not stop_event.is_set()})


def run_scraper_background(stop_event):
    """Function to run the scraper in the background thread."""
    logging.info("Scraper background thread started.")
    try:
        main(stop_event)  # Pass stop_event to main() # <---- CHANGED
    except Exception as e:
        logging.error(f"Scraper background thread encountered an error: {e}")
    finally:
        logging.info("Scraper background thread finished.")



# @app.route('/dashboard_summary') # No changes needed here if summary is based on DistinctObituary now
# def dashboard_summary():
#     """Route to get dashboard summary data."""
#     with app.app_context():
#         total_alumni = DistinctObituary.query.filter_by(is_alumni=True).count() # Use DistinctObituary
#         total_obituaries = DistinctObituary.query.count() # Use DistinctObituary
#         total_cities = len(set(obit.city for obit in DistinctObituary.query.all() if obit.city)) # Use DistinctObituary
#         return jsonify({  # Return summary data as JSON
#             'total_alumni': total_alumni,
#             'total_obituaries': total_obituaries,
#             'total_cities': total_cities,
#         })

@app.route('/obituary/<int:pk>')
def obituary_detail(pk):
    """Route to display details for a specific obituary."""
    with app.app_context():
        obituary = DistinctObituary.query.get_or_404(pk) # Fetch from DistinctObituary, or Obituary if you prefer
        return render_template('obituary_detail.html', obituary=obituary)

if __name__ == "__main__":
    with app.app_context():
        db.drop_all() # Be careful with drop_all in production!
        db.create_all()
        stop_event.set()
    app.run(debug=True)