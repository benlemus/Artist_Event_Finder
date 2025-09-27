import requests
from datetime import datetime

class TicketmasterAPI:
    def __init__(self, api_key, base_url="https://app.ticketmaster.com/discovery/v2"):
        self.api_key = api_key
        self.base_url = base_url
    
    def set_up_artists(self, artists):
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
                        genre_id = self.get_genre_id(genre)
                        genre_ids.append(genre_id)

                attraction_id = self.get_attraction_id(name, genre_ids)

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

    def get_genre_id(self, genre):
        res = requests.get(
            f'{self.base_url}/classifications.json',
            params={
                'keyword': genre,
                'apiKey': self.api_key
            }
        )

        genre_id = res.json().get('_embedded', None).get('classifications', [{}])[0].get('segment', None).get('_embedded', None).get('genres', [{}])[0].get('id', None)

        if not genre_id:
            return None
        
        return genre_id


    def get_attraction_id(self, name, genres):
        if name:
            if len(genres) != 0:
                res = requests.get(
                    f'{self.base_url}/attractions.json',
                    params={
                        'keyword': name,
                        'genreId': genres,
                        'apikey': self.api_key
                    }
                )

                if res.status_code == 200:
                    return res.json().get('_embedded', None).get('attractions', [{}])[0].get('id', None)

            res = requests.get(
                f'{self.base_url}/attractions.json',
                params={
                    'keyword': name,
                    'apikey': self.api_key
                }
            )

            return res.json().get('_embedded', None).get('attractions', [{}])[0].get('id', None)
        return None

    def get_events(self, artists, geohash):
        # coords = get_lat_long(93035)
        # geo_point = get_geohash(coords)
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
                f'{self.base_url}/events.json',
                params={
                    'attractionId': attraction_id,
                    'size': 1,
                    'geoPoint': geohash,
                    'sort': 'distance,date,asc',
                    'apikey': self.api_key
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
        
    def get_generic_events(self):
        events = []

        seen_artists = []
        num_events = 20
        page = 0

        while len(events) < num_events:
            res = requests.get(
                f'{self.base_url}/events.json',
                params={
                    'classificationName': 'music',
                    'sort': 'relevance,desc',
                    'page': page,
                    'apikey': self.api_key
                }
            )

            data = res.json().get('_embedded', {}).get('events', [{}])

            for event in data:
                if len(events) >= num_events:
                    break
                
                artist = event.get('_embedded', {}).get('attractions', [{}])[0].get('name')

                if artist in seen_artists:
                    continue
                name = event.get('name', 'could not get name')
                event_id = event.get('id', 'could not get event id')
                url = event.get('url', 'could not get event url')
                image = event.get('images', [{}])[0].get('url', 'could not get image')
                date = event.get('dates', {}).get('start', {}).get('dateTime', None)
                locations = event.get('_embedded', {}).get('venues', [{}])[0]
                location = f"{locations.get('city', {}).get('name', 'could not get city name')}, {locations.get('state', {}).get('name', 'could not get state name')}"

                if date:
                    formated_date = datetime.fromisoformat(date[:-1] + '+00:00').strftime('%B %d %Y')
                else:
                    formated_date = 'Could not get date'
                e_setup = {
                    'name': name,
                    'event_id': event_id,
                    'url': url,
                    'image': image,
                    'date': formated_date,
                    'location': location
                }

                seen_artists.append(artist)
                events.append(e_setup)
            page += 1 
        return events