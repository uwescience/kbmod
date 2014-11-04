import datetime
import psycopg2
import os
import stat
import json
import pytz

class Database(object):
    def __init__(self, loadUdf=True, udfPath="/home/ec2-user/src/kbmod/src/skyToIdx.so"):
        host, database, user, password = self.__get_authentication__()
        self.conn = psycopg2.connect(host=host, user=user, password=password, database=database)
        self.cursor = self.conn.cursor()   
        if loadUdf:
            self.loadUdf(udfPath)

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
        self.cursor.execute(sql)

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
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        print results

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
        self.xp = xp
        self.yp = yp

    def eval(self, time):
        dt    = (self.p0.getTime() - time).total_seconds()
        xeval = self.p0.getX() + dt * self.xp
        yeval = self.p0.getY() + dt * self.yp
        return Point(xeval, yeval, time)

if __name__ == "__main__":
    db = Database()

    ra   = -41.1
    dec  = 0.93
    
    time1 = datetime.datetime(1999, 10, 14, 3, 49, 1, 772609, tzinfo=pytz.UTC)
    time = "1999-10-14 03:49:01.772609z"
    
    pt = Point(ra, dec, time)
    pt1 = Point(ra, dec, time1)

    db.queryPoint(pt)
    db.queryPoint(pt1)

