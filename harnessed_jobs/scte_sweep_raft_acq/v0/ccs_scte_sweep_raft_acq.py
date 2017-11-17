"""
Jython script to run serial clock voltage sweep acquisitions at TS8.
"""

from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger
import itertools

class ScteSweepAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to sweep voltages and take flat image dataset.
    """

    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):

        super(ScteSweepAcquisition, self).__init__(seqfile, acq_config_file,
                                                     "SCTESWEEP", metadata,
                                                     subsystems, ccd_names,
                                                     logger=logger)

    def run(self):
        """
        Take flat datasets at each voltage setting in accordance to the
        configuration file.

        Sample config:

        SCTESWEEP_WL 500

        sctesweep 1000 2 -5.0 -4.0 0.5 4.0 5.0 0.5 
        """

        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        wl = float(self.eo_config.get("SCTESWEEP_WL", 500))

        seqno = 0
        for tokens in self.instructions:
            target_flux = float(tokens[1])
            nframes = int(tokens[2])
            min_serlo = float(tokens[3])
            max_serlo = float(tokens[4])
            step_serlo = float(tokens[5])
            min_serhi = float(tokens[6])
            max_serhi = float(tokens[7])
            step_serhi = float(tokens[8])

            if target_flux <1e4:
                flux_level = 'L'
            else:
                flux_level = 'H'
            meas_flux = self.measured_flux(wl)
            exptime = self.compute_exptime(target_flux, meas_flux)
            pd_readout = PhotodiodeReadout(exptime, self)

            ## Construct serial hi/lo voltage pairs
            serlo_values = [v/100. for v in range(int(100*min_serlo), int(100*max_serlo)+1,
                                                  int(100*step_serlo))]
            serhi_values = [v/100. for v in range(int(100*min_serhi), int(100*max_serhi)+1,
                                                  int(100*step_serhi))]
            voltage_pairs = itertools.product(serlo_values, serhi_values)

            for serlo, serhi in voltage_pairs:

                ## Sync commands issued to subsystems to change voltages
                self.sub.reb0rails.synchCommand(10, "change", "sclkLowP", serlo)
                self.sub.reb1rails.synchCommand(10, "change", "sclkLowP", serlo)
                self.sub.reb2rails.synchCommand(10, "change", "sclkLowP", serlo)
                self.sub.reb0rails.synchCommand(10, "change", "sclkHighP", serhi)
                self.sub.reb1rails.synchCommand(10, "change", "sclkHighP", serhi)
                self.sub.reb2rails.synchCommand(10, "change", "sclkHighP", serhi)

                ## Synch to ts8-raft to load DACs
                self.sub.ts8.synchCommand(10, "loadDacs true")
                
                for iframe in range(nframes):
                    self.bias_image(seqno)
                    file_template = '${CCDSerialLSST}_${testType}_%.2f_%.2f_${imageType}_%s%3.3d_${timestamp}.fits' % (serlo, serhi, flux_level, seqno+1)
                    pd_readout.start_accumulation()
                    fits_files = self.take_image(seqno, exptime, openShutter, 
                                                 actuateXed, image_type,
                                                 file_template=file_template)
                    pd_readout.get_readings(fits_files, seqno, 1)
                    seqno += 1

            self.set_nominal_voltages()

if __name__ == '__main__':

    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = ScteSweepAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                                       ccd_names)
    acq.run()
