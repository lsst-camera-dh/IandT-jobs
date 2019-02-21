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
from correlated_noise import correlated_noise, raft_level_oscan_correlations
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

    outfile = '%s_eotest_results.fits' % sensor_id
    results = sensorTest.EOTestResults(outfile)
    for amp in sampled_rn:
        results.add_seg_result(amp, 'READ_NOISE', sampled_rn[amp])

    # Mean image adu levels for each sequence number (exposure time).
    exptimes = np.zeros(len(seqnos), dtype=float)
    mean_signals = defaultdict(lambda: np.zeros(len(seqnos), dtype=float))
    for i, seqno in enumerate(seqnos):
        flat = sorted(glob.glob('%s/%s_conn_flat_%s_*.fits'
                                % (slot, sensor_id, seqno)))[0]
        ccd = sensorTest.MaskedCCD(flat)
        exptimes[i] = ccd.md.get('EXPTIME')
        means = aliveness_utils.get_mean_image_adu(ccd)
        if i > 0:
            for amp, value in means.items():
                colname = 'MEAN_SIGNAL_%s_minus_%s' % (seqno, seqnos[0])
                delta_signal = float(value - mean_signals[amp][0])
                results.add_seg_result(amp, colname, delta_signal)
                mean_signals[amp][i] = value

    # Linearity fits to mean signal vs exptime.
    for amp, signal in mean_signals.items():
        pars = np.polyfit(exptimes, signal, 1)
        results.add_seg_result(amp, 'SLOPE', float(pars[0]))
        results.add_seg_result(amp, 'INTERCEPT', float(pars[1]))

    results.write()
    results_files[slot] = outfile

spec_plots = raftTest.RaftSpecPlots(results_files)
spec_plots.make_plot('READ_NOISE', 'noise per pixel (ADU rms)',
                     title='{}, Run {}'.format(raft_id, run_number))
plt.savefig('{}_{}_read_noise.png'.format(raft_id, run_number))

columns = ['MEAN_SIGNAL_%s_minus_%s' % (seqno, seqnos[0])
           for seqno in seqnos[1:]]
spec_plots.make_multi_column_plot(columns, 'mean signal (ADU)',
                                  title='{}, Run {}'.format(raft_id, run_number))
plt.savefig('{}_{}_diff_mean_signal.png'.format(raft_id, run_number))

spec_plots.make_plot('SLOPE', 'slope of mean signal vs exptime (adu/s)',
                     title='{}, Run {}'.format(raft_id, run_number))
plt.savefig('{}_{}_mean_signal_vs_exptime_slope.png'.format(raft_id, run_number))

def plot_correlated_noise(bias_files, slot, sensor_id, run_number):
    _, corr_fig, _ = correlated_noise(bias_files, target=0, make_plots=True,
                                      title='{}, {}, Run {}'.format(slot,
                                                                    sensor_id,
                                                                    run_number))
    plt.figure(corr_fig.number)
    plt.savefig('{}_{}_correlated_noise.png'.format(sensor_id, run_number))

with multiprocessing.Pool(processes=len(list(raft.items()))) as pool:
    results = []
    for slot, sensor_id in raft.items():
        results.append(pool.apply_async(plot_correlated_noise,
                                        (bias_files[slot], slot, sensor_id,
                                         run_number)))
    pool.close()
    pool.join()
    [_.get() for _ in results]

title = 'Overscan correlations, {}, Run {}'.format(raft_id, run_number)
bias_files = {slot: x[0] for slot, x in bias_files.items()}
raft_level_oscan_correlations(bias_files, title=title)
plt.savefig('{}_{}_overscan_correlations.png'.format(raft_id, run_number))
