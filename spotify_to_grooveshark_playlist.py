#!/usr/bin/python

from groove import GrooveShark
import urllib
import sys
import os
import time
import helpers
import json

CACHE_DIR = 'cached'

DOWNLOADS_DIR = 'downloads'

#- Create cache dir if it doesn't exist -#
helpers.make_sure_dir_exists(CACHE_DIR)
helpers.make_sure_dir_exists(DOWNLOADS_DIR)

def params():
    print "%s <spotify_songs_file>" % sys.argv[0]
    exit(2)


def is_good_for_playlist(grooveshark_song):
    song_id = int(grooveshark_song['SongID'])
    temp_playlist_name = 'foo'
    #- Create a temporal playlist with the song-#
    temp_playlist_id = gs.create_playlist(temp_playlist_name, [song_id])
    #-Checking if it was added -#
    playlist_songs = gs.get_playlist_by_id(temp_playlist_id)
    #- Deleting temp playlist -#
    gs.delete_playlist(temp_playlist_id, temp_playlist_name)
    return len(playlist_songs['Songs']) == 1

if len(sys.argv) != 2:
    params()

spotify_file = sys.argv[1]
if not os.path.exists(spotify_file):
    print "'%s' doesn't exist." % spotify_file

gs = GrooveShark()
not_found = []
found = []

if gs.authenticate() is False:
    print "Error authenticating."
    exit(2)

for spotify_url in open(spotify_file):
    spotify_song = helpers.get_song_name(spotify_url)
    if spotify_song is None:
        print "No song info for %s" % spotify_url
        continue
    print "Spotify song: %s, %s, %s" % (spotify_song.get('song'), spotify_song.get('album') or '', spotify_song.get('artist') or '')
    #- Getting search result from cache or getting it and caching it -#
    cache_file = "%s/gs-result-%s" % (CACHE_DIR, helpers.md5(spotify_url))
    if os.path.exists(cache_file):
        result = json.loads(open(cache_file).read())
    else:
        result = gs.search_song(spotify_song.get('song'), spotify_song.get('album'), spotify_song.get('artist'))
        open(cache_file, 'wb').write(json.dumps(result))
    #- Nothing found -#
    if len(result) == 0:
        not_found.append(spotify_song)
        print "\tNo result in Grooveshark."
        continue
    grooveshark_song = result[0]
    print "\tGrooveshark: %s, %s, %s." % (grooveshark_song['SongName'], grooveshark_song['AlbumName'], grooveshark_song['ArtistName'])
    found.append((int(grooveshark_song['SongID']), grooveshark_song['SongName'], grooveshark_song['ArtistName'], grooveshark_song['AlbumName']))
    for attempt in xrange(3):
        if gs.add_song_to_queue(grooveshark_song, gs.get_queue_id()):
            break

print "Found: %d" % len(found)

if len(found) == 0:
    exit()

playlist_name = spotify_file.split('/')[-1]
song_ids = map(lambda item: item[0], set(found))
not_found_report = []
if len(not_found) > 0:
    not_found_report.append("%d song/s weren't found on Grooveshark:" % len(not_found))
    for offset, song in enumerate(not_found):
        not_found_report.append("\t%d - %s, %s, %s" % (offset+1, song.get('song'), song.get('album'), song.get('artist')))
    print "\n".join(not_found_report)
playlist_id = gs.create_playlist(playlist_name, song_ids)
playlist_songs = gs.get_playlist_songs(playlist_id)
print "Playlist created with: %d song/s" % len(playlist_songs)
if len(song_ids) < len(found):
    print "There were %d song/s repeated" % (len(found) - len(song_ids))
print "Playlist url: http://grooveshark.com/playlist/%s/%d" % (playlist_name, playlist_id)