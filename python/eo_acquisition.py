"""
Test Stand 8 electro-optical acquisition jython scripting module.
"""
from __future__ import print_function
import os
import sys
import glob
import time
from collections import namedtuple
import logging
import re
try:
    import java.lang
except ImportError:
    print("could not import java.lang")
from ccs_scripting_tools import CcsSubsystems, CCS
from ts8_utils import set_ccd_info, write_REB_info

__all__ = ["hit_target_pressure", "EOAcquisition",
           "PhotodiodeReadout", "EOAcqConfig", "AcqMetadata", "logger"]

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()


def hit_target_pressure(vac_sub, target, wait=5, tmax=7200, logger=logger):
    """
    Function to wait until target pressure in vacuum gauge subsystem
    is attained.

    Parameters
    ----------
    vac_sub : CCS subsystem
        The vacuum subsystem.
    target : float
        The target pressure (torr).
    wait : float, optional
        The wait time (sec) between pressure reads.  Default: 5
    tmax : float, optional
        The maximum time (sec) to allow for the target pressure to be attained.
        Default: 7200
    logger : logging.Logger
        The logger object.
    """
    tstart = time.time()
    pressure = vac_sub.synchCommand(20, "readPressure")
    while pressure > target or pressure < 0:
        logger.info("time = %s, pressure = %f", time.time(), pressure)
        if (time.time() - tstart) > tmax:
            raise RuntimeError("Exceeded allowed pump-down time for "
                               + "target pressure %s" % target)
        time.sleep(wait)
        pressure = vac_sub.synchCommand(20, "readPressure")


AcqMetadata = namedtuple('AcqMetadata', 'cwd raft_id run_number'.split())


class EOAcqConfig(dict):
    """
    Read the entries as key/value pairs from the acquisition
    configuration file that specifies the frames, exposure times, and
    signal levels for the various electro-optical tests.
    """
    def __init__(self, acq_config_file):
        """
        Parameters
        ----------
        acq_config_file : str
            The path to the acquisition configuration file.
        """
        super(EOAcqConfig, self).__init__()
        with open(acq_config_file) as input_:
            for line in input_:
                tokens = line.split()
                if len(tokens) < 2:
                    continue
                key = tokens[0].upper()
                if not self.has_key(key):
                    self[key] = tokens[1]

    def get(self, key, default="NOT FOUND"):
        """
        Get the desired value for the specified key, providing an
        optional default.
        """
        return super(EOAcqConfig, self).get(key, default)


class EOAcquisition(object):
    """
    Base class for TS8 electro-optical data acquisition.
    """
    def __init__(self, seqfile, acq_config_file, acqname, metadata,
                 subsystems, ccd_names, logger=logger, slit_id=2):
        """
        Parameters
        ----------
        seqfile : str
            The name of the sequencer file.
        acq_config_file : str
            The name of the acquisition configuration file.
        acqname : str
            The test type, e.g., 'FE55', 'FLAT', 'SFLAT', etc..
        metadata : namedtuple
            A nametuple of test-wide metadata, specifically, the
            current working directory, the LSST unit ID for the raft,
            and the run number.
        subsystems : dict
            A dictionary of CCS subsystems, keyed by standard attribute
            names for the CcsSubsystems class, i.e., 'ts', 'ts8', 'pd',
            and 'mono'.  If None, then the default subsystems, 'ts', 'ts8',
            'ts/PhotoDiode', and 'ts/Monochromator', will be attached.
        ccd_names : dict
            Dictionary of namedtuple containing the CCD .sensor_id and
            .maufacturer_sn information, keyed by slot name.
        logger : logging.Logger
            Log commands using the logger.info(...) function.
        slit_id: int [2]
            ID of the monochormator slit to set via ._set_slitwidth(...)
        """
        if subsystems is None:
            subsystems = dict(ts8='ts8', pd='ts8/Monitor',
                              mono='ts8/Monochromator')
        self.sub = CcsSubsystems(subsystems=subsystems, logger=logger)
        self.sub.write_versions(os.path.join(metadata.cwd, 'ccs_versions.txt'))
        self._check_subsystems()
        write_REB_info(self.sub.ts8,
                       outfile=os.path.join(metadata.cwd, 'reb_info.txt'))
        set_ccd_info(self.sub, ccd_names, logger)
        self.sub.ts8.synchCommand(10, 'setDefaultImageDirectory %s/S${sensorLoc}'
                                  % metadata.cwd)
        self.seqfile = seqfile
        self.eo_config = EOAcqConfig(acq_config_file)
        self.acqname = acqname
        self.md = metadata
        self.logger = logger
        self.slit_id = slit_id
        self._set_ts8_metadata()
        self._get_exptime_limits()
        self._get_image_counts()
        self._set_default_wavelength()
        self.current_slitwidth \
            = int(self.eo_config.get('DEFAULT_SLITWIDTH', default=240))
        self.set_slitwidth(self.current_slitwidth, self.slit_id)
        self._read_instructions(acq_config_file)
        self._fn_pattern = "${CCDSerialLSST}_${testType}_${imageType}_${SequenceInfo}_${RunNumber}_${timestamp}.fits"
        self.sub.ts8.synchCommand(90, "loadSequencer", self.seqfile)
        self.sub.mono.synchCommand(20, "openShutter")

    def _check_subsystems(self):
        """
        Check that the required subsystems are present.
        """
        required = 'ts8 pd mono ts8dac0 ts8dac1 ts8dac2'.split()
        missing = []
        for subsystem in required:
            if not hasattr(self.sub, subsystem):
                missing.append(subsystem)
        if missing:
            raise RuntimeError("EOAcquisition: missing CCS subsystems:"
                               + '\n'.join(missing))

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
        self.exptime_min = float(self.eo_config.get('%s_LOLIM' % self.acqname,
                                                    default='0.025'))
        self.exptime_max = float(self.eo_config.get('%s_HILIM' % self.acqname,
                                                    default='600.0'))

    def _get_image_counts(self):
        """
        Get the number of exposures and bias frames to take for each
        acquisition instruction.
        """
        self.imcount = int(self.eo_config.get('%s_IMCOUNT' % self.acqname,
                                              default='1'))
        self.bias_count = int(self.eo_config.get('%s_BCOUNT' % self.acqname,
                                                 default='1'))

    def _set_default_wavelength(self):
        """
        Set the default wavelength for all acquistions.
        """
        self.wl = float(self.eo_config.get('%s_WL' % self.acqname,
                                           default="550.0"))
        self.set_wavelength(self.wl)

    def _set_slitwidth(self, tokens, index):
        slit_width_changed = False
        try:
            width = int(tokens[index])
        except IndexError:
            width = int(self.eo_config.get('DEFAULT_SLITWIDTH', default=240))
        if width != self.current_slitwidth:
            self.set_slitwidth(width, self.slit_id)
            self.current_slitwidth = width
            slit_width_changed = True
        return slit_width_changed

    def set_slitwidth(self, width, slit_id):
        """Set the monochromator slit width."""
        self.sub.mono.synchCommand(10, 'setSlitSize', slit_id, width)

    def set_wavelength(self, wl):
        """
        Set the monochromator wavelength.

        Parameters
        ----------
        wl : float
            The desired wavelength in nm.
        """
        command = "setWaveAndFilter %s" % wl
        rwl = self.sub.mono.synchCommand(60, command)
        self.sub.ts8.synchCommand(10, "setMonoWavelength", rwl)
        return rwl

    def _read_instructions(self, acq_config_file):
        """
        Read the instructions for the current test type from the
        acquisition configuration file.
        """
        self.instructions = []
        with open(acq_config_file) as input_:
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
        The test type, e.g., 'FLAT', 'FE55', 'SFLAT', 'DARK', etc..
        """
        return self.acqname.upper()

    def take_image(self, seqno, exptime, openShutter, actuateXed,
                   image_type, test_type=None, file_template=None,
                   timeout=500, max_tries=3, try_wait=10.):
        """
        Take an image.

        Parameters
        ----------
        seqno : int
            The sequence number to be written into the FITS file name.
        exptime : float
            The exposure time in seconds.
        openShutter : bool
            Flag to indicate that the monochromator shutter should be
            opened for the exposure.
        actuateXed : bool
            Flag to indicate that the XED arms should be deployed so
            that a Fe55 exposure can be taken.
        image_type : str
            The image type for writing to the FITS header and filename.
            It must be one of "FLAT", "FE55", "DARK", "BIAS", "PPUMP".
        test_type : str, optional
            The test type to be written in to the FITS header and filename.
            If None, then the value set in the constructor is used.  This
            override option is needed since the superflat commands in the
            acq config file are labeled by 'SFLAT', whereas the FITS info
            needs to encode the wavelength of exposure, e.g., 'SFLAT_500'.
        file_template : str, optional
            The file template used by the CCS code for writing FITS
            filenames.  FLAT, SFLAT, and QE acquistions require special
            templates; all other acquisitions can use the default.
        timeout : int, optional
            Timeout (in seconds) for the synchronous "exposeAcquireAndSave"
            commmand.  Default: 500.
        max_tries : int, optional
            The number of maximum number of tries for the
            "exposeAcquireAndSave" command.  Default: 3.  If the command
            does not succeed in max_tries, the exception from the CCS code
            is re-raised.
        try_wait : float, optional
            The number of seconds to wait between subsequent tries of
            the "exposeAcquireAndSave" command.  Default: 10.

        Returns
        -------
        Result object from the CCS synchCommand(timeout, "exposeAcquireAndSave")
        execution.
        """
        if test_type is None:
            test_type = self.test_type
        if file_template is None:
            file_template = self._fn_pattern
        self.logger.info("%s: taking image type %s %d", test_type, image_type,
                         seqno)
        self.sub.ts8.synchCommand(10, "setTestType", test_type)
        self.sub.ts8.synchCommand(10, "setImageType", image_type)
        self.sub.ts8.synchCommand(10, "setSeqInfo", seqno)

        self.verify_sequencer_params()
        self.ccd_clear(1)

        command = 'exposeAcquireAndSave %d %s %s "%s"' \
            % (1000*exptime, openShutter, actuateXed, file_template)
        # ensure timeout exceeds exposure time by 20 seconds.
        timeout = int(max(timeout, exptime + 20))
        for itry in range(max_tries):
            try:
                result = self.sub.ts8.synchCommand(timeout, command)
                return result
            except (StandardError, java.lang.Exception) as eobj:
                self.logger.info("EOAcquisition.take_image: try %i failed",
                                 itry)
                self.logger.info(str(eobj))
                time.sleep(try_wait)
        raise RuntimeError("Failed to take an image after %i tries."
                           % max_tries)

    def image_clears(self, nclears=0, exptime=5):
        """
        Take some bias frames to clear the CCDs.

        nclears : int, optional
            The number of bias images to take.  Default: 2.
        exptime : float, optional
            Exposure time in seconds. Default: 5.
        """
        for i in range(nclears):
            try:
                self.take_image(0, exptime, False, False, "biasclear",
                                file_template='')
            except StandardError as eobj:
                self.logger.info("Clear attempt %d failed:\n %s", i, str(eobj))
                time.sleep(1.0)

    def bias_image(self, seqno, max_tries=3):
        """
        Take bias images.
        """
        exptime = 0
        openShutter = False
        actuateXed = False
        self.take_image(seqno, exptime, openShutter, actuateXed, "BIAS",
                        timeout=150, max_tries=max_tries)

    def dark_image(self, seqno, exptime, max_tries=3):
        """
        Take dark image
        """
        openShutter = False
        actuateXed = False
        timeout = int(max(150, exptime + 20))
        self.take_image(seqno, exptime, openShutter, actuateXed, "DARK",
                        timeout=timeout, max_tries=max_tries)

    def measured_flux(self, wl, seqno=0, fluxcal_time=2.):
        """
        Compute the measured flux by taking an exposure at the
        specified wavelength.

        Parameters
        ----------
        wl : float
            The wavelength in nm.
        seqno : int, optional
            The sequence number for the exposure.  Default: 0.
        fluxcal_time : float, optional
            The exposure time in seconds for the flux calibration exposure.
            Default: 2.

        Returns
        -------
        float :
            The flux value in e-/pixel/s.
        """
        self.set_wavelength(wl)
        openShutter = True
        actuateXed = False
        # Take a test image.
        self.take_image(seqno, fluxcal_time, openShutter, actuateXed,
                        "prefluxcalib", file_template='')
        # The calibration image.
        fits_files = self.take_image(seqno, fluxcal_time, openShutter,
                                     actuateXed, "fluxcalib", max_tries=3)
        flux_sum = 0.
        if isinstance(fits_files, int):
            # We must be using a subsystem-proxy the ts8 subsystem.
            # TODO: Find a better way to handle the subsystem-proxy
            # case.
            return 1
        for fits_file in fits_files:
            file_path = glob.glob(os.path.join(self.md.cwd, '*', fits_file))[0]
            command = "getFluxStats %s" % file_path
            flux_sum += \
                float(self.sub.ts8.synchCommand(10, command))
        return flux_sum/len(fits_files)

    def compute_exptime(self, target_counts, meas_flux):
        """
        Compute the exposure time for a specified wavelength and
        target signal level.

        Parameters
        ----------
        target_counts : float
            The desired signal level in e-/pixel.
        meas_flux : float
            The incident flux (at the current wavelength setting) in
            e-/pixel/s.

        Returns
        -------
        float :
            The exposure time in seconds.
        """
        exptime = target_counts/meas_flux
        exptime = min(max(exptime, self.exptime_min), self.exptime_max)
        return exptime


    def get_ccdtype(self):
        """ return ccdtype as a string"""
        res = str(self.sub.ts8.synchCommand(10, "getCcdType"))
        if re.match(r"^e2v$", res):
            return "e2v"
        elif re.match(r"^itl$", res):
            return "itl"
        else:
            self.logger.info("CCD Type unknown, returning None")
            return None

    def verify_sequencer_params(self):
        """ Check that CleaningNumber = 0 and ClearCount = 1
        Otherwise the wrong sequencer is loaded
        """
        #- CleaningNummber = [0, 0, 0]
        res = str(self.sub.ts8.synchCommand(10,
                         "getSequencerParameter", "CleaningNumber"))
        if not re.match(r"\[0, 0, 0\]", res):
            self.logger.info("SeqParam CleaningNumber:%s invalid", res)
            raise java.lang.Exception("Bad Sequencer: CleaningNumber=0 required")
        #- ClearCount = [1, 1, 1]
        res = str(self.sub.ts8.synchCommand(10,
                             "getSequencerParameter", "ClearCount"))
        if not re.match(r"\[1, 1, 1\]", res):
            self.logger.info("SeqParam ClearCount:%s invalid", res)
            raise java.lang.Exception("Bad Sequencer: ClearCount=1 required")

    def ccd_clear(self, nclears):
        """
        clear the ccd
        """
        if nclears < 1:
            return
        #  Perform the Clear main
        #
        self.logger.info("Clearing CCD %s times...", nclears)
        for _ in range(nclears):
            self.sub.ts8.synchCommand(10, "setSequencerStart", "Clear")
            self.sub.ts8.synchCommand(10, "startSequencer")
            self.sub.ts8.synchCommand(10, "waitSequencerDone", 1000)
            self.sub.ts8.synchCommand(10, "setSequencerStart", "Bias")


class PhotodiodeReadout(object):
    """
    Class to handle monitoring photodiode readout.
    """
    def __init__(self, exptime, eo_acq_object, max_reads=2048):
        """
        Parameters
        ----------
        exptime : float
            Exposure time in seconds for the frame to be taken.
        eo_acq_object : EOAcquisition object
            An instance of a subclass of EOAcquisition.
        max_reads : int, optional
            Maximum number of reads of monitoring photodiode.  Default: 2048.
        """
        self.sub = eo_acq_object.sub
        self.md = eo_acq_object.md
        self.logger = eo_acq_object.logger
        self._exptime = exptime
        self._buffertime = 2.0

        # for exposures over 0.5 sec, nominal PD readout at 60Hz,
        # otherwise 240Hz
        if exptime > 0.5:
            nplc = 0.5
        else:
            nplc = 0.25

        self.navg = int(10)

        # add a buffer to duration of PD readout
        nreads = min((exptime + self._buffertime)*60./nplc/self.navg, max_reads)
        self.nreads = int(nreads)

        self.nplc = nplc
        self._pd_result = None
        self._start_time = None

    def start_accumulation(self):
        """
        Start the asynchronous accumulation of photodiode current readings.
        """

        # get Keithley picoAmmeters ready by resetting and clearing buffer
        self.sub.pd.synchCommand(60, "reset")
        self.sub.pd.synchCommand(60, "clrbuff")

        # set Keithely picoAmmeters to be the fixed range mode
        self.sub.pd.synchCommand(60, "setCurrentRange 2e-6")

        #
        if self.navg != 1:
            self.sub.pd.synchCommand(60, "send AVER:COUNT %d" % self.navg)
            self.sub.pd.synchCommand(60, "send AVER:TCON REP")
            self.sub.pd.synchCommand(60, "send AVER ON")
        else:
            self.sub.pd.synchCommand(60, "send AVER OFF")

        # start accummulating current readings
        self.sub.pd.synchCommand(60, "setRate %f" % self.nplc)
        self._pd_result = self.sub.pd.asynchCommand("accumBuffer", self.nreads,
                                                    self.nplc, True)
        self._start_time = time.time()
        self.logger.info("Photodiode readout accumulation started at %f",
                         self._start_time)

        running = False
        while not running:
            try:
                running = self.sub.pd.synchCommand(20, "isAccumInProgress")
            except StandardError as eobj:
                self.logger.info("PhotodiodeReadout.start_accumulation:")
                self.logger.info(str(eobj))
            self.logger.info("Photodiode checking that accumulation started at %f",
                         time.time() - self._start_time)
            time.sleep(0.25)

    def write_readings(self, seqno, icount=1):
        """
        Output the accumulated photodiode readings to a text file.
        """
        # make sure Photodiode readout has had enough time to run
        pd_filename = os.path.join(self.md.cwd,
                                   "pd-values_%d-for-seq-%d-exp-%d.txt"
                                   % (int(self._start_time), seqno, icount))
        self.logger.info("Photodiode about to be readout at %f",
                         time.time() - self._start_time)

        result = self.sub.pd.synchCommand(1000, "readBuffer", pd_filename)
        self.logger.info("Photodiode readout accumulation finished at %f, %s",
                         time.time() - self._start_time, result)

        return pd_filename

    def add_pd_time_history(self, fits_files, pd_filename):
        "Add the photodiode time history as an extension to the FITS files."
        for fits_file in fits_files:
            full_path = glob.glob('%s/*/%s' % (self.md.cwd, fits_file))[0]
            command = "addBinaryTable %s %s AMP0.MEAS_TIMES AMP0_MEAS_TIMES AMP0_A_CURRENT %d" % (pd_filename, full_path, self._start_time)
            self.sub.ts8.synchCommand(200, command)
            self.logger.info("Photodiode readout added to fits file %s",
                             fits_file)

    def get_readings(self, fits_files, seqno, icount):
        """
        Output the accumulated photodiode readings to a text file and
        write that time history to the FITS files as a binary table
        extension.
        """
        pd_filename = self.write_readings(seqno, icount)
        try:
            self.add_pd_time_history(fits_files, pd_filename)
        except TypeError:
            # We must be using a subsystem-proxy for the ts8
            # subsystem.  TODO: Find a better way to handle the
            # subsystem-proxy case.
            pass
