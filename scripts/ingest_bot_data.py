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
parser.add_argument('--max_seqnum', type=int, default=None,
                    help='maximum sequence number to ingest')
parser.add_argument('--bad_frame_file', type=str, default=None,
                    help='file containing list of bad frames to skip')

args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(name)s: %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger('ingest_bot_data.py')
logger.setLevel(logging.INFO)

bad_frames = set()
if args.bad_frame_file is not None and os.path.isfile(args.bad_frame_file):
    with open(args.bad_frame_file) as fd:
        for line in fd:
            bad_frames.add(line.strip('\n'))
print('bad frames:', bad_frames)

def run_command(command):
    subprocess.check_call(command, shell=True)
    print(command)

def get_seqnum(frame):
    return int(frame.split('_')[-1])

# Make a list of non-empty frame subfolders with seqnum >= args.min_seqnum
# and seqnum <= args.max_seqnum.
if (os.path.basename(args.bot_data_folder).startswith('MC_C_') or
    os.path.basename(args.bot_data_folder).startswith('TS_C_')):
    # args.bot_data_folder is pointing at a single BOT/TS8 frame, rather
    # than its parent directory, so just make a single element list with
    # args.bot_data_folder as the entry.
    frame_folders = [args.bot_data_folder]
else:
    # Assume args.bot_data_folder is a day's worth of BOT/TS8 frames.
    pattern = os.path.join(args.bot_data_folder, f'{args.frame_prefix}*')
    frame_folders = [_ for _ in sorted(glob.glob(pattern)) if
                     (glob.glob(os.path.join(_, '*.fits')) and
                      (args.min_seqnum is None or
                       get_seqnum(_) >= args.min_seqnum) and
                      (args.max_seqnum is None or
                       get_seqnum(_) <= args.max_seqnum))]
print(frame_folders)

INDEX_NAME = '_index.json'
# Add the index files to each folder.
access_restricted = []
fhe_failures = []
corrupted = []
for folder in frame_folders:
    if os.path.isfile(os.path.join(folder, INDEX_NAME)):
        # Skip if index file already exists.
        continue
    if not os.access(folder, os.W_OK):
        # Need write access to make the index file. If not accessible,
        # add to list for later reporting.
        access_restricted.append(folder)
        continue
    if os.path.basename(folder) in bad_frames:
        continue
    # Skip folder if any file sizes are zero, possibly indicating
    # corrupted data.
    pattern = os.path.join(folder, f'{args.frame_prefix}*')
    if any([os.path.getsize(_) == 0 for _ in glob.glob(pattern)]):
        corrupted.append(folder)
        continue
    #command = ('astrometadata -p lsst.obs.lsst.translators write-index '
    #           f'--content=metadata {folder}')
    # Use Tony's faster fhe tool to make the index files.
    command = f'/sdf/group/lsst/sw/ccs/bin/fhe --dir {folder} -vvv'
    try:
        run_command(command)
    except subprocess.CalledProcessError:
        fhe_failures.append(folder)
        # Delete any _index.json file that was written.
        command = f'rm -f {folder}/{INDEX_NAME}'
        run_command(command)

# Run butler ingest-raws on each folder.
missing_keywords = []
required_keywords = ['EXPTIME', 'RUNNUM']
for folder in frame_folders:
    print('processing', folder)
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
    run_command(command)

    # Run eotask-gen3/eoIngestPd.py to ingest photodiode readings files.
    pd_files = glob.glob(os.path.join(folder, 'Photodiode_Readings*.txt'))
    if pd_files:
        file_list = ' '.join(pd_files)
        command = f'eoIngestPd.py -b {args.repo} {file_list}'
        run_command(command)

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
    logger.info('\n')

if fhe_failures:
    logger.info(f'{len(fhe_failures)} frames that failed _index.json '
                'generation:')
    for folder in fhe_failures:
        logger.info(' %s', folder)

if corrupted:
    logger.info(f'{len(corrupted)} frames:')
    for folder in corrupted:
        logger.info(' %s', folder)

if access_restricted or fhe_failures:
    raise RuntimeError('access_restricted or fhe_failures')
