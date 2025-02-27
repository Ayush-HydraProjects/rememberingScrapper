import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize Flask app
app = Flask(__name__)

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/rememberingDB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models to register with SQLAlchemy
from models import Obituary
from scrapper import main # Import scraper's main function

# --- Flask Routes ---
@app.route('/scrape')
def run_scraper_route(): # Renamed to avoid namespace conflict with scraper.py's main()
    with app.app_context():
        main() # Run scraper's main function within app context
    return "Scraping completed. Check logs for details.", 200

if __name__ == "__main__":
    with app.app_context(): # Create app context for initial db operations
        db.create_all() # Create database tables if they don't exist

    app.run(debug=True)