#!/usr/bin/env python
import os
import glob
from ccsTools import ccsProducer, CcsRaftSetup
import siteUtils
import lsst.eotest.sensor as sensorTest
import lsst.eotest.raft as raftTest
from correlated_noise import correlated_noise, raft_level_oscan_correlations
import camera_components

ccsProducer('rtm_aliveness_exposure', 'ccs_rtm_aliveness_exposure.py',
            ccs_setup_class=CcsRaftSetup)

# Perform noise analysis of last bias frame taken.
raft_id = siteUtils.getUnitId()
run_number = siteUtils.getRunNumber()

raft = camera_components.Raft.create_from_etrav(raft_id)
results_files = dict()
bias_files = dict()
bbox = None
for slot, sensor_id in raft.items():
    # glob the bias files for each sensor.  Use the last one in the sequence.
    bias_files[slot] = sorted(glob.glob('%s_conn_bias_*.fits'))[-1]

    ccd = MaskedCCD(bias_files[slot])

    if bbox is None:
        bbox = ccd.amp_geom.serial_overscan
        bbox.grow(-10)

    results = sensorTest.EOTestResults()
    for amp in ccd:
        image = ccd[amp].getImage()
        oscan = image.Factory(image, bbox)
        read_noise \
            = afw_math.makeStatistics(oscan, afw_math.STDEVCLIP).getValue()
        results.add_seg_result(amp, 'READ_NOISE', read_noise)
    outfile = '%s_eotest_results.fits' % sensor_id
    results.write(outfile)
    results_files[slot] = outfile

spec_plots = raftTest.RaftSpecPlots(results_files)
spec_plots.make_plot('READ_NOISE', 'noise per pixel (ADU rms)',
                     title='{}, {}'.format(raft_id, run_number))
plt.savefig('{}_{}_read_noise.png'.format(raft_id, run_number))

for slot, sensor_id in raft.items():
    _, corr_fig, _ = correlated_noise([bias_files[slot]]*2, target=0,
                                      make_plots=True,
                                      title='{} {} {}'.format(slot, sensor_id,
                                                              run_number))
    plt.savefig('{}_{}_correlated_noise.png'.format(sensor_id, run_number))

title = 'Overscan correlations, {}, Run {}'.format(raft_id, run_number)
raft_level_oscan_correlations(bias_files, title=title)
plt.savefig('{}_{}_overscan_correlations.png'.format(raft_id, run_number)
