import requests
from datetime import datetime
from models import Event, Artist

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
                spot_url = artist.get('spotify_url', None)
                image_url = artist.get('image_url', None)

                attraction_id = self.get_attraction_id(name, spot_url)

                if attraction_id == None:
                    print(f'Could not get artist TM ID for {name}')
                    continue

                setup = {
                    'name': name,
                    'spotify_id': spot_id,
                    'spotify_url': spot_url,
                    'image_url': image_url,
                    'attraction_id': attraction_id
                }
                artists_setup.append(setup)
            return artists_setup 
        return None

    def get_attraction_id(self, name, spotify_url):
        if name:
            res = requests.get(
                f'{self.base_url}/attractions.json',
                params={
                    'keyword': name,
                    'apikey': self.api_key
                }
            )

            data = res.json()

            artists = data.get('_embedded', {}).get('attractions', [{}])

            for artist in artists:
                tm_spot_url = artist.get('externalLinks', {}).get('spotify', [{}])[0].get('url', None)

                if spotify_url == tm_spot_url:
                    return artist.get('id', None)
        return None


    def get_user_events(self, artists, geohash=None):
        if not artists:
            return 'Could not get artists'

        events = []
        seen_events = []
        seen_artists = []
        num_events = 20
        page = 0

        artist_attraction_ids = [artist.attraction_id for artist in artists]

        while len(events) < num_events:

            if len(seen_artists) == 0:
                artist_attraction_ids = [artist.attraction_id for artist in artists]
            else:
                for artist in seen_artists:
                    if artist:
                        cur_a = Artist.query.filter_by(name=artist).first()
                        seen_artists.remove(artist)
                        artist_attraction_ids.remove(cur_a.attraction_id)

            if geohash:
                params = {
                    'attractionId': artist_attraction_ids,
                    'geoPoint': geohash,
                    'sort': 'distance,date,asc',
                    'apikey': self.api_key
                }
            else:
                params = {
                    'attractionId': artist_attraction_ids,
                    'sort': 'relevance,desc',
                    'apikey': self.api_key
                }

            res = requests.get(
                f'{self.base_url}/events.json', params=params)
            
            event_data = res.json().get('_embedded', {}).get('events', [{}])

            for event in event_data:

                if len(events) >= num_events:
                    break

                event_id = event.get('id', None)

                attractions = event.get('_embedded', {}).get('attractions', [{}])

                for attraction in attractions:
                    attraction_name = attraction.get('name', None)
                    if attraction_name in [artist.name for artist in artists]:
                        event_artist = attraction_name

                if not event_id:
                    print('could not get event id')
                    continue

                if not event_artist:
                    print('could not get artist name')
                    continue

                if event_id in seen_events:
                    continue
                
                if event_artist in seen_artists:
                    continue
                
                seen_artists.append(event_artist)
                seen_events.append(event_id)
                new_event = Event(event)
                events.append(new_event.create_event())
            page += 1                

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