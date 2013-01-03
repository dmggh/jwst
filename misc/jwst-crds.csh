# CRDS initialization script for DMSINSVM host

if (`hostname` == "dmsinsvm.stsci.edu") then 
	source /usr/stsci/envconfig.mac/cshrc
endif 

irafx
setenv CRDS_SERVER_URL http://jwst-crds.stsci.edu
setenv CRDS_PATH /grp/crds/jwst

