#!/usr/bin/python3

# Download Rain cell files, download Mean-ref files.
# Check Rain fall files are available in the bucket.

import fnmatch
import os
import zipfile
import sys
from datetime import datetime, timedelta
from google.cloud import storage
import BucketConfig as config


try:
    wrf_id = sys.argv[1]
    wrf_id_list = wrf_id.split("_")
    client = storage.Client.from_service_account_json(config.KEY_FILE_PATH)
    bucket = client.get_bucket(config.BUCKET_NAME)
    prefix = config.INITIAL_PATH_PREFIX + wrf_id
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if fnmatch.fnmatch(blob.name, "*" + config.WRF_RAINCELL_FILE_ZIP):
            print(blob.name)
            directory = config.RAIN_CELL_DIR + wrf_id_list[1]
            if not os.path.exists(directory):
                os.makedirs(directory)
            download_location = directory + '/' + config.WRF_RAINCELL_FILE_ZIP
            blob.download_to_filename(download_location)
            zip_ref = zipfile.ZipFile(download_location, 'r')
            zip_ref.extractall(directory)
            zip_ref.close()
            os.remove(download_location)
            src_file = directory + '/' + config.WRF_RAIN_CELL_FILE
            des_file = directory + '/' + config.RAIN_CELL_FILE
            os.rename(src_file, des_file)
        elif fnmatch.fnmatch(blob.name, "*" + config.MEAN_REF_FILE):
            print(blob.name)
            directory = config.RAIN_CELL_DIR + wrf_id_list[1]
            directory = config.MEAN_REF_DIR + date
            if not os.path.exists(directory):
                os.makedirs(directory)
            download_location = directory + '/' + config.MEAN_REF_FILE
            blob.download_to_filename(download_location)
        elif fnmatch.fnmatch(blob.name, "*" + config.RF_FILE_SUFFIX):
            print(blob.name)
            directory = config.RF_DIR + wrf_id_list[1]
            if not os.path.exists(directory):
                os.makedirs(directory)
            download_location = directory + '/' + config.RF_FILE
            blob.download_to_filename(download_location)
        else:
            print("File prefix didn't match.")
except:
    print('Rain cell/Mean-Ref/Rain fall file download failed')

