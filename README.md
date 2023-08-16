# AIL - feeder from Github Repository

This AIL feeder is a generic software to extract informations from Github Repository, collect and feed AIL via AIL ReST API.





# Usage

~~~shell
dacru@dacru:~/git/ail-feeder-github-repo/bin$ python3 github_repo.py --help  
usage: github_repo.py [-h] -l LIST_REPO [--nocache] [-v] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -l LIST_REPO, --list_repo LIST_REPO
                        list of repo to analyse
  --nocache             disable store of repository
  -v, --verbose         verbose, more display
  -d, --debug           debug mode


~~~





# JSON output format to AIL

- `source` is the name of the AIL feeder module
- `source-uuid` is the UUID of the feeder (unique per feeder)
- `data` is data in file
- `meta` is the generic field where feeder can add the metadata collected



Using the AIL API, `data` will be compress in gzip format and encode with base64 procedure. Then a new field will created, `data-sha256` who will be the result of sha256 on data after treatment.



# (main) Requirements

- [PyAIL](https://github.com/ail-project/PyAIL)

- [magic](https://github.com/ahupp/python-magic)

  - For magic, according to your OS, some additional stuff need to be download.

    - For Debian/Ubuntu:

    ```
    sudo apt-get install libmagic1
    ```

    - For Windows

    ```
    pip install python-magic-bin
    ```

- [redis](https://github.com/redis/redis-py)





## ail_feeder_github_repo

~~~json
{
    "data": "[general]\nuuid = 183f2812-db38-4935-b5da-ad03f94f118f\n\n[github]\napi_token = <YOURAPIKEY>\n\n[cache]\nexpire = 86400\n\n[ail]\nurl = https://127.0.0.1:7020/api/v1/import/json/item\napikey = <YOURAPIKEY> \n\n[redis]\nhost = 127.0.0.1\nport = 6379\ndb = 0\n\n[repo]\npathRepo = ",
    "meta": {
        "github_repo:path_file": "ail-feeder-github-repo-main/etc/config.cfg",
        "github_repo:file_size": "260",
        "github_repo:file_extention": "cfg",
        "github_repo:id": "433775806",
        "github_repo:node_id": "R_kgDOGdrkvg",
        "github_repo:name": "ail-project/ail-feeder-github-repo",
        "github_repo:owner_login": "ail-project",
        "github_repo:owner_id": "62389074",
        "github_repo:owner_node_id": "MDEyOk9yZ2FuaXphdGlvbjYyMzg5MDc0",
        "github_repo:datestamp": "2021-12-01",
        "github_repo:timestamp": "10:10:19",
        "github_repo:timezone": "UTC"
    }
}
~~~





## Format list to process repository

~~~json
[
    {
        "user": "ail-project",
        "repo_name": "ail-feeder-github-repo",
        "commit": "",
        "branch": ""
    },
    {
        "user": "ahupp",
        "repo_name": "python-magic",
        "commit": "",
        "branch": "libmagic-compat"
    }
] 
~~~



## Download all repository from an organization

If no `repo_name` is given, then the user is consider as an organization and all of is repository will be download

~~~
[
	{
        "user": "ail-project",
        "repo_name": "",
        "commit": "",
        "branch": ""
    }
]
~~~


## License


This software is licensed under [GNU Affero General Public License version 3](http://www.gnu.org/licenses/agpl-3.0.html)

Copyright (C) 2021-2023 CIRCL - Computer Incident Response Center Luxembourg

Copyright (C) 2021-2023 David Cruciani


