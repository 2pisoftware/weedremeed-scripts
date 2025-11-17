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

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import create_collection
from weedremeed_client.models import CollectionCreate, Collection
from weedremeed_client.api.collections import upload_file
from weedremeed_client.api.uploads import register_upload_part, mark_an_upload_as_done
from weedremeed_client.models.register_upload_part_body import RegisterUploadPartBody
from weedremeed_client.models.upload_file_body import UploadFileBody
from weedremeed_client.models.upload_file_upload_file_ok import UploadFileUploadFileOk
from weedremeed_client.models.register_upload_part_register_upload_part_ok import (
    RegisterUploadPartRegisterUploadPartOk,
)

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


BASE_URL = "https://test.portal.weedremeed.com.au"
token = os.environ["TOKEN"]
client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
)

CHUNK_SIZE = 1024 * 1024 * 5
MAX_RETRIES = 5


def createNewCollection(name: str, project_id: str):
    print("Collection not specified, creating one")

    ret = create_collection.sync(
        client=client,
        body=CollectionCreate.from_dict(
            {"title": name, "project_id": project_id, "description": "Uploaded via CLI"}
        ),
    )

    if not isinstance(ret, Collection):
        print(ret)
        sys.exit(1)

    return ret.id


collection_id = args.collection_id

if not collection_id:
    collection_id = createNewCollection(
        args.name or args.directory.name, args.project_id
    )

print("Destination: " + BASE_URL + "/weedremeed-collection/view/" + str(collection_id))


def uploadChunkRetry(upload_id: str, chunk: bytes, chunkId: int):
    for i in range(MAX_RETRIES):
        try:
            uploadChunk(upload_id, chunk, chunkId)
            return
        except httpx.HTTPError:
            time.sleep(0.2 * (5 * i))
            print("Upload failed... retrying " + str(i + 1) + "/" + str(MAX_RETRIES))
            continue

    print("Aborted")
    sys.exit(1)


def uploadChunk(upload_id: str, chunk: bytes, chunkId: int):
    md5Hash = base64.b64encode(hashlib.md5(chunk).digest()).decode()

    part = register_upload_part.sync(
        client=client,
        body=RegisterUploadPartBody.from_dict(
            {
                "id": upload_id,
                "part": chunkId,
                "length": len(chunk),
                "md5": md5Hash,
            }
        ),
    )

    if not isinstance(part, RegisterUploadPartRegisterUploadPartOk):
        print(part)
        sys.exit(1)

    httpx.put(
        part.endpoint, content=chunk, headers={"Content-MD5": md5Hash}
    ).raise_for_status()


def uploadFile(entry: os.DirEntry[str]):
    stat = entry.stat()

    upload = upload_file.sync(
        client=client,
        collection_id=collection_id,
        body=UploadFileBody.from_dict(
            {
                "filename": entry.name,
                "mime": mimetypes.guess_type(entry.path)[0],
                "size": stat.st_size,
            }
        ),
    )

    if not isinstance(upload, UploadFileUploadFileOk):
        print(upload)
        sys.exit(1)

    # for progress indicator?
    NUM_CHUNKS = math.ceil(stat.st_size / CHUNK_SIZE)
    chunkId = 1

    with open(entry.path, "rb") as stream:
        chunk = bytearray()
        while read := stream.read(DEFAULT_BUFFER_SIZE):
            chunk += bytearray(read)

            if len(chunk) >= CHUNK_SIZE:
                # our chunk is the length we want
                # upload it now

                uploadChunkRetry(upload.id, bytes(chunk), chunkId)

                chunkId += 1

                chunk = bytearray()

    if len(chunk) > 0:
        uploadChunkRetry(upload.id, bytes(chunk), chunkId)

    # uploads done
    # mark it as such

    mark_an_upload_as_done.sync(client=client, upload_id=upload.id)


total = len(os.listdir(args.directory))

with os.scandir(args.directory) as it:
    for inx, entry in enumerate(it):
        if (inx % (total / 10) == 0) or total < 20:
            print("Uploading " + str(inx + 1) + " of " + str(total + 1))

        uploadFile(entry)

print(
    "Done. View your collection here: "
    + BASE_URL
    + "/weedremeed-collection/view/"
    + str(collection_id)
)
