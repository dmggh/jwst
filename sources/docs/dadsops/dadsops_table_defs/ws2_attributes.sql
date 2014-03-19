CREATE TABLE wfpc2_secondary_data (
        ws2_data_set_name               varchar(39)     NOT NULL,
        ws2_program_id                  char(3)         NOT NULL,
        ws2_obset_id                    char(2)         NOT NULL,
        ws2_obsnum                      char(3)         NOT NULL,
        ws2_backgrnd_1                  float           NULL,
        ws2_backgrnd_2                  float           NULL,
        ws2_backgrnd_3                  float           NULL,
        ws2_backgrnd_4                  float           NULL,
        ws2_defaults                    char(4)         NULL,
        ws2_histwide_1                  float           NULL,
        ws2_histwide_2                  float           NULL,
        ws2_histwide_3                  float           NULL,
        ws2_histwide_4                  float           NULL,
        ws2_meanc100_1                  float           NULL,
        ws2_meanc100_2                  float           NULL,
        ws2_meanc100_3                  float           NULL,
        ws2_meanc100_4                  float           NULL,
        ws2_meanc10_1                   float           NULL,
        ws2_meanc10_2                   float           NULL,
        ws2_meanc10_3                   float           NULL,
        ws2_meanc10_4                   float           NULL,
        ws2_meanc200_1                  float           NULL,
        ws2_meanc200_2                  float           NULL,
        ws2_meanc200_3                  float           NULL,
        ws2_meanc200_4                  float           NULL,
        ws2_meanc25_1                   float           NULL,
        ws2_meanc25_2                   float           NULL,
        ws2_meanc25_3                   float           NULL,
        ws2_meanc25_4                   float           NULL,
        ws2_meanc300_1                  float           NULL,
        ws2_meanc300_2                  float           NULL,
        ws2_meanc300_3                  float           NULL,
        ws2_meanc300_4                  float           NULL,
        ws2_meanc50_1                   float           NULL,
        ws2_meanc50_2                   float           NULL,
        ws2_meanc50_3                   float           NULL,
        ws2_meanc50_4                   float           NULL,
        ws2_median_1                    float           NULL,
        ws2_median_2                    float           NULL,
        ws2_median_3                    float           NULL,
        ws2_median_4                    float           NULL,
        ws2_medshado_1                  float           NULL,
        ws2_medshado_2                  float           NULL,
        ws2_medshado_3                  float           NULL,
        ws2_medshado_4                  float           NULL,
        ws2_photbw_1                    float           NULL,
        ws2_photbw_2                    float           NULL,
        ws2_photbw_3                    float           NULL,
        ws2_photbw_4                    float           NULL,
        ws2_photflam_1                  float           NULL,
        ws2_photflam_2                  float           NULL,
        ws2_photflam_3                  float           NULL,
        ws2_photflam_4                  float           NULL,
        ws2_photmode_1                  char(48)        NULL,
        ws2_photmode_2                  char(48)        NULL,
        ws2_photmode_3                  char(48)        NULL,
        ws2_photmode_4                  char(48)        NULL,
        ws2_photplam_1                  float           NULL,
        ws2_photplam_2                  float           NULL,
        ws2_photplam_3                  float           NULL,
        ws2_photplam_4                  float           NULL,
        ws2_photzpt_1                   float           NULL,
        ws2_photzpt_2                   float           NULL,
        ws2_photzpt_3                   float           NULL,
        ws2_photzpt_4                   float           NULL,
        ws2_podpsff                     smallint        NULL,
        ws2_rsdpfill                    smallint        NULL,
        ws2_saturate                    smallint        NULL,
        ws2_skewness_1                  float           NULL,
        ws2_skewness_2                  float           NULL,
        ws2_skewness_3                  float           NULL,
        ws2_skewness_4                  float           NULL,
        ws2_stdcfff                     smallint        NULL,
        ws2_stdcffp                     char(6)         NULL,
        ws2_targtype                    char(18)        NULL,
        ws2_uafmptsl                    char(18)        NULL,
        ws2_uafmpwr                     char(18)        NULL,
        ws2_uafmriut                    float           NULL,
        ws2_uatpatmp                    float           NULL,
        ws2_uatpbtmp                    float           NULL,
        ws2_uatpctmp                    float           NULL,
        ws2_ubay1tmp                    float           NULL,
        ws2_ubay2tmp                    float           NULL,
        ws2_ubay3tmp                    float           NULL,
        ws2_ubay4tmp                    float           NULL,
        ws2_ubay5tmp                    float           NULL,
        ws2_ubldasnr                    int             NULL,
        ws2_ubldbsnr                    int             NULL,
        ws2_ucalmirs                    char(8)         NULL,
        ws2_ucalmpwr                    char(3)         NULL,
        ws2_ucanltim                    int             NULL,
        ws2_uch1hjtm                    float           NULL,
        ws2_uchbhtmp                    float           NULL,
        ws2_uchvlts                     float           NULL,
        ws2_ucmodtmp                    float           NULL,
        ws2_uexpocmd                    int             NULL,
        ws2_uexpodur                    int             NULL,
        ws2_uexpotim                    int             NULL,
        ws2_uexptmhi                    int             NULL,
        ws2_ufcstat                     int             NULL,
        ws2_ufmbhtmp                    float           NULL,
        ws2_ufoctm01                    int             NULL,
        ws2_ufoctm02                    int             NULL,
        ws2_ufoctm03                    int             NULL,
        ws2_ufoctm04                    int             NULL,
        ws2_ufoctm05                    int             NULL,
        ws2_ufoctm06                    int             NULL,
        ws2_ufoctm07                    int             NULL,
        ws2_ufoctm08                    int             NULL,
        ws2_ufoctm09                    int             NULL,
        ws2_ufoctm10                    int             NULL,
        ws2_ufoctm11                    int             NULL,
        ws2_uhtpihtr                    char(3)         NULL,
        ws2_ulvpsonf                    char(3)         NULL,
        ws2_umechpwr                    char(3)         NULL,
        ws2_umecvolt                    float           NULL,
        ws2_umntptmp                    float           NULL,
        ws2_un15vadc                    float           NULL,
        ws2_un15vana                    float           NULL,
        ws2_up10vlgc                    float           NULL,
        ws2_up15vadc                    float           NULL,
        ws2_up15vana                    float           NULL,
        ws2_up1afmx                     float           NULL,
        ws2_up1afmy                     float           NULL,
        ws2_up5vadc                     float           NULL,
        ws2_up5vlgc                     float           NULL,
        ws2_upomtemp                    float           NULL,
        ws2_upomxpos                    float           NULL,
        ws2_upomypos                    float           NULL,
        ws2_upyrmdtm                    float           NULL,
        ws2_uradntmp                    float           NULL,
        ws2_uradptmp                    float           NULL,
        ws2_urfiltps                    int             NULL,
        ws2_uriuatmp                    float           NULL,
        ws2_uriubtmp                    float           NULL,
        ws2_urplhtr                     char(3)         NULL,
        ws2_uscale                      float           NULL,
        ws2_uteccur                     float           NULL,
        ws2_utecpwrs                    char(3)         NULL,
        ws2_utecvolt                    float           NULL,
        ws2_utimexpo                    int             NULL,
        ws2_uuvcal                      char(3)         NULL,
        ws2_uuvinsel                    char(8)         NULL,
        ws2_uuvloutm                    float           NULL,
        ws2_uviscal                     char(3)         NULL,
        ws2_uw3afmx                     float           NULL,
        ws2_uw3afmy                     float           NULL,
        ws2_uw4afmx                     float           NULL,
        ws2_uw4afmy                     float           NULL,
        ws2_uwapuse                     char(7)         NULL,
        ws2_uwcancm                     int             NULL,
        ws2_uwlogof                     int             NULL,
        ws2_uwscap                      int             NULL,
        ws2_uzero                       float           NULL,
        ws2_zp_corr_1                   float           NULL,
        ws2_zp_corr_2                   float           NULL,
        ws2_zp_corr_3                   float           NULL,
        ws2_zp_corr_4                   float           NULL )
go
