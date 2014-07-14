CREATE TABLE otfc_calibration_fields (
        ocf_instrument                  char(6)         NOT NULL,
        ocf_keyword                     varchar(10)     NOT NULL,
        ocf_old_fieldname               varchar(30)     NOT NULL,
        ocf_best_fieldname              varchar(30)     NOT NULL,
        ocf_sequence_number             int             NULL,
        ocf_field_type                  varchar(8)      NOT NULL,
        ocf_file_type                   varchar(7)      NOT NULL )
go
