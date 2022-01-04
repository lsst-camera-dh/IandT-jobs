#!/usr/bin/env python
"""
Script to re-ingest raw data based on run number.
"""
import os
import glob
import argparse
import pathlib
import subprocess
from lsst.daf.butler import Butler

parser = argparse.ArgumentParser()
parser.add_argument('run', type=str, help='Run to re-ingest')
parser.add_argument('repo', type=str, help='Data repository')
parser.add_argument('--collection', type=str, default='LSSTCam/raw/all',
                    help='Collection containing the raw data')
args = parser.parse_args()

Run = args.run
repo = args.repo
collection = args.collection

# Find the frames associated with the specified run and save the
# exposure number if a .compress file exists and has
# os.stat(...).st_ctime more recent than the _index.json file.
frame_dirs = dict()
butler = Butler(repo, collections=[collection])
where = f"instrument='LSSTCam' and exposure.science_program='{Run}'"
dsrefs = list(butler.registry.queryDatasets('raw', where=where))
num_ds_orig = len(dsrefs)
for dsref in dsrefs:
    frame_dir = os.path.dirname(butler.getURI('raw', dsref.dataId).path)
    compress_md_file = os.path.join(frame_dir, '.compress')
    index_file = os.path.join(frame_dir, '_index.json')
    if (os.path.isfile(compress_md_file) and
        os.stat(compress_md_file).st_ctime > os.stat(index_file).st_ctime):
        exposure = dsref.dataId['exposure']
        if exposure not in frame_dirs:
            frame_dirs[exposure] = frame_dir
            print(exposure, frame_dir, flush=True)

# Prune the datasets, using the `where` clause to prune files for the
# compressed exposures.
for exposure in frame_dirs:
    where = f"instrument='LSSTCam' and exposure={exposure}"
    command = (f'butler prune-datasets --no-confirm --purge {collection} '
               f'--where "{where}" {repo} {collection}')
    print(command)
    subprocess.check_call(command, shell=True)

# Loop over BOT frames and re-ingest into the data repository.
for frame_dir in frame_dirs.values():
    command = f'butler ingest-raws --transfer=direct {repo} {frame_dir}'
    print(command)
    subprocess.check_call(command, shell=True)
    # Update the .st_ctime of the _index.json file.
    index_file = os.path.join(frame_dir, '_index.json')
    try:
        pathlib.Path(index_file).touch()
    except PermissionError:
        pass

# Check that the re-ingested run has the same number of datasets
# as before.
butler = Butler(repo, collections=[collection])
num_ds = len(list(butler.registry.queryDatasets('raw', where=where)))
if num_ds != num_ds_orig:
    raise RuntimeError('mismatch in numbers of original files and re-ingested:'
                       f'{num_ds_orig} versus {num_ds}.')
