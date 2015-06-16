
import numpy as np
import pylab as py
import json
import ztools

'''
Measuring low-order aberrations from defocused images
May 3, 2006
Translation to python Jun, 2015
'''

class Donut():

    def __init__(self):
        pass
        # Stores "common block" from IDL routine
        # self.donpar = None
        # self.ngrid = None
        # self.r = None
        # self.zgrid = None
        # self.pupil = None
        # self.Rpix = None
        # self.inside = None
        # self.asperpix = None
        # self.ccdpix = None
        # self.npixperpix = None
        # self.fovpix = None
        # self.sflag = None
        # self.sigpix = None
        # self.flux = None

    def readpar(self,filename):

        with open(filename) as data_file:
            data = json.load(data_file)

        for key in data['donpar']:
            k = key.keys()[0]
            self.__dict__[k.lower()] = key[k]

        self.data_struct = data

    def init(self):
        '''
        ; Pre-compute the parameters and save them in the COMMOM block
        :return:
        '''

        ngrid = self.ngrid
        d = self.d
        eps = self.eps
        alambda = self.alambda
        pixel = self.pixel
        self.sflag = 0 # fast seeing blur, set to 1 for slow calc.


        # Find reasonable limits on the grid parameters
        asperpix =  206265.*(1e-6*alambda)/D # maximum fine-pixel size

        ccdpix = float(pixel)
        k = np.floor(np.log10(ccdpix/asperpix)/np.log10(2.)) +1.
        npixperpix = 2**k
        fovpix = 2*ngrid/npixperpix     # CCD field size
        asperpix = ccdpix/npixperpix
        size = 206266.*(1e-6*alambda)/asperpix
        Rpix = ngrid/size*D

        print 'Rebinning factor: ', npixperpix
        print 'Grid pixel: ',asperpix,' arcsec'
        print 'Grid size: ', size,' m'
        print 'CCD pixel:  ',ccdpix,' arcsec'
        print 'CCD field:  ',fovpix*ccdpix,' arcsec'
        print 'CCD format: ', fovpix

        r = np.rool(np.roll(ztools.dist(2*ngrid),
                            ngrid,
                            axis=0),
                    ngrid,
                    axis=1) #distance from grid center, pixs
        inside = np.bitwise_and( r <= Rpix ,
                                 r <= Rpix*eps )
        pupil = np.zeros((2*ngrid,2*ngrid))    # zero array
        pupil[inside] = 1
        n = len(inside)

        x = (np.arange(2*ngrid) - ngrid) # replicate(1.,2*ngrid)
        theta = np.arctan2(x.T,x)
        theta[ngrid][ngrid]=0.
        self.zgrid = np.zeros((n,2))
        self.zgrid[0] = r(inside)/Rpix
        self.zgrid[1] = theta[inside]
        self.inside = inside
        self.fovpix = fovpix
        self.asperpix = asperpix
        self.ccdpix = ccdpix

    def getimage(self,z):
        '''

        :param z: the Zernike vector in microns, starting from Z=2 (tip)
                    z[0] is seeing in arcseconds
        :return:
        '''
        #COMMON imagedata, uampl, filter2, seeing


        fact = 2.*np.pi/self.alambda
        nzer = len(z)
        phase = np.zeros_like(self.zgrid[0]) # empty array for phase
        for j in range(1, nzer):
            phase += fact*z[j]*ztools.zernike_estim(j+1,self.zgrid)

        tmp = np.zeros((self.ngrid*2,self.ngrid*2))
        uampl = np.complex(tmp, tmp)
        self.uampl = uampl
        uampl[self.inside] = np.complex(np.cos(phase), np.sin(phase))

        self.seeing = z[0]

        #---------  compute the image ----------------------
        imh = np.abs(ztools.shift(np.ifft2(ztools.shift(uampl,self.ngrid,self.ngrid)),self.ngrid,self.ngrid))**2.
        if (self.sflag > 0): # exact seeing blur

            filter2 = np.exp(-2.*np.pi**2*(self.seeing/2.35/self.asperpix/2/self.ngrid)**2*self.r**2) # unbinned image
            imh = np.abs(np.fft2(ztools.shift(np.fft2(imh),self.ngrid,self.ngrid)*filter2))
            impix = ztools.rebin(imh,(self.fovpix,self.fovpix)) # rebinning into CCD pixels

        else:
            rr = ztools.shift(ztools.dist(self.fovpix),self.fovpix/2,self.fovpix/2)
            filter2 = np.exp(-2.*np.pi**2*(self.seeing/2.35/self.ccdpix/self.fovpix)**2*rr**2) # binned image
            impix = ztools.rebin(imh,self.fovpix,self.fovpix) # rebinning into CCD pixels
            impix = np.abs(np.fft2(ztools.shift(np.fft2(impix),self.fovpix/2,self.fovpix/2)*filter2)) # Seeing blur


        self.filter2 = filter2
        return impix/np.sum(impix)

    def newimage(self, a, jzer):
        '''
        a is the amplitude change of aberration (micron), Jzer is the Zernike number
        (1=seeing, 4=focus etc.)

        :param a:
        :param jzer:
        :return:
        '''

        #COMMON imagedata, uampl, filter2, seeing

        newampl = self.uampl
        if (jzer > 1): # Change Zernike coefficient
            newphase =  2.*np.pi/self.alambda*a*ztools.zernike_estim(jzer,self.zgrid)
            newampl[self.inside] *= np.complex(np.cos(newphase), np.sin(newphase))
            filter = self.filter2
        else: # new seeing
            newseeing = self.seeing + a
            if (sflag > 0):
                filter = np.exp(-2.*np.pi**2*(newseeing/2.35/self.asperpix/2/self.ngrid)**2*self.r**2) # unbinned image
            else:
                rr = ztools.shift(ztools.dist(self.fovpix),self.fovpix/2,self.fovpix/2)
                filter = np.exp(-2.*np.pi**2*(newseeing/2.35/self.ccdpix/self.fovpix)^2*rr**2) # binned image

        #---------  compute the image ----------------------
        imh = np.abs(ztools.shift(np.ifft2(ztools.shift(newampl,self.ngrid,self.ngrid)),self.ngrid,self.ngrid))**2
        if (sflag > 0): # exact seing blur
            imh = np.abs(np.fft2(ztools.shift(np.fft2(imh),self.ngrid,self.ngrid)*filter))
            impix = ztools.rebin(imh,self.fovpix,self.fovpix) # rebinning into CCD pixels
        else:
            impix = ztools.rebin(imh,self.fovpix,self.fovpix) # rebinning into CCD pixels
            impix = np.abs(np.fft2(ztools.shift(np.fft2(impix),self.fovpix/2,self.fovpix/2)*filter)) # Seeing blur

        return impix/np.sum(impix)

    def getmom(self,impix1): #, impix1, zestim
        '''

        :param impix1:
        :return: Vector of Zernike aberrations in microns
        '''
        n = self.ngrid/self.npixperpix
        xx = (np.arange(2*n)-n)#replicate(1,2*n)
        yy = (np.arange(2*n)-n)#replicate(1,2*n)

        thresh = np.max(impix1)*self.thresh
        impix = impix1
        impix[ impix < thresh ] = 0.

        imh0 = np.sum(impix)

        xc = np.sum(xx*impix)/imh0
        yc = np.sum(yy*impix)/imh0
        mxx = np.sum(impix*(xx-xc)^2)/imh0
        myy = np.sum(impix*(yy-yc)^2)/imh0
        mxy = np.sum(impix*(xx-xc)*(yy-yc))/imh0

        scale = self.npixperpix/(self.ngrid/self.rpix)

        a2 = scale*(xc+0.5)*np.pi*0.5
        a3 = scale*(yc+0.5)*np.pi*0.5
        a4 = scale*np.sqrt((mxx + myy)*0.5)/1.102
        a4 = (a4**2 - (0.5/2.35)**2)
        a4[a4 < 0.] = 0. # subtract 0.5arcsec seeing
        a5 = scale*mxy*(mxx*myy)**(-0.25)/1.45
        a6 = scale*(mxx - myy)*0.5*(mxx*myy)**(-0.25)/1.45
        zestim = [0.,a2,a3,a4,a5,a6]*self.alambda/(2.*np.pi) # estimated Zernike aberrations
        zestim[0] = 0.5

        return zestim

    def displ(self,image):
        py.imshow(image,
                  origin='lower',
                  interpolation='nearest')

    def find(self,impix,zres,nzer):
        '''
        Nzer is the highest Zernike number, zres is the  result
        :return:
        '''

        nzer = np.max([nzer,6])
        n1 = len(zres)
        nzer1 = np.max([n1,nzer])
        z0 = np.zeros(nzer1)
        z0[0:n1-1] = zres

        impixnorm = impix/np.sum(impix)
        impixmax = np.max(impix)

        xi = np.zeros(nzer)
        for j in np.arange(1,nzer):
            xi[j] = self.alambda/(2.*np.pi)*0.5/((np.sqrt(8.*(j+1.)-6.)-1.)/2.)
        xi[0] = 0.1
        indonut = impixnorm[impixnorm > impixmax*self.thresh]
        im = impixnorm(indonut)
        n = len(indonut)
        chi2old = n**2
        chi2norm = np.sum(im**2)

        ncycle = 20
        thresh0 = 0.01  # initial SVD threshold
        norm = np.max(impix)
        thresh = thresh0  # SVD inversion threshold, initial
        print 'Z  ',np.arange(nzer)+1
        self.alambda = 1. # for L-M method

        for k in range(ncycle):
            model = self.getimage(z0)
            im0 = model[indonut]
            chi2 = np.sqrt(np.sum((im0 - im)**2.)/chi2norm )
            invmat = np.zeros((n,nzer))
            print 'Cycle: ',k+1, '  RMS= ',chi2*100, ' percent'
            print 'um ', z0[0:nzer-1]

            thresh = thresh*0.5

            if (chi2 < 1e-4):
                break
            # do not degrade aberrations
            elif (chi2 <= chi2old):
                zres=z0
                self.alambda = self.alambda*0.1
                if ((chi2 >= chi2old*0.99) and (k > 3)):
                    break
                chi2old = chi2
            else:
                z0 = zres
                thresh = thresh0
                self.alambda = self.alambda*10.
                print 'Divergence... Now LM parameter = ', self.alambda

            if (k%2 == 0):
                imat = np.zeros((n,nzer))
                print 'Computing the interaction matrix...'
                for j in np.arange(nzer):
                    imat[j] =  ((self.newimage(xi[j],j+1))[indonut] - im0)/xi[j]
                tmat = np.dot(imat.T, imat)
                tmp = ztools.svd_invert(tmat, thresh)
                invmat = np.dot(tmp, imat.T)

            dif = im - im0
            dz = invmat # dif
            z0[0:nzer-1] += 0.7*dz

            z0[0] = np.max([z0[0], 0.2])
            z0[0] = np.min([z0[0], 1.5])

            d1 = np.min(dif)
            d2 = np.max(dif)
            #display the image (left: input, right: model)
            self.displ(np.append(impix,model,axis=-1))

        print 'Fitting done!'
        return chi2, model

    #-------------------------------------------------------

    def fit(self,impix, efoc):
        '''
        preliminary and final fitting
        :param impix:
        :param immod:
        :param zres:
        :param efoc:
        :param chi2:
        :return:
        '''

        zres = self.getmom(impix)

        nzer = self.nzer
        #if (self.static != ''):
        z0 = self.readz(self.static)# else z0 = fltarr(nzer)

        z0[0:5] = self.zres
        if (efoc < 0):
            z0[3:5] *= -1.
        self.zres = z0

        chi2, immod = self.find(impix, zres, nzer)

        return chi2,immod

    def writepar(self,filename):
        '''
        Write parameters into a file
        :param filename:
        :return:
        '''

        data = self.data_struct

        for key in data['donpar']:
            k = key.keys()[0]
            data[k] = self.__dict__[k.lower()]

        print 'Parameters are saved in ',filename

    def savez(self, z, filename):
        '''
        ; Save Zernike vector in ASCII file
        :param z:
        :param filename:
        :return:
        '''

        np.savetxt(filename,fmt='%8.3f',X=z)
        print 'Zernike vector is saved in ',filename


    def readz(self):

        if self.static != '':
            return np.loadtxt(self.static)
        else:
            return np.zeros(self.nzer)

    def saveres(self, resfile, z, chi2, imfile):

        with open(resfile) as fp:
            fmt_str = '%20s %6i %6i %10.3e %8.4f'+len(z)*' %8.3f'
            tuple_res = tuple(imfile, self.xc, self.yc, flux, chi2)+tuple(z)
            fp.write(fmt_str%tuple_res)

        fp.close()
        print 'Results are saved!'

    def extract(self,img, xc, yc, nccd):

        ix1 = np.max([xc-nccd,0])
        ix2 = np.min([xc+nccd, len(img)-1])
        iy1 = np.max([yc-nccd,0])
        iy2 = np.min([yc+nccd, len(img)-1])

        img1 = img[ix1:ix2,iy1:iy2] # cut out the required part

        img1 = img1 - np.min(img1)  # subtract background
        itot = sum(img1)

        # find the center-of-gravity
        nx = img1.shape[0]
        ny = img1.shape[1]

        xx = (np.arange(nx)-nx/2)#replicate(1,ny)
        ix = np.sum(img1*xx)/itot + 2

        yy = np.array(nx,copy=True) # (findgen(ny)-ny/2)
        iy = np.sum(img1*yy)/itot +2

        ix = np.array(np.floor(ix),dtype=np.int)+ nx/2
        iy = np.array(np.floor(iy),dtype=np.int)+ ny/2

        ix1 = np.max([ix-nccd/2 ,0])
        ix2 = np.min([ix1+nccd, nx-1])

        iy1 = np.max([iy-nccd/2 ,0])
        iy2 = np.min([iy1+nccd , ny-1])

        if (ix2-ix1 < nccd-1) or (iy2-iy1 < nccd-1):
            print 'Image is cut on one side!'
            return -1

        impix = img1[ix1:ix2,iy1:iy2]
        i = (np.sort(impix))[np.array(np.floor(0.1*self.fovpix**2),dtype=np.int)]
        backgr = impix[i] #; 10% quantile of pixel distribution

        impix = float(impix) - backgr
        self.flux = np.sum(impix)
        print 'Total flux, ADU: ', self.flux
        impix = impix/self.flux
        self.sigpix = np.max([impix ,0])*self.flux*self.eadu + self.ron**2  # variance in each pixel

        return impix