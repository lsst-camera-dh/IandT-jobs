#!/usr/bin/env python
"""
Producer script for BOT_acq_recovery harnessed job.

Given an acq_run number, specified in the lcatr.cfg file, this job
will collect the symlinks to the frames from all of the retry attempts
in the BOT_acq job's working directories for that run and copy the
symlinks to the current working directory.  The activityIds for the
retry attempts will be iterated over in reverse order so that the
first encountered symlink with a given frame name will be the last one
taken, and the data associated with that symlink will be used in the
aggregated data.  Subsequent symlinks with that frame name are
presumably from prior acquisitions attempts and are more likely to be
corrupted or incomplete and so will be ignored.
"""
import os
import glob
import shutil
import pathlib
import siteUtils

# Get the acq_run to use for the data recovery and aggregation from
# lcatr.cfg.
acq_run = os.environ['LCATR_ACQ_RUN']

# Get any bad frames from a text file specified in lcatr.cfg.
try:
    with open(os.environ['LCATR_BAD_FRAME_LIST'], 'r') as fd:
        bad_frames = [_.strip() for _ in fd]
except KeyError:
    bad_frames = []

staging_dir = os.path.join(os.environ['LCATR_STAGE_ROOT'],
                           siteUtils.getUnitType(), siteUtils.getUnitId())
outdir = '.'
acqs_dir = os.path.join(staging_dir, acq_run, 'BOT_acq', 'v0')
job_id_dirs = sorted(glob.glob(os.path.join(acqs_dir, '[0-9]*')), reverse=True)
for job_id_dir in job_id_dirs:
    frame_dirs = glob.glob(os.path.join(job_id_dir, '*'))
    for frame_dir in frame_dirs:
        dest = os.path.join(outdir, os.path.basename(frame_dir))
        if ((os.path.islink(frame_dir) or frame_dir.endswith('.cfg'))
            and not os.path.lexists(dest)):
            shutil.copyfile(frame_dir, dest, follow_symlinks=False)

# Delete any folders with bad data
fits_images = []
for bad_frame in bad_frames:
    pattern = os.path.join('*', f'*{bad_frame}*.fits')
    fits_images.extend(glob.glob(pattern))
bad_symlinks = set([os.path.dirname(_) for _ in fits_images])
for bad_symlink in bad_symlinks:
    os.remove(bad_symlink)

pathlib.Path('PRESERVE_SYMLINKS').touch()
