# main.py
from cryptography.fernet import Fernet
import base64
import requests
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import HTTPException
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
import json
import redis

# ---------------------
# FastAPI Setup
# ---------------------
app = FastAPI(
    title="Spotify Broadcast Backend",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc"
)

origins = [
    "http://localhost:3000",
    os.environ.get("FRONT_END_SERVER")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# Redis Setup
# ---------------------
REDIS_URL = os.environ.get("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True)

# ---------------------
# Spotify OAuth Setup
# ---------------------
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")

SCOPE = [
    "user-read-playback-state",
    "user-read-recently-played",
    "user-top-read",
    "user-read-email",
    "user-read-private"
]

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

# ---------------------
# Pydantic Models
# ---------------------


class TrackInfo(BaseModel):
    artists: list[str]
    track: str


class TrackVerboseInfo(BaseModel):
    artists: list[str]
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


class ErrorResponse(BaseModel):
    detail: str


class ArtistInfo(BaseModel):
    id: str
    name: str
    uri: str
    spotify_url: str
    image_url: str | None
    followers: int


class RecentlyPlayedTrack(BaseModel):
    id: str
    name: str
    artists: list[str]
    album: str
    image_url: str | None
    spotify_url: str
    played_at: str


class PlaylistInfo(BaseModel):
    id: str
    name: str
    description: str | None
    public: bool
    collaborative: bool
    owner: str
    tracks_total: int
    spotify_url: str
    image_url: str | None


class QueueTrackInfo(BaseModel):
    id: str
    name: str
    artists: list[str]
    album: str
    image_url: str | None
    spotify_url: str
    duration_ms: int

# ---------------------
# Helper Functions
# ---------------------


# Setup encryption
ENCRYPTION_KEY = os.environ.get(
    "ENCRYPTION_KEY").encode()  # store safely in env
fernet = Fernet(ENCRYPTION_KEY)


def save_token(token_info: dict):
    """Save access token with TTL and refresh token separately, encrypted."""
    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token")
    expires_in = token_info.get("expires_in", 3600)

    if access_token:
        encrypted_access = fernet.encrypt(access_token.encode()).decode()
        r.set("spotify_access_token", encrypted_access, ex=expires_in)

    if refresh_token:
        encrypted_refresh = fernet.encrypt(refresh_token.encode()).decode()
        r.set("spotify_refresh_token", encrypted_refresh)


def refresh_access_token():
    """Refresh the Spotify access token safely with Redis lock, decrypting the refresh token."""
    encrypted_refresh = r.get("spotify_refresh_token")
    if not encrypted_refresh:
        raise RuntimeError("No refresh token available in Redis")

    refresh_token = fernet.decrypt(encrypted_refresh.encode()).decode()

    with r.lock("spotify_refresh_lock", timeout=30, blocking_timeout=5):
        # Double-check in case another process refreshed while waiting
        encrypted_access = r.get("spotify_access_token")
        if encrypted_access:
            return fernet.decrypt(encrypted_access.encode()).decode()

        # Request new access token from Spotify
        auth_header = base64.b64encode(
            f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth_header}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to refresh token: {response.text}")

        token_info = response.json()
        save_token(token_info)
        return token_info["access_token"]


def get_valid_token():
    """Return a valid Spotify access token, refreshing if expired."""
    encrypted_access = r.get("spotify_access_token")
    if encrypted_access:
        return fernet.decrypt(encrypted_access.encode()).decode()
    return refresh_access_token()


def get_spotify_client():
    """Return a Spotify client with a valid token."""
    token = get_valid_token()
    if not token:
        return None
    return Spotify(auth=token)
# ---------------------
# Routes
# ---------------------


@app.get(
    "/",
    summary="Start Spotify OAuth",
    description="Redirects the client to Spotify's authorization page to start the OAuth flow.",
    responses={
        302: {"description": "Redirect to Spotify authorization URL"},
        500: {"model": ErrorResponse, "description": "Failed to generate authorization URL"},
    },
    tags=["auth"],
)
def index():
    """Redirect user to Spotify login"""
    try:
        auth_url = sp_oauth.get_authorize_url()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create auth URL: {e}")
    return RedirectResponse(auth_url)


@app.get(
    "/callback",
    summary="OAuth callback",
    description=(
        "Callback endpoint used by Spotify after user authorizes the app. "
        "Exchanges the provided `code` query parameter for an access/refresh token and stores it in Redis."
    ),
    responses={
        302: {"description": "Redirect to Swagger UI on success"},
        400: {"model": ErrorResponse, "description": "Missing or invalid code"},
        502: {"model": ErrorResponse, "description": "Token exchange failed"},
    },
    tags=["auth"],
)
def callback(request: Request):
    """Handle the OAuth callback from Spotify and store tokens."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    try:
        token_info = sp_oauth.get_access_token(code, as_dict=True)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Failed to exchange code for token: {e}")

    save_token(token_info)

    # After saving token, redirect to Swagger
    return RedirectResponse("/swagger")


@app.get(
    "/currently-playing",
    response_model=TrackInfo,
    summary="Simple currently playing track",
    description=(
        "Returns the currently playing track as a small object with `artist` and `track` fields. "
        "Requires a valid Spotify access token previously stored via the OAuth flow."
    ),
    responses={
        200: {"description": "OK - track data", "model": TrackInfo},
        204: {"description": "No Content - nothing is playing"},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["playback"],
)
def currently_playing():
    """Return a minimal representation of the currently playing track."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")
    try:
        results = sp.current_playback()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    is_private = results.get("device", {}).get("is_private_session", False)
    if is_private:
        return RedirectResponse(status_code=204, url="/currently-playing-verbose")

    if results and results.get("item") and results.get("is_playing"):
        track = results["item"]
        return {"artists": [artist["name"] for artist in track["artists"]], "track": track["name"]}
    # Nothing playing
    return RedirectResponse(status_code=204, url="/currently-playing")


@app.get(
    "/currently-playing-verbose",
    response_model=TrackVerboseInfo,
    summary="Verbose currently playing track",
    description=(
        "Returns detailed information about the currently playing track including album, image URL, "
        "progress and duration in milliseconds, playback state, and Spotify URLs."
    ),
    responses={
        200: {"description": "OK - verbose track data", "model": TrackVerboseInfo},
        204: {"description": "No Content - nothing is playing"},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["playback"],
)
def currently_playing_verbose():
    """Return a detailed representation of the currently playing track."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")
    try:
        results = sp.current_playback()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    is_private = results.get("device", {}).get("is_private_session", False)
    if is_private:
        return RedirectResponse(status_code=204, url="/currently-playing-verbose")

    if results and results.get("item") and results.get("is_playing"):
        track = results["item"]
        track_id = track["id"]
        position_seconds = results["progress_ms"] // 1000
        return {
            "artists": [artist["name"] for artist in track["artists"]],
            "track": track["name"],
            "album": track["album"]["name"],
            "image_url": track["album"]["images"][0]["url"],
            "progress_ms": results["progress_ms"],
            "duration_ms": track["duration_ms"],
            "is_playing": results["is_playing"],
            "spotify_url": f"https://open.spotify.com/track/{track_id}?t={position_seconds}",
            "spotify_uri": f"spotify:track:{track_id}",
            "track_id": track_id,
        }
    # Nothing playing
    return RedirectResponse(status_code=204, url="/currently-playing-verbose")


@app.get(
    "/user-info",
    response_model=UserInfo,
    summary="Get current user profile",
    description=(
        "Fetches the current Spotify user's profile information including display name, profile URI, "
        "profile image and follower count. Requires a valid Spotify access token."
    ),
    responses={
        200: {"description": "OK - user profile", "model": UserInfo},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["user"],
)
def get_user_info():
    """Return Spotify profile information for the authenticated user."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")
    try:
        me = sp.me()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")
    return {
        "display_name": me["display_name"],
        "uri": me["uri"],
        "image": me["images"][0]["url"] if me.get("images") else "https://i.scdn.co/image/ab67616100005174f1b7d5bb5d46191501fbd804",
        "height": me["images"][0]["height"] if me.get("images") else None,
        "width": me["images"][0]["width"] if me.get("images") else None,
        "followers": me["followers"]["total"] if me.get("followers") else None,
    }


@app.get(
    "/top-five",
    summary="Get top 5 tracks",
    description=(
        "Returns the authenticated user's top 5 tracks for the short-term time range. "
        "The endpoint uses Spotify's `current_user_top_tracks` with `limit=5` and `time_range='short_term'`."
    ),
    responses={
        200: {"description": "OK - list of top tracks"},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["user"],
)
def top_five():
    """Return the user's top five tracks in the short-term time range."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")
    try:
        top_tracks = sp.current_user_top_tracks(
            limit=5, time_range="short_term")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")
    return {"top_tracks": top_tracks['items']}


@app.get(
    "/top-five-artists",
    response_model=list[ArtistInfo],
    summary="Get top 5 artists",
    description=(
        "Returns the authenticated user's top 5 artists for the short-term time range. "
        "Uses Spotify's `current_user_top_artists` with `limit=5` and `time_range='short_term'`."
    ),
    responses={
        200: {"description": "OK - list of top artists"},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["user"],
)
def top_five_artists():
    """Return the user's top five artists in the short-term time range."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")
    try:
        top_artists = sp.current_user_top_artists(
            limit=5, time_range="short_term")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    # Map Spotify artist objects to our ArtistInfo model
    items = []
    for a in top_artists.get("items", []):
        items.append(
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "uri": a.get("uri"),
                "spotify_url": a.get("external_urls", {}).get("spotify"),
                "image_url": a.get("images", [{}])[0].get("url") if a.get("images") else None,
                "followers": a.get("followers", {}).get("total", 0),
            }
        )
    return items


@app.get(
    "/recently-played",
    response_model=list[RecentlyPlayedTrack],
    summary="Get recently played tracks",
    description=(
        "Returns the authenticated user's recently played tracks. "
        "Uses Spotify's `current_user_recently_played` with a default `limit=5` (max 50)."
    ),
    responses={
        200: {"description": "OK - list of recently played tracks", "model": list[RecentlyPlayedTrack]},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["user"],
)
def recently_played(limit: int = 5):
    """Return the user's recently played tracks."""
    if limit > 50:
        limit = 50  # Spotify max

    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")

    try:
        results = sp.current_user_recently_played(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    items = []
    for item in results.get("items", []):
        track = item["track"]
        items.append(
            RecentlyPlayedTrack(
                id=track["id"],
                name=track["name"],
                artists=[artist["name"] for artist in track["artists"]],
                album=track["album"]["name"],
                image_url=track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                spotify_url=track["external_urls"]["spotify"],
                played_at=item.get("played_at"),
            )
        )

    return items


@app.get(
    "/my-playlists",
    response_model=list[PlaylistInfo],
    summary="Get user's public playlists",
    description=(
        "Returns the authenticated user's public playlists. "
        "Uses Spotify's `current_user_playlists` endpoint."
    ),
    responses={
        200: {"description": "OK - list of public playlists", "model": list[PlaylistInfo]},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["playlists"],
)
def my_playlists(limit: int = 5):
    """Return the user's public playlists."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")

    try:
        results = sp.current_user_playlists()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    items = []
    if limit != -1:
        playlists = results.get("items", [])[:limit]
    else:
        playlists = results.get("items", [])
        
    for playlist in playlists:
        # Only include public playlists
        if playlist.get("public"):
            items.append(
                PlaylistInfo(
                    id=playlist["id"],
                    name=playlist["name"],
                    description=playlist.get("description"),
                    public=playlist["public"],
                    collaborative=playlist.get("collaborative", False),
                    owner=playlist["owner"]["display_name"],
                    tracks_total=playlist["tracks"]["total"],
                    spotify_url=playlist["external_urls"]["spotify"],
                    image_url=playlist["images"][0]["url"] if playlist.get(
                        "images") else None,
                )
            )

    return items


@app.get(
    "/next-in-queue",
    response_model=QueueTrackInfo,
    summary="Get next song in queue",
    description=(
        "Returns the next track in the user's playback queue. "
        "Uses Spotify's `queue` endpoint to fetch the upcoming track."
    ),
    responses={
        200: {"description": "OK - next track in queue", "model": QueueTrackInfo},
        204: {"description": "No Content - queue is empty"},
        401: {"model": ErrorResponse, "description": "Unauthorized - no token"},
        502: {"model": ErrorResponse, "description": "Upstream Spotify error"},
    },
    tags=["playback"],
)
def next_in_queue():
    """Return the next track in the user's playback queue."""
    sp = get_spotify_client()
    if not sp:
        raise HTTPException(status_code=401, detail="Spotify token not found")

    try:
        queue = sp.queue()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")

    # Get the first item in the queue (next track)
    queue_items = queue.get("queue", [])
    if not queue_items:
        raise HTTPException(status_code=204, detail="Queue is empty")

    next_track = queue_items[0]
    return QueueTrackInfo(
        id=next_track["id"],
        name=next_track["name"],
        artists=[artist["name"] for artist in next_track["artists"]],
        album=next_track["album"]["name"],
        image_url=next_track["album"]["images"][0]["url"] if next_track["album"].get("images") else None,
        spotify_url=next_track["external_urls"]["spotify"],
        duration_ms=next_track["duration_ms"],
    )
