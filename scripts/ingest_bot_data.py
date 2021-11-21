"""
Script to ingest BOT data from a folder containing subfolders for
each focal plane frame.
"""
import os
import sys
import glob
import json
import subprocess
import argparse
import logging

parser = argparse.ArgumentParser()
parser.add_argument('bot_data_folder', type=str,
                    help='Name of BOT data folder to ingest')
parser.add_argument('--repo', type=str, help='Gen3 repo',
                    default='/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data')
parser.add_argument('--frame_prefix', type=str, default='[MT][CS]_C_',
                    help='glob pattern prefix for each frame')
parser.add_argument('--min_seqnum', type=int, default=None,
                    help='mininum sequence number to ingest')

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(name)s: %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger('ingest_bot_data.py')
logger.setLevel(logging.INFO)

def get_seqnum(frame):
    return int(frame.split('_')[-1])

# Make a list of non-empty frame subfolders with seqnum >= args.min_seqnum
pattern = os.path.join(args.bot_data_folder, f'{args.frame_prefix}*')
frame_folders = [_ for _ in sorted(glob.glob(pattern)) if
                 (glob.glob(os.path.join(_, '*.fits')) and
                  (args.min_seqnum is None or
                   get_seqnum(_) >= args.min_seqnum))]
print(frame_folders)

INDEX_NAME = '_index.json'
# Add the index files to each folder.
access_restricted = []
for folder in frame_folders:
    if os.path.isfile(os.path.join(folder, INDEX_NAME)):
        # Skip if index file already exists.
        continue
    if not os.access(folder, os.W_OK):
        # Need write access to make the index file. If not accessible,
        # add to list for later reporting.
        access_restricted.append(folder)
        continue
    #command = ('astrometadata -p lsst.obs.lsst.translators write-index '
    #           f'--content=metadata {folder}')
    # Use Tony's faster fhe tool to make the index files.
    command = f'/sdf/group/lsst/sw/ccs/bin/fhe --dir {folder} -vvv'
    subprocess.check_call(command, shell=True)

# Run butler ingest-raws on each folder.
missing_keywords = []
required_keywords = ['EXPTIME', 'RUNNUM']
for folder in frame_folders:
    index_file = os.path.join(folder, INDEX_NAME)
    if not os.path.isfile(index_file):
        # Skip ingest if index file is missing.
        continue
    # Check index file for required keywords
    with open(index_file) as fd:
        indexes = json.load(fd)
    if ('__COMMON__' not in indexes or
        any(_ not in indexes['__COMMON__'] for _ in required_keywords)):
        missing_keywords.append(folder)
        continue
    logger.info('ingesting %s', folder)
    command = (f'butler ingest-raws --transfer=direct {args.repo} {folder}')
    subprocess.check_call(command, shell=True)

    # Run eotask-gen3/eoIngestPd.py to ingest photodiode readings files.
    pd_files = glob.glob(os.path.join(folder, 'Photodiode_Readings*.txt'))
    if pd_files:
        file_list = ' '.join(pd_files)
        command = f'eoIngestPd.py -b {args.repo} {file_list}'
        subprocess.check_call(command, shell=True)

if access_restricted:
    logger.info(f'{len(access_restricted)} access restricted folders:')
    for folder in access_restricted:
        logger.info(' %s', folder)
    logger.info('\n')

if missing_keywords:
    logger.info(f'{len(missing_keywords)} frames with '
                'missing required keywords:')
    for folder in missing_keywords:
        logger.info(' %s', folder)

if access_restricted or missing_keywords:
    raise RuntimeError('Access restricted folders or '
                       'frames with missing keywords')
