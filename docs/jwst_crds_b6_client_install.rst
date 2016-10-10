Overview
========

Normally installing the calibration software will automatically install CRDS as
a required dependency.  If you can do this:

% python -m crds.list --version
6.0.1, master, c89fc86

CRDS is already installed in your environment and the following *installation*
instructions can be skipped.  

The following tasks are still required but are performed by SDP:

1. The pipeline shell environment must be configured for CRDS.
2. The pipeline's CRDS cache must be synchronized with the CRDS server.

Configuring the pipeline environment for CRDS
=============================================

The pipeline environment for CRDS is configured in two ways depending on which
CRDS tasks are being performed, calibration runs or CRDS cache synchronization.
Synchronization can occur concurrently with calibration but different
environment settings are required for each.

Calibration Runtime Environment
-------------------------------

During pipeline calibration runs the following environment settings should be
used.  These configure CRDS to operate with no server and with no permission
to write to the CRDS cache.

% setenv CRDS_SERVER_URL https://jwst-serverless-mode.stsci.edu  # no connection
% setenv CRDS_PATH <where pipeline stores ~350G of CRDS rules, references, and config info>
% setenv CRDS_LOG_TIME 1
% setenv CRDS_READONLY_CACHE 1   # cache modifications disallowed

Synchronization Environment
---------------------------

During CRDS cache synchronization the following environment settings should be
used.  These configure CRDS to communicate with the CRDS server and give permission 
to change the CRDS cache.

% setenv CRDS_SERVER_URL https://jwst-crds-b6it.stsci.edu     # real server
% setenv CRDS_PATH <same as runtime path above>
% setenv CRDS_LOG_TIME 1
% setenv CRDS_READONLY_CACHE 0   # cache modifications allowed

Synchronizing the pipeline's CRDS cache
=======================================

Once the pipeline environment is configured for synchronization, the pipeline's
CRDS cache needs to be initialized by downloading CRDS rules and references
from the archive in cooperation with the CRDS server.  The CRDS cron_sync
command is nominally used for this:

% cron_sync --all --fetch-references --push-context <jwst-pipeline-uuid> |& tee cron_sync.err

In the pipeline environment this command is further wrapped by a shell script
delivered by SDP:

% crds_sync_cache.csh 

that hides all parameters from operators and is used to run cron_sync rather than
running cron_sync directly on the command line.

crds_sync_cache.csh also decrypts the <jwst-pipeline-uuid> used to identify
and update the CRDS server record of the pipeline context.

The above command will download thousands of files with an overall volume of
roughly ~350G increasing with subsequent builds.  Initial syncs take many hours or
even days.  Subsequent syncs are incremental and skip files downloaded previously.

Installing the CRDS Python client code
======================================

There are a variety of ways to install the CRDS software. The CRDS client
consists of a package of pure Python code suitable for installing into a
python-2.7.x or python-3.4.x environment.

Automatic installation as a dependency
--------------------------------------

CRDS software is listed as one of the dependencies in the Conda installation
recipe used to install the calibration software.  The instructions given with
the calibration software are definitive, superseding these, but entail tasks
similar to the following:

After following instructions on Continuum's website here:

http://conda.pydata.org/docs/install/quick.html

to install a basic conda environment, versions of the overall calibration
software of which CRDS is a direct dependency can be installed as follows:

% conda create -n jwst_0.6.0rc3 -c http://ssb.stsci.edu/conda-dev python=2.7 stsci-jwst=0.6.0rc3
% source activate jwst_0.6.0rc3

As a dependency of the calibration s/w, the matching version of CRDS is known
and installed automatically.

Explicit installation from delivered source code
------------------------------------------------

The CRDS client software is delivered in a zip-file named jwst_crds_build6.zip
CRDS can be directly installed in a python environment as follows:

% unzip jwst_crds_build6.zip
% cd jwst_crds_build6/CRDS-client-b6
% ./install

Download from GitHub Source Code Repository
-------------------------------------------

The CRDS client source code is maintained on the GitHub open source repository.
An CRDS installation based on a direct source code checkout from GitHub can be
achieved as follows:

% git clone https://github.com/spacetelescope/crds.git CRDS
% cd CRDS
% git checkout 6.0.1
% ./install

