#!/usr/bin/bash
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
bot_data_folder=$1

weekly=w_2021_38
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
export OMP_NUM_THREADS=1
timestamp=`date +%Y-%m-%d`
srun --time=02:00:00 --output=${script_dir}/bot_ingest_${timestamp}.log \
     python ${script_dir}/ingest_bot_data.py ${bot_data_folder}
