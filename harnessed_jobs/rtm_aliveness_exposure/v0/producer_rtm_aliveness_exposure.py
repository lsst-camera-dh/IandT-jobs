#!/usr/bin/env python
import glob
from collections import defaultdict
import multiprocessing
import numpy as np
import matplotlib.pyplot as plt
from ccsTools import ccsProducer, CcsRaftSetup
import lsst.eotest.sensor as sensorTest
import lsst.eotest.raft as raftTest
import siteUtils
from correlated_noise import correlated_noise, plot_correlated_noise, \
    raft_level_oscan_correlations
import camera_components
import aliveness_utils

ccsProducer('rtm_aliveness_exposure', 'ccs_rtm_aliveness_exposure.py',
            ccs_setup_class=CcsRaftSetup)

# Infer the sequence numbers from the files for the sensor in slot S00.
seqnos = sorted([x.split('_')[-3] for x in
                 sorted(glob.glob('S00/*flat*.fits'))])

# Perform noise analysis of last bias frame taken.
raft_id = siteUtils.getUnitId()
run_number = siteUtils.getRunNumber()

raft = camera_components.Raft.create_from_etrav(raft_id)
results_files = dict()
bias_files = dict()
bbox = None
for slot, sensor_id in raft.items():
    # glob the bias files for each sensor.  The correlated noise plots need
    # at least 2 bias files per ccd.
    bias_files[slot] = sorted(glob.glob('%s/%s_conn_bias_*.fits'
                                        % (slot, sensor_id)))[-2:]

    # For the read noise estimates from the overscan region, we
    # just need one file.
    ccd = sensorTest.MaskedCCD(bias_files[slot][-1])

    # The aliveness_utils.get_read_noise function uses the subregion
    # sampler to estimate the read noise from the overscane regoins.
    sampled_rn = aliveness_utils.get_read_noise(ccd)

    results_files[slot] = '%s_eotest_results.fits' % sensor_id
    results = sensorTest.EOTestResults(results_files[slot])
    for amp in sampled_rn:
        results.add_seg_result(amp, 'READ_NOISE', sampled_rn[amp])
    results.write()

    frames = dict()
    for seqno in seqnos:
        frames[seqno] = sorted(glob.glob('%s/%s_conn_flat_%s_*.fits'
                                         % (slot, sensor_id, seqno)))[0]

    columns = aliveness_utils.compute_response_diffs(frames,
                                                     results_files[slot])

file_prefix = '{}_{}'.format(raft_id, run_number)
title = '{}, Run {}'.format(raft_id, run_number)
spec_plots = raftTest.RaftSpecPlots(results_files)

spec_plots.make_plot('READ_NOISE', 'noise per pixel (ADU rms)', title=title)
plt.savefig('{}_read_noise.png'.format(file_prefix))
plt.close('all')

spec_plots.make_multi_column_plot(columns, 'mean signal (ADU)', title=title)
plt.savefig('{}_diff_mean_signal.png'.format(file_prefix))
plt.close('all')

spec_plots.make_plot('SLOPE', 'slope of mean signal vs exptime (adu/s)',
                     title=title)
plt.savefig('{}_mean_signal_vs_exptime_slope.png'.format(file_prefix))
plt.close('all')

def compute_correlated_noise(bias_files, slot, sensor_id):
    (corr_data, bias_stats), _, _ = correlated_noise(bias_files)
    f1, f2 = plot_correlated_noise(corr_data, bias_stats)
    return f1, slot, sensor_id

with multiprocessing.Pool(processes=len(list(raft.items()))) as pool:
    workers = []
    for slot, sensor_id in raft.items():
        workers.append(pool.apply_async(compute_correlated_noise,
                                        (bias_files[slot], slot, sensor_id)))
    pool.close()
    pool.join()
    results = [_.get() for _ in workers]

for items in results:
    fig1, slot, sensor_id = items
    plt.figure(fig1.number)
    fig1.suptitle('{}, {}, Run {}'.format(slot, sensor_id, run_number))
    plt.savefig('{}_{}_correlated_noise.png'.format(sensor_id, run_number))

plt.close('all')

title = 'Overscan correlations, {}, Run {}'.format(raft_id, run_number)
bias_files = {slot: x[0] for slot, x in bias_files.items()}
raft_level_oscan_correlations(bias_files, title=title)
plt.savefig('{}_{}_overscan_correlations.png'.format(raft_id, run_number))
