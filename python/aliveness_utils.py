"""
Utility functions for RTM aliveness testing.
"""
import os
from collections import defaultdict
import numpy as np
import lsst.eotest.image_utils as imutils
import lsst.eotest.sensor as sensorTest

__all__ = ['compute_response_diffs', 'get_read_noise', 'get_mean_image_adu',
           'get_median_signal_levels', 'raft_channel_statuses']


def compute_response_diffs(frames, results_file):
    """
    For each amp, compute the difference in response of sequential frames
    sorted by exposure time.

    Parameters
    ----------
    frames: dict
        Filenames for single CCD frames, keyed by sequence number.
    results_file: str
        Filename of eotest results file to which the response differences
        are written.

    Returns
    -------
    list of column names
    """
    seqnos = sorted(frames.keys())
    results = sensorTest.EOTestResults(results_file)
    mean_signals = defaultdict(list)
    columns = set()
    exptimes = []
    for i, seqno in enumerate(seqnos):
        ccd = sensorTest.MaskedCCD(frames[seqno])
        exptimes.append(ccd.md.get('EXPTIME'))
        means = get_mean_image_adu(ccd)
        for amp, value in means.items():
            mean_signals[amp].append(value)
            if i > 0:
                column = 'MEAN_SIGNAL_{}_minus_{}'.format(seqnos[i],
                                                          seqnos[i-1])
                columns.add(column)
                delta_signal = float(value - mean_signals[amp][i-1])
                results.add_seg_result(amp, column, delta_signal)

    for amp, signal in mean_signals.items():
        pars = np.polyfit(exptimes, signal, 1)
        results.add_seg_result(amp, 'SLOPE', float(pars[0]))
        results.add_seg_result(amp, 'INTERCEPT', float(pars[1]))

    results.write()
    return columns


def get_read_noise(ccd, boxsize=10, nsamp=50):
    """
    Compute the read noise per amp derived by randomly subsampling
    the overscan region and taking the median of the stdev values
    from the sample of subregions.

    Parameters
    ----------
    ccd: lsst.eotest.sensor.MaskedCCD
        The pixel data for a CCD frame.
    boxsize: int [10]
        The linear size in pixels of the square regions for subsampling.
    nsamp: int [50]
        The number of subregions to generate.

    Returns
    -------
    dict: a dictionary of the stdev values in ADU keyed by amp number.
    """
    read_noise = {}
    for amp in ccd:
        sampler = imutils.SubRegionSampler(boxsize, boxsize, nsamp,
                                           imaging=ccd.amp_geom.serial_overscan)
        image = ccd[amp].Factory(ccd[amp], ccd.amp_geom.serial_overscan)
        bbox = image.getBBox()
        stdevs = []
        for x, y in zip(sampler.xarr, sampler.yarr):
            subim = sampler.subim(image, x + bbox.getMinX(), y + bbox.getMinY())
            stdevs.append(np.std(subim.getImage().getArray().ravel()))
        read_noise[amp] = np.median(stdevs)
    return read_noise


def get_mean_image_adu(ccd, boxsize=50, nsamp=50):
    """
    Compute the mean signal in the imaging region by randomly
    subsampling the overscan subtracted imaging section and taking the
    median of the mean signal in each subregion.

    Parameters
    ----------
    ccd: lsst.eotest.sensor.MaskedCCD
        The pixel data for a CCD frame.
    boxsize: int [50]
        The linear size in pixels of the square regions for subsampling.
    nsamp: int [50]
        The number of subregions to generate.

    Returns
    -------
    dict: a dictionary of the mean values in ADU keyed by amp number.
    """
    medians = {}
    for amp in ccd:
        sampler = imutils.SubRegionSampler(boxsize, boxsize, nsamp,
                                           imaging=ccd.amp_geom.imaging)
        image = ccd.unbiased_and_trimmed_image(amp)
        bbox = image.getBBox()
        values = []
        for x, y in zip(sampler.xarr, sampler.yarr):
            subim = sampler.subim(image, x + bbox.getMinX(), y + bbox.getMinY())
            values.append(np.mean(subim.getImage().getArray().ravel()))
        medians[amp] = np.median(values)
    return medians


def get_median_signal_levels(ccd, segment_region, boxsize=10, nsamp=50):
    """
    Compute the median signal of a segment region by sub-region
    sampling in order to avoid affects of cosmic rays or other
    bright/dark defects.   The mean pixel values of the subregions
    is medianed for each channel

    Parameters
    ----------
    ccd: lsst.eotest.sensor.MaskedCCD
        The pixel data for a CCD frame.
    segment_region: lsst.afw.geom.Box2I
        The bounding box for the segment subregion to sample.
    boxsize: int [10]
        The linear size in pixels of the square regions for subsampling.
    nsamp : int [50]
        The number of subregions to generate.

    Returns
    -------
    dict : a dictionary of the median signal values keyed by amp number.
    """
    medians = {}
    for amp in ccd:
        sampler = imutils.SubRegionSampler(boxsize, boxsize, nsamp,
                                           imaging=segment_region)
        image = ccd[amp].Factory(ccd[amp], sampler.imaging)
        bbox = image.getBBox()
        means = []
        for x, y in zip(sampler.xarr, sampler.yarr):
            subim = sampler.subim(image, x + bbox.getMinX(),
                                  y + bbox.getMinY())
            means.append(np.mean(subim.getImage().getArray().ravel()))
        medians[amp] = np.median(means)
    return medians


def raft_channel_statuses(fits_files, threshold_factor=0.1):
    """
    Compute the connectivity status of each channel in a raft given a
    collection of FITS images for each of the 9 CCDs.  The FITS
    filenames are assumed to have the format <slot>/*.fits.

    Parameters
    ----------
    fits_files : list
        A list of FITS files with the single sensor images for the 9 CCDs
        in a raft.
    threshold_factor : float, optional
        The factor to mulitply the median of the channel signals to
        provide the threshold between a "bad" and "good" channel.

    Returns
    -------
    (dict, dict, int) : The first dict contains the signal levels for each
        channel keyed by slot and channel number; the second dict contains
        the channel status values of "good" or "bad"; the int is the exposure
        time in seconds.
    """
    exptimes = [int(imutils.Metadata(item).get('EXPTIME'))
                for item in fits_files]

    if min(exptimes) != max(exptimes):
        print(fits_files)
        raise RuntimeError("The exposure times differ among the " +
                           "input FITS files for this raft.")
    channel_signal = defaultdict(dict)
    channel_status = defaultdict(dict)
    signal_values = []
    for fits_file in fits_files:
        slot = fits_file.split(os.path.sep)[0]
        ccd = sensorTest.MaskedCCD(fits_file)
        imaging = get_median_signal_levels(ccd, ccd.amp_geom.imaging)
        oscan = get_median_signal_levels(ccd, ccd.amp_geom.serial_overscan)
        for amp in ccd:
            signal_values.append(imaging[amp] - oscan[amp])
            channel_signal[slot][amp] = signal_values[-1]
    # Check for bad channels using the specified threshold factor times
    # the median channel signal level
    threshold = threshold_factor*np.median(signal_values)
    for slot in channel_signal:
        for amp, signal in channel_signal[slot].items():
            if signal < threshold:
                channel_status[slot][amp] = 'bad'
            else:
                channel_status[slot][amp] = 'good'
    return channel_signal, channel_status, exptimes[0]
