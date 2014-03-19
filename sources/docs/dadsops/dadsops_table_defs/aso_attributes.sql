create table assoc_orphan (
        aso_data_set_name               varchar(39)     NOT NULL,
        aso_program_id                  char(3)         NOT NULL,
        aso_obset_id                    char(2)         NOT NULL,
        aso_obsnum                      char(3)         NOT NULL,
        aso_asn_id                      varchar(10)     NOT NULL,
        aso_member_type                 varchar(18)     NOT NULL,
        aso_orphan_type                 varchar(15)     NULL )
go
