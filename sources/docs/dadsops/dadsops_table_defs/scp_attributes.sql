CREATE TABLE scan_parameters ( 
        scp_program_id                  char(3)         NOT NULL,
        scp_obset_id                    char(2)         NOT NULL,
        scp_obsnum                      char(3)         NOT NULL,
        scp_angle_between_sides         float           NULL,
        scp_number_of_lines             int             NULL,
        scp_points_per_line             int             NULL,
        scp_position_angle              float           NULL,
        scp_scan_coord                  char(18)        NULL,
        scp_scan_length                 float           NULL,
        scp_scan_rate                   float           NULL,
        scp_scan_type                   char(18)        NULL,
        scp_scan_width                  float           NULL,
        scp_seconds_per_dwell           float           NULL )
go
