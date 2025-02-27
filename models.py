from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Obituary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    birth_date = db.Column(db.String(50), nullable=True)
    death_date = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(255), nullable=True)  # New field for city
    province = db.Column(db.String(255), nullable=True)  # New field for province
    obituary_url = db.Column(db.String(255), unique=True, nullable=False)
    family_information = db.Column(db.Text, nullable=True)
    donation_information = db.Column(db.Text, nullable=True)
    is_alumni = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Obituary {self.name} - {self.city}, {self.province}>"
