from database import Database
import os, sys
import ppygis
import pandas as pd
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import datetime
import urllib2

import pytz
JDOFFSET = 2400000.5
MJD0 = datetime.datetime(1858, 11, 17, 0, 0, 0, 0, tzinfo=pytz.UTC)

import seaborn as sns
sns.set_style("ticks")
sns.set_context("talk")

cmapper = ["r", "g", "b", "m", "k"]
db      = Database(doLoadUdf=False)

def getFields(h5name="runs.h5", absRa=5):
    if not os.path.isfile(h5name):
        sql     = "select * from run where run>1000 order by run"
        results = db.db.query(sql)
        results.to_hdf(h5name, "df")
    else:
        results = pd.read_hdf(h5name, "df")

    # for some reason the first 2 runs (94,125) dont have camcol 4,5,6

    def draw():
        for result in results.iterrows():
            idx = result[0]
            run = result[1].run

            sql = "select s.run, i.bbox from imagesetsdss as s, image as i where i.setid=s.setid and s.run=%d"%(run)
            results2 = db.db.query(sql)

            # Run bbox
            bbox  = ppygis.Geometry.read_ewkb(result[1]["bbox"])
            ll, lr, ul, ur = bbox.rings[0].points[:4]
            ras   = [p.x for p in (ll, lr, ul, ur, ll)]
            decs  = [p.y for p in (ll, lr, ul, ur, ll)]
            print result[1]["run"], idx, ras, decs
            cpoly   = cmapper[idx%len(cmapper)]
            ax.plot(ras, decs, lw=2, color=cpoly)
            ax.text(ras[1], decs[1]+0.05, "Run %d"%result[1]["run"], color=cpoly)

            # Image bbox
            polys = []
            for r2 in results2.iterrows():
                idx2   = r2[0]
                bbox2  = ppygis.Geometry.read_ewkb(r2[1]["bbox"])
                ll2, lr2, ul2, ur2 = bbox2.rings[0].points[:4]
                ras2   = [p.x for p in (ll2, lr2, ul2, ur2, ll2)]
                decs2  = [p.y for p in (ll2, lr2, ul2, ur2, ll2)]
                polys.append(zip(ras2, decs2))
            polyc = PolyCollection(polys)
            ax.add_collection(polyc)
            break # just plot first run

    fig, ax = plt.subplots(figsize=(14,7))
    draw()
    ax.set_xlim(-10, -6)
    ax.set_ylim(-1.1, 1.4)
    ax.set_xlabel("Right Ascension", weight="bold")
    ax.set_ylabel("Declination", weight="bold")

    plt.show()

if __name__ == "__main__":
    getFields()