CREATE VIEW archive_data_set_best AS
SELECT ads_data_set_name, 
       ads_archive_class, 
       ads_generation_date, 
       ads_mission, 
       ads_instrument, 
       ads_program_id, 
       ads_obset_id, 
       ads_obsnum, 
       ads_pep_id, 
       ads_start_time, 
       ads_end_time, 
       ads_data_receipt_time, 
       ads_completion_time, 
       ads_best_version, 
       ads_data_set_size, 
       ads_data_source, 
       ads_file_count, 
       ads_build_num, 
       ads_release_date, 
       ads_release_date_mod
FROM   archive_data_set_all
WHERE  ads_best_version = 'Y'
GO
