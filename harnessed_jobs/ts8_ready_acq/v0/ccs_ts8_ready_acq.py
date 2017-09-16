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

        if not self.instructions:
            # Use the default image sequence.
            self.instructions = ["ready FE55 10".split(),
                                 "ready FLAT 1".split(),
                                 "ready FLAT 4".split()]

    def run(self):
        """
        Take the readiness acquisition images.
        """
        openShutter = {'FE55': False, 'FLAT': True}
        actuateXed = {'FE55': True, 'FLAT': False}

        for seqno, tokens in enumerate(self.instructions):
            image_type = tokens[1]
            exptime = float(tokens[2])
            self.image_clears()
            self.take_image(seqno, exptime, openShutter[image_type],
                            actuateXed[image_type], image_type)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = ReadyAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                           ccd_names)

    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
