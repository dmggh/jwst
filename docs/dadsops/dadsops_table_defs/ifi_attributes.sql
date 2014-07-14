CREATE TABLE ingest_files (
        ifi_archive_class               varchar(3)      NOT NULL,
        ifi_data_set_name               varchar(39)     NOT NULL,
        ifi_generation_date             datetime        NOT NULL,
        ifi_mission                     varchar(10)     NOT NULL,
        ifi_file_extension              varchar(20)     NOT NULL,
        ifi_file_name                   varchar(100)    NOT NULL,
        ifi_file_type                   varchar(10)     NOT NULL,
        ifi_pre_compress_size           float           NOT NULL,
        ifi_post_compress_size          float           NOT NULL,
        ifi_verify_status               varchar(6)      NOT NULL,
        ifi_checksum                    int             NOT NULL,
        ifi_checksum_status             varchar(6)      NOT NULL,
        ifi_nsa_file_id                 bigint          NOT NULL )
go
