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

def getRuns(h5name="runs.h5", absRa=5):
    if not os.path.isfile(h5name):
        db      = Database(doLoadUdf=False)
        sql     = "select * from run where run>1000 order by run"
        results = db.db.query(sql)
        results.to_hdf(h5name, "df")
    else:
        results = pd.read_hdf(h5name, "df")

    # for some reason the first 2 runs (94,125) dont have camcol 4,5,6

    def draw(nframe):
        for result in results.iterrows():
            idx = result[0]
            if idx > nframe:
                break
            bbox  = ppygis.Geometry.read_ewkb(result[1]["bbox"])
            ll, lr, ul, ur = bbox.rings[0].points[:4]
            ras   = [p.x for p in (ll, lr, ul, ur, ll)]
            decs  = [p.y for p in (ll, lr, ul, ur, ll)]
            print result[1]["run"], idx, ras, decs
            cpoly   = cmapper[idx%len(cmapper)]
            ax.plot(ras, decs, lw=2, color=cpoly)
            ax.text(ras[1], decs[1]+0.05, "Run %d"%result[1]["run"], color=cpoly)
        ax.set_xlim(-60, 60)
        ax.set_ylim(-1.5, 1.5)
        ax.set_xlabel("Right Ascension", weight="bold")
        ax.set_ylabel("Declination", weight="bold")

    if 0:
        for i in range(len(results)):
            fig, ax = plt.subplots(figsize=(14,7))
            # 1 by 1
            draw(nframe)
            ax.set_xlim(-60, 60)
            ax.set_ylim(-1.5, 1.5)
            ax.set_xlabel("Right Ascension", weight="bold")
            ax.set_ylabel("Declination", weight="bold")

            fig.savefig("anim%d.png"%i)
            # OR
            #anim = animation.FuncAnimation(fig, draw, frames=arange(3, len(results)))
            #anim.save('test.gif', writer='imagemagick', fps=4)
    
    # Make 3D version showing time
    fig = plt.figure(figsize=(14,7))
    ax  = fig.gca(projection='3d')
    t0  = results.tmin[0]
    for result in results.iterrows():
        idx = result[0]
        bbox  = ppygis.Geometry.read_ewkb(result[1]["bbox"])
        ll, lr, ul, ur = bbox.rings[0].points[:4]
        ras   = [p.x for p in (ll, lr, ul, ur, ll)]
        decs  = [p.y for p in (ll, lr, ul, ur, ll)]
        dt    = (result[1].tmin - t0).total_seconds() / (365.24*24*3600)
        print result[1]["run"], idx, ras, decs
        cpoly   = cmapper[idx%len(cmapper)]
        ax.plot(ras, decs, lw=1, color=cpoly, zs=dt, alpha=0.25)

    if True:
        teval      = t0
        tmax       = result[1].tmax
        oras       = []
        odecs      = []
        ot         = []
        while teval < tmax: 
            try:
                ora, odec = getEphem(teval)
            except:
                teval += datetime.timedelta(days=30)
            else:
                oras.append(ora)
                odecs.append(odec)
                ot.append(teval)
                teval += datetime.timedelta(days=30)
        dt = [(t - t0).total_seconds() / (365.24*24*3600) for t in ot]
        plt.plot(oras, odecs, lw=2, ls="-", color="c", zs=dt)

    ax.set_xlabel('Ra (deg)', weight="bold")
    ax.set_ylabel('Dec (deg)', weight="bold")
    ax.set_zlabel('Time (years)', weight="bold")
    ax.set_xlim3d(-60, 60)
    ax.set_ylim3d(-1.5, 1.5)
    el0 = +88.0
    az0 = -90.1
    nsteps = 20

    if False:
        el1 = +1.0
        az1 = -140.0
        ax.view_init(elev=el0, azim=az0)
        plt.show()
        def rotate(n):
            el = el0 + (el1-el0)*n/nsteps
            az = az0 + (az1-az0)*n/nsteps
            ax.view_init(elev=el, azim=az)
        anim = animation.FuncAnimation(fig, rotate, frames=nsteps+1)
        anim.save('rotate1.gif', writer='imagemagick', fps=2)

    el1 = +2.0
    az1 = -94.0
    el2 = +1.0
    az2 = -177.0
    def rotate(n):
        if n < nsteps:
            el = el0 + (el1-el0)*n/nsteps
            az = az0 + (az1-az0)*n/nsteps
            ax.view_init(elev=el, azim=az)
        else:
            el = el1 + (el2-el1)*(n-nsteps)/nsteps
            az = az1 + (az2-az1)*(n-nsteps)/nsteps
        ax.view_init(elev=el, azim=az)
    anim = animation.FuncAnimation(fig, rotate, frames=2*(nsteps)+1)
    anim.save('rotate2.gif', writer='imagemagick', fps=2)




    #x.set_xlabel("Right Ascension", weight="bold")
    #ax.set_ylabel("Declination", weight="bold")
    #import pdb; pdb.set_trace()
    plt.show()

if __name__ == "__main__":
    getRuns()