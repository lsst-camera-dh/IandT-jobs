#!/usr/bin/env python
import glob
from collections import defaultdict
import numpy as np
import lcatr.schema
import siteUtils
import lsst.eotest.image_utils as imutils
import lsst.eotest.sensor as sensorTest

def get_median_signal_levels(ccd, segment_region, boxsize=10, nsamp=50):
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

results = []

job_schema = lcatr.schema.get('rtm_aliveness_exposure')

image_types = 'bias flat fe55'.split()

for image_type in image_types:
    fits_files = sorted(glob.glob('*_%s_*.fits' % image_type))
    exptime = int(imutils.Metadata(fits_files[0], 1).get('EXPTIME'))
    segment_signals = defaultdict(dict)
    signal_values = []
    for fits_file in fits_files:
        slot = fits_file.split('_')[0]
        ccd = sensorTest.MaskedCCD(fits_file)
        imaging = get_median_signal_levels(ccd, ccd.amp_geom.imaging)
        oscan = get_median_signal_levels(ccd, ccd.amp_geom.serial_overscan)
        for amp in ccd:
            signal_values.append(imaging[amp] - oscan[amp])
            segment_signals[slot][amp] = signal_values[-1]

    # Check for bad channels using an empirical threshold of
    # median(segment_signals)/10.
    threshold = np.median(signal_values)/10.
    for slot in segment_signals:
        for amp, signal in segment_signals[slot].items():
            if signal < threshold:
                status = 'bad'
            else:
                status = 'good'
            results.append(lcatr.schema.valid(job_schema,
                                              image_type=image_type,
                                              exptime=exptime,
                                              slot=slot,
                                              segment=imutils.channelIds[amp],
                                              status=status))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
