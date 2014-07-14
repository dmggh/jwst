CREATE TABLE request_operator_actions (
        roa_request_id                  varchar(30)     NOT NULL,
        roa_action_time                 datetime        NOT NULL,
        roa_action_type                 varchar(20)     NOT NULL,
        roa_operator                    varchar(31)     NOT NULL,
        roa_action_reason               varchar(255)    NOT NULL )
go

