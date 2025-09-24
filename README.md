# Spotify Broadcast Backend

This repository contains a FastAPI backend that integrates with the Spotify API to expose the currently playing track, user profile, and top tracks. This README combines the API reference, setup, and examples so you can get started quickly.

## Table of contents

- [Setup & environment](#setup--environment)
- [Run locally](#run-locally)
- [OAuth flow](#oauth-flow)
- [Endpoints (summary)](#endpoints-summary)
  - [`GET /`](#get-)
  - [`GET /callback`](#get-callback)
  - [`GET /currently-playing`](#get-currently-playing)
  - [`GET /currently-playing-verbose`](#get-currently-playing-verbose)
  - [`GET /user-info`](#get-user-info)
  - [`GET /top-five`](#get-top-five)
- [Examples (curl)](#examples-curl)
- [OpenAPI docs](#openapi-docs)
- [Suggestions & next steps](#suggestions--next-steps)

## Setup & environment

Create a copy of `.env.example` named `.env` and fill in your Spotify app credentials and Redis URL:

```env
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=http://localhost:8000/callback
FRONT_END_SERVER=http://localhost:3000
REDIS_URL=redis://localhost:6379/0
```

Notes:

- `.env` is ignored by git (see `.gitignore`). Do not commit secrets.
- You can also set these variables in your shell or CI environment.

## Run locally

Install dependencies and start the server:

```powershell
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Make sure Redis is running and accessible at `REDIS_URL` before starting the app.

## OAuth flow

1. Visit `GET /` in your browser — the backend will redirect you to Spotify's authorization screen.
2. After you authorize the app, Spotify redirects to `GET /callback?code=...`.
3. The backend exchanges the `code` for tokens, stores them in Redis under `spotify_token`, and redirects to `/swagger`.

## Endpoints (summary)

All endpoints are defined in `main.py` and documented in the OpenAPI schema available at `/swagger` and `/redoc`.

### GET /

- Description: Start the OAuth flow by redirecting to Spotify's authorization URL.
- Responses: `302` redirect, `500` on server error.

### GET /callback

- Description: OAuth callback; exchanges `code` for tokens and stores them in Redis.
- Query parameters: `code` (required)
- Responses: `302` redirect on success, `400` for missing code, `502` for token exchange failures.

### GET /currently-playing

- Description: Returns minimal currently playing info: `{ artist, track }`.
- Responses: `200` with `TrackInfo`, `204` if nothing is playing, `401` if no token, `502` for Spotify errors.

### GET /currently-playing-verbose

- Description: Returns verbose currently playing info with album, image, progress/duration, and Spotify URLs.
- Responses: `200` with `TrackVerboseInfo`, `204` if nothing is playing, `401` if no token, `502` for Spotify errors.

### GET /user-info

- Description: Returns the authenticated user's Spotify profile info.
- Responses: `200` with `UserInfo`, `401` if no token, `502` for Spotify errors.

### GET /top-five

- Description: Returns the user's top 5 tracks (short-term).
- Responses: `200` with `{ "top_tracks": [...] }`, `401` if no token, `502` for Spotify errors.

## Examples (curl)

Simple calls (replace `localhost:8000` with your host if different):

```bash
curl http://localhost:8000/currently-playing
curl http://localhost:8000/currently-playing-verbose
curl http://localhost:8000/user-info
curl http://localhost:8000/top-five
```

## OpenAPI docs

- Swagger UI: `http://localhost:8000/swagger`
- ReDoc: `http://localhost:8000/redoc`

The OpenAPI UI now includes response code documentation and the `ErrorResponse` schema for error responses.

## Example responses

Below are example success and error responses for each endpoint to make testing and docs clearer.

### GET / (start OAuth)

Success (redirect): 302 - Redirect to Spotify authorization URL

Example error (500):

```json
{ "detail": "Failed to create auth URL: <error message>" }
```

### GET /callback

Success (redirect): 302 - Redirect to `/swagger` after tokens saved.

Error (400) - missing code:

```json
{ "detail": "Missing code" }
```

Error (502) - token exchange failed:

```json
{ "detail": "Failed to exchange code for token: <error message>" }
```

### GET /currently-playing

Success (200):

```json
{ "artist": "Tame Impala", "track": "The Less I Know The Better" }
```

No content (204): empty body

Error (401) - no token:

```json
{ "detail": "Spotify token not found" }
```

Error (502):

```json
{ "detail": "Spotify API error: <error message>" }
```

### GET /currently-playing-verbose

Success (200):

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

No content (204): empty body

Error (401):

```json
{ "detail": "Spotify token not found" }
```

### GET /user-info

Success (200):

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

Error (401):

```json
{ "detail": "Spotify token not found" }
```

### GET /top-five

Success (200):

```json
{
    "top_tracks": [
        {
            "album": {
                "album_type": "compilation",
                "total_tracks": 11,
                "available_markets": [...],
                "external_urls": {
                "spotify": "https://open.spotify.com/album/4Y9ISbppFbwk0r1XCLUi0I"
                },
                "href": "https://api.spotify.com/v1/albums/4Y9ISbppFbwk0r1XCLUi0I",
                "id": "4Y9ISbppFbwk0r1XCLUi0I",
                "images": [
                {
                    "url": "https://i.scdn.co/image/ab67616d0000b273c1c10d28c1887c2bb1f6b2fa",
                    "height": 640,
                    "width": 640
                },
                {
                    "url": "https://i.scdn.co/image/ab67616d00001e02c1c10d28c1887c2bb1f6b2fa",
                    "height": 300,
                    "width": 300
                },
                {
                    "url": "https://i.scdn.co/image/ab67616d00004851c1c10d28c1887c2bb1f6b2fa",
                    "height": 64,
                    "width": 64
                }
                ],
                "name": "The Best of 2Pac",
                "release_date": "2007-12-03",
                "release_date_precision": "day",
                "type": "album",
                "uri": "spotify:album:4Y9ISbppFbwk0r1XCLUi0I",
                "artists": [
                {
                    "external_urls": {
                    "spotify": "https://open.spotify.com/artist/1ZwdS5xdxEREPySFridCfh"
                    },
                    "href": "https://api.spotify.com/v1/artists/1ZwdS5xdxEREPySFridCfh",
                    "id": "1ZwdS5xdxEREPySFridCfh",
                    "name": "2Pac",
                    "type": "artist",
                    "uri": "spotify:artist:1ZwdS5xdxEREPySFridCfh"
                }
                ]
            },
            "artists": [
                {
                "external_urls": {
                    "spotify": "https://open.spotify.com/artist/1ZwdS5xdxEREPySFridCfh"
                },
                "href": "https://api.spotify.com/v1/artists/1ZwdS5xdxEREPySFridCfh",
                "id": "1ZwdS5xdxEREPySFridCfh",
                "name": "2Pac",
                "type": "artist",
                "uri": "spotify:artist:1ZwdS5xdxEREPySFridCfh"
                },
                {
                "external_urls": {
                    "spotify": "https://open.spotify.com/artist/3GMoVpWJy4smKuxFuFTwXC"
                },
                "href": "https://api.spotify.com/v1/artists/3GMoVpWJy4smKuxFuFTwXC",
                "id": "3GMoVpWJy4smKuxFuFTwXC",
                "name": "Roger",
                "type": "artist",
                "uri": "spotify:artist:3GMoVpWJy4smKuxFuFTwXC"
                },
                {
                "external_urls": {
                    "spotify": "https://open.spotify.com/artist/6DPYiyq5kWVQS4RGwxzPC7"
                },
                "href": "https://api.spotify.com/v1/artists/6DPYiyq5kWVQS4RGwxzPC7",
                "id": "6DPYiyq5kWVQS4RGwxzPC7",
                "name": "Dr. Dre",
                "type": "artist",
                "uri": "spotify:artist:6DPYiyq5kWVQS4RGwxzPC7"
                }
            ],
            "available_markets": [...],
            "disc_number": 1,
            "duration_ms": 284480,
            "explicit": true,
            "external_ids": {
                "isrc": "USUG10702628"
            },
            "external_urls": {
                "spotify": "https://open.spotify.com/track/3djNBlI7xOggg7pnsOLaNm"
            },
            "href": "https://api.spotify.com/v1/tracks/3djNBlI7xOggg7pnsOLaNm",
            "id": "3djNBlI7xOggg7pnsOLaNm",
            "name": "California Love - Original Version",
            "popularity": 59,
            "preview_url": null,
            "track_number": 2,
            "type": "track",
            "uri": "spotify:track:3djNBlI7xOggg7pnsOLaNm",
            "is_local": false
        },
    ]
}
```

Error (401):

```json
{ "detail": "Spotify token not found" }
```
