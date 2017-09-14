#!/usr/bin/env python
import lcatr.schema
import siteUtils

producer = 'INT-SR-MET-01'
# Will need to make ABSOLUTE HEIGHT a separate harnessed job analysis?

# Locate the output files from the producer step
# Read and parse the ASCII tables, registering extracted results with the eTraveler database
# Register the ASCII files and PNG plots with the eTraveler database/Data Catalog - including associated
# metadata
# Do this separately for the two different TESTTYPE values?

testtype = 'FLATNESS'

md = siteUtils.DataCatalogMetadata(CCD_MANU=siteUtils.getCcdVendor(),
                                  LSST_NUM=sensor_id,
                                  PRODUCER='INT-SR-MET-01',
                                  ORIGIN='SLAC',
                                  TEST_CATEGORY='MET')

results_file = '%s_name_of_results_file.txt' % sensor_id
results = [lcatr.schema.fileref.make(results_file,
                                     metadata=md(DATA_PRODUCT='MET_RESULTS'))]

# below is just notional
png_files = glob.glob('*.png')
results.extend([lcatr.schema.fileref.make(item,
                                           metadata=md(DATA_PRODUCT='type of data product')
                for item in png_files])

# Parse the metadata from the scan file (also just notional)
temp_start = []
temp_end = []
for line in open(raftData.infile):
    if line.startswith('# start time ='):
        tokens = line.split()
        start_time = float(tokens[4])
        end_time = float(tokens[9])
    if line.startswith('# temperature'):
        tokens = line.split()
        temp_start.append(float(tokens[5]))
        temp_end.append(float(tokens[9]))

results.append(lcatr.schema.valid(lcatr.schema.get('ts5_raft_flatness2'),
                                  start_time=start_time,
                                  end_time=end_time,
                                  temp_A_start = temp_start[0],
                                  temp_B_start = temp_start[1],
                                  temp_C_start = temp_start[2],
                                  temp_D_start = temp_start[3],
                                  temp_A_end = temp_end[0],
                                  temp_B_end = temp_end[1],
                                  temp_C_end = temp_end[2],
                                  temp_D_end = temp_end[3]))


results.extend(siteUtils.jobInfo())
results.extend(siteUtils.packageVersions())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
