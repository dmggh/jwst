CREATE TABLE ingest_up_control (
        iuc_mission                     varchar(8)      NOT NULL,
        iuc_data_id                     varchar(3)      COLLATE SQL_Latin1_General_CP1_CS_AS NOT NULL,
        iuc_remote_pipeline             varchar(20)     NOT NULL,
        iuc_remote_stage                varchar(2)      NOT NULL,
        iuc_remote_success              varchar(1)      NOT NULL,
        iuc_remote_failure              varchar(1)      NOT NULL,
        iuc_remote_alarm                varchar(1)      NOT NULL )
go
