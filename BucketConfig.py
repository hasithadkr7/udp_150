#!/bin/python
#Retrieving rain cell and men-ref files from google buckets.
# Common.
FILE_GEN_TIME = '18:00'
BUCKET_NAME = 'curwsl_nfs_1'
WRF_NODE = 'wrf0'
KEY_FILE_PATH = '/home/uwcc-admin/uwcc-admin.json'

# For Rain cell
RAIN_CELL_DIR = '/home/wrf_bucket/Raincell'
WRF_RAINCELL_FILE_ZIP = 'RAINCELL_150m.zip'
WRF_RAIN_CELL_FILE = 'RAINCELL_150m.DAT'
RAIN_CELL_FILE = 'RAINCELL.DAT'
DEFAULT_DATE_SHIFT = 1

# For Mean-Rf
MEAN_REF_DIR = '/home/wrf_bucket/Meanref'
MEAN_REF_FILE = 'kub_mean_rf.txt'

# For RF data
RF_DIR = '/home/wrf_bucket/Rainfall'
RF_FILE = 'Norwood_stations_rf.txt'

# For RF data
SUB_REF_DIR = '/home/wrf_bucket/Subref'
SUB_REF_FILE = 'klb_mean_rf.txt'

DEFAULT_DATE_SHIFT = 1

RF_FILE_SUFFIX = 'stations_rf.txt'