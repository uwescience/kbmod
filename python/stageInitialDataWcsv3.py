import sys
import re
import md5
import numpy as np
import time
#import lsst.daf.persistence as dafPersist
#from lsst.obs.sdss import SdssMapper as Mapper

doWriteSql = True
doc = """Generate an initial set of test-data for KB-MOD"""

def doit(args):
    # I need to create a separate instance in each thread
    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()
    keys   = ["CRPIX1", "CRPIX2", "CD1_1", "CD1_2", "CD2_1", "CD2_2", "CRVAL1", "CRVAL2", "AP_0_0", "AP_0_1", "AP_0_2", "AP_0_3", "AP_0_4", "AP_0_5", "AP_1_0", "AP_1_1", "AP_1_2", "AP_1_3", "AP_1_4", "AP_2_0", "AP_2_1", "AP_2_2", "AP_2_3", "AP_3_0", "AP_3_1", "AP_3_2", "AP_4_0", "AP_4_1", "AP_5_0", "BP_0_0", "BP_0_1", "BP_0_2", "BP_0_3", "BP_0_4", "BP_0_5", "BP_1_0", "BP_1_1", "BP_1_2", "BP_1_3", "BP_1_4", "BP_2_0", "BP_2_1", "BP_2_2", "BP_2_3", "BP_3_0", "BP_3_1", "BP_3_2", "BP_4_0", "BP_4_1", "BP_5_0"]

    pid = multiprocessing.current_process().name
    output = ""
    badids = ""
    for arg in args:
        try:
            dataId     = {"run": int(info[0]), "camcol": int(info[1]), "filter": info[2], "field": int(info[3])}
            wcs        = butler.get(datasetType="asTrans", dataId = dataId)
            md         = wcs.getFitsMetadata()
            camcol     = dataId["camcol"]
            field      = dataId["field"]
            filterName = dataId["filter"]
            run        = dataId["run"]
            imageId    = int(md5.new(" ".join(map(str, [run, camcol, field, filterName]))).hexdigest(), 16) % 2**(64-1)
        except:
            badids.append(" ".join(arg)+"\n")
        else:
            output.append(str(fieldId)+","+",".join([str(md.get(key)) for key in keys])+"\n")

    wfile = "wcs-%s-v3.csv" % (pid)
    wbuff = open(wfile, "w")
    for line in output:
        wbuff.write(line)
    wbuff.close()

    wfile = "bad-%s-v3.csv" % (pid)
    wbuff = open(wfile, "w")
    for line in badids:
        wbuff.write(line)
    wbuff.close()

if __name__ == "__main__":
    info = []
    for line in open(sys.argv[1]).readlines():
        info.append(line.split())
    njobs = 10
    nper  = len(info)//njobs+1
    args = []
    for n in range(njobs):
        args.append(info[n*nper:(n+1)*nper])

    doit(args[0][:3])
    sys.exit(1)

    import multiprocessing
    pool = multiprocessing.Pool(njobs)
    pool.map(doit, args)
