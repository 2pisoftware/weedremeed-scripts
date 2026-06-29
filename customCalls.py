import sys
import os
from argparse import ArgumentParser
import pathlib
import httpx
import json

import pandas as pd

import WR_lib_uploader

from weedremeed_client import AuthenticatedClient
from weedremeed_client.api.collections import get_a_collections_content, get_collection
from weedremeed_client.models import (
    CollectionCreate, Collection,
    ProjectCreate, Project,
)
from weedremeed_client.models.get_a_collections_content_get_a_collections_content_ok import (
    GetACollectionsContentGetACollectionsContentOk,
)
from weedremeed_client.api.projects import get_project, list_projects, create_project
from weedremeed_client.models.project import Project

parser = ArgumentParser(
    description="AdHoc Org data migration in from Weedremeed",
    epilog="The 'TOKEN' environment variable must be set to the developer API key in the developer console.",
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


BASE_URL = "https://portal.weedremeed.com.au"
token = os.environ["WR_SRC_TOKEN"]
src_client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
)

token = os.environ["WR_DST_TOKEN"]
dst_client = AuthenticatedClient(
    base_url=BASE_URL,
    token=token,
    httpx_args={"event_hooks": {"response": [raise_for_status]}},
)


projects = list_projects.sync(client=src_client)
# df_prj = pd.DataFrame([x.to_dict() for x in projects])
shipped_projects = list_projects.sync(client=dst_client)
df_shipped_prj = pd.DataFrame([x.to_dict() for x in shipped_projects])

remapping_projects = {
    "9":31,
    "10":32,
    "11":33,
    "12":34,
    "13":35,
    "14":36,
}

if not isinstance(projects, list):
    print(projects)
    sys.exit(1)

print("Total projects: " + str(len(projects)))

    #############################################################################
    ####### Cache project evidence locally, and push it to dest if target group does not already have it:
    #############################################################################

for project in projects:
    project = get_project.sync(client=src_client, project_id=project.id)

    if (not isinstance(project, Project)):
        print(project)
        sys.exit(1)

    print("\n-------------------\nPROJECT IS: "+str(project.id)+" "+ project.title)
    delivery_group = remapping_projects[str(project.project_group_id)]
    print("DELIVERY IS TO:"+str(delivery_group))

    df_check_delivered = df_shipped_prj[df_shipped_prj['project_group_id'] == delivery_group]
    is_delivered = project.title in df_check_delivered['title'].values

    if is_delivered:
        print("PROJECT PLACEHOLDER IS ALREADY DELIVERED: "+str(is_delivered))
        df_check_delivered = df_shipped_prj[df_shipped_prj['title'] == project.title]['id'].unique()[0]
        delivery_dst = get_project.sync(client=dst_client, project_id=str(df_check_delivered))
        df_check_delivered= pd.DataFrame(delivery_dst.to_dict())

    else:
        if not project.description:
            project.description = project.title + " collections, as available from " + project.dt_created

        out_dir = args.output
        proj_filename = str(project.id) + ".json"

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(out_dir / proj_filename, "w") as f:
            f.write(json.dumps(project.to_dict()))

        create_project.sync(client=dst_client, body=ProjectCreate.from_dict({
            "title": project.title,
            "description": project.description,
            "project_group_id": str(delivery_group)
            }))

        shipped_projects = list_projects.sync(client=dst_client)
        df_shipped_prj = pd.DataFrame([x.to_dict() for x in shipped_projects])
        df_check_delivered = df_shipped_prj[df_shipped_prj['title'] == project.title]['id'].unique()[0]
        delivery_dst = get_project.sync(client=dst_client, project_id=str(df_check_delivered))
        df_check_delivered= pd.DataFrame(delivery_dst.to_dict())
        
        
    #############################################################################
    ## OK, now collections!
    #############################################################################

    map_to_project = str(df_check_delivered['id'].unique()[0])
    for collection in project.collections:
        if collection.type_ != "Upload" and collection.type_ != "Empty":
            print("Skipping 'special' collection '" + collection.title + "'")
            continue

        print("Downloading collection '" + collection.title + "'")
        print("Total attachments: " + str(collection.size))
        print("Belongs to "+df_check_delivered['title'].unique()[0]+" "+map_to_project)

        is_delivered = False
        if 'collections' in df_check_delivered.columns:
            df_check_delivered = pd.DataFrame([x for x in df_check_delivered['collections'].values])
            is_delivered = collection.title in df_check_delivered['title'].values

        if is_delivered:
            print("COLLECTION PLACEHOLDER IS ALREADY DELIVERED: "+str(is_delivered))
            map_to_collection = str(df_check_delivered[df_check_delivered['title'] == collection.title]['id'].unique()[0])
        else:
            if not project.description:
                collection.description = project.title + " collections:</br> " + collection.title
                # if not is_delivered:
                WR_lib_uploader.createNewCollection(client=dst_client, name=collection.title, description=collection.description, project_id=map_to_project)
                # And resync to get the new ID!
                shipped_projects = list_projects.sync(client=dst_client)
                df_shipped_prj = pd.DataFrame([x.to_dict() for x in shipped_projects])
                df_check_delivered = df_shipped_prj[df_shipped_prj['title'] == project.title]['id'].unique()[0]
                delivery_dst = get_project.sync(client=dst_client, project_id=str(df_check_delivered))
                df_check_delivered= pd.DataFrame(delivery_dst.to_dict())
                df_check_delivered = pd.DataFrame([x for x in df_check_delivered['collections'].values])
                map_to_collection = str(df_check_delivered[df_check_delivered['title'] == collection.title]['id'].unique()[0])

        #############################################################################
        ####### Iterate file set into local cache/copy:
        #############################################################################

        done = 0
        content = get_a_collections_content.sync(client=src_client, collection_id=collection.id)
        
        if not isinstance(content, GetACollectionsContentGetACollectionsContentOk):
            print(content)
            sys.exit(1)

        print("Delivering to collection: "+map_to_collection)

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
                print("UPLOADING!")
                WR_lib_uploader.uploadFile(client=dst_client, entry_name=file.filename, entry_path=out_dir / file.filename, collection_id=map_to_collection)
               
            if not content.next_:
                break

            content = get_a_collections_content.sync(client=src_client, collection_id=collection.id, cursor=content.next_)

            if (not isinstance(content, GetACollectionsContentGetACollectionsContentOk) or not content.files):
                break
          