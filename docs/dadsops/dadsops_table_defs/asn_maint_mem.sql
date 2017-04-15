CREATE TABLE asn_maint_mem (
        asn_id                          varchar(9)      NOT NULL,
        dataset_name                    varchar(9)      NOT NULL,
        asn_creation_date               datetime        NOT NULL,
        filter                          varchar(23)     NOT NULL,
        sroll                           int             NOT NULL,
        sdx                             int             NOT NULL,
        sdy                             int             NOT NULL,
        jdx                             int             NULL,
        jdy                             int             NULL,
        jflag                           char(1)         NULL,
        cdx                             int             NULL,
        cdy                             int             NULL,
        cerror                          int             NULL,
        cvote1                          tinyint         NULL,
        cvote2                          tinyint         NULL,
        cvote3                          tinyint         NULL,
        cvote4                          tinyint         NULL,
        type                            char(1)         NOT NULL,
        exptime                         float           NOT NULL,
        start_time_dmf                  int             NOT NULL,
        gen_date                        datetime        NOT NULL,
        gen_date_str                    varchar(12)     NOT NULL,
        pipe_status                     char(1)         NULL )
GO