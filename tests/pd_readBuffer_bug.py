import os
import sys
import time
sys.path.insert(0, '/lnfs/lsst/devel/jchiang/jh_install/IandT-jobs/python')
sys.path.insert(0, '/lnfs/lsst/devel/jchiang/jh_install/jh-ccs-utils/python')
from ccs_scripting_tools import CcsSubsystems
from eo_acquisition import PhotodiodeReadout, logger

class Metadata(object):
    def __init__(self, md_dict):
        self.__dict__.update(md_dict)

class EoAcqProxy(object):
    def __init__(self, logger=logger):
        self.sub = CcsSubsystems(dict(pd='ts8-bench/Monitor'), logger=logger)
        self.md = Metadata(dict(cwd=os.path.abspath('.')))
        self.logger = logger

acq = EoAcqProxy(logger=logger)

for seqno, exptime in enumerate((0.1, 1., 3., 10., 30.)):
#for seqno, exptime in enumerate((0.1,)):
    logger.info("seqno=%i, exptime=%f", seqno, exptime)

    pd_readout = PhotodiodeReadout(exptime, acq)

    # simulate delay for image_clears in preflight script
    time.sleep(2*5)

    pd_readout.start_accumulation()

    # simulate exposure in take_image(...)
    logger.info("simulating exposure time of %f seconds.", exptime)
    time.sleep(exptime)

    logger.info("about to write pd readings.")
    pd_readout.write_readings(seqno)
