CREATE TABLE archive_classes ( 
        arc_mission                     varchar(10)     NOT NULL,
        arc_archive_class               char(3)         NOT NULL,
        arc_description                 varchar(80)     NOT NULL,
        arc_instrument_list             varchar(80)     NULL,
        arc_special_processing          varchar(80)     NULL )
go
