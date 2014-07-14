CREATE TABLE otfr_keyword_repair (
        okr_instrument                  char(6)         NOT NULL,
	okr_data_set_name               varchar(39)     NOT NULL,
	okr_imset_name                  varchar(10)     NOT NULL,
	okr_imset_value			varchar(30)     NOT NULL,
	okr_telemetry_keyword		varchar(10)     NOT NULL,
	okr_fits_keyword		varchar(10)     NOT NULL,
	okr_keyword_value		varchar(50)     NOT NULL,
	okr_pr_number			int             NOT NULL,
	okr_entry_date			datetime        NOT NULL,
	okr_status			char(8)         NOT NULL,
	okr_status_date        		datetime        NOT NULL,
	okr_status_comment   		varchar(30)     NULL )
go
