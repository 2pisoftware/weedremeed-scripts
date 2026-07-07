import sys
import os
from argparse import ArgumentParser
import pathlib
from io import DEFAULT_BUFFER_SIZE
import mimetypes
import math
import hashlib
import httpx
import base64
import time

import WR_lib_uploader

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import create_collection
from weedremeed_client.models import CollectionCreate, Collection

parser = ArgumentParser(
    description="Utility for uploading directories to Weedremeed.",
    epilog="IDs can be found in the URL while viewing the target object. The 'TOKEN' environment variable must be set to the developer API key in the developer console.",
)
parser.add_argument(
    "-o", "--collection", dest="collection_id", type=int, help="Output collection ID"
)
parser.add_argument(
    "-n",
    "--name",
    dest="name",
    type=str,
    help="Name of collection to be created if ID not specified",
)
parser.add_argument(
    "-p",
    "--project",
    dest="project_id",
    type=int,
    required=True,
    help="Output project ID",
)
parser.add_argument(
    "-i",
    "--input",
    dest="directory",
    type=pathlib.Path,
    required=True,
    help="Path of directory to upload",
)

args = parser.parse_args()


def raise_for_status(response):
    response.raise_for_status()


BASE_URL = "https://portal.weedremeed.com.au"
token = os.environ["TOKEN"]
client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
)

CHUNK_SIZE = 1024 * 1024 * 5
MAX_RETRIES = 5


collection_id = args.collection_id

if not collection_id:
    collection_id = WR_lib_uploader.createNewCollection(
        client=client, name=(args.name or args.directory.name), description="Uploaded via CLI", project_id=args.project_id
    )

print("Destination: " + BASE_URL + "/weedremeed-collection/view/" + str(collection_id))

total = len(os.listdir(args.directory))

with os.scandir(args.directory) as it:
    for inx, entry in enumerate(it):
        print("Uploading " + str(inx + 1) + " of " + str(total + 1))

        WR_lib_uploader.uploadFile(client=client, entry_name=entry.name, entry_path=entry.path, collection_id=collection_id)
           

print(
    "Done. View your collection here: "
    + BASE_URL
    + "/weedremeed-collection/view/"
    + str(collection_id)
)
