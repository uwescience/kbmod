import datetime
import os
import stat
import json
import pytz
from db import DB
import numpy as np
import pandas as pd

class Database(object):
    def __init__(self, doLoadUdf=True, udfPath="/home/ec2-user/src/kbmod/src/skyToIdx.so"):
        host, database, user, password = self.__get_authentication__()
        self.db = DB(hostname=host, username=user, password=password, dbname=database, dbtype="postgres")
        if doLoadUdf:
            self.loadUdf(udfPath)
        self.times = self.getTimes()


    def __get_authentication__(self, authdir=".kbmod", authfile="db-auth.json"):
        authfile = os.path.join(os.environ["HOME"], authdir, authfile)
        if not os.path.isfile(authfile):
            print "Database authentication file %s does not exist, unable to proceed"
            raise IOError
        st = os.stat(authfile)
        if st.st_mode & (stat.S_IRWXO |  stat.S_IRWXG):
            print "File permissions on %s allow group/other access"
            raise PermissionError    
        jsonData = json.load(open(authfile, "r"))
        try:
            host = jsonData["host"]
            database = jsonData["database"]
            user = jsonData["user"]
            password = jsonData["password"]
        except:
            raise KeyError
        return host, database, user, password

    def loadUdf(self, udfPath):
        sql = """
        CREATE OR REPLACE FUNCTION c_skyToIdx(wcs, double precision, double precision) RETURNS integer
            AS '%s', 'c_skyToIdx'
            LANGUAGE C STRICT;
            """ % (udfPath)
        self.db.cur.execute(sql)

    def getTimes(self):
        sql = """SELECT tmid FROM fields"""
        return self.db.query(sql)

    def queryPoint(self, point):
        sql = """
        SELECT p.pixelId, p.pidx, p.fval
        FROM
            ST_SetSRID(ST_MakePoint(%f, %f),3786) as traj,
            pixels3 as p,
            fields as f,
            wcs as w,
            c_skyToIdx(w, %f, %f) as idx
        WHERE
            TIMESTAMP WITH TIME ZONE '%s' <@ f.trange
        AND
            ST_INTERSECTS(traj, f.bbox)
        AND
            f.fieldId = w.fieldId
        AND
            f.fieldId = p.fieldId
        AND
            p.pidx = idx;
        """ % (point.getX(), point.getY(), point.getX(), point.getY(), point.getTimeString())
        print sql
        results = self.db.query(sql)
        return results

class Point(object):
    def __init__(self, x, y, time):
        self.x    = x
        self.y    = y
        self.time = time

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def getTime(self):
        return self.time

    def getTimeString(self):
        if isinstance(self.time, str):
            return self.time
        if isinstance(self.time, datetime.datetime):
            return self.time.__str__()

class LinearTrajectory(object):
    def __init__(self, x0, y0, t0, xp, yp):
        self.p0 = Point(x0, y0, t0)
        self.xp = xp # In (units of x) / second
        self.yp = yp

    def eval(self, time):
        dt    = (self.p0.getTime() - time).total_seconds()
        xeval = self.p0.getX() + dt * self.xp
        yeval = self.p0.getY() + dt * self.yp
        return Point(xeval, yeval, time)

class K06Sb2Q(LinearTrajectory):
    def __init__(self, times):
        self.known = """
        K06Sb2Q  C2006 09 27.12671 21 09 20.29 +01 09 36.0          21.5 r      645
        K06Sb2Q  C2006 09 27.12754 21 09 20.29 +01 09 35.9          21.4 i      645
        K06Sb2Q  C2006 09 27.13003 21 09 20.28 +01 09 35.8          22.6 g      645

        K06Sb2Q  C2006 09 29.13924 21 09 13.81 +01 07 42.7          21.4 r      645
        K06Sb2Q  C2006 09 29.14006 21 09 13.83 +01 07 42.7          21.2 i      645
        K06Sb2Q  C2006 09 29.14255 21 09 13.81 +01 07 42.6          22.6 g      645

        K06Sb2Q  C2006 10 01.13632 21 09 07.93 +01 05 51.0          21.5 r      705
        K06Sb2Q  C2006 10 01.13964 21 09 07.89 +01 05 50.6          22.2 g      705

        K06Sb2Q  C2006 10 03.20084 21 09 02.39 +01 03 55.9          21.6 r      645
        K06Sb2Q  C2006 10 03.20166 21 09 02.39 +01 03 56.0          21.6 i      645
        """
        r0 = Point(*(self.parseMpc("K06Sb2Q  C2006 09 27.12671 21 09 20.29 +01 09 36.0          21.5 r      645")))
        r1 = Point(*(self.parseMpc("K06Sb2Q  C2006 09 29.13924 21 09 13.81 +01 07 42.7          21.4 r      645")))
        r2 = Point(*(self.parseMpc("K06Sb2Q  C2006 10 01.13632 21 09 07.93 +01 05 51.0          21.5 r      705")))
        r3 = Point(*(self.parseMpc("K06Sb2Q  C2006 10 03.20084 21 09 02.39 +01 03 55.9          21.6 r      645")))
        xp, yp = self.getLinearMotion((r0, r1, r2, r3))

        # Find the database time closest to the above time, and use this to start the trajectory
        idx = np.argmin(np.abs((r0.getTime() - times).values))
        self.p0 = Point(r0.getX(), r0.getY(), times.values[idx][0])
        self.xp = xp
        self.yp = yp

    def getLinearMotion(self, points):
        dt = np.empty(len(points)-1)
        dx = np.empty(len(points)-1)
        dy = np.empty(len(points)-1)

        t0 = points[0].getTime()
        x0 = points[0].getX()
        y0 = points[0].getY()
        for i, p in enumerate(points[1:]):
            dt[i] = (p.getTime()-t0).total_seconds()
            dx[i] = p.getX() - x0
            dy[i] = p.getY() - y0
        xp = np.mean(dx/dt)
        yp = np.mean(dy/dt)
        return xp, yp

    def parseMpc(self, mpc):
        fields = mpc.split()
        year   = int(fields[1][1:])
        month  = int(fields[2])
        fday   = float(fields[3])
        day    = int(fday)
        fday  -= day
        hour   = int(fday * 24)
        fday  -= hour / 24.
        min    = int(fday * 60)
        fday  -= min / 60.
        sec    = int(fday * 3600)
        fday  -= sec / 3600.
        msec   = int(fday * 1e6)
        time   = datetime.datetime(year, month, day, hour, min, sec, msec, tzinfo=pytz.UTC)

        rdeg   = int(fields[4])
        rmin   = int(fields[5])
        rsec   = float(fields[6])
        ra     = (rdeg + rmin/60. + rsec/3600.) * 15
        if ra > 180: 
            ra -= 360

        dsign  = fields[7][0]
        ddeg   = int(fields[7][1:])
        dmin   = int(fields[8])
        dsec   = float(fields[9])
        dec    = ddeg + dmin/60. + dsec/3600.
        if dsign == "-": dec *= -1

        return ra, dec, time

if __name__ == "__main__":
    db = Database()

    ra   = -41.1
    dec  = 0.93
    
    time1 = datetime.datetime(1999, 10, 14, 3, 49, 1, 772609, tzinfo=pytz.UTC)
    time = "1999-10-14 03:49:01.772609z"
    
    pt = Point(ra, dec, time)
    pt1 = Point(ra, dec, time1)

    print db.queryPoint(pt)
    print db.queryPoint(pt1)
    testTraj = K06Sb2Q(db.times)
    print db.queryPoint(testTraj.p0)
