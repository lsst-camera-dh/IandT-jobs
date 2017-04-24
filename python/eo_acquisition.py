"""
TestStand 8 electro-optical acquisition scripting module.
"""
import os
import sys
import glob
import time
import logging
from ccs_scripting_tools import CcsSubsystems
import eolib

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class EOAcquisition(object):
    """
    Base class for TS8 electro-optical data acquistion.
    """
    def __init__(self, seqfile, acq_config_file, metadata, logger=logger):
        self.sub = CcsSubsystems(subsystems=dict(ts='ts',
                                                 pd_bias='ts/Bias',
                                                 pd='ts/PhotoDiode',
                                                 mono='ts/Monochromator',
                                                 ts8='ts8',
                                                 rebps='ccs-rebps'))
        self.seqfile = seqfile
        self.acq_config_file = acq_config_file
        self.md = metadata
        self.logger = logger
        self._get_exptime_limits()
        self._get_image_counts()
        self.sub.ts8.synchCommand(90, "loadSequencer %s" % self.seqfile)
        self.sub.mono.synchCommand(20, "openShutter")
        self._set_default_wavelength()
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
                                              '%s_BCOUNT' % self.acqname,
                                              default='1'))

    def _set_default_wavelength(self):
        wl = float(eolib.getCfgVal(self.acq_config_file, '%s_WL' % self.acqname,
                                   default="550.0"))
        self.set_wavelength(wl)
        self.wl = wl

    def set_wavelength(self, wl):
        """
        Set the monochromator wavelength.
        """
        command = "setWaveAndFilter %s" % wl
        rwl = self.sub.mono.synchCommand(60, command).getResult()
        self.sub.ts8.synchCommand(10, "setMonoWavelength %s" % rwl)

    def set_fits_filename_pattern(self, pattern=None):
        """
        Set the filename pattern for the output FITS files.
        """
        if pattern is None:
            pattern = self._fn_pattern
        self.sub.ts8.synchCommand(10, "setFitsFileNamePattern %s" % pattern)

    def set_metadata(self):
        """
        Pass metadata such as image output directory, raft name, run
        number to the ts8 subsystem.
        """
        command = "setDefaultImageDirectory %s/S${sensorLoc}" % self.md.cwd
        self.sub.ts8.synchCommand(10, command)
        command = "setRaftName %s" % self.md.raft_id
        self.sub.ts8.synchCommand(10, command)
        command = "setRunNumber %s" % self.md.run_number
        self.sub.ts8.synchCommand(10, command)

    def _read_instructions(self):
        self.instructions = []
        with open(self.acq_config_file) as input_:
            for line in input_:
                tokens = line.split()
                if tokens and tokens[0] == self.acqname.lower():
                    self.instructions.append(tokens)

    def run(self):
        """
        Default run method to be re-implemented in subclasses.
        """
        raise NotImplementedError("Subclass must implement this function")

    @property
    def test_type(self):
        """
        The test type, e.g., FLAT, FE55, SFLAT, DARK, etc..
        """
        return self.acqname.upper()

    def take_image(self, seqno, exptime, openShutter, actuateXed,
                   image_type, test_type=None, file_template=None,
                   timeout=500):
        """
        Take an image.
        """
        if test_type is None:
            test_type = self.test_type
        if file_template is None:
            file_template = self._fn_pattern
        self.sub.ts8.synchCommand(10, "setTestType %s" % test_type)
        self.sub.ts8.synchCommand(10, "setImageType %s" % image_type)
        self.sub.ts8.synchCommand(10, "setSeqInfo %d" % seqno)
        command = 'exposeAcquireAndSave %d %s %s "%s"' \
            % (exptime, openShutter, actuateXed, file_template)
        return self.sub.ts8.synchCommand(timeout, command).getResult()

    def images_clears(self, nclears=7):
        """
        Take some bias frames to clear the CCDs.
        """
        for i in range(nclears):
            self.logger.info("Taking clearing bias image: %f", time.time())
            try:
                self.take_image(0, 50, False, False, "biasclear",
                                file_template='')
            except StandardError as eobj:
                self.logger.info("Clear attempt %d failed:\n %s", i, str(eobj))
                time.sleep(1.0)

    def bias_images(self, seqno, max_tries=3):
        """
        Take bias images.
        """
        exptime = 0
        i = 0
        while i < self.bias_count:
            for itry in range(max_tries):
                try:
                    self.take_image(seqno, exptime, False, False, "BIAS",
                                    timeout=150)
                    i += 1
                    break
                except StandardError as eobj:
                    if itry == (max_tries-1):
                        raise eobj
                    time.sleep(10.)

    def measured_flux(self, seqno, exptime=2000, wl=None):
        """
        Compute the measured flux by taking an exposure at the
        specified wavelength.
        """
        if wl is not None:
            self.set_wavelength(wl)
        self.sub.ts.synchCommand(60, "publishState")
        openShutter = True
        actuateXed = False
        # Take a test image.
        self.take_image(seqno, exptime, openShutter, actuateXed, "prefluxcalib",
                        file_template='')
        # Take flux calibration image.
        fits_files = self.take_image(seqno, exptime, openShutter, actuateXed,
                                     "fluxcalib")
        flux_sum = 0.
        for fits_file in fits_files:
            file_path = glob.glob(os.path.join(self.md.cwd, '*', fits_file))[0]
            command = "getFluxStats %s" % file_path
            flux_sum += \
                float(self.sub.ts8.synchCommand(10, command).getResult())
        return flux_sum/len(fits_files)

class PhotoDiodeReadout(object):
    """
    Class to handle monitoring photodiode readout.
    """
    def __init__(self, exptime, eo_acq_object, max_reads=2048):
        self.sub = eo_acq_object.sub
        self.md = eo_acq_object.md
        self.logger = eo_acq_object.logger
        if exptime > 0.5:
            nplc = 1.
        else:
            nplc = 0.25

        nreads = min((exptime + 2.)*60./nplc, max_reads)
        self.nreads = int(nreads)
        self.nplc = int((exptime + 2.)*60./nreads)
        self._pd_result = None
        self._start_time = None

    def start_accumulation(self):
        """
        Start the asynchronous accumulation of photodiode current readings.
        """
        command = "accumBuffer %d %d True" % (self.nreads, self.nplc)
        self._pd_result = self.sub.pd.asynchCommand(command)
        running = False
        while not running:
            try:
                running = self.sub.pd.synchCommand(20, "isAccumInProgress").getResult()
            except StandardError as eobj:
                self.logger.info("PhotoDiodeReadout.start_accumlation:")
                self.logger.info(str(eobj))
            time.sleep(0.25)
        self._start_time = time.time()
        self.logger.info("Photodiode readout accumulation started at %f"
                         % self._start_time)

    def get_readings(self, fits_files, seqno, icount):
        """
        Output the accumulated photodiode readings to a text file and
        write that time history to the FITS files as a binary table
        extension.
        """
        pd_filename = os.path.join(self.md.cwd,
                                   "pd-values_%d-for-seq-%d-exp-%d.txt"
                                   % (int(self._start_time), seqno, icount))
        time.sleep(10.)
        command = "readBuffer %s %s" % (pd_filename, "ts8prod@ts8-raft1")
        self.sub.pd.synchCommand(1000, command)
        time.sleep(5.)
        for fits_file in fits_files:
            full_path = glob.glob('%s/*/%s' % (self.md.cwd, fits_file))[0]
            command = "addBinaryTable %s %s AMP0.MEAS_TIMES AMP0_MEAS_TIMES AMP0_A_CURRENT %d" % (pd_filename, full_path, self._start_time)
            self.sub.ts8.synchCommand(200, command)

class FlatAcquisition(EOAcquisition):
    """
    EOAcquisition subclass to take the flat pair dataset.
    """
    def __init__(self, seqfile, acq_config_file):
        self.acqname = 'FLAT'
        super(FlatAcquisition, self).__init__(seqfile, acq_config_file)
        self.imcount = 2

    def run(self):
        """
        Take the flat pair sequence, reading the target signal levels
        from the configuration file.
        """
        openShutter = True
        actuateXed = False
        self.set_metadata()
        # Get measured flux at current wavelength for exposure time
        # calculation.
        meas_flux = self.measured_flux(0)  # e-/pixel/second
        # Loop over exposure pairs.
        for seqno, tokens in enumerate(self.instructions):
            self.image_clears()
            self.bias_images(seqno)
            # Compute exposure time to obtain the desired signal level.
            target_counts = float(tokens[1])  # e-/pixel
            exptime = target_counts/meas_flux
            # Impose exposure time limits.
            exptime = min(max(exptime, self.exptime_min), self.exptime_max)

            # Create photodiode readout handler.
            pd_readout = PhotoDiodeReadout(exptime, self)
            for icount in range(self.imcount):
                self.image_clears(nclears=3)
                file_template = '${CCDSerialLSST}_${testType}_%07.2fs_${imageType}%d_${RunNumber}_${timestamp}.fits' % (exptime, icount+1)
                pd_readout.start_accumulation()
                fits_files = self.take_image(seqno, exptime, openShutter,
                                             actuateXed, "FLAT",
                                             file_template=file_template)
                pd_readout.get_readings(fits_files, seqno, icount)
