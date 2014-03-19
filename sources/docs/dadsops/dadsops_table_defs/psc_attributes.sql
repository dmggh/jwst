CREATE TABLE proprietary_special_cases (
        psc_pep_id                      int             not null,
        psc_proposal_type               varchar(20)     not null,
        psc_data_set_name               varchar(39)     not null,
        psc_program_id                  char(3)         not null,
        psc_obset_id                    char(2)         not null,
        psc_obsnum                      char(3)         not null,
        psc_proprietary_start_time      datetime        null,
        psc_release_date                datetime        not null,
        psc_change_date                 datetime        not null,
        psc_username                    varchar(50)     not null,
        psc_comment                     varchar(255)    not null,
        psc_status                      varchar(20)     not null,
        psc_status_date                 datetime        not null )
go

