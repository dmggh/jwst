create table stdb_deadlock (
                date_time        varchar(30)     NULL,
                module           varchar(30)     NULL,
                cmd              int             NULL,
                relname          varchar(30)     NULL,
                dbuser           varchar(20)     NULL,
                node             varchar(10)     NULL,
                retry            int             NULL)
go

grant all on stdb_deadlock to public
go
