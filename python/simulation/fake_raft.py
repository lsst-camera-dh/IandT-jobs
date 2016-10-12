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
#import os
#import copy
import numpy as np
import astropy.io.fits as fits
import os
import yaml

import fnmatch
import lcatr.schema
from DataCatalog import DataCatalog

import siteUtils


def sensor_type_from_id(sensor_id):
    """  Get the sensor type ( e2v-CCD or ITL-CCD ) from the sensor_id string
    """
    stype =  sensor_id[0:7]
    if stype == 'E2V-CCD':
        stype = 'e2v-CCD'
    return stype


def make_datacat_path(root_folder,sensor_id,process_name,test_version="v0"):
    """ Build the data catalog path for a particular test on a particular sensor

    This appear to be <root_folder>/<sensor_type>/<sensor_id>/<process_name>/<test_version>
    where <sensor_type> is 'e2v-CCD' or 'ITL-CCD' and is derived from <sensor_id>
    """
    sensor_type = sensor_type_from_id(sensor_id)
    return os.path.join(root_folder,sensor_type,sensor_id,process_name,test_version)


def make_outfile_path(root_folder,raft_id,sensor_id,process_name,file_string,test_version="v0"):
    """ Build the path for an output file for a particular test on a particular sensor

    For now this is <root_folder>/<raft_id>/<sensor_type>/<sensor_id>/<process_name>/<test_version>/<file_string>
    where <sensor_type> is 'e2v-CCD' or 'ITL-CCD' and is derived from <sensor_id>    
    """
    sensor_type = sensor_type_from_id(sensor_id)
    return os.path.join(root_folder,raft_id,sensor_id,process_name,test_version,file_string)


def get_file_suffix(filepath):
    """ Get the last part of the file path, basically everything after the sensor_id.
        e.g., '_mean_bias_25.fits' or '_eotest_results.fits'
    """
    basename = os.path.basename(filepath)
    tokens = basename.split('_')
    s = ""
    for t in tokens[1:]:
        s += '_'
        s += t
    return s


def get_template_files(sensor_id, process_name, pattern, 
                       root_folder='LSST/mirror/SLAC-prod/prod',
                       site='slac.lca.archive', sort=False,
                       test_version="v0",
                       description='Analysis files'):
    """ Get files that serve as templates for a particular process_type 

    Parameters
    ----------
    sensor_id : str
        Name of the sensor, e.g., 'E2V-CCD250-104'
    
    process_name : str
        Name of the eTraveler process, e.g., 'fe55_offline' or 'dark_defects_offline'

    pattern : str
        Regular expression specifying which files to get / copy

    root_folder : str
        Top level data catalog folder for search

    site : str
        Specifies data catalog database to access
  
    sort : boolean
        Sort the file names before returning them

    test_version : str
        Version of the test process to search for 
    
    description : str
        Basically a dummy variable needed for data catalog query

    Returns
    ----------
    file_list : list
        List of file names for files that match the process_name and sensor_id     
    """

    # I'm not sure we really want this, it could easily mess things up
    try:
        folder = os.environ['LCATR_DATACATALOG_FOLDER']
    except KeyError:
        folder = make_datacat_path(root_folder,sensor_id,process_name,test_version)

    dc = DataCatalog(folder=folder, site=site)
    # Since we went to some trouble to specify the folder, we don't really need to make
    # the query all that specifc
    query = '&&'.join(('LSST_NUM=="%(sensor_id)s"',))
    query = query % locals()

    datasets = dc.find_datasets(query)
    file_list = []
    for item in datasets.full_paths():
        if fnmatch.fnmatch(os.path.basename(item), pattern):
            file_list.append(item)
    if sort:
        file_list = sorted(file_list)
    return file_list



def parse_eTraveler_response_raft_to_sensor(rsp,validate):
    """ Convert the response from an eTraveler clientAPI query to a key,value pair

    Parameters
    ----------
    rsp : return type from eTraveler.clientAPI.connection.Connection.getHardwareHierarchy 
          which is an array of dicts information about the 'children' of a particular hardware element

    validate : dict
          A validation dictionary, which contains the expected values for some parts of the rsp
          This is here for sanity checking, for example requiring that the parent element matches
          the input element to the request
          
    Returns
    ----------
    slot_name,child_esn : 
      slot_name  : str
          A string given to the particular 'slot' for each child

      child_esn : str
          The sensor id of the child, e.g., E2V-CCD250-104
    """
    for k,v in validate:
        try:            
            rsp_val = rsp[k]
            if isinstance(v,list):
                if rsp_val not in v:
                    print ("eTraveler response does not match expectation for key %s: %s not in %s"%(k,rsp_val,v))
                    return None
            else:
                if rsp_val != v:
                    print ("eTraveler response does not match expectation for key %s: %s != %s"%(k,rsp_val,v))
                    return None
        except:
            print ("eTraveler response does not include expected key %s"%(k))
            return None

    child_esn = rsp['child_experimentSN']
    slot_name = rsp['slotName']
    return slot_name,child_esn


class RaftImages(object):
    '''
    Writes a raft's worth of images based on a user-supplied single-sensor
    image.

    Parameters
    ----------
    raft_id : str
        Name of the raft, e.g., 'R22'.  This is used to evaluate coordinate
        keywords for focal plane coordinates
    process_name : str
        Name of the 'test' being applied.  This probably could be extracted
        from single_sensor_file.  No analysis is implied; the string is just
        used for assigning names to output files.
    sensor_type: str
        ITL or E2V
    output_path : str
        Path to prepended to the output file names

    Attributes
    ----------
    ccd_image : astropy.io.fits.HDUList
        This is an Astropy HDUList that contains all the headers and image
        extensions of the single_sensor_file
    '''

    def __init__(self, raft_id, process_name, sensor_type,
                 output_path):
        """
        Class constructor.
        """
        self.raft_id = raft_id
        self.process_name = process_name
        self.sensor_type = sensor_type
        self.output_path = output_path
        try:
            os.mkdir(self.output_path)
        except Exception,msg:
            #print (msg)
            pass


    def write_sensor_image(self, single_sensor_file, sensor_id, raft_id=None, clobber=True, dry_run=False):
        """
        Write a FITS image with pixel coordinates matching the specified
        sensor_id and raft_id.  The output file name is constructed from
        the test type, sensor type, sensor_id and raft_id.

        Parameters
        ----------
        single_sensor_file : str
            Name of the file to be copied
        sensor_id:  str
            Name of the sensor, e.g., 'E2V-CCD250-104' 
        clobber : bool, optional
            Flag indicating whether to overwrite an existing output file
        dry_run : bool, optional
            If true, just print output file names, but do not copy files
        """
        file_suffix = get_file_suffix(single_sensor_file)

        out_raft = raft_id
        if out_raft is None:
            out_raft = self.raft_id

        basename = "%s%s"%(sensor_id,file_suffix)
        outfilename = make_outfile_path(self.output_path,out_raft,sensor_id,self.process_name,basename)
        outdir = os.path.dirname(outfilename)
        print ("  Outfile = %s"%outfilename)
        if dry_run:
            return
        output = fits.open(single_sensor_file) 

        # FIXME, update the primary header keywords as needed

        for ext in range(1,16):
            # FIXME, Set the pixel coordinate keywords in each extension header
            pass

        try:
            os.makedirs(outdir)
        except Exception,msg:
            pass
            #print (msg)
                                          
        output.writeto(outfilename,clobber=clobber)
        output.close()





class Sensor:
    '''
    A simple class to carry around some information about sensors in a raft.

    Parameters
    ----------
    sensor_id : str
       Name of the sensor, e.g., 'E2V-CCD250-104
    
    raft_id : str
       Name of the associated raft
    '''
    def __init__(self,sensor_id,raft_id):
        """
        Class constructor.
        """
        self.__sensor_id = sensor_id
        self.__raft_id = raft_id

    @property
    def sensor_id(self):
        return self.__sensor_id

    @property 
    def raft_id(self):
        return self.__raft_id



class Raft:
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
    def __init__(self,raft_id,sensor_type,sensor_dict):
        """
        Class constructor.
        """
        self.__raft_id = raft_id
        self.__sensor_type = sensor_type
        self.__sensor_dict = sensor_dict

    @staticmethod
    def create_from_yaml(yamlfile):
        """ Create a Raft object from a yaml file """
        d = yaml.safe_load(open(yamlfile))
        raft_id = d['raft_id']
        sensor_type = d['sensor_type']
        sensors = d['sensors']
        sensor_dict = {}
        for k,v in sensors.items():
            sensor_dict[k] = Sensor(v,raft_id)
        return Raft(raft_id,sensor_type,sensor_dict)

    @staticmethod
    def create_from_eTraveler(user,db,prodServer,raft_id,htype,noBatched):
        """ Create a Raft object from query to the eTraveler

        Parameters
        ----------
        user   : str
                 Expected by the eTraveler interface

        db    : str
                Version of the eTraveler to query

        prodServer : ??

        raft_id : str
                  Name of the raft, this must match the 'parent_experimentSN' field in the eTraveler db.

        htype ; str
                  Hardware type, this must match the 'parent_hardware_type' field in the eTraveler db.

        noBatched : ???

        Returns
        ----------
        Newly created Raft object
        """
        from eTraveler.clientAPI.connection import Connection
        myConn = Connection(user,db,prodServer)
        return Raft.create_from_connection(myConn,raft_id,htype,noBatched)

    @staticmethod
    def create_from_connection(connection,raft_id,htype,noBatched):
        """ Create a Raft object from query to the eTraveler
        
        Parameters
        ----------
        connection : 'eTraveler/clientAPI/connection.Connection' 
             Object that wraps connection to eTraveler database
                 
        raft_id : str
                  Name of the raft, this must match the 'parent_experimentSN' field in the eTraveler db.

        htype ; str
                  Hardware type, this must match the 'parent_hardwareTypeName' field in the eTraveler db.

        noBatched : ???

        Returns
        ----------
        Newly created Raft
        """
        try:
            rsp = connection.getHardwareHierarchy(experimentSN=experimentSN,
                                                  htype=htype,
                                                  noBatched=noBatched);
        except Exception,msg:
            print ('Operation failed with exception: ')
            print (msg)
            return None


        sensor_dict = {}

        validate_dict = dict(parent_hardwareTypeName=htype,
                             parent_experimentSN=raft_id,
                             child_hardwareTypeName='sensor')

        for rsp_item in rsp:
            if rsp_item['relationshipTypeName'] != 'raft_to_sensor':
                print (rsp_item)
                continue
            slot,c_esn = parse_eTraveler_response(rsp_item)
            sensor_dict[slot] = Sensor(c_esn,raft_name)
        
        return Raft(raft_id,sensor_dict)

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
        sl = self.__sensor_dict.keys()
        sl.sort()
        return sl


    @property
    def sensor_names(self):
        """ The names of the sensors in this raft, sorted to match the slot names """
        sl = self.slot_names
        rl = [ self.__sensor_dict[s].sensor_id for s in sl]
        return rl

    def items(self):
        """ Iterator over slot_name, sensor_name pairs """
        sl = self.slot_names
        sn = self.sensor_names
        return zip(sl,sn)

    def sensor(self,slot):
        """ Sensor associated with a particular slot """
        return self.__sensor_dict[slot]

    def file_copy(self,process_name,
                  output_path,pattern='*.fits',
                  clobber=True,dry_run=False):
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

        clobber : bool, optional
                  Allow overwriting existing files

        dry_run : bool, optional
            If true, just print output file names, but do not copy files
         """        
        writer = RaftImages(self.__raft_id,process_name,self.sensor_type,output_path)

        for k,v in self.items():
            template_files = self.get_template_files(process_name,pattern,slot=k)
            for f in template_files:
                writer.write_sensor_image(f,v,clobber=clobber,dry_run=dry_run)
            
            
    def get_template_files(self,process_name,pattern='*.fits',slot=None):        
        """ Get examples of the input files associated to a particular process.

        Parameters
        ----------
        process_name : str
                    The name of the assoicated eTraveler process, used in making the output file name
              
        pattern : str
                    Regular expression specifying which files to get
 
        slot : str
                   If set, use the sensor associated with this slot as the template

        Returns
        ----------
        file_list : list

        List of file names for files that match the process_name, sensor_id and pattern
        """        
        if slot is None:
            sn = self.sensor_names[0]
        else:
            sn = self.sensor(slot).sensor_id

        return get_template_files(sn,process_name,pattern)



if __name__ == '__main__':

    outpath = 'output/'
    process_name = 'fe55_offline'
    pattern = '*.fits'

    raft = Raft.create_from_yaml("test_raft.yaml")
    raft.file_copy(process_name,outpath,pattern,dry_run=True)



