CREATE TABLE ingest_data_set_info ( 
        ids_group_data_id               varchar(3)      NOT NULL,
        ids_group_name                  varchar(39)     NOT NULL,
        ids_generation_date             datetime        NOT NULL,
        ids_archive_class               varchar(3)      NOT NULL,
        ids_data_set_name               varchar(39)     NOT NULL,
        ids_mission                     varchar(10)     NOT NULL,
        ids_ins_request_id              varchar(28)     NOT NULL,
        ids_data_source                 varchar(6)      NOT NULL,
        ids_receipt_date                datetime        NOT NULL,
        ids_path_name                   varchar(130)    NOT NULL,
        ids_file_count                  int             NOT NULL,
        ids_clean_delay_days            int             NOT NULL,
        ids_data_set_size               float           NOT NULL,
        ids_install_flag                varchar(1)      NOT NULL,
        ids_nsa_req_date                datetime        NOT NULL,
        ids_nsa_rsp_date                datetime        NOT NULL,
        ids_log_file_name               varchar(39)     NOT NULL )
go
