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

POLYORDER = 5

# https://dev.lsstcorp.org/cgit/LSST/DMS/afw.git/tree/include/lsst/afw/image/ImageUtils.h#n42
PixelZeroPos = 0.0

# https://dev.lsstcorp.org/cgit/LSST/DMS/afw.git/tree/src/image/TanWcs.cc#n50
fitsToLsstPixels = -1.0

# Total convention offset
offset = PixelZeroPos + fitsToLsstPixels

def getRaDecl(wcs, x, y):
    ra, decl = wcs.pixelToSky(x, y)
    # Make ra go from -180 to +180 for ease of use
    if ra > np.pi * afwGeom.radians:
        ra = ra - 2 * np.pi * afwGeom.radians
    return ra.asDegrees(), decl.asDegrees()
    
def doit(args):
    dataId = args
    print "# Running", dataId
 
    # I need to create a separate instance in each thread
    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()

    wcs    = butler.get(datasetType="asTrans", dataId = dataId)
    distortPixel(1.0, 2.0, wcs)
    import pdb; pdb.set_trace()

def makeApBp(wcs):
    # Turn wcs metadata into distortion matrices
    md = wcs.getFitsMetadata()
    apo = md.get("AP_ORDER")
    bpo = md.get("BP_ORDER")
    assert apo == POLYORDER
    assert bpo == POLYORDER
    Ap  = np.zeros((apo+1, apo+1))
    Bp  = np.zeros((bpo+1, bpo+1))
    for i in range(POLYORDER+1):
        for j in range(POLYORDER+1-i):
            Ap[i][j] = md.get("AP_%d_%d" % (i,j))
            Bp[i][j] = md.get("BP_%d_%d" % (i,j))
    return Ap, Bp

def polyElements(order, val):
    # https://dev.lsstcorp.org/cgit/LSST/DMS/afw.git/tree/src/image/TanWcs.cc#n300
    # Generate a vector of polynomial elements, x^i
    poly = np.zeros((order+1))
    poly[0] = 1.0
    if order == 0:
        return poly
    poly[1] = val
    for i in range(2, order+1):
        poly[i] = poly[i-1]*val
    return poly

def distortPixel(x, y, wcs):
    # https://dev.lsstcorp.org/cgit/LSST/DMS/afw.git/tree/src/image/TanWcs.cc#n353
    md     = wcs.getFitsMetadata() 
    crpix1 = md.get("CRPIX1")
    crpix2 = md.get("CRPIX2") 
    Ap, Bp = makeApBp(wcs)

    # Relative, undistorted pixel coords
    U = x - crpix1
    V = y - crpix2

    uPoly = polyElements(POLYORDER, U)
    vPoly = polyElements(POLYORDER, V)
    
    F = 0.0
    G = 0.0
    for i in range(POLYORDER):
        for j in range(POLYORDER):
            F += Ap[i,j] * uPoly[i] * vPoly[j]
            G += Bp[i,j] * uPoly[i] * vPoly[j]
            
    return x + F, y + G
    
def skyToPixel(raDeg, decDeg, wcs):
    # https://dev.lsstcorp.org/cgit/LSST/DMS/afw.git/tree/src/image/TanWcs.cc#n252
    # wcss2p(_wcsInfo, 1, 2, skyTmp, &phi, &theta, imgcrd, pixTmp, stat);

    # This needs to be written in C to make use of wcslib
    # x, y = wcss2p(raDeg, decDeg, wcs)

    # I will approximate this using a hopefully-right python implementation:
    # https://pypi.python.org/pypi/pywcs
    import pywcs
    md = wcs.getFitsMetadata() 
    prm = pywcs.Wcsprm()
    prm.crpix   = np.array((md.get("CRPIX1"), md.get("CRPIX2")))
    prm.crval   = np.array((md.get("CRVAL1"), md.get("CRVAL2")))
    prm.cunit   = ["deg", "deg"]
    prm.ctype   = ["RA---TAN", "DEC--TAN"]
    prm.equinox = md.get("EQUINOX")
    prm.radesys = md.get("RADESYS")
    prm.cd      = np.array(((md.get("CD1_1"), md.get("CD1_2")), (md.get("CD2_1"), md.get("CD2_2"))))

    raref       = 318.62
    decref      = -0.11
    # LSST official Wcs result
    xref, yref  = wcs.skyToPixel(afwCoord.Coord(afwGeom.Point2D(raref, decref)))
    
    # Linear approximation
    xlin, ylin  = prm.s2p(((raref,decref),), origin=0)["pixcrd"][0]

    # SIP addition
    xp, yp = distortPixel(xlin, ylin, wcs)

    print xref, yref, "LIN", (xref-xlin), (yref-ylin), "SIP", (xref-xp), (yref-yp)
    return xp + offset, yp + offset
    
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

    if True:
        # 1 by 1
        map(doit, args)
    else:
        # In parallel; note you need to import this *after* you declare doit()
        import multiprocessing
        pool = multiprocessing.Pool(multiprocessing.cpu_count()//2)
        pool.map(doit, args)
