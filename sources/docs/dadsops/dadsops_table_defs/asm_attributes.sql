create table assoc_member (
        asm_data_set_name               varchar(39)     NOT NULL,
        asm_program_id                  char(3)         NOT NULL,
        asm_obset_id                    char(2)         NOT NULL,
        asm_obsnum                      char(3)         NOT NULL,
        asm_asn_id                      varchar(10)     NOT NULL,
        asm_member_type                 varchar(18)     NOT NULL,
        asm_member_name                 varchar(9)      NOT NULL )
go
