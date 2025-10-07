import os
from flask import Flask, redirect, render_template, request, url_for, session, g, flash
from flask_session import Session
from dotenv import load_dotenv
import redis
import pgeocode
import pygeohash as pgh
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from validators import url as validate_url

from models import db, connect_db, User, Artist, UserArtist
from forms import NewUserForm, LoginForm, EditUserForm, ChangePasswordForm, ChangePfpForm
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
    events = ticketmaster.get_generic_events()
    all_generic_events = [events[0:5], events[5:10], events[10:15], events[15:]]

    if not g.user:
        form = LoginForm()
        return render_template('generic-homepage.html', form=form, all_events=all_generic_events)
    
    user = User.query.filter_by(username=g.user.username).first()

    if user:
        if session.get('spotify_token', None):

            artists = user.artists

            if artists:
                artist_num = 1
                top_artists = []
                for artist in artists[:5]:
                    top_artists.append({'id': artist_num, 'name': artist.name, 'img': artist.image})
                    artist_num += 1
                
                # zipcode = user.zipcode
                # coords = get_lat_long(zipcode)
                # geohash = get_geohash(coords)
                # top_events = ticketmaster.get_user_events(artists=artists, geohash=geohash)

                # all_top_events = [top_events[:5], top_events[5:10], top_events[10:15], top_events[15:]]

                    # all_top_events=all_top_events
                return render_template('user-homepage.html', user=user, all_events=all_generic_events, top_artists=top_artists, spot_login=True)
            
        return render_template('user-homepage.html', user=user, all_events=all_generic_events)
    return render_template('generic-homepage.html', all_events=all_generic_events)

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
    return redirect(url_for('homepage'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = NewUserForm()

    if form.validate_on_submit():
        try:
            data = {field: form[field].data for field in form._fields if field != 
            'csrf_token'}
            if not validate_url(data['profile_img']):
                data['profile_img'] = 'https://cdn-icons-png.freepik.com/512/5997/5997002.png'

            user = User.signup(**data)
            db.session.commit()
            do_login(user)
        except IntegrityError:
            flash('Username or email already in use.', 'danger')
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

@app.route('/user/details/edit/<username>', methods=['GET', 'POST'])
def edit_user(username):
    u = User.query.filter_by(username=username).first()

    form = EditUserForm(obj=u)

    if form.validate_on_submit():
        try:
            data = {field: form[field].data for field in form._fields if field != 'csrf_token'}
            user_id = u.id
            update = User.update_details(user_id, **data)
            db.session.commit()
            
        except PendingRollbackError:
            db.session.rollback()
            flash('An error occured', 'danger')
            return render_template('user-edit.html', form=form, u=u)
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig).lower()
            if 'username' in error_message and 'unique' in error_message:
                flash('Username already in use.', 'danger')
            elif 'email' in error_message and 'unique' in error_message:
                flash('Email already in use.', 'danger')
            return render_template('user-edit.html', form=form, u=u)

    return render_template('user-edit.html', form=form, u=u)

@app.route('/user/password/edit/<username>', methods=['GET', 'POST'])
def change_password(username):
    u = User.query.filter_by(username=username).first()
    
    form = ChangePasswordForm()

    if form.validate_on_submit():
        auth = User.authenticate(u.username, form.password.data)

        if auth:
            update = User.update_password(u.username, form.new_password.data)
            db.session.commit()

            if update:
                flash('Password updated!', 'success')
                return redirect(f'/user/details/{u.username}')
            
        flash('Could not update password', 'danger')
        return redirect(f'/user/details/{u.username}')
    
    return render_template('user-password-edit.html', form=form, u=u)

@app.route('/user/edit-pfp/<username>', methods=['GET', 'POST'])
def change_pfp(username):
    u = User.query.filter_by(username=username).first()

    form = ChangePfpForm()

    if form.validate_on_submit():
        profile_img = form.profile_img.data
        if not validate_url(profile_img):
            profile_img = 'https://cdn-icons-png.freepik.com/512/5997/5997002.png'
        update = User.update_pfp(u.username, profile_img)
        db.session.commit()

        if update:
            flash('Profile Picture Updated!', 'success')
            return redirect(f'/user/details/{u.username}')
        
        flash('could not update profile picture', 'danger')
        return redirect(f'/user/edit-pfp/{u.username}')
    
    return render_template('user-pfp-edit.html', form=form, u=u)

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

@app.route('/callback')
def callback():
    code = request.args.get('code')
    info = spotify.callback(code)
    session['spotify_token'] = info

    access_token = spotify.check_refesh_get_token(token_info=info)
    headers = {'Authorization': f'Bearer {access_token}'}
    top_artists = spotify.get_cur_u_top_artists(headers)

    add_artist_to_db(top_artists)

    return redirect(url_for('homepage'))





@app.route('/top-artists-events')
def get_top_artists():
    if not g.user:
        return None
    
    user = User.query.filter_by(username=g.user.username).first()

    artists = user.artists
    if not artists:
        return None
    
    zipcode = user.zipcode
    coords = get_lat_long(zipcode)
    geohash = get_geohash(coords)
    top_events = ticketmaster.get_user_events(artists=artists, geohash=geohash)

    all_top_events = [top_events[:5], top_events[5:10], top_events[10:15], top_events[15:]]

    return all_top_events


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

def add_artist_to_db(top_artists):
    u = User.query.filter_by(username=g.user.username).first()

    if u.artists:
        UserArtist.query.filter_by(user_id=u.id).delete()
        
    artists = ticketmaster.set_up_artists(top_artists)

    for artist in artists:
        spotify_id = artist.get('spotify_id', None)

        if spotify_id:
            new_artist = Artist.query.filter_by(spotify_id=spotify_id).first()

            if not new_artist:
                new_artist = Artist(
                    name=artist.get('name', 'could not get name'),
                    spotify_id=artist.get('spotify_id', 'could not get Spotify id'),
                    spotify_url=artist.get('spotify_url', 'could not get spotify url'),
                    image=artist.get('image_url', 'could not get image'),
                    attraction_id=artist.get('attraction_id', 'could not get attraction id')
                    )
                
                db.session.add(new_artist)
                db.session.commit()
          
            new_user_artist = UserArtist(user_id=u.id, artist_id=new_artist.id)

            db.session.add(new_user_artist)
            db.session.commit()
            
            