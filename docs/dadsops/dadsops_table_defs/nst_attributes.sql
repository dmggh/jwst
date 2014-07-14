CREATE TABLE nicmos_times (
        nst_program_id                  char(3)         NOT NULL,
        nst_obset_id                    char(2)         NOT NULL,
        nst_obsnum                      char(3)         NOT NULL,
        nst_sampnum                     smallint        NOT NULL,
        nst_deltatim                    float           NULL,
        nst_extver                      smallint        NULL,
        nst_routtime                    datetime        NULL,
        nst_samptime                    float           NULL )
go
