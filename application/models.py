from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_bcrypt import Bcrypt

import json

bcrypt = Bcrypt()
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text, nullable=False)
    country_code = db.Column(db.Text, nullable=True)
    zipcode = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_img = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now())

    @classmethod 
    def signup(cls, name, username, email, password, country, zipcode, bio, profile_img):

        country_codes = load_country_codes()
        code = country_codes.get(country, 'Code unavailable')
        hashed_pswd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            name=name,
            username=username,
            email=email,
            password=hashed_pswd,
            country=country,
            country_code=code,
            zipcode=zipcode,
            bio=bio,
            profile_img=profile_img
        )
        db.session.add(user)
        return user
    
    @classmethod
    def authenticate(cls, username, password):
        user = cls.query.filter_by(username=username).first()

        if user:
            auth = bcrypt.check_password_hash(user.password, password)
            if auth:
                return user
        return False


def connect_db(app):
    db.app = app
    db.init_app(app)


def load_country_codes(file_path='data/countries.json'):
    with open(file_path, 'r') as file:
        return json.load(file)
