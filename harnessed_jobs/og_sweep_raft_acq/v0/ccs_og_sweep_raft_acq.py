"""
Jython script to run output gate voltage sweep acquisitions at TS8.
"""

from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger
import numpy as np
import itertools

class OGSweepAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to sweep voltages and take flat image dataset.
    """

    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):

        super(OGSweepAcquisition, self).__init__(seqfile, acq_config_file,
                                                 "OGSWEEP", metadata,
                                                 subsystems, ccd_names,
                                                 logger=logger)

    def run(self):
        """
        Take flat datasets at each voltage setting in accordance to the
        configuration file.

        Sample config:

        OGSWEEP_WL 500

        ogsweep 1000 2 -3.0 0.0 0.5 
        """

        openShutter = True
        actuateXed = False
        image_type = "FLAT"

        wl = float(self.eo_config.get("OGSWEEP_WL", 500))

        seqno = 0
        for tokens in self.instructions:
            target_flux = float(tokens[1])
            nframes = int(tokens[2])
            min_vog = float(tokens[3])
            max_vog = float(tokens[4])
            step_vog = float(tokens[5])
            test_type = "OGSWEEP" % wl # Change to desired test name

            if target_flux <1e4:
                flux_level = 'L'
            else:
                flux_level = 'H'
            meas_flux = self.measured_flux(wl)
            exptime = self.compute_exptime(target_flux, meas_flux)
            pd_readout = PhotodiodeReadout(exptime, self)

            ## Construct serial hi/lo voltage pairs
            vog_values = list(np.arange(min_vog, max_vog+0.1, step_vog)) # Potential danger with inexact floats

            for vog in og_values:

                ## Sync commands issued to subsystems to change voltages
                self.sub.reb0bias0.synchCommand(10, "change", "ogP", vog)
                self.sub.reb0bias1.synchCommand(10, "change", "ogP", vog)
                self.sub.reb0bias2.synchCommand(10, "change", "ogP", vog)
                self.sub.reb1bias0.synchCommand(10, "change", "ogP", vog)
                self.sub.reb1bias1.synchCommand(10, "change", "ogP", vog)
                self.sub.reb1bias2.synchCommand(10, "change", "ogP", vog)
                self.sub.reb2bias0.synchCommand(10, "change", "ogP", vog)
                self.sub.reb2bias1.synchCommand(10, "change", "ogP", vog)
                self.sub.reb2bias2.synchCommand(10, "change", "ogP", vog)

                ## Synch to ts8-raft to load DACs
                self.sub.ts8.synchCommand(10, "loadBiasDacs true")
                
                for iframe in range(nframes):
                    self.image_clears()
                    self.bias_image(seqno)
                    file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%s%3.3d_${timestamp}.fits' % (vog, flux_level, seqno+1)
                    pd_readout.start_accumulation()
                    fits_files = self.take_image(seqno, exptime, openShutter, 
                                                 actuateXed, image_type,
                                                 test_type=test_type,
                                                 file_template=file_template)
                    pd_readout.get_readings(fits_files, seqno, 1)
                    seqno += 1

if __name__ == '__main__':

    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = OGSweepAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                                       ccd_names)
    acq.run()
