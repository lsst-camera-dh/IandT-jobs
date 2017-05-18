"""
Jython script to run Fe55 acquisitions at TS8.
"""
from eo_acquisition import EOAcquisition, AcqMetadata, logger

class Fe55Acquisition(EOAcquisition):
    """
    EOAcquisition subclass to take the Fe55 dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 logger=logger):
        super(Fe55Acquisition, self).__init__(seqfile, acq_config_file, "FE55",
                                              metadata, subsystems,
                                              logger=logger)

    def run(self):
        """
        Take the Fe55 data.
        """
        openShutter = False
        actuateXed = True
        image_type = "FE55"

        seqno = 0
        for tokens in self.instructions:
            exptime = float(tokens[1])
            nframes = int(tokens[2])
            for iframe in range(nframes):
                self.image_clears()
                self.bias_image(seqno)
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type)
                seqno += 1

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = Fe55Acquisition(sequence_file, rtmacqcfgfile, metadata, subsystems)
    acq.run()
