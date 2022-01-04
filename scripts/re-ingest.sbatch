#!/usr/bin/bash
#SBATCH --partition=shared
#SBATCH --mail-user=cam-bot-gen3-ingest-aaaaeubc3mngg4xb2sq6gvwc4e@lsstc.slack.com
#SBATCH --mail-type=FAIL
#SBATCH --cpus-per-task=1

REPO=/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data
weekly=w_2021_43
source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/${weekly}/loadLSST.bash
setup lsst_distrib
export OMP_NUM_THREADS=1
timestamp=`date +%Y-%m-%d_%H.%M.%S`

echo ${RUN} ${REPO}
eups list lsst_distrib
python ${SCRIPT_DIR}/re-ingest.py ${RUN} ${REPO}
