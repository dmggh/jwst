create table wfpc2_ref_data (
        w2r_data_set_name               varchar(39)     NOT NULL,
        w2r_program_id                  char(3)         NOT NULL,
        w2r_obset_id                    char(2)         NOT NULL,
        w2r_obsnum                      char(3)         NOT NULL,
        w2r_atodgain                    float           NULL,
        w2r_equinox                     char(8)         NULL,
        w2r_expstart                    datetime        NULL,
        w2r_filter1                     smallint        NULL,
        w2r_filter2                     smallint        NULL,
        w2r_filtnam1                    char(8)         NULL,
        w2r_filtnam2                    char(8)         NULL,
        w2r_imagetyp                    char(18)        NULL,
        w2r_mode                        char(4)         NULL,
        w2r_orientat_1                  float           NULL,
        w2r_orientat_2                  float           NULL,
        w2r_orientat_3                  float           NULL,
        w2r_orientat_4                  float           NULL,
        w2r_proposid                    int             NULL,
        w2r_serials                     char(3)         NULL,
        w2r_shutter                     char(7)         NULL,
        w2r_atodcorr                    char(8)         NULL,
        w2r_biascorr                    char(8)         NULL,
        w2r_blevcorr                    char(8)         NULL,
        w2r_darkcorr                    char(8)         NULL,
        w2r_dophotom                    char(8)         NULL,
        w2r_drizcorr                    char(8)         NULL,
        w2r_flatcorr                    char(8)         NULL,
        w2r_maskcorr                    char(8)         NULL,
        w2r_shadcorr                    char(8)         NULL,
        w2r_wf4tcorr                    char(8)         NULL,
        w2r_atodfile                    char(18)        NULL,
        w2r_biasfile                    char(18)        NULL,
        w2r_blevfile                    char(18)        NULL,
        w2r_cdbsfile                    char(18)        NULL,
        w2r_darkfile                    char(18)        NULL,
        w2r_dgeofile                    char(18)        NULL,
        w2r_flatfile                    char(18)        NULL,
        w2r_maskfile                    char(18)        NULL,
        w2r_shadfile                    char(18)        NULL,
        w2r_wf4tfile                    char(18)        NULL,
        w2r_comptab                     char(18)        NULL,
        w2r_graphtab                    char(18)        NULL,
        w2r_idctab                      char(18)        NULL,
        w2r_offtab                      char(18)        NULL,
        w2r_phottab                     char(18)        NULL,
        w2r_best_atodcorr               char(8)         NULL,
        w2r_best_biascorr               char(8)         NULL,
        w2r_best_blevcorr               char(8)         NULL,
        w2r_best_darkcorr               char(8)         NULL,
        w2r_best_dophotom               char(8)         NULL,
        w2r_best_drizcorr               char(8)         NULL,
        w2r_best_flatcorr               char(8)         NULL,
        w2r_best_maskcorr               char(8)         NULL,
        w2r_best_shadcorr               char(8)         NULL,
        w2r_best_wf4tcorr               char(8)         NULL,
        w2r_best_atodfile               char(18)        NULL,
        w2r_best_biasfile               char(18)        NULL,
        w2r_best_darkfile               char(18)        NULL,
        w2r_best_dgeofile               char(18)        NULL,
        w2r_best_flatfile               char(18)        NULL,
        w2r_best_maskfile               char(18)        NULL,
        w2r_best_shadfile               char(18)        NULL,
        w2r_best_wf4tfile               char(18)        NULL,
        w2r_best_comptab                char(18)        NULL,
        w2r_best_graphtab               char(18)        NULL,
        w2r_best_idctab                 char(18)        NULL,
        w2r_best_offtab                 char(18)        NULL )
go