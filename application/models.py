from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_bcrypt import Bcrypt

import json

bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text, nullable=False)
    country_code = db.Column(db.Text, nullable=True)
    zipcode = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_img = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    artists = db.relationship('Artist', secondary='users_artists', backref='users', lazy='dynamic')


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
    

    @classmethod
    def update_details(cls, user_id, name, username, email, country, zipcode, bio):
        country_codes = load_country_codes()
        code = country_codes.get(country, 'Code unavailable')

        user = cls.query.filter_by(id=user_id).first()

        if user:
            user.name = name
            user.username = username
            user.email = email
            user.country = country
            user.country_code = code
            user.zipcode = zipcode
            user.bio = bio       
            return user
        return False

    
    @classmethod
    def change_password(cls, username, password):
        user = cls.query.filter_by(username=username).first()

        if user:
            user.password = bcrypt.generate_password_hash(password).decode('UTF-8')
            return user
        return False
    

    @classmethod
    def update_pfp(cls, username, profile_img):
        user = cls.query.filter_by(username=username).first()

        if user:
            user.profile_img = profile_img
            return user
        return False
    

class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    spotify_id = db.Column(db.Text, nullable=False, unique=True)
    spotify_url = db.Column(db.Text, nullable=False, unique=True)
    image = db.Column(db.Text, nullable=True)
    attraction_id = db.Column(db.Text, nullable=False, unique=True)


    def get_by_order(self):
        pass


class UserArtist(db.Model):
    __tablename__ = 'users_artists'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)

    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id', ondelete='CASCADE'), primary_key=True)


class Event():
    def __init__(self, event):
        self.event = event
    

    def create_event(self):
        artist = self.event.get('_embedded', {}).get('attractions', [{}])[0].get('name', None)
        name = self.event.get('name', 'could not get artist name')
        event_id = self.event.get('id', 'could not get event info')
        url = self.event.get('url', 'could not get event url')
        images = self.event.get('images', [{}])
        date = self.event.get('dates', {}).get('start', {}).get('dateTime', None)
        locations = self.event.get('_embedded', {}).get('venues', [{}])[0]
        city = locations.get('city', {}).get('name', None)
        state = locations.get('state', {}).get('name', None)

        if date:
            formated_date = datetime.fromisoformat(date[:-1] + '+00:00').strftime('%B %d %Y')
        else:
            formated_date = 'TBA'

        if not city and not state:
            location = 'TBA'
        elif not city:
            location = state
        elif not state:
            location = city
        elif city and state:
            location = f'{city}, {state}'
            
        cur_biggest = 0
        for image in images:
            if int(image.get('width', 0)) >= cur_biggest:
                cur_biggest = int(image.get('width', 0))
                image_url = image.get('url', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwoFiJiFNFd9HI4Ez177ayXT1aDEejtgyMJA&s')
            else:
                continue

        return {
            'artist': artist,
            'name': name,
            'event_id': event_id,
            'url': url,
            'image': image_url,
            'date': formated_date,
            'location': location
        }


def connect_db(app):
    db.app = app
    db.init_app(app)


def load_country_codes(file_path='data/countries.json'):
    with open(file_path, 'r') as file:
        return json.load(file)

