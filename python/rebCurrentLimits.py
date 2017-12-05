"""
Class to handle REB current limit comparisons described in LCA-10064.
"""
from collections import OrderedDict, namedtuple
import java.lang

ChannelLimits = namedtuple('ChannelLimits',
                           ['reb_ps_name','low_lim', 'high_lim', 'comp_range'])

class RebCurrentLimits(OrderedDict):
    """
    Attributes
    ----------

    rebps : CCS subsystem object
        REB power supply subsystem, decorated by SubsystemDecorator.

    ts8 : CCS subsystem object
        TS8 raft subsystem, decorated by SubsystemDecorator.

    logger : Logging.Logger
        Logger object from self.rebps.
    """
    def __init__(self, rebps, ts8):
        """
        Parameters
        ----------

        rebps : CCS subsystem object
            REB power supply subsystem, decorated by SubsystemDecorator.

        ts8 : CCS subsystem object
            TS8 raft subsystem, decorated by SubsystemDecorator.
        """
        super(RebCurrentLimits, self).__init__()
        self.rebps = rebps
        self.ts8 = ts8
        self.logger = rebps.logger
        self['DigI'] = ChannelLimits('digital.IaftLDO', 500., 650., 100.)
        self['AnaI'] = ChannelLimits('analog.IaftLDO', 530., 615., 50.)
        self['ClkHI'] = ChannelLimits('clockhi.IaftLDO', 80., 92., 25.)
        self['ClkLI'] = ChannelLimits('clocklo.IaftLDO', 32., 42., 25.)
        self['ODI'] = ChannelLimits('OD.IaftLDO', 7., 13., 10.)
        self['HtrI'] = ChannelLimits('heater.IaftLDO', 0., 2., 0.)

    def check_rebps_limits(self, rebid, raise_exception=True):
        """
        Check the REB currents at the power supply are within the
        LCA-10064 limits for the specified REB.

        Parameters
        ----------

        rebid : int
            ID of the REB to test.

        Raises
        ------
        java.lang.Exception : If the current of any channel is out of range.
        """
        for limits in self.values():
            ps_channel_name = 'REB%d.%s' % (rebid, limits.reb_ps_name)
            ps_current = self.rebps.synchCommand(10, 'readChannelValue',
                                                 ps_channel_name).getResult()
            self.logger.info("%s: %s mA", ps_channel_name, ps_current)
            if ps_current < limits.low_lim or ps_current > limits.high_lim:
                self.rebps.synchCommand(10, 'sequencePower', rebid, False)
                message = '%s current out of range. Powering down this REB.' \
                          % ps_channel_name
                if raise_exception:
                    raise java.lang.Exception(message)
                else:
                    self.logger.info(message)

    def check_comparative_ranges(self, rebid, raise_exception=True):
        """
        Compare the currents at the power supply to the currents
        measured at the REB.  Issue a warning if they are outside the
        comparative range specified in LCA-10064.

        Parameters
        ----------

        rebid : int
            ID of the REB to test.
        """
        for channel_name, limits in self.items():
            if channel_name == 'HtrI':
                # There is no current channel for the heater in
                # the TS monitoring subsystem, so skip this check
                continue
            ps_channel_name = 'REB%d.%s' % (rebid, limits.reb_ps_name)
            ps_current = self.rebps.synchCommand(10, 'readChannelValue',
                                                 ps_channel_name).getResult()
            reb_channel_name = 'R00.Reb%d.%s' % (rebid, channel_name)
            reb_current = self.ts8.synchCommand(10, 'readChannelValue',
                                                reb_channel_name).getResult()
            if abs(ps_current - reb_current) > limits.comp_range:
                message \
                    = "Currents for %s and %s lie outside comparative range." \
                    % (ps_channel_name, reb_channel_name)
                if raise_exception:
                    raise java.lang.Exception(message)
                else:
                    self.logger.info(message)