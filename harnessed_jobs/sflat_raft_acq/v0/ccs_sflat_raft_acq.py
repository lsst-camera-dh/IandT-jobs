"""
Jython script to run superflat acquisitions at TS8.
"""
from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger

class SuperFlatAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take the flat pair dataset.
    """
    def __init__(self, seqfile, acq_config_file, metadata, logger=logger):
        super(SuperFlatAcquisition, self).__init__(seqfile, acq_config_file,
                                                   "SFLAT", metadata,
                                                   logger=logger)

    def run(self):
        """
        Take superflat datasets at the wavelength and signal values
        specified in the configuration file.
        """
        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        seqno = 0
        for tokens in enumerate(self.instructions):
            wl = float(tokens[1])
            target_flux = float(tokens[2])
            nframes = int(tokens[3])
            test_type = "SFLAT_%3.3d" % wl
            if target_flux < 1e4:
                flux_level = 'L'
            else:
                flux_level = 'H'
            meas_flux = self.measured_flux(wl)
            exptime = self.compute_exptime(target_flux, meas_flux)
            pd_readout = PhotodiodeReadout(exptime, self)
            for iframe in range(nframes):
                self.image_clears()
                self.bias_image(seqno)
                file_template = '${CCDSerialLSST}_${testType}_${imageType}_%s%3.3d_${timestamp}.fits' % (flux_level, seqno+1)
                pd_readout.start_accumulation()
                fits_files = self.take_image(seqno, exptime, openShutter,
                                             actuateXed, image_type,
                                             test_type=test_type,
                                             file_template=file_template)
                pd_readout.get_readings(fits_files, seqno, 1)
                seqno += 1

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = SuperFlatAcquisition(sequence_file, rtmacqcfgfile, metadata)
    acq.run()
