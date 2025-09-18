import os
import redis
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
REDIS_URL = os.environ.get("REDIS_URL")

# Spotify OAuth setup
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
    scope=SCOPE
)

# Connect to Redis
r = redis.from_url(REDIS_URL)

# Manually paste the "code" from Spotify's auth redirect
code = input("Paste Spotify code here: ").strip()

# Exchange code for tokens
token_info = sp_oauth.get_access_token(code)

# Write tokens to Redis
r.set("spotify_access_token", token_info["access_token"])
r.set("spotify_refresh_token", token_info["refresh_token"])

print("Tokens saved to Redis!")
# AQAOgVxuFX7krm8AumYiMEwRqW5FOh2CZuqwh-E3Yi1atuuAvDcMPDnNH838fhudqEzQ9XjgHbkvL1O0q5mVhf3dL_bhigcUxxMIJOaQSOymCCYEFLFL7FGubTr9doyU4sgBk6ETvjtNMuOxEp8rK4slpwXbi8YETvft-G9qGPD1I66o5B8ohcDnUYt59yydRy9j0qzSz89jbFvjYJ63ONsNYsTZG-SZz9W60tL1A6XD48Wk2PxbWahcieoK3B0xiXgThQiL0wogZ8IVXHFcCEM