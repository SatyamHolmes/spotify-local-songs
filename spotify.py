import requests as req
import argparse as ag
import os
import json
import sys
import time

tokenFile = 'token.json'

def get_parser():
    parser = ag.ArgumentParser(description="convert your song folder into a spotify playlist")
    parser.add_argument('path', type=str, help="path to the folder")
    parser.add_argument('--playlist', type=str, action='store', dest='playlist', required=False, default=None, help="Playlist name to use. Defauls to folder name")
    parser.add_argument('--genaccesstoken', action='store_true' , dest='genAccessToken', required=False, help="Generates access code")
    parser.add_argument('--preview', action='store_true', dest='preview', required=False, help="Just print the song list. Dont add to spotify")
    return parser

def get_config():
    config = 'config.json'
    if not os.path.isfile(config):
        print(f"config file not found at {config}")
        sys.exit(1)
    with open(config, 'r') as fp:
        data = json.load(fp)
    return data

def make_request(url, method, data, jsondata, headers, auth):
    out = None
    try:
        if method == 'POST':
            res = req.post(url, json=jsondata, data=data, auth=auth, headers=headers)
        elif method == 'GET':
            res = req.get(url, headers=headers, auth=auth)
        res.raise_for_status()
        out = res
    except req.HTTPError as err:
        print(f"HTTP error occured for {url}")
        print(err)
        print(err.response.text)
    except req.ConnectTimeout as err:
        print(f"Connection timed out for {url}")
    except req.ConnectionError as err:
        print(f"Unable to connect to {url}")
    except req.RequestException as err:
        print("Unexpected error occured")
        print(err)
        print(err.response.text)

    return out

def get_access_token():
    if os.path.isfile(tokenFile):
        with open(tokenFile, 'r') as fp:
            data = json.load(fp)
            currt = time.strftime('%s', time.gmtime())
            if int(currt) - int(data['time']) < 3600:
                return data['access_token']
            else:
                print("Access token has expired. Regenerating")
    else:
        print("Access token not present. Generating")

    return None

def gen_access_token(config):
    codeFile = 'code'

    if os.path.isfile(codeFile):
        with open(codeFile, 'r') as fp:
            code = fp.readline()
    else:
        code = input("Enter the auth req code: ")
    
    code = code.strip()
    api = "https://accounts.spotify.com/api/token"
    data = {'grant_type': "authorization_code", 'code': code, 'redirect_uri': config['redirect_uri']}
    auth = req.auth.HTTPBasicAuth(config['client_id'], config['client_secret'])
    headers = {"Content-Type": 'application/x-www-form-urlencoded'}

    res = make_request(api, 'POST', data, None, headers, auth)
    if res != None:
        res = json.loads(res.text)
        access_token = res['access_token']
        res['time'] = time.strftime('%s', time.gmtime())
        with open(tokenFile, 'w') as fp:
            fp.write(json.dumps(res))
            print(f"Token generated and saved to {tokenFile}")
        return access_token
    else:
        sys.exit(1)

def get_profile(access_token, config):
    url = "https://api.spotify.com/v1/me"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {access_token}"
    }
    auth = ()
    res = make_request(url, 'GET', None, None, headers, auth)
    return res.json()

def create_playlist(access_token, profile, name):
    url = f"https://api.spotify.com/v1/users/{profile['id']}/playlists"
    headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
            }
    data = {
            "name": name,
            "public": True
            }
    res = make_request(url, 'GET', None, None, headers, ())
    playlist_id = None
    if res == None:
        print(f"Unable to fetch user playlist")
        sys.exit(1)

    for item in res.json()['items']:
        if item['name'] == playlist_name:
            print(f"Playlist with name {name} already present. Using the same")
            playlist_id = item['id'] 
            break

    if playlist_id == None:
        res = make_request(url, 'POST', None, data, headers, ())
        if res == None:
            print(f"Failed to create playlist {name}")
            sys.exit(1)
        else:
            print(f"Playlist with name {name} created")
            playlist_id = res.json()['id']

    return playlist_id

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    config = get_config()

    if not os.path.isdir(args.path):
        print(f"dir {args.path} is not present or is not a directory") 
        sys.exit(1)

    playlist_name = args.playlist

    if playlist_name == None:
        playlist_name = os.path.normpath(args.path)[-1]

    access_token = get_access_token()
    if args.genAccessToken or access_token == None:
        access_token = gen_access_token(config)
    
    profile = get_profile(access_token, config)

    playlist_id = None

    if not args.preview:
        playlist_id = create_playlist(access_token, profile, playlist_name)

