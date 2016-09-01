Setting up the CRDS client software in the calibration pipeline consists of two broad
areas:

0. Configuring the pipeline environment for CRDS

(shown here with build-6 values)

% setenv CRDS_SERVER_URL https://jwst-crds-b6it.stsci.edu
% setenv CRDS_PATH <where pipeline would like to store ~350G of CRDS rules, references, and config info>
% setenv CRDS_LOG_TIME 1
% setenc CRDS_READONLY_CACHE 1

1. Installing the CRDS Python client code itself

(a) Automatic installation as a dependency

The CRDS client software is normally installed in the pipeline as part of the
overall calibration software delivery.  As such, the CRDS software is listed as
one of the dependencies in the Conda installation recipe used to install the
calibration software.  See the calibration software installation instructions
for more details, as a depenency listed in that recipe the installation of CRDS
is automatic.

(b) Explicit installation from delivered source code

The CRDS client software is delivered in a compressed tar ball.  It can be
installed in the python environment as follows:

% tar zxf CRDS.tar.gz
% cd CRDS
% ./install

2. Initializing or updating the pipeline's CRDS cache

Once the pipeline environment is configured and the CRDS software is installed,
the pipeline's CRDS cache needs to be initialized by downloading CRDS rules
and references from the archive in cooperation with the CRDS server.  The
cron_sync command is nominally used for this:

% cron_sync --all --fetch-references --verbose --stats --log-time |& tee cron_sync.err

The above command will download thousands of files with an overall volume of 
roughly ~350G,  increasing with subsequent builds following build-6.  Even on internal
networks at STScI the downloads will take many hours;  cron_sync provides log output
which can help estimate progress and the ultimate completion time.

