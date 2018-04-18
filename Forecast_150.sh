#!/bin/bash

#
# ./Forecast.sh -d <FORECAST_DATE>
#   e.g. ./Forecast.sh -d 2017-03-22
#
usage() {
cat <<EOF
Usage: ./Forecast.sh [-d FORECAST_DATE] [-t FORECAST_TIME] [-c CONFIG_FILE] [-r ROOT_DIR] [-b DAYS_BACK] [-f]

    -h      Show usage
    -d      Model State Date which need to run the forecast in YYYY-MM-DD format. Default is current date.
    -t      Model State Time which need to run the forecast in HH:MM:SS format. Default is current hour. Run on hour resolution only.
    --start-date    Start date of timeseries which need to run the forecast in YYYY-MM-DD format. Default is same as -d(date).
    --start-time    Start time of timeseries which need to run the forecast in HH:MM:SS format. Default is same as -t(time).
                    NOTE: Not working for the moment. Since Model states are stored in daily basis.
    -m|--mode       Forecast running mode one of 'd'-daily, 'h'-hourly. Default mode is 'd'.
    -c      Location of CONFIG.json. Default is Forecast.sh exist directory.
    -r      ROOT_DIR which is program running directory. Default is Forecast.sh exist directory.
    -b      Run forecast specified DAYS_BACK with respect to current date. Expect an integer.
            When specified -d option will be ignored.
    -B      Run forecast specified BACK_START with respect to model state date. Expect an integer.
            When specified --start-date option will be ignored.
    -f      Force run forecast. Even the forecast already run for the particular day, run again. Default is false.
    -i      Initiate a State at the end of HEC-HMS run.
    -s      Store Timeseries data on MySQL database.
    -e      Exit without executing models which run on Windows.
    -C      (Control Interval in minutes) Time period that HEC-HMS model should run

    -T|--tag    Tag to differential simultaneous Forecast Runs E.g. wrf1, wrf2 ...

    --wrf-out       Path of WRF_OUTPUT directory. If this is set, then 
                        <WRF_OUT>/RF                    (<-RF_DIR_PATH)
                        <WRF_OUT>/kelani-upper-basin    (<-KUB_DIR_PATH)
                        <WRF_OUT>/colombo               (<-RF_GRID_DIR_PATH)
                        <WRF_OUT>/kelani-basin          (<-FLO2D_RAINCELL_DIR_PATH)
                    will use respectively instead of CONFIG.json.
                    Otherwise using the values from CONFIG.json
    --wrf-rf        Path of WRF Rf(Rainfall) Directory. Otherwise using the 'RF_DIR_PATH' from CONFIG.json
    --wrf-kub       Path of WRF kelani-upper-basin(KUB) Directory. Otherwise using the 'KUB_DIR_PATH' from CONFIG.json
    --wrf-rf-grid   Path of WRF colombo(RF_GRID) Directory. Otherwise using the 'RF_GRID_DIR_PATH' from CONFIG.json
    --wrf-raincell  Path of WRF kelani-basin(Raincell) Directory. Otherwise using the 'RF_DIR_PATH' from CONFIG.json

    --hec-hms-model-dir  Path of HEC_HMS_MODEL_DIR directory. Otherwise using the 'HEC_HMS_MODEL_DIR' from CONFIG.json
    -n|--name            Name field value of the Run table in Database. Use time format such as 'Cloud-1-<%H:%M:%S>' to replace with time(t).
EOF
}

trimQuotes() {
    tmp="${1%\"}"
    tmp="${tmp#\"}"
    echo ${tmp}
}
# replaceStringVariable <variableName> <replacingVariableName> <replacingVariableValue>
replaceStringVariable() {
    # E.g. Working example of replacing "${HEC_HMS_MODEL_DIR}/2008_2_Events_input.dss"
    # with HEC_HMS_MODEL_DIR="./2008_2_Events"
    #
    # if [[ "$DSS_INPUT_FILE" =~ ^\$\{(HEC_HMS_MODEL_DIR)\} ]]; then
    #     DSS_INPUT_FILE=${DSS_INPUT_FILE/\$\{HEC_HMS_MODEL_DIR\}/$HEC_HMS_MODEL_DIR}
    # fi

    if [[ "$1" =~ ^\$\{("$2")\} ]]; then
        echo ${1/\$\{$2\}/"$3"}
    else
        echo $1
    fi
}


ROOT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INIT_DIR=$(pwd)
CONFIG_FILE=${ROOT_DIR}/CONFIG.json

# cd into bash script's root directory
cd ${ROOT_DIR}
echo "Current Working Directory set to -> $(pwd)"
if [ -z "$(find ${CONFIG_FILE} -name CONFIG.json)" ]; then
    echo "Unable to find $CONFIG_FILE file"
    exit 1
fi

HOST_ADDRESS=$(trimQuotes $(cat CONFIG.json | jq '.HOST_ADDRESS'))
HOST_PORT=$(cat CONFIG.json | jq '.HOST_PORT')
WINDOWS_HOST="$HOST_ADDRESS:$HOST_PORT"

RF_FORECASTED_DAYS=$(trimQuotes $(cat CONFIG.json | jq '.RF_FORECASTED_DAYS'))
RF_DIR_PATH=$(trimQuotes $(cat CONFIG.json | jq '.RF_DIR_PATH'))
KUB_DIR_PATH=$(trimQuotes $(cat CONFIG.json | jq '.KUB_DIR_PATH'))
RF_GRID_DIR_PATH=$(trimQuotes $(cat CONFIG.json | jq '.RF_GRID_DIR_PATH'))
FLO2D_RAINCELL_DIR_PATH=$(trimQuotes $(cat CONFIG.json | jq '.FLO2D_RAINCELL_DIR_PATH'))

OUTPUT_DIR=$(trimQuotes $(cat CONFIG.json | jq '.OUTPUT_DIR'))
STATUS_FILE=$(trimQuotes $(cat CONFIG.json | jq '.STATUS_FILE'))

HEC_HMS_MODEL_DIR=$(trimQuotes $(cat CONFIG.json | jq '.HEC_HMS_MODEL_DIR'))
HEC_HMS_MODEL_HACK_DIR=$(trimQuotes $(cat CONFIG.json | jq '.HEC_HMS_MODEL_HACK_DIR'))
HEC_HMS_DIR=$(trimQuotes $(cat CONFIG.json | jq '.HEC_HMS_DIR'))
HEC_DSSVUE_DIR=$(trimQuotes $(cat CONFIG.json | jq '.HEC_DSSVUE_DIR'))
DSS_INPUT_FILE=$(trimQuotes $(cat CONFIG.json | jq '.DSS_INPUT_FILE'))
DSS_OUTPUT_FILE=$(trimQuotes $(cat CONFIG.json | jq '.DSS_OUTPUT_FILE'))

INFLOW_DAT_FILE=$(trimQuotes $(cat CONFIG.json | jq '.INFLOW_DAT_FILE'))
OUTFLOW_DAT_FILE=$(trimQuotes $(cat CONFIG.json | jq '.OUTFLOW_DAT_FILE'))
META_FLO2D_DIR=${ROOT_DIR}/META_FLO2D
FLO2D_DIR=${ROOT_DIR}/FLO2D

forecast_date="`date +%Y-%m-%d`";
forecast_time="`date +%H:00:00`";
timeseries_start_date="";
# timeseries_start_time="`date +%H:00:00`";
timeseries_start_time="`date +00:00:00`";
rf_forecasted_date="`date -d "${forecast_date} ${RF_FORECASTED_DAYS} days" +'%Y-%m-%d'`";

MODE="d" # 'd' | 'h'
DAYS_BACK=0
BACK_START=0
FORCE_RUN=false
INIT_STATE=false
STORE_DATA=false
FORCE_EXIT=false
CONTROL_INTERVAL=0
TAG=""
WRF_OUT="/hec-hms"
RUN_NAME=""

HEC_HMS_ID="hec_hms0_2018-04-17_15:39_c6xe"
WRF_ID="wrf0_2018-04-15_18:00_f2Nq"

# Read the options
# Ref: http://www.bahmanm.com/blogs/command-line-options-how-to-parse-in-bash-using-getopt
TEMP=`getopt -o hd:t:m:c:r:b:B:fiseC:T:n: \
        --long arga::,argb,argc:,start-date:,start-time:,mode:,tag:,wrf-out:,hec-hms-model-dir:,name: \
        -n 'Forecast.sh' -- "$@"`

# Terminate on wrong args. Ref: https://stackoverflow.com/a/7948533/1461060
if [ $? != 0 ] ; then usage >&2 ; exit 1 ; fi

eval set -- "${TEMP}"

# Extract options and their arguments into variables.
while true ; do
    case "$1" in
        # -a|--arga)
        #     case "$2" in
        #         "") ARG_A='some default value' ; shift 2 ;;
        #         *) ARG_A=$2 ; shift 2 ;;
        #     esac ;;
        # -b|--argb) ARG_B=1 ; shift ;;
        # -c|--argc)
        #     case "$2" in
        #         "") shift 2 ;;
        #         *) ARG_C=$2 ; shift 2 ;;
        #     esac ;;

        -h)
            usage >&2
            exit 0
            shift ;;
        -d)
            case "$2" in
                "") shift 2 ;;
                *) forecast_date="$2" ; shift 2 ;;
            esac ;;
        -t)
            case "$2" in
                "") shift 2 ;;
                *) forecast_time="$2" ; shift 2 ;;
            esac ;;
        --start-date)
            case "$2" in
                "") shift 2 ;;
                *) timeseries_start_date="$2" ; shift 2 ;;
            esac ;;
        --start-time)
            case "$2" in
                "") shift 2 ;;
                *) timeseries_start_time="$2" ; shift 2 ;;
            esac ;;
        -m|--mode)
            case "$2" in
                "") shift 2 ;;
                *) MODE="$2" ; shift 2 ;;
            esac ;;
        -c)
            case "$2" in
                "") shift 2 ;;
                *) CONFIG_FILE="$2" ; shift 2 ;;
            esac ;;
        -r)
            case "$2" in
                "") shift 2 ;;
                *) ROOT_DIR="$2" ; shift 2 ;;
            esac ;;
        -b)
            case "$2" in
                "") shift 2 ;;
                *) DAYS_BACK="$2" ; shift 2 ;;
            esac ;;
        -B)
            case "$2" in
                "") shift 2 ;;
                *) BACK_START="$2" ; shift 2 ;;
            esac ;;
        -f)  FORCE_RUN=true ; shift ;;
        -i)  INIT_STATE=true ; shift ;;
        -s)  STORE_DATA=true ; shift ;;
        -e)  FORCE_EXIT=true ; shift ;;
        -C)
            case "$2" in
                "") shift 2 ;;
                *) CONTROL_INTERVAL="$2" ; shift 2 ;;
            esac ;;
        -T|--tag)
            case "$2" in
                "") shift 2 ;;
                *) TAG="$2" ; shift 2 ;;
            esac ;;
        --wrf-out)
            case "$2" in
                "") shift 2 ;;
                *) WRF_OUT="$2" ; shift 2 ;;
            esac ;;
        --hec-hms-model-dir)
            case "$2" in
                "") shift 2 ;;
                *) HEC_HMS_MODEL_DIR="$2" ; shift 2 ;;
            esac ;;
        -n|--name)
            case "$2" in
                "") shift 2 ;;
                *) RUN_NAME="$2" ; shift 2 ;;
            esac ;;

        --) shift ; break ;;
        *) usage >&2 ; exit 1 ;;
    esac
done

if [ "$DAYS_BACK" -gt 0 ]; then
    #TODO: Try to back date base on user given date
    forecast_date="`date +%Y-%m-%d -d "$DAYS_BACK days ago"`";
fi
if [ "$BACK_START" -gt 0 ]; then
    timeseries_start_date="`date +%Y-%m-%d -d "$forecast_date -$BACK_START days"`";
fi
if [ -z ${timeseries_start_date} ]; then
    timeseries_start_date=${forecast_date}
fi
if [[ "$MODE" == "d" ]]; then
    forecast_time="`date +00:00:00`";
fi
# Set the date of RF Forecasts are available for current run
rf_forecasted_date="`date -d "${forecast_date} ${RF_FORECASTED_DAYS} days" +'%Y-%m-%d'`";

current_date_time="`date +%Y-%m-%dT%H:%M:%S`";

main() {
    if [[ "$TAG" =~ [^a-zA-Z0-9\ ] ]]; then
        echo "Parameter for -T|--tag is \"$TAG\" invalid. It can only contain alphanumeric values."
        exit 1;
    fi

    if [ ! -z ${TAG} ]; then
        INFLOW_DAT_FILE=${INFLOW_DAT_FILE/.DAT/".$TAG.DAT"}
        OUTFLOW_DAT_FILE=${OUTFLOW_DAT_FILE/.DAT/".$TAG.DAT"}
        HEC_HMS_MODEL_DIR=${HEC_HMS_MODEL_DIR}.${TAG}
    fi

    if [ ! -z ${WRF_OUT} ] && [ -d ${WRF_OUT} ]; then
        RF_DIR_PATH=${WRF_OUT}/RF
        KUB_DIR_PATH=${WRF_OUT}/kelani-upper-basin
        RF_GRID_DIR_PATH=${WRF_OUT}/colombo
        FLO2D_RAINCELL_DIR_PATH=/home/uwcc-admin/udp_150/Raincell/${forecast_date}
        echo "WRF OUT paths changed to -> $RF_DIR_PATH, $KUB_DIR_PATH, $RF_GRID_DIR_PATH, $FLO2D_RAINCELL_DIR_PATH"
    fi
    RF_DIR_PATH=${RF_DIR_PATH}/${forecast_date}
    KUB_DIR_PATH=${KUB_DIR_PATH}/${forecast_date}
    FLO2D_RAINCELL_DIR_PATH=${FLO2D_RAINCELL_DIR_PATH}/${forecast_date}
    echo "------------------------------xxxxxxxxxxxxxxx---------------------------------"
    echo "RF_DIR_PATH:"$RF_DIR_PATH
	echo "KUB_DIR_PATH:"$KUB_DIR_PATH
	echo "RF_GRID_DIR_PATH:"$RF_GRID_DIR_PATH
	echo "FLO2D_RAINCELL_DIR_PATH:"$FLO2D_RAINCELL_DIR_PATH
	echo "HEC_HMS_MODEL_DIR:"$HEC_HMS_MODEL_DIR
    echo "------------------------------xxxxxxxxxxxxxxx---------------------------------"

    echo "HEC_HMS_MODEL_DIR=$HEC_HMS_MODEL_DIR"
    DSS_INPUT_FILE=$(replaceStringVariable ${DSS_INPUT_FILE} "HEC_HMS_MODEL_DIR" ${HEC_HMS_MODEL_DIR})
    echo "Set DSS_INPUT_FILE=$DSS_INPUT_FILE"
    DSS_OUTPUT_FILE=$(replaceStringVariable ${DSS_OUTPUT_FILE} "HEC_HMS_MODEL_DIR" ${HEC_HMS_MODEL_DIR})
    echo "Set DSS_OUTPUT_FILE=$DSS_OUTPUT_FILE"

    echo "Start at $current_date_time $FORCE_EXIT"
    echo "Forecasting with Forecast Date: $forecast_date @ $forecast_time, Config File: $CONFIG_FILE, Root Dir: $ROOT_DIR"
    echo "With Custom Timeseries Start Date: $timeseries_start_date @ $timeseries_start_time using RF data of $rf_forecasted_date"
    local forecastStatus=$(alreadyForecast ${ROOT_DIR}/${STATUS_FILE} ${forecast_date})
    if [ ${FORCE_RUN} == true ]; then
        forecastStatus=0
    fi
    echo $forecast_date
    result=`./FilesFromBucket.py ${WRF_ID}`
    echo $result
    if [ "$result" == "proceed" ]; then
        if [ ${forecastStatus} == 0 ]; then
            mkdir ${OUTPUT_DIR}
            # Read WRF forecast data, then create precipitation .csv for Upper Catchment
            # using Theissen Polygon
            ./RFTOCSV.py -d ${forecast_date} -t ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                --wrf-rf ${RF_DIR_PATH} --wrf-kub ${KUB_DIR_PATH} \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"`

            # HACK: There is an issue with running HEC-HMS model, it gave a sudden value change after 1 day
            # We discovered that, this issue on 3.5 version, hence upgrade into 4.1
            # But with 4.1, it runs correctly when the data are saved by the HEC-HMS program
            # After run the model using the script, it can't reuse for a correct run again
            # Here we reuse a corrected model which can run using the script
            if [ ! -d "$HEC_HMS_MODEL_DIR" ]; then
                mkdir ${HEC_HMS_MODEL_DIR}
            fi
            yes | cp -R ${HEC_HMS_MODEL_HACK_DIR}/* ${HEC_HMS_MODEL_DIR}

            # Remove .dss files in order to remove previous results
            rm ${DSS_INPUT_FILE}
            rm ${DSS_OUTPUT_FILE}
            # Read Avg precipitation, then create .dss input file for HEC-HMS model
                ./hec-dssvue201/hec-dssvue.sh CSVTODSS.py --date ${forecast_date} --time ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"` \
                `[[ -z ${HEC_HMS_MODEL_DIR} ]] && echo "" || echo "--hec-hms-model-dir $HEC_HMS_MODEL_DIR"`

            # Change HEC-HMS running time window
            ./Update_HECHMS.py -d ${forecast_date} -t ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                `[[ ${INIT_STATE} == true ]] && echo "-i" || echo ""` \
                `[[ ${CONTROL_INTERVAL} == 0 ]] && echo "" || echo "-c $CONTROL_INTERVAL"` \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"` \
                `[[ -z ${HEC_HMS_MODEL_DIR} ]] && echo "" || echo "--hec-hms-model-dir $HEC_HMS_MODEL_DIR"`

            # "HEC_HMS_MODEL_DIR" : "./2008_2_Events"
            # HEC_HMS_SCRIPT_PATH = "./2008_2_Events/2008_2_Events.script"
            # "HEC_HMS_DIR"       : "hec-hms41"

            # Run HEC-HMS model
            HEC_HMS_SCRIPT_PATH=${HEC_HMS_MODEL_DIR}/2008_2_Events.script
            # TODO: Check python3 availability
            HEC_HMS_SCRIPT_RELATIVE_PATH=$(python3 -c "import os.path; print(os.path.relpath('$HEC_HMS_SCRIPT_PATH', '$HEC_HMS_DIR'))")
            cd ${HEC_HMS_DIR}
            if [ -z "$(find ${HEC_HMS_SCRIPT_RELATIVE_PATH} -name 2008_2_Events.script)" ]; then
                echo "Unable to find $HEC_HMS_SCRIPT_RELATIVE_PATH file"
                exit 1
            fi
            # Set FLO2D model path
            # OpenProject("Model_Name", "Model folder path")
            HEC_HMS_PROJECT_RELATIVE_PATH=$(python3 -c "import os.path; print(os.path.relpath('$HEC_HMS_MODEL_DIR', '$HEC_HMS_DIR'))")
            HEC_HMS_PROJECT_NAME="2008_2_Events$([[ -z ${TAG} ]] && echo "" || echo "")" # Do nothing
            HEC_HMS_PROJECT_TXT="OpenProject(\"$HEC_HMS_PROJECT_NAME\", \"$HEC_HMS_PROJECT_RELATIVE_PATH\")"

            #sed -i "/OpenProject/c\\$HEC_HMS_PROJECT_TXT" ${HEC_HMS_SCRIPT_RELATIVE_PATH}

            ./hec-hms.sh -s ${HEC_HMS_SCRIPT_RELATIVE_PATH}
            ret=$?
            if [ ${ret} -ne 0 ]; then
                 echo "Error in running HEC-HMS Model"
                 exit 1
            fi
            cd ${ROOT_DIR}
            # Read HEC-HMS result, then extract Discharge into .csv
            ./hec-dssvue201/hec-dssvue.sh DSSTOCSV.py --date ${forecast_date} --time ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"` \
                `[[ -z ${HEC_HMS_MODEL_DIR} ]] && echo "" || echo "--hec-hms-model-dir $HEC_HMS_MODEL_DIR"`

            # Read Discharge .csv, then create INFLOW.DAT file for FLO2D
            ./CSVTODAT.py  -d ${forecast_date} -t ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"` \
                `[[ -z ${FORCE_RUN} ]] && echo "" || echo "-f"` \
                `[[ -z ${RUN_NAME} ]] && echo "" || echo "--name $RUN_NAME"`
            ret=$?
            if [ ${ret} -ne 0 ]; then
                 echo "Error in converting Discharge CSV to FLO2D INFLOW.DAT"
                 exit 1
            fi

            # Read Tidal Forecast values, then create OUTFLOW.DAT file for FLO2D
            ./TIDAL_TO_OUTFLOW.py  -d ${forecast_date} -t ${forecast_time} \
                --start-date ${timeseries_start_date} --start-time ${timeseries_start_time} \
                `[[ -z ${TAG} ]] && echo "" || echo "--tag $TAG"` \
                `[[ -z ${FORCE_RUN} ]] && echo "" || echo "-f"` \
                `[[ -z ${RUN_NAME} ]] && echo "" || echo "--name $RUN_NAME"`
            ret=$?
            if [ ${ret} -ne 0 ]; then
                 echo "Error in creating FLO2D OUTFLOW.DAT using Tidal data"
                 exit 1
            fi
            ./FilesToBucket.py ${HEC_HMS_ID}
            ret=$?
            if [ ${ret} -ne 0 ]; then
                 echo "Error in uploading INFLOW.DAT and OUTFLOW.DAT to bucket"
                 exit 1
            fi
        else
            echo "WARN: Already run the forecast. Quit"
            exit 1
        fi
    else
        echo "WARN: No required files found. Quit"
        exit 1
    fi
}


writeForecastStatus() {
    echo $1 >> $2
}

alreadyForecast() {
    local forecasted=0

    while IFS='' read -r line || [[ -n "$line" ]]; do
        if [ $2 == ${line} ]; then
            forecasted=1
            break
        fi
    done < "$1"
    echo ${forecasted}
}

main "$@"

# End of Forecast.sh
