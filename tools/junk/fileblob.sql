alter table crds_hst_catalog add
       uploaded_as varchar(80) NOT NULL;
alter table crds_hst_catalog add
      creator_name varchar(80) NOT NULL;
alter table crds_hst_catalog add
      deliverer_user varchar(80) NOT NULL;
alter table crds_hst_catalog add
      deliverer_email varchar(80) NOT NULL; 
alter table crds_hst_catalog add
      description longtext NOT NULL;
alter table crds_hst_catalog add
      catalog_link varchar(128) NOT NULL;
alter table crds_hst_catalog add
      replaced_by_filename varchar(128) NOT NULL;
alter table crds_hst_catalog add
      comment longtext NOT NULL;
alter table crds_hst_catalog add
      aperture varchar(80) NOT NULL;

