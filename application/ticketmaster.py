import requests
from datetime import datetime
from models import CreateEvent, Artist, Event, UserEvent
from app import db


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


                # else:
                #     params = {
                #         'attractionId': artist_attraction_ids,
                #         'geoPoint': geohash,
                #         'radius': '500',
                #         'unit': 'miles',
                #         'page': page,
                #         'sort': 'distance,date,asc',
                #         'apikey': self.api_key
                #     }


    def add_events_to_db(self, artists, geohash=None):
        for artist in artists:
            events_added = 0
            seen_events= []

            if not artist:
                break

            if geohash:
                params = {
                    'attractionId': artist.attraction_id,
                    'geoPoint': geohash,
                    'sort': 'distance,date,asc',
                    'apikey': self.api_key
                }
            else:
                params = {
                    'attractionId': artist.attraction_id,
                    'sort': 'relevance,desc',
                    'apikey': self.api_key
                }

            try:
                res = requests.get(f'{self.base_url}/events.json', params=params)
                response_json = res.json()
                event_data = response_json.get('_embedded', {}).get('events', [])

                if not event_data:
                    continue
            
                for event in event_data:
                    if events_added >= 2:
                        break
                    
                    event_id = event.get('id', None)

                    if event_id in seen_events:
                        continue

                    created_event = CreateEvent(event)
                    new_event = created_event.create_event()

                    existing_event = Event.query.filter_by(event_id=new_event['event_id']).first()

                    if not existing_event:
                        event_to_add = Event(**new_event)
                        db.session.add(event_to_add)
                        db.session.commit()

            except Exception as e:
                print(f'error making request: {e}')
                break


    def get_generic_events(self, geohash=None):
        events = []
        seen_artists = []
        num_events = 20
        page = 0

        while len(events) < num_events:

            if geohash:
                params = {
                    'classificationName': 'music',
                    'geoPoint': geohash,
                    'radius': '50',
                    'unit': 'miles',
                    'page': page,
                    'sort': 'relevance,desc',
                    'apikey': self.api_key
                }
            else:
                params={
                    'classificationName': 'music',
                    'sort': 'relevance,desc',
                    'page': page,
                    'apikey': self.api_key
                }

            res = requests.get(
                f'{self.base_url}/events.json', params=params)
            
            event_data = res.json().get('_embedded', {}).get('events', [{}])

            for event in event_data:
                if len(events) >= num_events:
                    break

                artist = event.get('_embedded', {}).get('attractions', [{}])[0].get('name', event.get('name'))

                if artist in seen_artists:
                    continue
                
                seen_artists.append(artist)
                new_event = CreateEvent(event)
                events.append(new_event.create_event())
            page += 1                

        return events if events else None
    
    def get_event(self, event_id):
        if event_id:
            res = requests.get(
                f'{self.base_url}/events',
                params={
                    'id': event_id,
                    'apikey': self.api_key
                }
            )

            event_data = res.json().get('_embedded', {}).get('events', [{}])[0]

            if event_data:
                new_event = CreateEvent(event_data)
                event = new_event.create_event()

                return event

