import os
from database import Database
import pandas as pd
import numpy as np
from convertSDSS import convert, getPath

sql = """
WITH TL AS (
    SELECT
       traj.trajId as trajId,
       traj.ra0 as ra0,
       traj.dec0 as dec0,
       traj.t0 as t0,
       traj.delta_ra as delta_ra,
       traj.delta_dec as delta_dec,
       ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM run.tmin)), 
                   ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM run.tmax))) as tline
    FROM 
       TrajectoryFixed as traj,
       Run as run
    WHERE
       run.bbox && 
       ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_dec),
                   ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_dec))
    AND
       ABS(EXTRACT(EPOCH FROM run.tmax-traj.t0)) < 2592000

  )
SELECT 
  set.setid, set.run, set.camcol, set.filter, im.positionId,
  (TL.ra0  + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_ra) as raInt, 
  (TL.dec0 + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_dec) as decInt
FROM
  Image as im,
  ImageSetSDSS as set,
  TL
WHERE
  im.bbox3d &&& TL.tline
AND
  im.setId = set.setId
;
"""

def makeRepo(results, root="./"):
    for index, row in results.iterrows():
        dataId = {"run": row["run"], "camcol": row["camcol"], "field": row["positionid"], "filter": row["filter"]}
        cexp = convert(dataId)
        outfile = getPath(dataId, root)
        if not os.path.isdir(os.path.dirname(outfile)):
           os.makedirs(os.path.dirname(outfile))
        cexp.writeFits(outfile)


if __name__ == "__main__":
    db = Database(doLoadUdf=False)
    results = db.db.query(sql)
    makeRepo(results)
