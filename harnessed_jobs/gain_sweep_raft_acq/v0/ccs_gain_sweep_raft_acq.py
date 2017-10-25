"""
Jython script to run output drain and reset drain voltage sweep acquisitions at TS8.
"""

from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger
import numpy as np
import itertools

class GainSweepAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to sweep voltages and take flat image dataset.
    """

    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):

        super(GainSweepAcquisition, self).__init__(seqfile, acq_config_file,
                                                           "GAINSWEEP", metadata,
                                                           subsystems, ccd_names,
                                                           logger=logger)

    def run(self):
        """
        Take flat datasets at each voltage setting in accordance to the
        configuration file.

        Sample config:

        gainsweep 60 10 25.0 28.0 0.5 12.0 14.0 0.5 
        """

        openShutter = False
        actuateXed = True
        image_type = "FE55"

        seqno = 0
        for tokens in self.instructions:
            exptime = float(tokens[1])
            nframes = int(tokens[2])
            min_vod = float(tokens[3])
            max_vod = float(tokens[4])
            step_vod = float(tokens[5])
            min_vrd = float(tokens[6])
            max_vrd = float(tokens[7])
            step_vrd = float(tokens[8])

            ## Construct serial hi/lo voltage pairs
            vod_values = list(np.arange(min_vod, max_vod+0.1, step_vod))
            vrd_values = list(np.arange(min_vrd, max_vrd+0.1, step_vrd))
            voltage_pairs = itertools.product(vod_values, vrd_values)

            for vod, vrd in voltage_pairs:

                ## Sync commands issued to subsystems to change voltages
                self.sub.reb0bias0.synchCommand(10, "change", "odP", vod)
                self.sub.reb0bias1.synchCommand(10, "change", "odP", vod)
                self.sub.reb0bias2.synchCommand(10, "change", "odP", vod)
                self.sub.reb1bias0.synchCommand(10, "change", "odP", vod)
                self.sub.reb1bias1.synchCommand(10, "change", "odP", vod)
                self.sub.reb1bias2.synchCommand(10, "change", "odP", vod)
                self.sub.reb2bias0.synchCommand(10, "change", "odP", vod)
                self.sub.reb2bias1.synchCommand(10, "change", "odP", vod)
                self.sub.reb2bias2.synchCommand(10, "change", "odP", vod)

                self.sub.reb0bias0.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb0bias1.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb0bias2.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb1bias0.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb1bias1.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb1bias2.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb2bias0.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb2bias1.synchCommand(10, "change", "rdP", vrd)
                self.sub.reb2bias2.synchCommand(10, "change", "rdP", vrd)

                ## Synch to ts8-raft to load DACs
                self.sub.ts8.synchCommand(10, "loadBiasDacs true")
                
                for iframe in range(nframes):
                    self.bias_image(seqno)
                    file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%3.3d_${timestamp}.fits' % (vod, vrd, seqno+1)
                    fits_files = self.take_image(seqno, exptime, openShutter, 
                                                 actuateXed, image_type,
                                                 file_template=file_template)
                    seqno += 1
    
            self.set_nominal_voltages()
        

if __name__ == '__main__':

    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = GainSweepAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                                       ccd_names)
    acq.run()
