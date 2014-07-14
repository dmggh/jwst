CREATE TABLE requests (
        req_tracking_id                 varchar(20)     NOT NULL,
        req_user_id                     varchar(31)     NOT NULL,
        req_request_id                  varchar(30)     NOT NULL,
        req_medium                      varchar(16)     NOT NULL,
        req_request_date                datetime        NOT NULL,
        req_completion                  datetime        NULL,
        req_status                      varchar(15)     NOT NULL,
        req_destination                 varchar(255)    NULL,
        req_nodename                    varchar(255)    NULL,
        req_num_bytes                   float           NULL,
        req_origin                      varchar(16)     NULL,
        req_exec_start_time             datetime        NULL,
        req_shipped_date                datetime        NULL )
go
