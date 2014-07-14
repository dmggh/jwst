CREATE VIEW request_files_all AS
SELECT rqf_tracking_id,
       rqf_request_date,
       rqf_sequence_num,
       rqf_request_id,
       rqf_archive_class,
       rqf_data_set_name,
       rqf_extension,
       rqf_generation_date,
       rqf_mission,
       rqf_file_size,
       rqf_proprietary,
       rqf_otfc_generated,
       rqf_delivery_date,
       rqf_status,
       rqf_status_text
FROM   request_files
UNION
SELECT rfl_tracking_id,
       rfl_request_date,
       rfl_sequence_num,
       rfl_request_id,
       rfl_archive_class,
       rfl_data_set_name,
       rfl_extension,
       rfl_generation_date,
       rfl_mission,
       rfl_file_size,
       rfl_proprietary,
       rfl_otfc_generated,
       rfl_delivery_date,
       rfl_status,
       rfl_status_text
FROM   dadsops_log..request_files_log
go
