"""
Makes a raft's worth of image files based on a user-specified single-sensor
image file, the raft designator, and the sensor type (ITL or E2V, which
probably could be guessable from the single-sensor image).  The test type
probably also needs to be specified (for the file naming)
The data in the nine output images are the same as in the input image.  What
is new is the raft coordinate-related header keywords.  These are derived
from the specification in LCA-13501.
"""

from __future__ import print_function, absolute_import, division

import sys
import os
import fnmatch
import yaml

import astropy.io.fits as fits

import siteUtils
from datacat.error import DcClientException
from DataCatalog import DataCatalog


# Configure the database interface
ROOT_FOLDER = 'LSST/mirror/SLAC-prod/prod'
ETRAV_DB = 'Dev'
USER = os.environ['USER']


def make_datacat_path(**kwargs):
    """ Build the data catalog path for a particular test on a particular sensor
    Looking at LSSTTD-690 it appear that with run numbers the best we can do is
    <root_folder>/<sensor_type>/<sensor_id>.
    """
    return os.path.join(kwargs.get('root_folder', ROOT_FOLDER),
                        kwargs['sensor_type'],
                        kwargs['sensor_id'])


def sort_unique(filelist):
    """ Remove duplicate files from re-running particular scripts
    This just keeps the file with the highest JOB ID
    """
    # Build a dictionary of dictionaries mapping base_id : job_id : filename
    sort_dict = {}
    for filename in filelist:
        fbase = os.path.splitext(os.path.basename(filename))[0]
        job_id = fbase.split('_')[-1]
        fid = fbase.replace('_%s'%job_id, '')
        try:
            sort_dict[fid].update({job_id:filename})
        except KeyError:
            sort_dict[fid] = {job_id:filename}

    # For each dictionary pull out just the filename associated to the latest job_id
    ret_list = []
    for value in sort_dict.values():
        keys2 = value.keys()
        keys2.sort()
        ret_list += [value[keys2[-1]]]

    return ret_list


def make_outfile_path(**kwargs):
    """ Build the path for an output file for a particular test on a particular sensor
    This is only the last part of the path, the job harness will move the files to
    <root_folder>/sraft<raft_id>/<process_name>/<job_id>
    For the last part of the path, we use
    <slot_name>/<file_string>  except that we replace the job_id in file_string with the
    current job_id
    """
    file_string = kwargs['file_string']
    job_id = kwargs['job_id']
    fname, ext = os.path.splitext(file_string)
    tokens = fname.split('_')
    fname = fname.replace("%s"%tokens[-1], "%s"%job_id)
    fname += ext
    return os.path.join(kwargs.get('outpath', OUTPATH),
                        kwargs['slot_name'], fname)


def get_file_suffix(filepath):
    """ Get the last part of the file path, basically everything after the sensor_id.
    e.g., '_mean_bias_25.fits' or '_eotest_results.fits'
    """
    basename = os.path.basename(filepath)
    tokens = basename.split('_')
    retval = ""
    for tok in tokens[1:]:
        retval += '_'
        retval += tok
    return retval


def get_template_files(root_folder, sensor_type, sensor_id, process_name, **kwargs):
    """ Get files that serve as templates for a particular process_type
    Parameters
    ----------
    root_folder : str
        Top level data catalog folder for search
    sensor_type : str
        Type of sensor, e.g., 'E2V-CCD'
    sensor_id : str
        Name of the sensor, e.g., 'E2V-CCD250-104'
    process_name : str
        Name of the eTraveler process, e.g., 'fe55_acq' or 'dark_acq'
    Keyword arguments
    -----------
    image_type : str or None
        Type of images to find
    test_type : str or None
        Type of test to find images for
    pattern : str
        Regular expression specifying which files to get / copy
    site : str
        Specifies data catalog database to access
    sort : bool
        Sort the file names before returning them
    test_version : str
        Version of the test process to search for
    Returns
    ----------
    file_list : list
        List of file names for files that match the process_name and sensor_id
    """
    pattern = kwargs.get('pattern', '*.fits')
    image_type = kwargs.get('image_type', None)
    test_type = kwargs.get('test_type', None)

    try:
        folder = os.environ['LCATR_DATACATALOG_FOLDER']
    except KeyError:
        folder = make_datacat_path(root_folder=root_folder, sensor_type=sensor_type,
                                   sensor_id=sensor_id)

    datacat = DataCatalog(folder=folder, site=kwargs.get('site', 'slac.lca.archive'))
    query = '&&'.join(('LSST_NUM=="%s"' % sensor_id,
                       'ProcessName=="%s"' % process_name))
    if image_type is not None:
        query += '&& IMGTYPE == "%s"' % image_type
    if test_type is not None:
        query += '&& TESTTYPE == "%s"' % test_type

    file_list = []
    try:
        datasets = datacat.find_datasets(query)
    except DcClientException as eobj:
        # Make the error message a bit more useful for debbuging
        msg = eobj.message + (":\nFolder = %s\n" % folder)
        msg += "Query = %s\n" % query
        sys.stderr.write(msg)
        return file_list
        #raise DcClientException(msg)

    for item in datasets.full_paths():
        if fnmatch.fnmatch(os.path.basename(item), pattern):
            file_list.append(item)

    file_list = sort_unique(file_list)
    if kwargs.get('sort', False):
        file_list = sorted(file_list)

    return file_list


def parse_etraveler_response(rsp, validate):
    """ Convert the response from an eTraveler clientAPI query to a key,value pair
    Parameters
    ----------
    rsp : return type from eTraveler.clientAPI.connection.Connection.getHardwareHierarchy
        which is an array of dicts information about the 'children' of a
        particular hardware element.
    validate : dict
        A validation dictionary, which contains the expected values for some parts of
        the rsp.  This is here for sanity checking, for example requiring that the
        parent element matches the input element to the request.
    Returns
    ----------
    slot_name,child_esn:
    slot_name  : str
        A string given to the particular 'slot' for each child
    child_esn : str
        The sensor id of the child, e.g., E2V-CCD250-104
    """
    for key, val in validate.items():
        try:
            rsp_val = rsp[key]
            if isinstance(val, list):
                if rsp_val not in val:
                    errmsg = "eTraveler response does not match expectation for key %s: " % (key)
                    errmsg += "%s not in %s" % (rsp_val, val)
                    raise ValueError(errmsg)
            else:
                if rsp_val != val:
                    errmsg = "eTraveler response does not match expectation for key %s: " % (key)
                    errmsg += "%s != %s" % (rsp_val, val)
                    raise ValueError(errmsg)
        except KeyError:
            raise KeyError("eTraveler response does not include expected key %s" % (key))

    child_esn = rsp['child_experimentSN']
    slot_name = rsp['slotName']
    return slot_name, child_esn


class RaftImages(object):
    '''
    Writes a raft's worth of images based on a user-supplied single-sensor
    image.
    Parameters
    ----------
    raft_id : str
        Name of the raft, e.g., 'RAFT_000'.  This is used to evaluate coordinate
        keywords for focal plane coordinates
    process_name : str
        Name of the 'test' being applied.  This probably could be extracted
        from single_sensor_file.  No analysis is implied; the string is just
        used for assigning names to output files.
    sensor_type: str
        ITL-CCD or E2V-CCD
    output_path : str
        Path to prepended to the output file names
    Attributes
    ----------
    ccd_image : astropy.io.fits.HDUList
        This is an Astropy HDUList that contains all the headers and image
        extensions of the single_sensor_file
    '''

    def __init__(self, raft_id, process_name, sensor_type, output_path):
        """
        Class constructor.
        """
        self.raft_id = raft_id
        self.process_name = process_name
        self.sensor_type = sensor_type
        self.output_path = output_path
        try:
            os.mkdir(self.output_path)
        except OSError:
            pass

    def update_primary_header(self, slot_name, hdu):
        """
        Update the primary image header
        Parameters
        ----------
        slot_name : str
            Name of the slot with in the raft
        hdu : fits.Image
            FITS image whose header is being updated
        """
        print ("Placeholder", self.raft_id, slot_name, hdu)

    def update_image_header(self, slot_name, ext_num, hdu):
        """
        Update the image header for one of the readout segments.  Adds raft-level
        coordinates (one set in Camera coordinates and one set rotated so the CCD
        orientation has serial direction horizontal).  Adds rotated CCD coordinates
        as well.  (Also rewrites amplifier and CCD-level Mosaic keywords.)
        See LCA-13501
        Parameters
        ----------
        slot_name : str
            Name of the slot within the raft
        ext_num:  int
            Number of the HDU extension for this segment
        hdu : fits.Image
            FITS image whose header is being updated
        """
        # The coordinate keyword values depend on the type of CCD.
        # Kind of awkward, but below the CCD type is identified by the assumed
        # values of DETSIZE for each type.  The image extension headers do not
        # include the sensor type explicitly

        hdu.header['SLOT'] = slot_name

        if hdu.header['DETSIZE'] == '[1:4096,1:4004]':
            # pixel parameters for e2v sensors
            dimv = 2002
            dimh = 512
            ccdax = 4004
            ccday = 4096
            ccdpx = 4197
            ccdpy = 4200
            gap_inx = 28
            gap_iny = 25
            gap_outx = 26.5
            gap_outy = 25
            preh = 10
        elif hdu.header['DETSIZE'] == '[1:4072,1:4000]':
            # pixel parameters for ITL sensors
            dimv = 2000
            dimh = 509
            ccdax = 4000
            ccday = 4072
            ccdpx = 4198
            ccdpy = 4198
            gap_inx = 27
            gap_iny = 27
            gap_outx = 26.0
            gap_outy = 26
            preh = 3
        else:
            raise RuntimeError("Sensor DETSIZE not recognized")

        # get the segment 'coordinates' from the extension name
        extname = hdu.header['EXTNAME']
        sx = int(extname[-2:-1])
        sy = int(extname[-1:])

        # For convenience of notation in LCA-13501 these are also defined as 'serial'
        # and 'parallel' indices, with Segment = Sp*10 + Ss
        sp = sx
        ss = sy

        # Extract the x and y location indexes in the raft from the slot name. Also
        # define the serial and parallel versions
        cx = int(slot_name[1:2])
        cy = int(slot_name[2:3])
        cp = cx
        cs = cy

        # Define the WCS and Mosaic keywords
        wcsnamea = 'AMPLIFIER'
        ctype1a = 'Seg_X   '
        ctype2a = 'Seg_Y   '
        wcsnamec = 'CCD     '
        ctype1c = 'CCD_X   '
        ctype2c = 'CCD_Y   '
        wcsnamer = 'RAFT    '
        ctype1r = 'RAFT_X  '
        ctype2r = 'RAFT_Y  '
        wcsnamef = 'FOCAL_PLANE'
        wcsnameb = 'CCD_SERPAR'
        ctype1b = 'CCD_S   '
        ctype2b = 'CCD_P   '
        wcsnameq = 'RAFT_SERPAR'
        ctype1q = 'RAFT_S  '
        ctype2q = 'RAFT_P  '

        if hdu.header['DETSIZE'] == '[1:4072,1:4000]':
            # header coordinate parameters for ITL sensors
            pc1_1a = 0
            pc1_2a = 1 - 2*sx
            pc2_1a = -1
            pc2_2a = 0
            crpix1a = 0
            crpix2a = 0
            crval1a = sx*(dimv + 1)
            crval2a = dimh + 1 - preh
            pc1_1c = 0
            pc1_2c = 1 - 2*sx
            pc2_1c = -1
            pc2_2c = 0
            crpix1c = 0
            crpix2c = 0
            crval1c = sx*(2*dimv + 1)
            crval2c = dimh + 1 + sy*dimh - preh
            pc1_1r = 0
            pc1_2r = 1 - 2*sx
            pc2_1r = -1
            pc2_2r = 0
            crpix1r = 0
            crpix2r = 0
            crval1r = (sx*(2*dimv + 1) + gap_outx + (ccdpx - ccdax)/2.
                       + cx*(2*dimv + gap_inx + ccdpx - ccdax))
            crval2r = (dimh + 1 + sy*dimh + gap_outy + (ccdpy - ccday)/2.
                       + cy*(8*dimh + gap_iny + ccdpy - ccday) - preh)
            pc1_1b = -1
            pc1_2b = 0
            pc2_1b = 0
            pc2_2b = 1 - 2*sp
            cdelt1b = 1
            cdelt2b = 1
            crpix1b = 0
            crpix2b = 0
            crval1b = (ss + 1)*dimh + 1 - preh
            crval2b = sp*(2*dimv + 1)
            pc1_1q = -1
            pc1_2q = 0
            pc2_1q = 0
            pc2_2q = 1 - 2*sp
            cdelt1q = 1
            cdelt2q = 1
            crpix1q = 0
            crpix2q = 0
            crval1q = (gap_outy + (ccdpy - ccday)/2. + cs*(8*dimh + gap_iny
                       + ccdpy - ccday) + (ss + 1)*dimh + 1 - preh)
            crval2q = (sp*(2*dimv + 1) + gap_outx + (ccdpx - ccdax)/2.
                       + cp*(2*dimv+gap_inx + ccdpx - ccdax))
            dtm1_1 = -1
            dtm1_2 = 0
            dtm2_1 = 0
            dtm2_2 = 2*sx - 1
            dtv1 = (dimh + 1) + sy*dimh + preh
            dtv2 = (2*dimv + 1)*(1 - sx)
        elif hdu.header['DETSIZE'] == '[1:4096,1:4004]':
            # header coordinate parameters for e2v sensors
            pc1_1a = 0
            pc1_2a = 1 - 2*sx
            pc2_1a = 1 - 2*sx
            pc2_2a = 0
            crpix1a = 0
            crpix2a = 0
            crval1a = sx*(dimv + 1)
            crval2a = sx*(dimh + 1) + (2*sx - 1)*preh
            pc1_1c = 0
            pc1_2c = 1 - 2*sx
            pc2_1c = 1 - 2*sx
            pc2_2c = 0
            crpix1c = 0
            crpix2c = 0
            crval1c = sx*(2*dimv+1)
            crval2c = sx*(dimh+1) + sy*dimh + (2*sx - 1)*preh
            pc1_1r = 0
            pc1_2r = 1 - 2*sx
            pc2_1r = 1 - 2*sx
            pc2_2r = 0
            cdelt1r = 1
            cdelt2r = 1
            crpix1r = 0
            crpix2r = 0
            crval1r = (sx*(2*dimv + 1) + gap_outx + (ccdpx - ccdax)/2.
                       + cx*(2*dimv + gap_inx + ccdpx - ccdax))
            crval2r = (sx*(dimh + 1) + sy*dimh + gap_outy
                       * (ccdpy - ccday)/2. + cy*(8*dimh + gap_iny + ccdpy
                       - ccday) + (2*sx - 1)*preh)
            pc1_1b = 1 - 2*sp
            pc1_2b = 0
            pc2_1b = 0
            pc2_2b = 1 - 2*sp
            cdelt1b = 1
            cdelt2b = 1
            crpix1b = 0
            crpix2b = 0
            crval1b = sp*(dimh + 1) + ss*dimh + (2*sp-1)*preh
            crval2b = sp*(2*dimv+1)
            pc1_1q = 1 - 2*sp
            pc1_2q = 0
            pc2_1q = 0
            pc2_2q = 1 - 2*sp
            cdelt1q = 1
            cdelt2q = 1
            crpix1q = 0
            crpix2q = 0
            crval1q = (gap_outy + (ccdpy - ccday)/2. + cs*(8*dimh + gap_iny
                       + ccdpy - ccday) + sp*(dimh + 1) + ss*dimh)
            crval2q = (sp*(2*dimv + 1) + gap_outx + (ccdpx - ccdax)/2.
                       + cp*(2*dimv + gap_inx + ccdpx - ccdax))
            dtm1_1 = 1 - 2*sx
            dtm1_2 = 0
            dtm2_1 = 0
            dtm2_2 = 2*sx - 1
            dtv1 = (dimh+1 + 2*preh)*sx + sy*dimh - preh
            dtv2 = (2*dimv + 1)*(1 - sx)
        else:
            raise RuntimeError("Sensor DETSIZE not recognized")

        hdu.header['DTM1_1'] = dtm1_1
        hdu.header['DTM1_2'] = dtm1_2
        hdu.header['DTM2_1'] = dtm2_1
        hdu.header['DTM2_2'] = dtm2_2
        hdu.header['DTV1'] = dtv1
        hdu.header['DTV2'] = dtv2

        hdu.header['WCSNAMEA'] = wcsnamea
        hdu.header['CTYPE1A'] = ctype1a
        hdu.header['CTYPE2A'] = ctype2a
        hdu.header['CRVAL1A'] = crval1a
        hdu.header['CRVAL2A'] = crval2a
        hdu.header['PC1_1A'] = pc1_1a
        hdu.header['PC1_2A'] = pc1_2a
        hdu.header['PC2_1A'] = pc2_1a
        hdu.header['PC2_2A'] = pc2_2a
        hdu.header['CDELT1A'] = 1
        hdu.header['CDELT2A'] = 1
        hdu.header['CRPIX1A'] = crpix1a
        hdu.header['CRPIX2A'] = crpix2a
        hdu.header['WCSNAMEC'] = wcsnamec
        hdu.header['CTYPE1C'] = ctype1c
        hdu.header['CTYPE2C'] = ctype2c
        hdu.header['CRVAL1C'] = crval1c
        hdu.header['CRVAL2C'] = crval2c
        hdu.header['PC1_1C'] = pc1_1c
        hdu.header['PC1_2C'] = pc1_2c
        hdu.header['PC2_1C'] = pc2_1c
        hdu.header['PC2_2C'] = pc2_2c
        hdu.header['CDELT1C'] = 1
        hdu.header['CDELT2C'] = 1
        hdu.header['CRPIX1C'] = crpix1c
        hdu.header['CRPIX2C'] = crpix2c
        hdu.header['WCSNAMER'] = wcsnamer
        hdu.header['CTYPE1R'] = ctype1r
        hdu.header['CTYPE2R'] = ctype2r
        hdu.header['CRVAL1R'] = crval1r
        hdu.header['CRVAL2R'] = crval2r
        hdu.header['PC1_1R'] = pc1_1r
        hdu.header['PC1_2R'] = pc1_2r
        hdu.header['PC2_1R'] = pc2_1r
        hdu.header['PC2_2R'] = pc2_2r
        hdu.header['CDELT1R'] = cdelt1r
        hdu.header['CDELT2R'] = cdelt2r
        hdu.header['CRPIX1R'] = crpix1r
        hdu.header['CRPIX2R'] = crpix2r
        hdu.header['WCSNAMEF'] = wcsnamef
        hdu.header['WCSNAMEB'] = wcsnameb
        hdu.header['CTYPE1B'] = ctype1b
        hdu.header['CTYPE2B'] = ctype2b
        hdu.header['CRVAL1B'] = crval1b
        hdu.header['CRVAL2B'] = crval2b
        hdu.header['PC1_1B'] = pc1_1b
        hdu.header['PC1_2B'] = pc1_2b
        hdu.header['PC2_1B'] = pc2_1b
        hdu.header['PC2_2B'] = pc2_2b
        hdu.header['CDELT1B'] = cdelt1b
        hdu.header['CDELT2B'] = cdelt2b
        hdu.header['CRPIX1B'] = crpix1b
        hdu.header['CRPIX2B'] = crpix2b
        hdu.header['WCSNAMEQ'] = wcsnameq
        hdu.header['CTYPE1Q'] = ctype1q
        hdu.header['CTYPE2Q'] = ctype2q
        hdu.header['CRVAL1Q'] = crval1q
        hdu.header['CRVAL2Q'] = crval2q
        hdu.header['PC1_1Q'] = pc1_1q
        hdu.header['PC1_2Q'] = pc1_2q
        hdu.header['PC2_1Q'] = pc2_1q
        hdu.header['PC2_2Q'] = pc2_2q
        hdu.header['CDELT1Q'] = cdelt1q
        hdu.header['CDELT2Q'] = cdelt2q
        hdu.header['CRPIX1Q'] = crpix1q
        hdu.header['CRPIX2Q'] = crpix2q

    def write_sensor_image(self, single_sensor_file, slot_name, sensor_id, **kwargs):
        """
        Write a FITS image with pixel coordinates matching the specified
        sensor_id and raft_id.  The output file name is constructed from
        the test type, sensor type, sensor_id and raft_id.
        Parameters
        ----------
        single_sensor_file : str
            Name of the file to be copied
        slot_name:  str
            Name of the slot this sensor occupies
        sensor_id:  str
            Name of the sensor, e.g., 'E2V-CCD250-104'
        Keyword arguments
        -----------
        raft_id : str
            Override the raft id
        process_name_out : str
            The name of the output eTraveler process, if it differs from process_name
        clobber : bool, optional
            Flag indicating whether to overwrite an existing output file
        dry_run : bool, optional
            If true, just print output file names, but do not copy files
        """
        file_suffix = get_file_suffix(single_sensor_file)

        clobber = kwargs.get('clobber', True)
        dry_run = kwargs.get('dry_run', False)
        job_id = kwargs.get('job_id', siteUtils.getJobName())
        basename = "%s%s" % (sensor_id, file_suffix)
        outfilename = make_outfile_path(outpath=self.output_path,
                                        slot_name=slot_name,
                                        file_string=basename,
                                        job_id=job_id)
        outdir = os.path.dirname(outfilename)
        try:
            os.makedirs(outdir)
        except OSError:
            pass

        print ("  Outfile = %s" % outfilename)
        if dry_run:
            os.system("touch %s"% outfilename)
            return
        output = fits.open(single_sensor_file)

        self.update_primary_header(slot_name, output[0])

        for ext_num in range(1, 16):
            self.update_image_header(slot_name, ext_num, output[ext_num])


        output.writeto(outfilename, clobber=clobber)
        output.close()


class Sensor(object):
    '''
    A simple class to carry around some information about sensors in a raft.
    Parameters
    ----------
    sensor_id : str
        Name of the sensor, e.g., 'E2V-CCD250-104'
    raft_id : str
        Name of the associated raft
    '''
    def __init__(self, sensor_id, raft_id):
        """
        Class constructor.
        """
        self.__sensor_id = sensor_id
        self.__raft_id = raft_id

    @property
    def sensor_id(self):
        """ Return the name of the sensor, e.g., 'E2V-CCD250-104' """
        return self.__sensor_id

    @property
    def raft_id(self):
        """ Return the Name of the sensor, e.g., 'RAFT-000' """
        return self.__raft_id


class Raft(object):
    '''
    A simple class to carry around some information about a raft.
    Parameters
    ----------
    raft_id : str
        Name of the raft
    sensor_type : str
        Type of sensors in the raft, either 'e2v-CCD' or 'ITL-CCD'
    sensor_dict : dict
        Dictionary for slot to Sensor
    '''
    def __init__(self, raft_id, sensor_type, sensor_dict):
        """
        Class constructor.
        """
        self.__raft_id = raft_id
        self.__sensor_type = sensor_type
        self.__sensor_dict = sensor_dict

    @staticmethod
    def create_from_yaml(yamlfile):
        """ Create a Raft object from a yaml file """
        input_dict = yaml.safe_load(open(yamlfile))
        raft_id = input_dict['raft_id']
        sensor_type = input_dict['sensor_type']
        sensors = input_dict['sensors']
        sensor_dict = {}
        for slot_name, sensor_name in sensors.items():
            sensor_dict[slot_name] = Sensor(sensor_name, raft_id)
        return Raft(raft_id, sensor_type, sensor_dict)

    @staticmethod
    def create_from_etrav(raft_id, **kwargs):
        """ Create a Raft object from query to the eTraveler
        Parameters
        ----------
        raft_id : str
            Name of the raft, this must match the 'parent_experimentSN' field
            in the eTraveler db.
        Keyword Arguments
        ----------
        user   : str
            Expected by the eTraveler interface
        db_name : str ['Dev']
            Version of the eTraveler to query
        prodServer : bool [True]
        htype : str ['LCA-10753-RSA_sim']
            Hardware type, this must match the 'parent_hardware_type' field
            in the eTraveler db.
        noBatched : str ['false']
        Returns
        ----------
        Newly created Raft object
        """
        user = kwargs.get('user', USER)
        db_name = kwargs.get('db_name', ETRAV_DB)
        prod_server = kwargs.get('prod_server', True)
        htype = kwargs.get('htype', siteUtils.getUnitType())
        no_batched = kwargs.get('no_batched', 'false')

        from eTraveler.clientAPI.connection import Connection
        my_conn = Connection(user, db_name, prod_server)
        return Raft.create_from_connection(my_conn, raft_id, htype, no_batched)

    @staticmethod
    def create_from_connection(connection, raft_id, htype,
                               no_batched='false'):
        """ Create a Raft object from query to the eTraveler
        Parameters
        ----------
        connection : 'eTraveler/clientAPI/connection.Connection'
            Object that wraps connection to eTraveler database
        raft_id : str
            Name of the raft, this must match the 'parent_experimentSN' field
            in the eTraveler db.
        htype : str
            Hardware type, this must match the 'parent_hardwareTypeName' field
            in the eTraveler db.
        no_batched : str ['false']
        Returns
        ----------
        Newly created Raft
        """
        rsp = connection.getHardwareHierarchy(experimentSN=raft_id,
                                              htype=htype,
                                              noBatched=no_batched)
        sensor_dict = {}

        validate_dict = dict(parent_hardwareTypeName=htype,
                             parent_experimentSN=raft_id,
                             child_hardwareTypeName=['e2v-CCD', 'ITL-CCD'])

        sensor_type = None

        rel_types = ['RSA_contains_E2V-CCD_sim',
                     'RSA_contains_ITL-CCD_sim']

        for rsp_item in rsp:
            if rsp_item['relationshipTypeName'] in rel_types:
                slot, c_esn = parse_etraveler_response(rsp_item, validate_dict)
                sensor_dict[slot] = Sensor(c_esn, raft_id)
                # For science rafts at least all the sensors in a raft are of the same type
                # So we can just latch the type from the first sensor
                if sensor_type is None:
                    sensor_type = rsp_item['child_hardwareTypeName']

        return Raft(raft_id, sensor_type, sensor_dict)

    @property
    def raft_id(self):
        """ The name of this raft """
        return self.__raft_id

    @property
    def sensor_type(self):
        """ The type of sensors in this raft.  'e2v-CCD' or 'ITL-CCD' """
        return self.__sensor_type

    @property
    def slot_names(self):
        """ The names of the 'slots' associated with the sensors """
        slots = self.__sensor_dict.keys()
        slots.sort()
        return slots

    @property
    def sensor_names(self):
        """ The names of the sensors in this raft, sorted to match the slot names """
        return [self.__sensor_dict[slot].sensor_id for slot in self.slot_names]

    def items(self):
        """ Iterator over slot_name, sensor_name pairs """
        return zip(self.slot_names, self.sensor_names)

    def sensor(self, slot):
        """ Sensor associated with a particular slot """
        return self.__sensor_dict[slot]

    def file_copy(self, process_name, output_path, **kwargs):
        """ Copy a single input file to the correct output location for each sensor in this raft.
            Possibly updating FITS header infomation along the way.
        Parameters
        ----------
        process_name : str
            The name of the assoicated eTraveler process, used in making the output file name
        output_path : str
            The prefix for the output file paths
        Keyword Arguments
        ----------
        test_type : str, optional
            Test type to copy files for
        image_type : str, optional
            Types of images copy
        pattern : str, optional
            Regular expression specifying which files to copy
        site : str
            Specifies data catalog database to access
        test_version : str
            Version of the test process to search for
        root_folder : str, defaults to 'LSST/mirror/BNL-prod/prod
            Allow overriding the top-level folder for the template file search
        process_name_out : str
            The name of the output eTraveler process, if it differs from process_name
        clobber : bool, optional
            Allow overwriting existing files
        dry_run : bool, optional
            If true, just print output file names, but do not copy files
        """
        kwargs = kwargs.copy()
        root_folder = kwargs.pop('root_folder', ROOT_FOLDER)
        kwargs_write = dict(clobber=kwargs.pop('clobber', False),
                            dry_run=kwargs.pop('dry_run', False),
                            process_name_out=kwargs.pop('process_name_out', process_name))

        writer = RaftImages(self.__raft_id, process_name, self.sensor_type, output_path)

        for slot_name, sensor_id in self.items():
            template_files = self.get_template_files(root_folder, process_name,
                                                     slot=slot_name, **kwargs)
            for fname in template_files:
                writer.write_sensor_image(fname, slot_name, sensor_id, **kwargs_write)


    def get_template_files(self, root_folder, process_name, slot, **kwargs):
        """ Get examples of the input files associated to a particular process.
        Parameters
        ----------
        root_folder : str
            Top level data catalog folder for search
        process_name : str
            The name of the assoicated eTraveler process,
            used in making the output file name
        slot : str
            Use the sensor associated with this slot as the template
        image_type : str
            Types of images to copy
        Keyword arguments
        -----------
        test_type : str, optional
            Type of test to find images for
        image_type : str, optional
            Type of images to find
        pattern : str, optional
            Regular expression specifying which files to get
        site : str
            Specifies data catalog database to access
        sort : boolean
            Sort the file names before returning them
        test_version : str
            Version of the test process to search for
        Returns
        ----------
        file_list : list
            List of file names for files that match the process_name, sensor_id and pattern
        """
        sensor_id = self.sensor(slot).sensor_id.replace('_sim', '')
        return get_template_files(root_folder, self.sensor_type,
                                  sensor_id=sensor_id,
                                  process_name=process_name, **kwargs)


if __name__ == '__main__':

    # These are in caps to keep pylint happy
    TESTTYPE = 'FE55'
    IMGTYPE = 'BIAS'
    PROCESS_NAME_IN = 'vendorIngest'
    PROCESS_NAME_OUT = 'fe55_acq'
    PATTERN = '*.fits'
    OUTPATH = '.'
    RAFT_ID = 'LCA-10753-RSA_sim-0000'

    #RAFT = Raft.create_from_yaml("test_raft.yaml")
    RAFT = Raft.create_from_etrav(RAFT_ID, user=USER, db_name=ETRAV_DB)

    RAFT.file_copy(PROCESS_NAME_IN, OUTPATH, root_folder=ROOT_FOLDER, dry_run=True,
                   test_type=TESTTYPE, image_type=IMGTYPE,
                   pattern=PATTERN)
