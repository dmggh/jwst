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

CrdsModel was factored out of BlobModel during the course of evolution.

**NOTE:** When adding new fields to a blob, existing records should be loaded
and saved to store a true value for the new field.  This is necessary for
SQL-lite database exports which cannot presume being interpreted by the CRDS
Django models code.  Since this is a time consuming process, it's left as a
maintenance activity rather than performed during dynamic SQL-lite database
conversion.

**NOTE:** CRDS does not currently use Django forms so the interaction between
BlobModel's and Django forms hasn't been explored.  Assume they don't work.

Key Models
----------

FileBlob(BlobModel)
...................

This is the central model in CRDS for recording all files.  It records both
references and mappings, around 19k+ CRDS references for HST, and far fewer
mappings.  Over HST mission life I'd expect/guess less than 25k files total so
I'm not anticipating significant performance degradation from here out.

FileBlob has been optimized to the point that ALL fields are now Django/SQL
fields and the blob is a residual retained for potential "emergency use".  
One potential mainenance acitivity would be to eliminate that unused (and
potentially slow) functionality.

FileBlob Repair Functionality
+++++++++++++++++++++++++++++

As CRDS went into operations, it became necessary to check and repair the file
catalog.  For various reasons.  The FileBlob model has defect detection and
repair methods.  The repair functionality is very lightly tested and may only
address project or situationally specific problems.

For super users, the Browse Files service has two extra check boxes for
detecting and displaying defective files.  These can be used to check for
defects in a browser session.  Bad files only just displays the bad files.
Show defects also displays the defect detection output which adds additional
columns.

See *Notes on Changing or Maintaing Models* for advice on how to use the repair
features.

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
practice, serving multiple projects/observatories from a common server
significantly increases the risk of any changes since the server affects
multiple projects.  It also affects server performance loads and database
performance by increasing/doubling the table record counts.  Hence, the
"observatory" field, while it is passed around extensively, is only partially
implemented server-side.  Client side, the observatory field is fully
implemented so that a single cache can support multiple projects; it remains
necessary client side to explicitly select a server or define the observatory
in some unambiguous way so that a default server can be selected.

Django Model Quirks
-------------------

I didn't study it in depth but believe the Django models don't subclass
normally due to uncommon OOP techniques.  Consequently, some CRDS models have
rather kludgy implementations.  Looking briefly I see this:

   https://racingtadpole.com/blog/django-subclasses-reusability/
   
   "The purpose of this post is simple: subclassing Django models does work,
   with a caveat: the usual object manager does not know the new post’s
   subclass."
   
So this is an area of CRDS which could be "improved", but as-is, works well
enough.  Intricate package specific techniques are pretty much the same as
hacks anyway from the perspective of readability.   The main issue might
be "well enough" and currently unused generic Django features.

Django Admin Interface
----------------------

Quick model fixes can sometimes be performed using the web based Dango admin
interface visible to server super users.  This is a convenient /
straight-forward / fully-functional way to add users or groups for instance.

The Admin interface for FileBlobs supports two custom methods for destroying
selected FileBlobs and associated cache files, or for repairing selected files.
The destroy FileBlob feature needs to be used with care because it is not fully
integrated with other models or file system structures like

Notes on Changing or Maintaining Models
---------------------------------------

A reasonably safe process for modifying models on the operational server is the
following:

1. Mirror the ops server to the DEV server.  If TEST is needed for some reason,
coordinate changes with the pipeline testing group on crds_team@stsci.edu (or 
with Mike Swam and Matt McMaster).

2. Change the models code if appropriate.

3. Use ./manage dbshell to execute any raw SQL statements (generally required
to drop tables or columns or do low level inspections).

4. Use ./manage shell to execute functions on the FileBlob table, particularly
get_defects and repair_defects.  models.get_fileblob_map() is useful for
getting a dictionary of the entire catalog of file models.

5. Re-install the server to update the models code and add any new tables.

6. Run appropriate (or all using ./runtests) server regression tests.

After carefully checking that models changes work, ./stop the OPS server and
repeat the process on the OPS server.  An untried approach would be to
mirror/promote an updated DEV or TEST database to the OPS server.  Presumably
that's recoverable using an OPS server backup...  but actual file deletions may
not be easily recoverable using mirroring until CRDS is fully using archived
files rather than serving them itself.  The cron sync between the CRDS OPS
servers and the global shared CRDS cache (currently /grp/crds/cache)
intentionally does not purge stray files and could serve as a redundant source
for lost files.
