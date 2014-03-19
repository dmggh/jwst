create table assoc_status (
        ast_asn_id                      varchar(10)     NOT NULL,
        ast_asn_status                  char(10)        NOT NULL,
        ast_products_present            char(1)         NOT NULL,
        ast_generation_date             datetime        NULL )
go
