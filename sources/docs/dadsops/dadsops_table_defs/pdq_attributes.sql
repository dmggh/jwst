CREATE TABLE pdq_summary ( 
        pdq_data_set_name               varchar(39)     NOT NULL,
        pdq_program_id                  char(3)         NOT NULL,
        pdq_obset_id                    char(2)         NOT NULL,
        pdq_obsnum                      char(3)         NOT NULL,
        pdq_asn_id                      varchar(10)     NULL,
        pdq_comment_1                   varchar(68)     NULL,
        pdq_comment_2                   varchar(68)     NULL,
        pdq_comment_3                   varchar(68)     NULL,
        pdq_quality                     varchar(68)     NULL,
        pdq_severity_code               smallint        NULL )
go
