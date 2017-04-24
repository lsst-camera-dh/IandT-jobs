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

__all__ = ["EOAcquisition", "PhotoDiodeReadout", "logger"]

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class EOAcquisition(object):
    """
    Base class for TS8 electro-optical data acquistion.
    """
    def __init__(self, seqfile, acq_config_file, acqname, metadata,
                 logger=logger):
        self.sub = CcsSubsystems(subsystems=dict(ts='ts',
                                                 pd_bias='ts/Bias',
                                                 pd='ts/PhotoDiode',
                                                 mono='ts/Monochromator',
                                                 ts8='ts8',
                                                 rebps='ccs-rebps'))
        self.seqfile = seqfile
        self.acq_config_file = acq_config_file
        self.acqname = acqname
        self.md = metadata
        self.logger = logger
        self._set_ts8_metadata()
        self._get_exptime_limits()
        self._get_image_counts()
        self._set_default_wavelength()
        self._read_instructions()
        self._fn_pattern = "${CCDSerialLSST}_${testType}_${imageType}_${SequenceInfo}_${RunNumber}_${timestamp}.fits"
        self.sub.ts8.synchCommand(90, "loadSequencer %s" % self.seqfile)
        self.sub.mono.synchCommand(20, "openShutter")

    def _set_ts8_metadata(self):
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

    def _get_exptime_limits(self):
        """
        Get the minimum and maximum exposure times from the config file.
        """
        self.exptime_min = float(eolib.getCfgVal(self.acq_config_file,
                                                 '%s_LOLIM' % self.acqname,
                                                 default='0.025'))
        self.exptime_max = float(eolib.getCfgVal(self.acq_config_file,
                                                 '%s_HILIM' % self.acqname,
                                                 default='600.0'))

    def _get_image_counts(self):
        """
        Get the number of exposures and bias frames to take for each
        acquisition instruction.
        """
        self.imcount = int(eolib.getCfgVal(self.acqcfgfile,
                                           '%s_IMCOUNT' % self.acqname,
                                           default='1'))
        self.bias_count = int(eolib.getCfgVal(self.acq_config_file,
                                              '%s_BCOUNT' % self.acqname,
                                              default='1'))

    def _set_default_wavelength(self):
        """
        Set the default wavelength for all acquistions.
        """
        self.wl = float(eolib.getCfgVal(self.acq_config_file,
                                        '%s_WL' % self.acqname,
                                        default="550.0"))
        self.set_wavelength(self.wl)

    def set_wavelength(self, wl):
        """
        Set the monochromator wavelength.
        """
        command = "setWaveAndFilter %s" % wl
        rwl = self.sub.mono.synchCommand(60, command).getResult()
        self.sub.ts8.synchCommand(10, "setMonoWavelength %s" % rwl)

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
                   timeout=500, max_tries=1, try_wait=10.):
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
        for itry in range(max_tries):
            try:
                result = self.sub.ts8.synchCommand(timeout, command).getResult()
                return result
            except StandardError as eobj:
                self.logger.info("EOAcquisition.take_image: try %i failed", itry)
                time.sleep(try_wait)
        raise eobj

    def images_clears(self, nclears=7):
        """
        Take some bias frames to clear the CCDs.
        """
        for i in range(nclears):
            try:
                self.take_image(0, 50, False, False, "biasclear",
                                file_template='')
            except StandardError as eobj:
                self.logger.info("Clear attempt %d failed:\n %s", i, str(eobj))
                time.sleep(1.0)
        raise eobj

    def bias_image(self, seqno, max_tries=3):
        """
        Take bias images.
        """
        exptime = 0
        openShutter = False
        actuateXed = False
        self.take_image(seqno, exptime, openShutter, actuateXed, "BIAS",
                        timeout=150, max_tries=max_tries)

    def measured_flux(self, seqno=0, exptime=2000, wl=None):
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
        # The calibration image.
        fits_files = self.take_image(seqno, exptime, openShutter, actuateXed,
                                     "fluxcalib", max_tries=3)
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
