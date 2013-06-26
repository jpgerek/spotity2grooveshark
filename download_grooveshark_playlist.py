#!/usr/bin/python

from groove import GrooveShark
import sys
import os
import time

DOWNLOADS_DIR = 'downloads'
DOWNLOAD_BW_LIMIT = 0  # KBs, 0 for no limit.
SONGS_DOWNLOADED_IN_A_ROW_LIMIT = 7
WAITING_TIME_MINS = 30

def params():
    print "%s <playlist id>" % sys.argv[0]
    exit(2)


def make_sure_dir_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

if len(sys.argv) != 2:
    params()

try:
    playlist_id = int(sys.argv[1])
except ValueError:
    params()

# Initialize the Groove() object
gs = GrooveShark()
# Setting bandwidth limit when downloading songs.
gs.set_download_bandwidth_limit(DOWNLOAD_BW_LIMIT)

# Get results as a SongList object
playlist = gs.get_playlist(playlist_id)
if 'Name' not in playlist:
    print "\tIt seems there is no a playlist with id: %d" % playlist_id
    exit(2)
playlist_name = playlist['Name']
if len(playlist['Songs']) == 0:
    print "No songs found for the playlist id: %d" % playlist_id
    exit()
print "\nPlaylist: '%s' (%d)\n" % (playlist_name, len(playlist['Songs']))
downloaded_counter = 0
already_downloaded_counter = 0
songs_not_downloaded = []
for song_offset, song in enumerate(playlist['Songs']):
    song_number = song_offset + 1
    #- Wait some time after a certain amount of downloaded songs to avoid being banned -*/
    if downloaded_counter > 0 and (downloaded_counter % SONGS_DOWNLOADED_IN_A_ROW_LIMIT) == 0:
        wait_time_mins = WAITING_TIME_MINS
        print "\t\tLets wait %d minutes before downloading the next song to avoid getting blocked." % wait_time_mins
        time.sleep(wait_time_mins*60)
    album_name = song['AlbumName'] if song['AlbumName'] != '' else 'no-album'
    print " %d: %s - %s - %s" % (song_number, song['Name'], song['AlbumName'], song['ArtistName'])
    dir = "%s/%s/%s/%s" % (DOWNLOADS_DIR, playlist_name, song['ArtistName'].replace('/', ' - '), album_name)
    make_sure_dir_exists(dir)
    #- Retry loop -#
    max_retries = 5
    for attempt in xrange(max_retries):
        print "\tDownload attempt: %d." % (attempt+1)
        download_result = gs.download_song(song, dir)
        if download_result == gs.SONG_ALREADY_DOWNLOADED:
            already_downloaded_counter += 1
            print "\t\tAlready downloaded. %d" % already_downloaded_counter
        elif download_result == gs.STREAM_RETRIEVAL_BLOCKED:
            waiting_minutes = WAITING_TIME_MINS * (attempt+1) # minutes
            print "\t\tGrooveshark is temporaly blocking you, lets wait %d minutes and retry." % waiting_minutes
            time.sleep(waiting_minutes*60)
            #- Retrying -#
            continue
        else:
            #- Download ok -#
            downloaded_counter += 1
            print "\t\tDownloaded. %d" % downloaded_counter
        #- Exiting the loop -#
        break
    else:
         #- All the retries were attempted, lets stop for a while -#
        songs_not_downloaded.append((song['SongID'], song['Name'], song['ArtistName'], song['AlbumName']))
        print "\t\tIt seems Grooveshark is blocking you for a long time, some times the block is per song so lets try the next song."           
#- Printing results stats -#
print "Playlist songs: %d." % len(playlist['Songs'])
print "Not downloaded: %d." % len(songs_not_downloaded)
print "Downloaded: %d." % downloaded_counter
print "Already downloaded: %d." % already_downloaded_counter