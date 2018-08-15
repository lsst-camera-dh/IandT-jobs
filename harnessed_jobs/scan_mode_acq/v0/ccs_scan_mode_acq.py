"""
Jython script to do scan mode acquistions at TS8
"""
from eo_acquisition import EOAcquisition, AcqMetadata, logger
from ccs_scripting_tools import CCS

class ScanModeAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take scan mode datasets.
    """
    def __init__(self, seqfile, seq_scan_file, acq_config_file,
                 subsystems, ccd_names, logger=logger):
        super(ScanModeAcqusition, self).__init__(seqfile, acq_config_file,
                                                 'SCAN', metadata, subsystems,
                                                 ccd_names, logger=logger)

        self.seq_file = seq_file
        self.seq_scan_file = seq_scan_file

    def run(self):
        """
        Perform scan mode acquisition.  For each "scan" entry in the
        eo_acq.cfg file, take a bias frame and a flat.
        """
        openShutter = True
        actuateXed = False
        image_type = 'FLAT'
        self.sub.ts8.synchCommand(20, 'loadSequencer', self.seq_scanfile)
        for seqno, tokens in enumerate(self.instructions):
            tm_mode = bool(tokens[1])
            test_type = 'SCAN_TM' if tm_mode else 'SCAN_DSI'
            exptime = float(tokens[2])
            clamp = bool(tokens[3])
            n_seq_clears = int(tokens[4])
            self.set_clamp(clamp)
            # Take bias frame.
            self.set_scan_mode(True)
            self.set_tm_mode(tm_mode)
            self.bias_image(seqno, test_type=test_type)
            self.set_tm_mode(False)
            self.set_scan_mode(False)
            self.seq_clears(n_seq_clears)
            # Take flat.
            self.set_scan_mode(True)
            self.set_tm_mode(tm_mode)
            self.take_image(seqno, exptime, openShutter, actuateXed,
                            image_type, test_type=test_type)
            self.set_tm_mode(False)
            self.set_scan_mode(False)
            self.seq_clears(n_seq_clears)
            self.set_clamp(False)
        self.sub.ts8.synchCommand(20, 'loadSequencer', self.seq_file)

    def set_scan_mode(self, do_enable):
        """
        Enable or disable scan mode and set offset register to 0.
        """
        enable_bit = 1 if do_enable else 0
        rebs = self.sub.ts8.synchCommand(10, 'getREBDevices').getResult()
        for reb in rebs:
            self.sub.ts8.synchCommand(10, 'writeRegister R00.Reb{} 0x330000 {}'
                                      .format(reb, enable_bit))
            self.sub.ts8.synchCommand(10, 'writeRegister R00.Reb{} 0x330001 0'
                                      .format(reb))

    def seq_clears(self, n_seq_clears):
        """
        Clear CCD via sequence main "Clear".
        """
        for _ in range(n_seq_clears):
            self.sub.ts8.synchCommand(10, "setSequencerStart", "Clear")
            self.sub.ts8.synchCommand(10, "startSequencer")
            self.sub.ts8.synchCommand(10, "waitSequencerDone", 1000).getResult()
            self.sub.ts8.synchCommand(10, "setSequencerStart", "Bias")

    def set_clamp(self, do_clamp):
        '''
        Clamp (or not) the aspics.

        TODO: Check if this is really needed for the harnessed job.
        '''
        clamp = 0xff if do_clamp else 0x00
        ts8 = self.sub.ts8.name
        rebs = self.sub.ts8.synchCommand(10, 'getREBDevices').getResult()
        for reb in rebs:
            for aspic in range(6):
                aspic_sub = CCS.attachSubsystem('{}/R00.Reb{}.ASPIC{}'
                                                .format(ts8, reb, aspic))
                command = 'change clamp 0x{:x}'.format(clamp)
                aspic_sub.synchCommand(10, command)
                del aspic_sub
        self.sub.ts8.synchCommand(10, "loadAspics true")

    def set_tm_mode(self, tm_mode):
        """
        Set transparent mode.
        """
        mode_value = 'true' if tm_mode else 'false'
        ts8 = self.sub.ts8.name
        rebs = self.sub.ts8.synchCommand(10, 'getREBDevices').getResult()
        for reb in rebs:
            reb_sub = CCS.attachSubsystem('{}/R00.Reb{}'.format(ts8, reb))
            reb_sub.synchCommand(10, 'setAllTM {}'.format(mode_value))
            del reb_sub
        self.sub.ts8.synchCommand(10, 'loadAspics true')

if __name__ == '__main__':
    metadata = AcqMetadata(cwd=tsCWD, raft_id=UNITID, run_number=RUNNUM)
    acq = ScanModeAcquistion(sequence_file, seq_scan_file, rtmacqcfgfile,
                             metadata, subsystems, ccd_names)
    acq.run()
