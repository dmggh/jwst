CREATE TABLE fuse_science (
        fes_data_set_name               varchar(39)     NOT NULL,
        fes_archive_class               char(3)         NOT NULL,
        fes_generation_date             datetime        NULL,
        fes_prgrm_id                    char(4)         NOT NULL,
        fes_targ_id                     char(2)         NOT NULL,
        fes_obs_id                      int             NOT NULL,
        fes_asn_id                      varchar(11)     NOT NULL,
        fes_aper_pa                     float           NULL,
        fes_bandwid                     float           NULL,
        fes_centrwv                     float           NULL,
        fes_dateobs                     datetime        NULL,
        fes_dec_targ                    float           NULL,
        fes_ebv                         float           NULL,
        fes_elat                        float           NULL,
        fes_elong                       float           NULL,
        fes_glat                        float           NULL,
        fes_glong                       float           NULL,
        fes_high_pm                     char(1)         NULL,
        fes_mov_targ                    char(1)         NULL,
        fes_objclass                    int             NULL,
        fes_obsend                      datetime        NULL,
        fes_obsstart                    datetime        NULL,
        fes_obstime                     float           NULL,
        fes_obs_stat                    int             NULL,
        fes_pr_inv_f                    varchar(40)     NULL,
        fes_pr_inv_l                    varchar(40)     NULL,
        fes_ra_targ                     float           NULL,
        fes_rawtime                     float           NULL,
        fes_scobs_id                    int             NULL,
        fes_sp_type                     varchar(20)     NULL,
        fes_src_type                    char(2)         NULL,
        fes_targname                    varchar(30)     NULL,
        fes_targtype                    char(1)         NULL,
        fes_telescop                    char(4)         NULL,
        fes_vmag                        float           NULL,
        fes_wavemax                     float           NULL,
        fes_wavemin                     float           NULL,
        fes_z                           float           NULL )
go