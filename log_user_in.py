import requests
import time
import json

# Replace these with your actual values
client_id = 'e6c0bc9e8d524b36996178a943047f75'
client_secret = '32617db6fdca4062b1cc096b87a25d8f'

code = 'AQB8egk4FnoeKMQDaqQwXpOdtmwLro0RAVZDn8-JLjX46BHgopiKOmcHb88F_r4n0WN7fh2tNAw1-lFdrQB6X8sNufy-wImqNME7wTWx0WsYu1mMFn8QtPo1McfqiY1RuMSjk9dHEtpTZqyUVjul0xEJkBRK5bAzK5_nUO4TAXYxxNfuWzmTsJ2NLXP2jv1jP2fKZqAq4DNYBGFdndl7NwykDqTxvY9pOdEdf3OqtIWIHg8wWIQdlzfxsA'
code = 'AQBgrwM6EbUqj5Qk6KjvLLQwKBRCh409mCdK4PrMNZGu6r9a3oKK7wmR2rphtqC4jtE0uTMp6pgnEJ9Rw2Sw37bKm-CME4O2f7qHbXcjiF0dRuya6jJJbZ6XkgAhBDkY-dB_C4oll5X8TDxL8Z1MQT6-TCA7qMJbHmxmQxnAienJQTwx5A6okv8EAhqM_i_KsTJewMsMWvtt-PYpTR4'
redirect_uri = 'https://www.example.com/callback'

response = requests.post(
    'https://accounts.spotify.com/api/token',
    data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
)

tokens = response.json()
access_token = tokens.get('access_token')
refresh_token = tokens.get('refresh_token')

print("Access Token:", access_token)
print("Refresh Token:", refresh_token)


expires_in = tokens.get('expires_in', 3600)  # fallback to 3600s
scope = tokens.get('scope', '')              # optional
token_type = tokens.get('token_type', 'Bearer')  # default is 'Bearer'

# Calculate expiration time
expires_at = int(time.time()) + int(expires_in)

# Construct the token dictionary
token_info = {
    "access_token": access_token,
    "token_type": token_type,
    "expires_in": expires_in,
    "refresh_token": refresh_token,
    "scope": scope,
    "expires_at": expires_at
}

# Save to .cache file
with open(".cache", "w") as f:
    json.dump(token_info, f)

print("Token saved to .cache")
