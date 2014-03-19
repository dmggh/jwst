CREATE TABLE stis_grand_mama ( 
        ssg_data_set_name               varchar(39)     NOT NULL, 
        ssg_detector                    varchar(10)     NULL,
        ssg_end_time                    datetime        NULL,
        ssg_firstday                    datetime        NULL,
        ssg_lastday                     datetime        NULL,
        ssg_maxcnts                     float           NULL,
        ssg_maxdqel                     float           NULL,
        ssg_meancnts                    float           NULL,
        ssg_meandqel                    float           NULL,
        ssg_medcnts                     float           NULL,
        ssg_mincnts                     float           NULL,
        ssg_mindqel                     float           NULL,
        ssg_start_tm                    datetime        NULL,
        ssg_sumtype                     char(8)         NULL,
        ssg_totsubt                     float           NULL,
        ssg_tottime                     float           NULL )
go
