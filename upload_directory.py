import sys
import os
from argparse import ArgumentParser, BooleanOptionalAction
import pathlib
from io import DEFAULT_BUFFER_SIZE
import mimetypes
import math
import hashlib
import httpx
import base64

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import create_collection
from weedremeed_client.models import CollectionCreate, Collection
from weedremeed_client.api.collections import upload_file
from weedremeed_client.api.uploads import register_upload_part, mark_an_upload_as_done
from weedremeed_client.models.register_upload_part_body import RegisterUploadPartBody
from weedremeed_client.models.upload_file_body import UploadFileBody
from weedremeed_client.models.upload_file_upload_file_ok import UploadFileUploadFileOk
from weedremeed_client.models.register_upload_part_register_upload_part_ok import RegisterUploadPartRegisterUploadPartOk

parser = ArgumentParser(description="Utility for uploading directories to Weedremeed.",
						epilog="IDs can be found in the URL while viewing the target object. The 'TOKEN' environment variable must be set to the developer API key in the developer console.")
parser.add_argument("-o", "--collection", dest="collection_id", type=int, help="Output collection ID")
parser.add_argument("-n", "--name", dest="name", type=str, help="Name of collection to be created if ID not specified")
parser.add_argument("-p", "--project", dest="project_id", type=int, required=True, help="Output project ID")
parser.add_argument("-i", "--input", dest="directory", type=pathlib.Path, required=True, help="Path of directory to upload")

args = parser.parse_args()

token = os.environ["TOKEN"]
client = AuthenticatedClient(base_url="https://test.portal.weedremeed.com.au", token=token)

CHUNK_SIZE = 1024 * 1024 * 5
MAX_RETRIES = 5

def createNewCollection(name: str, project_id: str):
	print("Collection not specified, creating one")

	ret = create_collection.sync(client=client, body=CollectionCreate.from_dict({
		"title": name,
		"project_id": project_id
	}))

	if not isinstance(ret, Collection):
		print(ret)
		sys.exit(1)

	return ret.id

collection_id = args.collection_id

if not collection_id:
	collection_id = createNewCollection(args.name or os.path.dirname(args.directory), args.project_id)

def uploadChunk(upload_id: str, chunk: bytes, totalChunks: int):
	md5Hash = base64.b64encode(hashlib.md5(chunk).digest()).decode()

	part = register_upload_part.sync(client=client, body=RegisterUploadPartBody.from_dict({
		"id": upload_id,
		"part": totalChunks,
		"length": len(chunk),
		"md5": md5Hash,
	}))

	if not isinstance(part, RegisterUploadPartRegisterUploadPartOk):
		print(part)
		sys.exit(1)

	ret = httpx.put(part.endpoint, content=chunk, headers={
		"Content-MD5": md5Hash
	})

	if ret.is_error:
		print(ret)
		sys.exit(1)

def uploadFile(entry: os.DirEntry[str]):
	stat = entry.stat()

	upload = upload_file.sync(client=client, collection_id=collection_id, body=UploadFileBody.from_dict({
		"filename": entry.name,
		"mime": mimetypes.guess_type(entry.path)[0],
		"size": stat.st_size
	}))

	if not isinstance(upload, UploadFileUploadFileOk):
		print(upload)
		sys.exit(1)

	NUM_CHUNKS = math.ceil(stat.st_size / CHUNK_SIZE) #for progress indicator?
	completedChunks = 1

	with open(entry.path, "rb") as stream:
		chunk = bytearray()
		while read := stream.read(DEFAULT_BUFFER_SIZE):
			chunk += bytearray(read)
			
			if len(chunk) >= CHUNK_SIZE:
				# our chunk is the length we want
				# upload it now

				uploadChunk(upload.id, bytes(chunk), completedChunks)
				completedChunks += 1

				chunk = bytearray()

	if len(chunk) > 0:
		uploadChunk(upload.id, bytes(chunk), completedChunks)
	
	# uploads done
	# mark it as such

	mark_an_upload_as_done.sync(client=client, upload_id=upload.id)

total = len(os.listdir(args.directory))

with os.scandir(args.directory) as it:
	for inx, entry in enumerate(it):
		if (inx % (total / 10) == 0) or total < 20:
			print("Uploading " + str(inx + 1) + " of " + str(total + 1))

		uploadFile(entry)