#!/usr/bin/env python
#from ccsTools import ccsValidator
import glob
import os
import lcatr.schema
import siteUtils

raft_id = siteUtils.getUnitID()

md = siteUtils.DataCatalogMetadata(CCD_MANU=siteUtils.getCcdVendor(),
                                   LSST_NUM=sensor_id,
                                   PRODUCER='INT-SR-MET-01',
                                   ORIGIN='SLAC',
                                   TEST_CATEGORY='MET')

# The pattern matching below needs to be specific enough to find the
# scan data file (and not, say, the scan plan file).  
datfile = glob.glob("*.tnt")[0]

# The lines below (copied from a BNL TS5 validator script) have the
# effect of moving any comment lines in the data file (lines that
# start with #) to the top of the file.  This does not seem particularly
# important
os.system("grep \"^#\" %s > temp.dat" % datfile)
os.system("grep -v \"^#\" %s >> temp.dat" % datfile)
os.system("mv temp.dat %s" % datfile)

#ccsValidator('TS5-PulseScan')

results = [lcatr.schema.fileref.make(datfile,
                                     metadata=md(DATA_PRODUCT='MET_DATA'))]

results.extend(siteUtils.jobInfo())
results.extend(siteUtils.packageVersions())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
