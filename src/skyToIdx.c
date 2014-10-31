#include <stdio.h>
#include "wcslib/wcs.h"
#include "postgres.h"
#include "fmgr.h"
#include "executor/executor.h"  /* for GetAttributeByName() */

/* Get the location of the postgres include/libs by:

 pg_config --includedir-server
 pg_config --libdir

cc -fpic -c skyToIdx.c -I/opt/local/include -I/opt/local/include/postgresql93/server/

 # Linux
cc -shared -lwcs -L/opt/local/lib -o skyToIdx.so skyToIdx.o

 # OS X
cc -bundle -flat_namespace -undefined suppress -lwcs -L/opt/local/lib -o skyToIdx.so skyToIdx.o
*/

#ifdef PG_MODULE_MAGIC
PG_MODULE_MAGIC;
#endif

PG_FUNCTION_INFO_V1(c_skyToIdx);

double* polyElements(int const order, double const value)
{
    double* poly = palloc(order+1 * sizeof(double));
    poly[0] = 1.0;
    if (order == 0) {
        return poly;
    }
    poly[1] = value;
    for (int i=2; i<=order; ++i) {
        poly[i] = poly[i-1]*value;
    }
    return poly;
}

Datum
c_skyToIdx(PG_FUNCTION_ARGS)
{
    HeapTupleHeader  t = PG_GETARG_HEAPTUPLEHEADER(0);
    bool isNull;
    double ra = PG_GETARG_FLOAT8(0);
    double decl = PG_GETARG_FLOAT8(1);

    /* Constants */
    int sipOrder=4;
    int nPixX=2048;
    int lsstToFitsPixels=+1;
    int fitsToLsstPixels=-1;
    //The amount of space allocated to strings in wcslib
    const int STRLEN = 72;

    /* Set up the Wcs struct */
    double CRPIX1 = DatumGetFloat8(GetAttributeByName(t, "CRPIX1", &isNull));
    double CRPIX2 = DatumGetFloat8(GetAttributeByName(t, "CRPIX2", &isNull));
    struct wcsprm* wcsInfo; // defined in wcs.h
    wcsInfo = palloc(sizeof(struct wcsprm));
    wcsInfo->flag = -1;
    int status = wcsini(true, 2, wcsInfo); 
    wcsInfo->crval[0] = DatumGetFloat8(GetAttributeByName(t, "CRVAL1", &isNull)); 
    wcsInfo->crval[1] = DatumGetFloat8(GetAttributeByName(t, "CRVAL2", &isNull)); 
    wcsInfo->crpix[0] = CRPIX1 + lsstToFitsPixels;
    wcsInfo->crpix[1] = CRPIX2 + lsstToFitsPixels;
    char strCd[5];
    for (int i=0; i<2; ++i) {
        for (int j=0; j<2; ++j) {
            sprintf(strCd, "CD%d_%d", i, j);
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

    /* SIP matrices */
    double sipAp[sipOrder+1][sipOrder+1], sipBp[sipOrder+1][sipOrder+1];
    char strA[6], strB[6];
    for (int i = 0; i <= sipOrder; ++i) {
        for (int j = 0; j <= sipOrder-i; ++j) {
            sprintf(strA, "AP_%d_%d", i, j);
            sprintf(strB, "BP_%d_%d", i, j);
            sipAp[i][j] = DatumGetFloat8(GetAttributeByName(t, strA, &isNull));
            sipBp[i][j] = DatumGetFloat8(GetAttributeByName(t, strB, &isNull));
        }
    }

    /* Create additional SIP modification */
    double F=0., G=0.;
    for (int i = 0; i < sipOrder; ++i) {
        for (int j = 0; j < sipOrder; ++j) {
            F += sipAp[i][j] * *(uPoly+i) * *(vPoly+j);
            G += sipBp[i][j] * *(uPoly+i) * *(vPoly+j);
        }
    }

    /* Final x,y coordinates */
    int xWarp = (int) xLin + F + fitsToLsstPixels + 0.5;
    int yWarp = (int) yLin + G + fitsToLsstPixels + 0.5;
    int pIdx  = xWarp + nPixX * yWarp;
    pfree(wcsInfo);
    pfree(uPoly);
    pfree(vPoly);
    PG_RETURN_INT32(pIdx);
}
