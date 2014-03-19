CREATE TABLE requests_log (
        rql_tracking_id                 varchar(20)     NOT NULL,
        rql_user_id                     varchar(31)     NOT NULL,
        rql_request_id                  varchar(30)     NOT NULL,
        rql_medium                      varchar(16)     NOT NULL,
        rql_request_date                datetime        NOT NULL,
        rql_completion                  datetime        NULL,
        rql_status                      varchar(15)     NOT NULL,
        rql_destination                 varchar(255)    NULL,
        rql_nodename                    varchar(255)    NULL,
        rql_num_bytes                   float           NULL,
        rql_origin                      varchar(16)     NULL,
        rql_exec_start_time             datetime        NULL,
        rql_shipped_date                datetime        NULL )
go
