/* DADSINDEX.SQL  -- creates all the indices for the DADS Database */
/* Note: When inserting a new index into this file place it in     */
/*       it's alphabetical position by table name.                 */

ALTER TABLE acs_a_data ADD CONSTRAINT pk_acs_a_data PRIMARY KEY
( aca_program_id, aca_obset_id, aca_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX aca_dsname_index ON acs_a_data
( aca_data_set_name )
go

ALTER TABLE acs_chip ADD CONSTRAINT pk_acs_chip PRIMARY KEY
( acc_program_id, acc_obset_id, acc_obsnum, acc_ccdchip )
go

ALTER TABLE acs_mama ADD CONSTRAINT pk_acs_mama PRIMARY KEY
( acm_data_set_name )
go

ALTER TABLE acs_ref_data ADD CONSTRAINT pk_acs_ref_data PRIMARY KEY
( acr_program_id, acr_obset_id, acr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX acr_dsname_index ON acs_ref_data
( acr_data_set_name )
go

ALTER TABLE acs_science ADD CONSTRAINT pk_acs_science PRIMARY KEY
( acs_program_id, acs_obset_id, acs_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX acs_dsname_index ON acs_science
( acs_data_set_name )
go

ALTER TABLE archive_classes ADD CONSTRAINT pk_archive_classes PRIMARY KEY
( arc_mission, arc_archive_class )
go

ALTER TABLE archive_data_set_all ADD CONSTRAINT pk_archive_data_set_all PRIMARY KEY
( ads_data_set_name, ads_archive_class, ads_generation_date, ads_mission )
go

CREATE NONCLUSTERED INDEX ads_observation_index ON archive_data_set_all
( ads_program_id, ads_obset_id, ads_obsnum )
go

CREATE NONCLUSTERED INDEX ads_pep_id_index ON archive_data_set_all
( ads_pep_id )
go

CREATE NONCLUSTERED INDEX ads_data_receipt_index ON archive_data_set_all
( ads_data_receipt_time )
go

ALTER TABLE archive_data_set_log_del ADD CONSTRAINT pk_archive_data_set_log_del PRIMARY KEY
( adl_data_set_name, adl_archive_class, adl_generation_date, adl_mission )
WITH (IGNORE_DUP_KEY=ON)
go

ALTER TABLE archive_data_set_old_ver ADD CONSTRAINT pk_archive_data_set_old_ver PRIMARY KEY
( ado_data_set_name, ado_archive_class, ado_generation_date, ado_mission )
WITH (IGNORE_DUP_KEY=ON)
go

ALTER TABLE archive_files ADD CONSTRAINT pk_archive_files PRIMARY KEY
( afi_file_id )
go

CREATE UNIQUE NONCLUSTERED INDEX ix_afi_dsn ON archive_files
( afi_data_set_name, afi_archive_class, afi_generation_date, afi_file_extension, afi_mission )
go

ALTER TABLE archive_files_log_del ADD CONSTRAINT pk_archive_files_log_del PRIMARY KEY
( afl_file_id )
WITH (IGNORE_DUP_KEY=ON)
go

CREATE UNIQUE NONCLUSTERED INDEX ix_afl_dsn ON archive_files_log_del
( afl_data_set_name, afl_archive_class, afl_generation_date, afl_file_extension, afl_mission )
go

ALTER TABLE archive_files_old_ver ADD CONSTRAINT pk_archive_files_old_ver PRIMARY KEY
( afo_file_id )
WITH (IGNORE_DUP_KEY=ON)
go

CREATE UNIQUE NONCLUSTERED INDEX ix_afo_dsn ON archive_files_old_ver
( afo_data_set_name, afo_archive_class, afo_generation_date, afo_file_extension, afo_mission )
go

ALTER TABLE archive_messages ADD CONSTRAINT pk_archive_messages PRIMARY KEY
( ame_message_id )
go

ALTER TABLE archive_operator_properties ADD CONSTRAINT pk_archive_operator_properties PRIMARY KEY
(aor_user_id, aor_prop_name)
go

ALTER TABLE archive_operators ADD CONSTRAINT pk_archive_operators PRIMARY KEY
( aop_user_id )
go

ALTER TABLE ArchiveFileNsaFileInfo ADD CONSTRAINT PK_ArchiveFileNsaFileInfo PRIMARY KEY
( ArchiveFileID )
go

CREATE NONCLUSTERED INDEX asn_maint_asn_id_idx ON asn_maint
( asn_id )
go

CREATE NONCLUSTERED INDEX asn_maint_mem_asn_id_idx ON asn_maint_mem
( asn_id )
go

CREATE NONCLUSTERED INDEX asn_maint_mem_dsname_idx ON asn_maint_mem
( dataset_name )
go

ALTER TABLE assoc_member ADD CONSTRAINT pk_assoc_member PRIMARY KEY
( asm_asn_id, asm_program_id, asm_obset_id, asm_obsnum )
go

CREATE NONCLUSTERED INDEX asm_pso_index ON assoc_member
( asm_program_id, asm_obset_id, asm_obsnum )
go

CREATE NONCLUSTERED INDEX asm_dsn_index ON assoc_member
( asm_data_set_name )
go

ALTER TABLE assoc_orphan ADD CONSTRAINT pk_assoc_orphan PRIMARY KEY
( aso_asn_id, aso_program_id, aso_obset_id, aso_obsnum )
go

CREATE NONCLUSTERED INDEX aso_pso_index ON assoc_orphan
( aso_program_id, aso_obset_id, aso_obsnum )
go

ALTER TABLE assoc_status ADD CONSTRAINT pk_assoc_status PRIMARY KEY
( ast_asn_id )
go

ALTER TABLE authorized_users ADD CONSTRAINT pk_authorized_users PRIMARY KEY
( atu_pep_id, atu_user_id )
go

CREATE NONCLUSTERED INDEX atu_user_id_index ON authorized_users
( atu_user_id )
go

ALTER TABLE cos_a_data ADD CONSTRAINT pk_cos_a_data PRIMARY KEY
( csa_program_id, csa_obset_id, csa_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX csa_dsname_index ON cos_a_data
( csa_data_set_name )
go

ALTER TABLE cos_b_data ADD CONSTRAINT pk_cos_b_data PRIMARY KEY
( csb_program_id, csb_obset_id, csb_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX csb_dsname_index ON cos_b_data
( csb_data_set_name )
go

ALTER TABLE cos_c_data ADD CONSTRAINT pk_cos_c_data PRIMARY KEY
( csc_program_id, csc_obset_id, csc_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX csc_dsname_index ON cos_c_data
( csc_data_set_name )
go

ALTER TABLE cos_cumulative_images ADD CONSTRAINT pk_cos_cumulative_images PRIMARY KEY
( csi_data_set_name )
go

ALTER TABLE cos_d_data ADD CONSTRAINT pk_cos_d_data PRIMARY KEY
( csd_program_id, csd_obset_id, csd_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX csd_dsname_index ON cos_d_data
( csd_data_set_name )
go

ALTER TABLE cos_ref_data ADD CONSTRAINT pk_cos_ref_data PRIMARY KEY
( csr_program_id, csr_obset_id, csr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX csr_dsname_index ON cos_ref_data
( csr_data_set_name )
go

ALTER TABLE cos_science ADD CONSTRAINT pk_cos_science PRIMARY KEY
( css_program_id, css_obset_id, css_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX css_dsname_index ON cos_science
( css_data_set_name )
go

ALTER TABLE cos_tv_exposures ADD CONSTRAINT pk_cos_tv_exposures PRIMARY KEY
( ctx_data_set_name )
go

ALTER TABLE cos_tv_int_data ADD CONSTRAINT pk_cos_tv_int_data PRIMARY KEY
( cti_data_set_name )
go

ALTER TABLE cos_tv_ref_data ADD CONSTRAINT pk_cos_tv_ref_data PRIMARY KEY
( ctr_data_set_name )
go

ALTER TABLE cos_tv_science ADD CONSTRAINT pk_cos_tv_science PRIMARY KEY
( cts_data_set_name )
go

ALTER TABLE cos_tv_segments ADD CONSTRAINT pk_cos_tv_segments PRIMARY KEY
( ctg_data_set_name, ctg_segment )
go

ALTER TABLE fgs_data ADD CONSTRAINT pk_fgs_data PRIMARY KEY
( fgs_program_id, fgs_obset_id, fgs_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX fgs_dsname_index ON fgs_data
( fgs_data_set_name )
go

ALTER TABLE fixed_target ADD CONSTRAINT pk_fixed_target PRIMARY KEY
( fit_program_id, fit_obset_id, fit_obsnum )
go

ALTER TABLE foc_data ADD CONSTRAINT pk_foc_data PRIMARY KEY
( foc_program_id, foc_obset_id, foc_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX foc_dsname_index ON foc_data
( foc_data_set_name )
go

ALTER TABLE foc_ref_data ADD CONSTRAINT pk_foc_ref_data PRIMARY KEY
( fcr_program_id, fcr_obset_id, fcr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX fcr_dsname_index ON foc_ref_data
( fcr_data_set_name )
go

ALTER TABLE fos_data ADD CONSTRAINT pk_fos_data PRIMARY KEY
( fos_program_id, fos_obset_id, fos_obsnum )
go
CREATE UNIQUE NONCLUSTERED INDEX fos_dsname_index ON fos_data
( fos_data_set_name )
go

ALTER TABLE fos_ref_data ADD CONSTRAINT pk_fos_ref_data PRIMARY KEY
( fsr_program_id, fsr_obset_id, fsr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX fsr_dsname_index ON fos_ref_data
( fsr_data_set_name )
go

ALTER TABLE fuse_authorized_users ADD CONSTRAINT pk_fuse_authorized_users PRIMARY KEY
( fea_prgrm_id, fea_user_id )
go

CREATE NONCLUSTERED INDEX fea_user_id_index ON fuse_authorized_users
( fea_user_id )
go

ALTER TABLE fuse_exposures ADD CONSTRAINT pk_fuse_exposures PRIMARY KEY
( fee_data_set_name, fee_archive_class )
go

CREATE NONCLUSTERED INDEX fee_user_id_index ON fuse_exposures
( fee_asn_id )
go

ALTER TABLE fuse_member ADD CONSTRAINT pk_fuse_member PRIMARY KEY
( fem_data_set_name, fem_asn_id )
go

CREATE NONCLUSTERED INDEX fem_asn_id_index ON fuse_member
( fem_asn_id )
go

ALTER TABLE fuse_science ADD CONSTRAINT pk_fuse_science PRIMARY KEY
( fes_data_set_name, fes_archive_class )
go

ALTER TABLE hrs_data ADD CONSTRAINT pk_hrs_data PRIMARY KEY
( hrs_program_id, hrs_obset_id, hrs_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX hrs_dsname_index ON hrs_data
( hrs_data_set_name )
go

ALTER TABLE hrs_ref_data ADD CONSTRAINT pk_hrs_ref_data PRIMARY KEY
( hsr_program_id, hsr_obset_id, hsr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX hsr_dsname_index ON hrs_ref_data
( hsr_data_set_name )
go

ALTER TABLE hsp_data ADD CONSTRAINT pk_hsp_data PRIMARY KEY
( hsp_program_id, hsp_obset_id, hsp_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX hsp_dsname_index ON hsp_data
( hsp_data_set_name )
go

ALTER TABLE hsp_ref_data ADD CONSTRAINT pk_hsp_ref_data PRIMARY KEY
( hpr_program_id, hpr_obset_id, hpr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX hpr_dsname_index ON hsp_ref_data
( hpr_data_set_name )
go

ALTER TABLE hst_notification_track ADD CONSTRAINT pk_hst_notification_track PRIMARY KEY
( hnt_program_id, hnt_pep_id, hnt_sms_id )
go

CREATE UNIQUE NONCLUSTERED INDEX hnt_sms_id_index ON hst_notification_track
( hnt_sms_id, hnt_program_id )
go

ALTER TABLE ingest_cleanup ADD CONSTRAINT pk_ingest_cleanup PRIMARY KEY
( icl_archive_class )
go

ALTER TABLE ingest_data_set_info ADD CONSTRAINT pk_ingest_data_set_info PRIMARY KEY
( ids_group_name, ids_group_data_id, ids_generation_date, ids_archive_class, ids_data_set_name, ids_mission )
go

CREATE UNIQUE NONCLUSTERED INDEX ids_request_index ON ingest_data_set_info
( ids_ins_request_id )
go

CREATE UNIQUE NONCLUSTERED INDEX ids_dataset_index ON ingest_data_set_info
( ids_archive_class, ids_data_set_name, ids_generation_date, ids_mission )
go

ALTER TABLE ingest_files ADD CONSTRAINT pk_ingest_files PRIMARY KEY
( ifi_archive_class, ifi_data_set_name, ifi_generation_date, ifi_file_extension, ifi_mission )
go
ALTER TABLE ingest_long_ext ADD CONSTRAINT pk_ingest_long_ext PRIMARY KEY
( ile_long_ext, ile_is_product, ile_mission )
go

CREATE UNIQUE NONCLUSTERED INDEX ile_ext_index ON ingest_long_ext
( ile_file_extension, ile_mission )
go

ALTER TABLE ingest_rm_control ADD CONSTRAINT pk_ingest_rm_control PRIMARY KEY
( irc_mission, irc_data_id )
go

ALTER TABLE ingest_up_control ADD CONSTRAINT pk_ingest_up_control PRIMARY KEY
( iuc_mission, iuc_data_id )
go

ALTER TABLE moving_target_position ADD CONSTRAINT pk_moving_target_position PRIMARY KEY
( mtp_program_id, mtp_obset_id, mtp_obsnum, mtp_level, mtp_line_number )
go

ALTER TABLE nicmos_a_data ADD CONSTRAINT pk_nicmos_a_data PRIMARY KEY
( nsa_program_id, nsa_obset_id, nsa_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX nsa_dsname_index ON nicmos_a_data
( nsa_data_set_name )
go

ALTER TABLE nicmos_b_data ADD CONSTRAINT pk_nicmos_b_data PRIMARY KEY
( nsb_program_id, nsb_obset_id, nsb_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX nsb_dsname_index ON nicmos_b_data
( nsb_data_set_name )
go

ALTER TABLE nicmos_c_data ADD CONSTRAINT pk_nicmos_c_data PRIMARY KEY
( nsc_program_id, nsc_obset_id, nsc_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX nsc_dsname_index ON nicmos_c_data
( nsc_data_set_name )
go

ALTER TABLE nicmos_ref_data ADD CONSTRAINT pk_nicmos_ref_data PRIMARY KEY
( nsr_program_id, nsr_obset_id, nsr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX nsr_dsname_index ON nicmos_ref_data
( nsr_data_set_name )
go

ALTER TABLE nicmos_science ADD CONSTRAINT pk_nicmos_science PRIMARY KEY
( nss_program_id, nss_obset_id, nss_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX nss_dsname_index ON nicmos_science
( nss_data_set_name )
go

ALTER TABLE nicmos_times ADD CONSTRAINT pk_nicmos_times PRIMARY KEY
( nst_program_id, nst_obset_id, nst_obsnum, nst_sampnum )
go

ALTER TABLE NsaMediaType ADD CONSTRAINT PK_NsaMediaType PRIMARY KEY
( mission, archiveClass, mediaType )
go

ALTER TABLE oms_data ADD CONSTRAINT pk_oms_data PRIMARY KEY
( oms_program_id, oms_obset_id, oms_obsnum, oms_data_set_name )
go

CREATE NONCLUSTERED INDEX oms_dsname_index ON oms_data
( oms_data_set_name )
go

ALTER TABLE oms_summary ADD CONSTRAINT pk_oms_summary PRIMARY KEY
( oss_program_id, oss_obset_id, oss_obsnum )
go

CREATE NONCLUSTERED INDEX oss_dsname_index ON oms_summary
( oss_data_set_name )
go

ALTER TABLE otf_support ADD CONSTRAINT pk_otf_support PRIMARY KEY
( ots_mission, ots_instrument, ots_archive_class )
go

ALTER TABLE otfc_calibration_fields ADD CONSTRAINT pk_otfc_calibration_fields PRIMARY KEY
( ocf_instrument, ocf_keyword, ocf_old_fieldname, ocf_best_fieldname, ocf_file_type )
go

ALTER TABLE otfr_keyword_repair ADD CONSTRAINT pk_otfr_keyword_repair PRIMARY KEY
( okr_data_set_name, okr_imset_name, okr_imset_value, okr_telemetry_keyword, okr_keyword_value, okr_status_date )
go

ALTER TABLE otfr_request_stats ADD CONSTRAINT pk_otfr_request_stats PRIMARY KEY
( ors_otfr_request_id, ors_data_set_name )
go

CREATE NONCLUSTERED INDEX ors_dads_tracking_id_index ON otfr_request_stats
( ors_dads_tracking_id, ors_dads_request_date )
go

CREATE NONCLUSTERED INDEX ors_ds_index ON otfr_request_stats
( ors_data_set_name )
go

ALTER TABLE otfr_special_processing ADD CONSTRAINT pk_otfr_special_processing PRIMARY KEY
( osp_data_set_name )
go

ALTER TABLE pdq_severity_mapping ADD CONSTRAINT pk_pdq_severity_mapping PRIMARY KEY
( psm_severity_code )
go

ALTER TABLE pdq_summary ADD CONSTRAINT pk_pdq_summary PRIMARY KEY
( pdq_program_id, pdq_obset_id, pdq_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX pdq_dsname_index ON pdq_summary
( pdq_data_set_name )
go

CREATE NONCLUSTERED INDEX pdq_severity_index ON pdq_summary
( pdq_severity_code )
go

ALTER TABLE proprietary_special_cases ADD CONSTRAINT pk_proprietary_special_cases PRIMARY KEY
( psc_program_id, psc_obset_id, psc_obsnum, psc_status, psc_status_date )
go

CREATE NONCLUSTERED INDEX psc_dsname_index ON proprietary_special_cases
( psc_data_set_name )
go

CREATE NONCLUSTERED INDEX psc_pep_id_index ON proprietary_special_cases
( psc_pep_id )
go

ALTER TABLE registered_users ADD CONSTRAINT pk_registered_users PRIMARY KEY
( rgu_user_id )
go

ALTER TABLE request_files ADD CONSTRAINT pk_request_files PRIMARY KEY
( rqf_tracking_id, rqf_request_date, rqf_sequence_num, rqf_data_set_name, rqf_archive_class, rqf_generation_date, rqf_extension, rqf_mission, rqf_delivery_date )
go

CREATE NONCLUSTERED INDEX rqf_dsn_ac_gd ON request_files
( rqf_data_set_name, rqf_archive_class, rqf_generation_date, rqf_mission )
go

CREATE NONCLUSTERED INDEX rqf_request_id ON request_files
( rqf_request_id )
go

ALTER TABLE request_key ADD CONSTRAINT pk_request_key PRIMARY KEY
( key_name )
go

ALTER TABLE request_operator_actions ADD CONSTRAINT pk_request_operator_actions PRIMARY KEY
( roa_request_id, roa_action_time )
go

ALTER TABLE requests ADD CONSTRAINT pk_requests PRIMARY KEY
( req_tracking_id, req_request_date )
go

CREATE NONCLUSTERED INDEX requests_requestid ON requests
( req_request_id )
go

ALTER TABLE restricted_data ADD CONSTRAINT pk_restricted_data PRIMARY KEY
( rda_pep_id, rda_status, rda_status_date )
go

ALTER TABLE retrieval_extensions ADD CONSTRAINT pk_retrieval_extensions PRIMARY KEY
( ree_mission, ree_instrument, ree_archive_class, ree_keyword, ree_file_extension )
go

ALTER TABLE scan_parameters ADD CONSTRAINT pk_scan_parameters PRIMARY KEY
( scp_program_id, scp_obset_id, scp_obsnum )
go

ALTER TABLE sci_inst_db_join ADD CONSTRAINT pk_sci_inst_db_join PRIMARY KEY
( sij_sdb_program_id, sij_sdb_obset_id, sij_sdb_obsnum, sij_idb_program_id, sij_idb_obset_id, sij_idb_obsnum )
go

CREATE NONCLUSTERED INDEX sij_idb_pso_index ON sci_inst_db_join
( sij_idb_program_id, sij_idb_obset_id, sij_idb_obsnum, sij_idb_data_set_name )
go

ALTER TABLE science ADD CONSTRAINT pk_science PRIMARY KEY
( sci_program_id, sci_obset_id, sci_obsnum )
go

CREATE NONCLUSTERED INDEX science_dsname ON science
( sci_data_set_name )
go

CREATE NONCLUSTERED INDEX science_pep_id ON science
( sci_pep_id )
go

ALTER TABLE shp_data ADD CONSTRAINT pk_shp_data PRIMARY KEY
( shp_program_id, shp_obset_id, shp_obsnum, shp_data_set_name )
go

CREATE NONCLUSTERED INDEX shp_dsname_index ON shp_data
( shp_data_set_name )
go

CREATE NONCLUSTERED INDEX shp_proposid_index ON shp_data
( shp_proposid )
go

ALTER TABLE sms_data ADD CONSTRAINT pk_sms_data PRIMARY KEY
( sms_data_set_name, sms_archive_class, sms_generation_date )
go

ALTER TABLE stis_a_data ADD CONSTRAINT pk_stis_a_data PRIMARY KEY
( ssa_program_id, ssa_obset_id, ssa_obsnum, ssa_data_set_name )
go

CREATE NONCLUSTERED INDEX ssa_dsname_index ON stis_a_data
( ssa_data_set_name )
go

ALTER TABLE stis_b_data ADD CONSTRAINT pk_stis_b_data PRIMARY KEY
( ssb_program_id, ssb_obset_id, ssb_obsnum, ssb_data_set_name )
go

CREATE NONCLUSTERED INDEX ssb_dsname_index ON stis_b_data
( ssb_data_set_name )
go

ALTER TABLE stis_c_data ADD CONSTRAINT pk_stis_c_data PRIMARY KEY
( ssc_program_id, ssc_obset_id, ssc_obsnum, ssc_data_set_name )
go

CREATE NONCLUSTERED INDEX ssc_dsname_index ON stis_c_data
( ssc_data_set_name )
go

ALTER TABLE stis_cumulative_images ADD CONSTRAINT pk_stis_cumulative_images PRIMARY KEY
( ssi_data_set_name )
go

ALTER TABLE stis_grand_mama ADD CONSTRAINT pk_stis_grand_mama PRIMARY KEY
( ssg_data_set_name )
go

ALTER TABLE stis_ref_data ADD CONSTRAINT pk_stis_ref_data PRIMARY KEY
( ssr_program_id, ssr_obset_id, ssr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX ssr_dsname_index ON stis_ref_data
( ssr_data_set_name )
go

ALTER TABLE stis_science ADD CONSTRAINT pk_stis_science PRIMARY KEY
( sss_program_id, sss_obset_id, sss_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX sss_dsname_index ON stis_science
( sss_data_set_name )
go

ALTER TABLE target_keyword ADD CONSTRAINT pk_target_keyword PRIMARY KEY
( tak_program_id, tak_obset_id, tak_obsnum, tak_broad_category, tak_keyword_text )
WITH (IGNORE_DUP_KEY=ON)
go

ALTER TABLE target_synonym ADD CONSTRAINT pk_target_synonym PRIMARY KEY
( tsy_program_id, tsy_obset_id, tsy_obsnum, tsy_name )
go

ALTER TABLE user_privileges ADD CONSTRAINT pk_user_privileges PRIMARY KEY
( usp_user_id, usp_mission )
go

ALTER TABLE wfc3_a_data ADD CONSTRAINT pk_wfc3_a_data PRIMARY KEY
( w3a_program_id, w3a_obset_id, w3a_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX w3a_dsname_index ON wfc3_a_data
( w3a_data_set_name )
go

ALTER TABLE wfc3_chip ADD CONSTRAINT pk_wfc3_chip PRIMARY KEY
( w3c_program_id, w3c_obset_id, w3c_obsnum, w3c_ccdchip )
go

CREATE UNIQUE NONCLUSTERED INDEX w3c_dsname_index ON wfc3_chip
( w3c_data_set_name, w3c_ccdchip )
go

ALTER TABLE wfc3_ref_data ADD CONSTRAINT pk_wfc3_ref_data PRIMARY KEY
( w3r_program_id, w3r_obset_id, w3r_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX w3r_dsname_index ON wfc3_ref_data
( w3r_data_set_name )
go

ALTER TABLE wfc3_science ADD CONSTRAINT pk_wfc3_science PRIMARY KEY
( w3s_program_id, w3s_obset_id, w3s_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX w3s_dsname_index ON wfc3_science
( w3s_data_set_name )
go

ALTER TABLE wfc3_times ADD CONSTRAINT pk_wfc3_times PRIMARY KEY
( w3t_program_id, w3t_obset_id, w3t_obsnum, w3t_sampnum )
go

CREATE UNIQUE NONCLUSTERED INDEX w3t_dsname_index ON wfc3_times
( w3t_data_set_name, w3t_sampnum )
go

ALTER TABLE wfc3_tv_chip ADD CONSTRAINT pk_wfc3_tv_chip PRIMARY KEY
( wtc_data_set_name, wtc_ccdchip )
go

ALTER TABLE wfc3_tv_int_data ADD CONSTRAINT pk_wfc3_tv_int_data PRIMARY KEY
( wti_data_set_name )
go

ALTER TABLE wfc3_tv_ref_data ADD CONSTRAINT pk_wfc3_tv_ref_data PRIMARY KEY
( wtr_data_set_name )
go

ALTER TABLE wfc3_tv_science ADD CONSTRAINT pk_wfc3_tv_science PRIMARY KEY
( wts_data_set_name )
go

ALTER TABLE wfc3_tv_times ADD CONSTRAINT pk_wfc3_tv_times PRIMARY KEY
( wtt_data_set_name, wtt_sampnum )
go

ALTER TABLE wfpc2_primary_data ADD CONSTRAINT pk_wfpc2_primary_data PRIMARY KEY
( wp2_program_id, wp2_obset_id, wp2_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX wp2_dsname_index ON wfpc2_primary_data
( wp2_data_set_name )
go

ALTER TABLE wfpc2_ref_data ADD CONSTRAINT pk_wfpc2_ref_data PRIMARY KEY
( w2r_program_id, w2r_obset_id, w2r_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX w2r_dsname_index ON wfpc2_ref_data
( w2r_data_set_name )
go

ALTER TABLE wfpc2_secondary_data ADD CONSTRAINT pk_wfpc2_secondary_data PRIMARY KEY
( ws2_program_id, ws2_obset_id, ws2_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX ws2_dsname_index ON wfpc2_secondary_data
( ws2_data_set_name )
go

ALTER TABLE wfpc_data ADD CONSTRAINT pk_wfpc_data PRIMARY KEY
( wfp_program_id, wfp_obset_id, wfp_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX wfp_dsname_index ON wfpc_data
( wfp_data_set_name )
go

ALTER TABLE wfpc_group_data ADD CONSTRAINT pk_wfpc_group_data PRIMARY KEY
( wgd_program_id, wgd_obset_id, wgd_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX wgd_dsname_index ON wfpc_group_data
( wgd_data_set_name )
go

ALTER TABLE wfpc_ref_data ADD CONSTRAINT pk_wfpc_ref_data PRIMARY KEY
( wcr_program_id, wcr_obset_id, wcr_obsnum )
go

CREATE UNIQUE NONCLUSTERED INDEX wcr_dsname_index ON wfpc_ref_data
( wcr_data_set_name )
go

