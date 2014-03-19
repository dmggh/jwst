CREATE TABLE wfc3_tv_chip (
        wtc_data_set_name               varchar(39)     NOT NULL,
        wtc_binaxis1                    smallint        NULL,
        wtc_binaxis2                    smallint        NULL,
        wtc_ccdchip                     smallint        NOT NULL,
        wtc_cd1_1                       float           NULL,
        wtc_cd1_2                       float           NULL,
        wtc_cd2_1                       float           NULL,
        wtc_cd2_2                       float           NULL,
        wtc_crpix1                      float           NULL,
        wtc_crpix2                      float           NULL,
        wtc_crval1                      float           NULL,
        wtc_crval2                      float           NULL,
        wtc_ctype1                      varchar(8)      NULL,
        wtc_ctype2                      varchar(12)     NULL,
        wtc_errcnt                      int             NULL,
        wtc_fillcnt                     int             NULL,
        wtc_goodmax                     float           NULL,
        wtc_goodmean                    float           NULL,
        wtc_goodmin                     float           NULL,
        wtc_ltm1_1                      float           NULL,
        wtc_ltm2_2                      float           NULL,
        wtc_ltv1                        float           NULL,
        wtc_ltv2                        float           NULL,
        wtc_meanblev                    float           NULL,
        wtc_meandark                    float           NULL,
        wtc_meanflsh                    float           NULL,
        wtc_ncombine                    smallint        NULL,
        wtc_ngoodpix                    int             NULL,
        wtc_orientat                    float           NULL,
        wtc_pa_aper                     float           NULL,
        wtc_photbw                      float           NULL,
        wtc_photflam                    float           NULL,
        wtc_photfnu                     float           NULL,
        wtc_photmode                    varchar(50)     NULL,
        wtc_photplam                    float           NULL,
        wtc_photzpt                     float           NULL,
        wtc_podpsff                     char(1)         NULL,
        wtc_sdqflags                    int             NULL,
        wtc_sizaxis1                    int             NULL,
        wtc_sizaxis2                    int             NULL,
        wtc_snrmax                      float           NULL,
        wtc_snrmean                     float           NULL,
        wtc_snrmin                      float           NULL,
        wtc_softerrs                    int             NULL,
        wtc_stdcfff                     char(1)         NULL,
        wtc_stdcffp                     varchar(6)      NULL )
go
