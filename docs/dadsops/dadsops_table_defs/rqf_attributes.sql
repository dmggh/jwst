CREATE TABLE request_files (
        rqf_tracking_id                 varchar(20)     NOT NULL,
        rqf_request_date                datetime        NOT NULL,
        rqf_sequence_num                int             NOT NULL,
        rqf_request_id                  varchar(30)     NOT NULL,
        rqf_archive_class               char(3)         NOT NULL,
        rqf_data_set_name               varchar(39)     NOT NULL,
        rqf_extension                   varchar(20)     NOT NULL,
        rqf_generation_date             datetime        NOT NULL,
        rqf_mission                     varchar(10)     NOT NULL,
        rqf_file_size                   float           NULL,
        rqf_proprietary                 char(1)         NOT NULL,
        rqf_otfc_generated              char(1)         NULL,
        rqf_delivery_date               datetime        NOT NULL,
        rqf_status                      varchar(15)     NOT NULL,
        rqf_status_text                 varchar(225)    NULL )
go
