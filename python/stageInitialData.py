import sys
import numpy as np
import time
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.daf.persistence as dafPersist
from lsst.obs.sdss import SdssMapper as Mapper
from lsst.obs.sdss import convertfpM

doWriteSql = True
doc = """Generate an initial set of test-data for KB-MOD"""

def getRaDecl(wcs, x, y):
    ra, decl = wcs.pixelToSky(x+x0, y+y0)
    # Make ra go from -180 to +180 for ease of use
    if ra > np.pi * afwGeom.radians:
        ra = ra - 2 * np.pi * afwGeom.radians
    return ra, decl
    
def doit(args):
    dataId = args
    print "# Running", dataId
 
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
    x1     = cBBox.getEndX()
    y1     = cBBox.getEndY()
    for y in range(ny):
        for x in range(nx):
            ra, decl = getRaDecl(wcs, x+x0, y+y0)
            raIm.getArray()[y, x] = ra
            decIm.getArray()[y, x] = decl

    # TODO: subtract off background, and scale by afwMath.makeStatistics(image, math::STDEVCLIP);
    # This will turn the image into "sigma"
    import pdb; pdb.set_trace()
    ctrl = afwMath.StatisticsControl(5.0, 5)
    stat = afwMath.makeStatistics(im, mask, afwMath.STDEVCLIP | afwMath.MEDIAN | afwMath.NPOINTS)
    idx  = np.where(mask.getArray() == 0)

    run = dataId["run"]
    camcol = dataId["camcol"]
    field = dataId["field"]
    filterName = dataId["filter"]
    if doWriteSql:
        # Make the table inputs
        xll, yll = getRaDecl(wcs, 0 +x0, 0+ y0)
        xlr, ylr = getRaDecl(wcs, x1+x0, 0+ y0)
        xur, yur = getRaDecl(wcs, x1+x0, y1+y0)
        xul, yul = getRaDecl(wcs, 0 +x0, y1+y0)

        pfile = "pixel-%06d-%s%s-%04d.pgsql" % (run, filterName, camcol, field))
        ffile = "field-%06d-%s%s-%04d.pgsql" % (run, filterName, camcol, field))
        pbuff = open(pfile, "w")
        fbuff = open(ffile, "w")
        fbuff.write("INSERT INTO fields (fieldId, run, camcol, field, filter, bbox, tmid, trange) VALUES\n")
        fbuff.write("(%d, %d, %d, %d, '%d', ST_GeomFromText('POLYGON((\n" % (fieldId, run, camcol, field, filterName))
        fbuff.write("        %.6f %.6f, %.6f %.6f,\n" % (xll, yll, xlr, ylr))
        fbuff.write("        %.6f %.6f, %.6f %.6f,\n" % (xur, yur, xul, yul))
        fbuff.write("        %.6f %.6f, %.6f %.6f))',4326),\n" % (xll, yll))
        fbuff.write("         '2010-01-01 14:30:30',\n"
        fbuff.write("         '[2010-01-01 14:30:00, 2010-01-01 14:31:01]');\n"
        pbuff.write("INSERT INTO pixels (fieldId, flux, mask) VALUES\n")
        for y in range(ny):
            for x in range(nx):
                if y==ny-1 and x==nx-1:
                    suffix = ""
                else:
                    suffix = ","
                pbuff.write("(%d, ST_MakePointM(-71.1043443253471, 42.3150676015829, 11.0), 128)%s\n" % (
                    fieldId, raIm[y,x], declIm[y,x], cim[y,x], mask[y,x], suffix))
        pbuff.close()
        fbuff.close()
    else:
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
    if True:
        # 1 by 1
        map(doit, args)
    else:
        # In parallel; note you need to import this *after* you declare doit()
        import multiprocessing
        pool = multiprocessing.Pool(multiprocessing.cpu_count()//2)
        pool.map(doit, args)
