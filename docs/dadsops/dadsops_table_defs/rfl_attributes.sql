CREATE TABLE request_files_log (
        rfl_tracking_id                 varchar(20)     NOT NULL,
        rfl_request_date                datetime        NOT NULL,
        rfl_sequence_num                int             NULL,
        rfl_request_id                  varchar(30)     NOT NULL,
        rfl_archive_class               char(3)         NOT NULL,
        rfl_data_set_name               varchar(39)     NOT NULL,
        rfl_extension                   varchar(20)     NOT NULL,
        rfl_generation_date             datetime        NULL,
        rfl_mission                     varchar(10)     NOT NULL,
        rfl_file_size                   float           NULL,
        rfl_proprietary                 char(1)         NOT NULL,
        rfl_otfc_generated              char(1)         NULL,
        rfl_delivery_date               datetime        NULL,
        rfl_status                      varchar(15)     NOT NULL,
        rfl_status_text                 varchar(225)    NULL )
go
