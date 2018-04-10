#!/bin/python

from gcloud import storage

client = storage.Client.from_service_account_json("/home/uwcc-admin/uwcc-admin.json")
buckets = client.list_buckets()
for bkt in buckets:
    print bkt

