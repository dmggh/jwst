CREATE TABLE cos_cumulative_images ( 
	csi_data_set_name		varchar(39)     NOT NULL,
        csi_archive_class               char(3)         NOT NULL,
        csi_generation_date             datetime        NULL,
        csi_ccitype                     smallint        NULL,
        csi_counts                      float           NULL,
        csi_date                        varchar(10)     NULL,
        csi_detector                    varchar(10)     NULL,
        csi_expend                      datetime        NULL,
        csi_expstart                    datetime        NULL,
        csi_exptime                     float           NULL,
        csi_numfiles                    int             NULL,
        csi_obsmode                     varchar(8)      NULL,
        csi_segment                     varchar(4)      NULL )
go
