"""
Jython script for generic, R&D-oriented acquisitions at TS8.
"""
import time
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class GenericAcquisition(EOAcquisition):
    """
    EOAcquisition subclass for generic data.  This is operationally
    the same as a single wavelength QE acquisition, but with the
    number of frames in the configuration.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(GenericAcquisition, self).__init__(seqfile, acq_config_file,
                                                 "GENERIC", metadata,
                                                 subsystems, ccd_names,
                                                 logger=logger)

    def run(self):
        """
        Take a sequence of frames at the configured wavelength,
        desired signal level, and requested number of exposures.
        """

        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        # Set wavelength, do the flux calibration, and compute the
        # exposure time to obtain the desired signal per frame.
        meas_flux = self.measured_flux(self.wl)
        target_counts = float(self.eo_config['%s_SIGNAL' % self.acqname])
        exptime = self.compute_exptime(target_counts, meas_flux)

        for icount in range(self.imcount):
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%4.4d_${RunNumber}_${timestamp}.fits' % int(wl)
            self.take_image(seqno, exptime, openShutter,
                            actuateXed, image_type,
                            file_template=file_template)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = GenericAcquisition(sequence_file, rtmacqcfgfile, metadata,
                             subsystems, ccd_names)
    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
