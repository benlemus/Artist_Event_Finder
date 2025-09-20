import os
import requests
from flask import Flask, redirect, render_template, request, url_for, jsonify
from dotenv import load_dotenv
from urllib.parse import urlencode
import base64
import time

load_dotenv()
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

SPOTIFY_BASE_URL = 'https://api.spotify.com/v1'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SCOPE = 'user-read-private user-read-email user-top-read streaming'

SPOTIFY_TOKEN_INFO = None

# ==============================================================
        # FLASK ROUTES
# ==============================================================

@app.route('/')
def homepage():
    global SPOTIFY_TOKEN_INFO

    if SPOTIFY_TOKEN_INFO != None:
        access_token = check_refesh_get_token_spotify()

        headers = {'Authorization': f'Bearer {access_token}'}

        user = get_cur_u_spotify(headers)
        artists = get_cur_u_top_artists(headers)
        return render_template('homepage.html', user=user, artists=artists)
    return render_template('homepage.html')

@app.route('/login')
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


@app.route('/logout')
def logout():
    global SPOTIFY_TOKEN_INFO
    SPOTIFY_TOKEN_INFO = None
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
        # PYTHON CODE
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
    params = {
        'limit': 5,
        'time_range': 'long_term'
    }

    top_artists = requests.get(f'{SPOTIFY_BASE_URL}/me/top/artists?{urlencode(params)}', headers=headers)
    users_top = top_artists.json()

    artist_names = []
    for artist in users_top.get('items', None):
        artist_names.append(artist.get('name', None))

    return artist_names

