"""
Jython script for XY staged acquisitions at TS8.
"""
import time
from eo_acquisition import EOAcquisition, AcqMetadata, logger
import TS8Stage

class XYStageAcquisition(EOAcquisition):
    """
    EOAcquisition subclass for "preflight" data.
    """
    def __init__(self, seqfile, acq_config_file, metadata, subsystems,
                 ccd_names, logger=logger):
        super(XYStageAcquisition, self).__init__(seqfile, acq_config_file,
                                                 "XY_STAGE", metadata,
                                                 subsystems, ccd_names,
                                                 logger=logger)

        self.xoffset = float(self.eo_config.get('XY_STAGE_XOFFSET',
                                                default=0.))
        self.yoffset = float(self.eo_config.get('XY_STAGE_YOFFSET',
                                                default=0.))
        self.theta0 = float(self.eo_config.get('XY_STAGE_THETA0', default=0.))
        self.xy_stage = TS8Stage.Stage(self.sub.xy_stage.name)

        # Set the XY stage at its home position.
        self.xy_stage.home((TS8Stage.X, TS8Stage.Y))

    def _moveTo(self, xpos, ypos):
        # Move along the x-axis to the absolute xpos position.
        self.xy_stage.enable(TS8Stage.X)
        self.xy_stage.moveTo(TS8Stage.X, xpos, TS8Stage.X.maxSpeed)
        self.xy_stage.disable(TS8Stage.X)

        # Move along the y-axis to the absolute ypos position.
        self.xy_stage.enable(TS8Stage.Y)
        self.xy_stage.moveTo(TS8Stage.Y, ypos, TS8Stage.Y.maxSpeed)
        self.xy_stage.disable(TS8Stage.Y)

    def _moveBy(self, dx, dy):
        # Move along the x-axis by a relative amount dx.
        self.xy_stage.enable(TS8Stage.X)
        self.xy_stage.moveBy(TS8Stage.X, dx, TS8Stage.X.maxSpeed)
        self.xy_stage.disable(TS8Stage.X)

        # Move along the y-axis to the absolute ypos position.
        self.xy_stage.enable(TS8Stage.Y)
        self.xy_stage.moveBy(TS8Stage.Y, dy, TS8Stage.Y.maxSpeed)
        self.xy_stage.disable(TS8Stage.Y)

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
            xrel = float(tokens[1])
            yrel = float(tokens[2])
            image_type = tokens[3]
            exptime = float(tokens[4])
            openShutter = (image_type == 'DARK')
            file_template = '${CCDSerialLSST}_${testType}_${imageType}_%.2f_%.2f_%04i_${RunNumber}_${timestamp}.fits' % (xrel, yrel, seqno)

            # Move to desired location.
            self._moveBy(xrel, yrel)

            # Take exposure(s).
            for i in range(self.imcount):
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type, file_template=file_template)
            # Take bias frame(s).
            image_type = 'BIAS'
            openShutter = False
            exptime = 0
            for i in range(self.bcount):
                self.take_image(seqno, exptime, openShutter, actuateXed,
                                image_type, file_template=file_template)

        # Return the XY stage to its home position.
        self.xy_stage.home((TS8Stage.X, TS8Stage.Y))


if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = XYStageAcquisition(sequence_file, rtmacqcfgfile, metadata,
                             subsystems, ccd_names)
    acq.run()
