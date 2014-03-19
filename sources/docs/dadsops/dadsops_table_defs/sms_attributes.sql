CREATE TABLE sms_data ( 
        sms_archive_class               char(3)         NOT NULL, 
        sms_data_set_name               varchar(39)     NOT NULL, 
        sms_generation_date             datetime        NOT NULL, 
        sms_calendar                    char(10)        NULL, 
        sms_pdb_id                      char(10)        NULL )
go
