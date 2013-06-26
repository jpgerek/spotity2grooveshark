import json
import hashlib
import httplib
import os
import time

CACHE_DIR = 'cached'

def get_song_name(spotify_url):
    domain = "ws.spotify.com"
    url = "/lookup/1/.json?uri=%s" % spotify_url.strip('\n')
    file = '%s/spotify-%s' % (CACHE_DIR, md5(url))
    content = None
    if not os.path.exists(file):
        conn = httplib.HTTPConnection(domain)
        conn.request("GET", url)
        content = conn.getresponse().read()
        f = open(file, 'wb')
        f.write(content)
        f.close()
    else:
        f = open(file)
        content = f.read()
        f.close()
    try:
        song = json.loads(content)
    except ValueError as ex:
        print "Error getting song name:"
        print url
        print content
        print "Retrying after 10 seconds."
        time.sleep(10)
        return get_song_name(spotify_url)
    result = {'song': song['track']['name']}
    track = song['track']
    if 'album' in track:
        result['album'] = track['album']['name']
    if 'artists' in track:
        result['artist'] = track['artists'][0]['name']
    return result

def md5(content):
    return hashlib.md5(content).hexdigest()

def make_sure_dir_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)