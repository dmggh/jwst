CREATE TABLE acs_mama ( 
        acm_data_set_name               varchar(39)     NOT NULL,
        acm_archive_class               char(3)         NOT NULL,
        acm_generation_date             datetime        NULL,
        acm_end_time                    datetime        NULL,
        acm_firstday                    datetime        NULL,
        acm_lastday                     datetime        NULL,
        acm_maxcnts                     float           NULL,
        acm_maxdqel                     float           NULL,
        acm_meancnts                    float           NULL,
        acm_meandqel                    float           NULL,
        acm_mincnts                     float           NULL,
        acm_mindqel                     float           NULL,
        acm_start_tm                    datetime        NULL,
        acm_sumtype                     char(8)         NULL,
        acm_tottime                     float           NULL )
go
