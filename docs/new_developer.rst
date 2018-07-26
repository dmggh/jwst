The CRDS OPS server for JWST is here:

https://jwst-crds.stsci.edu/

For HST this OPS server is here:

https://hst-crds.stsci.edu/

Documentation on the CRDS client and server is available on the CRDS web sites,
for JWST OPS here:

https://jwst-crds.stsci.edu/static/users_guide/index.html

For HST OPS nominally identical documenttion is here:

https://hst-crds.stsci.edu/static/users_guide/index.html

The CRDS client source code is here:

https://github.com/spacetelescope/crds.git

The CRDS server source code is here:

https://github.com/spacetelescope/crds-server.git

CRDS Confluence is here:

https://innerspace.stsci.edu/pages/viewpage.action?spaceKey=SCSB&title=CRDS

CRDS Confluence covers a number of key CRDS admin processes (particularly
OPS-to-TEST server mirroring) not described below.  CRDS confluence also
gives links to additional resources not replicated here.

---------------------------------------------------------------------------------------

Mailing lists:

redcat@stsci.edu                     INS team delivering files into CRDS

crds-servers@stsci.edu               nightly server regressions, cache checks, /grp/crds/cache updates, and server e-mails

crds_hst_ops_reprocessing@stsci.edu      reprocessing results for HST OPS
crds_hst_test_reprocessing@stsci.edu     " HST TEST
crds_jwst_ops_reprocessing@stsci.edu     " JWST OPS
crds_jwst_test_reprocessing@stsci.edu    " JWST TEST

crds-servers@stsci.edu                   " B7.1.3 I&T reprocessing
crds-servers@stsci.edu                   " B7.2 I&T reprocessing

crds_datamng@stsci.edu                   archive list for reprocessing info

CRDS-STATUS@MAILLIST.STSCI.EDU           Weekly and Monthly automated report

dms-developer@stsci.edu                   pipeline and archive development
dms-design@stsci.edi                      overall DMS design, metrics, requirements, tasks, schedule, budget

---------------------------------------------------------------------------------------

CRDS development / admin SUDO access and groups

CRDS developers and admins should be members of group crdsoper and given
"sudo crds" access to every VM they work on.

CRDS file submitters and maintainers should be added to group crdsoper.

CRDS archive ingest operators (CRDS poller operators) should likewise be added
to group crdsoper so they can manipulate the CRDS delivery directory and read,
rename, or remove file links.   The should not have write access to the
corresponding files.

The CRDS servers run under the account "crds" for which ordinary logins are not
normally used.  Instead, developers and admins access the CRDS server account
by first ssh'ing to the appropriate CRDS VM as their normal AD user, then using
SUDO to become the CRDS user:

    $ ssh iljwdmsccrds.stsci.edu

It's convenient to set up .ssh for your AD login on the CRDS VMs.  Then sudo
from your AD to CRDS:

    $ usr/bin/sudo /bin/su - crds

For string isolation purposes,  each CRDS VM has an independent /home and
independent user directory which needs to be initialized separately.

To make this easier,  I use this shell program which,  once .ssh is set up,
only requires me to enter a password to sudo to CRDS:

   #! /bin/tcsh
   exec ssh -A -t jmiller@$1.stsci.edu /usr/bin/sudo /bin/su - crds

It is run like this:

   $ crds_server iljwdmsccrds
   password:  [type in AD password for jmiller]
   
The CRDS servers all have local isolated file systems and password files.
Maintainers need to have accounts on the CRDS server VMs as well as sudo
access to the "crds" account.   Maintainers login to the VMs using their
AD accounts but then sudo to "crds" to perform server maintenance.

---------------------------------------------------------------------------------------

There are a total of 8 CRDS server VMs and servers which are devoted to the
following development stages:

PROJECT/STAGE         PROXY ADDRESS                       DIRECT FIREWALLED VM URL

HST OPS               https://hst-crds.stsci.edu          https://plhstcrds.stsci.edu:8001
HST TEST              https://hst-crds-test.stsci.edu     https://tlhstcrds.stsci.edu:8001
HST DEV               https://hst-crds-dev.stsci.edu      https://dlhstcrds.stsci.edu:8001

JWST OPS              https://jwst-crds.stsci.edu         https://pljwcrds.stsci.edu:8001
JWST TEST             https://jwst-crds-test.stsci.edu    https://tljwcrds.stsci.edu:8001
JWST DEV              https://jwst-crds-dev.stsci.edu     https://dljwcrds.stsci.edu:8001

JWST I&T B-string     https://jwst-crds-bit.stsci.edu    https://jwdmsbcrds.stsci.edu:8001
JWST I&T C-string     https://jwst-crds-cit.stsci.edu    https://jwdmsccrds.stsci.edu:8001

OPS will eventually be AKA A-string,  as of 2018-07-19 TEST is being used as
A-string / practice OPS.   (There is still a *real* JWST OPS already.)

OPS is used for the operational pipeline or, for JWST,  as the spearhead or
development and "operational version" supporting JWST such as-it-is.

TEST is used for pipeline testing.  In summer 2018 CRDS TEST is integrated with
DMS A-string as an "OPS" test string.

DEV is a VM environment for standalone CRDS development, not integrated with
archive + pipeline.

I&T servers are frozen dedicated servers to support I&T and NASA constractual requirements.

---------------------------------------------------------------------------------------

Server Development Workflow

# alias to go to CRDS client git checkout directory  (probably still svn)
% crds

# alias to go to CRDS server source code and utilities directory,  svn checkout
% server

# additional environment defined by running CRDS server ./install script,  required for tools and scripts
% source env.csh

% ... edit source code,  most likely sources/interactive/...
% ... edit static files, javascript, css, etc.   generally in sources/static

# does CRDS client and server source installs,  independent of Python stack install
% ./install jwst dev

# start the apache+mod_wsgi+django system,  also memcached memory cache
% ./run

# does install + run with no parameters once the server is fully set up
% ./rerun

# shuts down apache + memcached
% ./stop

# runs the server self-tests,  also run nightly at ~3:05 am,  see runtests.jwst.dev.err
# it's normal for a few of these to be failing.
% ./runtests  

# Run Django manage.py in general on CRDS server install
% ./manage ...

# Open an Ipython shell in the context of the CRDS server
% ./manage shell

# Operate on CRDS server interactive models (nominally the file catalog, context history, etc.)
% ./manage shell
>>> from crds.server.interactive import models
>>> models...

# Open a SQL/MySQL shell on the CRDS server models
% ./manage dbshell

# Mirror the OPS server and latest official rules and references and database down to DEV
% mirror_server jwst ops https://jwst-crds.stsci.edu |& tee mirror_server.jwst.ops.err

# Look at server log files
% logs   # alias to go to log directory

# Generally view function stderr and crds.log output
% tail -1000 error_log
...

# Apache log to monitor requests and their sources,  stats on usage
% tail -1000 xfor_request_log | resolve_ip
...

Less useful

% tail -1000 ssl_request_log
...
% tail -1000 ssl_error_log
...

# Look at general CRDS environment
% printenv | grep CRDS

---------------------------------------------------------------------------------------

The CRDS servers perform these diverse functions:

1. They explain or provide various ways of obtaining best references on web
pages.

2. They provide JSON RPC web services for obtaining best references and various
kinds of CRDS-related information such as the default context.

3. They display the current version of CRDS rules in a tabular format.

4. They display the history of which versions of CRDS rules were operational at
which dates and the differences between versions.

5. They support browsing a catalog of the reference file, rules, and associated
metadata.

6. They support searching the log of recent activity which monitors new
reference deliveries and  changes to rules,  changes to operational context in
use in pipeline.

7. They support client tools which distribute CRDS rules and references to end
user caches.

Authenticated users have additional functions avalable:

8. Support for certifying uploaded files.

9. Support for differencing uploaded or archived files.

10 Support for updating the default operational context for use in calibration.

11. Support for submitting new references with automatic rules updates and
addition to the CRDS catalog and STScI archive.

12. Support for submitting new references or rules without automated rules
generation.

13. Support for displaying downstream archive delivery status (shaky, relies on
correct exectution of downstream ACK protocol).

14. Support for marking files bad.

As a background activities,  the CRDS servers and their associated VMs:

15. Automatically update the shared readonly CRDS cache at /grp/crds/cache on
the Central Store.

16. Automatically monitor rules updates and compute lists of dataset ids which
are candidates for reprocessing based on the new reference files.

17. Run nightly server regression tests.

18. Run nightly server Python stack builds, CRDS re-installs, and/or server
    reboots.

19. Do nightly server code updates from subversion and CRDS server re-installs.

20. Perform nightly server Django catalog and selective file system backups
which can be used to support "mirroring" servers between two server development
stages.  (e.g. OPS --> TEST or OPS --> I&T or OPS --> DEV or TEST --> DEV).

Authentication currently supports locking for a single instrument to provide
file submitters with exclusive access to their instrument.  There is an
automatic 4 hour count down, logoff, and submission cancellation for inactive
authenticated users.

---------------------------------------------------------------------------------------

CRDS command line tools

The following CRDS tools are available on the command line.   The names below
describe CRDS Python package structure (or virtual structure).   For example,
the program corresponding to the:

    crds.bestrefs

package is run using a command line wrapper as:

    crds bestrefs ....


1. crds.bestrefs    (used by server repro and HST pipeline)

is the HST tool for updating dataset file headers with best references.
Additionally this tool is equipped to do regression testing or
context-to-context reprocessing determinations based on DADSOPS (or equivalent)
database reference file matching parameters.

Because of the direct integration of CRDS with JWST calibration code via the
CRDS interface layer, crds.bestrefs is less critical for basic pipeline operation.
Nevertheless it's regression and reprocessing capabilities are used by both projects.

For HST, crds.bestrefs is wrapped by the safe_bestrefs script which is used to
configure CRDS to run readonly for the cache and to run serverless, independent
of the CRDS Server. This configuration mitigates pipeline concurrency and
avoids multiple simultaneoius CRDS cache updates.  For JWST CRDS_SERVER_URL and
CRDS_READONLY_CACHE must be correctly set by the pipeline for the calibration
Step code to run in a similar readonly decoupled fashion.

crds.bestrefs is tuned for the single user case by default which runs either
against the complete shared readonly cache /grp/crds/cache or against a local
user defined readwrite cache (CRDS_PATH) which crds.bestrefs automatially updates.
Similarly the JWST calibration code automatically updates the cache unless
explicitly prohibited from doing so.

crds.bestrefs has an optional "affected table rows" optimization which is
intended to diagnose the datasets affected by specific table row changes.  This
check is applied selectively to supported tables (it must emulate row lookups
for specific instruments and table types) and currently is turned off because
it does not account for the global effects of modified primary header keywords
(which also must be defined).

2. crds.sync    (used by pipeline primarily)

The sync tool is used to explicitly update, check, purge, and organize the CRDS
cache.  Other tools such as crds.bestrefs or the calibration code can also
implicitly update the CRDS cache.  The sync tool can also download the CRDS
catalog from the CRDS server for use with local Sqlite3 queries.  The sync tool
is wrapped by the "cron_sync" script for operation in pipelines.  The cron_sync
script provides pipeline interface encapsulation as well as locking to prevent
log running cron updates to result in multiple concurrent cache syncs.

3. crds.certify    (used by ReDCaT + servers)

The certify program is used to check reference files and rules files.  For HST
reference checks are based on .tpn constraint files.  Rules checks are based on
_ld.tpn files.  For JWST the certifier attempts to leverage appropriate data
model schema to augment file checking. CRDS also has capabilities for writing
.tpn files for JWST which can futher augment any schema checks, potentially
with more targeted and stringent checks.  In addition crds.certify can be
augmented with table row checks which detect duplicated rows within a single
table or deleted rows between two different versions of a table.  crds.certify
is also augmented by a Parsley mapping grammar used to detect duplicate lines
as well as other grammatical errors in CRDS mappings.   

table row checks are driven by a project specific row_keys.dat file which
defines the columns which can effectively be used to define unique rows or
"pseudo modes".  The idea is that some columns characterize the data, and some
columns *are* the data.  Checking which modes are accidentally duplicated or
deleted doesn't revolve around actual coeffecient values, just the "mode"
parameters which define a row as for a particular mode.  There are several
different row lookup algorithms but CRDS certifies tables using this single
minimal model.   Not all tables are checked,  that hinges on being able to
characterize rows as "unique under these column values" and making an
appropriate entry in row_keys.dat for that instrument and type.   Not all
tables work within this model, roughly 50% of HST tables are covered.  No JWST
tables are covered yet.


3. crds.list     (utility)

Is used to report on CRDS configurations, list out available or cached
reference and rules and their cache paths.  It is a swiss army knife of minor
informational functions some of which satisfy formal requirements.  This is
also commonly used for end user and pipeline debug to dump the CRDS
configuration.

4. crds.diff     (used primarily by servers)

Is used to difference to sets of rules,  potentially recursively,  potentially
with additional text, fits, or table row differences.

5. crds.refactor

Is used to perform simple rmap file inserts/deletes on the command line.  The
server will eventually use the same core code for automatic rules updates so
crds.refactor is often used to "proof" rmaps and type specifications in code.

6. crds.newcontext    (used primarily by servers)

Is used to generate new pmaps and imaps given a baseline set of rules and new
rmaps to insert.

7. crds.checksum   (used by ReDCaT)

Used to update CRDS rules internal checksums.

8. crds.matches    (used by ReDCaT?)
 
Is used to display which parameter values a particular reference file or
dataset id match on.   These are complementary pieces of information displayed
by the same tool.

9. crds.uses     (little used?)

Is used to display all of the mappings which directly or indirectly refer to
the specified mapping.  This runs relative to a CRDS cache,  so in principle to
work correctly the cache should be fully synced via crds.sync.   crds.uses on a
.imap will produce the list of .pmaps which refer to it.   crds.uses on a .rmap
will produce  the list of .pmaps and .imaps which refer to it.

10. crds.sql    (little used?)

Bare bones wrapper intended to provide a command line API which wraps the CRDS
capability of distributing it's metadata catalog as a SQLite 3 file.   It can
perform basic SQL queries on the catalog via the command line and is an
alternative to dumping the catalog via crds.sync and running the normal sqlite3
program on the downloaded file.

11. crds.submit   (used by ReDCaT)

To simplify ReDCaT file submission processes, a client program was created to
initiate CRDS reference file submissions from the command line and integrate
with additional ReDCaT programs.  File submissions are started from ReDCaT VMs
running the crds.submit program which interacts with the web page used for
routine file submissions.  After the initial file validation and CRDS rules
updates have succeeded, the web site issues an e-mail and/or reports a web link
which is used to review complex file submission results, errors or warnings and
general


---------------------------------------------------------------------------------------

Useful generic command line switches and debug behaviors:

--help           will dump standard argparse help and app specific switches

--verbose        sets logging for debug output level 50
--verbosity=N    sets logging for debug output level N

--debug-traps    enables deeply nested CRDS exception traps to raise un-impeded
                 exceptions producing a full traceback.

--pdb            runs a program inside pdb

--profile=[.stats file or "console"]    runs a program under the profiler

--readonly-cache  runs a program such that it should not alter the CRDS Cache
