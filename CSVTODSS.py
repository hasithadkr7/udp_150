#!/usr/bin/python

# Rainfall CSV file format should follow as 
# https://publicwiki.deltares.nl/display/FEWSDOC/CSV 

import java, csv, sys, datetime, re
from hec.script import MessageBox
from hec.heclib.dss import HecDss
from hec.heclib.util import HecTime
from hec.io import TimeSeriesContainer

from optparse import OptionParser

sys.path.append("./simplejson-2.5.0")
import simplejson as json

try :
    try :
        print 'Jython version: ', sys.version

        CONFIG = json.loads(open('CONFIG.json').read())
        # print('Config :: ', CONFIG)

        NUM_METADATA_LINES = 3;
        HEC_HMS_MODEL_DIR = './2008_2_Events'
        DSS_INPUT_FILE = './2008_2_Events/2008_2_Events_force.dss'
        RAIN_CSV_FILE = 'DailyRain.csv'
        OUTPUT_DIR = './OUTPUT'

        if 'HEC_HMS_MODEL_DIR' in CONFIG :
            HEC_HMS_MODEL_DIR = CONFIG['HEC_HMS_MODEL_DIR']
        if 'DSS_INPUT_FILE' in CONFIG :
            DSS_INPUT_FILE = CONFIG['DSS_INPUT_FILE']
        if 'RAIN_CSV_FILE' in CONFIG :
            RAIN_CSV_FILE = CONFIG['RAIN_CSV_FILE']
        if 'OUTPUT_DIR' in CONFIG :
            OUTPUT_DIR = CONFIG['OUTPUT_DIR']

        date = ''
        time = ''
        startDateTS = ''
        startTimeTS = ''
        tag = ''

        # Passing Commandline Options to Jython. Not same as getopt in python.
        # Ref: http://www.jython.org/jythonbook/en/1.0/Scripting.html#parsing-commandline-options
        # Doc : https://docs.python.org/2/library/optparse.html
        parser = OptionParser(description='Upload CSV data into HEC-HMS DSS storage')
        # ERROR: Unable to use `-d` or `-D` option with OptionParser
        parser.add_option("--date", help="Date in YYYY-MM. Default is current date.")
        parser.add_option("--time", help="Time in HH:MM:SS. Default is current time.")
        parser.add_option("--start-date", help="Start date of timeseries which need to run the forecast in YYYY-MM-DD format. Default is same as -d(date).")
        parser.add_option("--start-time", help="Start time of timeseries which need to run the forecast in HH:MM:SS format. Default is same as -t(date).")
        parser.add_option("-T", "--tag", help="Tag to differential simultaneous Forecast Runs E.g. wrf1, wrf2 ...")
        parser.add_option("--hec-hms-model-dir", help="Path of HEC_HMS_MODEL_DIR directory. Otherwise using the `HEC_HMS_MODEL_DIR` from CONFIG.json")

        (options, args) = parser.parse_args()
        print 'Commandline Options:', options

        if options.date :
            date = options.date
        if options.time :
            time = options.time
        if options.start_date :
            startDateTS = options.start_date
        if options.start_time :
            startTimeTS = options.start_time
        if options.tag :
            tag = options.tag
        if options.hec_hms_model_dir :
            HEC_HMS_MODEL_DIR = options.hec_hms_model_dir
            # Reconstruct DSS_INPUT_FILE path
            dssFileName = DSS_INPUT_FILE.rsplit('/', 1)
            DSS_INPUT_FILE = os.path.join(HEC_HMS_MODEL_DIR, dssFileName[-1])

        # Replace CONFIG.json variables
        if re.match('^\$\{(HEC_HMS_MODEL_DIR)\}', DSS_INPUT_FILE) :
            DSS_INPUT_FILE = re.sub('^\$\{(HEC_HMS_MODEL_DIR)\}', '', DSS_INPUT_FILE).strip("/\\")
            DSS_INPUT_FILE = os.path.join(HEC_HMS_MODEL_DIR, DSS_INPUT_FILE)
            print '"Set DSS_INPUT_FILE=', DSS_INPUT_FILE

        # Default run for current day
        modelState = datetime.datetime.now()
        if date :
            modelState = datetime.datetime.strptime(date, '%Y-%m-%d')
        date = modelState.strftime("%Y-%m-%d")
        if time :
            modelState = datetime.datetime.strptime('%s %s' % (date, time), '%Y-%m-%d %H:%M:%S')
        time = modelState.strftime("%H:%M:%S")

        startDateTimeTS = datetime.datetime.now()
        if startDateTS :
            startDateTimeTS = datetime.datetime.strptime(startDateTS, '%Y-%m-%d')
        else :
            startDateTimeTS = datetime.datetime.strptime(date, '%Y-%m-%d')
        startDateTS = startDateTimeTS.strftime("%Y-%m-%d")

        if startTimeTS :
            startDateTimeTS = datetime.datetime.strptime('%s %s' % (startDateTS, startTimeTS), '%Y-%m-%d %H:%M:%S')
        startTimeTS = startDateTimeTS.strftime("%H:%M:%S")

        print 'Start CSVTODSS.py on ', date, '@', time, tag, HEC_HMS_MODEL_DIR
        print ' With Custom starting', startDateTS, '@', startTimeTS

        myDss = HecDss.open(DSS_INPUT_FILE)
        
        fileName = RAIN_CSV_FILE.rsplit('.', 1)
        # str .format not working on this version
        fileName = '%s-%s%s.%s' % (fileName[0], date, '.'+tag if tag else '', fileName[1])
        RAIN_CSV_FILE_PATH = os.path.join(OUTPUT_DIR, fileName)
        print 'Open Rainfall CSV ::', RAIN_CSV_FILE_PATH
        csvReader = csv.reader(open(RAIN_CSV_FILE_PATH, 'r'), delimiter=',', quotechar='|')
        csvList = list(csvReader)
        
        
        numLocations = len(csvList[0]) - 1
        numValues = len(csvList) - NUM_METADATA_LINES # Ignore Metadata
        locationIds = csvList[1][1:]
        print 'Start reading', numLocations, csvList[0][0], ':', ', '.join(csvList[0][1:])
        print 'Period of ', numValues, 'values'
        print 'Location Ids :', locationIds

        for i in range(0, numLocations):
            print '\n>>>>>>> Start processing ', locationIds[i], '<<<<<<<<<<<<'
            precipitations = []
            for j in range(NUM_METADATA_LINES, numValues + NUM_METADATA_LINES):
                p = float(csvList[j][i+1])
                precipitations.append(p)

            print 'Precipitation of ', locationIds[i], precipitations[:10]
            tsc = TimeSeriesContainer()
            # tsc.fullName = "/BASIN/LOC/FLOW//1HOUR/OBS/"
            # tsc.fullName = '//' + locationIds[i].upper() + '/PRECIP-INC//1DAY/GAGE/'
            tsc.fullName = '//' + locationIds[i].upper() + '/PRECIP-INC//1HOUR/GAGE/'

            print 'Start time : ', csvList[NUM_METADATA_LINES][0]
            start = HecTime(csvList[NUM_METADATA_LINES][0])
            tsc.interval = 60 # in minutes
            times = []
            for value in precipitations :
              times.append(start.value())
              start.add(tsc.interval)
            tsc.times = times
            tsc.values = precipitations
            tsc.numberValues = len(precipitations)
            tsc.units = "MM"
            tsc.type = "PER-CUM"
            myDss.put(tsc)

    except Exception, e :
        MessageBox.showError(' '.join(e.args), "Python Error")
    except java.lang.Exception, e :
        MessageBox.showError(e.getMessage(), "Error")
finally :
    myDss.done()
    print '\nCompleted converting ', RAIN_CSV_FILE_PATH, ' to ', DSS_INPUT_FILE
    print 'done'