CREATE TABLE oms_summary (
        oss_data_set_name               varchar(39)     NOT NULL,
        oss_program_id                  char(3)         NOT NULL,
        oss_obset_id                    char(2)         NOT NULL,
        oss_obsnum                      char(3)         NOT NULL,
        oss_asn_id                      varchar(10)     NULL,
        oss_config                      char(15)        NULL,
        oss_earthmod                    float           NULL,
        oss_galactic                    float           NULL,
        oss_gsd_dec                     float           NULL,
        oss_gsd_fgs                     char(1)         NULL,
        oss_gsd_id                      varchar(10)     NULL,
        oss_gsd_mag                     float           NULL,
        oss_gsd_ra                      float           NULL,
        oss_gsr_dec                     float           NULL,
        oss_gsr_fgs                     char(1)         NULL,
        oss_gsr_id                      varchar(10)     NULL,
        oss_gsr_mag                     float           NULL,
        oss_gsr_ra                      float           NULL,
        oss_guidecmd                    varchar(20)     NULL,
        oss_mgssprms                    float           NULL,
        oss_moonmod                     float           NULL,
        oss_mv2_p2p                     float           NULL,
        oss_mv3_p2p                     float           NULL,
        oss_opus_ver                    varchar(18)     NULL,
        oss_operate                     datetime        NULL,
        oss_parallel                    varchar(13)     NULL,
        oss_pdb_ver                     varchar(18)     NULL,
        oss_predgsep                    float           NULL,
        oss_primesi                     char(10)        NULL,
        oss_proposid                    int             NULL,
        oss_t_acq2fl                    char(1)         NULL,
        oss_t_actgsp                    char(1)         NULL,
        oss_t_clmper                    char(1)         NULL,
        oss_t_dcfunc                    char(1)         NULL,
        oss_t_fgsfal                    char(1)         NULL,
        oss_t_fosopn                    char(1)         NULL,
        oss_t_fw_err                    char(1)         NULL,
        oss_t_gdact                     char(1)         NULL,
        oss_t_gsfail                    char(1)         NULL,
        oss_t_gsgap                     char(1)         NULL,
        oss_t_hvtoff                    char(1)         NULL,
        oss_t_no_eph                    char(1)         NULL,
        oss_t_no_sam                    char(1)         NULL,
        oss_t_noslew                    char(1)         NULL,
        oss_t_notlm                     char(1)         NULL,
        oss_t_ntmgap                    int             NULL,
        oss_t_sdlost                    char(1)         NULL,
        oss_t_sgstar                    char(1)         NULL,
        oss_t_sisafe                    char(1)         NULL,
        oss_t_sispnd                    char(1)         NULL,
        oss_t_slewng                    char(1)         NULL,
        oss_t_tapdrp                    char(1)         NULL,
        oss_t_tdfdwn                    char(1)         NULL,
        oss_t_tlmprb                    char(1)         NULL,
        oss_t_tmgap                     float           NULL,
        oss_targname                    varchar(30)     NULL,
        oss_tdec_avg                    float           NULL,
        oss_tendtime                    datetime        NULL,
        oss_tlocklos                    float           NULL,
        oss_tnlosses                    smallint        NULL,
        oss_tnrecent                    smallint        NULL,
        oss_tra_avg                     float           NULL,
        oss_trecentr                    float           NULL,
        oss_trollavg                    float           NULL,
        oss_tstrtime                    datetime        NULL,
        oss_tv2_rms                     float           NULL,
        oss_tv3_rms                     float           NULL,
        oss_zodmod                      float           NULL )
go
