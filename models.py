from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Obituary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    obituary_url = db.Column(db.String(500), unique=True, nullable=False)
    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    death_date = db.Column(db.Date)
    family_information = db.Column(db.Text)
    donation_information = db.Column(db.Text)
    funeral_home = db.Column(db.String(255))
    is_alumni = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text)

    def __repr__(self):
        return f"<Obituary {self.name} - {self.city}, {self.province}>"
