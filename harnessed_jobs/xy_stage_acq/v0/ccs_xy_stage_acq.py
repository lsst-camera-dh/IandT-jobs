"""
Jython script for XY staged acquisitions at TS8.
"""
import time
from eo_acquisition import AcqMetadata, logger
from xy_stage_acquisition import XYStageAcquisition, XYStageAcquisitionError
import TS8Stage

class XYStageEOAcquisition(XYStageAcquisition):
    """
    XYStageAcquisition subclass for EO acquisitions at TS8 using the
    xy-stage.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(XYStageEOAcquisition, self).__init__(seqfile, acq_config_file,
                                                   "XY_STAGE", metadata,
                                                   subsystems, ccd_names,
                                                   logger=logger)

    def run(self):
        """
        Take images at the various locations, with the number of images
        given by self.imcount and the number of bias frames given by
        self.bcount.
        """
        # Move to initial (xoffset, yoffset) position.
        self._moveTo(self.xoffset, self.yoffset)

        # Loop over image sequence.
        actuateXed = False
        for seqno, tokens in enumerate(self.instructions):
            filter_pos = int(tokens[1])
            xrel = float(tokens[2])
            yrel = float(tokens[3])
            image_type = tokens[4]
            exptime = float(tokens[5])
            openShutter = (image_type != 'DARK')
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%03i_${RunNumber}.fits' % (xrel, yrel, seqno)

            # Set filter position, if it is a valid choice.
            # Otherwise, do nothing.
            if filter_pos in self._valid_filter_pos:
                self.sub.mono.synchCommand(10, 'setFilter', filter_pos)

            # Move to desired location.
            self._move_to_rel_pos(xrel, yrel)

            # Take exposure(s).
            for i in range(self.imcount):
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type, file_template=file_template)
            # Take bias frame(s).
            for i in range(self.bcount):
                self.bias_image(seqno)

        # Return the XY stage to its home position.
        #self.xy_stage.home((TS8Stage.X, TS8Stage.Y))


if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = XYStageEOAcquisition(sequence_file, rtmacqcfgfile, metadata,
                               subsystems, ccd_names)
    acq.run()
