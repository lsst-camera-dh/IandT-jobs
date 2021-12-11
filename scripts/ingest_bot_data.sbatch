#!/usr/bin/bash
#SBATCH --partition=shared
#SBATCH --mail-user=cam-bot-gen3-ingest-aaaaeubc3mngg4xb2sq6gvwc4e@lsstc.slack.com
#SBATCH --mail-type=FAIL
#SBATCH --cpus-per-task=1

weekly=w_2021_43
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
setup -r /sdf/group/lsst/software/IandT/eotask-gen3 -j
export OMP_NUM_THREADS=1
timestamp=`date +%Y-%m-%d_%H.%M.%S`

echo ${REPO} ${BOT_DATA_FOLDER}
eups list lsst_distrib
python ${SCRIPT_DIR}/ingest_bot_data.py --repo ${REPO} ${BOT_DATA_FOLDER} \
    --bad_frame_file ${SCRIPT_DIR}/bad_frames.txt
