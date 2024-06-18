from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
import requests
from bs4 import BeautifulSoup as bs
import re
from django.conf import settings

rapidapi_key = settings.RAPIDAPI_KEY
rapidapi_host = settings.RAPIDAPI_HOST 

# Create your views here.
def top_artists():

    url = "https://spotify-scraper.p.rapidapi.com/v1/chart/artists/top"

    querystring = {"type":"weekly"}

    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)
    response_data = response.json()
    artists_info = []

    if 'artists' in response_data:
        for artist in response_data['artists']:
            name = artist.get('name', 'No Name')
            artist_id = artist.get('id', 'No ID')
            avatar_url = artist.get('visuals', {}).get('avatar', [{}])[0].get('url', 'No URL')
            artists_info.append((name, avatar_url, artist_id))

    return artists_info

def top_songs():
    url = "https://spotify-scraper.p.rapidapi.com/v1/chart/tracks/top"

    querystring = {"type":"weekly"}

    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)

    data = response.json()
    track_details = []

    if 'tracks' in data:
        shortened_data = data['tracks'][:25]

        for track in shortened_data:
            track_id = track['id']
            track_name = track['name']
            track_artist_name = track['artists'][0]['name'] if track['artists'] else None
            cover_url = track['album']['cover'][0]['url'] if track['album']['cover'] else None

            track_details.append({
                'id': track_id,
                'track_name': track_name,
                'artist_name': track_artist_name,
                'cover_url': cover_url,
            })
    else:
        print("Track not found in response")
    
    return track_details

def get_audio_details(query):
    url = "https://spotify-scraper.p.rapidapi.com/v1/track/download"

    querystring = {"track": query}

    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)

    audio_details = []

    if response.status_code == 200:
        response_data = response.json()

        if 'youtubeVideo' in response_data and 'audio' in response_data['youtubeVideo']:
            audio_list = response_data['youtubeVideo']['audio']
            if audio_list:
                first_audio_url = audio_list[0]['url']
                duration_text = audio_list[0]['durationText']

                audio_details.append(first_audio_url)
                audio_details.append(duration_text)
                
            else:
                print("No audio data available")
        else:
            print("No 'youtubeVideo' or 'audio' key found")
    else:
        print("Failed to fetch data")
    
    return audio_details
        
def get_track_image(track_id, track_name):

    url = f"https://open.spotify.com/track/{track_id}"
    r = requests.get(url)
    soup = bs(r.content, 'html.parser')
    image_tag = soup.find('img', {'alt': track_name})

    if image_tag:
        image_srcset = image_tag.get('srcset', '')
        # Parse all image URLs and their sizes
        images = re.findall(r'(https:\/\/i\.scdn\.co\/image\/[a-zA-Z0-9]+) (\d+)w', image_srcset)
        if images:
            # Convert sizes to integers and find the closest to the target width
            images = [(url, int(size)) for url, size in images]
            closest_image = min(images, key=lambda x: abs(x[1] - 250))
            url_closest = closest_image[0]
        else:
            url_closest = 'No Image URL'
    else:
        url_closest = 'No Image Tag Found'

    return url_closest

def music(request, pk):

    track_id = pk

    url = "https://spotify-scraper.p.rapidapi.com/v1/track/metadata"

    querystring = {"trackId": track_id}

    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        data = response.json()
        track_name = data.get("name")
        artists_list = data.get("artists", [])
        first_artist_name = artists_list[0].get("name") if artists_list else "No artist found"
        track_image = get_track_image(track_id, track_name)
        audio_details_query = track_name + first_artist_name
        audio_details = get_audio_details(audio_details_query)
        audio_url = audio_details[0]
        duration_text = audio_details[1]

        context = {
            'track_name': track_name,
            'artist_name': first_artist_name,
            'track_image': track_image,
            'audio_url': audio_url,
            'duration_text': duration_text,
        }

    return render(request, 'music.html', context)



@login_required(login_url='login')
def index(request):
    artists_info = top_artists()
    top_track_list = top_songs()

    #divde top songs into 5 lists to be looped in index.html
    first_five_tracks = top_track_list[:5]
    second_five_tracks = top_track_list[5:10]
    third_five_tracks = top_track_list[10:15]
    fourth_five_tracks = top_track_list[15:20]
    fifth_five_tracks = top_track_list[20:25]

    context = {
        'artists_info': artists_info,
        'first_five_tracks': first_five_tracks,
        'second_five_tracks': second_five_tracks,
        'third_five_tracks': third_five_tracks,
        'fourth_five_tracks': fourth_five_tracks,
        'fifth_five_tracks': fifth_five_tracks
    }
    return render(request, 'index.html', context)

def search(request):
    if request.method == "POST":
        search_query = request.POST['search_query']
        url = "https://spotify-scraper.p.rapidapi.com/v1/search"

        querystring = {"term":search_query, "type": "track"}

        headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
        }

        response = requests.get(url, headers=headers, params=querystring)

        track_list = []

        if response.status_code == 200:
            data = response.json()

            search_results_count = data["tracks"]["totalCount"]
            tracks = data["tracks"]["items"]

            for track in tracks:
                track_name = track["name"]
                artist_name = track["artists"][0]["name"]
                duration = track["durationText"]
                trackid = track["id"]
                track_image = get_track_image(trackid, track_name)
                if get_track_image(trackid, track_name):
                    track_image = get_track_image(trackid, track_name)
                else:
                    track_image = "https://imgv3.fotor.com/images/blog-richtext-image/music-of-the-spheres-album-cover.jpg"

                track_list.append({
                    'track_name': track_name,
                    'artist_name': artist_name,
                    'duration': duration,
                    'trackid': trackid,
                    'track_image': track_image,
                })
        context = {
            'search_results_count': search_results_count,
            'track_list': track_list,
        }

        return render(request, 'search.html', context)
    else:
        return render(request, 'search.html')

def profile(request, pk):
    artist_id = pk
    url = "https://spotify-scraper.p.rapidapi.com/v1/artist/overview"

    querystring = {"artistId": artist_id}

    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        data = response.json()

        name = data["name"]
        monthly_listeners = data["stats"]["monthlyListeners"]
        header_url = data["visuals"]["header"][0]["url"]

        top_tracks = []

        for track in data["discography"]["topTracks"]:
            trackid = str(track["id"])
            trackname = str(track["name"])
            if get_track_image(trackid, trackname):
                trackimage = get_track_image(trackid, trackname)
            else:
                trackimage = ""

            track_info = {
                "id": track["id"],
                "name": track["name"],
                "durationText": track["durationText"],
                "playCount": track["playCount"],
                "track_image": trackimage
            }

            top_tracks.append(track_info)

        artist_data = {
            "name": name,
            "monthlyListeners": monthly_listeners,
            "headerUrl": header_url,
            "topTracks": top_tracks,
        }
    else:
        artist_data = {}
    return render(request, 'profile.html', artist_data)

def login(request):
    if request.method == 'POST':
        password = request.POST['password']
        username = request.POST['username']
        
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            #log user in
            auth.login(request, user)
            return redirect('/')
        else:
            messages.info(request, 'Credentials Invalid')
            return redirect('login')
    return render(request, './login.html')

def signup(request):
    if request.method == 'POST':
        email = request.POST['email']
        username = request.POST['username']
        password = request.POST['password']
        password2 = request.POST['password2']

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email is taken.')
                return redirect('signup') 
            elif User.objects.filter(email=email).exists():
                messages.info(request, 'Email is taken.')
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                #log user in

                user_login = auth.authenticate(username=username, password=password)
                auth.login(request, user_login)
                return redirect('/')
        else:
            messages.info(request, 'Password does not match.')
            return redirect('signup')
    else:
        return render(request, 'signup.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    return redirect('login')