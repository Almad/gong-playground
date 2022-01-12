from getpass import getpass
import json
import os, os.path
from pathlib import Path

import requests
from keyring import get_keyring, get_password

fromDateTime = "2021-09-01T00:00:00-08:00"
toDateTime = "2021-12-31T23:59:59-08:00"
workspace = {"workspaceId": 2686967882418498600}
dateFilter = {"fromDateTime": fromDateTime, "toDateTime": toDateTime}
headers = {"Accept": "application/json", "Content-Type": "application/json"}

# MAC OS X only and you have to deal with it! (PRs welcome)
PRIVATE_FOLDER = Path(os.path.expanduser("~")) / "Library/Application Support/Gong\ Transcripts"
CONFIG_FILE = PRIVATE_FOLDER / "config.json"

APPLICATION_KEYRING_NAME = "co.stephenwalker.gong.transcripts"


def get_config():
    keyring = get_keyring()
    try:
        config = json.loads(CONFIG_FILE.read_text())
        config["client_secret"] = keyring.get_password(
            APPLICATION_KEYRING_NAME, config["client_id"]
        )
    except FileNotFoundError:
        client_id = input("Enter id: ").strip()
        client_secret = getpass("Enter secret: ").strip()

        keyring.set_password(APPLICATION_KEYRING_NAME, client_id, client_secret)

        if not os.path.exists(PRIVATE_FOLDER):
            os.makedirs(PRIVATE_FOLDER)

        CONFIG_FILE.write_text(json.dumps(dict(client_id=client_id)))
        config = {"client_id": client_id, "client_secret": client_secret}

    return config



def get_transcripts():
    config = get_config()
    KEY = config["client_id"]
    SECRET = config['client_secret']

    callLogs = requests.post('https://api.gong.io/v2/calls/transcript',
                            headers=headers,
                            auth=(KEY, SECRET),
                            json={"filter": {**workspace, **dateFilter}}).json()

    all_logs_cnt = callLogs['records']['totalRecords']
    params = {
        "count": "100",
        "cursor": callLogs['records']['cursor']
    }


    with requests.Session() as req:
        all_transcripts = []
        print('All transcripts: ', all_logs_cnt)
        while all_logs_cnt != len(all_transcripts):
            print(len(all_transcripts))
            callLogs = req.post('https://api.gong.io/v2/calls/transcript',
                                     headers=headers,
                                     auth=(KEY, SECRET),
                                     json={"filter": {**workspace, **dateFilter}, "cursor": params['cursor']}).json()
            params['cursor'] = callLogs['records']['cursor'] if callLogs['records']['currentPageSize'] == 100 else None

            all_transcripts.extend(callLogs['callTranscripts'])
    
    return(all_transcripts)

def main():
    get_transcripts()

if __name__ == '__main__':
    main()