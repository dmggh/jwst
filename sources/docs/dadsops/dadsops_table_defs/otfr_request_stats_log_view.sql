CREATE VIEW otfr_request_stats_log AS 
SELECT orl_data_set_name,
       orl_otfr_request_id,
       orl_dads_tracking_id,
       orl_dads_request_date,
       orl_instrume,
       orl_program_id,
       orl_obset_id,
       orl_obsnum,
       orl_out_file_count,
       orl_out_data_set_size,
       orl_trouble_flag,
       orl_cal_success,
       orl_req_receipt_time,
       orl_pod_retr_start_time,
       orl_pod_retr_stop_time,
       orl_sci_proc_start_time,
       orl_sci_proc_stop_time,
       orl_req_response_time 
FROM   dadsops_log..otfr_request_stats_log
go
