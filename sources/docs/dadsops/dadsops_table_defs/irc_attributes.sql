CREATE TABLE ingest_rm_control (
        irc_mission                     varchar(8)      NOT NULL,
        irc_data_id                     varchar(3)      COLLATE SQL_Latin1_General_CP1_CS_AS NOT NULL,
        irc_request_type                varchar(10)     NOT NULL,
        irc_file_name_format            varchar(20)     NOT NULL,
        irc_request_data_id             varchar(3)      NOT NULL,
        irc_data_source                 varchar(4)      NOT NULL )
go
