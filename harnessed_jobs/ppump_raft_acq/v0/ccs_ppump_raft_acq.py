"""
Jython script to run the pocket-pumping acquisition at TS8.
"""
from eo_acquisition import EOAcquisition, AcqMetadata, logger

class PPumpAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take the pocket-pumping dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(PPumpAcquisition, self).__init__(seqfile, acq_config_file,
                                               "TRAP", metadata, subsystems,
                                               ccd_names, logger=logger)

    def run(self):
        """
        Take the pocket-pumping data.
        """
        openShutter = True
        actuateXed = False
        image_type = "PPUMP"

        wl = float(self.eo_config.get("PPUMP_WL", 550))
        meas_flux = self.measured_flux(wl)
        seqno = 0
        for tokens in self.instructions:
            exptime = float(tokens[1])
            nframes = int(tokens[2])
            shifts = int(tokens[3])
            for iframe in range(nframes):
                self.image_clears()
                self.bias_image(seqno)
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type)
                seqno += 1

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = PPumpAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                           ccd_names)
    acq.run()
