from models import User, Artist, UserArtist
from app import db, app

with app.app_context():

    db.drop_all()
    db.create_all()

    u1 = User.signup(
        name='Milo',
        username='RunningPuppy',
        email='ruff@bark.com',
        password='TestPassword',
        country='Brazil',
        zipcode='90001',
        bio='I am a dog.',
        profile_img='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ0uth7LMdNHQanxMZ5qq7-7AFFIW63VI-B4A&s'
    )

    u2 = User.signup(
        name='Marvin',
        username='meowmeow5',
        email='meow@fish.com',
        password='testpassword',
        country='United States of America',
        zipcode='90002',
        bio='Im really good at sleeping',
        profile_img='https://cdn.shopify.com/s/files/1/0765/3946/1913/files/1_be68b38a-8738-4c2e-b418-592186164ab1.jpg?v=1740656934'
    )

    u3 = User.signup(
        name='Mojo',
        username='MouseHunter1',
        email='notacat@exterminator.com',
        password='testpassword1',
        country='New Zealand',
        zipcode='90003',
        bio='Call me if you have rats, I can take care of them.',
        profile_img='https://www.terminix.com/-/media/Feature/Terminix/Articles/cats-get-rid-of-mice.jpg?rev=499bc54abdfa40a08e3452c7ad1bb8d2'
    )

    u4 = User.signup(
        name='Miles',
        username='AnkleBiter',
        email='runner@energy.com',
        password='TESTPASSWORD1#',
        country='Costa Rica',
        zipcode='90004',
        bio='I see horse, I chase horse.... Horse sees me. I run.',
        profile_img='https://i.pinimg.com/736x/7c/72/7e/7c727ec2c3ce40b5ef8f424f010778a1.jpg'
    )

    db.session.commit()


        # used to limit bio and profile_img length while viewsing in terminal
# CREATE VIEW users_truncated AS
# SELECT
#     name,
#     username,
#     email,
#     SUBSTRING(password FROM 1 FOR 5) AS password,
#     SUBSTRING(country FROM 1 FOR 10) AS country,
#     zipcode,
#     SUBSTRING(bio FROM 1 FOR 15) AS bio,
#     SUBSTRING(profile_img FROM 1 FOR 20) AS profile_img,
#     created_at
# FROM users;

# CREATE VIEW artists_truncated AS
# SELECT
#     id,
#     name,
#     spotify_id,
#     SUBSTRING(spotify_url FROM 1 FOR 10) AS spotify_url,
#     SUBSTRING(image FROM 1 FOR 10) AS image,
#     attraction_id
# FROM artists;

# CREATE VIEW events_truncated AS
# SELECT
#     event_id,
#     name,
#     artist,
#     SUBSTRING(url FROM 1 FOR 10) AS url,
#     SUBSTRING(image FROM 1 FOR 10) AS image,
#     date,
#     location
# FROM events;