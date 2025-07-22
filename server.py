import os
import time


from flask import Flask, redirect, request,jsonify
from flasgger import Swagger
from pydantic import BaseModel
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from flask_cors import CORS


# Set up Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000","https://spotify-broadcast-frontend.vercel.app"])  # ← allow your React dev server


# Initialize Swagger UI
swagger = Swagger(app)

# Set up your Spotify client credentials and redirect URI
CLIENT_ID = 'e6c0bc9e8d524b36996178a943047f75'
CLIENT_SECRET = '32617db6fdca4062b1cc096b87a25d8f'
REDIRECT_URI = 'https://www.example.com/callback'
SCOPE = 'user-read-playback-state'

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         redirect_uri=REDIRECT_URI,
                         cache_path="/home/wmpofos/mysite/.cache",
                         scope=SCOPE)

# Route for the initial Spotify authorization request
@app.route('/')
def index():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# # Callback route for Spotify to redirect to with authorization code
# @app.route('/callback')
# def callback():
#     # Get the authorization code from the URL
#     token_info = sp_oauth.get_access_token(request.args['code'])
#     access_token = token_info['access_token']

#     # Create the Spotify client with the access token
#     sp = Spotify(auth=access_token)

#     # Get the current playback details
#     results = sp.current_playback()

#     if results and results['is_playing']:
#         track = results['item']
#         return f"Currently playing: {track['artists'][0]['name']} – {track['name']}"
#     else:
#         return "No track currently playing."

# Pydantic model for track info
class TrackInfo(BaseModel):
    artist: str
    track: str

# Model for detailed track info
class TrackVerboseInfo(BaseModel):
    artist: str
    track: str
    album: str
    image_url: str
    progress_ms: int
    duration_ms: int
    is_playing: bool
    track_id: str
    spotify_url: str
    spotify_uri: str

# Function to get the current playback from Spotify
def get_current_playback():
    # In your case, you need to have an active token; you can either retrieve it from your OAuth flow or store it
    token_info = sp_oauth.get_cached_token()  # Assuming token is cached
    if not token_info:
        return None
    sp = Spotify(auth=token_info['access_token'])
    return sp.current_playback()

@app.route("/currently-playing", methods=["GET"])
def currently_playing():
    """
    This route fetches the current track being played.
    ---
    responses:
      200:
        description: Returns the current track information (artist and track name).
        schema:
          id: TrackInfo
          properties:
            artist:
              type: string
              example: 'Artist Name'
            track:
              type: string
              example: 'Track Name'
    """
    results = get_current_playback()
    if results and results.get('is_playing'):
        track = results['item']
        track_info = TrackInfo(
            artist=track['artists'][0]['name'],
            track=track['name']
        )
        return jsonify(track_info.dict())  # Convert Pydantic model to dict and jsonify
    return jsonify({"artist": "None", "track": "Nothing playing"})

@app.route("/currently-playing-verbose", methods=["GET"])
def currently_playing_verbose():

    """
    This route fetches detailed information about the current track being played.
    ---
    responses:
      200:
        description: Returns detailed information about the current track (artist, track, album, etc.)
        schema:
          id: TrackVerboseInfo
          properties:
            artist:
              type: string
              example: 'Artist Name'
            track:
              type: string
              example: 'Track Name'
            album:
              type: string
              example: 'Album Name'
            image_url:
              type: string
              example: 'http://link-to-image.com/image.jpg'
            progress_ms:
              type: integer
              example: 120000
            duration_ms:
              type: integer
              example: 300000
            is_playing:
              type: boolean
              example: true
    """
    results = get_current_playback()
    if results and results.get("is_playing"):
        track = results["item"]
        track_id = track["id"]
        position_seconds = results["progress_ms"] // 1000

        spotify_link = f"https://open.spotify.com/track/{track_id}?t={position_seconds}"
        app_link = f"spotify:track:{track_id}"

        track_verbose_info = TrackVerboseInfo(
            artist=track["artists"][0]["name"],
            track=track["name"],
            album=track["album"]["name"],
            image_url=track["album"]["images"][0]["url"],
            progress_ms=results["progress_ms"],
            duration_ms=track["duration_ms"],
            is_playing=results["is_playing"],
            spotify_url=spotify_link,
            spotify_uri=app_link,
            track_id=track_id

        )
        return jsonify(track_verbose_info.dict())  # Convert Pydantic model to dict and jsonify
    return jsonify({"artist": "None", "track": "Nothing playing"})

# if __name__ == '__main__':
    # Run the Flask app on localhost
    # app.run(port=5001)
