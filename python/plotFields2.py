from database import Database
import os
import ppygis
import urllib2
import pandas as pd
import numpy as np

from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection
import matplotlib.pyplot as plt

import datetime
import pytz
JDOFFSET = 2400000.5
MJD0 = datetime.datetime(1858, 11, 17, 0, 0, 0, 0, tzinfo=pytz.UTC)
cmapper = ["r", "g", "b", "m", "k"]

import seaborn as sns
sns.set_style("ticks")

SECINYEAR = 365.242 * 24 * 60 * 60

def getEphem(tmid, name="308933"):
    delta = tmid - MJD0
    jd = JDOFFSET + (delta.days + (delta.seconds + delta.microseconds / 1.e6) / 86400.)

    url  = "http://ssd.jpl.nasa.gov/horizons_batch.cgi?batch=1&COMMAND=\'%s\'&MAKE_EPHEM=\'YES\'&OBJ_DATA=\'NO\'" % (name)
    url += "&CENTER=\'645\'&ANG_FORMAT=\'DEG\'&EXTRA_PREC=\'YES\'"
    url += "&TABLE_TYPE=\'OBSERVER\'&TLIST=\'%f\'" % (jd)
    url += "&QUANTITIES=\'1\'&CSV_FORMAT=\'NO\'"
    #print url

    search = urllib2.urlopen(url)
    page   = search.read()
    lines = page.split('\n')
    for l in range(len(lines)):
        if lines[l].startswith('$$SOE'):
            hresults = lines[l+1]
            break
    fields = hresults.split()
    ra = float(fields[-2])
    if ra > 180:
        ra -= 360.
    decl = float(fields[-1])
    return ra, decl

def getFields(h5name="fields.h5", absRa=5):
    if not os.path.isfile(h5name):
        db      = Database(doLoadUdf=False)
        sql     = "select s.run, i.bbox, i.tmid from imagesetsdss as s, image as i where i.setid=s.setid"
        results = db.db.query(sql)
        results.to_hdf(h5name, "df")
    else:
        results = pd.read_hdf(h5name, "df")

    t0      = min(results["tmid"])
    uruns   = list(set(results["run"]))
    uruns.sort()
    uruns   = uruns[2:]

    tmidsAll = []
    polysAll = []
    for run in uruns:
        dframe = results[results["run"] == run]
        bboxes = [ppygis.Geometry.read_ewkb(f) for f in dframe["bbox"].values]
        tmids  = [f for f in dframe["tmid"].values]
        verts  = [b.rings[0].points[:4] for b in bboxes]
        polys  = []
        tmids2 = []
        for i, v in enumerate(verts):
            ll, lr, ul, ur = v
            ras  = [p.x for p in [ll, lr, ul, ur, ll]]
            decs = [p.y for p in [ll, lr, ul, ur, ll]]
            if min(ras)<-1*absRa or max(ras)>absRa:
                continue
            polys.append(zip(ras, decs))
            tmids2.append(tmids[i])
        tmidsAll.append(tmids2)
        polysAll.append(polys)

    tmax = (max(tmids) - t0).total_seconds() / SECINYEAR
    for i, run in enumerate(uruns):
        if len(tmidsAll[i]) == 0:
            continue
        print "#", run
        fig = plt.figure()
        ax  = fig.gca(projection='3d')

        for j in range(i+1):
            cpoly   = cmapper[uruns.index(uruns[j])%len(cmapper)]
            toffset = [(t-t0).total_seconds()/SECINYEAR for t in tmidsAll[j]]
            poly    = PolyCollection(polysAll[j], facecolors=cpoly, edgecolors=None)
            poly.set_alpha(0.25)
            ax.add_collection3d(poly, zs=toffset)

        ax.set_xlabel('Ra (deg)', weight="bold")
        ax.set_ylabel('Dec (deg)', weight="bold")
        ax.set_zlabel('Time (year)', weight="bold")
        ax.set_xlim3d(-1*absRa, absRa)
        ax.set_ylim3d(-1, 1)
        ax.set_zlim3d(0, tmax)
#        ax.view_init(elev=40., azim=-130)
        ax.view_init(elev=32., azim=-134)
        ax.dist=10
        plt.show()

if __name__ == "__main__":
    getFields()