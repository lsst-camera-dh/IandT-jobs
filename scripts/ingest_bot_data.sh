#!/usr/bin/bash
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
repo=/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data
#repo=/sdf/home/j/jchiang/BOT_gen3_testing/file_transfer/transfer_test_repo
bot_data_folder=$1

weekly=w_2021_39
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
export OMP_NUM_THREADS=1
timestamp=`date +%Y-%m-%d_%H.%M.%S`
log_file=${script_dir}/bot_ingest_${timestamp}.log
srun --time=02:00:00 --output=${log_file} \
    python ${script_dir}/ingest_bot_data.py --repo ${repo} ${bot_data_folder} \
    && : || echo -e "Subject: BOT ingest failure\n\n${log_file}\n" \
    | sendmail cam-bot-gen3-ingest-aaaaeubc3mngg4xb2sq6gvwc4e@lsstc.slack.com &
