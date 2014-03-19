CREATE VIEW requests_log AS
SELECT rql_tracking_id,
       rql_user_id,
       rql_request_id,
       rql_medium,
       rql_request_date,
       rql_completion,
       rql_status,
       rql_destination,
       rql_nodename,
       rql_num_bytes,
       rql_origin,
       rql_exec_start_time,
       rql_shipped_date
FROM   dadsops_log..requests_log
go
