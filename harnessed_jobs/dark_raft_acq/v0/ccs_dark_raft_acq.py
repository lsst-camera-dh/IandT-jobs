"""
Jython script to acquire dark exposure dataset (used to find bright defects and
to estimate dark current).
"""
from eo_acquisition import EOAcquisition, AcqMetadata, logger

class DarkAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to acquire dark exposure dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 logger=logger):
        super(DarkAcquisition, self).__init__(seqfile, acq_config_file, "DARK",
                                              metadata, subsystems,
                                              logger=logger)

    def run(self):
        """
        Take the dark exposures.
        """
        openShutter = False
        actuateXed = False
        image_type = "DARK"

        for tokens in self.instructions:
            exptime = float(tokens[1])
            frame_count = int(tokens[2])
            for seqno in range(frame_count):
                self.image_clears()
                self.bias_image(seqno)
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = DarkAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems)
    acq.run()
