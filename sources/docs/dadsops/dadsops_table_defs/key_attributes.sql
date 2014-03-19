CREATE TABLE request_key (
        key_name                        char(6)         NOT NULL,  /* ex. REQNUM, ... */
        key_value                       int             NOT NULL) /* Highest key used so far */
go
