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

sql1A = """
WITH TL AS (
    SELECT
       set.setId as setId,
       traj.trajId as trajId,
       ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM LOWER(set.trange))), 
                   ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM UPPER(set.trange)))) as tline
    FROM 
       Trajectory as traj,
       ImageSetSDSS as set
  )
SELECT 
  im.imageId, TL.setId, TL.trajId
FROM
  Image as im,
  TL
WHERE
  im.bbox3d &&& TL.tline
AND
  im.setId = TL.setId
;
"""

sql1B = """
WITH TL AS (
    SELECT
       set.setId as setId,
       traj.trajId as trajId,
       ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM LOWER(set.trange))), 
                   ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM UPPER(set.trange)))) as tline
    FROM 
       Trajectory as traj,
       ImageSetSDSS as set
    WHERE
        set.bbox && 
        ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_ra, 
                                 traj.dec0 + EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) * traj.delta_dec),
                    ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_ra, 
                                 traj.dec0 + EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) * traj.delta_dec))
  )
SELECT 
  im.imageId, TL.trajId
FROM
  Image as im,
  TL
WHERE
  im.bbox3d &&& TL.tline
AND
  im.setId = TL.setId
;
"""

sql2A = """
WITH TL AS (
    SELECT
       traj.trajId as trajId,
       ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmin-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM run.tmin)), 
                   ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_ra, 
                                traj.dec0 + EXTRACT(EPOCH FROM run.tmax-traj.t0) * traj.delta_dec,
                                EXTRACT(EPOCH FROM run.tmax))) as tline
    FROM 
       Trajectory as traj,
       Run as run
  )
SELECT 
  im.imageId, TL.trajId
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
  )
SELECT 
  im.imageId, TL.trajId
FROM
  Image as im,
  TL
WHERE
  im.bbox3d &&& TL.tline
;
"""

for npts in (500, 1000, 5000):
    dt1As = []
    dt1Bs = []
    dt2As = []
    dt2Bs = []
    for i in range(10):
        #reset(db, npts); t0 = time.time(); r1A = db.db.query(sql1A); dt1A = time.time() - t0
        #reset(db, npts); t0 = time.time(); r1B = db.db.query(sql1B); dt1B = time.time() - t0
        dt1A=1
        dt1B=1
        reset(db, npts); t0 = time.time(); r2A = db.db.query(sql2A); dt2A = time.time() - t0
        reset(db, npts); t0 = time.time(); r2B = db.db.query(sql2B); dt2B = time.time() - t0
        dt1As.append(dt1A)
        dt1Bs.append(dt1B)
        dt2As.append(dt2A)
        dt2Bs.append(dt2B)
    print npts, "%.3f +/- %.3f   %.3f +/- %.3f    %.3f +/- %.3f   %.3f +/- %.3f" % (
      np.median(dt1As), 0.741*(np.percentile(dt1As, 75)-np.percentile(dt1As, 25)),
      np.median(dt1Bs), 0.741*(np.percentile(dt1Bs, 75)-np.percentile(dt1Bs, 25)),
      np.median(dt2As), 0.741*(np.percentile(dt2As, 75)-np.percentile(dt2As, 25)),
      np.median(dt2Bs), 0.741*(np.percentile(dt2Bs, 75)-np.percentile(dt2Bs, 25)))


