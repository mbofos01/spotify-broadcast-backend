# Spotify Broadcast Backend - API Endpoints

This document describes all public HTTP endpoints provided by the `Spotify Broadcast Backend` (defined in `main.py`). Each endpoint includes path, HTTP method, authentication requirements, parameters, response schema, example responses, and common status codes.

---

## Authentication and Setup

This service uses Spotify OAuth to obtain an access token. The service requires the following environment variables (see `.env.example`):

- `CLIENT_ID` - Spotify app client ID
- `CLIENT_SECRET` - Spotify app client secret
- `REDIRECT_URI` - OAuth redirect URI configured in your Spotify app
- `REDIS_URL` - Redis connection URL used to persist token info

The backend stores Spotify token information in Redis under the key `spotify_token`.

OAuth flow:
1. Call `GET /` to receive a redirect URL to Spotify's authorization page.
2. After user authorizes, Spotify redirects to `/callback` with a `code` query parameter.
3. The backend exchanges the `code` for tokens, saves the token in Redis, and redirects to `/swagger`.

---

## Endpoints

### 1) GET /
- Purpose: Start the OAuth flow. Redirects user to the Spotify authorization URL.
- Method: `GET`
- Authentication: None
- Query parameters: None
- Request body: None
- Responses:
  - `302` Redirect to the Spotify authorization URL
- Example usage:
  - Browser: navigate to `http://<host>/`

---

### 2) GET /callback
- Purpose: OAuth callback endpoint. Exchanges `code` for an access token and stores it in Redis.
- Method: `GET`
- Authentication: None (Spotify will call this after user authorization)
- Query parameters:
  - `code` (required) - authorization code provided by Spotify
- Request body: None
- Responses:
  - `302` Redirect to `/swagger` on success
  - `200` or `4xx` JSON with an `error` message if missing `code` or exchange fails
- Example:
  - `GET /callback?code=AQBk...`

---

### 3) GET /currently-playing
- Purpose: Return a simple currently playing track object: `{ artist, track }`.
- Method: `GET`
- Authentication: Requires a valid Spotify token (stored in Redis) — otherwise returns defaults indicating nothing playing.
- Query parameters: None
- Request body: None
- Response schema: `TrackInfo`
  ```json
  {
    "artist": "string",
    "track": "string"
  }
  ```
- Responses:
  - `200` JSON with the currently playing track or a placeholder if not available.
- Example success response:
  ```json
  {
    "artist": "Tame Impala",
    "track": "The Less I Know The Better"
  }
  ```
- Example fallback response when no token or nothing playing:
  ```json
  {"artist": "None", "track": "Nothing playing"}
  ```

---

### 4) GET /currently-playing-verbose
- Purpose: Return detailed track info with album, image, progress, duration, play state, and Spotify URLs.
- Method: `GET`
- Authentication: Requires valid Spotify token
- Request body: None
- Response schema: `TrackVerboseInfo`
  ```json
  {
    "artist": "string",
    "track": "string",
    "album": "string",
    "image_url": "string",
    "progress_ms": 0,
    "duration_ms": 0,
    "is_playing": true,
    "track_id": "string",
    "spotify_url": "string",
    "spotify_uri": "string"
  }
  ```
- Responses:
  - `200` JSON with track details, or a default object when no track is playing or token is missing.
- Example success response:
  ```json
  {
    "artist": "Tame Impala",
    "track": "The Less I Know The Better",
    "album": "Currents",
    "image_url": "https://i.scdn.co/image/...",
    "progress_ms": 123456,
    "duration_ms": 216000,
    "is_playing": true,
    "track_id": "5yEP6q9ugbSrzV4r5q5FQX",
    "spotify_url": "https://open.spotify.com/track/5yEP6q9ugbSrzV4r5q5FQX?t=123",
    "spotify_uri": "spotify:track:5yEP6q9ugbSrzV4r5q5FQX"
  }
  ```

---

### 5) GET /user-info
- Purpose: Return user profile information from Spotify (display name, uri, image, followers, image dimensions)
- Method: `GET`
- Authentication: Requires valid Spotify token
- Request body: None
- Response schema: `UserInfo`
  ```json
  {
    "display_name": "string",
    "uri": "string",
    "image": "string | null",
    "height": 0 | null,
    "width": 0 | null,
    "followers": 0 | null
  }
  ```
- Responses:
  - `200` JSON with user info or default/unknown values when token missing
- Example success response:
  ```json
  {
    "display_name": "Marvin B.",
    "uri": "spotify:user:marvin",
    "image": "https://i.scdn.co/image/...",
    "height": 300,
    "width": 300,
    "followers": 123
  }
  ```

---

### 6) GET /top-five
- Purpose: Return the user's top 5 tracks for the short term
- Method: `GET`
- Authentication: Requires valid Spotify token
- Request body: None
- Response: JSON object `{ "top_tracks": [ <track objects> ] }` using Spotify's track object schema
- Responses:
  - `200` JSON list of up to 5 top tracks
  - `200` `{ "top_tracks": [] }` when no token or none available
- Example response (truncated track object):
  ```json
  {
    "top_tracks": [
      {"id":"...","name":"...","artists":[{"name":"..."}], ...},
      ...
    ]
  }
  ```

---

## Error handling
- This backend returns minimal error payloads. Common fallback:
  - When token not found or Spotify client unavailable: endpoints return default JSON objects indicating nothing is playing or unknown user.
- If Spotify API calls fail with 4xx/5xx, FastAPI will return an HTTP error status with details from the Spotipy exception.

## Running locally
- Create a `.env` file or set environment variables for `CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`, and `REDIS_URL`.
- Start Redis locally or provide a Redis URL (e.g., `redis://localhost:6379/0`).
- Install dependencies in `requirements.txt` and start the FastAPI app (example using uvicorn):

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

After tokens are saved, use the endpoints above to fetch user / playback data.

---

## OpenAPI / Swagger
This FastAPI application exposes Swagger UI at `/swagger` (custom `docs_url`) and Redoc at `/redoc`.

---

## Suggestions / Improvements
- Add proper error responses (HTTP status codes and structured error bodies) for missing tokens, rate-limits, and Spotify errors.
- Protect the `/callback` route with a CSRF state parameter to validate the OAuth flow more securely.
- Add a `POST /refresh-token` endpoint if you want manual token refresh capability.
- Add request logging and rate-limiting for production.

---

If you want, I can also:
- Generate an OpenAPI YAML/JSON file with example responses.
- Add a brief `README_API.md` with example curl commands for each endpoint.
- Implement a small Postman collection or `httpie` snippets for testing.

Which of the above would you like next?