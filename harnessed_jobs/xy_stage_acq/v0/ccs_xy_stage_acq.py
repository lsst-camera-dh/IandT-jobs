"""
Jython script for XY staged acquisitions at TS8.
"""
import time
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class XYStageAcquisition(EOAcquisition):
    """
    EOAcquisition subclass for "preflight" data.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(XYStageAcquisition, self).__init__(seqfile, acq_config_file,
                                                 "xy_stage", metadata,
                                                 subsystems, ccd_names,
                                                 logger=logger)

    def run(self):
        """
        Take images.
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
            self.image_clears(nclears=2, exptime=5)
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%4.4d_${RunNumber}_${timestamp}.fits' % int(wl)
            pd_readout.start_accumulation()
            fits_files = self.take_image(seqno, exptime, openShutter,
                                         actuateXed, image_type,
                                         file_template=file_template)
            pd_readout.get_readings(fits_files, seqno, 1)

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = XYStageAcquisition(sequence_file, rtmacqcfgfile, metadata,
                             subsystems, ccd_names)
    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
