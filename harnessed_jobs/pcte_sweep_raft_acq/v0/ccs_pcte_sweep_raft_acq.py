"""
Jython script to run parallel clock voltage sweep acquisitions at TS8.
"""

from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger
import itertools

class PcteSweepAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to sweep voltages and take flat image dataset.
    """

    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):

        super(PcteSweepAcquisition, self).__init__(seqfile, acq_config_file,
                                                       "PCTESWEEP", metadata,
                                                       subsystems, ccd_names,
                                                       logger=logger)

    def run(self):
        """
        Take flat datasets at each voltage setting in accordance to the
        configuration file.

        Sample config:

        PCTESWEEP_WL 500

        pctesweep 1000 2 -5.0 -4.0 0.5 4.0 5.0 0.5 
        """

        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        wl = float(self.eo_config.get("PCTESWEEP_WL", 500))

        seqno = 0
        for tokens in self.instructions:
            target_flux = float(tokens[1])
            nframes = int(tokens[2])
            min_parlo = float(tokens[3])
            max_parlo = float(tokens[4])
            step_parlo = float(tokens[5])
            min_parhi = float(tokens[6])
            max_parhi = float(tokens[7])
            step_parhi = float(tokens[8])

            if target_flux <1e4:
                flux_level = 'L'
            else:
                flux_level = 'H'
            meas_flux = self.measured_flux(wl)
            exptime = self.compute_exptime(target_flux, meas_flux)
            pd_readout = PhotodiodeReadout(exptime, self)

            ## Construct serial hi/lo voltage pairs
            parlo_values = [v/100. for v in range(int(100*min_parlo), int(100*max_parlo)+1,
                                                  int(100*step_parlo))]
            parhi_values = [v/100. for v in range(int(100*min_parhi), int(100*max_parhi)+1,
                                                  int(100*step_parhi))]
            voltage_pairs = itertools.product(parlo_values, parhi_values)

            for parlo, parhi in voltage_pairs:

                ## Sync commands issued to subsystems to change voltages
                self.sub.reb0rails.synchCommand(10, "change", "pclkLowP", parlo)
                self.sub.reb1rails.synchCommand(10, "change", "pclkLowP", parlo)
                self.sub.reb2rails.synchCommand(10, "change", "pclkLowP", parlo)
                self.sub.reb0rails.synchCommand(10, "change", "pclkHighP", parhi)
                self.sub.reb1rails.synchCommand(10, "change", "pclkHighP", parhi)
                self.sub.reb2rails.synchCommand(10, "change", "pclkHighP", parhi)

                ## Synch to ts8-raft to load DACs
                self.sub.ts8.synchCommand(10, "loadDacs true")
                
                for iframe in range(nframes):
                    self.bias_image(seqno)
                    file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%s%3.3d_${timestamp}.fits' % (parlo, parhi, flux_level, seqno+1)
                    pd_readout.start_accumulation()
                    fits_files = self.take_image(seqno, exptime, openShutter, 
                                                 actuateXed, image_type,
                                                 file_template=file_template)
                    pd_readout.get_readings(fits_files, seqno, 1)
                    seqno += 1

            self.set_nominal_voltages()

if __name__ == '__main__':

    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = PcteSweepAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                                       ccd_names)
    acq.run()
