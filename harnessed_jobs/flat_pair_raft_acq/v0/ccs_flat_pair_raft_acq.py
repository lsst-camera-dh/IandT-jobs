"""
Jython script to run flat pair acquisitions at TS8.
"""
from eo_acquisition import EOAcquisition, PhotoDiodeReadout, logger

class FlatAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take the flat pair dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, logger=logger):
        super(FlatAcquisition, self).__init__(seqfile, acq_config_file, "FLAT",
                                              metadata, logger=logger)
        self.imcount = 2

    def run(self):
        """
        Take the flat pair sequence, reading the target signal levels
        from the configuration file.
        """
        openShutter = True
        actuateXed = False

        # Get measured flux at current wavelength for exposure time
        # calculation.
        meas_flux = self.measured_flux()  # e-/pixel/second

        # Loop over exposure pairs.
        for seqno, tokens in enumerate(self.instructions):
            self.image_clears()
            self.bias_image(seqno)

            # Compute exposure time to obtain the desired signal level.
            target_counts = float(tokens[1])  # e-/pixel
            exptime = target_counts/meas_flux
            # Impose exposure time limits.
            exptime = min(max(exptime, self.exptime_min), self.exptime_max)

            # Create photodiode readout handler.
            pd_readout = PhotoDiodeReadout(exptime, self)

            # Take a pair of exposures (self.imcount = 2).
            for icount in range(self.imcount):
                self.image_clears()
                file_template = '${CCDSerialLSST}_${testType}_%07.2fs_${imageType}%d_${RunNumber}_${timestamp}.fits' % (exptime, icount+1)
                pd_readout.start_accumulation()
                fits_files = self.take_image(seqno, exptime, openShutter,
                                             actuateXed, "FLAT",
                                             file_template=file_template)
                pd_readout.get_readings(fits_files, seqno, icount)

if __name__ == '__main__':
    metadata = dict(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = FlatAcquisition(sequence_file, rtmacqcfgfile, metadata)
    acq.run()
