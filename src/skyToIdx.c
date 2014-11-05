#include "postgres.h"
#include <stdio.h>
#include <string.h>
#include "wcslib/wcs.h"
#include "fmgr.h"
#include "executor/executor.h"  /* for GetAttributeByName() */

/* Get the location of the postgres include/libs by:

 pg_config --includedir-server
 pg_config --libdir

# HOW TO BUILD:

Window 1: 
   OS X:
      rm skyToIdx.o skyToIdx.so ; cc -O3 -fpic -c skyToIdx.c -I/opt/local/include -I/opt/local/include/postgresql93/server/ ; cc -O3 -bundle -flat_namespace -undefined suppress -lwcs -L/opt/local/lib -o skyToIdx.so skyToIdx.o
   LINUX: 
      rm skyToIdx.o skyToIdx.so ; cc -O3 -fpic -c skyToIdx.c -I/usr/local/include/ -I/usr/include/pgsql/server/; cc -O3 -shared -lwcs -L/usr/local/lib -o skyToIdx.so skyToIdx.o

Window 2: \q
          psql -U postgres -d kbmod
          CREATE OR REPLACE FUNCTION c_skyToIdx(wcs, double precision, double precision) RETURNS integer
            AS '/Users/acbecker/src/github/kbmod/src/skyToIdx', 'c_skyToIdx'
            LANGUAGE C STRICT;

# Other useful pgsql commands:

DROP FUNCTION c_skyToIdx(wcs, double precision, double precision);
\df+ c_skyToIdx;

*/

#ifdef PG_MODULE_MAGIC
PG_MODULE_MAGIC;
#endif

PG_FUNCTION_INFO_V1(c_skyToIdx);

double* polyElements(int const order, double const value)
{
    double* poly = palloc((order+1) * sizeof(double));
    poly[0] = 1.0;
    if (order == 0) {
        return poly;
    }
    poly[1] = value;
    int i;
    for (i=2; i<=order; ++i) {
        poly[i] = poly[i-1]*value;
    }
    return poly;
}

Datum
c_skyToIdx(PG_FUNCTION_ARGS)
{
    HeapTupleHeader t = PG_GETARG_HEAPTUPLEHEADER(0);
    bool isNull;
    double ra = PG_GETARG_FLOAT8(1);
    double decl = PG_GETARG_FLOAT8(2);
    
    /* Constants */
    int sipOrder=5;
    int nPixX=2048;
    int lsstToFitsPixels=+1;
    int fitsToLsstPixels=-1;
    //The amount of space allocated to strings in wcslib
    const int STRLEN = 72;
    
    /* Set up the Wcs struct */
    double CRPIX1 = DatumGetFloat8(GetAttributeByName(t, "crpix1", &isNull));
    double CRPIX2 = DatumGetFloat8(GetAttributeByName(t, "crpix2", &isNull));

    struct wcsprm* wcsInfo; // defined in wcs.h
    wcsInfo = palloc(sizeof(struct wcsprm));
    wcsInfo->flag = -1;
    int status = wcsini(true, 2, wcsInfo); 
    wcsInfo->crval[0] = DatumGetFloat8(GetAttributeByName(t, "crval1", &isNull)); 
    wcsInfo->crval[1] = DatumGetFloat8(GetAttributeByName(t, "crval2", &isNull)); 
    // NOTE: if we are getting these from LSST, there has already been a compensataion for 
    //  pixel addressing convetions, i.e. lsstToFitsPixels
    // See e.g. Wcs::initWcsLib in afw/src/image/Wcs.cc where they initialize with an
    //  external crpix and do e.g.
    //  _wcsInfo->crpix[0] = crpix.getX() + lsstToFitsPixels;
    // I don't believe we need that here
    wcsInfo->crpix[0] = CRPIX1;
    wcsInfo->crpix[1] = CRPIX2;

    char strCd[STRLEN];
    int i, j;
    for (i=0; i<2; ++i) {
        for (j=0; j<2; ++j) {
            sprintf(strCd, "cd%d_%d", i+1, j+1);
            wcsInfo->cd[(2*i) + j] = DatumGetFloat8(GetAttributeByName(t, strCd, &isNull));
        }
    }
    wcsInfo->altlin = 2;
    wcsInfo->flag   = 0;  
    wcsInfo->types = NULL;
    strncpy(wcsInfo->ctype[0], "RA---TAN", STRLEN);
    strncpy(wcsInfo->ctype[1], "DEC--TAN", STRLEN);
    strncpy(wcsInfo->radesys, "FK5", STRLEN);
    wcsInfo->equinox = 2000.0;
    strncpy(wcsInfo->cunit[0], "deg", STRLEN);
    strncpy(wcsInfo->cunit[1], "deg", STRLEN);
    status=wcsset(wcsInfo);

    // Do the initial coordinate mapping
    double skyIn[2];
    double imgcrd[2];
    double phi, theta;
    double pixOut[2];
    skyIn[wcsInfo->lng] = ra;
    skyIn[wcsInfo->lat] = decl;
    int stat[1];
    status = 0;
    status = wcss2p(wcsInfo, 1, 2, skyIn, &phi, &theta, imgcrd, pixOut, stat);

    double xLin = pixOut[0];
    double yLin = pixOut[1];

    double U = xLin - CRPIX1;
    double V = yLin - CRPIX2;
    double *uPoly, *vPoly;
    uPoly = polyElements(sipOrder, U);
    vPoly = polyElements(sipOrder, V);

    /* Create additional SIP modification */
    double F=0., G=0.;
    char strA[STRLEN], strB[STRLEN];
    double sipAp, sipBp;
    for (i = 0; i <= sipOrder; ++i) {
        for (j = 0; j <= sipOrder-i; ++j) {
            sprintf(strA, "ap_%d_%d", i, j);
            sprintf(strB, "bp_%d_%d", i, j);
            sipAp = DatumGetFloat8(GetAttributeByName(t, strA, &isNull));
            sipBp = DatumGetFloat8(GetAttributeByName(t, strB, &isNull));
            F += sipAp * *(uPoly+i) * *(vPoly+j);
            G += sipBp * *(uPoly+i) * *(vPoly+j);
        }
    }
   
    /* Final x,y coordinates */
    int xWarp = (int) (xLin + F + fitsToLsstPixels + 0.5);
    int yWarp = (int) (yLin + G + fitsToLsstPixels + 0.5);
    int pIdx  = xWarp + nPixX * yWarp;

    pfree(wcsInfo);
    pfree(uPoly);
    pfree(vPoly);
    PG_RETURN_INT32(pIdx);
}
