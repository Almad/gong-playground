from datetime import datetime, timezone
from getpass import getpass
import json
from math import ceil
import os, os.path
from pathlib import Path
import sys

from dateutil.relativedelta import relativedelta
from keyring import get_keyring, get_password
import requests

DATETIME_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
DOWNLOAD_INTERVAL = relativedelta(months=3)
# DOWNLOAD_INTERVAL = relativedelta(days=10)

VERBOSE = "-v" in sys.argv

DEFAULT_WORKSPACE_ID = 2686967882418498600
WORKSPACE_ID = int(os.environ.get("WORKSPACE_ID", DEFAULT_WORKSPACE_ID))

TRANSCRIPT_ENDPOINT = "https://api.gong.io/v2/calls/transcript"

# MAC OS X only and you have to deal with it! (PRs welcome)
PRIVATE_FOLDER = (
    Path(os.path.expanduser("~")) / "Library/Application Support/Gong\ Transcripts"
)
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
    SECRET = config["client_secret"]

    filter_json = {
        "filter": {
            "workspace": WORKSPACE_ID,
            "fromDateTime": DATETIME_START.isoformat(),
            "toDateTime": (DATETIME_START + DOWNLOAD_INTERVAL).isoformat(),
        }
    }

    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    if cursor:
        filter_json["cursor"] = cursor

    return requests.post(
        TRANSCRIPT_ENDPOINT,
        headers=headers,
        auth=(KEY, SECRET),
        json=filter_json,
    ).json()


def get_transcripts():
    config = get_config()

    total_records = 100 * 100
    cursor = None
    transcripts = []

    while len(transcripts) < total_records:
        page_data = get_transcript_page(config, cursor)

        cursor = page_data["records"].get("cursor", None)
        total_records = page_data["records"]["totalRecords"]

        transcripts = transcripts + page_data["callTranscripts"]

        if VERBOSE:
            print(
                f"Page {page_data['records']['currentPageNumber']} downloaded ({len(transcripts)} / {total_records})"
            )

    return transcripts


def main():
    transcripts = get_transcripts()

    if VERBOSE:
        print("Total transcripts downloaded: %s" % len(transcripts))
        # print("Example transcript below")
        # print(json.dumps(transcripts[0], indent=2))


if __name__ == "__main__":
    main()
