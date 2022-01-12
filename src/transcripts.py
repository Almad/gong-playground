from datetime import datetime, timezone
from getpass import getpass
import json
import os, os.path
from pathlib import Path

from dateutil.relativedelta import relativedelta
from keyring import get_keyring, get_password
import requests

DATETIME_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
DOWNLOAD_INTERVAL = relativedelta(months=3)

DEFAULT_WORKSPACE_ID = 2686967882418498600
WORKSPACE_ID = int(os.environ.get("WORKSPACE_ID", DEFAULT_WORKSPACE_ID))

PAGE_SIZE = 100

fromDateTime = "2021-09-01T00:00:00-08:00"
toDateTime = "2021-12-31T23:59:59-08:00"

workspace = {"workspaceId": 2686967882418498600}
dateFilter = {"fromDateTime": fromDateTime, "toDateTime": toDateTime}
headers = {"Accept": "application/json", "Content-Type": "application/json"}

TRANSCRIPT_ENDPOINT = "https://api.gong.io/v2/calls/transcript"

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


def get_transcript_page(config, cursor=None):
    KEY = config["client_id"]
    SECRET = config['client_secret']

    filter_json = {
        'workspace': WORKSPACE_ID,
        "fromDateTime": DATETIME_START.isoformat(),
        "toDateTime": (DATETIME_START + DOWNLOAD_INTERVAL).isoformat(),
        "count": PAGE_SIZE
    }

    if cursor:
        filter_json['cursor'] = cursor

    return requests.post(TRANSCRIPT_ENDPOINT,
                            headers=headers,
                            auth=(KEY, SECRET),
                            json={"filter": {**filter_json}}).json()



def get_transcripts():
    config = get_config()

    last_page_size = PAGE_SIZE
    cursor = None
    transcripts = []

    while last_page_size == PAGE_SIZE:
        page_data = get_transcript_page(config, cursor)
        last_page_size = page_data['records']['currentPageSize']
        cursor = page_data['records']['cursor']

        transcripts = transcripts + page_data['callTranscripts']

    return transcripts

def main():
    transcripts = get_transcripts()

    print("Total transcripts downloaded: %s" % len(transcripts))
    print("Example transcript below")
    print(json.dumps(transcripts[0]))


if __name__ == '__main__':
    main()