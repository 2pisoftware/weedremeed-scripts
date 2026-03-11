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
from weedremeed_client.api.projects import get_project
from weedremeed_client.models.project import Project

parser = ArgumentParser(
    description="Utility for downloading collections from Weedremeed",
    epilog="IDs can be found in the URL while viewing the target object. The 'TOKEN' environment variable must be set to the developer API key in the developer console.",
)

parser.add_argument(
    "-i",
    "--project",
    dest="project_id",
    type=int,
    help="Project ID to download",
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

# out_base_dir = args.output
# if not os.path.exists(out_base_dir):
#     os.makedirs(out_base_dir)

project = get_project.sync(client=client, project_id=args.project_id)

if (not isinstance(project, Project)):
    print(project)
    sys.exit(1)

done = 1
for collection in project.collections:
    done = 1
    
    if collection.type_ != "Upload" and collection.type_ != "Empty":
        print("Skipping workflow output collection '" + collection.title + "'")
        continue

    print("Downloading collection '" + collection.title + "'")
    print("Total attachments: " + str(collection.size))

    content = get_a_collections_content.sync(client=client, collection_id=collection.id)
    
    if not isinstance(content, GetACollectionsContentGetACollectionsContentOk):
        print(content)
        sys.exit(1)

    while True:
        for file in content.files:
            done +=1

            out_dir = args.output / str(project.id) / str(collection.id)

            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            if os.path.isfile(out_dir / file.filename):
                continue

            print(
                "Downloading '" + file.filename + "' " + str(done) + "/" + str(collection.size)
            )

            r = httpx.get(file.url)
            with open(out_dir / file.filename, "wb") as f:
                f.write(r.content)

        if not content.next_:
            break

        content = get_a_collections_content.sync(client=client, collection_id=collection.id, cursor=content.next_)

        if (not isinstance(content, GetACollectionsContentGetACollectionsContentOk) or not content.files):
            break