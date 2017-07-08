CREATE TABLE shp_data ( 
        shp_data_set_name               varchar(39)     NOT NULL,
        shp_archive_class               char(3)         NOT NULL,
        shp_program_id                  char(3)         NOT NULL,
        shp_obset_id                    char(2)         NOT NULL,
        shp_obsnum                      char(3)         NOT NULL,
        shp_asn_id                      varchar(10)     NULL,
        shp_accpdate                    datetime        NULL,
        shp_cal_ver                     varchar(40)     NULL,
        shp_calibrat                    char(1)         NULL,
        shp_clkdrftr                    float           NULL,
        shp_clkrate                     float           NULL,
        shp_dcfobsn                     int             NULL,
        shp_fltswver                    varchar(8)      NULL,
        shp_instrume                    char(6)         NULL,
        shp_opus_ver                    varchar(18)     NULL,
        shp_proctime                    float           NULL,
        shp_refframe                    varchar(8)      NULL,
        shp_spclincn                    float           NULL,
        shp_utc0                        datetime        NULL,
        shp_anglesep                    float           NULL,
        shp_aperobj                     char(10)        NULL,
        shp_aperoffx                    float           NULL,
        shp_aperoffy                    float           NULL,
        shp_apersky                     char(10)        NULL,
        shp_apertype                    char(18)        NULL,
        shp_calibtyp                    char(1)         NULL,
        shp_cdbsdata                    char(5)         NULL,
        shp_dgestar                     char(12)        NULL,
        shp_expacket                    int             NULL,
        shp_opformat                    char(18)        NULL,
        shp_pa_ref                      float           NULL,
        shp_prodtype                    char(18)        NULL,
        shp_pstptime                    datetime        NULL,
        shp_pstrtime                    datetime        NULL,
        shp_rtamatch                    char(19)        NULL,
        shp_saaavoid                    char(2)         NULL,
        shp_sgestar                     char(12)        NULL,
        shp_wrd11_14                    smallint        NULL,
        shp_annparra                    float           NULL,
        shp_dec_moon                    float           NULL,
        shp_dec_sun                     float           NULL,
        shp_dec_v1                      float           NULL,
        shp_eqradtrg                    float           NULL,
        shp_flatntrg                    float           NULL,
        shp_postnstx                    float           NULL,
        shp_postnsty                    float           NULL,
        shp_postnstz                    float           NULL,
        shp_ra_moon                     float           NULL,
        shp_ra_sun                      float           NULL,
        shp_ra_v1                       float           NULL,
        shp_rotrttrg                    float           NULL,
        shp_taraqmod                    char(2)         NULL,
        shp_v2aperce                    float           NULL,
        shp_v3aperce                    float           NULL,
        shp_velabbra                    float           NULL,
        shp_velocstx                    float           NULL,
        shp_velocsty                    float           NULL,
        shp_velocstz                    float           NULL,
        shp_cirveloc                    float           NULL,
        shp_cosincli                    float           NULL,
        shp_dec_ref                     float           NULL,
        shp_epchtime                    datetime        NULL,
        shp_eplongpm                    float           NULL,
        shp_hsthorb                     float           NULL,
        shp_longpmer                    float           NULL,
        shp_par_corr                    char(1)         NULL,
        shp_ra_ref                      float           NULL,
        shp_sdma3sq                     float           NULL,
        shp_sdmeanan                    float           NULL,
        shp_t51_angl                    float           NULL,
        shp_t51_rate                    float           NULL,
        shp_targdist                    float           NULL,
        shp_trk_type                    char(3)         NULL,
        shp_argperig                    float           NULL,
        shp_ecbdx3                      float           NULL,
        shp_ecbdx4d3                    float           NULL,
        shp_eccentry                    float           NULL,
        shp_eccentx2                    float           NULL,
        shp_esqdx5d2                    float           NULL,
        shp_fdmeanan                    float           NULL,
        shp_meananom                    float           NULL,
        shp_obsstrtt                    datetime        NULL,
        shp_pep_expo                    char(15)        NULL,
        shp_proposid                    int             NULL,
        shp_rascascn                    float           NULL,
        shp_rcargper                    float           NULL,
        shp_rcascnrd                    float           NULL,
        shp_rcascnrv                    float           NULL,
        shp_semilrec                    float           NULL,
        shp_sineincl                    float           NULL,
        shp_timeffec                    datetime        NULL,
        shp_dec_targ                    float           NULL,
        shp_ra_targ                     float           NULL,
        shp_cmd_exp                     float           NULL,
        shp_col_b_v                     float           NULL,
        shp_col_u_b                     float           NULL,
        shp_col_v_r                     float           NULL,
        shp_e_b_v                       float           NULL,
        shp_extnct_v                    float           NULL,
        shp_linenum                     char(15)        NULL,
        shp_mag_b                       float           NULL,
        shp_mag_r                       float           NULL,
        shp_mag_u                       float           NULL,
        shp_mag_v                       float           NULL,
        shp_mu_epoch                    char(7)         NULL,
        shp_parentid                    int             NULL,
        shp_seqline                     char(15)        NULL,
        shp_seqname                     char(15)        NULL,
        shp_surf_b                      float           NULL,
        shp_surf_r                      float           NULL,
        shp_surf_u                      float           NULL,
        shp_surf_v                      float           NULL,
        shp_tar_type                    char(15)        NULL,
        shp_targ_id                     char(15)        NULL )
go