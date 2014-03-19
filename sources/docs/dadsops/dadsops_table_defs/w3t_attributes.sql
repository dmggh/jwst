CREATE TABLE wfc3_times (
        w3t_data_set_name               varchar(39)     NOT NULL,
        w3t_program_id                  char(3)         NOT NULL,
        w3t_obset_id                    char(2)         NOT NULL,
        w3t_obsnum                      char(3)         NOT NULL,
        w3t_deltatim                    float           NULL,
        w3t_routtime                    float           NULL,
        w3t_sampnum                     smallint        NOT NULL,
        w3t_samptime                    float           NULL,
        w3t_tdftrans                    int             NULL )
go
