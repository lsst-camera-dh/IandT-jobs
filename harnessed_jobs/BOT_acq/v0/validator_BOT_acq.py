#!/usr/bin/env python
"""
Validator script for BOT_acq harnessed job.
"""
import os
import shutil
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

    pd_files = sorted(glob.glob('*/Photodiode_Readings*.txt'))
    results.extend([lcatr.schema.fileref.make(_) for _ in pd_files])

    seq_files = glob.glob('*.seq')
    results.extend([lcatr.schema.fileref.make(_) for _ in seq_files])

    ccs_config_file = 'ccs_config.txt'
    if os.path.isfile(ccs_config_file):
        # Add the run number to filename.
        run_number = siteUtils.getRunNumber()
        outfile = f'ccs_config_{run_number}.txt'
        shutil.copy(ccs_config_file, outfile)
        results.append(lcatr.schema.fileref.make(outfile))

    acq_config = siteUtils.get_job_acq_configs()
    bot_eo_acq_cfg = os.path.basename(acq_config['bot_eo_acq_cfg'])
    cfg_files = glob.glob(bot_eo_acq_cfg.replace('.cfg', '') + '*.cfg')
    results.extend([lcatr.schema.fileref.make(_) for _ in cfg_files])

try:
    results = siteUtils.persist_ccs_versions(results)
except Exception as eobj:
    print('Error encountered in persisting CCS versions:\n', eobj)

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
