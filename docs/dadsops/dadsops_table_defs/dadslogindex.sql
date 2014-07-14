/* DADSLOGINDEX.SQL  -- creates all the indices for the DADS Log Database */

ALTER TABLE otfr_request_stats_log ADD CONSTRAINT pk_otfr_request_stats_log PRIMARY KEY
( orl_dads_tracking_id, orl_dads_request_date, orl_data_set_name, orl_req_receipt_time )
go

ALTER TABLE requests_log ADD CONSTRAINT pk_requests_log PRIMARY KEY
( rql_tracking_id, rql_request_date )
go

CREATE NONCLUSTERED INDEX rql_completion ON requests_log
( rql_completion )
go

ALTER TABLE requests_rolled ADD CONSTRAINT pk_requests_rolled PRIMARY KEY
( rqr_tracking_id, rqr_request_date )
go

CREATE UNIQUE CLUSTERED INDEX rfl_primary ON request_files_log
( rfl_tracking_id, rfl_request_date, rfl_sequence_num, rfl_data_set_name, rfl_archive_class, rfl_generation_date, rfl_extension, rfl_mission, rfl_delivery_date )
go

CREATE NONCLUSTERED INDEX rfl_dsn_ac_gd ON request_files_log
( rfl_data_set_name, rfl_archive_class, rfl_generation_date, rfl_mission )
go
