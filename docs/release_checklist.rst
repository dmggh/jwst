Process for Upgrading CRDS Servers
==================================

This writeup describes a rough plan for updating a CRDS OPS server, i.e.  to achieve something
similar to the upgrade corresponding to an OPUS release.  This plan applied to HST OPUS 2014.3.

There are a number of steps which should be followed to accomplish the
upgrade:

Prepare
-------

- Review the nightly regression tests on the TEST server and OPS server with vigour.

- Shut down the cronjob on the OPS server.

- Shut down the OPS server.

- Verify that the OPS server nightly backup executed

Backups
-------

- Backup anything important on the TEST server.  Maybe sync mappings somewhere and tar it.

- Backup mappings on the OPS server.  Maybe sync mappings somewhere and tar a mappings/config cache.  Commit config and mappings to an svn branch.

- Mirror the OPS server down to TEST, or TEST down to DEV, or both.   Probably stagger this by a day if both.

- Back up the OPS server tree.  Some files, e.g. the logs,  should be compressed.  Try
for a complete backup of /data1,  including Isilon server_files.   XXXX update this.

Reinstall
---------

- Wipe out the server software installation directories in the OPS server tree,  not the stacks.

- Switch the OPS server CRDS and CRDS_server directories on the OPS server VM to the new 
OPUS release branch.

- Re-install the OPS server and ./runtests on the backup port,  leaving the server on the
backup port.  Hack ./runtests to do this,  so it doesn't restart the server as an operational
system automatically.

- Try out the OPS server on the backup port.

- Switch the server stack to the new one in dot_setenv.

- Re-install the server again,  ./runtests on the backup port,  hack to prevent auto restart on operational port.

- If all is well, bring up the OPS server for real and give it a once over.

File Submissions
----------------

- Submit the new empty WFC3 NPOLFILE.

- Submit any WFC3 NPOLFILE references.

- Delete bad files.

- Set the operational context.

- Mark files bad.

- Watch for affected datasets.

- Check server logs for nominal output.

