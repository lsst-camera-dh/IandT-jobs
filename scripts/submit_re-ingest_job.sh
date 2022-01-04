#!/usr/bin/bash
weekly=w_2021_43
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
export OMP_NUM_THREADS=1

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
run=$1
if [[ $# == 2 ]];
then
    repo=$2
else
    repo=/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data
fi

export SCRIPT_DIR=${script_dir}
export REPO=${repo}
export RUN=${run}

timestamp=`date +%Y-%m-%d_%H.%M.%S`
log_file=${script_dir}/bot_re-ingest_${timestamp}.log
job_name=re-ingest-bot-${run}
job_time=`python ${script_dir}/estimate_re-ingest_time.py ${run}`

sbatch --export=ALL --output=${log_file} --job-name=${job_name} \
    --time=${job_time} ${script_dir}/re-ingest.sbatch
