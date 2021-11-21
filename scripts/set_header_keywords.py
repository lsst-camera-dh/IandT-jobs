"""
Script to update the header keywords for data taken in R_and_D
mode so that the files can be ingested into a gen3 repo.
"""
import os
import sys
import glob
import yaml
import argparse
from astropy.io import fits

parser = argparse.ArgumentParser()
parser.add_argument('bot_data_folder', type=str,
                    help='Name of BOT data folder to add a run number')
parser.add_argument('--keyword_file', type=str, default='phdu_keywords.yaml',
                    help="file with PHDU key/value pairs to set")
parser.add_argument('--frame_prefix', type=str, default='[MT][CS]_C_',
                    help='glob pattern prefix for each frame')
parser.add_argument('--min_seqnum', type=int, default=None,
                    help=('Minimum sequence number to process to enable '
                          'skipping already-processed files'))

args = parser.parse_args()

pattern = os.path.join(args.bot_data_folder, f'{args.frame_prefix}*', '*.fits')
raw_files = sorted(glob.glob(pattern))

with open(args.keyword_file) as fd:
    phdu_keywords = yaml.safe_load(fd)

for item in raw_files:
    seq_num = int(os.path.basename(item).split('_')[3])
    if args.min_seqnum is not None and seq_num < args.min_seqnum:
        continue
    with fits.open(item) as hdus:
        print(item)
        sys.stdout.flush()
        for key, value in phdu_keywords.items():
            hdus[0].header[key] = value
        hdus.writeto(item, overwrite=True)
