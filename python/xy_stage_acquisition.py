import time
from eo_acquisition import EOAcquisition, logger
import TS8Stage

class XYStageAcquisitionError(RuntimeError):
    def __init__(self, *args, **kwds):
        super(XYStageAcquisitionError, self).__init__(args, kwds)

class XYStageAcquisition(EOAcquisition):
    """
    EOAcquisition base class for taking data using the XY stage at TS8.
    """
    def __init__(self, seqfile, acq_config_file, acqname, metadata,
                 subsystems, ccd_names, logger=logger):
        super(XYStageAcquisition, self).__init__(seqfile, acq_config_file,
                                                 acqname, metadata,
                                                 subsystems, ccd_names,
                                                 logger=logger)

        # Valid filter positions for TS8: 1 through 6
        self._valid_filter_pos = range(1, 7)

        self.bcount = int(self.eo_config.get('%s_BCOUNT' % acqname.upper(),
                                             default=1))
        self.dcount = int(self.eo_config.get('%s_DCOUNT' % acqname.upper(),
                                             default=0))
        self.imcount = int(self.eo_config.get('%s_IMCOUNT' % acqname.upper(),
                                              default=1))
        self.xoffset = float(self.eo_config.get('%s_XOFFSET' % acqname.upper(),
                                                default=0.))
        self.yoffset = float(self.eo_config.get('%s_YOFFSET' % acqname.upper(),
                                                default=0.))
        self.theta0 = float(self.eo_config.get('%s_THETA0' % acqname.upper(),
                                               default=0.))
        self.xy_stage = TS8Stage.Stage(self.sub.xy_stage.name)

        # Set the XY stage at its home position.
        #self.xy_stage.home(TS8Stage.X, TS8Stage.Y)

    def _moveTo(self, xpos, ypos, retries=2, tol=0.01):
        # Move along the y-axis to the absolute ypos position.
        logger.info("moving xy stage to absolute y-position %.1f mm", ypos)
        ntries = 0
        while True:
            self.xy_stage.enable(TS8Stage.Y)
            self.xy_stage.moveTo(TS8Stage.Y, ypos, TS8Stage.Y.maxSpeed)
            ystat = self.xy_stage.getAxisStatus(TS8Stage.Y)
            if abs(ystat.getPosition() - ypos) < tol:
                break
            ntries += 1
            if ntries > retries:
                raise XYStageAcquisitionError("current ypos, target ypos = %s, %s"
                                              % (ystat.getPosition(), ypos))
        time.sleep(1)

        # Move along the x-axis to the absolute xpos position.
        logger.info("moving xy stage to absolute x-position %.1f mm", xpos)
        ntries = 0
        while True:
            self.xy_stage.enable(TS8Stage.X)
            self.xy_stage.moveTo(TS8Stage.X, xpos, TS8Stage.X.maxSpeed)
            xstat = self.xy_stage.getAxisStatus(TS8Stage.X)
            if abs(xstat.getPosition() - xpos) < tol:
                break
            ntries += 1
            if ntries > retries:
                raise XYStageAcquisitionError("current xpos, target xpos = %s, %s"
                                              % (xstat.getPosition(), xpos))
        time.sleep(1)

    def _move_to_rel_pos(self, xrel, yrel):
        self._moveTo(self.xoffset + xrel, self.yoffset + yrel)

    def _moveBy(self, dx, dy):
        # Move along the x-axis by a relative amount dx.
        self.xy_stage.enable(TS8Stage.X)
        self.xy_stage.moveBy(TS8Stage.X, dx, TS8Stage.X.maxSpeed)

        # Move along the y-axis to the absolute ypos position.
        self.xy_stage.enable(TS8Stage.Y)
        self.xy_stage.moveBy(TS8Stage.Y, dy, TS8Stage.Y.maxSpeed)
