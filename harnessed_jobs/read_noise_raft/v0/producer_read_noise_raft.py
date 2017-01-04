#!/usr/bin/env python
from __future__ import print_function
import sys
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
    #
    # Use Fe55 exposures and the overscan region instead of the bias
    # frames as per 2015-09-10 TS1-TS3 sprint decision:
    # https://confluence.slac.stanford.edu/display/LSSTCAM/Science+Raft+Teststands
    #
    bias_files = siteUtils.dependency_glob('S*/%s_fe55_fe55_*.fits' % sensor_id,
                                           jobname='fe55_raft_acq_sim',
                                           description='Fe55 files for read noise:')
    bias_files = [str(x) for x in bias_files]
    gains = eotestUtils.getSensorGains(jobname='fe55_raft_analysis',
                                       sensor_id=sensor_id)
    system_noise = eotestUtils.getSystemNoise(gains)
    if system_noise is None:
        print()
        print("WARNING: The system noise file is not given in")
        print("config/%s/eotest_calibrations.cfg." % siteUtils.getSiteName())
        print("The system noise will be set to zero for all amplifiers.")
        print()
        sys.stdout.flush()

    mask_files = \
        eotestUtils.glob_mask_files(pattern='%s_*mask.fits' % sensor_id)

    task = sensorTest.ReadNoiseTask()
    task.run(sensor_id, bias_files, gains, system_noise=system_noise,
             mask_files=mask_files, use_overscan=True)
