import sys
import re
import md5
import numpy as np
import time
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.meas.algorithms as measAlg
import lsst.daf.persistence as dafPersist
import lsst.daf.base as dafBase
from lsst.obs.sdss import SdssMapper as Mapper
from lsst.obs.sdss import convertfpM

doWriteSql = True
doc = """Generate an initial set of test-data for KB-MOD"""

def doit(args):
    dataId = args
    print "# Running", dataId
 
    # I need to create a separate instance in each thread
    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()

    wcs    = butler.get(datasetType="asTrans", dataId = dataId)
    md     = wcs.getFitsMetadata()
    keys   = ["CRPIX1", "CRPIX2", "CD1_1", "CD1_2", "CD2_1", "CD2_2", "CRVAL1", "CRVAL2", "AP_0_0", "AP_0_1", "AP_0_2", "AP_0_3", "AP_0_4", "AP_0_5", "AP_1_0", "AP_1_1", "AP_1_2", "AP_1_3", "AP_1_4", "AP_2_0", "AP_2_1", "AP_2_2", "AP_2_3", "AP_3_0", "AP_3_1", "AP_3_2", "AP_4_0", "AP_4_1", "AP_5_0", "BP_0_0", "BP_0_1", "BP_0_2", "BP_0_3", "BP_0_4", "BP_0_5", "BP_1_0", "BP_1_1", "BP_1_2", "BP_1_3", "BP_1_4", "BP_2_0", "BP_2_1", "BP_2_2", "BP_2_3", "BP_3_0", "BP_3_1", "BP_3_2", "BP_4_0", "BP_4_1", "BP_5_0"]

    camcol = dataId["camcol"]
    field = dataId["field"]
    filterName = dataId["filter"]
    run = dataId["run"]
    fieldId  = int(md5.new(" ".join(map(str, [run, filterName, camcol, field]))).hexdigest(), 16) % 2**63

    wfile = "wcs-%06d-%s%s-%04d.csv" % (run, filterName, camcol, field)
    wbuff = open(wfile, "w")
    wbuff.write(str(fieldId)+","+",".join([str(md.get(key)) for key in keys])+"\n")
    wbuff.close()

if __name__ == "__main__":
    if False:
        dataIds = [{"run": 6474, "camcol": 5, "field": 143},
                   {"run": 6484, "camcol": 5, "field": 144},
                   {"run": 6504, "camcol": 5, "field": 146}]
    else:  
        dataIds = []
        infile = sys.argv[1]
        for line in open(infile).readlines():
            if line.startswith('#'):
                continue
            fields = line.split()
            dataIds.append({"run": int(fields[0]), "camcol": int(fields[1]), "field": int(fields[2])})

    args = []
    for dataId in dataIds:
        for filterName in ["g", "r", "i"]:
            dId = dataId.copy()
            dId["filter"] = filterName
            args.append(dId)

    if False:
        # 1 by 1; debugging
        map(doit, args)
    else:
        # In parallel; note you need to import this *after* you declare doit()
        import multiprocessing
        pool = multiprocessing.Pool(multiprocessing.cpu_count()//2)
        pool.map(doit, args)
