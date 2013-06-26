#!/usr/bin/python

from groove import GrooveShark
import sys
import os
import time
import helpers
import json

CACHE_DIR = 'cached'

DOWNLOADS_DIR = 'downloads'
DOWNLOAD_BW_LIMIT = 0  # KBs, 0 for no limit.
SONGS_DOWNLOADED_IN_A_ROW_LIMIT = 7
WAITING_TIME_MINS = 30

def make_sure_dir_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

#- Create cache dir if it doesn't exist -#
make_sure_dir_exists(CACHE_DIR)
make_sure_dir_exists(DOWNLOADS_DIR)

def params():
    print "%s <spotify_songs_file>" % sys.argv[0]
    exit(2)

def etree_to_dict(t):
    d = {t.tag : map(etree_to_dict, t.iterchildren())}
    d.update(('@' + k, v) for k, v in t.attrib.iteritems())
    return d

if len(sys.argv) != 2:
    params()

spotify_file = sys.argv[1]
if not os.path.exists(spotify_file):
    print "'%s' doesn't exist." % spotify_file

gs = GrooveShark()
# Setting bandwidth limit when downloading songs.
gs.set_download_bandwidth_limit(DOWNLOAD_BW_LIMIT)

not_found = []
found = []
found_but_not_downloaded = []
grooveshark_songs_list = []
downloaded_counter = 0
already_downloaded_counter = 0
for spotify_url in open(spotify_file):
    spotify_song = helpers.get_song_name(spotify_url)
    if spotify_song is None:
        print "No song info for %s" % spotify_url
        continue
    print "Spotify song: %s, %s, %s" % (spotify_song.get('song'), spotify_song.get('album'), spotify_song.get('artist'))
    #- Getting search result from cache or getting it and caching it -#
    cache_file = "%s/gs-result-%s" % (CACHE_DIR, helpers.md5(spotify_url))
    if os.path.exists(cache_file):
        f = open(cache_file)
        search_result = json.loads(f.read())
        f.close()
    else:
        #- Searching for a song's substitute in Grooveshark -#
        search_result = gs.search_song(spotify_song.get('song'), spotify_song.get('album'), spotify_song.get('artist'))
    #- Nothing found -#
    if len(search_result) == 0:
        not_found.append(spotify_song)
        print "\tNo result on Grooveshark."
        #- Caching empty search result -#
        f = open(cache_file, 'wb')
        f.write(json.dumps(search_result))
        f.close()
        continue
    #- Wait some time after a certain amount of downloaded songs to avoid being banned -*/
    if downloaded_counter > 0 and (downloaded_counter % SONGS_DOWNLOADED_IN_A_ROW_LIMIT) == 0:
        wait_time_minutes = WAITING_TIME_MINS
        print "\t\tLets wait %d minutes before downloading the next song to avoid getting blocked." % wait_time_minutes
        time.sleep(wait_time_minutes*60)
    #- Download the song -#
    grooveshark_song = search_result[0]
    grooveshark_songs_list.append(grooveshark_song)
    found.append((grooveshark_song['SongID'], grooveshark_song['SongName'], grooveshark_song['ArtistName'], grooveshark_song['AlbumName']))
    print "\tGrooveshark: %s, %s, %s, %d." % (grooveshark_song['SongName'], grooveshark_song['AlbumName'], grooveshark_song['ArtistName'], int(grooveshark_song['SongID']))
    album_name = grooveshark_song['AlbumName'] if grooveshark_song['AlbumName'] != '' else 'no-album'
    directory = "%s/%s/%s/%s" % (DOWNLOADS_DIR, spotify_file, gs.clean_file_path(grooveshark_song['ArtistName']), gs.clean_file_path(album_name))
    print "\tTrying download."
    #- Retry loop -#
    max_retries = 5
    for attempt in xrange(max_retries):
        download_result = gs.download_song(grooveshark_song, directory)
        if download_result == gs.SONG_ALREADY_DOWNLOADED:
            already_downloaded_counter += 1
            print "\t\tAlready downloaded. %d" % already_downloaded_counter
        elif download_result == gs.STREAM_RETRIEVAL_BLOCKED:
            waiting_minutes = WAITING_TIME_MINS * (attempt+1)#  minutes.
            print "\t\tGrooveshark is temporaly blocking you, lets wait %d minutes and retry." % waiting_minutes
            time.sleep(waiting_minutes*60)
            #- Searching again, some times old results don't work -#
            search_result = gs.search_song(spotify_song.get('song'), spotify_song.get('album'), spotify_song.get('artist'))
            grooveshark_song = search_result[0]
            #- Retrying -#
            continue
        else:
            #- Download ok -#
            downloaded_counter += 1
            print "\t\tDownloaded. %d" % downloaded_counter
        #- Caching search result -#
        f = open(cache_file, 'wb')
        f.write(json.dumps(search_result))
        f.close()
        #- Exiting the loop -#
        break
    else:
        #- All the retries were attempted, lets stop for a while -#
        found_but_not_downloaded.append((grooveshark_song['SongID'], grooveshark_song['SongName'], grooveshark_song['ArtistName'], grooveshark_song['AlbumName']))
        print "It seems Grooveshark is blocking you for a long time, some times the block is per song so lets try the next song."
#- Printing results stats -#
print "Not found: %d." % len(not_found)
print "Found: %d." % len(found)
print "Found but not downloaded: %d." % len(found_but_not_downloaded)
print "Downloaded: %d." % downloaded_counter
print "Already downloaded: %d." % already_downloaded_counter
