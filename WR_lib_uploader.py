import httpx
import time
import base64
import os
import mimetypes
import math
from io import DEFAULT_BUFFER_SIZE
import hashlib
# from argparse import ArgumentParser
# import pathlib

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import upload_file, get_collection, create_collection
from weedremeed_client.models import CollectionCreate, Collection
from weedremeed_client.models.upload_file_body import UploadFileBody
from weedremeed_client.models.upload_file_upload_file_ok import UploadFileUploadFileOk
from weedremeed_client.api.uploads import register_upload_part, mark_an_upload_as_done
from weedremeed_client.models.register_upload_part_body import RegisterUploadPartBody
from weedremeed_client.models.register_upload_part_register_upload_part_ok import RegisterUploadPartRegisterUploadPartOk

# ---------------------------
# Customised tooling in the manner of:
# https://gitlab.internal.2pisoftware.com/customers/CISS/weedremeed/weedremeed-scripts/-/blob/main/upload_directory.py?ref_type=heads
# ---------------------------

CHUNK_SIZE = 1024 * 1024 * 5
MAX_RETRIES = 5

def raise_for_status(response):
    response.raise_for_status()

def uploadChunkRetry(client: AuthenticatedClient, upload_id: str, chunk: bytes, chunkId: int):
    for i in range(MAX_RETRIES):
        try:
            return_state = uploadChunk(client, upload_id, chunk, chunkId)
            return return_state
        except httpx.HTTPError:
            time.sleep(0.2 * (5 * i))
            print("Upload failed... retrying " + str(i + 1) + "/" + str(MAX_RETRIES))
            continue

    print("Upload Exhausted Retries! Aborted...")
    return False


def uploadChunk(client: AuthenticatedClient, upload_id: str, chunk: bytes, chunkId: int):
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
        return False

    httpx.put(
        part.endpoint, content=chunk, headers={"Content-MD5": md5Hash}
    ).raise_for_status()

    return True


def getFileMd5(file_path):
    with open(entry.path, "rb") as f:
        return hashlib.file_digest(f, "md5")


def uploadFile(client: AuthenticatedClient, entry_name: str, entry_path: str, collection_id: str):
    stat = os.stat(entry_path)
    file_md5 = getFileMd5(entry_path)
    
    upload = upload_file.sync(
        client=client,
        collection_id=collection_id,
        body=UploadFileBody.from_dict(
            {
                "filename": entry_name,
                "mime": mimetypes.guess_type(entry_path)[0] or "application/octet-stream",
                "size": stat.st_size,
                "md5": file_md5
            }
        ),
    )
    
    return_state = isinstance(upload, UploadFileUploadFileOk)
    if not return_state:
        print(upload)
        return return_state

    # for progress indicator?
    NUM_CHUNKS = math.ceil(stat.st_size / CHUNK_SIZE)
    chunkId = 1

    with open(entry_path, "rb") as stream:
        chunk = bytearray()
        while read := stream.read(DEFAULT_BUFFER_SIZE):
            chunk += bytearray(read)
            if len(chunk) >= CHUNK_SIZE:
                # our chunk is the length we want
                # upload it now
                return_state = uploadChunkRetry(client=client, upload_id=upload.id, chunk=bytes(chunk), chunkId=chunkId)
                if not return_state:
                    return return_state

                chunkId += 1
                chunk = bytearray()

    if len(chunk) > 0:
        return_state = uploadChunkRetry(client=client, upload_id=upload.id, chunk=bytes(chunk), chunkId=chunkId)
        if not return_state:
            return return_state

    # upload is done
    # mark it as such
    mark_an_upload_as_done.sync(client=client, upload_id=upload.id)
    return return_state

# ---------------------------
# Lever destinations through WR API
# ---------------------------
def createNewCollection(client: AuthenticatedClient, name: str, description: str, project_id: str) -> int:
    print("Creating Collection:",name,"||",description,"in project",project_id)
    ret = create_collection.sync(
        client=client,
        body=CollectionCreate.from_dict(
            {"title": name, "project_id": project_id, "description": description}
        ),
    )

    if not isinstance(ret, Collection):
        print(ret)
        exit()

    return ret.id