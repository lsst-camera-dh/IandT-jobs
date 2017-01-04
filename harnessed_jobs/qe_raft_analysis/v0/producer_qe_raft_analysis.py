#!/usr/bin/env python
from __future__ import print_function
import lsst.eotest.sensor as sensorTest
import siteUtils
import eotestUtils
import simulation.fake_raft

siteUtils.aggregate_job_ids()

raft_id = siteUtils.getUnitId()
db_name = 'Dev'
raft = simulation.fake_raft.Raft.create_from_etrav(raft_id, db_name=db_name)

for sensor_id in raft.sensor_names:
    sensor_id = str(sensor_id)
    lambda_files = siteUtils.dependency_glob('*_lambda_flat_*.fits',
                                             jobname=siteUtils.getProcessName('qe_acq'),
                                             description='Lambda files:')

    pd_ratio_file = eotestUtils.getPhotodiodeRatioFile()
    if pd_ratio_file is None:
        message = ("The test-stand specific photodiode ratio file is " +
                   "not given in config/%s/eotest_calibrations.cfg."
                   % siteUtils.getSiteName())
        raise RuntimeError(message)

    correction_image = eotestUtils.getIlluminationNonUniformityImage()
    if correction_image is None:
        print()
        print("WARNING: The correction image file is not given in")
        print("config/%s/eotest_calibrations.cfg." % siteUtils.getSiteName())
        print("No correction for non-uniform illumination will be applied.")
        print()
        sys.stdout.flush()

    mask_files = \
        eotestUtils.glob_mask_files(pattern='%s_*mask.fits' % sensor_id)
    gains = eotestUtils.getSensorGains(jobname='fe55_raft_analysis',
                                       sensor_id=sensor_id)

task = sensorTest.QeTask()
task.run(sensor_id, lambda_files, pd_ratio_file, mask_files, gains,
         correction_image=correction_image)

