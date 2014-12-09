import sys
import re
import md5
import numpy as np
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.meas.algorithms as measAlg
import lsst.daf.persistence as dafPersist
from lsst.obs.sdss import SdssMapper as Mapper
from lsst.obs.sdss import convertfpM

# In the end we really want these to be methods on a KbmodData class
def createKey(dataId):
    run        = dataId["run"]
    camcol     = dataId["camcol"]
    field      = dataId["field"]
    filterName = dataId["filter"]
    imageId    = int(md5.new(" ".join(map(str, [run, camcol, field, filterName]))).hexdigest(), 16) % 2**(64-1)

def getPath(dataId, root):
    key        = createKey(dataId)
    run        = dataId["run"]
    camcol     = dataId["camcol"]
    filterName = dataId["filter"]
    outfile    = os.path.join(root, "kbmod/%d/%d/%s/%d.fits"%(run, camcol, filterName, key)
    return outfile

def convert(dataId):
    print "# Converting", dataId
 
    # I need to create a separate instance in each thread
    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()

    # Grab science pixels
    im     = butler.get(datasetType="fpC", dataId = dataId).convertF()

    # Remove the 128 pixel duplicate overlap between fields
    # See python/lsst/obs/sdss/processCcdSdss.py for guidance
    bbox    = im.getBBox()
    begin   = bbox.getBegin()
    extent  = bbox.getDimensions()
    extent -= afwGeom.Extent2I(0, 128)
    tbbox   = afwGeom.BoxI(begin, extent)
    im      = afwImage.ImageF(im, tbbox, True)
    nx0, ny0 = extent

    # Remove 1000 count pedestal
    im    -= 1000.0 

    # Create image variance from gain
    calib, gain = butler.get(datasetType="tsField", dataId = dataId)
    var    = afwImage.ImageF(im, True)
    var   /= gain

    # Note I need to do a bit extra for the mask; I actually need to call
    # convertfpM with allPlanes = True to get all the SDSS info
    #
    # mask   = butler.get(datasetType="fpM", dataId = dataId)
    fpMFile = butler.mapper.map_fpM(dataId = dataId).getLocations()[0]
    mask    = convertfpM(fpMFile, True)
    # Remove the 128 pixel duplicate overlap...
    mask    = afwImage.MaskU(mask, tbbox, True)

    # We need this for the background estimation
    exp = afwImage.ExposureF(afwImage.MaskedImageF(im, mask, var))

    # Subtract off background, and scale by stdev
    # This will turn the image into "sigma"
    bgctrl = measAlg.BackgroundConfig(binSize=512, statisticsProperty="MEANCLIP", ignoredPixelMask=mask.getMaskPlaneDict().keys())
    bg, bgsubexp = measAlg.estimateBackground(exp, bgctrl, subtract=True)
    im = bgsubexp.getMaskedImage().getImage()
    sctrl = afwMath.StatisticsControl()
    sctrl.setAndMask(reduce(lambda x, y, mask=mask: x | mask.getPlaneBitMask(y), bgctrl.ignoredPixelMask, 0x0))
    stdev = afwMath.makeStatistics(im, mask, afwMath.STDEVCLIP, sctrl).getValue(afwMath.STDEVCLIP)
    im /= stdev

    # Additional info
    psf    = butler.get(datasetType="psField", dataId = dataId)
    wcs    = butler.get(datasetType="asTrans", dataId = dataId)

    # Decision point: do I send the convolution a MaskedImage, in which
    # case the mask is also spread, or just an Image, and not spread
    # the mask...  
    # 
    # I think for now I will not spread the mask so that it represents the
    # condition of the underlying pixels, not the Psf-filtered ones

    # Image convolved with the Psf, i.e. maximum point source likelihood image
    cim    = afwImage.ImageF(im, True)
    afwMath.convolve(cim, im, psf.getKernel(), True)

    # NOTE: DO WE SHRINK THE IMAGES HERE?  IF SO, WE NEED TO TWEAK WCS
    # For now, I will not do so
    # The pixels that are "good" in the image, i.e. ignore borders
    #cBBox  = psf.getKernel().shrinkBBox(cim.getBBox())
    #cim    = afwImage.ImageF(cim, cBBox)
    #mask   = afwImage.MaskU(mask, cBBox)

    cexp   = afwImage.ExposureF(afwImage.MaskedImageF(cim, mask, var), wcs)
    return cexp
 
if __name__ == "__main__":
    dataIds = [{"run": 6474, "camcol": 5, "field": 143},
               {"run": 6484, "camcol": 5, "field": 144},
               {"run": 6504, "camcol": 5, "field": 146}]

    args = []
    for dataId in dataIds:
        for filterName in ["g", "r", "i"]:
            dId = dataId.copy()
            dId["filter"] = filterName
            args.append(dId)

    if True:
        # 1 by 1; debugging
        map(doit, args)
    else:
        # In parallel
        import multiprocessing
        pool = multiprocessing.Pool(multiprocessing.cpu_count()//2)
        pool.map(doit, args)
