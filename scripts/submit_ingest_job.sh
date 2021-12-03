#!/usr/bin/bash
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
bot_data_folder=$1
if [[ $# == 2 ]];
then
    repo=$2
else
    repo=/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data
fi

export SCRIPT_DIR=${script_dir}
export REPO=${repo}
export BOT_DATA_FOLDER=${bot_data_folder}

timestamp=`date +%Y-%m-%d_%H.%M.%S`
log_file=${script_dir}/bot_ingest_${timestamp}.log
job_name=ingest-bot-${bot_data_folder}
job_time=`python ${script_dir}/estimate_job_time.py ${bot_data_folder}`
echo ${job_time}

sbatch --export=ALL --output=${log_file} --job-name=${job_name} \
    --time=${job_time} ${script_dir}/ingest_bot_data.sbatch
