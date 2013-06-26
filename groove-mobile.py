#!/usr/bin/env python
import httplib
import StringIO
import hashlib
import uuid
import random
import string
import sys
import os
import subprocess
import gzip
import threading
import re
import time
if sys.version_info[1] >= 6:  import json
else: import simplejson as json

class GrooveSharkMobile:
    _useragent = "Grooveshark 2.6.6 rv:149 (iPhone; iPhone OS 5.0.1; en_EN)"
    _domain = "api.grooveshark.com" #The base URL of Grooveshark
    _base64_http_authorization = 'ZGV2ZWxvcGVyczpkM3ZEZW0wIQ=='
    _download_user_agent = "Grooveshark/149 CFNetwork/548.0.4 Darwin/11.0.0"
    _session_id = (''.join(random.choice(string.digits + string.letters[:6]) for x in range(32))).lower()
    _token = None
    _queue_id = None
    _queue_songs_counter = 0
    _username = None
    _password = None
    _user = None
    _config = None
    
    MOBILE = False # When is true it downloads a version of the song with lower bitrate.
    CONFIG_FILE = 'config.json'
    DOWNLOAD_BW_LIMIT = 75 # KB, 0 for no limit.
    
    CLIENT_TYPE_HTML = 0
    CLIENT_TYPE_JSQUEUE = 1
    ERROR_CODE_LOGIN_REQUIRED = 8
    ERROR_CODE_INVALID_TOKEN = 256
    SONG_ALREADY_DOWNLOADED = 2
    STREAM_RETRIEVAL_BLOCKED = 3
    STREAM_TYPE_VIP = 8
    
    #Setting the static header (country, session and uuid)
    _payload_header = {}
    _payload_header ["country"] = {}
    _payload_header ["country"]["CC1"] = 0
    _payload_header ["country"]["CC2"] = 0
    _payload_header ["country"]["CC3"] = 0
    _payload_header ["country"]["CC4"] = 0
    _payload_header ["country"]["ID"] = 1
    _payload_header ["country"]["IPR"] = 0
    _payload_header ["sessionID"] = _session_id
 
# POST /ws.php?search.songsUnfiltered&ios HTTP/1.1
#Host: api.grooveshark.com
#User-Agent: Grooveshark 2.6.6 rv:149 (iPhone; iPhone OS 5.0.1; es_ES)
#Content-Length: 147
#Referer: mobile
#Content-Type: text/json
#Cookie: PHPSESSID=10df1296b947ddf0724d88121a491fc2
#Accept-Encoding: gzip
#Authorization: Basic ZGV2ZWxvcGVyczpkM3ZEZW0wIQ==
#Connection: close

    _http_headers = {
                     'Host': _domain,
                     'User-Agent': _useragent,
                     'Referer': 'mobile',
                     'Content-Type': 'text/json',
                     'Cookie': 'PHPSESSID=%s' % _session_id,
                     'Accept-Encoding': 'gzip',
                     'Authorization': 'Basic %s' % _base64_http_authorization,
                     'Connection': 'close'
                     }
    
    def __init__(self):
        #-- Config --#
        
        #- Loding config from a yaml file if there is one -#}
        if os.path.exists(self.CONFIG_FILE):
            cf = open(self.CONFIG_FILE)
            try:
                config = json.load(cf)
            except Exception as ex:
                print "There was some error loading the config file, '%s'." % self.CONFIG_FILE
                exit(2)
            cf.close()
            #- Setting config data -#
            username = config['grooveshark_account']['username']
            password = config['grooveshark_account']['password']
            if username and password and username != '' and password != '':
                self._username = config['grooveshark_account']['username']
                self._password = config['grooveshark_account']['password']
  
    def _request(self, method, parameters, https=False):
        payload = {}
        payload["parameters"] = parameters
        payload["header"] = self._payload_header
        payload["method"] = method
        if https:
            conn = httplib.HTTPSConnection(self._domain)
        else:
            conn = httplib.HTTPConnection(self._domain)
        conn.request("POST", "/ws.php?" + method + '&ios', json.JSONEncoder().encode(payload), self._http_headers)
        try:
            raw_answer = gzip.GzipFile(fileobj=(StringIO.StringIO(conn.getresponse().read()))).read()
        except IOError as ex:
            #- Response is not gzip -#
            print conn.getresponse().read()
            raise ex
        if raw_answer == 'HTTPS required':
            print "The request demands HTTPS."
            print payload
            exit(2)
        elif raw_answer == '':
            print "Empty answer from the server, we've probably been banned temporaly."
            print payload
            exit(2)
        try:
            json_answer = json.JSONDecoder().decode(raw_answer)
        except Exception as ex:
            print payload
            print raw_answer
            raise ex
        if 'result' not in json_answer:
            print json_answer
            exit()
            fault_code = json_answer['fault']['code'] 
            if fault_code == self.ERROR_CODE_LOGIN_REQUIRED:
                print "Authentication is required."
                auth_result = self.authenticate() 
                if auth_result['authToken'] is False:
                    print "Error authenticating."
                    exit(2)
                print "Succesful authentication."
                self._user = auth_result
                return self._request(method, parameters)
            elif fault_code == self.ERROR_CODE_INVALID_TOKEN:
                print "Invalid token error, forcing requesting a new one."
                time.sleep(1)
                #- Setting the token to None to force requesting a new one -#
                self._token = None
                return self._request(method, parameters)
            else:
                print "There was some error"
                print json_answer
                exit(2)
        return json_answer["result"]
                
    #Fetch a queueID (right now we randomly generate it)
    def get_queue_id(self):
        if self._queue_id is None:
            self._queue_id = random.randint(10000000000000000000000,99999999999999999999999) #For now this will do
        return self._queue_id
    
    def authenticate(self, username=None, password=None):
        username = username or self._username
        password = password or self._password
        while not username or username == '':
            self._username = username = raw_input("Type your username: ")
        while not password or password == '':
            self._password = password = raw_input("Type your password: ")
        parameters = {
                      'username': username,
                      'password': password
                      }
        auth_result = self._request("authenticateUser", parameters, https=True)
        if auth_result['authToken'] is False:
            return False
        return auth_result
    
    def get_playlist(self, playlist_id):
        parameters = {
                      'playlistID': playlist_id
                      }
        json_answer = self._request('getPlaylistByID', parameters)
        return json_answer
    
    def get_queue_song_list_from_song_ids(self, song_ids):
        method = "getQueueSongListFromSongIDs"
        parameters = {
                      'songIDs': map(lambda item: int(item), song_ids)
                      }
        json_answer = self._request(method, parameters)
        return json_answer
    
    #Process a search and return the result as a list.
    def get_results_from_search(self, query, page=1, limit=80):
        #{"method":"search.songsUnfiltered","header":{"sessionID":"10df1296b947ddf0724d88121a491fc2"},"parameters":{"page":1,"query":"9 crimes","limit":80}}
        parameters = {}
        parameters["page"] = page
        parameters["query"] = query 
        parameters["limit"] = limit
        json_answer = self._request("search.songsUnfiltered", parameters)
        print json_answer
        exit()
        songs = json_answer["result"]["Songs"]
        #- Ordering by popularity -# 
        songs.sort(lambda a, b: b['Popularity']-a['Popularity'])
        return songs 
    
    regex_remove_parenthesis = re.compile(r'(\(.*?\) ?)')
    regex_remove_square_brackets = re.compile(r'(\[.*?\] ?)')
    regex_remove_after_dash = re.compile(r'( *-.*?$)')
    def _clean_query_search(self, query_list):
        #- Remove parenthesis and
        return ', '.join(map(lambda item: self.regex_remove_square_brackets.sub('', self.regex_remove_after_dash.sub('', self.regex_remove_parenthesis.sub('', item))), query_list))
    
    def search_song(self, song_name, album_name, artist_name):
        #- Searching for song, album and artist -#
        query = "%s, %s, %s" % (song_name, album_name, artist_name)
#        print query
        result = self.get_results_from_search(query)
        if len(result) == 0:
            #- Cleaning query and searching again -#
            clean_query = self._clean_query_search([song_name, album_name, artist_name])
            if clean_query != query:
#                print clean_query
                result = self.get_results_from_search(clean_query) 
            if len(result) == 0:         
                #- Searching for song and artist -#
                query = "%s, %s" % (song_name, artist_name)
#                print query
                result = self.get_results_from_search(query)
                if len(result) == 0:
                    #- Cleaning query and searching again -#
                    clean_query = self._clean_query_search([song_name, artist_name])
                    if clean_query != query:
#                        print clean_query
                        result = self.get_results_from_search(clean_query) 
                    #- Searching just for song produces bad matches most of the time -#
#                    if len(result) == 0:
#                        #- Searching for song -#
#                        query = song_name
#                        print query
#                        result = self.get_results_from_search(query)
#                        if len(result) == 0:
#                            #- Cleaning query and searching again -#
#                            clean_query = self._clean_query_search([song_name])
#                            if clean_query != query:
#                                print clean_query
#                                result = self.get_results_from_search(clean_query)
#                            result = self.get_results_from_search(query)                            
        return result
    
    def create_playlist(self, name, song_ids, description=""):
        parameters = {
                      'playlistName': name,
                      'songIDs': map(lambda item: int(item), song_ids),
                      'playlistAbout': description
                      }
        json_answer = self._request('createPlaylist', parameters)
        return json_answer
    
    #Get all songs by a certain artist
    def artistGetSongsEx(self, id, isVerified):
        parameters = {
                      'artistID': id,
                      'isVerifiedOrPopuplar': isVerified
                      }
        return self._request("artistGetSongsEx", parameters)
    
    #Get the streamKey used to download the songs off of the servers.
    def get_stream_key_from_song_id(self, id):
        parameters = {}
        parameters["type"] = self.STREAM_TYPE_VIP
        parameters["mobile"] = self.MOBILE
        parameters["prefetch"] = False
        parameters["songID"] = id
        parameters["country"] = self._payload_header["country"]
        stream = self._request("getStreamKeyFromSongIDEx", parameters)
        if len(stream) == 0:
            #- This usually means grooveshark banned us-#
            return None
        return stream
     
    @classmethod
    def clean_file_path(cls, file_path):
        return file_path.replace('/', '-').replace('"', '').replace("'", "")
    
    def download_song(self, song, directory=False, overwrite_file_name=None):
        if overwrite_file_name:
            file_name = self.clean_file_path(overwrite_file_name + ".mp3")
        else:
            song_name = song['SongName'] if 'SongName' in song else song['Name']
            file_name = self.clean_file_path(song_name + ".mp3")
        if directory is False:
            file_full_path = file_name
        else:
            if not os.path.exists(directory):
                os.makedirs(directory)
            file_full_path = directory.rstrip('/') + '/' + file_name
        #- Checking if the file already exists -#
        if os.path.exists(file_full_path):
            return self.SONG_ALREADY_DOWNLOADED
        stream = self.get_stream_key_from_song_id(song['SongID'])
        if stream is None:
            return self.STREAM_RETRIEVAL_BLOCKED
        limit_rate = ''
        if self.DOWNLOAD_BW_LIMIT > 0:
            limit_rate = "--limit-rate=%dk" % self.DOWNLOAD_BW_LIMIT
        cmd = 'wget %s --user-agent="%s" --read-timeout=30 -O "%s" "http://%s/stream.php?stremKey=%s"' % (limit_rate, self._download_user_agent, file_full_path, stream["ip"], stream["streamKey"]) #Run wget to download the song
        payload = subprocess.Popen(cmd, shell=True)
        markTimer = threading.Timer(30 + random.randint(0,5), self.mark_stream_key_over_30_seconds, [song["SongID"], str(self.get_queue_id()), stream["ip"], stream["streamKey"]]) #Starts a timer that reports the song as being played for over 30-35 seconds. May not be needed.
        markTimer.start()
        #- This request are performed after the stream beggins to be downloaded -#
        self.mark_song_downloaded_ex(stream["ip"], song["SongID"], stream["streamKey"]) #This is the important part, hopefully this will stop grooveshark from banning us.
        self.mark_song_queue_song_played(song["SongID"], self.get_queue_id(), stream["ip"], stream["streamKey"])
        try:
            payload.wait() #Wait for wget to finish
        except KeyboardInterrupt as ex: #If we are interrupted by the user
            os.remove(file_full_path) #Delete the song
            print "\nDownload cancelled. File deleted."
            exit(2)
        markTimer.cancel()

    
    #Add a song to the browser queue, used to imitate a browser
    def add_song_to_queue(self, songObj, songQueueID, source = "user"):   
        # {"songIDsArtistIDs":[{"source":"user","songID":2075207,"songQueueSongID":90,"artistID":37799}],"songQueueID":"28167367421354715374330"}
        self._queue_songs_counter += 1 
        queueObj = {}
        queueObj["songID"] = int(songObj["SongID"])
        queueObj["artistID"] = int(songObj["ArtistID"])
        queueObj["source"] = source
        queueObj["songQueueSongID"] = self._queue_songs_counter
        parameters = {}
        parameters["songIDsArtistIDs"] = [queueObj]
        parameters["songQueueID"] = songQueueID
        json_answer = self._request("addSongsToQueue", parameters)
        return json_answer
    
    #Remove a song from the browser queue, used to imitate a browser, in conjunction with the one above.
    def removeSongFromQueue(self, songQueueID, userRemoved = True):
        self._queue_songs_counter -= 1
        parameters = {}
        parameters["songQueueID"] = songQueueID
        parameters["userRemoved"] = True
        parameters["songQueueSongIDs"]=[1]
        return self._request("removeSongsFromQueue", parameters)
    
    #Mark the song as being played more then 30 seconds, used if the download of a songs takes a long time.
    def mark_stream_key_over_30_seconds(self, songID, songQueueID, streamServer, streamKey):
        parameters = {}
        parameters["songQueueID"] = songQueueID
        parameters["streamServerID"] = streamServer
        parameters["songID"] = songID
        parameters["streamKey"] = streamKey
        parameters["songQueueSongID"] = self._queue_songs_counter
        return self._request("songMarkStreamKeyOver30Seconds", parameters)
   
    def mark_song_queue_song_played(self, songID, songQueueID, streamServer, streamKey):
        method = "markSongQueueSongPlayed"
        parameters = {}
        parameters["songQueueID"] = songQueueID
        parameters["streamServerID"] = streamServer
        parameters["songID"] = songID
        parameters["streamKey"] = streamKey
        parameters["songQueueSongID"] = self._queue_songs_counter
        return self._request(method, parameters)

      
    #Mark the song as downloaded, hopefully stopping us from getting banned.
    def mark_song_downloaded_ex(self, streamServer, songID, streamKey):
        parameters = {}
        parameters["streamServerID"] = streamServer
        parameters["songID"] = songID
        parameters["streamKey"] = streamKey
        return self._request("markSongDownloadedEx", parameters)
    
    def get_playlist_songs(self, playlist_id):
        parameters = {
                      'playlistID': playlist_id
                      }
        json_answer = self._request("playlistGetSongs", parameters)
        if 'Songs' not in json_answer:
            return []
        return json_answer['Songs']

#- Called directly from the command line -#
if __name__ == "__main__":
    gs = GrooveSharkMobile()
    input = raw_input("Search: ")
    m = 0
    #- Searching songs matching the input
    search_result = gs.get_results_from_search(input)
    #- Exiting if there were no results -#
    if len(search_result) == 0:
        print "No results found"
        exit()
    result_output = [('%s - "%s", "%s", "%s"' % (offset+1, song['SongName'], song['ArtistName'], song['AlbumName'])) for offset, song in enumerate(search_result[:10])]
    #- Printing results -#
    print '\n'.join(result_output) 
    while True:
        song_input = raw_input("Enter the song number you want to download or \"e\" to exit: ")
        if song_input == "e":
            exit() #Exit if choice is empty or q
        try:
            song_offset = int(song_input)-1
            break
        except ValueError:
            #- Not a number case -#
            continue
    queue_id = gs.get_queue_id()
    song = search_result[song_offset]
    #- Add song to queue, it mimics browser's behavior -#
    gs.add_song_to_queue(song, queue_id)
    song_file_name = ' - '.join([song['ArtistName'], song['AlbumName'], song['SongName']]) 
    print "Trying to download song.."
    result = gs.download_song(song, overwrite_file_name=song_file_name)
    if result == gs.SONG_ALREADY_DOWNLOADED:
        print "The song was already downloaded."
    elif result == gs.STREAM_RETRIEVAL_BLOCKED:
        print "\tNot possible to download, your connection seem to be banned, try again after some time."
        exit(2)
    else:
        print "Song downloaded."