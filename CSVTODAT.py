#!/usr/bin/python3

import csv
import datetime
import getopt
import json
import os
import sys
import traceback
import copy

from curwmysqladapter import MySQLAdapter

from Util.LibForecastTimeseries import extractForecastTimeseries
from Util.LibForecastTimeseries import extractForecastTimeseriesInDays


def usage():
    usageText = """
Usage: ./CSVTODAT.py [-d YYYY-MM-DD] [-h]

-h  --help          Show usage
-d  --date          Model State Date in YYYY-MM. Default is current date.
-t  --time          Model State Time in HH:MM:SS. Default is current time.
    --start-date    Start date of timeseries which need to run the forecast in YYYY-MM-DD format. Default is same as -d(date).
    --start-time    Start time of timeseries which need to run the forecast in HH:MM:SS format. Default is same as -t(date).
-T  --tag           Tag to differential simultaneous Forecast Runs E.g. wrf1, wrf2 ...
-f  --forceInsert   Force Insert into the database. May override existing values.
-n  --name          Name field value of the Run table in Database. Use time format such as 'Cloud-1-<%H:%M:%S>' to replace with time(t).
"""
    print(usageText)


def save_forecast_timeseries(my_adapter, timeseries, my_model_date, my_model_time, my_opts):
    print('CSVTODAT:: save_forecast_timeseries:: len', len(timeseries), my_model_date, my_model_time)
    forecast_timeseries = extractForecastTimeseries(timeseries, my_model_date, my_model_time, by_day=True)
    # print(forecastTimeseries[:10])
    extracted_timeseries = extractForecastTimeseriesInDays(forecast_timeseries)
    print('Extracted forecast types # :', len(extracted_timeseries))
    # for ll in extractedTimeseries :
    #     print(ll)

    force_insert = my_opts.get('forceInsert', False)
    my_model_date_time = datetime.datetime.strptime('%s %s' % (my_model_date, my_model_time), '%Y-%m-%d %H:%M:%S')

    # TODO: Check whether station exist in Database
    run_name = my_opts.get('runName', 'Cloud-1')
    less_char_index = run_name.find('<')
    greater_char_index = run_name.find('>')
    # if less_char_index > -1 and greater_char_index > -1 and less_char_index < greater_char_index :
    if -1 < less_char_index < greater_char_index > -1:
        start_str = run_name[:less_char_index]
        date_format_str = run_name[less_char_index + 1:greater_char_index]
        end_str = run_name[greater_char_index + 1:]
        try:
            date_str = my_model_date_time.strftime(date_format_str)
            run_name = start_str + date_str + end_str
        except ValueError:
            raise ValueError("Incorrect data format " + date_format_str)
    types = [
        'Forecast-0-d',
        'Forecast-1-d-after',
        'Forecast-2-d-after',
        'Forecast-3-d-after',
        'Forecast-4-d-after',
        'Forecast-5-d-after',
        'Forecast-6-d-after',
        'Forecast-7-d-after',
        'Forecast-8-d-after',
        'Forecast-9-d-after'
    ]
    meta_data = {
        'station': 'Hanwella',
        'variable': 'Discharge',
        'unit': 'm3/s',
        'type': types[0],
        'source': 'HEC-HMS',
        'name': run_name,
    }
    for index in range(0, min(len(types), len(extracted_timeseries))):
        meta_data_copy = copy.deepcopy(meta_data)
        meta_data_copy['type'] = types[index]
        event_id = my_adapter.get_event_id(meta_data_copy)
        if event_id is None:
            event_id = my_adapter.create_event_id(meta_data_copy)
            print('HASH SHA256 created: ', event_id)
        else:
            print('HASH SHA256 exists: ', event_id)
            if not force_insert:
                print('Timeseries already exists. User --force to update the existing.\n')
                continue
        
        # for l in timeseries[:3] + timeseries[-2:] :
        #     print(l)
        row_count = my_adapter.insert_timeseries(event_id, extracted_timeseries[index], force_insert)
        print('%s rows inserted.\n' % row_count)
    # -- END OF SAVE_FORECAST_TIMESERIES


try:
    CONFIG = json.loads(open('CONFIG.json').read())
    # print('Config :: ', CONFIG)

    CSV_NUM_METADATA_LINES = 2
    DAT_WIDTH = 12
    DISCHARGE_CSV_FILE = 'DailyDischarge.csv'
    INFLOW_DAT_FILE = './FLO2D/INFLOW.DAT'
    OUTPUT_DIR = './OUTPUT'
    INIT_WL_CONFIG = './Template/INITWL.CONF'

    MYSQL_HOST="localhost"
    MYSQL_USER="root"
    MYSQL_DB="curw"
    MYSQL_PASSWORD=""

    if 'DISCHARGE_CSV_FILE' in CONFIG:
        DISCHARGE_CSV_FILE = CONFIG['DISCHARGE_CSV_FILE']
    if 'INFLOW_DAT_FILE' in CONFIG:
        INFLOW_DAT_FILE = CONFIG['INFLOW_DAT_FILE']
    if 'OUTPUT_DIR' in CONFIG:
        OUTPUT_DIR = CONFIG['OUTPUT_DIR']
    if 'INIT_WL_CONFIG' in CONFIG:
        INIT_WL_CONFIG = CONFIG['INIT_WL_CONFIG']

    if 'MYSQL_HOST' in CONFIG:
        MYSQL_HOST = CONFIG['MYSQL_HOST']
    if 'MYSQL_USER' in CONFIG:
        MYSQL_USER = CONFIG['MYSQL_USER']
    if 'MYSQL_DB' in CONFIG:
        MYSQL_DB = CONFIG['MYSQL_DB']
    if 'MYSQL_PASSWORD' in CONFIG:
        MYSQL_PASSWORD = CONFIG['MYSQL_PASSWORD']

    date = ''
    time = ''
    startDate = ''
    startTime = ''
    tag = ''
    forceInsert = False
    storeData = False
    runName = 'Cloud-1'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:t:T:fsn:", [
            "help", "date=", "time=", "start-date=", "start-time=", "tag=", "force", "runName="
        ])
    except getopt.GetoptError:          
        usage()                        
        sys.exit(2)                     
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in ("-d", "--date"):
            date = arg
        elif opt in ("-t", "--time"):
            time = arg
        elif opt in ("--start-date"):
            startDate = arg
        elif opt in ("--start-time"):
            startTime = arg
        elif opt in ("-T", "--tag"):
            tag = arg
        elif opt in ("-f", "--force"):
            forceInsert = True
        elif opt in ("-s", "--store"):
            storeData = True
        elif opt in ("-n", "--name"):
            runName = arg

    # FLO-2D parameters
    IHOURDAILY  = 0     # 0-hourly interval, 1-daily interval
    IDEPLT      = 0     # Set to 0 on running with Text mode. Otherwise cell number e.g. 8672
    IFC         = 'C'   # foodplain 'F' or a channel 'C'
    INOUTFC     = 0     # 0-inflow, 1-outflow
    #KHIN        = 8655  # inflow nodes
    KHIN	= 41550
    HYDCHAR     = 'H'   # Denote line of inflow hydrograph time and discharge pairs

    # Default run for current day
    modelState = datetime.datetime.now()
    if date:
        modelState = datetime.datetime.strptime(date, '%Y-%m-%d')
    date = modelState.strftime("%Y-%m-%d")
    if time:
        modelState = datetime.datetime.strptime('%s %s' % (date, time), '%Y-%m-%d %H:%M:%S')
    time = modelState.strftime("%H:%M:%S")

    startDateTime = datetime.datetime.now()
    if startDate:
        startDateTime = datetime.datetime.strptime(startDate, '%Y-%m-%d')
    else:
        startDateTime = datetime.datetime.strptime(date, '%Y-%m-%d')
    startDate = startDateTime.strftime("%Y-%m-%d")

    if startTime:
        startDateTime = datetime.datetime.strptime('%s %s' % (startDate, startTime), '%Y-%m-%d %H:%M:%S')
    startTime = startDateTime.strftime("%H:%M:%S")

    print('CSVTODAT startTime:', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tag)
    print(' CSVTODAT run for', date, '@', time, tag)
    print(' With Custom starting', startDate, '@', startTime, ' run name:', runName)

    fileName = DISCHARGE_CSV_FILE.rsplit('.', 1)
    fileName = '{name}-{date}{tag}.{extension}'.\
        format(name=fileName[0], date=date, tag='.'+tag if tag else '', extension=fileName[1])
    DISCHARGE_CSV_FILE_PATH = os.path.join(OUTPUT_DIR, fileName)
    print('Open Discharge CSV ::', DISCHARGE_CSV_FILE_PATH)
    csvReader = csv.reader(open(DISCHARGE_CSV_FILE_PATH, 'r'), delimiter=',', quotechar='|')
    csvList = list(csvReader)

    # Validate Discharge Timeseries
    if not len(csvList[CSV_NUM_METADATA_LINES:]) > 0 :
        print('ERROR: Discharge timeseries length is zero.')
        sys.exit(1)

    fileName2 = INFLOW_DAT_FILE.rsplit('.', 1)
    INFLOW_DAT_FILE_PATH = '{name}{tag}.{extension}'.\
        format(name=fileName2[0], tag='.'+tag if tag else '', extension=fileName2[1])
    print('Open FLO2D INFLOW ::', INFLOW_DAT_FILE_PATH)
    f = open(INFLOW_DAT_FILE_PATH, 'w')
    line1 = '{0} {1:{w}{b}}\n'.format(IHOURDAILY, IDEPLT, b='d', w=DAT_WIDTH)
    line2 = '{0} {1:{w}{b}} {2:{w}{b}}\n'.format(IFC, INOUTFC, KHIN, b='d', w=DAT_WIDTH)
    line3 = '{0} {1:{w}{b}} {2:{w}{b}}\n'.format(HYDCHAR, 0.0, 0.0, b='.1f', w=DAT_WIDTH)
    f.writelines([line1, line2, line3])

    lines = []; i = 1.0
    for value in csvList[CSV_NUM_METADATA_LINES:] :
        lines.append('{0} {1:{w}{b}} {2:{w}{b}}\n'.format(HYDCHAR, i, float(value[1]), b='.1f', w=DAT_WIDTH))
        i += 1.0

    print('Inserting Initial Water levels...')
    with open(INIT_WL_CONFIG) as initWLConfFile:
        initWaterLevels = initWLConfFile.readlines()
        for initWaterLevel in initWaterLevels:
            if len(initWaterLevel.split()):
                lines.append(initWaterLevel)

    f.writelines(lines)

    # Save Forecast values into Database
    opts = {
        'forceInsert': forceInsert,
        'runName': runName
    }
    if storeData:
        adapter = MySQLAdapter(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, db=MYSQL_DB)
        save_forecast_timeseries(adapter, csvList[CSV_NUM_METADATA_LINES:], date, time, opts)
    else:
        print("---------------------------------------Mysql db not updated.-------------------------------------")

except Exception as e :
    print(e)
    traceback.print_exc()
finally:
    f.close()
    print('Completed ', DISCHARGE_CSV_FILE_PATH, ' to ', INFLOW_DAT_FILE_PATH)
