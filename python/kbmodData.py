import os
import md5
import pandas as pd
import numpy as np

class KbmodData(object):
    def __init__(self, ukeys):
        self.ukeys = ukeys

    def createMd5Key(self, data, bits=64):
        return int(md5.new(" ".join(map(str, [data[key] for key in self.ukeys]))).hexdigest(), 16) % 2**(bits-1)

    def likeImagePath(self, data, rootDir="./kbmod"):
        md5key = self.createKey(data)
        subdirs = "/".join(map(str, [data[key] for key in self.ukeys]))
        outfile = os.path.join(root, subdirs, "%d.fits"%(md5key))

    def createLikeImage(self, data):
        """ Must override """
        raise NotImplementedError("User must override createLikeImage method")

    def writeLikeImage(self, data, image):
        outfile = likeImagePath(data)
        dirname = os.path.dirname(outfile)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        image.writeFits(outfile)
