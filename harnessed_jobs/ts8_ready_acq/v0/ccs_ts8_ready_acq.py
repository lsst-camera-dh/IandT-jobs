"""
Jython script for readiness acquisitions at TS8.

This is based on harnessed-jobs/T08/read_acq/ccseorebalive_exposure.py
"""
import time
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class ReadyAcquisition(EOAcquisition):
    """
    EOAcquisition subclass for "readiness" data.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(ReadyAcquisition, self).__init__(seqfile, acq_config_file,
                                               "READY", metadata,
                                               subsystems, ccd_names,
                                               logger=logger)
        self.sub.pd.synchCommand(10, "setCurrentRange", 0.00002)

    def run(self):
        """
        Take 3 images: 10s Fe55, 1s flat, 4s flat.
        """
        # Fe55
        seqno = 0
        exptime = 10
        openShutter = False
        actuateXed = True
        image_type = "FE55"
        self.image_clears()
        self.take_image(seqno, exptime, openShutter, actuateXed, image_type)

        # Flats
        openShutter = True
        actuateXed = False
        image_type = "FLAT"
        for seqno, exptime in zip((1, 2), (1., 4.)):
            self.image_clears()
            self.take_image(seqno, exptime, openShutter, actuateXed, image_type)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = ReadyAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                           ccd_names)

    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
