CREATE TABLE stis_ref_data ( 
        ssr_data_set_name               varchar(39)     NOT NULL,
        ssr_program_id                  char(3)         NOT NULL,
        ssr_obset_id                    char(2)         NOT NULL,
        ssr_obsnum                      char(3)         NOT NULL,
        ssr_aperture                    varchar(16)     NULL,
        ssr_binaxis1                    smallint        NULL,
        ssr_binaxis2                    smallint        NULL,
        ssr_ccdamp                      varchar(3)      NULL,
        ssr_ccdgain                     smallint        NULL,
        ssr_ccdoffst                    int             NULL,
        ssr_cenwave                     smallint        NULL,
        ssr_crsplit                     smallint        NULL,
        ssr_detector                    varchar(10)     NULL,
        ssr_doppon                      char(1)         NULL,
        ssr_lampset                     varchar(6)      NULL,
        ssr_obstype                     varchar(14)     NULL,
        ssr_opt_elem                    varchar(8)      NULL,
        ssr_proposid                    int             NULL,
        ssr_texpstrt                    datetime        NULL,
        ssr_wavecal                     varchar(18)     NULL,
        ssr_atodcorr                    varchar(8)      NULL,
        ssr_backcorr                    varchar(8)      NULL,
        ssr_biascorr                    varchar(8)      NULL,
        ssr_blevcorr                    varchar(8)      NULL,
        ssr_crcorr                      varchar(8)      NULL,
        ssr_darkcorr                    varchar(8)      NULL,
        ssr_dispcorr                    varchar(8)      NULL,
        ssr_doppcorr                    varchar(8)      NULL,
        ssr_dqicorr                     varchar(8)      NULL,
        ssr_expscorr                    varchar(8)      NULL,
        ssr_flatcorr                    varchar(8)      NULL,
        ssr_fluxcorr                    varchar(8)      NULL,
        ssr_geocorr                     varchar(8)      NULL,
        ssr_glincorr                    varchar(8)      NULL,
        ssr_helcorr                     varchar(8)      NULL,
        ssr_lflgcorr                    varchar(8)      NULL,
        ssr_lorscorr                    varchar(8)      NULL,
        ssr_photcorr                    varchar(8)      NULL,
        ssr_rptcorr                     varchar(8)      NULL,
        ssr_sc2dcorr                    varchar(8)      NULL,
        ssr_sgeocorr                    varchar(8)      NULL,
        ssr_shadcorr                    varchar(8)      NULL,
        ssr_wavecorr                    varchar(8)      NULL,
        ssr_x1dcorr                     varchar(8)      NULL,
        ssr_x2dcorr                     varchar(8)      NULL,
        ssr_biasfile                    varchar(18)     NULL,
        ssr_darkfile                    varchar(18)     NULL,
        ssr_dfltfile                    varchar(18)     NULL,
        ssr_lfltfile                    varchar(18)     NULL,
        ssr_pfltfile                    varchar(18)     NULL,
        ssr_sdstfile                    varchar(18)     NULL,
        ssr_shadfile                    varchar(18)     NULL,
        ssr_apdestab                    varchar(18)     NULL,
        ssr_apertab                     varchar(18)     NULL,
        ssr_atodtab                     varchar(18)     NULL,
        ssr_bpixtab                     varchar(18)     NULL,
        ssr_ccdtab                      varchar(18)     NULL,
        ssr_cdstab                      varchar(18)     NULL,
        ssr_crrejtab                    varchar(18)     NULL,
        ssr_disptab                     varchar(18)     NULL,
        ssr_echsctab                    varchar(18)     NULL,
        ssr_exstab                      varchar(18)     NULL,
        ssr_gactab                      varchar(18)     NULL,
        ssr_halotab                     varchar(18)     NULL,
        ssr_idctab                      varchar(18)     NULL,
        ssr_inangtab                    varchar(18)     NULL,
        ssr_lamptab                     varchar(18)     NULL,
        ssr_mlintab                     varchar(18)     NULL,
        ssr_mofftab                     varchar(18)     NULL,
        ssr_pctab                       varchar(18)     NULL,
        ssr_phottab                     varchar(18)     NULL,
        ssr_riptab                      varchar(18)     NULL,
        ssr_sdctab                      varchar(18)     NULL,
        ssr_sptrctab                    varchar(18)     NULL,
        ssr_srwtab                      varchar(18)     NULL,
        ssr_tdctab                      varchar(18)     NULL,
        ssr_tdstab                      varchar(18)     NULL,
        ssr_teltab                      varchar(18)     NULL,
        ssr_wcptab                      varchar(18)     NULL,
        ssr_xtractab                    varchar(18)     NULL,
        ssr_best_atodcorr               varchar(8)      NULL,
        ssr_best_backcorr               varchar(8)      NULL,
        ssr_best_biascorr               varchar(8)      NULL,
        ssr_best_blevcorr               varchar(8)      NULL,
        ssr_best_crcorr                 varchar(8)      NULL,
        ssr_best_darkcorr               varchar(8)      NULL,
        ssr_best_dispcorr               varchar(8)      NULL,
        ssr_best_doppcorr               varchar(8)      NULL,
        ssr_best_dqicorr                varchar(8)      NULL,
        ssr_best_expscorr               varchar(8)      NULL,
        ssr_best_flatcorr               varchar(8)      NULL,
        ssr_best_fluxcorr               varchar(8)      NULL,
        ssr_best_geocorr                varchar(8)      NULL,
        ssr_best_glincorr               varchar(8)      NULL,
        ssr_best_helcorr                varchar(8)      NULL,
        ssr_best_lflgcorr               varchar(8)      NULL,
        ssr_best_lorscorr               varchar(8)      NULL,
        ssr_best_photcorr               varchar(8)      NULL,
        ssr_best_rptcorr                varchar(8)      NULL,
        ssr_best_sc2dcorr               varchar(8)      NULL,
        ssr_best_sgeocorr               varchar(8)      NULL,
        ssr_best_shadcorr               varchar(8)      NULL,
        ssr_best_wavecorr               varchar(8)      NULL,
        ssr_best_x1dcorr                varchar(8)      NULL,
        ssr_best_x2dcorr                varchar(8)      NULL,
        ssr_best_biasfile               varchar(18)     NULL,
        ssr_best_darkfile               varchar(18)     NULL,
        ssr_best_dfltfile               varchar(18)     NULL,
        ssr_best_lfltfile               varchar(18)     NULL,
        ssr_best_pfltfile               varchar(18)     NULL,
        ssr_best_sdstfile               varchar(18)     NULL,
        ssr_best_shadfile               varchar(18)     NULL,
        ssr_best_apdestab               varchar(18)     NULL,
        ssr_best_apertab                varchar(18)     NULL,
        ssr_best_atodtab                varchar(18)     NULL,
        ssr_best_bpixtab                varchar(18)     NULL,
        ssr_best_ccdtab                 varchar(18)     NULL,
        ssr_best_cdstab                 varchar(18)     NULL,
        ssr_best_crrejtab               varchar(18)     NULL,
        ssr_best_disptab                varchar(18)     NULL,
        ssr_best_echsctab               varchar(18)     NULL,
        ssr_best_exstab                 varchar(18)     NULL,
        ssr_best_gactab                 varchar(18)     NULL,
        ssr_best_halotab                varchar(18)     NULL,
        ssr_best_idctab                 varchar(18)     NULL,
        ssr_best_inangtab               varchar(18)     NULL,
        ssr_best_lamptab                varchar(18)     NULL,
        ssr_best_mlintab                varchar(18)     NULL,
        ssr_best_mofftab                varchar(18)     NULL,
        ssr_best_pctab                  varchar(18)     NULL,
        ssr_best_phottab                varchar(18)     NULL,
        ssr_best_riptab                 varchar(18)     NULL,
        ssr_best_sdctab                 varchar(18)     NULL,
        ssr_best_sptrctab               varchar(18)     NULL,
        ssr_best_srwtab                 varchar(18)     NULL,
        ssr_best_tdctab                 varchar(18)     NULL,
        ssr_best_tdstab                 varchar(18)     NULL,
        ssr_best_teltab                 varchar(18)     NULL,
        ssr_best_wcptab                 varchar(18)     NULL,
        ssr_best_xtractab               varchar(18)     NULL,
        ssr_imphttab                    varchar(18)     NULL,
        ssr_best_imphttab               varchar(18)     NULL )
go