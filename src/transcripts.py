from datetime import datetime, timezone
from getpass import getpass
import json
from math import ceil
import os, os.path
from pathlib import Path
import sys
from tempfile import mkdtemp

from dateutil.relativedelta import relativedelta
from keyring import get_keyring, get_password
import requests

# Must be first day of a month
DATETIME_START = datetime(2021, 9, 1, tzinfo=timezone.utc)
NO_OF_MONTHS_TO_DOWNLOAD = 3

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


def get_transcript_page(config, start_date, end_date, cursor=None):
    KEY = config["client_id"]
    SECRET = config["client_secret"]

    filter_json = {
        "filter": {
            "workspace": WORKSPACE_ID,
            "fromDateTime": start_date.isoformat(),
            "toDateTime": end_date.isoformat(),
        }
    }

    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    if cursor:
        filter_json["cursor"] = cursor

    res = requests.post(
        TRANSCRIPT_ENDPOINT,
        headers=headers,
        auth=(KEY, SECRET),
        json=filter_json,
    )

    if res.status_code != 200:
        raise ValueError(f"Error code {res.status_code} retrieved: \n{res.json()}")

    return res.json()


def get_transcripts(start_date, end_date):
    config = get_config()

    total_records = 100 * 100
    cursor = None
    transcripts = []

    while len(transcripts) < total_records:
        page_data = get_transcript_page(config, start_date, end_date, cursor)

        cursor = page_data["records"].get("cursor", None)
        total_records = page_data["records"]["totalRecords"]

        transcripts = transcripts + page_data["callTranscripts"]

        if VERBOSE:
            print(
                f"Page {page_data['records']['currentPageNumber']} downloaded ({len(transcripts)} / {total_records})"
            )

    return transcripts


def get_transcripts_content(transcripts):
    return "\n\n".join(
        [
            "".join(
                [
                    "".join([sentence["text"] for sentence in transcript["sentences"]])
                    for transcript in call_transcript["transcript"]
                ]
            )
            for call_transcript in transcripts
        ]
    )


def write_transcripts(output_directory, transcripts, start_date):
    file_name = f"{start_date.strftime('%Y-%m')}.txt"
    file_path = os.path.join(output_directory, file_name)

    with open(file_path, "w") as f:
        f.write(get_transcripts_content(transcripts))


def main():
    total_transcripts = 0

    output_directory = mkdtemp(prefix="gong-transcripts")

    if VERBOSE:
        print(f"Downloading transcripts into {output_directory}")

    for i in range(0, NO_OF_MONTHS_TO_DOWNLOAD):
        start_date = DATETIME_START
        if i > 0:
            start_date = start_date + relativedelta(months=+i)
        end_date = (start_date + relativedelta(months=1)) - relativedelta(seconds=1)

        if VERBOSE:
            print(
                f"Downloading data from date {start_date.isoformat()} to {end_date.isoformat()}"
            )

        transcripts = get_transcripts(start_date=start_date, end_date=end_date)

        total_transcripts += len(transcripts)

        write_transcripts(output_directory, transcripts, start_date)

    if VERBOSE:
        print(f"Total transcripts downloaded: {total_transcripts}")
        # print("Example transcript below")
        # print(json.dumps(transcripts[0], indent=2))

    print(f"Transcripts can be found in {output_directory}")


if __name__ == "__main__":
    main()
