"""
Jython script for preflight acquisitions at TS8.

This is based on harnessed-jobs/T08/preflight_acq.
"""
import time
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class PreflightAcquisition(EOAcquisition):
    """
    EOAcquisition subclass for "preflight" data.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(PreflightAcquisition, self).__init__(seqfile, acq_config_file,
                                                   "PREFLIGHT", metadata,
                                                   subsystems, ccd_names,
                                                   logger=logger)
        self.sub.pd.synchCommand(10, "setCurrentRange", 0.00002)
        self.imcount = 1
        # There are no preflight instructions in the acq_config_file,
        # so enter the desired ones here.
        self.instructions = ["lambda 0450 3".split(),
                             "lambda 0450 3".split(),
                             "lambda 0450 3".split(),
                             "lambda 0823 3".split()]

    def run(self):
        """
        Take images at 450, 823 nm.
        """
        openShutter = True
        actuateXed = True
        image_type = "FLAT"

        self.sub.mono.synchCommand(36, "setFilter", 1)
        exptime = 3.0
        for seqno, tokens in enumerate(self.instructions):
            wl = float(tokens[1])
            exptime = float(tokens[2])
            rwl = self.set_wavelength(wl)
            filt = self.sub.mono.synchCommand(60, "getFilter").getResult()
            logger.info("Wavelength: %f; Filter: %f" % (rwl, filt))
            time.sleep(4.)

            pd_readout = PhotodiodeReadout(exptime, self)
            self.image_clears()
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%4.4d_${RunNumber}_${timestamp}.fits' % int(wl)
            pd_readout.start_accumulation()
            fits_files = self.take_image(seqno, exptime, openShutter,
                                         actuateXed, image_type,
                                         file_template=file_template)
            pd_readout.get_readings(fits_files, seqno, 1)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = PreflightAcquisition(sequence_file, rtmacqcfgfile, metadata,
                               subsystems, ccd_names)
    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
