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

import astropy.io.fits as fits

import siteUtils
from datacat.error import DcClientException
from DataCatalog import DataCatalog
import camera_components

# Configure the database interface
ROOT_FOLDER = 'LSST/mirror/SLAC-prod/prod'


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
    return os.path.join(kwargs.get('outpath', '.'),
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


def copy_single_sensor_data(raft, process_name, output_path, **kwargs):

    """ Copy a single input file to the correct output location for
        each sensor in this raft.  Possibly updating FITS header
        infomation along the way.

    Parameters
    ----------
    process_name : str
        The name of the assoicated eTraveler process, used in making
        the output file name
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
        The name of the output eTraveler process, if it differs from
        process_name
    clobber : bool, optional
        Allow overwriting existing files
    dry_run : bool, optional
        If true, just print output file names, but do not copy files
    """
    kwargs = kwargs.copy()
    root_folder = kwargs.pop('root_folder', ROOT_FOLDER)
    kwargs_write = dict(clobber=kwargs.pop('clobber', False),
                        dry_run=kwargs.pop('dry_run', False),
                        process_name_out=kwargs.pop('process_name_out',
                                                    process_name))

    writer = RaftImages(raft.raft_id, process_name, raft.sensor_type,
                        output_path)

    for slot_name, sensor_id in raft.items():
        template_files = get_template_files(root_folder, raft.sensor_type,
                                            sensor_id=sensor_id.replace('_sim', ''),
                                            process_name=process_name, **kwargs)
        for fname in template_files:
            writer.write_sensor_image(fname, slot_name, sensor_id,
                                      **kwargs_write)


if __name__ == '__main__':

    USER = os.environ['USER']
    ETRAV_DB = 'Dev'

    # These are in caps to keep pylint happy
    TESTTYPE = 'FE55'
    IMGTYPE = 'BIAS'
    PROCESS_NAME_IN = 'vendorIngest'
    PROCESS_NAME_OUT = 'fe55_acq'
    PATTERN = '*.fits'
    OUTPATH = '.'
    RAFT_ID = 'LCA-10753-RSA_sim-0000'

    #RAFT = FakeRaft.create_from_yaml("test_raft.yaml")
    RAFT = FakeRaft.create_from_etrav(RAFT_ID, user=USER, db_name=ETRAV_DB)

    RAFT.file_copy(PROCESS_NAME_IN, OUTPATH, root_folder=ROOT_FOLDER, dry_run=True,
                   test_type=TESTTYPE, image_type=IMGTYPE,
                   pattern=PATTERN)
