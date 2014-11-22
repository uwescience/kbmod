import os
import stat
import json
from db import DB

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
            host = jsonData["kbmod"]["host"]
            database = jsonData["kbmod"]["database"]
            user = jsonData["kbmod"]["user"]
            password = jsonData["kbmod"]["password"]
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
