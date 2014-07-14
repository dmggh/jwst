create table sci_inst_db_join (
        sij_sdb_program_id              char(3)         NOT NULL,
        sij_sdb_obset_id                char(2)         NOT NULL,
        sij_sdb_obsnum                  char(3)         NOT NULL,
        sij_idb_program_id              char(3)         NOT NULL,
        sij_idb_obset_id                char(2)         NOT NULL,
        sij_idb_obsnum                  char(3)         NOT NULL,
        sij_idb_data_set_name           varchar(39)     NOT NULL )
go
