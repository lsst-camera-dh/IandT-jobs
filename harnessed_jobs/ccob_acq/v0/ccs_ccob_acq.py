"""
Jython script for CCOB Wide Beam acquisitions.
"""
import time
from eo_acquisition import XYStageAcquisition, AcqMetadata, logger
import TS8Stage

class CcobWideBeamAcquisition(XYStageAcquisition):
    """
    XYStageAcquisition subclass for EO data taking using the CCOB wide beam.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(CcobWideBeamAcquisition, self).__init__(seqfile, acq_config_file,
                                                      "CCOB", metadata,
                                                      subsystems, ccd_names,
                                                      logger=logger)

    def take_ccob_image(seqno, exptime, file_template):
        raise NotImplemented("take_ccob_image not implemented")

    def run(self):
        """
        Take images at the various locations, with the number of images
        given by self.imcount and the number of bias frames given by
        self.bcount.
        """
        # Move to initial (xoffset, yoffset) position.
        self._moveTo(self.xoffset, self.yoffset)

        # Loop over image sequence.
        for seqno, tokens in enumerate(self.instructions):
            band = tokens[1]
            xrel = float(tokens[1])
            yrel = float(tokens[2])
            exptime = float(tokens[4])
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%04i_${RunNumber}_${timestamp}.fits' % (xrel, yrel, seqno)

            # Set band.
            self.sub.ccob.synchCommand(10, 'setBand', band)

            # Move to desired location.
            self._moveBy(xrel, yrel)

            # Take exposure(s).
            for i in range(self.imcount):
                self.take_ccob_image(seqno, exptime, file_template)

            # Take bias frame(s).
            for i in range(self.bcount):
                self.bias_image(seqno)

        # Return the XY stage to its home position.
        self.xy_stage.home((TS8Stage.X, TS8Stage.Y))


if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = XYStageEOAcquisition(sequence_file, rtmacqcfgfile, metadata,
                               subsystems, ccd_names)
    acq.run()
