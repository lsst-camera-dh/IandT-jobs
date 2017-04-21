import sys
import glob
import time
import logging
import java.lang
from org.lsst.ccs.scripting import CCS
import eolib
from ccs_scripting_tools import CcsSubsystems

CCS.setThrowExceptions(True);

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

def setup_sequencer(ts8, logger=logger):
    ts8.synchCommand(10, "setSequencerStart Clear")
    for iclear in range(9):
        ts8.synchCommand(10, "startSequencer")
        ts8.synchCommand(10, "waitSequencerDone 5000")
    command = 'exposeAcquireAndSave 100 False False ""'
    logger.info(ts8.synchCommand(500, command).getResult())

def setup_ccd_info(ccs_sub, ccdtype, ccdnames, ccdmanunames):
    """
    Refactored version of eolib.EOTS8SetupCCDInfo
    """
    geo = ccs_sub.ts8.synchCommand(2, "printGeometry 3").getResult()
    for line in geo.split('\n'):
        if 'Sen' not in line:
            continue
        slot = line[-2:]
        ccdid = line.split(' ')[1]
        command = 'setLsstSerialNumber %s %s' % (ccdid, ccdnames[slot])
        ccs_sub.ts8.synchCommand(2, command)
        rebid = int(slot[0])
        ccdnum = int(slot[1])
        if ccdmanunames[slot]:
            command = ('setManufacturerSerialNumber %s %s'
                       % (ccdid, ccdmanunames[slot]))
            ccs_sub.ts8.synchCommand(command)
        command = "getChannelValue R00.Reb%i.CCDTemp%i" % (rebid, ccdnum)
        ccdtemp = ccs_sub.ts8.synchCommand(2, command).getResult()
        command = "setMeasuredCCDTemperature %s %s" % (ccdid, ccdtemp)
        ccs_sub.ts8.synchCommand(10, command)
        command = "getChannelValue REB%s.hvbias.VbefSwch"  % rebid
        hv = ccs_sub.rebps.synchCommand(10, command).getResult()
        ccs_sub.ts8.synchCommand(10, "setMeasuredCCDBSS %s %s" % (ccdid, hv))

def get_exptime_limits(acqname, acq_config_file):
    lo_lim = float(eolib.getCfgVal(acq_config_file, '%s_LOLIM' % acqname,
                                   default='0.025'))
    hi_lim = float(eolib.getCfgVal(acq_config_file, '%s_HILIM' % acqname,
                                   default='600.0'))
    return lo_lim, hi_lim

def get_image_count(acqname, acq_config_file):
    if 'FLAT' in acqname:
        imcount = int(eolib.getCfgVal(acqcfgfile, '%s_IMCOUNT' % acqname,
                                      default='2'))
    else:
        imcount = int(eolib.getCfgVal(acqcfgfile, '%s_IMCOUNT' % acqname,
                                      default='1'))
    return imcount

if __name__ == '__main__':
    ccs_sub = CcsSubsystems(subsystems=dict(ts='ts',
                                            pd_bias='ts/Bias',
                                            pd='ts/PhotoDiode',
                                            mono='ts/Monochromator',
                                            ts8='ts8',
                                            rebps='ccs-rebps'))

    ccs_sub.ts8.synchCommand(90, "loadSequencer %s" % seqfile)

    result = ccs_sub.mono.synchCommand(20, "openShutter")

    lo_lim, hi_lim = get_exptime_limits(acqname, acq_config_file)
    imcount = get_image_count(acqname, acq_config_file)

    wl = float(eolib.getCfgVal(acqcfgfile, '%s_WL' % acqname, default="550.0"))

# move to default wl
    print "Setting monochromator wl to default value"
    rwl = monosub.synchCommand(60,"setWaveAndFilter",wl).getResult();
    print "Monochromator reports wl = ",rwl
    result = ts8sub.synchCommand(10,"setMonoWavelength %f" % rwl)
# bias image count
    bcount = int(eolib.getCfgVal(acqcfgfile, '%s_BCOUNT' % acqname, default='1'))
# sequence number
    seq = 0
# old wave length setting
    owl = -1.0
# number of PulseLinceCounts between readings
    nplc = 1.0
# exposure time
    exptime = -1
# default file pattern
    def_pat = "${CCDSerialLSST}_${testType}_${imageType}_${SequenceInfo}_${RunNumber}_${timestamp}.fits"
    ts8sub.synchCommand(10,"setFitsFileNamePattern",def_pat)
# flat file pattern
# E2V-CCD250-179_flat_0065.07_flat2_20161130064552.fits
    flat_pat = '${CCDSerialLSST}_${testType}_%07.2fs_${imageType}%d_${RunNumber}_${timestamp}.fits'
# qe file pattern
# E2V-CCD250-179_lambda_flat_1100_076_20161130124533.fits
    qe_pat = '${CCDSerialLSST}_${testType}_${imageType}_%4.4d_${RunNumber}_${timestamp}.fits'
# sflat file pattern
# E2V-CCD250-179_lambda_flat_1100_076_20161130124533.fits
    sflat_pat = '${CCDSerialLSST}_${testType}_${imageType}_%s%3.3d_${timestamp}.fits'



    print "Working on RAFT %s" % UNITID

# keep list of produced files
    fpfiles = open("%s/acqfilelist" % tsCWD,"w");

# count how many instructions there are
    fp = open(acqcfgfile,"r");
    number_instr = 0
    for line in fp:
        tokens = str.split(line)
        if ((len(tokens) > 0) and (tokens[0] == acqname.lower())):
            number_instr += 1
    fp.close()

# ---- now start --------------
# go through EO test config file looking for instructions
    print "Scanning config file for specifications for %s" % acqname.lower();
    fp = open(acqcfgfile,"r");
    for line in fp:

# split the instruction according to test type
        tokens = str.split(line)
        if ((len(tokens) > 0) and (tokens[0] == acqname.lower())):

            print "==== working on sequence %d  Total# = %d" % (seq,number_instr)

            doXED = False
            doLight = False

            if 'FLAT' in acqname :
# .. indicate that the exposure time must be recalculated
                exptime = -1
                doLight = True
                if 'SFLAT' in acqname :
                    wl = int(tokens[1])
                    target = int(tokens[2])
                    imcount = int(tokens[3])
                else :
# exptime will be set later using the flux calib
                    target = float(tokens[1])
# imcount was already set
            elif 'LAMBDA' in acqname :
                wl = int(tokens[1])
                target = float(tokens[2])
# .. indicate that the exposure time must be recalculated
                exptime = -1
                doLight = True
                print "wl = %f" % wl;
            else :
                exptime = float(tokens[1])
                imcount = float(tokens[2])
                if 'PPUMP' in acqname :
                    nshifts  = float(tokens[3])
                elif 'FE55' in acqname :
                    doXED = True
            print "\nfound instruction (%s) with image count = %d" % (line,imcount)

# ==================================================
# setup meta data for these exposures
# ==================================================
            print "setting location of fits directory"

            ts8sub.synchCommand(10,"setDefaultImageDirectory","%s/S${sensorLoc}" % (tsCWD));

            ts8sub.synchCommand(10,"setRaftName",str(UNITID))
            ts8sub.synchCommand(10,"setRunNumber",runnum)

# ==================================================
# take bias images
# ==================================================

# probably not needed any more 
            for i in range(7):
                timestamp = time.time()
                print "Ready to take clearing bias image. time = %f" % time.time()
                ts8sub.synchCommand(10,"setTestType",acqname.upper())
                ts8sub.synchCommand(10,"setImageType","biasclear")
                ts8sub.synchCommand(10,"setSeqInfo",seq)
                try:
                    rply = ts8sub.synchCommand(500,"exposeAcquireAndSave",50,False,False,"").getResult()
                    print "clearing acquisition completed"
                except Exception, ex:
                    print "Proceeding despite error: %s" % str(ex)
                    pass
                print "after click click at %f" % time.time()
                time.sleep(1.0)

            ts8sub.synchCommand(10,"setFitsFileNamePattern",def_pat)
            time.sleep(3.0)
# now do the useful bias acquisitions
            num_tries = 0
            max_tries = 3
            i = 0
            while i<bcount:
                try:
                    timestamp = time.time()

                    print "Ready to take bias image. time = %f" % time.time()


                    ts8sub.synchCommand(10,"setTestType",acqname.upper().replace("PPUMP","TRAP").replace("SFLAT","SFLAT_%3.3d"%int(wl)))
                    ts8sub.synchCommand(10,"setImageType","BIAS")
                    ts8sub.synchCommand(10,"setSeqInfo",seq)
                    rply = ts8sub.synchCommand(150,"exposeAcquireAndSave",0,False,False).getResult()
                    print "completed bias exposure"
                    i += 1
                    num_tries = 0
                except Exception, ex:
                    num_tries += 1
                    if num_tries < max_tries:
                        print "RETRYING BIAS EXPOSURE - Error was: %s" % ex
                        time.sleep(10.0)
                    else:
                        raise Exception("EXCEEDED MAX RETRIES ON BIAS EXPOSURE: %s" % str(ex))

                print "after click click at %f" % time.time()
#                time.sleep(3.0)


########################## Start of flux calib section #############################
            if (('FLAT' in acqname or 'LAMBDA' in acqname) and wl!=owl):
                                            
                print "Setting monochromator lambda = %8.2f" % wl
                for itry in range(3) :
                    try:
                        rwl = monosub.synchCommand(60,"setWaveAndFilter",wl).getResult();
                        print "Monochromator reports wl = ",rwl
#                        result = ts8sub.synchCommand(10,"setHeader","MonochromatorWavelength %f true" % rwl)
                        result = ts8sub.synchCommand(10,"setMonoWavelength %f" % rwl)
                        break
                    except:
                        time.sleep(5.0)
                        print "trying again"
                        pass

                time.sleep(10.0)
                print "publishing state"
                result = tssub.synchCommand(60,"publishState");


# dispose of first image
                ts8sub.synchCommand(10,"setTestType",acqname.upper())
                ts8sub.synchCommand(10,"setImageType","prefluxcalib")
                ts8sub.synchCommand(10,"setSeqInfo",seq)
                try:
                    testfitsfiles = ts8sub.synchCommand(500,"exposeAcquireAndSave",2000,True,False,"").getResult();
                except:
                    pass
                time.sleep(2.0)

# now do the useful exposure for the flux calibration
                success = False
                num_tries = 0
                max_tries = 3
                while not success:
                    try:
                        ts8sub.synchCommand(10,"setTestType",acqname.upper())
                        ts8sub.synchCommand(10,"setImageType","fluxcalib")
                        ts8sub.synchCommand(10,"setSeqInfo",seq)

                        testfitsfiles = ts8sub.synchCommand(500,"exposeAcquireAndSave",2000,True,False).getResult();

                        success = True
                    except Exception, ex:
                        num_tries += 1
                        if num_tries > max_tries :
                            raise Exception("EXCEEDED MAXIMUM NUMBER OF RETRIES FOR FLUX CALIB: %s" % str(ex))
                        else:
                            print "RETRYING FLUX CALIB EXPOSURE"
                            time.sleep(10.0)
                print "fitsfiles = "
                print testfitsfiles

                fluxsum = 0.0
                nflux = 0
                for flncal in testfitsfiles:
                    flncalpath = glob.glob("%s/*/%s" % (tsCWD,flncal))[0]
                    print "full flux file path = %s" % flncalpath
                    fluxfl = float(ts8sub.synchCommand(10,"getFluxStats","%s" % flncalpath).getResult());
                    print "flux = ",fluxfl
                    fluxsum += fluxfl;
                    nflux=nflux+1;

                flux = fluxsum / nflux;

                print "The flux is determined to be %f" % flux

                owl = wl
# ####################################################################################
                print "raw flux value = %f" % flux
                if (flux < 2.0) :
                # must be a test
                    flux = 300.0
                    print "SETTING A DEFAULT TEST FLUX OF 300 DUE TO APPARENT NO SENSOR TEST IN PROGRESS"

####################### End of flux calib section ###########################################

# check if exptime needs to be recalculated
            if (exptime < 0.):
                exptime = target/flux

            print "needed exposure time = %f" % exptime
            if (exptime > hi_lim) :
                exptime = hi_lim
            if (exptime < lo_lim) :
                exptime = lo_lim
            print "adjusted exposure time = %f" % exptime

# =========================================
# prepare to readout photodiodes                
# =========================================
            if (exptime>0.5) :
                nplc = 1.0
            else :
                nplc = 0.25

            MAX_READS = 2048
            if 'DARK' in acqname or 'FE55' in acqname :
                MAX_READS = 1000

            nreads = (exptime+2.0)*60/nplc
            if (nreads > MAX_READS):
                nreads = MAX_READS
                nplc = (exptime+2.0)*60/nreads
                print "Nreads limited to 3000. nplc set to %f to cover full exposure period " % nplc


# adjust timeout because we will be waiting for the data to become ready
            mywait = nplc/60.*nreads*1.50 ;
            print "Setting timeout to %f s" % mywait
#temp            pdsub.synchCommand(1000,"setTimeout",mywait);

# =====================================================================================
#       EXPOSE
# =====================================================================================
            num_tries = 0
            max_tries = 3
            imdone=0
            print "\n\n\n ######################################################################## "
            print "\n       starting exposure sequence %d of %d for %d images" % (seq,number_instr,imcount)
            print "\n ######################################################################## "
            while imdone<imcount :

                try:
                    fpause = open("/tmp/ccs.pause","r");
                    print "Detected pause request (/tmp/ccs.pause) exists. Remove this file to proceed"
                    fpause.close()
                    time.sleep(5.0)
                    continue
                except:
                    pass


                try:
                    print "\n ######################################################################## "
                    print "\n            image number %d in 0->%d in sequence %d in 0->%d  -- try#%d   " % (imdone,imcount-1,seq,number_instr-1,num_tries)
                    print "\n ######################################################################## "
                    print " starting clearing "
                    for i in range(3):
                        timestamp = time.time()
                        print "Ready to take clearing bias image. time = %f" % time.time()
                        ts8sub.synchCommand(10,"setTestType",acqname.upper())
                        ts8sub.synchCommand(10,"setImageType","biasclear")
                        ts8sub.synchCommand(10,"setSeqInfo",seq)
                        try:
                            rply = ts8sub.synchCommand(500,"exposeAcquireAndSave",0,False,False,"").getResult()
                            print "image done"
                        except Exception, ex:
                            print "Proceeding despite error: %s" % str(ex)
                            pass
                        print "after click click at %f" % time.time()
                        time.sleep(1)
                    print "done clearing"
                    if (doPD) :
                        print "calling accumBuffer to start IS photodiode recording at %f" % time.time()
                        pdresult =  pdsub.asynchCommand("accumBuffer",int(nreads),float(nplc),True);

                        while(True) :
                            result = pdsub.synchCommand(10,"isAccumInProgress");
                            rply = result.getResult();
                            print "checking for PD accumulation in progress at %f" % time.time()
                            if rply==True :
                                print "accumulation running"
                                break
                            print "accumulation hasn't started yet"
                            time.sleep(0.25)
                        print "recording should now be in progress and the time is %f" % time.time()

                    timestamp = time.time()

# make sure to get some readings before the state of the shutter changes       
                    time.sleep(0.2);

                    print "Ready to take image with exptime = %f at time = %f" % (exptime,time.time())
                
                    ts8sub.synchCommand(10,"setTestType",acqname.upper().replace("PPUMP","TRAP").replace("SFLAT","SFLAT_%3.3d"%int(wl)))
                    ts8sub.synchCommand(10,"setImageType",acqname.upper().replace("SFLAT","FLAT").replace("LAMBDA","FLAT"))

                    ts8sub.synchCommand(10,"setSeqInfo",seq)
#                        ts8sub.synchCommand(10,"setSeqInfo","%s_%07.2f" % (str(seq),exptime))

                    if 'FLAT' in acqname :
                        if 'SFLAT' in acqname :
                            lohiflux = "L"
                            if (target>10000) :
                                lohiflux = "H"
                            ts8sub.synchCommand(10,"setFitsFileNamePattern",sflat_pat % (lohiflux,imdone+1))
                        else :
                            ts8sub.synchCommand(10,"setFitsFileNamePattern",flat_pat % (exptime,imdone+1))
                    if 'LAMBDA' in acqname :
                        ts8sub.synchCommand(10,"setFitsFileNamePattern",qe_pat % int(wl))

                    fitsfiles = ts8sub.synchCommand(700,"exposeAcquireAndSave",int(exptime*1000),doLight,doXED).getResult();
                    ts8sub.synchCommand(10,"setFitsFileNamePattern",def_pat)

                    print "image %d done at %f" % (imdone,time.time())

# =======================================
#  retrieve the photodiode readings
# =======================================

                    if (doPD) :
                        print "getting photodiode readings at time = %f" % time.time();

                        pdfilename = "pd-values_%d-for-seq-%d-exp-%d.txt" % (int(timestamp),seq,i+1)

                        print "starting the wait for an accumBuffer done status message at %f" % time.time()
                        tottime = pdresult.get();

# make sure the sample of the photo diode is complete
                        time.sleep(10.)

                        print "executing readBuffer at %d, tsCWD=%s , pdfilename = %s" % (time.time(),tsCWD,pdfilename)

#                result = pdsub.synchCommand(1000,"readBuffer","/tmp/%s" % pdfilename);
                        result = pdsub.synchCommand(1000,"readBuffer","/%s/%s" % (tsCWD,pdfilename),"ts8prod@ts8-raft1");
                        buff = result.getResult()
                        print "Finished getting readings at %f" % time.time()

                        time.sleep(5.0)

                        for fitsfilename in fitsfiles :
                            print "adding binary table of PD values for %s" % fitsfilename
                            fullfitspath = glob.glob("%s/*/%s" % (tsCWD,fitsfilename))[0]
                            print "fullfitspath = %s" % fullfitspath
                            result = ts8sub.synchCommand(200,"addBinaryTable","%s/%s" % (tsCWD,pdfilename),"%s" % fullfitspath,"AMP0.MEAS_TIMES","AMP0_MEAS_TIMES","AMP0_A_CURRENT",timestamp)
                            fpfiles.write("%s %s/%s %f\n" % (fullfitspath,tsCWD,pdfilename,timestamp))
# ===================== end of PD value retrieval and end of exposure section ======================
                    print "successful exposure .... incrementing images completed count"
                    imdone = imdone + 1
                    num_tries = 0
                except Exception, ex:
                    num_tries += 1
                    if num_tries > max_tries :
                        raise Exception('TOO MANY RETRIES! %s' % str(ex))
                    else :
                        print "something went wrong during the exposure ... RETRYING: %s" % str(ex)
                        time.sleep(20.0)
                        rply = pdsub.synchCommand(30,"reset").getResult()
                        time.sleep(20.0)
                print "checking ... imdone = %d" % imdone
            print "incrementing sequence number"
            seq += 1
# ------------------- end of imcount loop --------------------------------

# reset timeout to something reasonable for a regular command
#            pdsub.synchCommand(1000,"setTimeout",10.);


    fpfiles.close();
    fp.close();

    fp = open("%s/status.out" % (tsCWD),"w");

    istate=0;
    result = tssub.synchCommandLine(10,"getstate");
    istate=result.getResult();
    fp.write(`istate`+"\n");
    fp.write("%s\n" % ts_version);
    fp.write("%s\n" % ts_revision);
    fp.write("%s\n" % "NA");
    fp.write("%s\n" % "NA");
    fp.write("%s\n" % ts8_version);
    fp.write("%s\n" % ts8_revision);
    fp.write("%s\n" % power_version);
    fp.write("%s\n" % power_revision);
    fp.close();

# move TS to idle state
                    
#    result = tssub.synchCommand(200,"setTSReady");
#    rply = result.getResult();

# get the glowing vacuum gauge back on
#    result = pdusub.synchCommand(120,"setOutletState",vac_outlet,True);
#    rply = result.getResult();
try:
    result = ts8sub.synchCommand(10,"setTestType","%s-END" % acqname)
    print "something"

except Exception, ex:

# get the glowing vacuum gauge back on
#    result = pdusub.synchCommand(120,"setOutletState",vac_outlet,True);
#    rply = result.getResult();

    rply = pdsub.synchCommand(10,"softReset").getResult()

    raise Exception("There was an exception in the acquisition producer script. The message is\n (%s)\nPlease retry the step or contact an expert," % ex)

except ScriptingTimeoutException, exx:

    print "ScriptingTimeoutException at %f " % time.time()

# get the glowing vacuum gauge back on
#    result = pdusub.synchCommand(120,"setOutletState",vac_outlet,True);
#    rply = result.getResult();

    rply = pdsub.synchCommand(10,"softReset").getResult()

    raise Exception("There was an exception in the acquisition producer script. The message is\n (%s)\nPlease retry the step or contact an expert," % exx)


print "%s: END" % acqname
