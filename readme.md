# Weedremeed Scripts

A collection of public scripts for use with Weedremeed.

For a quick setup with few environment assumptions besides linux [APT]:
~~~
sudo apt update; sudo apt install -y python3-venv
deactivate; python3 -m venv WR_venv; sudo chmod +x WR_venv/bin/* -R && source WR_venv/bin/activate && pip install -r requirements.txt && sudo chmod +x WR_venv/* -R
~~~

Note, preference for any temp folder to be masked by "_" per gitignore!
~~~
# pattern mask intented for VENV and SCRATCH FILE caches
# eg: WR_OUT (file downloads) or WR_venv (local libs)
*_*/
~~~

## Usage

To use these scripts, download this repository. Then, with Python and Pip installed:

1. Install the python dependencies `pip install -r requirements.txt`
2. Set the 'TOKEN' environment variable to the developer API key from the developer console
3. Run your desired script e.g. `python3 upload_directory.py`

IDs can be found in the URL while viewing the target object.

## Available scripts

### `upload_directory.py`

Upload an entire directory to a collection.

```
options:
  -h, --help                      Show the help message and exit
  -o, --collection COLLECTION_ID  Output collection ID
  -n, --name NAME                 Name of collection to be created if ID not specified
  -p, --project PROJECT_ID        Output project ID
  -i, --input DIRECTORY           Path of directory to upload
```

### `download_collection.py`

Download an entire collection to a directory.

This script downloads the entire collection one at a time.
If you wish to download items faster, use the native Archiver tool in Weedremeed.

```
options:
  -h, --help                        Show this help message and exit
  -i, --collection COLLECTION_ID    Collection ID to download
  -o, --output OUTPUT               Output path
```