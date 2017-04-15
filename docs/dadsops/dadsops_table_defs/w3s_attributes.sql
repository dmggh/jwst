CREATE TABLE wfc3_science ( 
        w3s_data_set_name               varchar(39)     NOT NULL,
        w3s_program_id                  char(3)         NOT NULL,
        w3s_obset_id                    char(2)         NOT NULL,
        w3s_obsnum                      char(3)         NOT NULL,
        w3s_centera1                    int             NULL,
        w3s_centera2                    int             NULL,
        w3s_expname                     varchar(25)     NULL,
        w3s_acc_rdly                    float           NULL,
        w3s_aperture                    varchar(16)     NULL,
        w3s_atodgna                     float           NULL,
        w3s_atodgnb                     float           NULL,
        w3s_atodgnc                     float           NULL,
        w3s_atodgnd                     float           NULL,
        w3s_badinpdq                    smallint        NULL,
        w3s_biasleva                    float           NULL,
        w3s_biaslevb                    float           NULL,
        w3s_biaslevc                    float           NULL,
        w3s_biaslevd                    float           NULL,
        w3s_cal_ver                     varchar(24)     NULL,
        w3s_calibrat                    char(1)         NULL,
        w3s_ccdofsab                    int             NULL,
        w3s_ccdofscd                    int             NULL,
        w3s_ccdofsta                    int             NULL,
        w3s_ccdofstb                    int             NULL,
        w3s_ccdofstc                    int             NULL,
        w3s_ccdofstd                    int             NULL,
        w3s_cdbsdata                    varchar(5)      NULL,
        w3s_clkdrftr                    float           NULL,
        w3s_clkrate                     float           NULL,
        w3s_crmask                      char(1)         NULL,
        w3s_crradius                    float           NULL,
        w3s_crsigmas                    varchar(15)     NULL,
        w3s_crsplit                     smallint        NULL,
        w3s_crthresh                    float           NULL,
        w3s_ctedir                      varchar(8)      NULL,
        w3s_cteimage                    varchar(4)      NULL,
        w3s_date_obs                    datetime        NULL,
        w3s_dec_prop                    float           NULL,
        w3s_det_warm                    float           NULL,
        w3s_dirimage                    varchar(9)      NULL,
        w3s_equinox                     float           NULL,
        w3s_fgslock                     varchar(18)     NULL,
        w3s_filename                    varchar(39)     NULL,
        w3s_filetype                    varchar(9)      NULL,
        w3s_flashdur                    float           NULL,
        w3s_flashsta                    varchar(16)     NULL,
        w3s_fltswver                    varchar(8)      NULL,
        w3s_imagetyp                    varchar(18)     NULL,
        w3s_initgues                    varchar(8)      NULL,
        w3s_instrume                    varchar(6)      NULL,
        w3s_meanexp                     float           NULL,
        w3s_moonangl                    float           NULL,
        w3s_nrptexp                     smallint        NULL,
        w3s_nsamp                       smallint        NULL,
        w3s_obsmode                     varchar(10)     NULL,
        w3s_obstype                     varchar(14)     NULL,
        w3s_opus_ver                    varchar(18)     NULL,
        w3s_p1_angle                    float           NULL,
        w3s_p1_centr                    varchar(8)      NULL,
        w3s_p1_frame                    varchar(9)      NULL,
        w3s_p1_lspac                    float           NULL,
        w3s_p1_npts                     smallint        NULL,
        w3s_p1_orint                    float           NULL,
        w3s_p1_pspac                    float           NULL,
        w3s_p1_purps                    varchar(10)     NULL,
        w3s_p1_shape                    varchar(18)     NULL,
        w3s_p2_angle                    float           NULL,
        w3s_p2_centr                    varchar(8)      NULL,
        w3s_p2_frame                    varchar(9)      NULL,
        w3s_p2_lspac                    float           NULL,
        w3s_p2_npts                     smallint        NULL,
        w3s_p2_orint                    float           NULL,
        w3s_p2_pspac                    float           NULL,
        w3s_p2_purps                    varchar(10)     NULL,
        w3s_p2_shape                    varchar(18)     NULL,
        w3s_pa_v3                       float           NULL,
        w3s_pattern1                    varchar(30)     NULL,
        w3s_pattern2                    varchar(30)     NULL,
        w3s_pattstep                    smallint        NULL,
        w3s_pequinox                    varchar(7)      NULL,
        w3s_postarg1                    float           NULL,
        w3s_postarg2                    float           NULL,
        w3s_primesi                     varchar(8)      NULL,
        w3s_proc_typ                    varchar(12)     NULL,
        w3s_proctime                    float           NULL,
        w3s_propaper                    varchar(16)     NULL,
        w3s_ra_prop                     float           NULL,
        w3s_readnsea                    float           NULL,
        w3s_readnseb                    float           NULL,
        w3s_readnsec                    float           NULL,
        w3s_readnsed                    float           NULL,
        w3s_rej_rate                    float           NULL,
        w3s_saa_dark                    varchar(9)      NULL,
        w3s_saa_exit                    varchar(17)     NULL,
        w3s_saa_time                    int             NULL,
        w3s_saacrmap                    varchar(18)     NULL,
        w3s_sampzero                    float           NULL,
        w3s_scalense                    float           NULL,
        w3s_sclamp                      varchar(14)     NULL,
        w3s_skysub                      varchar(4)      NULL,
        w3s_skysum                      float           NULL,
        w3s_spclincn                    float           NULL,
        w3s_ss_a1crn                    int             NULL,
        w3s_ss_a1sze                    float           NULL,
        w3s_ss_a2crn                    int             NULL,
        w3s_ss_a2sze                    float           NULL,
        w3s_ss_aper                     varchar(16)     NULL,
        w3s_ss_cbna1                    smallint        NULL,
        w3s_ss_cbna2                    smallint        NULL,
        w3s_ss_dtctr                    varchar(10)     NULL,
        w3s_ss_filt                     varchar(20)     NULL,
        w3s_ss_gain                     float           NULL,
        w3s_ss_nsamp                    smallint        NULL,
        w3s_ss_obsmd                    varchar(15)     NULL,
        w3s_ss_rpt                      smallint        NULL,
        w3s_ss_split                    smallint        NULL,
        w3s_ss_subar                    varchar(8)      NULL,
        w3s_subarray                    char(1)         NULL,
        w3s_sunangle                    float           NULL,
        w3s_targname                    varchar(30)     NULL,
        w3s_utc0                        float           NULL )
go