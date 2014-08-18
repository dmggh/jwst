Interactive Application Models
==============================

Overview
--------

This document briefly outlines the models for the interactive aspect of the
CRDS website (as opposed to JSON RPC services).  Strictly speaking the
interactive models include the reference file catalog and context history
databases, so the models are used widely by many applications but contained in
the interactive application.  The models have seen considerable evolution over
the course of CRDS development and re-development, and for performance
optimization and database content defect analysis and repair.

Base Classes
------------

The original CRDS models were derived from pyetc models which use a "blob"
design to capture arbitrary simple parameters in a serialized dictionary stored
as variable length text. As time went on, the performance disadvantages of
blob's became evident, searching on blob parameters requires deserializing the
entire database rather than simple SQL.

CrdsModel(models.Model)
.......................

This is the fundamental model in the CRDS interactive application from which
all other models are ultimately derived.  The CrdsModel is abstract, so it does
not create an SQL table. The primary attribute of the CRDS model is a name
field which is intended to be unique.   It also supports generic repr'ing
and unicode'ing with attention to fields which should be included based
on class-defined inclusion lists.   A key feature of CrdsModel is that all
it's fields are directly represented in SQL.

A small wart to CrdsModel is that not all derived models naturally support
unique name fields.  In some cases name is unused.

BlobModel(CrdsModel)
....................

The BlobModel was the original CRDS baseclass from which all other models were
derived.  It's based (in spirit) on the pyetc modeldesign (circa 2011) but with
support for some field type checking and/or awllowed value specification.  In
short,  BlobModel's can have a mixture of Django and Blob fields.  

Key concepts for the BlobModel are "freezing" and "thawing", the process of
serializing and deserializing blob fields.  The save() method is overridden to
freeze before executing SQL.

One key advantage to the BlobModel is that all fields are effectively variable
length with no need to modify the underlying SQL schema.  In addition it is
possible to add fields to the BlobModel without modifying schema, and any
provided default will be used records which have no value for the new field.
Finally, adding fields to a BlobModel is very simple,  particularly for 
enumerations or unconstrained types,  requiring no knowledge of Django fields.

The key disadavantage to BlobModels is poor performance in many use cases.  The
original fast search design for BlobModels was by-name only, although filter
was/(is?) supported for blob fields as well.  Filtering on blob fields can only
be done by thawing each blob selected by non-blob fields like "name".  In
practice this is too slow for some cases, on the order of seconds.

BlobModel is abstract so SQL tables are only created for subclasses.

CrdsModel was factored out of BlobModel during the course of evolution as a
more performant baseclass.

**NOTE:** When adding new fields to a blob, existing records should be loaded
and saved to store a true value for the new field.  This is necessary for
SQL-lite database exports which cannot presume being interpreted by the CRDS
Django models code.  Since this is a time consuming process, it's left as a
maintenance activity rather than performed during dynamic SQL-lite database
conversion.

**NOTE:** CRDS does not currently use Django forms so the interaction between
BlobModel's and Django forms hasn't been explored.

Key Models
----------

FileBlob(BlobModel)
...................

This is the central model in CRDS for recording all reference and rules files.
It records around 19k+ CRDS references for HST, as well as a few hundred rules
files.

Although it remains a BlobModel, FileBlob has been optimized such that all
fields are now primitive Django/SQL fields and the blob is empty but retained
for potential "emergency use".  

new() and add_files()
+++++++++++++++++++++

FileBlob() has a new() method which is similar to __init__() but separates the
creation of a SQL record from the process of populating all the fields.   The 
add_file() function further separates slow and/or complex or unrelated operations 
from the new() method which creates a database record.  For the sake of development
and test,  initializing the sha1sum and checking for duplicate files using the
sha1sum are optional.

destroy()
+++++++++

This is a dangerous method similar to __del__(), which destroys both a file
record and the associated CRDS cache file copy.  If a file isn't already
archived or duplicated elsewhere, it's gone.

Blacklisting and File Rejection
+++++++++++++++++++++++++++++++

The CRDS distributed design supports the optional continued use of bad files.
CRDS continually distributes a list of bad files, one per line, in a config
file.  For expediency the bad files list is distributed with the server info
and then written down separately as well.  (More ideally, generic replication
of a cache file tree would be implemented.)

For marking files bad, FileBlob has a reject_flag, a blacklist_flag, and a
blacklisted_by files list.  File rejection is intransitive and affects only a
specific file, nominally a reference file.  File blacklisting is transitive
and applies to rules.   Bad rules make use of all three fields,  bad references
only use the reject flag.

Blacklisting a .rmap means that all .imaps and .pmaps dependent on it are also
blacklisted and considered bad.  Client side bad rules handling is currently
crude, so using a bad .pmap issues a warning regardless of the instrument and
types being computed and which instruments and types are actually bad.  Bad
references are more precise and only explicit recommendation of the bad file
generates a warning.

Blacklisting rules also results in a warning whenever a new context is derived
from a blacklisted file.  This is probably the primary use for file rejection
transitiveness.

File Delivery Status
++++++++++++++++++++

For interfacing with the CRDS pipeline (archive delivery) each file is
delivered to a delivery directory and listed in a catalog file.  The status
protocol between the CRDS pipeline and the CRDS server involves checking the
catalog file; when the catalog is deleted from the delivery directory, the
delivery is assumed to be complete (Originally, that was the entire protocol.
The CRDS pipeline now renames the catalog file several times corresponding to
different delivery states.  Until a file is in a terminal state, every time it
is displayed the catalog link is reinterpreted to determine the actual state of
the file.  This only affects the small set of files which are pending
archiving.

ContextHistoryModel
...................

The ContextHistoryModel records the selection of contexts by the pipeline as
operational.  This table skips over intermediate contexts which are never made
operational, and can include the same context more than once.  Each row records
the start of an operational period, and each pair of rows records an interval
of operations for the latter of the two history entries.  These records are
created by the Set Context service.

ContextHistoryModel is used to create a straightforward tabular dump of the
Context History.

ContextModel
............

The default editing and operational contexts are tracked with these models,
i.e.  whihc context to derive from by default,  and which context should be
used for bestrefs by default.

Secondary Models
----------------

These models are more incidental and supporting,  both dubious at this point.

CounterModel
............

The counter model records the next serial number to be generated for each file
type.  Different rows supports each context and mapping type, reference type,
and catalog files.  File naming has evolved and a possible alternative is more
reflexive, basing the name of the next file on the name of the latest existing
file.  In CRDS, it's important that file names be lexically sortable in time
order (for file reversion detection and possibly other things).  Since file
naming now also includes reflexive code which keeps the counters consistent
with files already in the cache, the only remaining purpose of database
counters that I'm aware of is baselining new series of files with a common
starting point, e.g. the 250-series .rmap's.

AuditBlob
.........

The AuditBlob records different actions and who did them.   Currently it provides
the basis for recording file submission grouping and unifying the delivery of files 
with the selection of files as operational and the marking of files as bad.  It
has an entry for the initialization of the database with existing CDBS files, and
also records the variant of file submission code used to add files or modify rules.

AuditBlobs are used to produce the delivery status display by selecting the blobs
for .cat catalog files.

RepeatableResultBlob
....................

The RepeatableResultBlob records web page parameters and template required to
redisplay important historical results at a later date.  Since the
RepeatableResultBlob tends to record all important parameters, they are also
exploited to perform subsequent workflow computations.  The two primary kinds
of repeatable results are the file submission confirmation page (initial
submission) and the file submission result page (confirmation outcome page).
Since it's inappropriate to redisplay confirmation options verbatim,
RepeatableResultBlob also has methods for changing paramters so that subsequent
renderings are not identical to the first, replacing perhaps an OK/Cancel with
the actual choice selected by the submitter.

Locks
.....

This model is created by the django-locking application/package.   Locks are
used to provide mutual exclusion for users,  preventing multiple users from
submitting files to the same instrument at one time,  or multiple users from
generating a new context at the same time.  Rather than modifying the core
Locks model and adding fields,  CRDS uses two locks,  one to lock an instrument
generically,  and one to additionally record the name of the user locking it.

Django-locking is probably fairly easily replaceable with UNIX file locks, but
those need to be considered carefully in the context of network file systems.

JPoll
.....

JPoll is the CRDS Django applicatiojn for sending "asynchronous" status
messages back to a web page during a long running Django view function.  JPoll
is unidirectional, server to browser.  With Jpoll, a view communicates back to
a page by writing through the database, where the original page polls the
database for new messages using AJAX view functions.  Additionally, Jpoll can
effect a page result ("done") after a web proxy has timed out and caused the
original request to fail.  (In theory the CRDS proxies now time out after 30
minutes, so pretty massive submissions should work even without JPoll
completion handling.  (For JWST though 30 minutes might only be 15 files...
definitely impossible to rule out.)

JPoll handles current HST web submissions practically, where submission
requests generally run for 10s of seconds to a couple minutes.  It gives the
user that important sense that something is happening!  I think changes to
Django modeling across versions (transactions) may have degraded the
responsiveness of JPoll by delaying SQL updates for messages, but it does still
basically work;  20 minutes won't pass in silence.

JPoll is more dubious for JWST however where simply computing a single a
sha1sum might take 2 minutes. For both projects the fundamental problem is that
file submissions have an unbounded amount of data... and hence unbounded
processing time.  Consequently an alternative, using background processing to
handle long running processes like file submission, is being considered for
JWST.  The goal of background processing would be to keep the runtime of any
particular view under a couple seconds, with some form of deferred response
like an e-mail of a link.

Channel Models
++++++++++++++

A JPoll channel is associated with a single web session and/or submission page.
The channel is opened when the page is visited.  The page executes periodic
Javascript to check for new messages.

Message Models
++++++++++++++

Each message sent to a JPoll channel creates a new message model. There are
currently two types: log_message and done.  done is essentially an asynchronous
response.

Proposed Models
---------------

Nothing beats hindsight.  There are two models which should probably have been
created but were not due to unknowns and complexity creep.  Intitially it was not
known that multiple files need to be submissible on one form,  rules need to be
automatically generated, file deliveries could fail in every conceivable manner
and order, etc.  In retrospect,  clearly recording inputs and outputs for page
actions associated with submissions makes sense.

FileSubmission
..............

There should be a model which records each group of files which is submitted
and the parameters they were submitted with.  Potentially it should include a
directory linked to each submitted file.  These could support trouble shooting
in the advent of submission failures.  More importantly, these can support a
consistent processing paradigm for a background processor driven by web inputs
or a command line interface.  The command line interface and background
processing are largely driven by JWST file sizes which more-or-less wreck a
simple web submission paradigm.

FileDelivery
............

Likewise each file should be associated with a delivery which manages the catalog
link, catalog, and delivery directories.   These could also provide a single evaluable
point for file delivery status for every associated file.

CRDS Server Quirks and Limitations
----------------------------------

End-to-end, much CRDS functionality is coupled to the original 3-tiered concept
for CRDS rules: pipeline, instrument, reference type.  This manifests in models
with discrete fields representing observatory, instrument, filekind.

Two things to point out here is that the 3-tiered rules structure may not be
appropriate for representing all systems, particularly pysynphot references.
Additionally,  observatory is generally defined by server and constant.

The original hope of the "observatory" field was to potentially represent
multiple observatories on one CRDS server.  That has major potential
maintenance advantages, cutting the VM / server count in half from 6 to 3.  In
practice, serving multiple projects/observatories from a common server is both
risky (single point) and probably inappropriate since separate projects
probably want dedicated service.  Supporting multiple projects also has a
direct effect on table lengths affecting performance.

Hence, the "observatory" field, while it is passed around extensively, is only
partially implemented server-side,  neither truly used nor implemented with 
complete consistency.  Possibly it should be ripped out.

Client side, the observatory field is fully implemented so that a single cache
can support multiple projects; it remains necessary client side to explicitly
select a server or define the observatory in some unambiguous way so that a
default server can be selected.

Django Model Quirks
-------------------

I didn't study it in depth but believe the Django models don't subclass
normally due to uncommon OOP techniques which do things like automagically
create SQL tables.     Consequently, some CRDS models have rather kludgy
implementations; I beat my head against the wall trying different subclassing
techniques and finally gave up and hacked methods to do what needed doing.

Looking briefly I see this:

   https://racingtadpole.com/blog/django-subclasses-reusability/
   
   "The purpose of this post is simple: subclassing Django models does work"

Ergo, enough people said Django models don't subclass well to motivate the post.

Notes on Changing or Maintaining Servers
----------------------------------------

General Process
...............

A reasonably safe process for modifying models on the operational server is the
following:

1. Mirror the OPS or TEST server to the DEV server.

2. Change the models or server code as appropriate.

3. Re-install the server to update code and add any new tables or columns.

4. Change model schema or instances using raw SQL (./manage dbshell).

5. Hack models using a Python shell and calling models functions or methods.  (./manage shell)

6. Run appropriate (or all using ./runtests) server regression tests.

7. Use the same perfected process on the OPS or TEST server.

The important principle is rehearsal.  Although server backups exist, they're
not guaranteed to work in all cases so it's better to practice and perfect
than screw up the OPS server and attempt to recover.

New fields should be automatically added to the database schema by Django
syncdb.  Changes in field width are not automatic.

AFAIK Raw SQL is generally required to drop tables or columns, do low level
inspections, resize, etc.

Repairing FileBlob Models
.........................

As CRDS went into operations, it became necessary to check and repair the file
catalog rather than reinitialize it, so the FileBlob model has defect detection
and repair methods.  The repair functionality is very lightly tested and may
only address project or situationally specific problems so it has to be
reviewed with care on case-by-case basis.  The repair functionality is now
factored out of the FileBlob model into a Mixin to consolidate the functionality
and simplify FileBlob.

Browse Files Defect Detection
+++++++++++++++++++++++++++++

For super users, the Browse Files service has two extra check boxes for
detecting and displaying defective files.  These can be used to check for
defects in a browser session.  Detect defects adds a column showing any
defects for each file record.  Show defects limits displayed files to
*only* those with defects.   This is fairly convenient for checking
the catalog but detection is slow.

Admin Defect Repair
+++++++++++++++++++

Quick model fixes can sometimes be performed using the web based Dango admin
interface visible to server super users.  This works for most/all models, not
just FileBlob,  but explicit support has to be added to interactive.admin.

This is a convenient way to add users or groups,  for instance,  but can also
be used to manually tweak most models fields.

The Admin interface for FileBlobs also supports two custom methods for
destroying selected FileBlobs and associated cache files, or for repairing
selected files.  (These methods are in addition to the standard admin method
for deleting instances of the model.)  The FileBlob.destroy() feature needs to
be used with care because it is not fully integrated with other CRDS models and
other aspects of the file system like the catalogs and delivery directories.
FileBlob.destroy() is best used to clean up submissions which fail prior to
the delivery phase.


Shell Based Defect Repair
+++++++++++++++++++++++++

Using a Python shell and operating directly on models (or models functions) is
the most potent approach to check and repair file records:

1. Optionally ./stop the server.

2. Use ./manage shell to interactively execute python functions directly on models classes.

3. Run interactive.models.detect_defects() get a defect map.

4. Review the defects.

5. Review and update the defect detection and repair code as needed.

6. Run interactive.models.repair_defects() on the fields and blobs in need of repair.

7. Restart the server and ./runtests.

./manage puts IPython into the same context and cwd that the Django server
processes run in.

After carefully checking that models changes work, ./stop the OPS server and
repeat the process on the OPS server.

interactice.models.repair_defects_all() runs both detect and repair in one step,
but should be used sparingly for easy cases.

