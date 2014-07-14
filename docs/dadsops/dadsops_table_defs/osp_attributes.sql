CREATE TABLE otfr_special_processing (
        osp_instrument                  char(6)         NOT NULL,
        osp_data_set_name               varchar(39)     NOT NULL,
        osp_data_source                 varchar(15)     NULL,
        osp_processing_steps            varchar(60)     NULL,                
        osp_pr_number                   int             NULL,
        osp_user_name                   varchar(31)     NOT NULL,
        osp_entry_date                  datetime        NOT NULL,
        osp_status                      char(8)         NOT NULL,
        osp_status_date                 datetime        NULL )
go
