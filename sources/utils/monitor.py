"""a program which runs in the background parallel to the web server:

1. periodically verifies that the services are running

2. cleans up stale web file submissions

3. backs up the CRDS Django database

4. periodically e-mails status
"""