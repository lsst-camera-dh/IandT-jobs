#!/usr/bin/env python
#from ccsTools import ccsValidator
import glob
import os
import lcatr.schema
import siteUtils

raft_id = siteUtils.getUnitId()

md = siteUtils.DataCatalogMetadata(CCD_MANU=siteUtils.getCcdVendor(),
                                   LSST_NUM=raft_id,
                                   PRODUCER='INT-SR-MET-01',
                                   ORIGIN='SLAC',
                                   TEST_CATEGORY='MET')

# The pattern matching below needs to be specific enough to find the
# scan plan file  
scanplan = glob.glob("*scanplan*")[0]

# The pattern matching below needs to be specific enough to find the
# scan data file (and not, say, the scan plan file)
scandata = glob.glob("*.tnt")[0]

results = [lcatr.schema.fileref.make(scanplan, metadata=md(DATA_PRODUCT='MET_DATA')),
           lcatr.schema.fileref.make(scandata, metadata=md(DATA_PRODUCT='MET_DATA'))]

print(results)

results.extend(siteUtils.jobInfo())
results.extend(siteUtils.packageVersions())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
