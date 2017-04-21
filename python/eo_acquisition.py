class EOAcquisition(object):
    def __init__(self, seqfile, acq_config_file, metadata, logger=logger):
        self.ccs_sub = CcsSubsystems(subsystems=dict(ts='ts',
                                                     pd_bias='ts/Bias',
                                                     pd='ts/PhotoDiode',
                                                     mono='ts/Monochromator',
                                                     ts8='ts8',
                                                     rebps='ccs-rebps'))
        self.seqfile = seqfile
        self.acq_config_file = acq_config_file
        self.md = metadata
        self._get_exptime_limits()
        self._get_image_counts()
        self.ccs_sub.ts8.synchCommand(90, "loadSequencer %s" % self.seqfile)
        self.ccs_sub.mono.synchCommand(20, "openShutter")
        self._set_default_wavelength()
        # TODO: override this value in subclasses
        self._fn_pattern = "${CCDSerialLSST}_${testType}_${imageType}_${SequenceInfo}_${RunNumber}_${timestamp}.fits"
        self._read_instructions()

    def _get_exptime_limits(self):
        self.exptime_min = float(eolib.getCfgVal(self.acq_config_file,
                                                 '%s_LOLIM' % self.acqname,
                                                 default='0.025'))
        self.exptime_max = float(eolib.getCfgVal(self.acq_config_file,
                                                 '%s_HILIM' % self.acqname,
                                                 default='600.0'))
    def _get_image_counts(self):
        self.imcount = int(eolib.getCfgVal(self.acqcfgfile,
                                           '%s_IMCOUNT' % self.acqname,
                                           default='1'))
        self.bias_count = int(eolib.getCfgVal(self.acq_config_file,
                                              '%s_BCOUNT' % acqname,
                                              default='1'))

    def _set_default_wavelength(self):
        wl = float(eolib.getCfgVal(self.acq_config_file, '%s_WL' % self.acqname,
                                   default="550.0"))
        self.set_wavelength(wl)

    def set_wavelength(self, wl)
        command = "setWaveAndFilter %s" % wl
        rwl = self.ccs_sub.mono.synchCommand(60, command).getResult()
        self.ccs_sub.ts8.synchCommand(10, "setMonoWavelength %s" % rwl)

    def set_fits_filename_pattern(self, pattern=None):
        if pattern is None:
            pattern = self._fn_pattern
        ccs_sub.ts8.synchCommand(10, "setFitsFileNamePattern %s" % pattern)

    def set_metadata(self):
        command = "setDefaultImageDirectory %s/S${sensorLoc}" % self.md.cwd
        self.ccs_sub.ts8.synchCommand(10, command)
        command = "setRaftName %s" % self.md.raft_id
        self.ccs_sub.ts8.synchCommand(10, command)
        command = "setRunNumber %s" % self.md.run_number
        self.ccs_sub.ts8.synchCommand(10, command)

    def nplc(self, exptime):
        if exptime > 0.5:
            return 1.
        else:
            return 0.25

    def _read_instructions(self):
        self.instructions = []
        with open(self.acq_config_file) as input_:
            for line in input_:
                tokens = line.split()
                if tokens and tokens[0] == self.acqname.lower():
                    self.instructions.append(tokens)

    def run(self):
        raise NotImplementedError("Subclass must implement this function")

    @property
    def test_type(self):
        return self.acqname.upper()

    def bias_images_clears(self):
        for i in range(7):
            timestamp = time.time()
            self.logger.info("Taking clearing bias image: %f" % time.time())
            ccs_sub.ts8.synchCommand(10, "setTestType %s"
                                     % self.acqname.upper())
            ccs_sub.ts8.synchCommand(10, "setImageType biasclear")
            ccs_sub.ts8.synchCommand(10, "setSeqInfo %s" % 0)
            try:
                command = 'exposeAcquireAndSave 50 False False ""'
                ccs_sub.ts8.synchCommand(500, command)
            except StandardError as eobj:
                self.logger.info("Proceeding despite error:\n %s", str(eobj))
                time.sleep(1.0)

    def bias_images(self, max_tries=3):
        i = 0
        while i < self.bias_count:
            for itry in range(max_tries):
                try:
                    command = "setTestType %s" % self.test_type
                    self.ccs_sub.ts8.synchCommand(10, command)
                    self.ccs_sub.ts8.synchCommand(10, "setImageType BIAS")
                    command = "exposeAcquireAndSave 0 False False"
                    self.ccs_sub.ts8.synchCommand(command)
                    i += 1
                    break
                except StandardError as eobj:
                    if itry == (max_tries-1):
                        raise eobj
                    time.sleep(10.)

    def flux_calibration(self):
        pass

class FlatAcquisition(EOAcquisition):
    def __init__(self, seqfile, acq_config_file):
        self.acqname = 'FLAT'
        super(FlatAcquisition, self).__init__(seqfile, acq_config_file)
        self._fn_pattern = '${CCDSerialLSST}_${testType}_%07.2fs_${imageType}%d_${RunNumber}_${timestamp}.fits'
        self.imcount = 2
    def run(self):
        # Loop over instructions.
        self.flux_calibration()
        for seqno, tokens in enumerate(self.instructions):
            target_flux = float(tokens[1])
            self.set_metadata()
            self.bias_image_clears()
            command = "setFitsFileNamePattern %s" % self._fn_pattern
            self.ccs_sub.ts8.synchCommand(10, command)
            self.bias_images()
