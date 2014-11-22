import MySQLdb
import os
import json
import datetime
import dateutil.parser
import md5
import numpy as np

def getCursor():
    authdir  = ".kbmod"
    authfile = "db-auth.json"
    authfile = os.path.join(os.environ["HOME"], authdir, authfile)
    jsonData = json.load(open(authfile, "r"))            
    host     = jsonData["ncsa-lsst"]["host"]
    user     = jsonData["ncsa-lsst"]["user"]
    password = jsonData["ncsa-lsst"]["password"]
    port     = jsonData["ncsa-lsst"]["port"]
    database = "DC_W13_Stripe82"
    db = MySQLdb.connect(host=host, user=user, passwd=password, db=database, port=port)
    cursor = db.cursor()
    return cursor

def makeSetHash(run, camcol, filterName):
    return int(md5.new(" ".join(map(str, [run, camcol, filterName]))).hexdigest(), 16) % 2**(32-1)

def makeImageHash(run, camcol, position, filterName):
    return int(md5.new(" ".join(map(str, [run, camcol, position, filterName]))).hexdigest(), 16) % 2**(64-1)

def makeImageSet(cursor):
    sqlIn = """
    SELECT
        run, camcol, filterName,
        min(expMidpt) as tMin,
        max(expMidpt) as tMax,
        min(IF(corner1Ra>180,corner1Ra-360,corner1Ra)) as raMin,
        max(IF(corner3Ra>180,corner3Ra-360,corner3Ra)) as raMax,
        min(corner1Decl) as decMin,
        max(corner3Decl) as decMax
    FROM
        Science_Ccd_Exposure
    GROUP BY
        run, camcol, filterName
    ORDER BY
        run, camcol, filterName;
    """
    cursor.execute(sqlIn)
    results = cursor.fetchall()
    
    halfexp = datetime.timedelta(seconds=0.5*53.9075) 
    sqlOut = "INSERT INTO ImageSetSDSS (setId, run, camcol, filter, bbox, trange) VALUES\n"
    for result in results:
        run, camcol, filterName, tMin, tMax, raMin, raMax, decMin, decMax = result
        tMin   = dateutil.parser.parse(tMin)
        tMax   = dateutil.parser.parse(tMax)
        tMin  -= halfexp
        tMax  += halfexp
        bbox   = "ST_GeomFromText('POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))',3786)"%(
            raMin, decMin, raMax, decMin, raMax, decMax, raMin, decMax, raMin, decMin)
        trange = "[%s, %s]" % (tMin, tMax)
        setId  = makeSetHash(run, camcol, filterName)
        sqlOut += "  (%d, %d, %d, '%s', %s, '%s'),\n" % (setId, run, camcol, filterName, bbox, trange)
    sqlOut = sqlOut[:-2]+"\n;"
    return sqlOut

def makeImage(cursor):
    sqlIn = """
    SELECT
        run, camcol, field, filterName, expMidpt, 
        IF(corner1Ra>180,corner1Ra-360,corner1Ra) as raMin,
        IF(corner3Ra>180,corner3Ra-360,corner3Ra) as raMax,
        corner1Decl as decMin,
        corner3Decl as decMax
    FROM
        Science_Ccd_Exposure
    ORDER BY
        run, camcol, field, filterName;
    """
    cursor.execute(sqlIn)
    results = cursor.fetchall()

    halfexp = datetime.timedelta(seconds=0.5*53.9075) 

    aruns = np.array([x[0] for x in results])
    uruns = list(set(aruns))
    uruns.sort()
    output = {}
    for urun in uruns:
        idx = np.where(aruns==urun)[0]
        sqlOut = "BEGIN TRANSACTION;\nINSERT INTO Image (imageId, setId, positionId, bbox, tmid, trange) VALUES\n"
        for i in idx:
            result = results[i]
            run, camcol, position, filterName, tMid, raMin, raMax, decMin, decMax = result
            setId  = makeSetHash(run, camcol, filterName)
            imageId = makeImageHash(run, camcol, position, filterName)
            tMid = dateutil.parser.parse(tMid)
            tMin = tMid - halfexp
            tMax = tMid + halfexp
            bbox   = "ST_GeomFromText('POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))',3786)"%(
                raMin, decMin, raMax, decMin, raMax, decMax, raMin, decMax, raMin, decMin)
            trange = "[%s, %s]" % (tMin, tMax)
            sqlOut += "  (%d, %d, %d, %s, '%s', '%s'),\n" % (imageId, setId, position, bbox, tMid, trange)
        sqlOut = sqlOut[:-2]+";\nCOMMIT;\n"
        output[urun] = sqlOut
    return output

if __name__ == "__main__":
    cursor = getCursor()    
    sqlSet = makeImageSet(cursor)
    open("v2_imageset.sql", "w").write(sqlSet)

    sqlIms = makeImage(cursor)
    for key, value in sqlIms.items():
        open("v2_image_%d.sql"%key, "w").write(value)
