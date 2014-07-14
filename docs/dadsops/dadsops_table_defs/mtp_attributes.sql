CREATE TABLE moving_target_position ( 
        mtp_program_id                  char(3)         NOT NULL,
        mtp_obset_id                    char(2)         NOT NULL,
        mtp_obsnum                      char(3)         NOT NULL,
        mtp_level                       tinyint         NOT NULL,
        mtp_line_number                 tinyint         NOT NULL,
        mtp_spec_text                   varchar(68)     NULL )
go
