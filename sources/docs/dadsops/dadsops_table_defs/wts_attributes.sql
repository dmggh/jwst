CREATE TABLE wfc3_tv_science ( 
        wts_data_set_name               varchar(39)     NOT NULL,
        wts_centera1                    int             NULL,
        wts_centera2                    int             NULL,
        wts_expname                     varchar(25)     NULL,
        wts_acc_rdly                    float           NULL,
        wts_aperture                    varchar(16)     NULL,
        wts_atodgna                     float           NULL,
        wts_atodgnb                     float           NULL,
        wts_atodgnc                     float           NULL,
        wts_atodgnd                     float           NULL,
        wts_badinpdq                    smallint        NULL,
        wts_biasleva                    float           NULL,
        wts_biaslevb                    float           NULL,
        wts_biaslevc                    float           NULL,
        wts_biaslevd                    float           NULL,
        wts_cal_ver                     varchar(24)     NULL,
        wts_calibrat                    char(1)         NULL,
        wts_ccdofsab                    int             NULL,
        wts_ccdofscd                    int             NULL,
        wts_ccdofsta                    int             NULL,
        wts_ccdofstb                    int             NULL,
        wts_ccdofstc                    int             NULL,
        wts_ccdofstd                    int             NULL,
        wts_cdbsdata                    varchar(5)      NULL,
        wts_chinject                    varchar(8)      NULL,
        wts_clkdrftr                    float           NULL,
        wts_clkrate                     float           NULL,
        wts_crmask                      char(1)         NULL,
        wts_crradius                    float           NULL,
        wts_crsigmas                    varchar(15)     NULL,
        wts_crsplit                     smallint        NULL,
        wts_crthresh                    float           NULL,
        wts_ctedir                      varchar(8)      NULL,
        wts_cteimage                    varchar(4)      NULL,
        wts_date_obs                    datetime        NULL,
        wts_dec_prop                    float           NULL,
        wts_det_warm                    float           NULL,
        wts_detectid                    varchar(16)     NULL,
        wts_dirimage                    varchar(9)      NULL,
        wts_equinox                     float           NULL,
        wts_expend                      float           NULL,
        wts_expflag                     varchar(13)     NULL,
        wts_expstart                    float           NULL,
        wts_exptime                     float           NULL,
        wts_fgslock                     varchar(18)     NULL,
        wts_filename                    varchar(39)     NULL,
        wts_filetype                    varchar(9)      NULL,
        wts_flashcur                    varchar(7)      NULL,
        wts_flashdur                    float           NULL,
        wts_flashsta                    varchar(16)     NULL,
        wts_fltswver                    varchar(8)      NULL,
        wts_imagetyp                    varchar(18)     NULL,
        wts_initgues                    varchar(3)      NULL,
        wts_instrume                    varchar(6)      NULL,
        wts_meanexp                     float           NULL,
        wts_moonangl                    float           NULL,
        wts_nrptexp                     smallint        NULL,
        wts_nsamp                       smallint        NULL,
        wts_obsmode                     varchar(10)     NULL,
        wts_obstype                     varchar(14)     NULL,
        wts_opus_ver                    varchar(18)     NULL,
        wts_osbandw                     float           NULL,
        wts_oscalfle                    varchar(30)     NULL,
        wts_osdetctr                    varchar(5)      NULL,
        wts_osdshtr                     varchar(6)      NULL,
        wts_oset                        varchar(9)      NULL,
        wts_osetfoc                     float           NULL,
        wts_osfibre                     varchar(9)      NULL,
        wts_osfilt0                     varchar(6)      NULL,
        wts_osfilt1                     varchar(6)      NULL,
        wts_osfilt2                     varchar(6)      NULL,
        wts_osflux                      float           NULL,
        wts_osfshtr                     varchar(6)      NULL,
        wts_oshene                      varchar(6)      NULL,
        wts_oshenedb                    int             NULL,
        wts_osimgpos                    varchar(30)     NULL,
        wts_oslambda                    float           NULL,
        wts_oslamp                      varchar(5)      NULL,
        wts_osld1064                    float           NULL,
        wts_osld1310                    float           NULL,
        wts_osld810                     float           NULL,
        wts_osmrmode                    varchar(11)     NULL,
        wts_osndcorr                    float           NULL,
        wts_osoa_v2                     float           NULL,
        wts_osoa_v2a                    float           NULL,
        wts_osoa_v3                     float           NULL,
        wts_osoa_v3a                    float           NULL,
        wts_ospt                        varchar(8)      NULL,
        wts_ospt_v1                     float           NULL,
        wts_ospt_v2                     float           NULL,
        wts_ospt_v2a                    float           NULL,
        wts_ospt_v3                     float           NULL,
        wts_ospt_v3a                    float           NULL,
        wts_osqthlmp                    float           NULL,
        wts_ossanity                    varchar(3)      NULL,
        wts_osstabla                    float           NULL,
        wts_osstablm                    float           NULL,
        wts_osswmirr                    varchar(16)     NULL,
        wts_oswvfrnt                    varchar(61)     NULL,
        wts_osxelmp                     float           NULL,
        wts_p1_angle                    float           NULL,
        wts_p1_centr                    varchar(3)      NULL,
        wts_p1_frame                    varchar(9)      NULL,
        wts_p1_lspac                    float           NULL,
        wts_p1_npts                     smallint        NULL,
        wts_p1_orint                    float           NULL,
        wts_p1_pspac                    float           NULL,
        wts_p1_purps                    varchar(10)     NULL,
        wts_p1_shape                    varchar(18)     NULL,
        wts_pa_v3                       float           NULL,
        wts_pattern1                    varchar(24)     NULL,
        wts_pattstep                    smallint        NULL,
        wts_pequinox                    varchar(7)      NULL,
        wts_postarg1                    float           NULL,
        wts_postarg2                    float           NULL,
        wts_pr_inv_f                    varchar(20)     NULL,
        wts_pr_inv_l                    varchar(30)     NULL,
        wts_pr_inv_m                    varchar(20)     NULL,
        wts_primesi                     varchar(6)      NULL,
        wts_proc_typ                    varchar(12)     NULL,
        wts_proctime                    float           NULL,
        wts_propaper                    varchar(16)     NULL,
        wts_ra_prop                     float           NULL,
        wts_readnsea                    float           NULL,
        wts_readnseb                    float           NULL,
        wts_readnsec                    float           NULL,
        wts_readnsed                    float           NULL,
        wts_rej_rate                    float           NULL,
        wts_saa_dark                    varchar(9)      NULL,
        wts_saa_exit                    varchar(17)     NULL,
        wts_saa_time                    int             NULL,
        wts_saacrmap                    varchar(18)     NULL,
        wts_sampzero                    float           NULL,
        wts_scalense                    float           NULL,
        wts_sclamp                      varchar(14)     NULL,
        wts_skysub                      varchar(4)      NULL,
        wts_skysum                      float           NULL,
        wts_spclincn                    float           NULL,
        wts_ss_a1crn                    int             NULL,
        wts_ss_a1sze                    float           NULL,
        wts_ss_a2crn                    int             NULL,
        wts_ss_a2sze                    float           NULL,
        wts_ss_aper                     varchar(16)     NULL,
        wts_ss_cbna1                    smallint        NULL,
        wts_ss_cbna2                    smallint        NULL,
        wts_ss_dtctr                    varchar(10)     NULL,
        wts_ss_filt                     varchar(20)     NULL,
        wts_ss_gain                     smallint        NULL,
        wts_ss_nsamp                    smallint        NULL,
        wts_ss_obsmd                    varchar(15)     NULL,
        wts_ss_rpt                      smallint        NULL,
        wts_ss_split                    smallint        NULL,
        wts_ss_subar                    varchar(8)      NULL,
        wts_subarray                    char(1)         NULL,
        wts_sunangle                    float           NULL,
        wts_targname                    varchar(30)     NULL,
        wts_tvenv                       varchar(8)      NULL,
        wts_tvnum                       int             NULL,
        wts_tvstart                     varchar(19)     NULL,
        wts_tvtest                      varchar(32)     NULL,
        wts_utc0                        float           NULL )
go
