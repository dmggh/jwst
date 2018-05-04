#! /usr/bin/env python
#
# utils.py: utility functions
import logging
import numpy as np

from .. import datamodels
from ..datamodels import dqflags
from ..lib import reffile_utils

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OptRes:
    """
    Object to hold optional results for all good pixels for
    y-intercept, slope, uncertainty for y-intercept, uncertainty for
    slope, inverse variance, first frame (for pedestal image), and
    cosmic ray magnitude.
    """

    def __init__(self, n_int, imshape, max_seg, nreads):
        """
        Short Summary
        -------------
        Initialize the optional attributes. These are 4D arrays for the
        segment-specific values of the y-intercept, the slope, the uncertainty
        associated with both, the weights, the approximate cosmic ray
        magnitudes, and the inverse variance.  These are 3D arrays for the
        integration-specific first frame and pedestal values.

        Parameters
        ----------
        n_int: int
            number of integrations in data set

        imshape: (int, int) tuple
            shape of 2D image

        max_seg: int
            maximum number of segments fit

        nreads: int
            number of reads in an integration
        """
        self.yint_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.slope_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.sigyint_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.sigslope_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.inv_var_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.firstf_int = np.zeros((n_int,) + imshape, dtype=np.float32)
        self.ped_int = np.zeros((n_int,) + imshape, dtype=np.float32)
        self.cr_mag_seg = np.zeros((n_int,)+(nreads,)+imshape, dtype=np.float32)
        self.cr_mag_seg = np.zeros((n_int,) + (nreads,)+imshape, dtype=np.int16)
        self.var_p_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
        self.var_r_seg = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)


    def init_2d(self, npix, max_seg):
        """
        Short Summary
        -------------
        Initialize the 2D segment-specific attributes for the current data
        section.

        Parameters
        ----------
        npix: integer
            number of pixels in section of 2D array

        max_seg: integer
            maximum number of segments that will be fit within an
            integration, calculated over all pixels and all integrations

        Returns
        -------
        None
        """
        self.interc_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.slope_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.siginterc_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.sigslope_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.inv_var_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.firstf_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.var_s_2d = np.zeros((max_seg, npix), dtype=np.float32)
        self.var_r_2d = np.zeros((max_seg, npix), dtype=np.float32)


    def reshape_res(self, num_int, rlo, rhi, sect_shape, ff_sect):
        """
        Short Summary
        -------------
        Loop over the segments and copy the reshaped 2D segment-specific
        results for the current data section to the 4D output arrays.

        Parameters
        ----------
        num_int: int
            integration number

        rlo: int
            first column of section

        rhi: int
            last column of section

        sect_sect: (int,int) tuple
            shape of section image

        ff_sect: 2D array
            first frame data

        Returns
        -------
        """
        for ii_seg in range(0, self.yint_seg.shape[1]):
            self.yint_seg[num_int, ii_seg, rlo:rhi, :] = \
                           self.interc_2d[ii_seg, :].reshape(sect_shape)
            self.slope_seg[num_int, ii_seg, rlo:rhi, :] = \
                            self.slope_2d[ii_seg, :].reshape(sect_shape)
            self.sigyint_seg[num_int, ii_seg, rlo:rhi, :] = \
                              self.siginterc_2d[ii_seg, :].reshape(sect_shape)
            self.sigslope_seg[num_int, ii_seg, rlo:rhi, :] = \
                               self.sigslope_2d[ii_seg, :].reshape(sect_shape)
            self.inv_var_seg[num_int, ii_seg, rlo:rhi, :] = \
                              self.inv_var_2d[ii_seg, :].reshape(sect_shape)
            self.firstf_int[num_int, rlo:rhi, :] = ff_sect


    def append_arr(self, num_seg, g_pix, intercept, slope, sig_intercept,
                   sig_slope, inv_var):
        """
        Short Summary
        -------------
        Add the fitting results for the current segment to the 2d arrays.

        Parameters
        ----------
        num_seg: int, 1D array
            counter for segment number within the section

        g_pix: int, 1D array
            pixels having fitting results in current section

        intercept: float, 1D array
            intercepts for pixels in current segment and section

        slope: float, 1D array
            slopes for pixels in current segment and section

        sig_intercept: float, 1D array
            uncertainties of intercepts for pixels in current segment
            and section

        sig_slope: float, 1D array
            uncertainties of slopes for pixels in current segment and
            section

        inv_var: float, 1D array
            reciprocals of variances for fits of pixels in current
            segment and section

        Returns
        -------
        None
        """
        self.interc_2d[num_seg[g_pix], g_pix] = intercept[g_pix]
        self.slope_2d[num_seg[g_pix], g_pix] = slope[g_pix]
        self.siginterc_2d[num_seg[g_pix], g_pix] = sig_intercept[g_pix]
        self.sigslope_2d[num_seg[g_pix], g_pix] = sig_slope[g_pix]
        self.inv_var_2d[num_seg[g_pix], g_pix] = inv_var[g_pix]


    def shrink_crmag(self, n_int, dq_cube, imshape, nreads):
        """
        Extended Summary
        ----------------
        Compress the 4D cosmic ray magnitude array for the current
        integration, removing all groups whose cr magnitude is 0 for
        pixels having at least one group with a non-zero magnitude. For
        every integration, the depth of the array is equal to the
        maximum number of cosmic rays flagged in all pixels in all
        integrations.  This routine currently involves a loop over all
        pixels having at least 1 group flagged; if this algorithm takes
        too long for datasets having an overabundance of cosmic rays,
        this routine will require further optimization.

        Parameters
        ----------
        n_int: int
            number of integrations in dataset

        dq_cube: 4D float array
            input data quality array

        imshape: (int, int) tuple
            shape of a single input image

        nreads: int
            number of reads in an integration

        Returns
        ----------
        None

        """
        # Loop over data integrations to find max num of crs flagged per pixel
        # (this could exceed the maximum number of segments fit)
        max_cr = 0
        for ii_int in range(0, n_int):
            dq_int = dq_cube[ii_int, :, :, :]
            dq_cr = np.bitwise_and(dqflags.group['JUMP_DET'], dq_int)
            max_cr_int = (dq_cr > 0.).sum(axis=0).max()
            max_cr = max(max_cr, max_cr_int)

        # Allocate compressed array based on max number of crs
        cr_com = np.zeros((n_int,) + (max_cr,) + imshape, dtype=np.int16)

        # Loop over integrations and groups: for those pix having a cr, add
        #    the magnitude to the compressed array
        for ii_int in range(0, n_int):
            cr_mag_int = self.cr_mag_seg[ii_int, :, :, :]
            cr_int_has_cr = np.where(cr_mag_int.sum(axis=0) != 0)

            # Initialize number of crs for each image pixel for this integration
            end_cr = np.zeros(imshape, dtype=np.int16)

            for k_rd in range(nreads):
                # loop over pixels having a CR
                for nn in range(len(cr_int_has_cr[0])):
                    y, x = cr_int_has_cr[0][nn], cr_int_has_cr[1][nn]

                    if (cr_mag_int[k_rd, y, x] > 0.):
                        cr_com[ii_int, end_cr[y, x], y, x] = cr_mag_int[k_rd, y, x]
                        end_cr[y, x] += 1

        max_num_crs = end_cr.max()
        self.cr_mag_seg = cr_com [:,:max_num_crs,:,:]


    def output_optional(self, model, effintim):
        """
        Short Summary
        -------------
        These results are the cosmic ray magnitudes in the
        segment-specific results for the count rates, y-intercept,
        uncertainty in the slope, uncertainty in the y-intercept,
        pedestal image, fitting weights, and the uncertainties in
        the slope due to poisson noise only and read noise only, and
        the integration-specific results for the pedestal image.  The
        slopes are divided by the effective integration time here to
        yield the count rates.

        Parameters
        ----------
        model: instance of Data Model
            DM object for input

        effintim: float
            effective integration time for a single group

        Returns
        -------
        rfo_model: Data Model object
        """
        rfo_model = \
        datamodels.RampFitOutputModel(\
            slope=self.slope_seg.astype(np.float32) / effintim,
            sigslope=self.sigslope_seg.astype(np.float32),
            var_poisson=self.var_p_seg.astype(np.float32),
            var_rnoise=self.var_r_seg.astype(np.float32),
            yint=self.yint_seg.astype(np.float32),
            sigyint=self.sigyint_seg.astype(np.float32),
            pedestal=self.ped_int.astype(np.float32),
            weights=self.weights.astype(np.float32),
            crmag=self.cr_mag_seg)

        rfo_model.meta.filename = model.meta.filename

        return rfo_model


    def print_full(self):
        """
        Short Summary
        -------------
        Diagnostic function for printing optional output arrays; most
        useful for tiny datasets

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        print('Will now print all optional output arrays - ')
        print(' yint_seg: ')
        print((self.yint_seg))
        print('  ')
        print(' slope_seg: ')
        print(self.slope_seg)
        print('  ')
        print(' sigyint_seg: ')
        print(self.sigyint_seg)
        print('  ')
        print(' sigslope_seg: ')
        print(self.sigslope_seg)
        print('  ')
        print(' inv_var_2d: ')
        print((self.inv_var_2d))
        print('  ')
        print(' firstf_int: ')
        print((self.firstf_int))
        print('  ')
        print(' ped_int: ')
        print((self.ped_int))
        print('  ')
        print(' cr_mag_seg: ')
        print((self.cr_mag_seg))


def alloc_arrays(n_int, imshape, max_seg):
    """
    Short Summary
    -------------
    Allocate arrays for integration-specific results and segment-specific
    results and variances.

    Parameters
    ----------
    n_int: int
        number of integrations

    imshape: (int, int) tuple
        shape of a single image

    max_seg: int
        maximum number of segments fit

    Returns
    -------
    slope_int: float, 3D array
        Cube of integration-specific slopes

    dq_int: int, 3D array
        Cube of integration-specific group data quality values

    var_p3: float, 3D array
        Cube of integration-specific values for the slope variance due to
        Poisson noise only

    var_r3: float, 3D array
        Cube of integration-specific values for the slope variance due to
        readnoise only

    median_diffs_2d: float, 2D array
        Estimated median slopes

    var_p4: float, 4D array
        Hypercube of segment- and integration-specific values for the slope
        variance due to Poisson noise only

    var_r4: float, 4D array
        Hypercube of segment- and integration-specific values for the slope
        variance due to read noise only

    var_both4: float, 4D array
        Hypercube of segment- and integration-specific values for the slope
        variance due to combined Poisson noise and read noise

    var_both3: float, 3D array
        Cube of segment- and integration-specific values for the slope
        variance due to combined Poisson noise and read noise

    inv_var_p4: float, 4D array
        Hypercube of reciprocals of segment- and integration-specific values for
        the slope variance due to Poisson noise only

    inv_var_r4: float, 4D array
        Hypercube of reciprocal of segment- and integration-specific values for
        the slope variance due to read noise only

    inv_var_both4: float, 4D array
        Hypercube of reciprocals of segment- and integration-specific values for
        the slope variance due to combined Poisson noise and read noise

    s_inv_var_p3: float, 3D array
        Cube of reciprocals of segment- and integration-specific values for
        the slope variance due to Poisson noise only, summed over segments

    s_inv_var_r3: float, 3D array
        Cube of reciprocals of segment- and integration-specific values for
        the slope variance due to read noise only, summed over segments

    s_inv_var_both3: float, 3D array
        Cube of reciprocals of segment- and integration-specific values for
        the slope variance due to combined Poisson noise and read noise, summed
        over segments

    segs_4: integer, 4D array
        Hypercube of lengths of segments for all integrations and pixels

    num_seg_per_int: integer, 3D array
        Cube of numbers of segments for all integrations and pixels
    """
    slope_int = np.zeros((n_int,) + imshape, dtype=np.float32)
    dq_int = np.zeros((n_int,) + imshape, dtype=np.uint32)

    # for integration-specific variances
    var_p3 = np.zeros((n_int,) + imshape, dtype=np.float32)
    var_r3 = var_p3.copy() * 0.
    var_both3 = var_r3.copy() * 0.
    s_inv_var_p3 = var_p3.copy() * 0.
    s_inv_var_r3 = var_p3.copy() * 0.
    s_inv_var_both3 = var_p3.copy() * 0.

    # for segment-specific variances
    var_p4 = np.zeros((n_int,)+(max_seg,)+imshape,dtype=np.float32)
    var_r4 = var_p4.copy() * 0.
    var_both4 = var_p4.copy() * 0.
    inv_var_p4 = var_p4.copy() * 0.
    inv_var_r4 = var_p4.copy() * 0.
    inv_var_both4 = var_p4.copy() * 0.

    # number of segments
    segs_4 = np.zeros((n_int,)+(max_seg,)+imshape, dtype=np.uint8)
    num_seg_per_int = np.zeros((n_int,)+imshape, dtype=np.uint8)

    # for estimated median slopes
    median_diffs_2d = np.zeros(imshape,dtype=np.float32)

    return (slope_int, dq_int, var_p3, var_r3, median_diffs_2d, var_p4, var_r4,
            var_both4, var_both3, inv_var_p4, inv_var_r4, inv_var_both4,
            s_inv_var_p3, s_inv_var_r3, s_inv_var_both3, segs_4, num_seg_per_int)


def calc_slope_vars(rn_sect, gain_sect, gdq_sect, group_time, max_seg):
    """
    Short Summary
    -------------
    Calculate the segment-specific variance arrays for the given
    integration.

    Parameters
    ----------
    rn_sect: float, 2D array
        read noise values for all pixels in data section

    gain_sect: float, 2D array
        gain values for all pixels in data section

    gdq_sect: int, 3D array
        data quality flags for pixels in section

    group_time: float
        Time increment between groups, in seconds.

    max_seg: int
        maximum number of segments fit

    Returns
    -------
    den_r3: float, 3D array
        for a given integration, the reciprocal of the denominator of the
        segment-specific variance of the segment's slope due to read noise

    den_p3: float, 3D array
        for a given integration, the reciprocal of the denominator of the
        segment-specific variance of the segment's slope due to Poisson noise

    num_r3: float, 3D array
        numerator of the segment-specific variance of the segment's slope
        due to read noise
 
    segs_beg_3: integer, 3D array
        lengths of segments for all pixels in the given data section and
        integration
    """
    (nreads, asize2, asize1) = gdq_sect.shape
    npix = asize1 * asize2
    imshape = (asize2, asize1)

    # Create integration-specific sections of input arrays for determination
    #   of the variances.
    gdq_2d = gdq_sect[:,:,:].reshape(( nreads, npix ))
    gain_1d = gain_sect.reshape( npix )
    gdq_2d_nan = gdq_2d.copy()  # group dq with SATS will be replaced by nans
    gdq_2d_nan = gdq_2d_nan.astype(np.float32)

    wh_sat = np.where(np.bitwise_and( gdq_2d, dqflags.group['SATURATED'] ))
    if len( wh_sat[0]) > 0:
        gdq_2d_nan[ wh_sat ] = np.nan  # set all SAT groups to nan

    # Get lengths of semiramps for all pix [number_of_semiramps, number_of_pix]
    segs = gdq_2d.copy()* 0.

    # Counter of semiramp for each pixel
    sr_index = np.zeros( npix, dtype=np.uint8 )
    pix_not_done = np.ones( npix, dtype=np.bool)  # initialize to True

    i_read = 0
    # Loop over reads for all pixels to get segments (segments per pixel)
    while (i_read < nreads and np.any(pix_not_done)):
        gdq_1d = gdq_2d_nan[ i_read, :]
        wh_good = np.where( gdq_1d == 0) # good groups

        # if this group is good, increment those pixels' segments' lengths
        if len( wh_good[0] ) > 0:
            segs[ sr_index[ wh_good], wh_good ] += 1

        # Locate any CRs that appear before the first SAT group...
        wh_cr = np.where( gdq_2d_nan[i_read, :] == dqflags.group['JUMP_DET'])

        # ... but not on final read:
        if (len(wh_cr[0]) > 0 and (i_read < nreads-1) ):
            sr_index[ wh_cr[0] ] += 1
            segs[ sr_index[wh_cr], wh_cr ] += 1

        # If current group is a NaN, this pixel is done (pix_not_done is False)
        wh_nan = np.where( np.isnan(gdq_2d_nan[ i_read, :]))
        if len( wh_nan[0]) > 0:
            pix_not_done[ wh_nan[0]] = False

        i_read += 1

    segs = segs.astype(np.uint8)
    segs_beg = segs[:max_seg, :] # the leading nonzero lengths

    # Create reshaped version [ segs, y, x ] to simplify computation
    segs_beg_3 = segs_beg.reshape( max_seg, imshape[0], imshape[1] )

    # Create a version 1 less for later calculations for the variance due to
    #   Poisson, with a floor=1 to handle single-group segments
    wh_pos_3 = np.where(segs_beg_3 > 1)
    segs_beg_3_m1 = segs_beg_3.copy()
    segs_beg_3_m1[wh_pos_3] -= 1
    segs_beg_3_m1[ segs_beg_3_m1 < 1 ] = 1

    # For a segment, the variance due to Poisson noise
    # = slope/(tgroup * gain * (ngroups-1)),
    #   where slope is the estimated median slope, tgroup is the group time,
    #   and ngroups is the number of groups in the segment.
    #   Here the denominator of this quantity will be computed, which will be
    #   later multiplied by the estimated median slope.
    den_p3 = 1./(group_time * gain_1d.reshape(imshape) * segs_beg_3_m1 )
    den_p3 = rem_nan_inf(den_p3)

    # For a segment, the variance due to readnoise noise
    # = 12 * readnoise**2 /(ngroups_seg**3. - ngroups_seg)/( tgroup **2.)
    num_r3 = 12. * (rn_sect/group_time)**2.  # always >0
    # Reshape for every group, every pixel in section
    num_r3 = np.dstack( [num_r3] * max_seg )
    num_r3 = np.transpose( num_r3, (2, 0, 1))

    # Denominator den_r3 = 1./(segs_beg_3 **3. -segs_beg_3). The minimum number
    #   of allowed groups is 2, which will apply if there is actually only 1
    #   group; in this case den_r3 = 1/6. This covers the case in which there is
    #   only one good group at the beginning of the integration, so it will be
    #   be compared to the plane of (near) zeros resulting from the reset. For
    #   longer segments, this value is overwritten below.
    den_r3 = num_r3.copy() * 0. + 1./6
    wh_seg_pos = np.where (segs_beg_3 > 1)
    den_r3[ wh_seg_pos ] = 1./(segs_beg_3[ wh_seg_pos ] **3. -
                             segs_beg_3[ wh_seg_pos ]) # overwrite where segs >1
    den_r3 = rem_nan_inf(den_r3)

    return ( den_r3, den_p3, num_r3, segs_beg_3 )


def calc_pedestal(num_int, slope_int, firstf_int, dq_cube, nframes, groupgap,
                  dropframes1):
    """
    Short Summary
    -------------
    The pedestal is calculated by extrapolating the final slope for
    each pixel from its value at the first sample in the integration to
    an exposure time of zero; this calculation accounts for the values of
    nframes and groupgap.  Any pixel that is saturated on the 1st
    group is given a pedestal value of 0.

    Parameters
    ----------
    num_int: int
        integration number

    slope_int: float, 3D array
        cube of integration-specific slopes

    firstf_int: float, 3D array
        integration-specific first frame array

    dq_cube: int, 4D array
        hypercube of DQ array

    nframes: int
        number of frames averaged per group; from the NFRAMES keyword. Does
        not contain the groupgap.

    groupgap: int
        number of frames dropped between groups, from the GROUPGAP keyword.

    dropframes1: int
        number of frames dropped at the beginning of every integration, from
        the DRPFRMS1 keyword.

    Returns
    -------
    ped: float, 2D array
        pedestal image
    """
    ff_all = firstf_int[num_int, :, :].astype(np.float32)
    dq_first = dq_cube[num_int, 0, :, :]
    ped = ff_all - slope_int[num_int, : :] * \
             (((nframes + 1.)/2. + dropframes1)/(nframes+groupgap))

    ped[np.bitwise_and(dq_first, dqflags.group['SATURATED']
                       ) == dqflags.group['SATURATED']]  = 0
    ped[ np.isnan( ped )] = 0.

    return ped


def output_integ(model, slope_int, dq_int, effintim, var_p3, var_r3, var_both3):

    """
    Short Summary
    -------------
    Construct the output integration-specific results

    Parameters
    ----------
    model: instance of Data Model
       DM object for input

    slope_int: float, 3D array
       Data cube of weighted slopes for each integration

    dq_int: int, 3D array
       Data cube of DQ arrays for each integration

    effintim: float
       Effective integration time per integration

    var_p3: float, 3D array
        Cube of integration-specific values for the slope variance due to
        Poisson noise only

    var_r3: float, 3D array
        Cube of integration-specific values for the slope variance due to
        read noise only

    var_both3: float, 3D array
        Cube of integration-specific values for the slope variance due to
        read noise and Poisson noise

    Returns
    -------
    cubemod: Data Model object

    """
    cubemod = datamodels.CubeModel()
    cubemod.data = slope_int / effintim

    cubemod.err = np.sqrt(var_both3)
    cubemod.err = rem_nan_inf(cubemod.err)

    cubemod.dq = dq_int

    cubemod.var_poisson = var_p3
    cubemod.var_rnoise = var_r3

    cubemod.update(model) # keys from input needed for photom step

    return cubemod


def gls_output_optional(model, intercept_int, intercept_err_int,
                        pedestal_int,
                        ampl_int, ampl_err_int):
    """Construct the optional results for the GLS algorithm.

    Short Summary
    -------------
    Construct the GLS-specific optional output data.
    These results are the Y-intercepts, uncertainties in the intercepts,
    pedestal (first group extrapolated back to zero time),
    cosmic ray magnitudes, and uncertainties in the CR magnitudes.

    Parameters
    ----------
    model: instance of Data Model
        Data model object for input; this is used only for the file name.

    intercept_int: 3-D ndarray, float32, shape (n_int, ny, nx)
        Y-intercept for each integration, at each pixel.

    intercept_err_int: 3-D ndarray, float32, shape (n_int, ny, nx)
        Uncertainties for Y-intercept for each integration, at each pixel.

    pedestal_int: 3-D ndarray, float32, shape (n_int, ny, nx)
        The pedestal, for each integration and each pixel.

    ampl_int: 4-D ndarray, float32, shape (n_int, ny, nx, max_num_cr)
        Cosmic-ray amplitudes for each integration, at each pixel, and for
        each CR hit in the ramp.  max_num_cr will be the maximum number of
        CRs within the ramp for any pixel, or it will be one if there were
        no CRs at all.

    ampl_err_int: 4-D ndarray, float32, shape (n_int, ny, nx, max_num_cr)
        Uncertainties for cosmic-ray amplitudes for each integration, at
        each pixel, and for each CR in the ramp.

    Returns
    -------
    gls_ramp_model: GLS_RampFitModel object
        GLS-specific ramp fit data for the exposure.
    """

    gls_ramp_model = datamodels.GLS_RampFitModel()

    gls_ramp_model.yint = intercept_int
    gls_ramp_model.sigyint = intercept_err_int
    gls_ramp_model.pedestal = pedestal_int
    gls_ramp_model.crmag = ampl_int
    gls_ramp_model.sigcrmag = ampl_err_int

    return gls_ramp_model


def gls_pedestal(first_group, slope_int, s_mask,
                 frame_time, nframes_used):

    """Calculate the pedestal for the GLS case.

    The pedestal is the first group, but extrapolated back to zero time
    using the slope obtained by the fit to the whole ramp.  The time of
    the first group is the frame time multiplied by (M + 1) / 2, where M
    is the number of frames per group, not including the number (if any)
    of skipped frames.

    The input arrays and output pedestal are slices of the full arrays.
    They are just the relevant data for the current integration (assuming
    that this function is called within a loop over integrations), and
    they may include only a subset of image lines.  For example, this
    function might be called with slope_int argument given as:
    `slope_int[num_int, rlo:rhi, :]`.  The input and output parameters
    are in electrons.

    Parameters
    ----------
    first_group: float32, 2-D array
        A slice of the first group in the ramp.

    slope_int: float32, 2-D array
        The slope obtained by GLS ramp fitting.  This is a slice for the
        current integration and a subset of the image lines.

    s_mask: bool, 2-D array
        True for ramps that were saturated in the first group.

    frame_time: float
        The time to read one frame, in seconds.

    nframes_used: int
        Number of frames that were averaged together to make a group.
        Exludes the groupgap.

    Returns
    -------
    pedestal: float32, 2-D array
        This is a slice of the full pedestal array, and it's for the
        current integration.
    """

    M = float(nframes_used)
    pedestal = first_group - slope_int * frame_time * (M + 1.) / 2.
    if s_mask.any():
        pedestal[s_mask] = 0.

    return pedestal


def shift_z(a, off):
    """
    Short Summary
    -------------
    Shift input 3D array by requested offset in z-direction, padding
    shifted array (of the same size) by leading or trailing zeros as
    needed.

    Parameters
    ----------
    a: float, 3D array
        input array

    off: int
        offset in z-direction

    Returns
    -------
    b: float, 3D array
        shifted array

    """
    # set initial and final indices along z-direction for original and
    #    shifted 3D arrays
    ai_z = int((abs(off) + off) / 2)
    af_z = a.shape[0] + int((-abs(off) + off) / 2)

    bi_z = a.shape[0] - af_z
    bf_z = a.shape[0] - ai_z

    b = a * 0
    b[bi_z:bf_z, :, :] = a[ai_z:af_z, :, :]

    return b


def get_efftim_ped(model):
    """
    Short Summary
    -------------
    Calculate the effective integration time for a single group, and return the
    number of frames per group, and the number of frames dropped between groups.

    Parameters
    ----------
    model: instance of Data Model
        DM object for input

    Returns
    -------
    effintim: float
        effective integration time for a single group

    nframes: int
        number of frames averaged per group; from the NFRAMES keyword.

    groupgap: int
        number of frames dropped between groups; from the GROUPGAP keyword.

    dropframes1: int
        number of frames dropped at the beginning of every integration; from
        the DRPFRMS1 keyword, or 0 if the keyword is missing
    """
    groupgap = model.meta.exposure.groupgap
    nframes = model.meta.exposure.nframes
    frame_time = model.meta.exposure.frame_time
    dropframes1 = model.meta.exposure.drop_frames1

    if (dropframes1 is None):    # set to default if missing
        dropframes1 = 0
        log.debug('Missing keyword DRPFRMS1, so setting to default value of 0')
 
    try:
        effintim = (nframes + groupgap) * frame_time
    except TypeError:
        log.error('Can not retrieve values needed to calculate integ. time')

    log.debug('Calculating effective integration time for a single group using:')
    log.debug(' groupgap: %s' % (groupgap))
    log.debug(' nframes: %s' % (nframes))
    log.debug(' frame_time: %s' % (frame_time))
    log.debug(' dropframes1: %s' % (dropframes1))
    log.info('Effective integration time per group: %s' % (effintim))

    return effintim, nframes, groupgap, dropframes1


def get_dataset_info(model):
    """
    Short Summary
    -------------
    Extract values for the number of groups, the number of pixels,
    dataset shapes, the number of integrations, the instrument name,
    the frame time, and the observation time

    Parameters
    ----------
    model: instance of Data Model
       DM object for input

    Returns
    -------
    nreads: int
       number of reads in input dataset

    npix: int
       number of pixels in 2D array

    imshape: (int, int) tuple
       shape of 2D image

    cubeshape: (int, int, int) tuple
       shape of input dataset

    n_int: int
       number of integrations

    instrume: string
       instrument

    frame_time: float
       integration time from TGROUP

    ngroups: int
        number of groups per integration

    group_time: float
        Time increment between groups, in seconds.
    """

    instrume = model.meta.instrument.name
    frame_time = model.meta.exposure.frame_time
    ngroups = model.meta.exposure.ngroups
    group_time = model.meta.exposure.group_time

    n_int = model.data.shape[0]
    nreads = model.data.shape[1]
    asize2 = model.data.shape[2]
    asize1 = model.data.shape[3]

    # If nreads and ngroups are not the same, override the value of ngroups
    #   with nreads, which is more likely to be correct, since it's based on
    #   the image shape.
    if nreads != ngroups:
        log.warning('The value from the key NGROUPS does not (but should) match')
        log.warning('  the value of nreads from the data; will use value of')
        log.warning('  nreads: %s' % (nreads ))
        ngroups = nreads

    npix = asize2 * asize1  # number of pixels in 2D array
    imshape = (asize2, asize1)
    cubeshape = (nreads,) + imshape

    return nreads, npix, imshape, cubeshape, n_int, instrume, frame_time, \
           ngroups, group_time


def get_more_info(model):
    """Get information used by GLS algorithm.

    Parameters
    ----------
    model: instance of Data Model
        DM object for input

    Returns
    -------
    group_time: float
        Time increment between groups, in seconds.

    nframes_used: int
        Number of frames that were averaged together to make a group,
        i.e. excluding skipped frames.

    saturated_flag: int
        Group data quality flag that indicates a saturated pixel.

    jump_flag: int
        Group data quality flag that indicates a cosmic ray hit.
    """

    group_time = model.meta.exposure.group_time
    nframes_used = model.meta.exposure.nframes
    saturated_flag = dqflags.group['SATURATED']
    jump_flag = dqflags.group['JUMP_DET']

    return (group_time, nframes_used, saturated_flag, jump_flag)


def get_max_num_cr(gdq_cube, jump_flag):
    """
    Short Summary
    -------------
    Find the maximum number of cosmic-ray hits in any one pixel.

    Parameters
    ----------
    gdq_cube: 3-D ndarray
        The group data quality array.

    jump_flag: int
        The data quality flag indicating a cosmic-ray hit.

    Returns
    -------
    max_num_cr: int
        The maximum number of cosmic-ray hits for any pixel.
    """

    cr_flagged = np.empty(gdq_cube.shape, dtype=np.uint8)
    cr_flagged[:] = np.where(np.bitwise_and(gdq_cube, jump_flag), 1, 0)
    max_num_cr = cr_flagged.sum(axis=0, dtype=np.int32).max()
    del cr_flagged

    return max_num_cr


def reset_bad_gain(pdq, gain):
    """
    Short Summary
    -------------
    For pixels in the gain array that are either non-positive or NaN, reset the
    the corresponding pixels in the pixel DQ array to NO_GAIN_VALUE and
    DO_NOT_USE so that they will be ignored.

    Parameters
    ----------
    pdq: int, 2D array
        pixel dq array of input model

    gain: float32, 2D array
        grain array from reference file

    Returns
    -------
    pdq: int, 2D array
        pixleldq array of input model, reset to NO_GAIN_VALUE and DO_NOT_USE
        for pixels in the gain array that are either non-positive or NaN.
    """
    wh_g = np.where( gain <= 0.)
    if len(wh_g[0]) > 0:
        pdq[wh_g] = np.bitwise_or( pdq[wh_g], dqflags.pixel['NO_GAIN_VALUE'] )
        pdq[wh_g] = np.bitwise_or( pdq[wh_g], dqflags.pixel['DO_NOT_USE'] )

    wh_g = np.where( np.isnan( gain ))
    if len(wh_g[0]) > 0:
        pdq[wh_g] = np.bitwise_or( pdq[wh_g], dqflags.pixel['NO_GAIN_VALUE'] )
        pdq[wh_g] = np.bitwise_or( pdq[wh_g], dqflags.pixel['DO_NOT_USE'] )

    return pdq


def get_ref_subs(model, readnoise_model, gain_model):
    """
    Short Summary
    -------------
    Get readnoise array for calculation of variance of noiseless ramps, and
    the gain array in case optimal weighting is to be done.

    Parameters
    ----------
    model: data model
        input data model, assumed to be of type RampModel

    readnoise_model: instance of data Model
        readnoise for all pixels

    gain_model: instance of gain Model
        gain for all pixels

    Returns
    -------
    readnoise_2d: float, 2D array; multiplied by gain
        readnoise subarray

    gain_2d: float, 2D array
        gain subarray
    """
    if reffile_utils.ref_matches_sci(model, gain_model):
        gain_2d = gain_model.data
    else:
        log.info('Extracting gain subarray to match science data')
        gain_2d = reffile_utils.get_subarray_data(model, gain_model)

    if reffile_utils.ref_matches_sci(model, readnoise_model):
        readnoise_2d = readnoise_model.data
    else:
        log.info('Extracting readnoise subarray to match science data')
        readnoise_2d = reffile_utils.get_subarray_data(model, readnoise_model)

    readnoise_2d *= gain_2d # convert read noise to correct units

    return readnoise_2d, gain_2d


def rem_nan_inf( input_arr ):
    """
    Short Summary
    -------------
    Remove values of NaN and Inf from array

    Parameters
    ----------
    input_arr: float, array
        input array
    """
    input_arr[ np.isinf(input_arr)] = 0.
    input_arr[ np.isnan(input_arr)] = 0.
    return input_arr
