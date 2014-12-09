from database import Database
import time
import matplotlib.pyplot as plt
import numpy as np


def reset(db, npts):
    sql = "DROP TABLE IF EXISTS trajectory;"
    db.db.cur.execute(sql)

    sql = """
    CREATE TABLE Trajectory (
        trajId    BIGSERIAL PRIMARY KEY,                                                                                    
        t0        TIMESTAMP WITH TIME ZONE,
        ra0       DOUBLE PRECISION,
        dec0      DOUBLE PRECISION,
        delta_ra  DOUBLE PRECISION,
        delta_dec DOUBLE PRECISION
        ); 
    """
    db.db.cur.execute(sql)

    sql = """
    INSERT INTO Trajectory (t0, ra0, dec0, delta_ra, delta_dec) 
    (SELECT tmid, st_x(ST_Centroid(bbox)), st_y(ST_Centroid(bbox)), 7.7e-8, 7.7e-8 FROM IMAGE ORDER BY RANDOM() LIMIT %d); 
    """%(npts)
    db.db.cur.execute(sql)

    sql = "COMMIT;"      
    db.db.cur.execute(sql)

db = Database(doLoadUdf=False)

sql2A = """
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
       Trajectory as traj,
       Run as run
    WHERE
       ABS(EXTRACT(EPOCH FROM run.tmax-traj.t0)) < 2592000
  )
SELECT 
  im.imageId, TL.trajId,
  (TL.ra0  + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_ra) as raInt, 
  (TL.dec0 + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_dec) as decInt
FROM
  Image as im,
  TL
WHERE
  im.bbox3d &&& TL.tline
;
"""

sql2B = """
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
       Trajectory as traj,
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
  im.imageId, TL.trajId,
  (TL.ra0  + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_ra) as raInt, 
  (TL.dec0 + EXTRACT(EPOCH FROM im.tmid-TL.t0) * TL.delta_dec) as decInt
FROM
  Image as im,
  TL
WHERE
  im.bbox3d &&& TL.tline
;
"""

for npts in (1, 5, 10, 50, 100):
    dt2As = []
    dt2Bs = []
    for i in range(10):
        reset(db, npts); t0 = time.time(); r2A = db.db.query(sql2A); dt2A = time.time() - t0
        reset(db, npts); t0 = time.time(); r2B = db.db.query(sql2B); dt2B = time.time() - t0
        dt2As.append(dt2A)
        dt2Bs.append(dt2B)
    print npts, "%.3f +/- %.3f   %.3f +/- %.3f" % (
      np.median(dt2As), 0.741*(np.percentile(dt2As, 75)-np.percentile(dt2As, 25)),
      np.median(dt2Bs), 0.741*(np.percentile(dt2Bs, 75)-np.percentile(dt2Bs, 25)))


