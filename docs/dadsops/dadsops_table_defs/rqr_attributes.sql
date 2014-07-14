CREATE TABLE requests_rolled (
        rqr_tracking_id                 varchar(20)     NOT NULL,
        rqr_request_date                datetime        NOT NULL,
        rqr_process_date                datetime        NOT NULL,
        rqr_rollover_date               datetime        NOT NULL )
go
