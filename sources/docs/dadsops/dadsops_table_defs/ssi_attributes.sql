CREATE TABLE stis_cumulative_images ( 
	ssi_data_set_name		varchar(39)     NOT NULL,
        ssi_archive_class               char(3)         NOT NULL,
        ssi_generation_date             datetime        NULL,
        ssi_counts                      float           NULL,
        ssi_date                        varchar(10)     NULL,
        ssi_detector                    varchar(10)     NULL,
        ssi_expend                      datetime        NULL,
        ssi_expstart                    datetime        NULL,
        ssi_exptime                     float           NULL,
        ssi_numfiles                    int             NULL )
go
