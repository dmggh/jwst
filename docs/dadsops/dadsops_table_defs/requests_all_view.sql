CREATE VIEW requests_all AS
SELECT req_tracking_id,
       req_user_id,
       req_request_id,
       req_medium,
       req_request_date,
       req_completion,
       req_status,
       req_destination,
       req_nodename,
       req_num_bytes,
       req_origin,
       req_exec_start_time,
       req_shipped_date
FROM   requests
UNION
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
