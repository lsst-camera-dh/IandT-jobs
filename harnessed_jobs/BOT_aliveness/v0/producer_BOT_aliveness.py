#!/usr/bin/env python
"""
Producer script for BOT aliveness test acquisitions.
"""
import os
import subprocess
import matplotlib.pyplot as plt
import lsst.afw.math as afw_math
import siteUtils
import lsst.eotest.sensor as sensorTest
import lsst.eotest.raft as raftTest
from correlated_noise import correlated_noise, raft_leve_oscan_correlations
from camera_components import camera_info
from multiprocessor_execution import run_device_analysis_pool


# Find BOT aliveness acquisition config file from the top-level
# acquisition configuration file.
with open(os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg'), 'r') as fd:
    for line in fd:
        if line.startswith('bot_aliveness_acq_cfg'):
            cfg_file = line.strip().split('=')[1].strip()
            break

run_number = siteUtils.getRunNumber()

command = '/home/ccs/bot-data.py --symlink . --run {} {}'.format(run_number,
                                                                 cfg_file)
subprocess.check_call(command)

def read_noise_stats(raft_name, run_number=run_number):
    file_prefix = '{}_{}'.format(run_number, raft_name)
    title = '{}, {}'.format(run_number, raft_name)

    bias_files = dict()
    results_files = dict()
    slot_names = camera_info.get_slot_names()
    for slot_name in slot_names:
        det_name = '{}_{}'.format(raft_name, slot_name)
        pattern = 'dark_bias_*/*_{}.fits'.format(det_name)
        bias_files[slot_name] = sorted(glob.glob(pattern))
        if not bias_files[slot_name]:
            print("read_noise_stats: Needed bias files missing for raft",
                  raft_name)
            return

        ccd = sensortest.MaskedCCD(bias_files[slot_name][-1])
        bbox = ccd.amp_geom.serial_overscan
        bbox.grow(-10)
        outfile = '%s_eotest_results.fits' % det_name
        results = sensorTest.EOTestResults(outfile)
        for amp in ccd:
            image = ccd[amp].getImage()
            oscan = image.Factory(image, bbox)
            read_noise \
                = afw_math.makeStatistics(oscan, afw_math.STDEVCLIP).getValue()
            results.add_seg_result(amp, 'READ_NOISE', read_noise)
        results.write()
        results_files[slot_name] = outfile

    spec_plots = raftTest.RaftSpecPlots(results_files)
    spec_plots.make_plot('READ_NOISE', 'noise per pixel (ADU rms)',
                         title=title)
    plt.savefig('{}_read_noise.png'.format(file_prefix))

    for slot_name in slot_names:
        corr_fig_prefix = '{}_{}'.format(title, slot_name)
        corr_fig_title = '{}, {}'.format(title, slot_name)
        _, corr_fig, _ = correlated_noise(bias_files[slot_name], target=0,
                                          make_plots=True, title=corr_fig_title)
        plt.figure(corr_fig.number)
        plt.savefig('{}_correlated_noise.png'.format(corr_fig_prefix))

    oscan_title = 'Overscan correlations, {}'.format(title)
    bias_files = {slot_name: x[0] for slot_name, x in bias_files.items()}
    raft_level_oscan_correlations(bias_files, title=oscan_title)
    plt.savefig('{}_overscan_correlations.png'.format(file_prefix))

raft_names = camera_info.get_raft_names()
processes = None
run_device_analysis_pool(read_noise_stats, raft_names, processes=processes)
