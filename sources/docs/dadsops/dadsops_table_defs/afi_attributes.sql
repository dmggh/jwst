CREATE TABLE archive_files (
        afi_data_set_name               varchar(39)     NOT NULL,
        afi_archive_class               char(3)         NOT NULL,
        afi_generation_date             datetime        NOT NULL,
        afi_mission                     varchar(10)     NOT NULL,
        afi_file_extension              varchar(20)     NOT NULL,
        afi_file_name                   varchar(100)    NOT NULL,
        afi_file_type                   varchar(10)     NOT NULL,
        afi_pre_compress_size           float           NOT NULL,
        afi_post_compress_size          float           NULL,
        afi_checksum                    int             NULL,
        afi_verify_status               varchar(10)     NULL,
        afi_virtual                     char(1)         NOT NULL,
        afi_file_id                     bigint IDENTITY NOT NULL )
go
