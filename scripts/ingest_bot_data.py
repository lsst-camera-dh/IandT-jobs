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
                    default='/sdf/group/lsst/camera/IandT/repo_gen3/bot_data')
parser.add_argument('--frame_prefix', type=str, default='MC_C_',
                    help='Folder name prefix for each frame')

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(name)s: %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger('ingest_bot_data.py')
logger.setLevel(logging.INFO)

# Make a list of non-empty frame subfolders
pattern = os.path.join(args.bot_data_folder, f'{args.frame_prefix}*')
frame_folders = [_ for _ in sorted(glob.glob(pattern)) if
                 glob.glob(os.path.join(_, '*.fits'))]

INDEX_NAME = '_index.json'
# Add the index files to each folder.
access_restricted = []
for folder in frame_folders:
    if not os.access(folder, os.W_OK):
        # Need write access to make the index file. If not accessible,
        # add to list for later reporting.
        access_restricted.append(folder)
        continue
    if os.path.isfile(os.path.join(folder, INDEX_NAME)):
        # Skip if index file already exists.
        continue
    #command = ('astrometadata -p lsst.obs.lsst.translators write-index '
    #           f'--content=metadata {folder}')
    # Use Tony's faster fhe tool to make the index files.
    command = f'/sdf/group/lsst/sw/ccs/bin/fhe --dir {folder} -vvv'
    subprocess.check_call(command, shell=True)

if access_restricted:
    logger.info('Access restricted folders:')
    for folder in access_restricted:
        logger.info(' %s', folder)

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

if access_restricted:
    raise RuntimeError('Access restricted folders')

if missing_keywords:
    logger.info('Frames with missing required keywords:')
    for folder in missing_keywords:
        logger.info(' %s', folder)
