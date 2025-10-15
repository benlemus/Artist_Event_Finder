import os
from flask import Flask, redirect, render_template, request, url_for, session, g, flash
from flask_session import Session
from dotenv import load_dotenv
import redis
import pgeocode
import pygeohash as pgh
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from validators import url as validate_url

from models import db, connect_db, User, Artist, UserArtist, Event, UserEvent, WishList, CreateEvent
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
    generic_events = ticketmaster.get_generic_events()
    all_generic_events = [generic_events[0:5], generic_events[5:10], generic_events[10:15], generic_events[15:]]

    generic_artists = []
    for i in range(5):
        artist = Artist.query.filter_by(id=i+1).first()
        generic_artists.append(artist)

    if not g.user:
        form = LoginForm()
        return render_template('generic-homepage.html', form=form, all_events=all_generic_events)
    
    user = User.query.filter_by(username=g.user.username).first()

    if user:
        zipcode = user.zipcode
        coords = get_lat_long(zipcode)
        geohash = get_geohash(coords)
        generic_events_geohash = ticketmaster.get_generic_events(geohash=geohash)

        if session.get('spotify_token', None):

            artists = user.artists
            wishlist = [event.event_id for event in user.wishlist.all()]
            print(wishlist)

            if artists:
                artist_num = 1
                top_artists = []
                for artist in artists[:5]:
                    top_artists.append({'id': artist_num, 'name': artist.name, 'img': artist.image})
                    artist_num += 1
                return render_template('user-homepage.html', user=user, all_events=all_generic_events, top_artists=top_artists, spot_login=True, generic_events_geohash=generic_events_geohash, wishlist=wishlist)
            
        return render_template('user-homepage.html', user=user, all_events=all_generic_events, generic_artists=generic_artists, generic_events_geohash=generic_events_geohash)
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


@app.route('/add-to-wishlist/<event_id>', methods=['POST'])
def add_to_wishlist(event_id):
    if not g.user:
        return None

    user = User.query.filter_by(username=g.user.username).first()

    existing_event = Event.query.filter_by(event_id=event_id).first()

    if not existing_event:
        event = ticketmaster.get_event(event_id)
        event_to_add = Event(**event)
        db.session.add(event_to_add)
        db.session.commit()

    new_wishlist = WishList(user_id=user.id, event_id=event_id)
    db.session.add(new_wishlist)
    db.session.commit()

    return {'message': 'event added to wishlist'}


@app.route('/remove-wishlist/<event_id>', methods=['POST'])
def remove_from_wishlist(event_id):
    user = User.query.filter_by(username=g.user.username).first()
    item = WishList.query.filter_by(user_id=user.id, event_id=event_id).first()
    db.session.delete(item)
    db.session.commit()

    return {'message': 'event removed from wishlist'}


@app.route('/get-wishlist')
def get_wishlist():
    user = User.query.filter_by(username=g.user.username).first()
    wishlist_events = [event.event_id for event in user.wishlist]

    return wishlist_events if wishlist_events else []

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
    if code:
        info = spotify.callback(code)

        try:
            session['spotify_token'] = info
            access_token = spotify.check_refesh_get_token(token_info=info)
            headers = {'Authorization': f'Bearer {access_token}'}
            top_artists = spotify.get_cur_u_top_artists(headers)

            add_artist_to_db(top_artists)
            return redirect(url_for('homepage'))
        
        except KeyError:
            flash('Error getting Spotify token info', 'danger')
            return redirect(url_for('homepage'))
        
    flash('Error getting Spotify code from callback', 'danger')
    return redirect(url_for('homepage'))


@app.route('/top-artists-events')
def get_top_artists():
    if not g.user:
        return None
    
    if not session['spotify_token']:
        return None

    user = User.query.filter_by(username=g.user.username).first()    

    artists = user.artists
    if not artists:
        return None
    
    user_events = user.events.order_by(Event.date.asc()).limit(16).all()
    ordered_events = []
    top_events = []

    if not user_events:      
        zipcode = user.zipcode
        coords = get_lat_long(zipcode)
        geohash = get_geohash(coords)
        ticketmaster.add_events_to_db(artists=artists, geohash=geohash)

        all_events = Event.get_condensed_events(artists)

        for event in ordered_events:
            new_user_event = UserEvent(user_id=user.id, event_id=event.event_id)
            db.session.add(new_user_event)
            db.session.commit()
    elif user_events:
        all_events = Event.get_condensed_events(artists)

    itteration = 0
    looped = False
    for _ in range(2):
        for event_group in all_events:
            if itteration == len(all_events):
                looped = True
            elif itteration == len(all_events) * 2:
                break

            if looped:
                try:
                    ordered_events.append(event_group[1])
                    itteration += 1
                except IndexError as e:
                    print(f'No index of 2... skipping')
            elif not looped:
                ordered_events.append(event_group[0])
                itteration += 1

    for event in ordered_events:
        setup = {
            'event_id': event.event_id,
            'name': event.name,
            'artist': event.artist,
            'url': event.url,
            'image': event.image,
            'date': event.date.strftime('%B %-d, %Y') if event.date else 'TBA',
            'location': event.location
        }        
        top_events.append(setup)
    
    all_top_events = []
    x = 0
    i = 2

    for _ in range(round(len(top_events)/2)):
        section = top_events[x:i]
        all_top_events.append(section)
        x += 2
        i += 2

    return all_top_events if all_top_events else None


@app.route('/get-authorization')
def get_authorization():
    if g.user:
        login = True
    else:
        login = False
    if session.get('spotify_token', False):
        spotify = True
    else: 
        spotify = False
    return {'login': login, 'spotify': spotify}
    

@app.route('/testing')
def testing():
    return render_template('test.html')


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