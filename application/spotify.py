import base64
import time
import requests
from urllib.parse import urlencode

class SpotifyAPI:
    def __init__(self, client_id, client_secret, redirect_uri, base_url="https://api.spotify.com/v1", token_url='https://accounts.spotify.com/api/token', auth_url='https://accounts.spotify.com/authorize', scope='user-read-private user-read-email user-top-read streaming'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = base_url
        self.token_url = token_url
        self.auth_url = auth_url
        self.scope = scope

# TOKENS/ GENERIC SPOTIFY API

    def auth_token_header(self):
        auth_str = f'{self.client_id}:{self.client_secret}'
        auth_bytes = auth_str.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        return {'Authorization': f'Basic {auth_base64}'}

    def get_token(self, code):
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        headers = self.auth_token_header()

        res = requests.post(self.token_url, data=payload, headers=headers)

        return res.json()

    def refresh_token(self, refresh_token):
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        headers = self.auth_token_header()

        res = requests.post(self.token_url, data=payload, headers=headers)

        return res.json()    


    def check_refesh_get_token(self, token_info=None):
        info = token_info

        if info:
            if info['expires_at'] < int(time.time()):
                info = self.refresh_token(info['refresh_token'])
                if info:
                    info['expires_at'] = int(time.time() + info['expires_in'])
                return None
        return info['access_token']
    
    def callback(self, code):
        if code:
            token_info = self.get_token(code)
            if token_info:
                token_info['expires_at'] = int(time.time() + token_info['expires_in'])
                return token_info
            return None
        return None
    
# FUNCTIONS

    def swtich_account(self):
        params = {
            'client_id': self.client_id,
            'scope': self.scope,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'show_dialog': True
        }
        return f'{self.auth_url}?{urlencode(params)}'

    def login_with_spotify(self, token_info=None):
        if token_info == None:
            params = {
                'client_id': self.client_id,
                'scope': self.scope,
                'response_type': 'code',
                'redirect_uri': self.redirect_uri,
            }

            return f'{self.auth_url}?{urlencode(params)}'

    def get_cur_u(self, headers):
        res = requests.get(f'{self.base_url}/me', headers=headers)
        return res.json()

    def get_cur_u_top_artists(self, headers):
        top_artists = requests.get(
            f'{self.base_url}/me/top/artists',
            params={
                'limit': 10,
                'time_range': 'long_term'
            },
            headers=headers
        )

        users_top = top_artists.json()

        artists_setup = []
        
        for artist in users_top.get('items', {}): 
            setup = {
                'name': artist.get('name', None),
                'spotify_id': artist.get('id'),
                'spotify_url': artist.get('external_urls', {}).get('spotify', None),
                'image_url': artist.get('images')[0].get('url')
            }
            artists_setup.append(setup)     

        return artists_setup
