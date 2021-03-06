# Routines used for building cubes
from __future__ import absolute_import, print_function

import sys
import time
import numpy as np
import math
import json

from astropy.io import fits

from gwcs.utils import _domain_to_bounds
from ..associations import Association
from .. import datamodels
from ..assign_wcs import nirspec
from . import cube
from . import CubeOverlap
from . import CubeCloud
from . import coord
from gwcs import wcstools

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

#********************************************************************************
def DetermineScale(Cube, InstrumentInfo):
#********************************************************************************
    """
    Short Summary
    -------------
    Determine the scale (sampling) in the 3 dimensions for the cube

    Parameters
    ----------
    Cube: Class holding basic information on cube
    InstrumentInfo holds the defaults scales for each channel/subchannel

    Returns
    -------
    scale, holding the scale for the 3 dimensions of the cube/

    """
    a = Cube.detector
    scale = [0, 0, 0]

    if(Cube.instrument == 'MIRI'):
        number_channels = len(Cube.channel)
        number_sub = len(Cube.subchannel)
        min_a = 1000.00
        min_b = 1000.00
        min_w = 1000.00

        for i in range(number_channels):
            this_channel = Cube.channel[i]
            for j in range(number_sub):
                this_sub = Cube.subchannel[j]
                print('channel and subch',this_channel,this_sub)

                a_scale, b_scale, wscale = InstrumentInfo.GetScale(this_channel,this_sub)

                if(a_scale < min_a):
                    min_a = a_scale
                if(b_scale < min_b):
                    min_b = b_scale
                if(wscale < min_w):
                    min_w = wscale

        scale = [min_a, min_b, min_w]

    elif(Cube.instrument == 'NIRSPEC'):
        number_gratings = len(Cube.grating)
        min_a = 1000.00
        min_b = 1000.00
        min_w = 1000.00

        for i in range(number_gratings):
            this_gwa = Cube.grating[i]
            a_scale, b_scale, wscale = InstrumentInfo.GetScale(this_gwa)

            if(a_scale < min_a):
                min_a = a_scale
            if(b_scale < min_b):
                min_b = b_scale
            if(wscale < min_w):
                min_w = wscale

        scale = [min_a, min_b, min_w]

    return scale
#_______________________________________________________________________


#********************************************************************************
def FindFootPrintMIRI(self, input, this_channel, InstrumentInfo):
#********************************************************************************

    """
    Short Summary
    -------------
    For each channel find:
    a. the min and max spatial coordinates (alpha,beta) or (V2-v3) depending on coordinate system.
      axis a = naxis 1, axis b = naxis2
    b. min and max wavelength is also determined. , beta and lambda for those slices


    Parameters
    ----------
    input: input model (or file)
    this_channel: channel working with


    Returns
    -------
    min and max spaxial coordinates  and wavelength for channel.
    spaxial coordinates are in units of arc secons. 
    """
    # x,y values for channel - convert to output coordinate system
    # return the min & max of spatial coords and wavelength  - these are of the pixel centers

    xstart, xend = InstrumentInfo.GetMIRISliceEndPts(this_channel)
    y, x = np.mgrid[:1024, xstart:xend]

    coord1 = np.zeros(y.shape)
    coord2 = np.zeros(y.shape)
    lam = np.zeros(y.shape)


    if (self.coord_system == 'alpha-beta'):
        detector2alpha_beta = input.meta.wcs.get_transform('detector', 'alpha_beta')
        coord1, coord2, lam = detector2alpha_beta(x, y)

    elif (self.coord_system == 'ra-dec'):
        detector2v23 = input.meta.wcs.get_transform('detector', 'v2v3')
        v23toworld = input.meta.wcs.get_transform("v2v3","world")

        v2, v3, lam = detector2v23(x, y) 
        coord1,coord2,lam = v23toworld(v2,v3,lam)

    else:
        # error the coordinate system is not defined
        raise NoCoordSystem(" The output cube coordinate system is not definded")

    a_min = np.nanmin(coord1)
    a_max = np.nanmax(coord1)

    b_min = np.nanmin(coord2)
    b_max = np.nanmax(coord2)

    lambda_min = np.nanmin(lam)
    lambda_max = np.nanmax(lam)

    return a_min, a_max, b_min, b_max, lambda_min, lambda_max

#********************************************************************************
def FindFootPrintNIRSPEC(self, input,flag_data):
#********************************************************************************

    """
    Short Summary
    -------------
    For each slice find:
    a. the min and max spatial coordinates (alpha,beta) or (V2-v3) depending on coordinate system.
      axis a = naxis 1, axis b = naxis2
    b. min and max wavelength is also determined. , beta and lambda for those slices


    Parameters
    ----------
    input: input model (or file)

    Returns
    -------
    min and max spaxial coordinates  and wavelength for channel.

    """
    # loop over all the region (Slices) in the Channel
    # based on regions mask (indexed by slice number) find all the detector
    # x,y values for slice. Then convert the x,y values to  v2,v3,lambda
    # return the min & max of spatial coords and wavelength  - these are of the pixel centers
#    print('in find footprint NIRSPEC')

    start_slice = 0
    end_slice = 29

    nslices = end_slice - start_slice + 1

    a_slice = np.zeros(nslices * 2)
    b_slice = np.zeros(nslices * 2)
    lambda_slice = np.zeros(nslices * 2)

    regions = list(range(start_slice, end_slice + 1))
    k = 0

    self.log.info('Looping over slices to determine cube size .. this takes a while')
    # for NIRSPEC there are 30 regions
    for i in regions:
#        print('on slice',i)
        slice_wcs = nirspec.nrs_wcs_set_input(input,  i)
        yrange_slice = slice_wcs.domain[1]['lower'],slice_wcs.domain[1]['upper']
        xrange_slice = slice_wcs.domain[0]['lower'],slice_wcs.domain[0]['upper']

        if(xrange_slice[0] >= 0 and xrange_slice[1] > 0): 

            x,y = wcstools.grid_from_domain(slice_wcs.domain)
#            y, x = np.mgrid[yrange[0]:yrange[1], xrange[0]:xrange[1]]
            ra,dec,lam = slice_wcs(x,y)

            #        print('ra',ra.shape,ra[20,0:20])
            #        print('dec',dec.shape,dec[20,0:20])

            a_slice[k] = np.nanmin(ra)
            a_slice[k + 1] = np.nanmax(ra)

            b_slice[k] = np.nanmin(dec)
            b_slice[k + 1] = np.nanmax(dec)

            lambda_slice[k] = np.nanmin(lam)
            lambda_slice[k + 1] = np.nanmax(lam)

        k = k + 2

    a_min = min(a_slice)
    a_max = max(a_slice)

    b_min = min(b_slice)
    b_max = max(b_slice)

    lambda_min = min(lambda_slice)
    lambda_max = max(lambda_slice)

#    print('Size of NIRSPEC CUBE FOV: (arcseconds)')
#    print('max a',a_min,a_max, 
#          (a_max-a_min)*math.cos(b_min*math.pi/180)*3600.0)
#    print('max b',b_min,b_max, (b_max-b_min)*3600.0)
#    print('wave',lambda_min,lambda_max)
    if(a_min == 0.0 and a_max == 0.0 and b_min ==0.0 and b_max == 0.0):
        self.log.info('This NIRSPEC exposure has no IFU data on it - skipping file')
        flag_data = -1

    return a_min, a_max, b_min, b_max, lambda_min, lambda_max
#_______________________________________________________________________
#********************************************************************************
def DetermineCubeSize(self, Cube, MasterTable, InstrumentInfo):
#********************************************************************************
    """
    Short Summary
    -------------
    Function to determine the min and max coordinates of the spectral cube,given channel & subchannel

    Parameter
    ----------
    Cube: class the holds the basic paramters of the IFU cube to be created
    MasterTable:  A table that contains the channel/subchannel or filter/grating for each input file
    InstrumentInfo: Default information on the MIRI and NIRSPEC instruments. This information might
                    contained in a different file in the future. Probably a reference file

    Returns
    -------
    Cube Dimension Information:

    Footprint of cube: min and max of coordinates of cube. If an offset list is provided then these values are applied.
    if the coordinate system is alpha-beta (MIRI) then min and max coordinates of alpha (arc sec),
    beta (arc sec) and lambda (microns) 
    if the coordinate system is ra-dec then the min and max of ra(degress), dec (degrees) and lambda (microns)
    is returned. 


    """
    instrument = Cube.instrument

    if(instrument == 'MIRI'):
        parameter1 = self.metadata['band_channel']
        parameter2 = self.metadata['band_subchannel']
    elif(instrument == 'NIRSPEC'):
        parameter1 = self.metadata['band_grating']
        parameter2 = self.metadata['band_filter']


    a_min = []
    a_max = []
    b_min = []
    b_max = []
    lambda_min = []
    lambda_max = []

    self.log.info('Number of bands in cube  %i', 
                              self.metadata['num_bands'])

    for i in range(self.metadata['num_bands']):
 
        this_a = parameter1[i]
        this_b = parameter2[i]
        self.log.info('Working on data  from %s,%s',this_a,this_b)

        n = len(MasterTable.FileMap[instrument][this_a][this_b])
        self.log.info('number of files %d ', n)

    # each file find the min and max a and lambda (OFFSETS NEED TO BE APPLIED TO THESE VALUES)
        for k in range(n):
            amin = 0.0
            amax = 0.0
            bmin = 0.0
            bmax = 0.0
            lmin = 0.0
            lmax = 0.0
            c1_offset = 0.0
            c2_offset = 0.0
            ifile = MasterTable.FileMap[instrument][this_a][this_b][k]
            ioffset = len(MasterTable.FileOffset[this_a][this_b]['C1'])
            if(ioffset == n):
                c1_offset = MasterTable.FileOffset[this_a][this_b]['C1'][k]
                c2_offset = MasterTable.FileOffset[this_a][this_b]['C2'][k]
#________________________________________________________________________________
# Open the input data model
            with datamodels.ImageModel(ifile) as input_model:
                t0 = time.time()
                if(instrument == 'NIRSPEC'):
                    flag_data = 0 
                    ChannelFootPrint = FindFootPrintNIRSPEC(self, input_model,flag_data)
                    amin, amax, bmin, bmax, lmin, lmax = ChannelFootPrint
                    t1 = time.time()
#________________________________________________________________________________
                if(instrument == 'MIRI'):
                    ChannelFootPrint = FindFootPrintMIRI(self, input_model, this_a, InstrumentInfo)
                    amin, amax, bmin, bmax, lmin, lmax = ChannelFootPrint
                    t1 = time.time()

                log.info("Time find foot print = %.1f.s" % (t1 - t0,))
# If a dither offset list exists then apply the dither offsets (offsets in arc seconds)

                amin = amin - c1_offset/3600.0
                amax = amax - c1_offset/3600.0

                bmin = bmin - c2_offset/3600.0
                bmax = bmax - c2_offset/3600.0

                a_min.append(amin)
                a_max.append(amax)
                b_min.append(bmin)
                b_max.append(bmax)
                lambda_min.append(lmin)
                lambda_max.append(lmax)

#________________________________________________________________________________
    # done looping over files determine final size of cube

    final_a_min = min(a_min)
    final_a_max = max(a_max)
    final_b_min = min(b_min)
    final_b_max = max(b_max)
    final_lambda_min = min(lambda_min)
    final_lambda_max = max(lambda_max)

#    print('Final wavelength ',final_lambda_min,final_lambda_max)
    if(self.wavemin != None and self.wavemin > final_lambda_min):
        final_lambda_min = self.wavemin
        self.log.info('Changed min wavelength of cube to %f ',final_lambda_min)

    if(self.wavemax != None and self.wavemax < final_lambda_max):
        final_lambda_max = self.wavemax
        self.log.info('Changed max wavelength of cube to %f ',final_lambda_max)
#________________________________________________________________________________
# Test that we have data (NIRSPEC NRS2 only has IFU data for 3 configurations) 

    test_a = final_a_max - final_a_min
    test_b = final_b_max - final_b_min
    test_w = final_lambda_max - final_lambda_min
    tolerance1 = 0.00001
    tolerance2 = 0.1
    
    if(test_a < tolerance1 or test_b < tolerance1 or test_w < tolerance2):
        
        self.log.info('No Valid IFU slice data found %f %f %f ',test_a,test_b,test_w)
        #raise ErrorNoIFUData(" NO Valid IFU slice data found on exposure ")
#________________________________________________________________________________
    CubeFootPrint = (final_a_min, final_a_max, final_b_min, final_b_max,
                     final_lambda_min, final_lambda_max)
    
    return CubeFootPrint
#________________________________________________________________________________


#********************************************************************************
def MapDetectorToCube(self,this_par1, this_par2, 
                      Cube, spaxel, 
                      MasterTable, 
                      InstrumentInfo,
                      IFUCube):
#********************************************************************************
    """
    Short Summary
    -------------
    Loop over files that cover the cube and map the detector pixel to Cube spaxels
    If dither offsets have been supplied then apply those values to the data

    Parameter
    ----------
    
    Cube - contains the basic header information of Cube
    spaxel: List of Spaxels

    Returns
    -------
    if(interpolation = area - only valid for alpha-beta
    or
    if(interpolation = pointcloud
    """

    instrument = Cube.instrument
    nfiles = len(MasterTable.FileMap[instrument][this_par1][this_par2])
    log.info('Number of files in cube %i', nfiles)

    # loop over the files that cover the spectral range the cube is for
    
    for k in range(nfiles):
        ifile = MasterTable.FileMap[instrument][this_par1][this_par2][k]
        
        ioffset = len(MasterTable.FileOffset[this_par1][this_par2]['C1'])
        Cube.file.append(ifile)
        c1_offset = 0.0
        c2_offset = 0.0
        # c1_offset and c2_offset are the dither offset sets (in arc seconds)
        # by default these are zer0. The user has to supply these 
        if(ioffset == nfiles):
            c1_offset = MasterTable.FileOffset[this_par1][this_par2]['C1'][k]
            c2_offset = MasterTable.FileOffset[this_par1][this_par2]['C2'][k]

# Open the input data model
        with datamodels.ImageModel(ifile) as input_model:

#********************************************************************************
            if(instrument == 'MIRI'):
                v2ab_transform = input_model.meta.wcs.get_transform('v2v3', 
                                                                    'alpha_beta')
                wave_weights = CubeCloud.FindWaveWeights(this_par1, this_par2)
                worldtov23 = input_model.meta.wcs.get_transform("world","v2v3")

            # for each file we need information that will be the same for all
            # the pixels on the image.
            # For MIRI this information is used in the weight scheme on how to 
            # combine the surface brightness information. The Cube class stores 
            # these paramters as a series of lists.  

                Cube.a_wave.append(wave_weights[0])
                Cube.c_wave.append(wave_weights[1])
                Cube.a_weight.append(wave_weights[2])
                Cube.c_weight.append(wave_weights[3])
                Cube.transform_worldtov23.append(worldtov23) 
                Cube.transform_v23toab.append(v2ab_transform)
#________________________________________________________________________________
# Standard method 
                if(self.interpolation == 'pointcloud'):
                    xstart, xend = InstrumentInfo.GetMIRISliceEndPts(this_par1)
                    y, x = np.mgrid[:1024, xstart:xend]
                    y = np.reshape(y, y.size)
                    x = np.reshape(x, x.size)
                    
                    t0 = time.time()
                    
                    cloud = CubeCloud.MakePointCloudMIRI(self,input_model,
                                                         x, y, k, 
                                                         Cube,
                                                        c1_offset, c2_offset)

                    if(k == 0):  # If first time
                        Cloud = cloud
                    else:    #  add information for another slice  to the  PixelCloud
                        Cloud = np.hstack((Cloud, cloud))

                                       

                    print('in MapDetector2Cube',cloud.shape,Cloud.shape)
                    t1 = time.time()
                    log.debug("Time Map one Channel from 1 file  to Cloud = %.1f.s" 
                              % (t1 - t0,))
#________________________________________________________________________________
#2D area method - only works for single files and coord_system = 'alpha-beta'
                if(self.interpolation == 'area'):
                    det2ab_transform = input_model.meta.wcs.get_transform('detector', 
                                                                      'alpha_beta')
                    start_region = InstrumentInfo.GetStartSlice(this_par1)
                    end_region = InstrumentInfo.GetEndSlice(this_par1)
                    regions = list(range(start_region, end_region + 1))

                    for i in regions:
                        log.info('Working on Slice # %d', i)

                        y, x = (det2ab_transform.label_mapper.mapper == i).nonzero()

                    # spaxel object holds all needed information in a set of lists
                    #    flux (of overlapping detector pixel)
                    #    error (of overlapping detector pixel)
                    #    overlap ratio
                    #    beta distance

# getting pixel corner - ytop = y + 1 (routine fails for y = 1024)
                        index = np.where(y < 1023) 
                        y = y[index]
                        x = x[index]
                        t0 = time.time()

                        beta_width = Cube.Cdelt2
                        CubeOverlap.SpaxelOverlap(self, x, y, i, 
                                                  start_region, 
                                                  input_model, 
                                                  det2ab_transform, 
                                                  beta_width, 
                                                  Cube, spaxel)
                        t1 = time.time()
                        log.debug("Time Map one Slice  to Cube = %.1f.s" % (t1 - t0,))

#********************************************************************************
            elif(instrument == 'NIRSPEC'):
# each file, detector has 30 slices - wcs information access seperately for each slice 
                start_slice = 0
                end_slice = 29
                nslices = end_slice - start_slice + 1
                regions = list(range(start_slice, end_slice + 1))
                for i in regions:
                    t0 = time.time()
                    cloud = CubeCloud.MakePointCloudNIRSPEC(self,input_model,
                                                            k,
                                                            i,
                                                            Cube,
                                                            c1_offset, c2_offset)

                    if(i == start_slice and k == 0  ):  # If first time
                        Cloud = cloud
                    else:    #  add information for another slice  to the  PixelCloud
                        Cloud = np.hstack((Cloud, cloud))

#                    print("cloud, Cloud Shape",cloud.shape,Cloud.shape)

                    t1 = time.time()
                    log.debug("Time Map one NIRSPEC slice  to Cloud = %.1f.s" % (t1 - t0,))

#________________________________________________________________________________

    return Cloud


#********************************************************************************
def FindCubeFlux(self, Cube, spaxel, PixelCloud):
#********************************************************************************
    """
    Short Summary
    -------------
    Depending on the interpolation method, find the flux for each spaxel value

    Parameter
    ----------
    Cube - contains the basic header information of Cube
    spaxel: List of Spaxels
    PixelCloud - pixel point cloud, only filled in if doing 3-D interpolation

    Returns
    -------
    if(interpolation = area) flux determined for each spaxel
    or
    if(interpolation = pointcloud) flux determined for each spaxel based on interpolation of PixelCloud
    """



    if self.interpolation == 'area':
        nspaxel = len(spaxel)

        for i in range(nspaxel):
            s = len(spaxel[i].pixel_overlap)
            if(s > 0):
                CubeOverlap.SpaxelFlux(self.roi2, i, Cube, spaxel)

    elif self.interpolation == 'pointcloud':
        icube = 0
        t0 = time.time()
        for iz, z in enumerate(Cube.zcoord):
            for iy, y in enumerate(Cube.ycoord):
                for ix, x in enumerate(Cube.xcoord):
                    num = len(spaxel[icube].ipointcloud)

                    if(num > 0):
                        pointcloud_index = spaxel[icube].ipointcloud
                        weightpt = spaxel[icube].pointcloud_weight
                        pixelflux = PixelCloud[5, pointcloud_index]

                        weight = 0
                        value = 0
                        for j in range(num):
                            weight = weight + weightpt[j]
                            value = value + (weightpt[j] * pixelflux[j])
#                            if(iz == 39 or iz == 40 ):
#                                if(ix == 14 and iy == 16): 
#                                    print('Checking ', icube, ix, iy, iz)
#                                    print('icube', icube)
#                                    print('pointcloud', pointcloud_index[j])
#                                    print('flux = {0:.5f}'.format(pixelflux[j]))
#                                    print('w', weightpt[j])
#                                    print(' ',weightpt[j] * pixelflux[j])
#                                    print('num',num)


                        if(weight != 0):
                            value = value / weight
                            spaxel[icube].flux = value
#                            if(iz == 39 or iz == 40 ):
#                                if(ix == 14 and iy == 16): 
#                                    print('Final Flux', value* weight, weight, value,num)


                    icube = icube + 1
#                    ix = ix + 1
#                iy = iy + 1
#            iz = iz + 1

        t1 = time.time()
        log.info("Time to interpolate at spaxel values = %.1f.s" % (t1 - t0,))


#________________________________________________________________________________
#********************************************************************************
def CheckCubeType(self):

    if(self.interpolation == "area"):
        if(self.metadata['number_files'] > 1):
            raise IncorrectInput("For interpolation = area, only one file can be used to created the cube")

        if(len(self.metadata['channel']) > 1):
            raise IncorrectInput("For interpolation = area, only channel can be used to created the cube")

    if(self.coord_system == "alpha-beta"):
        if(self.metadata['number_files'] > 1):
            raise IncorrectInput("Cubes built in alpha-beta coordinate system are built from a single file")


#********************************************************************************

class IncorrectInput(Exception):
    pass

class NoCoordSystem(Exception):
    pass

class ErrorNoIFUData(Exception):
    pass
