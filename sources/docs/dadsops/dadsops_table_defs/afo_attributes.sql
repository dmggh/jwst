CREATE TABLE archive_files_old_ver (
        afo_data_set_name               varchar(39)     NOT NULL,
        afo_archive_class               char(3)         NOT NULL,
        afo_generation_date             datetime        NOT NULL,
        afo_mission                     varchar(10)     NOT NULL,
        afo_file_extension              varchar(20)     NOT NULL,
        afo_file_name                   varchar(100)    NOT NULL,
        afo_file_type                   varchar(10)     NOT NULL,
        afo_pre_compress_size           float           NOT NULL,
        afo_post_compress_size          float           NULL,
        afo_checksum                    int             NULL,
        afo_verify_status               varchar(10)     NULL,
        afo_virtual                     char(1)         NOT NULL,
        afo_file_id                     bigint          NOT NULL )
go
