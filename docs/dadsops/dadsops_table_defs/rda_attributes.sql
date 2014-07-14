CREATE TABLE restricted_data (
        rda_pep_id                      int             not null,
        rda_proposal_type               varchar(20)     not null,
        rda_proprietary_start_time      datetime        not null,
        rda_insert_date                 datetime        not null,
        rda_username                    varchar(50)     not null,
        rda_comment                     varchar(255)    not null,
        rda_status                      varchar(20)     not null,
        rda_status_date                 datetime        not null )
go
