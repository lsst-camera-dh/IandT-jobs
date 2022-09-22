import os
import glob
import shutil
from astropy.io import fits


def update_ts8_headers(dayobs_dir):
    pattern = os.path.join(dayobs_dir, 'TS*')
    folders = sorted(glob.glob(pattern))
    for folder in folders:
        fits_files = sorted(glob.glob(os.path.join(folder, 'TS*.fits')))
        if not fits_files:
            continue
        # Only consider non-empty fits files:
        non_empty = []
        empty = []
        for item in fits_files:
            if os.stat(item).st_size > 0:
                non_empty.append(item)
            else:
                empty.append(item)
        # Move empty files out of the way.
        if empty:
            dest_dir = os.path.join(folder, 'empty_files')
            os.makedirs(dest_dir, exist_ok=True)
            for src in empty:
                dest = os.path.join(dest_dir, os.path.basename(src))
                shutil.move(src, dest)
        fits_files = non_empty
        if not non_empty:
            continue
        # Check the header of the last fits file in the non-empty list.
        # If its header is up-to-date, then assume entire folder is as well.
        try:
            with fits.open(fits_files[-1]) as hdus:
                is_updated = (hdus[0].header['TSTAND'] == 'TS8' and
                              hdus[0].header['INSTRUME'] == 'LSST-TS8')
        except OSError:
            print("OSError:", fits_files[-1], flush=True)
            raise
        if is_updated:
            continue
        for fits_file in fits_files:
            # HDUList.writeto is slow so write to temp file first, then
            # replace the original with the temp file.  This avoids
            # corrupting the original file in case the job times out or
            # is canceled while the .writeto is still running.
            temp_file = 'temp_file.fits'
            try:
                with fits.open(fits_file) as hdus:
                    hdus[0].header['TSTAND'] = 'TS8'
                    hdus[0].header['INSTRUME'] = 'LSST-TS8'
                    hdus.writeto(temp_file, overwrite=True)
                shutil.move(temp_file, fits_file)
            except (OSError, TypeError):
                print("OSError, TypeError:", fits_file, flush=True)
                raise
            except fits.verify.VerifyError:
                print("fits.verify.VerifyError:", fits_file, flush=True)
                raise
        print(folder, flush=True)


with open('processed_folders.txt') as fobj:
    processed_folders = [_.strip() for _ in fobj]

ts8_root_dir = '/sdf/group/lsst/camera/IandT/R_and_D/ts8'
dayobs_dirs = sorted(glob.glob(os.path.join(ts8_root_dir, '*')))

for dayobs_dir in dayobs_dirs:
    if '20220706' in dayobs_dir or dayobs_dir in processed_folders:
        continue
    update_ts8_headers(dayobs_dir)
    print("processed", dayobs_dir, flush=True)
