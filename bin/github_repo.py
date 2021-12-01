import os
import json
import time
# import redis
import hashlib
import pathlib
import argparse
import datetime
import requests
import configparser
from pyail import PyAIL

from urllib.request import urlopen
from io import BytesIO
from zipfile import ZipFile

pathProg = pathlib.Path(__file__).parent.absolute()
uuid = "1"

## Config
config = configparser.ConfigParser()
config.read('../etc/config.cfg')

if 'general' in config:
    uuid = config['general']['uuid']

if 'github' in config:
    api_token = config['github']['api_token']

if 'ail' in config:
    ail_url = config['ail']['url']
    ail_key = config['ail']['apikey']

"""if 'redis' in config:
    r = redis.Redis(host=config['redis']['host'], port=config['redis']['port'], db=config['redis']['db'])
else:
    r = redis.Redis(host='localhost', port=6379, db=0)"""

pathRepo = os.path.join(pathProg, "Repo")
if 'repo' in config:
    if config['repo']['pathRepo']:
        pathRepo = config['repo']['pathRepo']


def download_and_unzip(url, extract_to=pathRepo):
    http_response = urlopen(url)
    zipfile = ZipFile(BytesIO(http_response.read()))
    zipfile.extractall(path=extract_to)

def pushToAil(file, json_api, nameFolder):
    f = open(file, "r", encoding="cp850")
    read_file = f.read()
    f.close()

    data = read_file
    default_encoding = 'UTF-8'

    pathList = list()
    head, tail = os.path.split(file)
    while tail != nameFolder:
        pathList.append(tail)
        head, tail = os.path.split(head)

    pathToFile = nameFolder

    for element in pathList[::-1]:
        pathToFile = os.path.join(pathToFile, element)

    meta = dict()
    meta["github_repo:path_file"] = str(pathToFile)
    meta["github_repo:file_size"] = os.path.getsize(file)

    meta["github_repo:id"] = str(json_api["id"])
    meta["github_repo:node_id"] = json_api["node_id"]
    meta["github_repo:name"] = json_api["full_name"]

    meta["github_repo:owner_login"] = json_api["owner"]["login"]
    meta["github_repo:owner_id"] = str(json_api["owner"]["id"])
    meta["github_repo:owner_node_id"] = json_api["owner"]["node_id"]

    meta["github_repo:datestamp"] = datetime.datetime.strptime(json_api["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
    meta["github_repo:timestamp"] = datetime.datetime.strptime(json_api["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M:%S")
    meta["github_repo:timezone"] = "UTC"

    source = "github_feeder"
    source_uuid = uuid


    json_test = {}
    json_test["data"] = data
    json_test["meta"] = meta

    with open(pathProg + "json_test.json", "a") as write_file:
        json.dump(json_test, write_file, indent=4)

    # pyail.feed_json_item(data, meta, source, source_uuid, default_encoding)


def exploration(folder, json_api, nameFolder):
    for content in os.listdir(folder):
        chemin = os.path.join(folder, content)
        if not os.path.isdir(chemin):
            hashFile = hashlib.sha1(open(chemin, 'rb').read()).hexdigest()
            pushToAil(chemin, json_api, nameFolder)
        else:
            exploration(chemin, json_api, nameFolder)

def api_process(json_api):
    if "message" in json_api:
        if "Not Found" in json_api["message"]:
            print(f"[-] Repo not found: {repo_name}")
            return True
        if "No commit found" in json_api["message"]:
            print(f"[-] Commit {commit} not found for: {repo_name}")
            return True
        if "API rate limit exceeded" in json_api["message"]:

            time_remain = datetime.datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset'])).strftime('%Y-%m-%d %H:%M:%S')
            time_remain = datetime.datetime.strptime(time_remain, "%Y-%m-%d %H:%M:%S")
            diff = abs(time_remain - datetime.datetime.now())

            print(f"\n\n[-] API rate limit exceeded, sleep for {diff}")
            time.sleep(diff.total_seconds() + 10)

            response = requests.get(f"https://api.github.com/repos/{user}/{repo_name}")
            json_api = json.loads(response.content)

            api_process(json_api)
            return False
        return True
    return False



parser = argparse.ArgumentParser()
parser.add_argument("list_repo", help="list of repo to analyse")
parser.add_argument("--nocache", help="disable store of archive", action="store_true")
args = parser.parse_args()

with open(args.list_repo, "r") as read_file:
    json_repo = json.load(read_file)

## Ail
"""try:
    pyail = PyAIL(ail_url, ail_key, ssl=False)
except Exception as e:
    # print(e)
    print("\n\n[-] Error during creation of AIL instance")
    sys.exit(0)"""


for repo in json_repo:
    user = repo["user"]
    repo_name = repo["repo_name"]
    commit = repo["commit"]
    branch = repo["branch"]

    ## Get the default branch
    response = requests.get(f"https://api.github.com/repos/{user}/{repo_name}")
    json_api = json.loads(response.content)

    if not api_process(json_api):
        if commit:
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{commit}")
        elif branch:
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{branch}")
        else:
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{json_api['default_branch']}")

        if not os.path.isdir(pathToDL):
            if commit:
                download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/{commit}.zip")
            elif branch:
                download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/refs/heads/{branch}.zip")
            else:
                download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/refs/heads/{json_api['default_branch']}.zip")

        head, tail = os.path.split(pathToDL)
        exploration(pathToDL, json_api, tail)