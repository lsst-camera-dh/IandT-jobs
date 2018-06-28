"""
Jython script to run output drain and reset drain voltage sweep acquisitions at TS8.
"""

from eo_acquisition import EOAcquisition, PhotodiodeReadout, AcqMetadata, logger
import numpy as np
import itertools

class LinearitySweepAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to sweep voltages and take flat image dataset.
    """

    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):

        super(LinearitySweepAcquisition, self).__init__(seqfile, acq_config_file,
                                                           "LINEARITYSWEEP", metadata,
                                                           subsystems, ccd_names,
                                                           logger=logger)

    def run(self):
        """
        Take flat datasets at each voltage setting in accordance to the
        configuration file.

        Sample config:

        linearitysweep 60 10 25.0 28.0 0.5 12.0 14.0 0.5 
        """

        openShutter = True
        actuateXed = False
        image_type = "RAMP"

        seqno = 0
        for tokens in self.instructions:
            rowdelay = int(tokens[1])
            nframes = int(tokens[2])
            min_vod = float(tokens[3])
            max_vod = float(tokens[4])
            step_vod = float(tokens[5])
            min_vrd = float(tokens[6])
            max_vrd = float(tokens[7])
            step_vrd = float(tokens[8])
            exptime = int(2048*rowdelay/1000000)

            self.sub.ts8.synchCommand(10, "setParameter", "Slope", 0)
            self.sub.ts8.synchCommand(10, "setParameter", "SlopeDelay", rowdelay)

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
                self.sub.ts8.synchCommand(10, "loadBiasDacs true")
                
                for iframe in range(nframes):
                    self.bias_image(seqno) # Will this work with the ramp sequencer?
                    file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%3.3d_${timestamp}.fits' % (vod, vrd, seqno+1)
                    fits_files = self.take_image(seqno, exptime, openShutter, 
                                                 actuateXed, image_type,
                                                 file_template=file_template)
                    seqno += 1

if __name__ == '__main__':

    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = LinearitySweepAcquisition(sequence_file, rtmacqcfgfile, metadata, subsystems,
                                       ccd_names)
    acq.run()
