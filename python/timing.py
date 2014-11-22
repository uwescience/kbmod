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

#for npts in (5, 10, 50, 100):
for npts in (100,):
    dt1s = []
    dt2s = []
    for i in range(10):
        #reset(db, npts); t0 = time.time(); r1 = db.db.query(sql1); dt1 = time.time() - t0
        dt1 = 100
        reset(db, npts); t0 = time.time(); r2 = db.db.query(sql2); dt2 = time.time() - t0
        dt1s.append(dt1)
        dt2s.append(dt2)
    print npts, "%.3f +/- %.3f   %.3f +/- %.3f" % (np.mean(dt1s), np.std(dt1s), np.mean(dt2s), np.std(dt2s))

# 5 140.119 +/- 18.699     1.228 +/- 0.170
# 10 288.267 +/- 35.372    2.247 +/- 0.284
# 50 1401.957 +/- 83.573   11.287 +/- 0.627
# 100 XXX +/- XXX          21.107 +/- 0.977

#    plt.errorbar(npts, np.mean(dt1s), yerr=np.std(dt1s), fmt="ro-")
#    plt.errorbar(npts, np.mean(dt2s), yerr=np.std(dt2s), fmt="bs-")
#    plt.ylabel("Time(seconds)")
#    plt.xlabel("N Traj")
#plt.show()
