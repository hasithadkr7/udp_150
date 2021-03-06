#!/usr/bin/python3.5

import csv
import getopt
import glob
import json
import os
import sys
import traceback
from collections import OrderedDict
import fnmatch
import zipfile
from datetime import datetime, timedelta
from google.cloud import storage
import BucketConfig as config
from curwmysqladapter import MySQLAdapter, Data


def usage():
    usage_text = """
Usage: ./CSVTODAT.py [-d YYYY-MM-DD] [-t HH:MM:SS] [-h]

-h  --help          Show usage
-d  --date          Date in YYYY-MM-DD. Default is current date.
-t  --time          Time in HH:MM:SS. Default is current time.
    --start-date    Start date of timeseries which need to run the forecast in YYYY-MM-DD format. Default is same as -d(date).
    --start-time    Start time of timeseries which need to run the forecast in HH:MM:SS format. Default is same as -t(date).
-T  --tag           Tag to differential simultaneous Forecast Runs E.g. wrf1, wrf2 ...
    --wrf-rf        Path of WRF Rf(Rainfall) Directory. Otherwise using the `RF_DIR_PATH` from CONFIG.json
    --wrf-kub       Path of WRF kelani-upper-basin(KUB) Directory. Otherwise using the `KUB_DIR_PATH` from CONFIG.json
"""
    print(usage_text)


def get_observed_timeseries(my_adapter, my_event_id, my_opts):
    existing_timeseries = my_adapter.retrieve_timeseries([my_event_id], my_opts)
    new_timeseries = []
    if len(existing_timeseries) > 0 and len(existing_timeseries[0]['timeseries']) > 0:
        existing_timeseries = existing_timeseries[0]['timeseries']
        prev_date_time = existing_timeseries[0][0]
        prev_sum = existing_timeseries[0][1]
        for tt in existing_timeseries:
            tt[0] = tt[0]
            if prev_date_time.replace(minute=0, second=0, microsecond=0) == tt[0].replace(minute=0, second=0,
                                                                                          microsecond=0):
                prev_sum += tt[1]  # TODO: If missing or minus -> ignore
                # TODO: Handle End of List
            else:
                new_timeseries.append([tt[0].replace(minute=0, second=0, microsecond=0), prev_sum])
                prev_date_time = tt[0]
                prev_sum = tt[1]

    return new_timeseries


def download_required_files(wrf_id):
    try:
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

try:
    CONFIG = json.loads(open('CONFIG.json').read())
    # print('Config :: ', CONFIG)
    RF_FORECASTED_DAYS = 0
    RAIN_CSV_FILE = 'DailyRain.csv'
    RF_DIR_PATH = '/home/wrf_bucket/Rainfall'
    KUB_DIR_PATH = '/home/wrf_bucket/Meanref'
    KLB_DIR_PATH = '/home/wrf_bucket/Subref'
    OUTPUT_DIR = './OUTPUT'
    # Kelani Upper Basin
    # KUB_OBS_ID = 'b0e008522be904bcf71e290b3b0096b33c3e24d9b623dcbe7e58e7d1cc82d0db'
    KUB_OBS_ID = 'fb575cb25f1e3d3a07c84513ea6a91c8f2fb98454df1a432518ab98ad7182861'  # wrf0, kub_mean, 0-d
    # Kelani Lower Basin
    # KLB_OBS_ID = '3fb96706de7433ba6aff4936c9800a28c9599efd46cbc9216a5404aab812d76a'
    KLB_OBS_ID = '69c464f749b36d9e55e461947238e7ed809c2033e75ae56234f466eec00aee35'  # wrf0, klb_mean, 0-d

    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_DB = "curw"
    MYSQL_PASSWORD = ""

    if 'RF_FORECASTED_DAYS' in CONFIG:
        RF_FORECASTED_DAYS = CONFIG['RF_FORECASTED_DAYS']
    if 'RAIN_CSV_FILE' in CONFIG:
        RAIN_CSV_FILE = CONFIG['RAIN_CSV_FILE']
    if 'RF_DIR_PATH' in CONFIG:
        RF_DIR_PATH = CONFIG['RF_DIR_PATH']
    if 'KUB_DIR_PATH' in CONFIG:
        KUB_DIR_PATH = CONFIG['KUB_DIR_PATH']
    if 'OUTPUT_DIR' in CONFIG:
        OUTPUT_DIR = CONFIG['OUTPUT_DIR']

    if 'MYSQL_HOST' in CONFIG:
        MYSQL_HOST = CONFIG['MYSQL_HOST']
    if 'MYSQL_USER' in CONFIG:
        MYSQL_USER = CONFIG['MYSQL_USER']
    if 'MYSQL_DB' in CONFIG:
        MYSQL_DB = CONFIG['MYSQL_DB']
    if 'MYSQL_PASSWORD' in CONFIG:
        MYSQL_PASSWORD = CONFIG['MYSQL_PASSWORD']

    print("MYSQL_HOST:", MYSQL_HOST)
    print("MYSQL_USER:", MYSQL_USER)
    print("MYSQL_DB:", MYSQL_DB)
    print("MYSQL_PASSWORD:", MYSQL_PASSWORD)

    date = ''
    time = ''
    startDate = ''
    startTime = ''
    tag = ''
    wrf_id = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:t:T:", [
            "help", "date=", "time=", "start-date=", "start-time=", "wrf-rf=", "wrf-kub=", "tag="
        ])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-d", "--date"):
            date = arg
        elif opt in ("-t", "--time"):
            time = arg
        elif opt in ("--start-date"):
            startDate = arg
        elif opt in ("--start-time"):
            startTime = arg
        elif opt in ("--wrf-rf"):
            RF_DIR_PATH = arg
        elif opt in ("--wrf-kub"):
            KUB_DIR_PATH = arg
        elif opt in ("-T", "--tag"):
            tag = arg
        elif opt in ("--wrf_id"):
            wrf_id = arg

    UPPER_CATCHMENT_WEIGHTS = {
        # 'Attanagalla'   : 1/7,    # 1
        'Daraniyagala': 0.146828,  # 2
        'Glencourse': 0.208938,  # 3
        'Hanwella': 0.078722,  # 4
        'Holombuwa': 0.163191,  # 5
        'Kitulgala': 0.21462,  # 6
        'Norwood': 0.187701  # 7
    }
    UPPER_CATCHMENTS = UPPER_CATCHMENT_WEIGHTS.keys()

    KELANI_UPPER_BASIN_WEIGHTS = {
        'kub-mean-rf': 1
    }
    KELANI_UPPER_BASIN = KELANI_UPPER_BASIN_WEIGHTS.keys()

    LOWER_CATCHMENT_WEIGHTS = {
        'Colombo': 1
    }
    LOWER_CATCHMENTS = LOWER_CATCHMENT_WEIGHTS.keys()

    # Default run for current day
    modelState = datetime.now()
    if date:
        modelState = datetime.strptime(date, '%Y-%m-%d')
    date = modelState.strftime("%Y-%m-%d")
    if time:
        modelState = datetime.strptime('%s %s' % (date, time), '%Y-%m-%d %H:%M:%S')
    time = modelState.strftime("%H:%M:%S")
    # Set the RF forecast data available file name pattern
    rfForecastedDate = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=RF_FORECASTED_DAYS)
    rfForecastedDate = rfForecastedDate.strftime("%Y-%m-%d")

    startDateTime = datetime.now()
    if startDate:
        startDateTime = datetime.strptime(startDate, '%Y-%m-%d')
    else:
        startDateTime = datetime.strptime(date, '%Y-%m-%d')
    startDate = startDateTime.strftime("%Y-%m-%d")

    if startTime:
        startDateTime = datetime.strptime('%s %s' % (startDate, startTime), '%Y-%m-%d %H:%M:%S')
    startTime = startDateTime.strftime("%H:%M:%S")

    print('RFTOCSV startTime:', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(' RFTOCSV run for', date, '@', time, tag)
    print(' With Custom starting', startDate, '@', startTime, ' using RF data of ', rfForecastedDate)

    RF_DIR_PATH = '/hec-hms/Rainfall/' + rfForecastedDate
    KUB_DIR_PATH = '/hec-hms/Meanref/' + rfForecastedDate
    KLB_DIR_PATH = '/hec-hms/Subref/' + rfForecastedDate

    print('RF_DIR_PATH:', RF_DIR_PATH)
    print('KUB_DIR_PATH:', KUB_DIR_PATH)
    print('KLB_DIR_PATH:', KLB_DIR_PATH)

    # TODO: Do not use any more, using WRF generated KUB
    # Norwood_stations_rf.txt
    UPPER_THEISSEN_VALUES = OrderedDict()
    for catchment in UPPER_CATCHMENTS:
        for filename in glob.glob(os.path.join(RF_DIR_PATH, '%s_stations_rf.txt' % catchment)):
            print('---------------------Start Operating on (Upper) ', filename)
            csvCatchment = csv.reader(open(filename, 'r'), delimiter='\t', skipinitialspace=True)
            csvCatchment = list(csvCatchment)
            for row in csvCatchment:
                # print(row[0].replace('_', ' '), row[1].strip(' \t'))
                d = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                key = d.timestamp()
                if key not in UPPER_THEISSEN_VALUES:
                    UPPER_THEISSEN_VALUES[key] = 0
                UPPER_THEISSEN_VALUES[key] += float(row[1].strip(' \t')) * UPPER_CATCHMENT_WEIGHTS[catchment]

    # TODO: Need to be replace by retrieving data from database
    # kub_mean_rf.txt
    KELANI_UPPER_BASIN_VALUES = OrderedDict()
    for catchment in KELANI_UPPER_BASIN:
        for filename in glob.glob(os.path.join(KUB_DIR_PATH, 'kub_mean_rf.txt')):
            print('---------------------Start Operating on (Kelani Upper Basin) ', filename)
            csvCatchment = csv.reader(open(filename, 'r'), delimiter='\t', skipinitialspace=True)
            csvCatchment = list(csvCatchment)
            for row in csvCatchment:
                # print(row[0].replace('_', ' '), row[1].strip(' \t'))
                d = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                key = d.timestamp()
                if key not in KELANI_UPPER_BASIN_VALUES:
                    KELANI_UPPER_BASIN_VALUES[key] = 0
                KELANI_UPPER_BASIN_VALUES[key] += float(row[1].strip(' \t')) * KELANI_UPPER_BASIN_WEIGHTS[catchment]

    # TODO: Need to be replace by using KLB-Mean generate by WRF
    # TODO: Get data from database directly
    # klb_mean_rf.txt
    LOWER_THEISSEN_VALUES = OrderedDict()
    for lowerCatchment in LOWER_CATCHMENTS:
        for filename in glob.glob(os.path.join(RF_DIR_PATH, '%s_stations_rf.txt' % lowerCatchment)):
            print('--------------------Start Operating on (Lower) ', filename)
            csvCatchment = csv.reader(open(filename, 'r'), delimiter='\t', skipinitialspace=True)
            csvCatchment = list(csvCatchment)
            for row in csvCatchment:
                # print(row[0].replace('_', ' '), row[1].strip(' \t'))
                d = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                key = d.timestamp()
                if key not in LOWER_THEISSEN_VALUES:
                    LOWER_THEISSEN_VALUES[key] = 0
                LOWER_THEISSEN_VALUES[key] += float(row[1].strip(' \t')) * LOWER_CATCHMENT_WEIGHTS[lowerCatchment]

    # Get Observed Data
    adapter = MySQLAdapter(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, db=MYSQL_DB)
    opts = {
        'from': (startDateTime - timedelta(minutes=90)).strftime("%Y-%m-%d %H:%M:%S"),
        'to': modelState.strftime("%Y-%m-%d %H:%M:%S"),
        # 'mode': Data.processed_data TODO: Hack -> Fill with WRF data
    }
    KUB_Timeseries = get_observed_timeseries(adapter, KUB_OBS_ID, opts)
    if len(KUB_Timeseries) > 0:
        # print(KUB_Timeseries)
        print('KUB_Timeseries::', len(KUB_Timeseries), KUB_Timeseries[0], KUB_Timeseries[-1])
    else:
        print('No data found for KUB Obs timeseries: ', KUB_Timeseries)
    KLB_Timeseries = get_observed_timeseries(adapter, KLB_OBS_ID, opts)
    if len(KLB_Timeseries) > 0:
        # print(KLB_Timeseries)
        print('KLB_Timeseries::', len(KLB_Timeseries), KLB_Timeseries[0], KLB_Timeseries[-1])
    else:
        print('No data found for KLB Obs timeseries: ', KLB_Timeseries)

    print('Finished processing files. Start Writing Theissen polygon avg in to CSV')
    # print(UPPER_THEISSEN_VALUES)

    fileName = RAIN_CSV_FILE.rsplit('.', 1)
    fileName = '{name}-{date}{tag}.{extention}'.format(name=fileName[0], date=date, tag='.' + tag if tag else '',
                                                       extention=fileName[1])
    RAIN_CSV_FILE_PATH = os.path.join(OUTPUT_DIR, fileName)
    csvWriter = csv.writer(open(RAIN_CSV_FILE_PATH, 'w'), delimiter=',', quotechar='|')
    # Write Metadata https://publicwiki.deltares.nl/display/FEWSDOC/CSV
    csvWriter.writerow(['Location Names', 'Awissawella', 'Colombo'])
    csvWriter.writerow(['Location Ids', 'Awissawella', 'Colombo'])
    csvWriter.writerow(['Time', 'Rainfall', 'Rainfall'])

    # Insert available observed data
    lastObsDateTime = startDateTime
    for kub_tt in KUB_Timeseries:
        # look for same time value in Kelani Basin
        klb_tt = kub_tt  # TODO: Better to replace with missing ???
        for sub_tt in KLB_Timeseries:
            if sub_tt[0] == kub_tt[0]:
                klb_tt = sub_tt
                break

        csvWriter.writerow([kub_tt[0].strftime('%Y-%m-%d %H:%M:%S'), "%.2f" % kub_tt[1], "%.2f" % klb_tt[1]])
        lastObsDateTime = kub_tt[0]

    # Iterate through each timestamp
    for avg in UPPER_THEISSEN_VALUES:
        # print(avg, UPPER_THEISSEN_VALUES[avg], LOWER_THEISSEN_VALUES[avg])
        d = datetime.fromtimestamp(avg)
        if d > lastObsDateTime:
            try:
                csvWriter.writerow([d.strftime('%Y-%m-%d %H:%M:%S'), "%.2f" % KELANI_UPPER_BASIN_VALUES[avg],
                                "%.2f" % LOWER_THEISSEN_VALUES[avg]])
            except KeyError:
                print(KeyError)

except ValueError:
    raise ValueError("Incorrect data format, should be YYYY-MM-DD")
except Exception as e:
    print(e)
    traceback.print_exc()
finally:
    print('Completed ', RF_DIR_PATH, ' to ', RAIN_CSV_FILE_PATH)
