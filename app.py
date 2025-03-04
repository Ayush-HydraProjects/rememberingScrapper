# app.py
import os
from flask import Flask, render_template, jsonify, request
from flask_migrate import Migrate

import logging
from flask_sqlalchemy import SQLAlchemy
from models import Obituary, DistinctObituary, db # Import DistinctObituary

# Initialize Flask app (rest remains same as before)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                       'postgresql://postgres:admin@localhost/rememberingDB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
migrate = Migrate(app, db)
db.init_app(app)

# Import models to register with SQLAlchemy
from scrapper import main


# --- Flask Routes ---
@app.route('/')
def dashboard():
    """Route to display the scraper dashboard with latest distinct obituaries.""" # Updated docstring
    with app.app_context():
        total_alumni = DistinctObituary.query.filter_by(is_alumni=True).count() # Use DistinctObituary
        total_obituaries = DistinctObituary.query.count() # Use DistinctObituary
        total_cities = len(set(obit.city for obit in DistinctObituary.query.all() if obit.city)) # Use DistinctObituary
        latest_obituaries = DistinctObituary.query.filter_by(is_alumni=True).order_by(DistinctObituary.id.desc()).limit(10).all() # Use DistinctObituary

        return render_template('dashboard.html',
                               total_alumni=total_alumni,
                               total_obituaries=total_obituaries,
                               total_cities=total_cities,
                               obituaries=latest_obituaries) # Pass distinct obituaries to template

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

        obituaries = query_filter.order_by(DistinctObituary.last_name).limit(50).all()

        logging.info(f"Search Query returned {len(obituaries)} obituaries") # <----- Log result count

        obituary_list = [{  # Prepare obituary data as dictionaries for JSON response
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


@app.route('/scrape', methods=['POST'])  # Expect POST for scrape trigger
def run_scraper_route():
    """Route to trigger the scraper (still targets Obituary table as before)."""
    with app.app_context():
        main() # Assuming main() still populates the Obituary table
    return jsonify({'message': 'Scraping completed successfully!'})  # Return JSON response with message



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


if __name__ == "__main__":
    with app.app_context():
        db.drop_all() # Be careful with drop_all in production!
        db.create_all()
    app.run(debug=True)