#!/usr/bin/bash
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
bot_data_folder=$1
if [[ $# == 2 ]];
then
    repo=$2
else
    repo=/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data
fi

weekly=w_2021_43
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
setup -r /sdf/group/lsst/software/IandT/eotask-gen3 -j
export OMP_NUM_THREADS=1
timestamp=`date +%Y-%m-%d_%H.%M.%S`
log_file=${script_dir}/bot_ingest_${timestamp}.log
job_name=ingest-bot-${bot_data_folder}

srun --time=05:00:00 --output=${log_file} --job-name=${job_name} \
    --mail-user=cam-bot-gen3-ingest-aaaaeubc3mngg4xb2sq6gvwc4e@lsstc.slack.com \
    --mail-type=FAIL \
    python ${script_dir}/ingest_bot_data.py --repo ${repo} ${bot_data_folder} &
