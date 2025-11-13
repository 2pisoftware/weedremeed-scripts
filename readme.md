# Weedremeed Scripts

A collection of public scripts for use with Weedremeed.

## Usage

To use these scripts, download this repository. Then, with Python and Pip installed:

1. Install the python dependencies `pip install -r requirements.txt`
2. Run your desired script e.g. `python3 upload_directory.py`

## Available scripts

### `upload_directory.py`

Upload an entire directory to a collection.
The 'TOKEN' environment variable must be set to the developer API key in the developer console

```
options:
  -h, --help            			Show the help message and exit
  -o, --collection COLLECTION_ID	Output collection ID
  -n, --name NAME       			Name of collection to be created if ID not specified
  -p, --project PROJECT_ID			Output project ID
  -i, --input DIRECTORY				Path of directory to upload
```

IDs can be found in the URL while viewing the target object.