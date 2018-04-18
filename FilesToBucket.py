#!/usr/bin/python3

# Upload Hec-Hms generated files, INFLOW.DAT, OUTFLOW.DAT
from google.cloud import storage
import json
import sys
import string
import random
from datetime import datetime


# Buckets/curwsl_nfs_1/results/wrf0_2018-04-15_18:00_f2Nq
# Buckets/curwsl_nfs_1/results/hec_hms0_2018-04-15_18:00
# inflow
# outflow
# /hec-hms/FLO2D/INFLOW.DAT
# /hec-hms/FLO2D/OUTFLOW.DAT


# def upload_hec_hms_files():
#     print("upload_hec_hms_files...")
#     time = datetime.now().strftime("%H:%M")
#     path_suffix = '_'+time+'_'+''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))
#     try:
#         client = storage.Client.from_service_account_json(key_file)
#         try:
#             bucket = client.get_bucket(bucket_name)
#             print("Upload INFLOW.DAT to bucket...")
#             try:
#                 inflow_blob = bucket.blob('/results/hec-hms0_'+forecast_date+path_suffix+'/inflow/INFLOW.DAT')
#                 inflow_blob.upload_from_filename(filename=inflow_dat)
#             except Exception as ex1:
#                 print("Upload INFLOW.DAT|Exception: ", ex1)
#             print("Upload OUTFLOW.DAT to bucket...")
#             try:
#                 outflow_blob = bucket.blob('/results/hec-hms0_'+forecast_date+path_suffix+'/outflow/OUTFLOW.DAT')
#                 outflow_blob.upload_from_filename(filename=outflow_dat)
#             except Exception as ex2:
#                 print("Upload OUTFLOW.DAT|Exception: ", ex2)
#         except LookupError as look_ex:
#             print("client.get_bucket|LookupError:", look_ex)
#     except KeyError as key_ex:
#         print("storage.Client.from_service_account_json|KeyError:", key_ex)

def upload_hec_hms_files():
    print("upload_hec_hms_files...")
    try:
        client = storage.Client.from_service_account_json(key_file)
        try:
            bucket = client.get_bucket(bucket_name)
            print("Upload INFLOW.DAT to bucket...")
            try:
                inflow_blob = bucket.blob('results/'+hec_hms_id+'/inflow/INFLOW.DAT')
                inflow_blob.upload_from_filename(filename=inflow_dat)
            except Exception as ex1:
                print("Upload INFLOW.DAT|Exception: ", ex1)
            print("Upload OUTFLOW.DAT to bucket...")
            try:
                outflow_blob = bucket.blob('results/'+hec_hms_id+'/outflow/OUTFLOW.DAT')
                outflow_blob.upload_from_filename(filename=outflow_dat)
            except Exception as ex2:
                print("Upload OUTFLOW.DAT|Exception: ", ex2)
        except LookupError as look_ex:
            print("client.get_bucket|LookupError:", look_ex)
    except KeyError as key_ex:
        print("storage.Client.from_service_account_json|KeyError:", key_ex)


try:
    hec_hms_id = sys.argv[1]
    forecast_date = hec_hms_id.split("_")[1]
    print("Load configuration...")
    with open('CONFIG.json') as json_file:
        config_data = json.load(json_file)
        key_file = config_data["KEY_FILE_PATH"]
        bucket_name = config_data["BUCKET_NAME"]
        bucket_id_prefix = config_data["BUCKET_ID_PREFIX"]
        inflow_dat = config_data["INFLOW_FILE_PATH"]
        outflow_dat = config_data["OUTFLOW_FILE_PATH"]
        try:
            upload_hec_hms_files()
        except Exception as ex:
            print("upload_hec_hms_files|Exception: ",ex)
except Exception as e:
    print("Exception occurred: ", e)


