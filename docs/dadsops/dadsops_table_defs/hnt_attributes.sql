CREATE TABLE hst_notification_track (
        hnt_program_id                  char(3)         NOT NULL,
        hnt_pep_id                      int             NOT NULL,
        hnt_sms_id                      varchar(9)      NOT NULL,
        hnt_archive_start               datetime        NULL,
        hnt_data_available              datetime        NULL,
        hnt_skip                        char(1)         NOT NULL )
go

