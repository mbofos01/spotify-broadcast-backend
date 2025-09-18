from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import json
import redis

# ---------------------
# FastAPI Setup
# ---------------------
app = FastAPI(
    title="Spotify Broadcast Backend",
    description="Backend service for Spotify data with FastAPI",
    version="1.0.0",
    docs_url="/swagger",   # Swagger UI at /swagger
    redoc_url="/redoc"     # ReDoc at /redoc
)

# CORS setup
origins = [
    "http://localhost:3000",
    "https://spotify-broadcast-frontend.vercel.app"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# Spotify OAuth Setup
# ---------------------
load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
REDIS_URL = os.environ.get("REDIS_URL")

# Redis connection using URL
r = redis.from_url(REDIS_URL, decode_responses=True)

SCOPE = [
    "user-read-playback-state",
    "user-top-read",
    "user-read-email",
    "user-read-private"
]

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    cache_path=".cache",
    scope=SCOPE
)

# ---------------------
# Pydantic Models
# ---------------------


class TrackInfo(BaseModel):
    artist: str
    track: str


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


class UserInfo(BaseModel):
    display_name: str
    uri: str
    image: str | None
    height: int | None
    width: int | None
    followers: int | None

# ---------------------
# Helper Functions
# ---------------------


def save_token(token_info: dict):
    r.set("spotify_token", json.dumps(token_info))


def load_token():
    token = r.get("spotify_token")
    return json.loads(token) if token else None


def get_spotify_client():
    token_info = load_token()
    if not token_info:
        return None
    # Refresh token if expired
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        save_token(token_info)
    return Spotify(auth=token_info["access_token"])

# ---------------------
# Routes
# ---------------------


@app.get("/")
def index():
    """Get Spotify authorization URL"""
    return {"auth_url": sp_oauth.get_authorize_url()}


@app.get("/currently-playing", response_model=TrackInfo)
def currently_playing():
    """Get current track (basic info)"""
    sp = get_spotify_client()
    if not sp:
        return {"artist": "None", "track": "Nothing playing"}
    results = sp.current_playback()
    if results and results.get("is_playing"):
        track = results["item"]
        return {"artist": track["artists"][0]["name"], "track": track["name"]}
    return {"artist": "None", "track": "Nothing playing"}


@app.get("/currently-playing-verbose", response_model=TrackVerboseInfo)
def currently_playing_verbose():
    """Get detailed track info"""
    sp = get_spotify_client()
    if not sp:
        return {"artist": "None", "track": "Nothing playing"}
    results = sp.current_playback()
    if results and results.get("is_playing"):
        track = results["item"]
        track_id = track["id"]
        position_seconds = results["progress_ms"] // 1000
        return {
            "artist": track["artists"][0]["name"],
            "track": track["name"],
            "album": track["album"]["name"],
            "image_url": track["album"]["images"][0]["url"],
            "progress_ms": results["progress_ms"],
            "duration_ms": track["duration_ms"],
            "is_playing": results["is_playing"],
            "spotify_url": f"https://open.spotify.com/track/{track_id}?t={position_seconds}",
            "spotify_uri": f"spotify:track:{track_id}",
            "track_id": track_id
        }
    return {"artist": "None", "track": "Nothing playing"}


@app.get("/user-info", response_model=UserInfo)
def get_user_info():
    """Get user profile info"""
    sp = get_spotify_client()
    if not sp:
        return {"display_name": "Unknown", "uri": "", "image": None,
                "height": None, "width": None, "followers": None}
    me = sp.me()
    return {
        "display_name": me["display_name"],
        "uri": me["uri"],
        "image": me["images"][0]["url"] if me.get("images") else None,
        "height": me["images"][0]["height"] if me.get("images") else None,
        "width": me["images"][0]["width"] if me.get("images") else None,
        "followers": me["followers"]["total"] if me.get("followers") else None,
    }


@app.get("/top-five")
def top_five():
    """Get top 5 tracks"""
    sp = get_spotify_client()
    if not sp:
        return {"top_tracks": []}
    top_tracks = sp.current_user_top_tracks(limit=5, time_range="short_term")
    simplified = []
    for t in top_tracks["items"]:
        simplified.append({
            "artist": t["artists"][0]["name"],
            "track": t["name"]
        })
    return {"top_tracks": simplified}


@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing code"}

    token_info = sp_oauth.get_access_token(code, as_dict=True)
    save_token(token_info)
    return {"message": "Login successful. Token saved."}
