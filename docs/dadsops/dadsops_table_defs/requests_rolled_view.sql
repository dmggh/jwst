CREATE VIEW requests_rolled AS
SELECT rqr_tracking_id,
       rqr_request_date,
       rqr_process_date,
       rqr_rollover_date
FROM   dadsops_log..requests_rolled
go
