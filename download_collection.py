import sys
import os
from argparse import ArgumentParser
import pathlib
import httpx

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import get_a_collections_content, get_collection
from weedremeed_client.models import (
    Collection,
)
from weedremeed_client.models.get_a_collections_content_get_a_collections_content_ok import (
    GetACollectionsContentGetACollectionsContentOk,
)

parser = ArgumentParser(
    description="Utility for downloading collections from Weedremeed",
    epilog="IDs can be found in the URL while viewing the target object. The 'TOKEN' environment variable must be set to the developer API key in the developer console.",
)

parser.add_argument(
    "-i",
    "--collection",
    dest="collection_id",
    type=int,
    help="Collection ID to download",
    required=True,
)

parser.add_argument(
    "-o",
    "--output",
    dest="output",
    type=pathlib.Path,
    help="Output path",
    required=True,
)

args = parser.parse_args()


def raise_for_status(response):
    response.raise_for_status()


BASE_URL = "https://test.portal.weedremeed.com.au"
token = os.environ["TOKEN"]
client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
)

target = get_collection.sync(client=client, collection_id=args.collection_id)

if not isinstance(target, Collection):
    print("Collection does not exist")
    sys.exit(1)

print("Downloading collection '" + target.title + "'")
print("Total attachments: " + str(target.size))

content = get_a_collections_content.sync(client=client, collection_id=target.id)

if not isinstance(content, GetACollectionsContentGetACollectionsContentOk):
    print(content)
    sys.exit(1)

out_dir = args.output
if not os.path.exists(out_dir):
    os.makedirs(out_dir)

done = 1
while True:
    for file in content.files:
        done += 1
        if os.path.isfile(out_dir / file.filename):
            continue

        print(
            "Downloading '" + file.filename + "' " + str(done) + "/" + str(target.size)
        )
        r = httpx.get(file.url)
        with open(out_dir / file.filename, "wb") as f:
            f.write(r.content)

    if not content.next_:
        break

    content = get_a_collections_content.sync(
        client=client, collection_id=target.id, cursor=content.next_
    )

    if (
        not isinstance(content, GetACollectionsContentGetACollectionsContentOk)
        or not content.files
    ):
        break

print("All files downloaded successfully")
