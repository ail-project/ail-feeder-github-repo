import os
import json
import time
import magic
import redis
import shutil
import hashlib
import pathlib
import argparse
import datetime
import requests
import configparser
from pyail import PyAIL

from urllib.request import urlopen
import urllib.error
from io import BytesIO
from zipfile import ZipFile

pathProg = pathlib.Path(__file__).parent.absolute()
uuid = "183f2812-db38-4935-b5da-ad03f94f118f"

## Config
config = configparser.ConfigParser()
config.read('../etc/ail-feeder-github-repo.cfg')

if 'general' in config:
    uuid = config['general']['uuid']

if 'github' in config:
    api_token = config['github']['api_token']

if 'cache' in config:
    cache_expire = config['cache']['expire']
else:
    cache_expire = 86400
    
if 'ail' in config:
    ail_url = config['ail']['url']
    ail_key = config['ail']['apikey']

if 'redis' in config:
    r = redis.Redis(host=config['redis']['host'], port=config['redis']['port'], db=config['redis']['db'])
else:
    r = redis.Redis(host='localhost', port=6379, db=0)

head, tail = os.path.split(pathProg)
pathRepo = os.path.join(head, "Repo")
if 'repo' in config:
    if config['repo']['pathRepo']:
        pathRepo = config['repo']['pathRepo']


## Function
def download_and_unzip(url, extract_to=pathRepo):
    try:
        http_response = urlopen(url)
    except urllib.error.HTTPError:
        return "[-] Not Found"
    zipfile = ZipFile(BytesIO(http_response.read()))
    zipfile.extractall(path=extract_to)

def pushToAil(file, json_api, nameFolder, extension):
    f = open(file, "r", encoding="utf-8")
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
    meta["github_repo:file_size"] = str(os.path.getsize(file))

    if extension:
        meta["github_repo:file_extention"] = extension

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

    if debug:
        with open(os.path.join(pathProg, "json_test.json"), "a") as write_file:
            json.dump(json_test, write_file, indent=4)
    else:
        pyail.feed_json_item(data, meta, source, source_uuid, default_encoding)


def exploration(folder, json_api, nameFolder, nocache, cpfile, cpPush):
    for content in os.listdir(folder):
        chemin = os.path.join(folder, content)
        if os.path.isfile(chemin):
            hashFile = hashlib.sha1(open(chemin, 'rb').read()).hexdigest()
            cpfile += 1 
            if not r.exists("file:{}".format(hashFile)) or nocache:
                if not nocache:
                    r.set("file:{}".format(hashFile), hashFile)
                    r.expire("file:{}".format(hashFile), cache_expire)

                type_file = magic.from_file(chemin, mime=True)

                # Push only text file
                if type_file and type_file.split("/")[0] == "text":
                    extension = ""
                    try:
                        extension = content.split(".")[1]
                    except:
                        pass
                    cpPush += 1
                    # print("Magic Type : {}".format(magic.from_file(chemin, mime=True)))
                    pushToAil(chemin, json_api, nameFolder, extension)
        else:
            cpfile, cpPush = exploration(chemin, json_api, nameFolder, nocache, cpfile, cpPush)

    return cpfile, cpPush


def api_process(json_api, headers, repo_name, commit):
    if "message" in json_api:
        if "Not Found" in json_api["message"]:
            print(f"[-] Repo not found: {repo_name}")
            return True
        if "No commit found" in json_api["message"]:
            print(f"[-] Commit {commit} not found for: {repo_name}")
            return True
        if "Bad credentials" in json_api["message"]:
            print("[-] Bad credentials for API")
            exit(-1)
        if "API rate limit exceeded" in json_api["message"]:

            time_remain = datetime.datetime.fromtimestamp(int(headers['X-RateLimit-Reset'])).strftime('%Y-%m-%d %H:%M:%S')
            time_remain = datetime.datetime.strptime(time_remain, "%Y-%m-%d %H:%M:%S")
            diff = abs(time_remain - datetime.datetime.now())

            print(f"\n\n[-] API rate limit exceeded, sleep for {diff}")
            time.sleep(diff.total_seconds() + 10)

            response = requests.get(f"https://api.github.com/repos/{user}/{repo_name}")
            json_api = json.loads(response.content)

            api_process(json_api, headers, repo_name, commit)
            return False
        return True
    return False



parser = argparse.ArgumentParser()
parser.add_argument("-l", "--list_repo", help="list of repo to analyse", required=True)
parser.add_argument("--nocache", help="disable store of repository", action="store_true")
parser.add_argument("-v", "--verbose", help="verbose, more display", action="store_true")
parser.add_argument("-d", "--debug", help="debug mode", action="store_true")
args = parser.parse_args()

debug = args.debug
verbose = args.verbose

with open(args.list_repo, "r") as read_file:
    json_repo = json.load(read_file)

if not os.path.isdir(pathRepo):
    os.mkdir(pathRepo)

## Ail
if not debug:
    try:
        pyail = PyAIL(ail_url, ail_key, ssl=False)
    except Exception as e:
        # print(e)
        print("\n\n[-] Error during creation of AIL instance")
        exit(0)


for repo in json_repo:
    user = repo["user"]
    repo_name = repo["repo_name"]
    commit = repo["commit"]
    branch = repo["branch"]

    cpfile = 0
    cpPush = 0

    ## Get the default branch and Check if the repo is up
    header = {'Authorization': f'token {api_token}'}

    try:
        response = requests.get(f"https://api.github.com/repos/{user}/{repo_name}", headers=header)
    except requests.exceptions.ConnectionError:
        print("[-] Connection Error to GHArchive")
        exit(-1)

    json_api = json.loads(response.content)

    if not api_process(json_api, response.headers, repo_name, commit):
        if commit:
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{commit}")
        elif branch:
            # Branch can have / in is name and after unzip became -
            branchTemp = branch.replace("/", "-")
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{branchTemp}")
        else:
            pathToDL = os.path.join(pathRepo, f"{repo_name}-{json_api['default_branch']}")

        if not os.path.isdir(pathToDL):
            print("[+] Downloading...")
            if commit:
                error = download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/{commit}.zip")
            elif branch:
                error = download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/refs/heads/{branch}.zip")
            else:
                error = download_and_unzip(f"https://github.com/{user}/{repo_name}/archive/refs/heads/{json_api['default_branch']}.zip")
            
            # Branch or commit not exist
            if error:
                print(f"{error} for {repo_name}")
                continue

        print(f"[+] Exploration of Repository: {repo_name}")
        head, tail = os.path.split(pathToDL)
        cpfile, cpPush = exploration(pathToDL, json_api, tail, args.nocache, cpfile, cpPush)

        if verbose:
            print(f"\t[+] Numbers of file in repo: {cpfile}")
            print(f"\t[+] Numbers of file push to Ail: {cpPush}")
    else:
        if debug:
            print(response.text)

    if args.nocache:
        try:
            shutil.rmtree(pathRepo)
        except Exception as e:
            if not debug:
                pass
            else:
                print(e)