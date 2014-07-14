CREATE VIEW data_quality AS
SELECT pdq_data_set_name,
       pdq_program_id,
       pdq_obset_id,
       pdq_obsnum,
       pdq_asn_id, 
       pdq_comment_1,
       pdq_comment_2,
       pdq_comment_3,
       pdq_quality,
       pdq_severity_code,
       psm_severity_value pdq_severity_value
FROM   pdq_summary, pdq_severity_mapping
WHERE  pdq_severity_code = psm_severity_code
GO
