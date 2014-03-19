CREATE TABLE archive_files_log_del (
        afl_data_set_name               varchar(39)     NOT NULL,
        afl_archive_class               char(3)         NOT NULL,
        afl_generation_date             datetime        NOT NULL,
        afl_mission                     varchar(10)     NOT NULL,
        afl_file_extension              varchar(20)     NOT NULL,
        afl_file_name                   varchar(100)    NOT NULL,
        afl_file_type                   varchar(10)     NOT NULL,
        afl_pre_compress_size           float           NOT NULL,
        afl_post_compress_size          float           NULL,
        afl_checksum                    int             NULL,
        afl_verify_status               varchar(10)     NULL,
        afl_virtual                     char(1)         NOT NULL,
        afl_file_id                     bigint          NOT NULL )
go
