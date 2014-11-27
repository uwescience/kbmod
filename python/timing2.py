from database import Database
import time
import matplotlib.pyplot as plt
import numpy as np


def reset(db, npts):
    sql = "DROP TABLE IF EXISTS trajectory;"
    print sql

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
    print sql

    sql = """
    INSERT INTO Trajectory (t0, ra0, dec0, delta_ra, delta_dec) 
    (SELECT tmid, st_x(ST_Centroid(bbox)), st_y(ST_Centroid(bbox)), 7.7e-8, 7.7e-8 FROM IMAGE ORDER BY RANDOM() LIMIT %d); 
    """%(npts)
    print sql

    #sql = "COMMIT;"      
    #print sql;

sql1 = """
SELECT
  im.imageId, traj.trajId
FROM
  Trajectory as traj,
  ImageSetSDSS as set,
  Image as im,
  EXTRACT(EPOCH FROM LOWER(set.trange)-traj.t0) as set_dt0,
  EXTRACT(EPOCH FROM UPPER(set.trange)-traj.t0) as set_dt1,
  EXTRACT(EPOCH FROM im.tmid-traj.t0) as im_dt
WHERE
  im.setId = set.setId
AND
  ST_INTERSECTS(ST_SetSRID(ST_MakePoint((traj.ra0  + set_dt0 * traj.delta_ra), (traj.dec0 + set_dt0 * traj.delta_dec)),3786), set.bbox)
AND
  ST_INTERSECTS(ST_SetSRID(ST_MakePoint((traj.ra0  + set_dt1 * traj.delta_ra), (traj.dec0 + set_dt1 * traj.delta_dec)),3786), set.bbox)
AND
  ST_INTERSECTS(ST_SetSRID(ST_MakePoint((traj.ra0  + im_dt * traj.delta_ra),   (traj.dec0 + im_dt * traj.delta_dec)),3786), im.bbox)
;
"""

sql2 = """
WITH TL AS (
    WITH T AS (
      SELECT runs.run as run,
             traj.trajId as trajId,
             traj.ra0 as ra0,
             traj.dec0 as dec0,
             traj.delta_ra as delta_ra,
             traj.delta_dec as delta_dec,
             EXTRACT(EPOCH FROM runs.tmin-traj.t0) as trun0,
             EXTRACT(EPOCH FROM runs.tmax-traj.t0) as trun1
      FROM
             Trajectory as traj,
             Runs as runs
      ) 
    SELECT
       T.run as run,
       T.trajId as trajId,
       ST_SetSRID(ST_MakeLine(ARRAY[ST_MakePoint(T.ra0  + T.trun0 * T.delta_ra, 
                                                 T.dec0 + T.trun0 * T.delta_dec), 
                                    ST_MakePoint(T.ra0  + T.trun1 * T.delta_ra, 
                                                 T.dec0 + T.trun1 * T.delta_dec)]),3786) as tline
    FROM 
      T
  )
SELECT 
  im.imageId, TL.trajId
FROM
  Image as im,
  ImageSetSDSS as set,
  TL
WHERE
  ST_INTERSECTS(TL.tline, im.bbox)
AND
  set.run = TL.run
AND 
  set.setId = im.setId;
"""

sql3 = """
WITH TL AS (
    SELECT
       runs.run as run,
       traj.trajId as trajId,
       ST_SetSRID(ST_MakeLine(ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM runs.tmin-traj.t0) * traj.delta_ra, 
                                           traj.dec0 + EXTRACT(EPOCH FROM runs.tmin-traj.t0) * traj.delta_dec), 
                              ST_MakePoint(traj.ra0  + EXTRACT(EPOCH FROM runs.tmax-traj.t0) * traj.delta_ra, 
                                           traj.dec0 + EXTRACT(EPOCH FROM runs.tmax-traj.t0) * traj.delta_dec)),3786) as tline
    FROM 
       Trajectory as traj,
       Runs as runs
  )
SELECT 
  im.imageId, TL.trajId
FROM
  Image as im,
  ImageSetSDSS as set,
  TL
WHERE
  ST_INTERSECTS(TL.tline, im.bbox)
AND
  set.run = TL.run
AND 
  set.setId = im.setId;
"""


print "\\timing on;"
for npts in (5, 10, 50, 100):
    reset(None, npts)
    print sql2
