import re
from enum import Enum

import aiohttp
import spotipy
from bs4 import BeautifulSoup
from config import config
from spotipy.oauth2 import SpotifyClientCredentials

try:
    sp_api = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=config.SPOTIFY_ID, client_secret=config.SPOTIFY_SECRET))
    api = True
except:
    api = False

# Fixed regex patterns with raw strings
url_regex = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

# Session management
_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'})
    return _session

async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None

def clean_sclink(track):
    if track.startswith("https://m."):
        track = track.replace("https://m.", "https://")
    if track.startswith("http://m."):
        track = track.replace("http://m.", "https://")
    return track

async def convert_spotify(url):
    session = await get_session()
    if re.search(url_regex, url):
        result = url_regex.search(url)
        if "?si=" in url:
            url = result.group(0) + "&nd=1"

    async with session.get(url) as response:
        page = await response.text()
        soup = BeautifulSoup(page, 'html.parser')
        title = soup.find('title')
        title = title.string
        title = title.replace('- song by', '')
        title = title.replace('| Spotify', '')
        return title

async def get_spotify_playlist(url):
    """Return Spotify_Playlist class"""
    code = url.split('/')[4].split('?')[0]

    if api:
        if "open.spotify.com/album" in url:
            try:
                results = sp_api.album_tracks(code)
                tracks = results['items']
                while results['next']:
                    results = sp_api.next(results)
                    tracks.extend(results['items'])
                return [track['external_urls']['spotify'] for track in tracks if 'external_urls' in track]
            except:
                if config.SPOTIFY_ID or config.SPOTIFY_SECRET:
                    print("ERROR: Check spotify CLIENT_ID and SECRET")

        if "open.spotify.com/playlist" in url:
            try:
                results = sp_api.playlist_items(code)
                tracks = results['items']
                while results['next']:
                    results = sp_api.next(results)
                    tracks.extend(results['items'])
                return [track['track']['external_urls']['spotify'] for track in tracks if track.get('track', {}).get('external_urls')]
            except:
                if config.SPOTIFY_ID or config.SPOTIFY_SECRET:
                    print("ERROR: Check spotify CLIENT_ID and SECRET")

    session = await get_session()
    async with session.get(url + "&nd=1") as response:
        page = await response.text()

    soup = BeautifulSoup(page, 'html.parser')
    results = soup.find_all(property="music:song", attrs={"content": True})
    return [item['content'] for item in results]

def get_url(content):
    if re.search(url_regex, content):
        result = url_regex.search(content)
        return result.group(0)
    return None

class Sites(Enum):
    Spotify = "Spotify"
    Spotify_Playlist = "Spotify Playlist"
    YouTube = "YouTube"
    Twitter = "Twitter"
    SoundCloud = "SoundCloud"
    Bandcamp = "Bandcamp"
    Custom = "Custom"
    Unknown = "Unknown"

class Playlist_Types(Enum):
    Spotify_Playlist = "Spotify Playlist"
    YouTube_Playlist = "YouTube Playlist"
    BandCamp_Playlist = "BandCamp Playlist"
    Unknown = "Unknown"

class Origins(Enum):
    Default = "Default"
    Playlist = "Playlist"

def identify_url(url):
    if url is None:
        return Sites.Unknown
    if "https://www.youtu" in url or "https://youtu.be" in url:
        return Sites.YouTube
    if "https://open.spotify.com/track" in url:
        return Sites.Spotify
    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return Sites.Spotify_Playlist
    if "bandcamp.com/track/" in url:
        return Sites.Bandcamp
    if "https://twitter.com/" in url:
        return Sites.Twitter
    if url.lower().endswith(config.SUPPORTED_EXTENSIONS):
        return Sites.Custom
    if "soundcloud.com/" in url:
        return Sites.SoundCloud
    return Sites.Unknown

def identify_playlist(url):
    if url is None:
        return Sites.Unknown
    if "playlist?list=" in url:
        return Playlist_Types.YouTube_Playlist
    if "https://open.spotify.com/playlist" in url or "https://open.spotify.com/album" in url:
        return Playlist_Types.Spotify_Playlist
    if "bandcamp.com/album/" in url:
        return Playlist_Types.BandCamp_Playlist
    return Playlist_Types.Unknown
