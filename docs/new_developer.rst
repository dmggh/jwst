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

https://aeon.stsci.edu/ssb/svn/crds/trunk

The CRDS server source code is here:

https://aeon.stsci.edu/ssb/svn/crds_server/trunk

Client Trac is here (public and with most tickets):

https://aeon.stsci.edu/ssb/trac/crds

Server Trac is here (private web source code):

https://aeon.stsci.edu/ssb/trac/crds_server

---------------------------------------------------------------------------------------

Mailing lists:

crds_team@stsci.edu                  mainly ReDCat to pipeline and archive
crds@stsci.edu                           mainly INS to ReDCaT initial deliveries

crds-servers@stsci.edu               nightly server regressions, cache checks,  /grp/crds/cache updates, and server e-mails
crds_hst_ops_reprocessing@stsci.edu      reprocessing results for HST OPS
crds_hst_test_reprocessing@stsci.edu     " HST TEST
crds_jwst_ops_reprocessing@stsci.edu     " JWST OPS
crds_jwst_test_reprocessing@stsci.edu    " JWST TEST
crds_jwst_ita_reprocessing@stsci.edu     " B7 I&T
crds_jwst_itb_reprocessing@stsci.edu     " B5 I&T
crds_jwst_itc_reprocessing@stsci.edu     " B6 I&T

crds_datamng                             archive list for reprocessing info

dms-developer@stsci.edu                     pipeline and archive development
dms-design@stsci.edi                           overall DMS design, metrics, requirements, tasks, schedule, budget

I'm not aware of a ReDCaT list,  those communications seem to happen on crds_team and crds.

---------------------------------------------------------------------------------------

There are a total of 9 CRDS server VMs and servers which are devoted to the
following development stages:

PROJECT/STAGE         PROXY ADDRESS                       DIRECT FIREWALLED VM URL

HST OPS               https://hst-crds.stsci.edu          https://plhstcrdsv1.stsci.edu:8001
HST TEST              https://hst-crds-test.stsci.edu     https://tlhstcrdsv1.stsci.edu:8001
HST DEV               https://hst-crds-dev.stsci.edu      https://dlhstcrdsv1.stsci.edu:8001

JWST OPS              https://jwst-crds.stsci.edu         https://pljwstcrdsv1.stsci.edu:8001
JWST TEST             https://jwst-crds-test.stsci.edu    https://tljwstcrdsv1.stsci.edu:8001
JWST DEV              https://jwst-crds-dev.stsci.edu     https://dljwstcrdsv1.stsci.edu:8001

JWST Build 5 I&T   B  https://jwst-crds-b5it.stsci.edu    https://jwdmsbcrdsv1.stsci.edu:8001
JWST Build 6 I&T   C  https://jwst-crds-b6it.stsci.edu    https://jwdmsccrdsv1.stsci.edu:8001
JWST Build 7 I&T   A  https://jwst-crds-b7it.stsci.edu    https://jwdmsacrdsv1.stsci.edu:8001

OPS is used for the operational pipeline or, for JWST,  as the spearhead or
development and "operational version" supporting JWST such as-it-is.

TEST is used for pipeline testing.

DEV  is a VM environment for high fidelity CRDS server testing (better than
Django DEV server).

I&T servers are frozen dedicated servers to support I&T and NASA constractual requirements.

---------------------------------------------------------------------------------------

The CRDS servers run under the account "crds" which does not have a direct
login shell.

CRDS file submitters and maintainers should be added to group crdsoper.

The CRDS servers all have local isolated file systems and password files.
Maintainers need to have accounts on the CRDS server VMs as well as sudo
access to the "crds" account.   Maintainers login to the VMs using their
AD accounts but then sudo to "crds" to perform server maintenance.

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

18. Run nightly server Python stack builds.

19. Do nightly server code updates from subversion and CRDS server re-installs.

20. Perform nightly server Django catalog and selective file system backups
which can be used to support "mirroring" servers between two server development
stages.  (e.g. OPS --> TEST or OPS --> I&T or OPS --> DEV or TEST --> DEV).

Authentication currently supports locking for a single instrument to provide
file submitters with exclusive access to their instrument.  There is an
automatic 4 hour count down, logoff, and submission cancellation for inactive
authenticated users.

---------------------------------------------------------------------------------------

The following CRDS tools are available on the command line:

1. crds.bestrefs

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

2. crds.sync

The sync tool is used to explicitly update, check, purge, and organize the CRDS
cache.  Other tools such as crds.bestrefs or the calibration code can also
implicitly update the CRDS cache.  The sync tool can also download the CRDS
catalog from the CRDS server for use with local Sqlite3 queries.  The sync tool
is wrapped by the "cron_sync" script for operation in pipelines.  The cron_sync
script provides pipeline interface encapsulation as well as locking to prevent
log running cron updates to result in multiple concurrent cache syncs.

3. crds.certify

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


3. crds.list

Is used to report on CRDS configurations, list out available or cached
reference and rules and their cache paths.  It is a swiss army knife of minor
informational functions some of which satisfy formal requirements.  This is
also commonly used for end user and pipeline debug to dump the CRDS
configuration.

4. crds.diff

Is used to difference to sets of rules,  potentially recursively,  potentially
with additional text, fits, or table row differences.

5. crds.refactor

Is used to perform simple rmap file inserts/deletes on the command line.  The
server will eventually use the same core code for automatic rules updates so
crds.refactor is often used to "proof" rmaps and type specifications in code.

6. crds.newcontext

Is used to generate new pmaps and imaps given a baseline set of rules and new
rmaps to insert.

7. crds.checksum

Used to update CRDS rules internal checksums.

8. crds.matches

Is used to display which parameter values a particular reference file or
dataset id match on.   These are complementary pieces of information displayed
by the same tool.

9. crds.uses

Is used to display all of the mappings which directly or indirectly refer to
the specified mapping.  This runs relative to a CRDS cache,  so in principle to
work correctly the cache should be fully synced via crds.sync.   crds.uses on a
.imap will produce the list of .pmaps which refer to it.   crds.uses on a .rmap
will produce  the list of .pmaps and .imaps which refer to it.

10. crds.sql

Bare bones wrapper intended to provide a command line API which wraps the CRDS
capability of distributing it's metadata catalog as a SQLite 3 file.   It can
perform basic SQL queries on the catalog via the command line and is an
alternative to dumping the catalog via crds.sync and running the normal sqlite3
program on the downloaded file.

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
