#!/usr/bin/env python
"""
Validator script for BOT_acq harnessed job.
"""
import os
import glob
import lcatr.schema
import siteUtils
from camera_components import camera_info

results = []

if 'LCATR_ACQ_RUN' not in os.environ:
    det_names = camera_info.get_det_names()
    for det_name in det_names:
        fits_files = sorted(glob.glob('*/*_{}.fits'.format(det_name)))
        for item in fits_files:
            results.append(lcatr.schema.fileref.make(item))

    pd_files = sorted(glob.glob('*/Photodiode_Readings.txt'))
    results.extend([lcatr.schema.fileref.make(_) for _ in pd_files])

    acq_config = siteUtils.get_job_acq_configs()
    bot_eo_acq_cfg = os.path.basename(acq_config['bot_eo_acq_cfg'])
    cfg_files = glob.glob(bot_eo_acq_cfg.replace('.cfg', '') + '*.cfg')
    results.extend([lcatr.schema.fileref.make(_) for _ in cfg_files])

    # Get fp-scripts commit and tag info.
    repo_path = os.environ.get('LCATR_FP_SCRIPTS_REPO_DIR', None)
    if repo_path is not None:
        try:
            git_hash, git_tag = siteUtils.get_git_commit_info(repo_path)
        except Exception as eobj:
            print('Error encountered retrieving fp-scripts git info:\n', eobj)
        else:
            schema_values = {'fp-scripts_git_hash': git_hash,
                             'fp-scripts_git_tag': str(git_tag)}
            results.append(lcatr.schema.valid(lcatr.schema.get('BOT_acq'),
                                              **schema_values))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
