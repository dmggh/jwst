Introduction
------------
This guide is intended to introduce the CRDS servers for the purposes of maintenance and emergency backup for Todd.

Historical Institute contacts for the CRDS servers include:

    * Todd Miller:    yours truly,  primary CRDS and (sole) CRDS server application developer.
    * Patrick Taylor: web proxies, ssl support, and server rc/reboot script coordination
    * Thomas Walker:  initial VM creation, file systems, and Isilon storage setup.
    
Servers
-------

CRDS pseudo-user and group
..........................

The CRDS servers run as the no-login user "crds".  The CRDS servers are maintained by getting sudo
access to the crds user and the equivalent of "su crds" from a normal user account.   The CRDS
crds_server script contains the following::

    ssh -A -t $1.stsci.edu /usr/bin/sudo /bin/su - crds

and is invoked like this:

    % crds_server plhstcrdsv1
    # crds_server VM-hostname

The ssh first logs into your normal user account on the server VM, then su's you to CRDS.

Server maintainers need to get membership in group crdsoper and "sudo su crds" access on
the appropriate servers.

Members of DSB share the crdsoper group and use it to modify the CRDS server file delivery 
directory described below.

Virtual Machines and URLs
.........................

The CRDS servers exist on virtual machines,  run Apache servers and Django via mod_wsgi,
are backed by memcached as a memory caching optimization for frequent traffic.  Currently
there are 6 VMs and servers:  (hst, jwst) x (dev, test, ops):

...........   ............   .............  ...........     ................................
observatory   use            host/vm        direct port     url
...........   ............   .............  ...........     ................................
hst           dev            dlhstcrdsv1    8001            https://hst-crds-dev.stsci.edu
hst           test           tlhstcrdsv1    8001            https://hst-crds-test.stsci.edu
hst           ops            plhstcrdsv1    8001            https://hst-crds.stsci.edu

jwst          dev            dljwstcrdsv1   8001            https://jwst-crds-dev.stsci.edu
jwst          test           tljwstcrdsv1   8001            https://jwst-crds-test.stsci.edu
jwst          ops            pljwstcrdsv1   8001            https://jwst-crds.stsci.edu

For debug purposes the servers can be accessed bypassing the proxy by using VM-based URLs such
as https://plhstcrdsv1.stsci.edu:8001/.

See CRDS_server/sources/site_config.py to verify this information.

Server File Systems
-------------------

/home/crds
..........

The VMs and servers share a common /home/crds directory which has potential as a single point failure.  In particular,
critical shell rc scripts (.setenv) are shared by all servers and must be updated with extreme care because
any error instantly affects all 6 servers.  As a rule, .setenv should also be kept as simple as reasonably
possible.  /home/crds is useful for communicating information between VMs during setup and maintenance.

Server Static File Storage
..........................

The CRDS server code and support files (Python stack, logs, monitor_reprocessing dir) are stored on
a private VM-unique volume named after the host,  e.g.  /crds/data1.  This serves as the
./configure --prefix directory for a small number of packages not contained in the crds_stack subdirectory.
Files within this directory tree are logically executable or in some way secret,  sensitive with respect
to server security.   Most files/subdirs are located in a subdirectory named after the host,  
e.g. /crds/data1/plhstcrdsv1. 

Database files
++++++++++++++

Files required to support operations with databases are stored in a subdirectory,  e.g. /crds/data1/database.

CRDS
++++

The checkout of the CRDS core library source code installed with the CRDS server is located in the static file tree
under the subdirectory CRDS and visited using the alias "crds".  e.g.  /crds/data1/plhstcrdsv1/CRDS

CRDS_server
+++++++++++

The checkout of the CRDS server source code is located in the static file tree under the subdirectory CRDS_server
and visited using the alias "server".  e.g. /crds/data1/plhstcrdsv1/CRDS_server

host
::::

The CRDS_server/host subdirectory is on the PATH.  It contains scripts related to cron jobs,  affected datasets 
reprocessing, stack building,  server utilities, etc.   e.g. /crds/data1/plhstcrdsv1/CRDS_server/host

tools
:::::

The CRDS_server/tools directory contains more complicated scripts related to server backup, restore, mirroring, 
consistency checking, server initialization, user and group maintenance, etc.   The tools directory is not on the
PATH and contains more eclectic scripts developed in an unplanned manner,  basically capturing whatever I needed
to do repeatedly or had to Google.   e.g. /crds/data1/plhstcrdsv1/CRDS_server/tools

servers
:::::::

This directory contains the Apache and mod_wsgi configuration files.  e.g. /crds/data1/plhstcrdsv1/CRDS_server/servers

sources
:::::::

This directory contains the Django server and application source code.   e.g. /crds/data1/plhstcrdsv1/CRDS_server/sources

* sources/configs contains site specific django configuration and database configuration files.  The appropriate files
  are copied to sources/site_config.py and sources/crds_database.py at install time.   Those are then imported into
  more generic configuration files sources/config.py and sources/settings.py.   The site specific files are intended
  to contain the minimal information required to differentiate servers.

* sources/urls.py     defines most of the site URLs for all applications. 

* sources/settings.py fairly standard Django settings.py 

* sources/templates  contains web template base classes

* sources/static     contains most CRDS static files,  particularly Javascript and CSS.

* sources/interactive  is the primary web application for CRDS browsing and file submission.

* sources/jsonapi     is the JSONRPC application which supports web services in the crds.client api.

* sources/jpoll      application supports the Javascript logging + done polling system used for long running views,  
                     particularly file submissions which can exceed proxy timeouts and run too long to leave a human 
                     without info.
                     
* sources/locking     application for database based locks used by CRDS web logins for exclusive access to an instrument.

* sources/fileupload  application supports the fancy file submission file upload dialogs for file submissions.

* sources/stats      mostly defunct django-level request logging,  superceded by Apache logging.


crds_stacks
+++++++++++

The crds_stacks subdirectory contains stock python stacks and source code.  The CRDS server Python stack is built 
from source contained in the installer3 subdirectory.  An automatic nightly build and reinstall of the stack occurs on the 
dev and test servers so it's possible to upgrade all the non-ops servers by updating the installer3 repo.  The
master copy of the CRDS server installer3 repo is contained in /eng/ssb/crds/installer3.   Independent checkouts 
of the repo are contained in the stacks file store for each VM.   e.g. /crds/data1/plhstcrdsv1/crds_stacks

monitor_reprocessing
++++++++++++++++++++

Output from the monitor_reprocessing cron job is stored in dated subdirectories here.  Also the file old_context.txt
which records the last known operational context against which changes are measured.  Changed old_context.txt will
trigger an affected datasets calculation as will changing the operational context on the web site.

Server Dynamic File Storage
...........................

For operating,  the CRDS servers require a certain amount of dynamic storage use for purposes like:

* holding pending archive deliveries  (deliveries, catalogs)
* uploading files (uploads, ingest, ingest_ssb)

The server dynamic file storage is located on the Isilon file server at:

    /ifs/crds/<obsevatory>/<use>/server_files,    e.g. /ifs/crds/hst/ops/server_files.
    
Since this area is actively written as a consequence of users accessing the web site,  it is kept distinct from the
code and files required to run the server.

Catalog Directory
+++++++++++++++++

Files submitted to the archive generate .cat file lists which are stored permanently in the catalogs directory.
Any file in CRDS is also stored in the server file cache,  so given the .cat file list the delivery can be recreated
by regenerating file links in the deliveries directory.  The catalogs directory is an internal CRDS server data store
which records file lists from past deliveries.

Deliveries Directory
++++++++++++++++++++

The deliveries directory is cross-mounted between the CRDS server VM and CRDS-archive-pipeline machines,  not
necessarily under the same path name.

Files submitted to the archive are placed in the CRDS delivery directory along with a numbered catalog file which
lists the submitted files one per line.   Unlike more CRDS directories,  the delivery directory is cross-mounted
to pipeline machines which handle archiving.  As part of the protocol with the CRDS archiving pipeline,  the catalog
file is renamed to indicate processing status.  When the catalog is finally deleted,  CRDS assumes that archiving
is successful.   See crds.server.interactive.models for more info on the delivery naming protocol.  Note that files
in the delivery directory are linked to the same inode as the CRDS file cache copy of the file,  or,  in the case
of the .cat delivery file lists, to the permanent copy in the catalogs directory.  For references,  linking avoids
substantial I/O overheads associated with multi-gigabyte JWST references.  For catalogs,  linked or not,  like named
file lists should have the same contents in catalogs and deliveries.

Uploads Directory
+++++++++++++++++

The uploads directory is the default Django file upload directory for simple file uploads.

Ingest Directory
++++++++++++++++

The ingest directory tree contains per-submitter subdirectories which are written to by the Django-file-upload
muli-file upload application used on file submission pages.  The user's guide gives instructions enabling submitters
to copy files directly into their per-user subdirectories as an upload bypass for telecommuters.  (This is a work
around for the situation in which a VPN user winds up transparently downloading and then explicitly uploading
references submitted via the web site;  instead,  a submitter places the file directly into their own ingest
directory keeping the file onsite,  then proceeds with the submission on the web server normally.)

Ingest SSB Directory
++++++++++++++++++++

The ingest_ssb directory tree is the historical drop-off point for the files generated by the jwst_gentools via
direct file copy from an SSB'er,  nominally Pey Lian Lim.  Ingested files are then copied into the CRDS server
cache or submitted to the web site.

Server File Cache
.................

Each CRDS server (test or ops) has a full copy (~2T allocation) of all operational and historical (CRDS-only) 
reference files.   The dev servers have a smaller allocation which is generally linked to /grp/crds 
(synced from ops servers) rather than internally stored.  The Isilon CRDS cache storage (i.e. CRDS_PATH for servers) 
is located similarly to dynamic file storage:

    e.g. /ifs/crds/jwst/test/file_cache

The server file cache config area is generally updated transparently by running cronjobs.   The server file_cache
and delivery areas are updated as a result of file submissions and archive activity.  Once global Isilon archive storage
becomes available, cache space can be reclaimed by symlinking the CRDS cache path to the global storage rather than
maintaining an internal copy;  there should be a lag of a couple weeks to a month between submission and reclamation
during which the potentially transient file is fully stored in the CRDS server.   Because the CRDS server caches also
contain unconfirmed and unarchived files,  they are currently read protected from anyone except crds.crdsoper.

See the User's manual in the ? on the web sites for more info on the CRDS cache.

RC scripts
----------

The RC scripts are kept with the server source code in the directory "hosts" under the names dot_setenv and 
rc_script.

.setenv
.......

The CRDS user runs under /bin/tcsh and executes .setenv for CRDS-server specific initializations.   Note that
$HOME/.setenv is shared across all CRDS servers and should be modified with extreme caution.

$HOME/rc_script
...............

The /home/crds/rc_script is executed to restart the servers,  or shut them down,  whenever the server is rebooted.

Cron Jobs
---------

Use shell command::

    % crontab -l
    
to dump the current crontab and observe the jobs.   Cronjobs currently produce .log files in the CRDS_server directory.

See "man cron" or Google for more info on maintaining the cron table.

nightly.cron.job
................

CRDS_server/hosts/nifghtl directory and executes every night at 3:05 am.  The dev and test versions
of the nightly cron fully rebuild and reinstall the CRDS servers,  with the exceptions of database secret setup,
cron jobs, and .setenv rc_script scripts.   The nightly cronjob on all servers captures diagnostic information about
the server,  including server configuration, disk quotas and usage, subversion status for detecting uncommitted 
changes and observing branch and revision, and cache consistency and orphan file checking.   All of the servers
currently update subversion although the OPS (and often TEST) servers are typically on a static branch.   The dev
and test servers also restart.  Output from the nightly cron is sent to the MAILTO variable defined in the
CRDS_server/host/crontab file,  currently jmiller@stsci.edu.

monitor_reprocessing
....................

Every 5 minutes CRDS_server/host/monitor_reprocessing looks for changes in the CRDS operational context and
does an "affected datasets" context-to-context bestrefs comparison when the context changes.   This generates
an e-mail to the $CRDS_AFFECTED_DATASETS_RECIPIENTS addresses set up by the .setenv file.   bestrefs can require
from 20 seconds to 4-8 hours depending on the number of datasets potentially affected as determined by file
differences.

clear_expired_locks
...................

Somewhat dubious,  this falls into the category of periodic server maintenance,  removing expired instrument locking 
records from the server locking database.   Every 5 minutes.

sync_ops_to_grp
...............

Every 10 minutes sync_ops_to_grp runs crds.sync to publish the crds ops server to the /grp/crds/cache global readonly
Central Store file cache CRDS currently uses as default for OPUS 2014.3.   This does not produce e-mail.

