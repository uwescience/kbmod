import sys
import lsst.afw.image as afwImage
import lsst.daf.persistence as dafPersist
from lsst.obs.sdss import SdssMapper as Mapper

doc = """Generate an initial set of test-data for KB-MOD"""

if __name__ == "__main__":
    dataIds = [{"visit": 6474, "camcol": 5, "field": 143},
               {"visit": 6484, "camcol": 5, "field": 144},
               {"visit": 6504, "camcol": 5, "field": 146}]

    mapper = Mapper(root = "/lsst7/stripe82/dr7/runs/", calibRoot = None, outputRoot = None)
    butler = dafPersist.ButlerFactory(mapper = mapper).create()
    for dataId in dataIds:
        for filterName in ["g", "r", "i"]:
            dataId["filter"] = filterName
            calexp = butler.get(datasetType="calexp", dataId = dataId)
            mi     = calexp.getMaskedImage()
            psf    = calexp.getPsf()
            wcs    = calexp.getWcs()

            cim    = afwImage.MaskedImageF(mi, True)
            afwMath.convolve(cim, mi, psf.getKernel(), True)
