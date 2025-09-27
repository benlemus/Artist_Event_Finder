import os
from flask import Flask, redirect, render_template, request, url_for, session, g, flash
from flask_session import Session
from dotenv import load_dotenv
import redis
import pgeocode
import pygeohash as pgh
from sqlalchemy.exc import IntegrityError

from models import db, connect_db, User
from forms import NewUserForm, LoginForm
from ticketmaster import TicketmasterAPI
from spotify import SpotifyAPI

load_dotenv()
app = Flask(__name__)

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

Session(app)
connect_db(app)

CUR_U_ID = 'user id'

SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

TICKETMASTER_API_KEY = os.environ.get('TICKETMASTER_API_KEY')

spotify = SpotifyAPI(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URI)
ticketmaster = TicketmasterAPI(api_key=TICKETMASTER_API_KEY)

@app.before_request
def add_user_to_g():
    if CUR_U_ID in session:
        g.user = User.query.filter_by(id=session[CUR_U_ID]).first()

    else:
        g.user = None

@app.route('/')
def homepage():
    if not g.user:
        form = LoginForm()
        events = ticketmaster.get_generic_events()
        all_events = [events[0:5], events[5:10], events[10:15], events[15:]]
        return render_template('generic-homepage.html', form=form, all_events=all_events)
    
    user = User.query.filter_by(username=g.user.username).first()

    if user:
        if session.get('spotify_token', None):
            access_token = spotify.check_refesh_get_token(token_info=session['spotify_token'])
            headers = {'Authorization': f'Bearer {access_token}'}
            artists = spotify.get_cur_u_top_artists(headers)
            all_artists = [artists[0:5], artists[5:]]
            print(all_artists)
            return render_template('user-homepage.html', user=user, all_artists=all_artists)
        return(render_template('user-homepage.html', user=user))
    return render_template('generic-homepage.html')

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
            do_login(user)
        except IntegrityError:
            flash('Username already taken', 'danger')
            return render_template('signup.html', form=form)

        return  redirect(url_for('homepage'))

    return render_template('signup.html', form=form)

@app.route('/user/details/<username>')
def user_details(username):
    if not g.user:
        flash('You must be logged in to view this page.')
        return redirect(url_for('homepage'))
    
    user = User.query.filter_by(username=username).first()

    return render_template('user-details.html', user=user)

# --------------- SPOTIFY FLASK ROUTES ---------------

@app.route('/logout')
def logout():
    session['spotify_token'] = None
    do_logout()
    return redirect(url_for('homepage'))

@app.route('/connect-spotify')
def login_with_spotify():
    auth_url = spotify.login_with_spotify()
    if auth_url:
        return redirect(auth_url)
    return redirect(url_for('homepage'))

@app.route('/switch-accounts')
def switch_account():
    auth_url = spotify.swtich_account()
    if auth_url:
        return redirect(auth_url)
    return redirect(url_for('homepage'))

@app.route('/artist-event-search')
def artist_search():
    token_info = session['spotify_token']
    access_token = spotify.check_refesh_get_token(token_info=token_info)
    if access_token:
        headers = {'Authorization': f'Bearer {access_token}'}

    top_artists = spotify.get_cur_u_top_artists(headers)
    if top_artists:   
        artists = ticketmaster.set_up_artists(top_artists)
        if artists:
            user = User.query.filter_by(username=g.user.username).first()
            zipcode = user.zipcode
            coords = get_lat_long(zipcode)
            geohash = get_geohash(coords)
            events = ticketmaster.get_events(artists=artists, geohash=geohash)

        # SAVE EVENTS TO DB OR SESSION

    return redirect(url_for('homepage'))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    info = spotify.callback(code)
    session['spotify_token'] = info
    return redirect(url_for('homepage'))


# ==============================================================
        # PYTHON FUNCTIONS
# ==============================================================
def do_login(user):
    session[CUR_U_ID] = user.id

def do_logout():
    if CUR_U_ID in session:
        del session[CUR_U_ID]

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