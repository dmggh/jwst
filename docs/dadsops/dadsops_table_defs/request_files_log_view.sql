CREATE VIEW request_files_log AS
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

GO
