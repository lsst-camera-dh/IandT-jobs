"""
Jython script for acquisition of QE dataset.
"""
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class QEAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take QE dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(QEAcquisition, self).__init__(seqfile, acq_config_file, "LAMBDA",
                                            metadata, subsystems, ccd_names,
                                            logger=logger)

    def run(self):
        """
        Take a sequence of flats as a function of wavelength,
        recomputing the exposure needed to get the desired signal
        level at each wavelength.
        """
        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        for seqno, tokens in enumerate(self.instructions):
            self.image_clears()
            self.bias_image(seqno)

            wl = float(tokens[1])
            target_counts = float(tokens[2])
            meas_flux = self.measured_flux(wl)
            exptime = self.compute_exptime(target_counts, meas_flux)

            pd_readout = PhotodiodeReadout(exptime, self)
            self.image_clears()
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%4.4d_${RunNumber}_${timestamp}.fits' % int(wl)
            pd_readout.start_accumulation()
            fits_files = self.take_image(seqno, exptime, openShutter, actuateXed,
                                         image_type, file_template=file_template)
            pd_readout.get_readings(fits_files, seqno, 1)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = QEAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                        ccd_names)
    acq.run()
