CREATE TABLE cos_tv_segments (
        ctg_data_set_name               varchar(39)     NOT NULL,
        ctg_segment                     varchar(4)      NOT NULL,
        ctg_detector                    varchar(3)      NULL,
        ctg_globlim                     varchar(16)     NULL,
        ctg_globrate                    float           NULL,
        ctg_goodmax                     float           NULL,
        ctg_goodmean                    float           NULL,
        ctg_nbadevnt                    int             NULL,
        ctg_ngoodpix                    int             NULL )
go
