# API Quick Reference & Examples

Start the server (example):

```bash
uvicorn main:app --reload --port 8000
```

OAuth and token setup:

1. Visit `GET /` in your browser to be redirected to Spotify's authorization page.
2. After authorizing, Spotify will redirect to `/callback` and the server will store token in Redis.

Example curl requests (replace `localhost:8000` with your host if different):

- Simple currently playing:

```bash
curl http://localhost:8000/currently-playing
```

- Verbose currently playing:

```bash
curl http://localhost:8000/currently-playing-verbose
```

- User info:

```bash
curl http://localhost:8000/user-info
```

- Top five tracks:

```bash
curl http://localhost:8000/top-five
```

Browse interactive docs:

- Swagger UI: `http://localhost:8000/swagger`
- ReDoc: `http://localhost:8000/redoc`

Notes:
- The server must have a valid Spotify access token saved in Redis before endpoints return real user data.
- Use `.env.example` to configure the environment variables for local development.

