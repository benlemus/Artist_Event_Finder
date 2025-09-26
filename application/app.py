import os
import requests
from flask import Flask, redirect, render_template, request, url_for, session, g, flash
from dotenv import load_dotenv
from urllib.parse import urlencode
import base64
import time
import pgeocode
import pygeohash as pgh
from sqlalchemy.exc import IntegrityError

from models import db, connect_db, User
from forms import NewUserForm, LoginForm

load_dotenv()
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)

CUR_U_ID = 'user id'

SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

SPOTIFY_BASE_URL = 'https://api.spotify.com/v1'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SCOPE = 'user-read-private user-read-email user-top-read streaming'

SPOTIFY_TOKEN_INFO = None

TICKETMASTER_API_KEY = os.environ.get('TICKETMASTER_API_KEY')
TICKETMASTER_BASE_URL = 'https://app.ticketmaster.com/discovery/v2/'


# ==============================================================
        # FLASK ROUTES
# ==============================================================

@app.before_request
def add_user_to_g():
    if CUR_U_ID in session:
        g.user = User.query.filter_by(id=session[CUR_U_ID]).first()

    else:
        g.user = None

@app.route('/')
def homepage():
    global SPOTIFY_TOKEN_INFO

    if not g.user:
        return render_template('homepage.html')
    
    user = User.query.filter_by(username=g.user.username).first()

    if user:
        if SPOTIFY_TOKEN_INFO != None:
            access_token = check_refesh_get_token_spotify()

            headers = {'Authorization': f'Bearer {access_token}'}
            artists = get_cur_u_top_artists(headers)
            artists_1 = artists[0:5]
            artists_2 = artists[5:]
            
            return render_template('user-homepage.html', user=user, artists_1=artists_1, artists_2=artists_2)
        return(render_template('user-homepage.html', user=user))
    return render_template('generic-homepage.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        auth = User.authenticate(form.username.data, form.password.data)

        if auth:
            do_login(auth)
            flash(f'Welcome, {auth.username}', 'success')
            return redirect(url_for('homepage'))
        
        flash('Invalid username/password', 'danger')
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = NewUserForm()

    if form.validate_on_submit():
        try:
            data = {field: form[field].data for field in form._fields if field != 'csrf_token'}
            user = User.signup(**data)
            db.session.commit()
        except IntegrityError:
            flash('Username already taken', 'danger')
            return render_template('signup.html', form=form)

        return  redirect(url_for('homepage'))

    return render_template('signup.html', form=form)


# --------------- SPOTIFY FLASK ROUTES ---------------

@app.route('/logout')
def logout():
    global SPOTIFY_TOKEN_INFO
    SPOTIFY_TOKEN_INFO = None
    do_logout()
    return redirect(url_for('homepage'))

@app.route('/connect-spotify')
def login_with_spotify():
    global SPOTIFY_TOKEN_INFO
    if SPOTIFY_TOKEN_INFO == None:
        params = {
            'client_id': SPOTIFY_CLIENT_ID,
            'scope': SCOPE,
            'response_type': 'code',
            'redirect_uri': SPOTIFY_REDIRECT_URI,
        }
        auth_url = f'{SPOTIFY_AUTH_URL}?{urlencode(params)}'
        return redirect(auth_url)
    return redirect(url_for('homepage'))

@app.route('/switch-accounts')
def switch_account():
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'scope': SCOPE,
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'show_dialog': True
    }
    auth_url = f'{SPOTIFY_AUTH_URL}?{urlencode(params)}'
    return redirect(auth_url)

@app.route('/artist-search')
def artist_search():
    access_token = check_refesh_get_token_spotify()
    headers = {'Authorization': f'Bearer {access_token}'}

    top_artists = get_cur_u_top_artists(headers)   
    artists = set_up_artists_TM(top_artists)
    events = get_events_TM(artists)

    return redirect(url_for('homepage'))

@app.route('/callback')
def callback():
    global SPOTIFY_TOKEN_INFO
    code = request.args.get('code')

    if code:
        token_info = get_token_spotify(code)
        if token_info:
            token_info['expires_at'] = int(time.time() + token_info['expires_in'])
            SPOTIFY_TOKEN_INFO = token_info
            return redirect(url_for('homepage'))
        return 'No token'
    return 'No code'

# ==============================================================
        # PYTHON FUNCTIONS
# ==============================================================
def do_login(user):
    session[CUR_U_ID] = user.id

def do_logout():
    if CUR_U_ID in session:
        del session[CUR_U_ID]



# ==============================================================
        # SPOTIFY PYTHON FUNCTIONS
# ==============================================================


def auth_token_header_spotify():
    auth_str = f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'
    auth_bytes = auth_str.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    return {'Authorization': f'Basic {auth_base64}'}

def get_token_spotify(code):
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI
    }

    headers = auth_token_header_spotify()

    res = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)

    return res.json()

def refresh_token_spotify(refresh_token):
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    headers = auth_token_header_spotify()

    res = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)

    return res.json()    


def check_refesh_get_token_spotify():
    global SPOTIFY_TOKEN_INFO
    info = SPOTIFY_TOKEN_INFO

    if info:
        if info['expires_at'] < int(time.time()):
            info = refresh_token_spotify(info['refresh_token'])
            if info:
                info['expires_at'] = int(time.time() + info['expires_in'])
                SPOTIFY_TOKEN_INFO = info
            return 'no info'
    return info['access_token']

def get_cur_u_spotify(headers):
    res = requests.get(f'{SPOTIFY_BASE_URL}/me', headers=headers)
    return res.json()

def get_cur_u_top_artists(headers):
    top_artists = requests.get(
        f'{SPOTIFY_BASE_URL}/me/top/artists',
        params={
            'limit': 10,
            'time_range': 'long_term'
        },
        headers=headers
    )

    users_top = top_artists.json()

    artists_setup = []
    for artist in users_top.get('items', None):

        setup = {
            'name': artist.get('name', None),
            'spotify_id': artist.get('id'),
            'spotify_genres': artist.get('genres'),
            'image_url': artist.get('images')[0].get('url')
        }
        artists_setup.append(setup)

    return artists_setup


# ==============================================================
        # TICKETMASTER PYTHON FUNCTIONS
# ==============================================================

def set_up_artists_TM(artists):
    if artists:
        artists_setup = []
        for artist in artists:
            name = artist.get('name', None)
            spot_id = artist.get('spotify_id', None)
            spot_genres = artist.get('spotify_genres', [])
            image_url = artist.get('image_url', None)
            genre_ids = []

            if not spot_genres:
                for genre in spot_genres:
                    genre_id = get_genre_id_TM(genre)
                    genre_ids.append(genre_id)

            attraction_id = get_attraction_id_TM(name, genre_ids)

            if attraction_id == None:
                return 'Could not get artist TM ID'
            setup = {
                'name': name,
                'spotify_id': spot_id,
                'spotify_genres': spot_genres,
                'image_url': image_url,
                'genre_ids': genre_ids,
                'attraction_id': attraction_id
            }
            artists_setup.append(setup)
        return artists_setup 
    return None

def get_genre_id_TM(genre):

    res = requests.get(
        f'{TICKETMASTER_BASE_URL}/classifications.json',
        params={
            'keyword': genre,
            'apiKey': TICKETMASTER_API_KEY
        }
    )

    genre_id = res.json().get('_embedded', None).get('classifications', [{}])[0].get('segment', None).get('_embedded', None).get('genres', [{}])[0].get('id', None)

    if not genre_id:
        return None
    
    return genre_id


def get_attraction_id_TM(name, genres):
    if name:
        if len(genres) != 0:
            res = requests.get(
                f'{TICKETMASTER_BASE_URL}/attractions.json',
                params={
                    'keyword': name,
                    'genreId': genres,
                    'apikey': TICKETMASTER_API_KEY
                }
            )

            if res.status_code == 200:
                return res.json().get('_embedded', None).get('attractions', [{}])[0].get('id', None)

        res = requests.get(
            f'{TICKETMASTER_BASE_URL}/attractions.json',
            params={
                'keyword': name,
                'apikey': TICKETMASTER_API_KEY
            }
        )

        return res.json().get('_embedded', None).get('attractions', [{}])[0].get('id', None)
    return None

def get_events_TM(artists):
    coords = get_lat_long(93035)
    geo_point = get_geohash(coords)

    if not artists:
        return 'Could not get artists'

    events = []
    for artist in artists:

        attraction_id = artist.get('attraction_id')
        artist_name = artist.get('name', None)

        if not attraction_id:
            print(f'No attraction ID for {artist_name}')
            continue  

        res = requests.get(
            f'{TICKETMASTER_BASE_URL}/events.json',
            params={
                'attractionId': attraction_id,
                'size': 1,
                'geoPoint': geo_point,
                'sort': 'distance,date,asc',
                'apikey': TICKETMASTER_API_KEY
            }
        )

        elems = res.json().get('page', {}).get('totalElements', 0)

        if elems == 0:
            print(f'No events found for {artist_name}')
            continue
        event_data = res.json().get('_embedded', {}).get('events', [])
        venues = event_data[0].get('_embedded', {}).get('venues',[])
        test_venue = venues[0].get('name', None)
        print(artist_name, test_venue)

    return events if events else None    
    



# ADD ARTIST TO DB USING ARTIST NAME, SPOT ID AND ATTRACTION ID

# ==============================================================
        # GEO/LOCATION PYTHON FUNCTIONS
# ==============================================================

def get_lat_long(zipcode):
    user = {
        'country_code': 'US',
        'postal_code': zipcode
    }

    nomi = pgeocode.Nominatim(user.get('country_code', 'US'))
    data = nomi.query_postal_code(user.get('postal_code', '90001'))

    lat = data.get('latitude', None)
    long = data.get('longitude', None)

    return (lat, long)

def get_geohash(coords):
    lat, long = coords
    geohash = pgh.encode(latitude=lat, longitude=long, precision=9)

    return geohash