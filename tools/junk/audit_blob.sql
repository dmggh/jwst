alter table crds_hst_actions add user varchar(64) NOT NULL;
alter table crds_hst_actions add `date` varchar(26) NOT NULL;
alter table crds_hst_actions add `action` varchar(19) NOT NULL;
alter table crds_hst_actions add `filename` varchar(64) NOT NULL;
alter table crds_hst_actions add `observatory` varchar(8) NOT NULL;
alter table crds_hst_actions add `instrument` varchar(32) NOT NULL;
alter table crds_hst_actions add `filekind` varchar(32) NOT NULL;
alter table crds_hst_actions add `why` longtext NOT NULL;
alter table crds_hst_actions add `details` longtext NOT NULL;