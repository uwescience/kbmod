import sys
import numpy as np
import time
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.daf.persistence as dafPersist
from lsst.obs.sdss import SdssMapper as Mapper
from lsst.obs.sdss import convertfpM


doc = """Generate an initial set of test-data for KB-MOD"""

def doit(args):
    dataId = args
    print "# Running", dataId
 
    # I need to create a separate instance in each thread
    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()

    # Note: what to do about the 128 pixel overlap?
    # See python/lsst/obs/sdss/processCcdSdss.py for guidance
    im     = butler.get(datasetType="fpC", dataId = dataId).convertF()
    calib, gain = butler.get(datasetType="tsField", dataId = dataId)
    var    = afwImage.ImageF(im, True)
    var   /= gain

    # Note I need to do a bit extra for the mask; I actually need to call
    # convertfpM with allPlanes = True to get all the SDSS info
    #
    # mask   = butler.get(datasetType="fpM", dataId = dataId)
    fpMFile = butler.mapper.map_fpM(dataId = dataId).getLocations()[0]
    mask   = convertfpM(fpMFile, True)

    # Decision point: do I send the convolution a MaskedImage, in which
    # case the mask is also spread, or just an Image, and not spread
    # the mask...  
    # 
    # I think for now I will not spread the mask so that it represents the
    # condition of the underlying pixels, not the Psf-filtered ones
    # mi     = afwImage.MaskedImageF(im, mask, var)

    psf    = butler.get(datasetType="psField", dataId = dataId)
    wcs    = butler.get(datasetType="asTrans", dataId = dataId)

    # Image convolved with the Psf, i.e. maximum point source likelihood image
    cim    = afwImage.ImageF(im, True)
    afwMath.convolve(cim, im, psf.getKernel(), True)
    # The pixels that are "good" in the image, i.e. ignore borders
    cBBox  = psf.getKernel().shrinkBBox(cim.getBBox())
    cim    = afwImage.ImageF(cim, cBBox)
    mask   = afwImage.MaskU(mask, cBBox)
 
    # Create an ra,decl map for the good pixels
    raIm   = afwImage.ImageF(cim.getDimensions())
    decIm  = afwImage.ImageF(cim.getDimensions())
    nx, ny = cim.getDimensions()
    # But note that the Wcs expects their coordinates in the non-shrunk image
    x0     = cBBox.getBeginX()
    y0     = cBBox.getBeginY()
    for y in range(ny):
        for x in range(nx):
            ra, decl = wcs.pixelToSky(x+x0, y+y0)
            # Make ra go from -180 to +180 for ease of use
            if ra > np.pi * afwGeom.radians:
                ra = ra - 2 * np.pi * afwGeom.radians
            raIm.getArray()[y, x] = ra
            decIm.getArray()[y, x] = decl

    run = dataId["run"]
    camcol = dataId["camcol"]
    field = dataId["field"]
    filterName = dataId["filter"]
    cim.writeFits("image-%06d-%s%s-%04d.fits" % (run, filterName, camcol, field))
    mask.writeFits("mask-%06d-%s%s-%04d.fits" % (run, filterName, camcol, field))
    raIm.writeFits("ra-%06d-%s%s-%04d.fits" % (run, filterName, camcol, field))
    decIm.writeFits("dec-%06d-%s%s-%04d.fits" % (run, filterName, camcol, field))


if __name__ == "__main__":
    args = []
    dataIds = [{"run": 6474, "camcol": 5, "field": 143},
               {"run": 6484, "camcol": 5, "field": 144},
               {"run": 6504, "camcol": 5, "field": 146}]

    for dataId in dataIds:
        for filterName in ["g", "r", "i"]:
            dId = dataId.copy()
            dId["filter"] = filterName
            args.append(dId)

    print args
    if False:
        # 1 by 1
        map(doit, args)
    else:
        # In parallel; note you need to import this *after* you declare doit()
        import multiprocessing
        pool = multiprocessing.Pool(multiprocessing.cpu_count()//2)
        pool.map(doit, args)
