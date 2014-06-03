#! /bin/csh

# to be sourced for running cron jobs
#
# uses a path common across all servers (which nevertheless points to server-unique storage)
# which is not auto-mounted so that it will be ready when cron executes.
#
# this approach is an alternative to just sourcing ${HOME}/.setenv, etc. since the latter had 
# problems with intermittent stale file handles believed to be caused by auto mounting.
#

cd /crds/data1/cron

source dot_setenv    # This is the login .setenv

cd ${CRDS}/CRDS_server

source env.csh

