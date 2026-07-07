import os
from argparse import ArgumentParser
import pathlib

import WR_lib_uploader

from weedremeed_client import AuthenticatedClient

parser = ArgumentParser(
    description="Upload a single file: you need a filename and a collection ID",
    epilog="The 'WR_TOKEN' must be set to the developer API key in the developer console.",
)

parser.add_argument(
    "-f",
    "--filepath",
    dest="file_path",
    type=pathlib.Path,
    help="Source File Path",
    required=True,
)

parser.add_argument(
    "-i",
    "--id",
    dest="dst_collection",
    type=str,
    help="Destination Collection ID",
    required=True,
)


args = parser.parse_args()


def raise_for_status(response):
    response.raise_for_status()


BASE_URL = "https://portal.weedremeed.com.au"
token = os.environ["WR_TOKEN"]
wr_client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
    verify_ssl=False
)

print("Delivering to collection: "+args.dst_collection)

if not os.path.isfile(args.file_path):
    print("File is no good!")
    exit()

print(
    "Uploading:",args.file_path,"as", os.path.basename(args.file_path)
)

WR_lib_uploader.uploadFile(client=wr_client, entry_name=os.path.basename(args.file_path), entry_path=args.file_path, collection_id=args.dst_collection)
           