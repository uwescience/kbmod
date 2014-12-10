from kbmodData import KbmodData

# Imports to use the LSST Data Management stack to generate the Kbmod data
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.meas.algorithms as measAlg
import lsst.daf.persistence as dafPersist
from lsst.obs.sdss import SdssMapper as Mapper
from lsst.obs.sdss import convertfpM
import lsst.afw.display.ds9 as ds9

class SdssKbmodData(KbmodData):
    def __init__(self, ukeys):
        KbmodData.__init__(self, ukeys)
        
        def createLikeImage(self, data):
            print "# Converting", data
            
            # Convert from Pandas to Dictionary
            dataId = {}
            for key in self.ukeys:
                dataId[key] = data[key]
         
            # I need to create a separate butler instance in case of multi threading
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
            fpMFile = butler.mapper.map_fpM(dataId = dataId).getLocations()[0]
            mask    = convertfpM(fpMFile, True)

            # Remove the 128 pixel duplicate overlap...
            mask    = afwImage.MaskU(mask, tbbox, True)

            # Convert to Exposure for the background estimation
            exp = afwImage.ExposureF(afwImage.MaskedImageF(im, mask, var))

            # Subtract off background, and scale by stdev.  
            # This will turn the image into a "sigma" image
            bgctrl = measAlg.BackgroundConfig(binSize=512, statisticsProperty="MEANCLIP", ignoredPixelMask=mask.getMaskPlaneDict().keys())
            bg, bgsubexp = measAlg.estimateBackground(exp, bgctrl, subtract=True)
            im = bgsubexp.getMaskedImage().getImage()
            sctrl = afwMath.StatisticsControl()
            sctrl.setAndMask(reduce(lambda x, y, mask=mask: x | mask.getPlaneBitMask(y), bgctrl.ignoredPixelMask, 0x0))
            stdev = afwMath.makeStatistics(im, mask, afwMath.STDEVCLIP, sctrl).getValue(afwMath.STDEVCLIP)
            im /= stdev

            # Grab the Psf for filtering, and the Wcs for inclusion in final Exposure
            psf    = butler.get(datasetType="psField", dataId = dataId)
            wcs    = butler.get(datasetType="asTrans", dataId = dataId)

            # Decision point: do I send the convolution a MaskedImage, in which
            # case the mask is also spread, or just an Image, and not spread
            # the mask...  
            # 
            # I think for now I will not spread the mask so that it represents the
            # condition of the underlying pixels, not the Psf-filtered ones
            #
            # Create sigma image convolved with the Psf, i.e. maximum point source likelihood image
            cim    = afwImage.ImageF(im, True)
            afwMath.convolve(cim, im, psf.getKernel(), True)

            # Note that the convolution will create border regions of "bad" pixels.
            # If we tried to trim these, we would have to tweak the Wcs CRPIX etc.  So just leave as-is.
            cexp   = afwImage.ExposureF(afwImage.MaskedImageF(cim, mask, var))
            cexp.setWcs(wcs)
            return cexp
 
