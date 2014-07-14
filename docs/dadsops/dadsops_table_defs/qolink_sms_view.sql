CREATE VIEW qolink_sms (
            program_id,
            obset_id,
	    ob_number,
	    sms_id,
	    status )
AS SELECT
            program_id,
	    obset_id,
	    ob_number,
	    sms_id,
	    status
FROM opus..qolink_sms
go
