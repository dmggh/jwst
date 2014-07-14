CREATE TABLE fixed_target ( 
        fit_program_id                  char(3)         NOT NULL,
        fit_obset_id                    char(2)         NOT NULL,
        fit_obsnum                      char(3)         NOT NULL,
        fit_dec_proper_motion           float           NULL,
        fit_parallax                    float           NULL,
        fit_radial_velocity             float           NULL,
        fit_ra_proper_motion            float           NULL,
        fit_redshift                    float           NULL,
        fit_type                        char(15)        NULL )
go
