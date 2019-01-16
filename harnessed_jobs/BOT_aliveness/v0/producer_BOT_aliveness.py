#!/usr/bin/env python
"""
Producer script for BOT aliveness test acquisitions.
"""
import os
import glob
import shutil
import subprocess
import matplotlib.pyplot as plt
import lsst.afw.math as afw_math
import siteUtils
import lsst.eotest.sensor as sensorTest
import lsst.eotest.raft as raftTest
from correlated_noise import correlated_noise, raft_level_oscan_correlations
from camera_components import camera_info
from multiprocessor_execution import run_device_analysis_pool

run_number = siteUtils.getRunNumber()

def take_bot_data():
    """
    Take the BOT data for the aliveness test.
    """
    acq_config = siteUtils.get_job_acq_configs()
    command = '/home/ccs/bot-data.py --symlink . --run {} {}'\
        .format(run_number, acq_config['bot_aliveness_cfg'])
    subprocess.check_call(command, shell=True)


def symlink_r_and_d_data(r_and_d_path=None):
    """
    Symlink copies of R_and_D frames for testing.
    """
    print("symlinking R and D data")
    if r_and_d_path is None:
        r_and_d_path \
            = '/gpfs/slac/lsst/fs2/u1/devel/jchiang/BOT_aliveness/R_and_D_data'
    r_and_d_dirs = [x for x in sorted(glob.glob(os.path.join(r_and_d_path, '*'))) if os.path.isdir(x)]
    for i in range(0, 2):
        outdir = 'dark_bias_{:03d}'.format(i)
        os.makedirs(outdir, exist_ok=True)
        #os.symlink(r_and_d_dirs[i], outdir)
        command = 'cp {}/* {}/'.format(r_and_d_dirs[i], outdir)
        print(command)
        subprocess.check_call(command, shell=True)
    for i in range(2, 5):
        outdir = 'dark_dark_{:03d}'.format(i)
        os.makedirs(outdir, exist_ok=True)
        #os.symlink(r_and_d_dirs[i], outdir)
        command = 'cp {}/* {}/'.format(r_and_d_dirs[i], outdir)
        print(command)
        subprocess.check_call(command, shell=True)


def get_bias_files(raft_name):
    """
    Get the bias files for the aliveness test.
    """
    slot_names = camera_info.get_slot_names()
    bias_files = dict()
    for slot_name in slot_names:
        det_name = '{}_{}'.format(raft_name, slot_name)
        pattern = 'dark_bias_*/*_{}.fits'.format(det_name)
        bias_files[slot_name] = sorted(glob.glob(pattern))
        if not bias_files[slot_name]:
            raise FileNotFoundError("needed bias files not found for %s"
                                    % det_name)
    return bias_files


def read_noise_stats(raft_name, run_number=run_number):
    """
    Compute the read noise stats and make plots.
    """
    file_prefix = '{}_{}'.format(run_number, raft_name)
    title = '{}, {}'.format(run_number, raft_name)

    results_files = dict()
    try:
        bias_files = get_bias_files(raft_name)
    except FileNotFoundError:
        print("read_noise_stats: Needed bias files missing for raft",
              raft_name)
        return

    for slot_name in bias_files:
        det_name = '{}_{}'.format(raft_name, slot_name)
        ccd = sensorTest.MaskedCCD(bias_files[slot_name][-1])
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

def correlated_noise_figures(det_name, run_number=run_number):
    """
    Compute intra-CCD read noise correlations.
    """
    file_prefix = '{}_{}'.format(run_number, det_name)
    title = '{}, {}'.format(run_number, det_name)
    pattern = 'dark_bias_*/*_{}.fits'.format(det_name)
    bias_files = sorted(glob.glob(pattern))
    if not bias_files:
        print("correlated_noise_figures: Needed bias files not found for",
              det_name)
        return
    _, corr_fig, _ = correlated_noise(bias_files, target=0, make_plots=True,
                                      title=title)
    plt.figure(corr_fig.number)
    plt.savefig('{}_correlated_noise.png'.format(file_prefix))

def raft_overscan_correlations(raft_name, run_number=run_number):
    """
    Compute raft-level inter-CCD read noise correlations.
    """
    file_prefix = '{}_{}'.format(run_number, raft_name)
    title = '{}, {}'.format(run_number, raft_name)

    try:
        bias_files = get_bias_files(raft_name)
    except FileNotFoundError:
        print("raft_overscan_correlations: Needed bias files missing for raft",
              raft_name)
        return

    bias_files = {slot_name: x[0] for slot_name, x in bias_files.items()}
    oscan_title = 'Overscan correlations, {}'.format(title)
    raft_level_oscan_correlations(bias_files, title=oscan_title)
    plt.savefig('{}_overscan_correlations.png'.format(file_prefix))

if __name__ == '__main__':
    if 'LCATR_RUN_SIM' in os.environ:
        symlink_r_and_d_data()
    else:
        take_bot_data()

    det_names = camera_info.get_det_names()
    raft_names = camera_info.get_raft_names()
    processes = None
    run_device_analysis_pool(read_noise_stats, raft_names, processes=processes)
    run_device_analysis_pool(correlated_noise_figures, det_names,
                             processes=processes)
    run_device_analysis_pool(raft_overscan_correlations, raft_names,
                             processes=processes)
