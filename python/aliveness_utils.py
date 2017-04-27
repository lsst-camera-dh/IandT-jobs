"""
Utility functions for RTM aliveness testing.
"""
import os
from collections import defaultdict
import numpy as np
import lsst.eotest.image_utils as imutils
import lsst.eotest.sensor as sensorTest

__all__ = ['get_median_signal_levels', 'raft_channel_statuses']

def get_median_signal_levels(ccd, segment_region, boxsize=10, nsamp=50):
    """
    Compute the median signal of a segment region by sub-region
    sampling in order to avoid affects of cosmic rays or other
    bright/dark defects.   The mean pixel values of the subregions
    is medianed for each channel

    Parameters
    ----------
    ccd : lsst.eotest.sensor.MaskedCCD
        The pixel data for a CCD frame.
    segment_region : lsst.afw.geom.Box2I
        The bounding box for the segment subregion to sample.
    boxsize : int, optional
        The linear size in pixels of the square regions for subsampling.
        Default: 10
    nsamp : int, optional
        The number of subregions to generate. Default: 50

    Returns
    -------
    dict : a dictionary of the median signal values keyed by channel/amp
        number.
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
    exptimes = [int(imutils.Metadata(item, 1).get('EXPTIME'))
                for item in fits_files]
    if min(exptimes) != max(exptimes):
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
