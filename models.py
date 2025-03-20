# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class Obituary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    # publication_date = db.Column(db.Date, nullable=True)
    birth_date = db.Column(db.String(50), nullable=True)
    death_date = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(255), nullable=True)
    publication_date = db.Column(db.DateTime(50), nullable=True)
    obituary_url = db.Column(db.String(255), unique=True, nullable=False)
    family_information = db.Column(db.Text, nullable=True)
    donation_information = db.Column(db.Text, nullable=True)
    is_alumni = db.Column(db.Boolean, default=False)
    funeral_home = db.Column(db.String(255), nullable=True) # New field: Funeral Home
    tags = db.Column(db.Text, nullable=True) # New field: Tags (comma-separated string for now)

    def __repr__(self):
        return f"<Obituary {self.name} - {self.city}, {self.province}>"

class DistinctObituary(db.Model): # New model for dist_obituary
    __tablename__ = 'dist_obituary' # Specify the table name if it's different from class name

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    # publication_date = db.Column(db.String(255), nullable=True)
    birth_date = db.Column(db.String(50), nullable=True)
    death_date = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(255), nullable=True)
    publication_date = db.Column(db.DateTime(50), nullable=True)
    obituary_url = db.Column(db.String(255), unique=True, nullable=False)
    family_information = db.Column(db.Text, nullable=True)
    donation_information = db.Column(db.Text, nullable=True)
    is_alumni = db.Column(db.Boolean, default=False)
    funeral_home = db.Column(db.String(255), nullable=True) # New field: Funeral Home
    tags = db.Column(db.Text, nullable=True) # New field: Tags (comma-separated string for now)


    def __repr__(self):
        return f"<DistinctObituary {self.name} - {self.city}, {self.province}>"
    

class Metadata(db.Model):
    __tablename__ = 'metadata'  # Explicitly setting the table name

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(255), unique=True, nullable=False)  # City name
    last_scrape_date = db.Column(db.String(50), nullable=False)  # Store human-readable date (string format)
    last_scrape_timestamp = db.Column(db.Integer, default=lambda: int(datetime.now().timestamp()), nullable=False)  # Store epoch timestamp (integer format)
    last_record_count = db.Column(db.Integer, nullable=False)  # Number of records in the last scrape
    last_publication_date = db.Column(db.String(50), nullable=True)  # Latest publication date from the last scrape

    def __repr__(self):
        return f"<ScrapeMetadata {self.city} - Last Scrape Date: {self.last_scrape_date}, Last Scrape Timestamp: {self.last_scrape_timestamp}, Records: {self.last_record_count}>"
