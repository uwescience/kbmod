import urllib2

import psycopg2
import ppygis

from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection
import matplotlib.pyplot as plt

import datetime
import pytz
JDOFFSET = 2400000.5
MJD0 = datetime.datetime(1858, 11, 17, 0, 0, 0, 0, tzinfo=pytz.UTC)

conn = psycopg2.connect(host='54.191.82.210', user='postgres', password='kbmod', database='kbmod')
cursor = conn.cursor()
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

def getFields():
    sql = "select run, bbox, tmid from fields;"
    cursor.execute(sql)
    results = cursor.fetchall()

    fig = plt.figure()
    ax = fig.gca(projection='3d')

    verts  = []
    ts     = []
    runs   = []
    for result in results:
        run            = result[0]
        bbox           = ppygis.Geometry.read_ewkb(result[1])
        ll, lr, ul, ur = bbox.rings[0].points[:4]
        tmid           = result[2]
        if tmid.year < 2001:
            continue
        if ll.x > -40: 
            continue

        print tmid, tmid.year, bbox

        ras            = [p.x for p in [ll, lr, ul, ur, ll]]
        decs           = [p.y for p in [ll, lr, ul, ur, ll]]
        verts.append(zip(ras,decs))
        ts.append(tmid)
        runs.append(run)


    uruns   = list(set(runs))
    cpoly   = [cmapper[c] for c in [uruns.index(r)%len(cmapper) for r in runs]]
    toffset = [(t-ts[0]).total_seconds() for t in ts]

    tmin = min(ts)
    tmax = max(ts)
    orbra  = []
    orbdec = []
    orbt   = []
    teval  = tmin
    while teval < tmax:
        try:
            ora, ordec = getEphem(teval)
            #print teval, ora, ordec
        except:
            teval += datetime.timedelta(days=30)
        else:
            orbra.append(ora)
            orbdec.append(ordec)
            orbt.append(teval)
            teval += datetime.timedelta(days=30)

    poly = PolyCollection(verts, facecolors=cpoly)
    poly.set_alpha(0.25)
    ax.add_collection3d(poly, zs=toffset)
    ax.set_xlabel('Ra', weight="bold")
    ax.set_ylabel('Dec', weight="bold")
    ax.set_zlabel('Time', weight="bold")

    ax.set_xlim3d(-45, -40)
    ax.set_ylim3d(-1, 1)
    ax.set_zlim3d(0, max(toffset))
    ax.plot(orbra, orbdec, [(t-ts[0]).total_seconds() for t in orbt], "ro-")
    plt.show()

if __name__ == "__main__":
    getFields()