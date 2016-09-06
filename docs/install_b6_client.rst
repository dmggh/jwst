Setting up the CRDS client software in the calibration pipeline consists of a few broad
areas:

Configuring the pipeline environment for CRDS
================================================

(shown here with build-6 values)

% setenv CRDS_SERVER_URL https://jwst-crds-b6it.stsci.edu
% setenv CRDS_PATH <where pipeline would like to store ~350G of CRDS rules, references, and config info>
% setenv CRDS_LOG_TIME 1
% setenc CRDS_READONLY_CACHE 1

Installing the CRDS Python client code
======================================

The CRDS client consists of a package of pure Python code suitable for installing into
a python-2.7.x or python-3.4.x environment.   Further, CRDS and calibration software 
created by the Science Software Branch are managed, tracked, and distributed using 
Continuum's Conda system so CRDS can be installed automatically via Conda in addition
to explicit source code install.

Automatic installation as a dependency
--------------------------------------

The CRDS client software is normally installed in the pipeline as part of the
overall calibration software delivery.  As such, the CRDS software is listed as
one of the dependencies in the Conda installation recipe used to install the
calibration software.  See the calibration software installation instructions
for more details, as a depenency listed in that recipe the installation of CRDS
is automatic.

After following instructions on Continuum's website here:

http://conda.pydata.org/docs/install/quick.html

to install a basic conda environment, versions of the overall calibration
software of which CRDS is a direct dependency can be installed as follows:

% conda create -n jwst_0.6.0rc3 -c http://ssb.stsci.edu/conda-dev python=2.7 stsci-jwst=0.6.0rc3
% source activate jwst_0.6.0rc3

As a dependency of the calibration s/w, the matching version of CRDS is
known and installed automatically.

Explicit installation from delivered source code
------------------------------------------------

The CRDS client software is delivered in a zip-file named jwst_crds_build6.zip
CRDS can be directly installed in a python environment as follows:

% unzip jwst_crds_build6.zip
% cd jwst_crds_build6/CRDS-client-b6
% ./install

Initializing or updating the pipeline's CRDS cache
==================================================

Once the pipeline environment is configured and the CRDS software is installed,
the pipeline's CRDS cache needs to be initialized by downloading CRDS rules
and references from the archive in cooperation with the CRDS server.  The
cron_sync command is nominally used for this:

% cron_sync --all --fetch-references --verbose --stats --log-time |& tee cron_sync.err

The above command will download thousands of files with an overall volume of 
roughly ~350G,  increasing with subsequent builds following build-6.  Even on internal
networks at STScI the downloads will take many hours;  cron_sync provides log output
which can help estimate progress and the ultimate completion time.

