import os
import glob
import sys
import time
from lsst.daf.butler import Butler

repo = '/sdf/group/lsst/camera/IandT/repo_gen3/BOT_data'
collections = ['LSSTCam/raw/all']
Run = sys.argv[1]

butler = Butler(repo, collections=collections)

where = f"instrument='LSSTCam' and exposure.science_program='{Run}'"
dsrefs = list(butler.registry.queryDatasets('raw', where=where))
num_frames = len(dsrefs)//205

secs_per_frame = 21.
offset = 1.5*3600
duration = time.gmtime(secs_per_frame*num_frames + offset)
print(time.strftime('%H:%M:%S', duration))

