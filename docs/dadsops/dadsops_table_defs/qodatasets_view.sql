CREATE VIEW qodatasets (
	    sms_id,
            program_id,
            ndatasets,
	    last_obs_time )
AS SELECT
	    sms_id,
            program_id,
            ndatasets,
	    last_obs_time 
FROM opus..qodatasets
go
