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


def get_rain_cell_file(blob, file_dir, date_shift):
    date = get_daily_directory(date_shift)
    directory = file_dir + date
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


def get_mean_ref_file(blob, file_dir, date_shift):
    date = get_daily_directory(date_shift)
    directory = file_dir + date
    if not os.path.exists(directory):
        os.makedirs(directory)
    download_location = directory + '/' + config.MEAN_REF_FILE
    blob.download_to_filename(download_location)


def get_sub_ref_file(blob, file_dir, date_shift):
    date = get_daily_directory(date_shift)
    directory = file_dir + date
    if not os.path.exists(directory):
        os.makedirs(directory)
    download_location = directory + '/' + config.SUB_REF_FILE
    blob.download_to_filename(download_location)


def get_blob(bucket, prefix, required_file):
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if fnmatch.fnmatch(blob.name, "*" + required_file):
            return blob


def get_folder_prefix(wrf_node, file_time, date_shift):
    if date_shift == 0:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = (datetime.today() - timedelta(days=date_shift)).strftime("%Y-%m-%d")
    prefix = 'results/' + wrf_node + '_' + date + '_' + file_time + '_'
    return prefix


def get_bucket(key_file, bucket_name):
    client = storage.Client.from_service_account_json(key_file)
    bucket = client.get_bucket(bucket_name)
    return bucket


def get_daily_directory(date_shift):
    if date_shift == 0:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = (datetime.today() - timedelta(days=date_shift)).strftime("%Y-%m-%d")
    return date


def get_rf_files(pattern, file_dir, shift):
    bucket = get_bucket(config.KEY_FILE_PATH, config.BUCKET_NAME)
    prefix = get_folder_prefix(config.WRF_NODE, config.FILE_GEN_TIME, shift)
    blobs = bucket.list_blobs(prefix=prefix)
    directory = file_dir + date
    for blob in blobs:
        if fnmatch.fnmatch(blob.name, "*" + pattern):
            if not os.path.exists(directory):
                os.makedirs(directory)
            download_location = directory + '/' + config.RF_FILE_SUFFIX
            blob.download_to_filename(download_location)


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)


try:
    past_date_str = sys.argv[1]
    #print(past_date_str)
    shift_datetime = datetime.strptime(past_date_str, "%Y-%m-%d")
    #print(shift_datetime)
    shift_date = shift_datetime.strftime("%Y-%m-%d")
    #print(shift_date)
    current_date = datetime.today().strftime("%Y-%m-%d")
    #print(current_date)
    shift = days_between(shift_date, current_date)
    #print(shift)
    try:
        cell_bucket = get_bucket(config.KEY_FILE_PATH, config.BUCKET_NAME)
        cell_prefix = get_folder_prefix(config.WRF_NODE, config.FILE_GEN_TIME, shift)
        cell_blob = get_blob(cell_bucket, cell_prefix, config.WRF_RAINCELL_FILE_ZIP)
        get_rain_cell_file(cell_blob, config.RAIN_CELL_DIR, shift)
        try:
            meanrf_bucket = get_bucket(config.KEY_FILE_PATH, config.BUCKET_NAME)
            meanrf_prefix = get_folder_prefix(config.WRF_NODE, config.FILE_GEN_TIME, shift)
            meanrf_blob = get_blob(meanrf_bucket, meanrf_prefix, config.MEAN_REF_FILE)
            get_mean_ref_file(meanrf_blob, config.MEAN_REF_DIR, shift)
            try:
                get_rf_files(config.RF_FILE_SUFFIX, config.RF_DIR, shift)
                print('proceed')
            except:
                print('Rainfall files download failed')
        except:
            print('Mean-Ref file download failed')
    except:
        print('Rain cell file download failed')
except:
    print('Rain cell/Mean-Ref/Rain fall file download failed')

