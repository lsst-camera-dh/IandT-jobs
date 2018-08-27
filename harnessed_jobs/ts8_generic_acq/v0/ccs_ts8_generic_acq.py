"""
Jython script for generic, R&D-oriented acquisitions at TS8.
"""
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
        Take N sets of a sequence of frames at the configured wavelengths,
        desired signal level, and requested number of exposures of dark, flat, fe55,
        and bias.

        Example rtmacqcfgfile content:

GENERIC_NCYCLES         10  # Number of cycles
GENERIC_WLS            500,600,700   # Wavelength in nm
GENERIC_NBIAS           1   # Number of bias among a cycle
GENERIC_NDARK           1   # Number of dark among a cycle
GENERIC_NFLAT           1   # Number of flat among a cycle
GENERIC_NFE55           1   # Number of fe55 among a cycle
GENERIC_SIGNAL      20000   # Target signal in e-
# Exposure time in seconds, if present, it will override the target signal.
#GENERIC_TDARK          10   # exposure tiem of dark image
#GENERIC_TFLAT          100  # exposure time of flat image
#GENERIC_TFE55          100  # exposure time of fe55 image
        """
        ncycles = int(self.eo_config.get('%s_NCYCLES' % self.acqname,
                        default='1'))

        wls     = map(lambda x: float(x),
                        (self.eo_config.get('%s_WLS' % self.acqname,
                        default='550')).split(",") )
        seqno = 0
        for wl in wls:
            for ncylce in range(ncycles):
                self.wl = wl
                self.set_wavelength( wl )
                for params  in [
                       ( "BIAS", False, False, "RaD_BIAS" ),
                       ( "DARK", False, False, "RaD_DARK" ),
                       ( "FLAT", True,  False, "RaD_FLAT" ),
                       ( "FE55", False, True , "RaD_FE55" ),
        
                                ]:
                    key, openShutter, actuateXed, image_type = params
                    print "## %s ###################################" % key
        
                    ntake = int(self.eo_config.get( "%s_N%s" % ( self.acqname, key ) ,default='0'))
        
                    if ntake == 0:
                        continue

                    try:
                        exptime= float(self.eo_config["%s_T%s" % ( self.acqname, key )])
                    except KeyError:
                        # Set wavelength, do the flux calibration, and compute the
                        # exposure time to obtain the desired signal per frame.
                        if key == "BIAS":
                            exptime = 0.0
                        else:
                            meas_flux = self.measured_flux(self.wl)
                            target_counts = float(self.eo_config['%s_SIGNAL' % self.acqname])
                            exptime = self.compute_exptime(target_counts, meas_flux)
                    # Create photodiode readout handler.
                    pd_readout = PhotodiodeReadout(exptime, self)
        
                    for i in range(ntake):
                        print "##########"
                        print "### %d ###" % seqno
                        print "##########"
			    
                        pd_readout.start_accumulation()
                        fits_files = self.take_image(seqno, exptime, openShutter, actuateXed, image_type)
                        pd_readout.get_readings(fits_files, seqno, i)
			    

                seqno = seqno + 1


if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = GenericAcquisition(sequence_file, rtmacqcfgfile, metadata,
                             subsystems, ccd_names)
    acq.run()
    acq.sub.mono.synchCommand(900, "openShutter")
