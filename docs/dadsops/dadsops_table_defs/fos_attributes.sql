CREATE TABLE fos_data ( 
        fos_data_set_name               varchar(39)     NOT NULL,
        fos_program_id                  char(3)         NOT NULL,
        fos_obset_id                    char(2)         NOT NULL,
        fos_obsnum                      char(3)         NOT NULL,
        fos_aper_fov                    char(18)        NULL,
        fos_header                      char(1)         NULL,
        fos_trailer                     char(1)         NULL,
        fos_err_corr                    char(8)         NULL,
        fos_gmf_corr                    char(8)         NULL,
        fos_ints                        int             NULL,
        fos_mod_corr                    char(8)         NULL,
        fos_npat                        int             NULL,
        fos_nread                       int             NULL,
        fos_sky_corr                    char(8)         NULL,
        fos_slices                      int             NULL,
        fos_wav_corr                    char(8)         NULL,
        fos_ybase                       int             NULL,
        fos_yrange                      int             NULL,
        fos_yspace                      float           NULL,
        fos_ysteps                      int             NULL,
        fos_date                        datetime        NULL,
        fos_deadtime                    int             NULL,
        fos_decaper1                    float           NULL,
        fos_livetime                    int             NULL,
        fos_maxclk                      int             NULL,
        fos_nmclears                    int             NULL,
        fos_noiselm                     int             NULL,
        fos_podpsff                     char(1)         NULL,
        fos_ra_aper1                    float           NULL,
        fos_stdcfff                     char(1)         NULL,
        fos_xbase                       int             NULL,
        fos_xpitch                      int             NULL,
        fos_ypitch                      int             NULL,
        fos_ystep1                      char(3)         NULL,
        fos_ystep2                      char(3)         NULL,
        fos_ystep3                      char(3)         NULL,
        fos_y1oatmp                     float           NULL,
        fos_y1obtmp                     float           NULL,
        fos_y2oatmp                     float           NULL,
        fos_y2obtmp                     float           NULL,
        fos_y3obtmp                     float           NULL,
        fos_y4obtmp                     float           NULL,
        fos_y5vlpsv                     float           NULL,
        fos_y8vqpsv                     float           NULL,
        fos_yapertmp                    float           NULL,
        fos_yariutmp                    float           NULL,
        fos_ybriutmp                    float           NULL,
        fos_ycalvlt                     float           NULL,
        fos_yceatmp                     float           NULL,
        fos_yclscur                     float           NULL,
        fos_ycpstmp                     float           NULL,
        fos_ydoortmp                    float           NULL,
        fos_ydscrvlt                    float           NULL,
        fos_yfgmatmp                    float           NULL,
        fos_yfgmbtmp                    float           NULL,
        fos_yhvcur                      float           NULL,
        fos_yhvtmp                      float           NULL,
        fos_yhvvlt                      float           NULL,
        fos_exptime                     float           NULL,
        fos_kxbfocus                    float           NULL,
        fos_kybfocus                    float           NULL,
        fos_kybxtilt                    float           NULL,
        fos_kybytilt                    float           NULL,
        fos_proposid                    int             NULL,
        fos_ydatalim                    int             NULL,
        fos_ypamatmp                    float           NULL,
        fos_ypambtmp                    float           NULL,
        fos_ypcatmp                     float           NULL,
        fos_ypcbtmp                     float           NULL,
        fos_ypmfatmp                    float           NULL,
        fos_ypmfbtmp                    float           NULL,
        fos_ypolrtmp                    float           NULL,
        fos_ysigptmp                    float           NULL,
        fos_ytrmfcur                    float           NULL,
        fos_yxdefcur                    float           NULL,
        fos_yxydftmp                    float           NULL,
        fos_yydefcur                    float           NULL,
        fos_yyindfhy                    int             NULL,
        fos_yypath                      int             NULL,
        fos_yfgimpen                    char(1)         NULL,
        fos_yfgimper                    char(3)         NULL )
go