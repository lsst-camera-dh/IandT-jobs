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

import os
import fnmatch
import yaml

import astropy.io.fits as fits
from datacat.error import DcClientException
from DataCatalog import DataCatalog
# import siteUtils


def make_datacat_path(**kwargs):
    """ Build the data catalog path for a particular test on a particular sensor

    Looking at LSSTTD-690 it appear that with run numbers the best we can do is
    <root_folder>/<sensor_type>/<sensor_id>.
    """
    return os.path.join(kwargs['root_folder'], kwargs['sensor_type'],
                        kwargs['sensor_id'])


def make_outfile_path(**kwargs):
    """ Build the path for an output file for a particular test on a particular sensor

    Looking at LSSTTD-690 for rafts this should be
    <root_folder>/sraft<raft_id>/<process_name>/<job_id>/s<slot_name>/<file_string>
    """
    return os.path.join(kwargs['root_folder'], "sraft%s" % (kwargs['raft_id']),
                        "%04i" % (kwargs['run_id']), kwargs['process_name'],
                        "%04i" % (kwargs['job_id']), "s%s" % (kwargs['slot_name']),
                        kwargs['file_string'])


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
    sort : boolean
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

    try:
        datasets = datacat.find_datasets(query)
    except DcClientException, msg:
        # Make the error message a bit more useful for debbuing
        msg += "Folder = %s\n" % folder
        msg += "Query = %s\n" % query
        raise DcClientException(msg)

    file_list = []
    for item in datasets.full_paths():
        if fnmatch.fnmatch(os.path.basename(item), pattern):
            file_list.append(item)
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
    for key, val in validate:
        try:
            rsp_val = rsp[key]
            if isinstance(val, list):
                if rsp_val not in val:
                    errmsg = "eTraveler response does not match expectation for key %s: " % (key)
                    errmsg += "%s not in %s" % (rsp_val, val)
                    raise KeyError(errmsg)
            else:
                if rsp_val != val:
                    errmsg = "eTraveler response does not match expectation for key %s: " % (key)
                    errmsg += "%s != %s" % (rsp_val, val)
                    raise ValueError(errmsg)
        except:
            raise ValueError("eTraveler response does not include expected key %s" % (key))

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
        Update the image header for one of the readout segments

        Parameters
        ----------
        slot_name : str
            Name of the slot with in the raft
        ext_num:  int
            Number of the HDU extension for this segment
        hdu : fits.Image
            FITS image whose header is being updated
        """
        print ("Placeholder", self.raft_id, slot_name, ext_num, hdu)

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
        run_id : int
            Override the run id (defaults to 1111)
        job_id : int
            Override the job id (defaults to 2222)
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
        basename = "%s%s" % (sensor_id, file_suffix)
        outfilename = make_outfile_path(root_folder=self.output_path,
                                        raft_id=kwargs.get('raft_id', self.raft_id),
                                        run_id=kwargs.get('run_id', 1111),
                                        process_name=kwargs.get('process_name_out',
                                                                self.process_name),
                                        job_id=kwargs.get('job_id', 2222),
                                        slot_name=slot_name,
                                        file_string=basename)
        outdir = os.path.dirname(outfilename)
        print ("  Outfile = %s" % outfilename)
        if dry_run:
            return
        output = fits.open(single_sensor_file)

        self.update_primary_header(slot_name, output[0])

        for ext_num in range(1, 16):
            self.update_image_header(slot_name, ext_num, output[ext_num])

        try:
            os.makedirs(outdir)
        except OSError:
            pass

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
        db_name : str
            Version of the eTraveler to query
        prodServer : ??
        htype : str
            Hardware type, this must match the 'parent_hardware_type' field
            in the eTraveler db.
        noBatched : ???

        Returns
        ----------
        Newly created Raft object
        """
        user = kwargs.get('user', 'echarles')
        db_name = kwargs.get('db_name', '??')
        prod_server = kwargs.get('prod_server', '???')
        htype = kwargs.get('htype', 'RAFT')
        no_batched = kwargs.get('no_batched', False)

        from eTraveler.clientAPI.connection import Connection
        my_conn = Connection(user, db_name, prod_server)
        return Raft.create_from_connection(my_conn, raft_id, htype, no_batched)

    @staticmethod
    def create_from_connection(connection, raft_id, htype, no_batched):
        """ Create a Raft object from query to the eTraveler

        Parameters
        ----------
        connection : 'eTraveler/clientAPI/connection.Connection'
            Object that wraps connection to eTraveler database
        raft_id : str
            Name of the raft, this must match the 'parent_experimentSN' field
            in the eTraveler db.
        htype ; str
            Hardware type, this must match the 'parent_hardwareTypeName' field
            in the eTraveler db.
        no_batched : ???

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
                             child_hardwareTypeName='sensor')

        sensor_type = None
        for rsp_item in rsp:
            if rsp_item['relationshipTypeName'] == 'raft_to_sensor':
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
        pattern : str
            Regular expression specifying which files to get

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
        clobber = kwargs.pop('clobber', True)
        dry_run = kwargs.pop('dry_run', False)
        root_folder = kwargs.pop('root_folder', 'LSST/mirror/BNL-prod/prod')
        process_name_out = kwargs.pop('process_name_out', process_name)

        writer = RaftImages(self.__raft_id, process_name, self.sensor_type, output_path)

        for slot_name, sensor_id in self.items():
            template_files = self.get_template_files(root_folder, process_name,
                                                     slot=slot_name, **kwargs)
            for fname in template_files:
                writer.write_sensor_image(fname, slot_name, sensor_id,
                                          process_name_out=process_name_out,
                                          clobber=clobber, dry_run=dry_run)

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
        return get_template_files(root_folder, self.sensor_type,
                                  sensor_id=self.sensor(slot).sensor_id,
                                  process_name=process_name, **kwargs)


if __name__ == '__main__':

    # These are in caps to keep pylint happy
    OUTPATH = 'output/'
    TESTTYPE = 'FE55'
    IMGTYPE = 'BIAS'
    PROCESS_NAME_IN = 'vendorIngest'
    PROCESS_NAME_OUT = 'fe55_acq'
    PATTERN = '*.fits'
    ROOT_FOLDER = 'LSST/mirror/SLAC-prod/prod'

    RAFT = Raft.create_from_yaml("test_raft.yaml")
    RAFT.file_copy(PROCESS_NAME_IN, OUTPATH, root_folder=ROOT_FOLDER, dry_run=True,
                   test_type=TESTTYPE, image_type=IMGTYPE,
                   pattern=PATTERN)
