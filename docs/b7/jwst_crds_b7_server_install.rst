========
Overview
========

These notes describe initializing a CRDS web server VM and server.

------------------------
Initial resource request
------------------------
Setting up a CRDS server involves several different activities:

1. Virtual machine setup

   iljwdmsdcrdsv1.stsci.edu, 8 cores, 8G RAM, 2G swap
   
2. Server file system setup

/dev/mapper/system-root
                      7.8G  1.4G  6.1G  19% /
tmpfs                 3.9G     0  3.9G   0% /dev/shm
/dev/sda1             191M  108M   74M  60% /boot
/dev/mapper/system-tmp
                      2.0G  133M  1.7G   8% /tmp
/dev/mapper/system-usr
                      7.8G  3.0G  4.5G  40% /usr
/dev/mapper/system-var
                      7.8G  845M  6.6G  12% /var
/dev/mapper/vg1-data1
                       50G   11G   36G  24% /crds/data1
/dev/mapper/vg2-home   99G  9.4G   84G  11% /home
isistor1d:/ifs/isifs/archive/public/jwst/dit
                      2.5T  390G  2.2T  16% /ifs/crds/jwst/dit
emcdm3:/eng/ssb        11T  6.7T  3.8T  64% /eng/ssb

3. Database setup

   (see below)

4. SSL and proxy setup

   (see below)

5. Network setup

eth0      Link encap:Ethernet  HWaddr 00:50:56:BD:3B:43  
          inet addr:130.167.252.189  Bcast:130.167.252.255  Mask:255.255.255.0
          inet6 addr: fe80::250:56ff:febd:3b43/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:144416469 errors:0 dropped:0 overruns:0 frame:0
          TX packets:85838206 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000 
          RX bytes:156882172815 (146.1 GiB)  TX bytes:81630707131 (76.0 GiB)

eth1      Link encap:Ethernet  HWaddr 00:50:56:BD:39:EC  
          inet addr:192.168.41.138  Bcast:192.168.41.255  Mask:255.255.255.0
          inet6 addr: fe80::250:56ff:febd:39ec/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:9000  Metric:1
          RX packets:254020 errors:0 dropped:0 overruns:0 frame:0
          TX packets:14 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000 
          RX bytes:27654551 (26.3 MiB)  TX bytes:1008 (1008.0 b)

lo        Link encap:Local Loopback  
          inet addr:127.0.0.1  Mask:255.0.0.0
          inet6 addr: ::1/128 Scope:Host
          UP LOOPBACK RUNNING  MTU:65536  Metric:1
          RX packets:250759 errors:0 dropped:0 overruns:0 frame:0
          TX packets:250759 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:0 
          RX bytes:114158595 (108.8 MiB)  TX bytes:114158595 (108.8 MiB)
   
   
-------------------
SSL and Proxy setup
-------------------

The ITSD division configures server proxies that present the CRDS public
interface to the internet.   The server proxy request for CRDS for build-6
was:

        proxy     internal hostname / https port
    -------------------- -------------------------------
    jwst-crds-dit.stsci.edu            --> iljwdmsdcrdsv1.stsci.edu:8001

--------------------
CRDS UNIX User/Group
--------------------

The CRDS server runs as user "crds" with group "crdsoper."   The "crds" user
only supports sudo logins from other users,  not direct login.   File submitters
and the archive file delivery interface (CRDS pipeline) also

Logins:

    Either direct login and password for crds
            -or-
    Login for jmiller + sudo to crds,  more sudo users coming later

File permissions/ownership:

    user    crds
    group   crdsoper

    with g+s

Storage:

    50G of host-specifc storage (each) mounted at:
         /crds/data1/iljwdmsdcrdsv1               (same path, one volume per server)

    50G isolated /home storage:
         /home/crds       (if isolated file system, clone from networked/shared pljwstcrdsv1:/home/crds)

    2.5T of Isilon storage mounted at:
         /ifs/crds/jwst/dit              (iljwdmsccrdsv1 only)

The CRDS JWST I&T servers are supported by dedicated database virtual machines
running MySQL servers. Provisisioning the virtual machines is handled by ITSD
but database accounts are required as follows:

    user:
            jwstcrds

     server:  MySQL

        B6 database VM     iljwdmsccrdsdbv.stsci.edu   port 3306
        
    databases:
            crds_jwst_b6it
            test_crds_jwst_b6it

    grants:
            GRANT USAGE ON *.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'
            IDENTIFIED BY PASSWORD 'XXX'
            GRANT ALL PRIVILEGES ON `crds\_jwst_b6it`.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'
            GRANT ALL PRIVILEGES ON `test\_crds\_jwst_b6it`.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'

            GRANT USAGE ON *.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'
            IDENTIFIED BY PASSWORD 'XXX'
            GRANT ALL PRIVILEGES ON `test\_crds\_jwst_b6it`.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'
            GRANT ALL PRIVILEGES ON `crds\_jwst_b6it`.* TO 'jwstcrds'@'iljwdmsccrdsv1.stsci.edu'

-------------------
Source Installation
-------------------

Two source directories need to be set up on the CRDS server,  the client source
and the server source.   See the corresponding client instructions for information
on insalling the CRDS client s/w.

NOTE: The resulting directories should be set up in parallel like this:

...rootdir/CRDS
...rootdir/CRDS_server

so that the server install script can refer to the client source using ../CRDS.

Using the delivered source code zipfile:

% cd /crds/data1/iljwdmsccrdsv1
% unzip CRDS_server_v7.0.0.zip
% unzip CRDS_v7.0.12.zip      
% mv CRDS_server_v7.0.0   CRDS_server
% mv CRDS_v7.0.12         CRDS

Obtaining the build-7 CRDS server source code from subversion:

% svn co https://aeon.stsci.edu/ssb/svn/crds_server/branches/jwst-build-7 CRDS_server

and installing the combined client and server source code.

% cd CRDS_server
% ./install jwst dit 

# assumes client is installed in parallel directory at ../CRDS

-----------------------
Key Configuration Files
-----------------------

As an overview, these files within the CRDS_server source code checkout configure server setup:

env.csh    (critical to source into shell,  generated by e.g. ./install jwst dit )
host/dot_setenv
host/dot_aliases
sources/configs/config.dit.jwst.py
sources/configs/database.dit.jwst.py
servers/*

----------
VM .setenv
----------

As part of the CRDS_server "./install jwst dit" files "dot_setenv" and
"dot_aliases" are automatically copied to "$HOME/.setenv" and "$HOME/.aliases"
respectively.

If there is no CRDS .setenv installed,  do e.g.:

% cp /crds/data1/iljwdmsccrdsv1/CRDS_server/host/dot_setenv $HOME/.setenv
% cp /crds/data1/iljwdmsccrdsv1/CRDS_server/host/dot_alias $HOME/.alias

In any case,  a section for the new VM(s) needs to be added to $HOME/.setenv,  e.g.:

       case iljwdmsccrdsv1:
        setenv CRDS_STACK ${CRDS}/crds_stacks/crds_conda-3
        setenv CRDS_PROJECT jwst
        setenv CRDS_USECASE dit
        setenv CRDS_AFFECTED_DATASETS_RECIPIENTS "jmiller@stsci.edu  crds_${CRDS_PROJECT}_${CRDS_USECASE}_reprocessing@maillist.stsci.edu   crds_datamng@stsci.edu"
        setenv CRDS_GRP_CACHE_KEY 3d15844c-62a0-4a00-bedc-fafdb34f4a2c
       breaksw

Logout and log back in and typing the alias "server" should now take you to the
CRDS_server checkout from above.

Each execution of the ./install script in CRDS_server will replace the .setenv and .alias
in $HOME with those in the source distribution.  Edit them as dot_setenv and dot_alias
under CRDS_server/host first,  then execute the ./install script to install them into $HOME.

--------------------------
Create Server Config Files
--------------------------

Every CRDS server is customized by two files defined in the
CRDS_server/sources/configs directory which define file system paths,
provided and required URLs, database details, etc.

As delivered for JWST B6, the config.dit.jwst.py and database.dit.jwst.py
have already been created and customized.

The general process for setting up a new server variant is to copy
from another observatory and/or use case to the new use case and edit
the contents to customize for the new server.

% server
% cd sources/configs
% cp config.ops.jwst.py config.dit.jwst.py    
% cp database.ops.jwst.py database.dit.jwst.py

Edit/customize the new dit files and add them to subversion.   The required
facts come from discussions with ITSD during the initial resource setup.

-----------------------
CRDS Server Stack Build
-----------------------

The CRDS server runs on a custom Python stack installed using a combination
of Continuum's Conda distribution and custom CRDS source packages. To rebuild
the CRDS server Python stack,  do:

% mkdir /crds/data1/iljwdmsccrdsv1/crds_stacks
% cd /crds/data1/iljwdmsccrdsv1/crds_stacks
% cp -r /eng/ssb/crds/installer4 .
% server
% host/build_conda  |& tee build_stack.conda.err

"conda" is this stack's indentifying "version" in both .setenv and build_stack,
the stack is named "crds_conda".

See Conda and CRDS maintained package dependency lists below.

The overall conda stack version is defined by the git hash used from
/eng/ssb/crds/installer4 and by the version of the CRDS_server/host/build_conda
script used to build the stack.

    commit 24f6bc527882c68ef8b2416b2801b5b34b29d567
    Author: Todd Miller <jmiller@stsci.edu>
    Date:   Mon Dec 12 08:07:52 2016 -0500
    Final JWST build-7 sources.

    URL: https://aeon.stsci.edu/ssb/svn/crds_server/branches/jwst-build-7
    Repository Root: https://aeon.stsci.edu/ssb/svn/crds_server
    Repository UUID: 37088bc5-bd3f-4c5b-b9de-119bb1e8f7e3
    Revision: 2681
    Node Kind: directory
    Schedule: normal
    Last Changed Author: jmiller@stsci.edu
    Last Changed Rev: 2681
    Last Changed Date: 2016-12-12 15:36:02 -0500 (Mon, 12 Dec 2016)

Comprehensive version information is included on the 

------------------------
CRDS Server Installation
------------------------

NOTE:  build nomenclature changed relative to prior builds so the server
identifier is now based on D-string (dit) instead of build number (b6it).
This applies to the web proxy, internal file paths, and the server use
case designator used to install a particular instance of the server.

The CRDS source code is installed independently of the Python stack to a
different directory.   Once the .setenv and .alias files are installed,
and you've logged back in,  you should be able to install the CRDS server
as follows:

% server
% ./install jwst dit

This installs a JWST server for the dit use case.  Also  b5it, b6it, dev, test, ops

This results in a server setup with an empty CRDS cache and database.

Ongoing server initializations have been performed by cloning the database and
server file area of the operational server using the server mirroring tool:

% server         # (alias to chdir to .../CRDS_server source code)
% mirror_server jwst ops https://jwst-crds.stsci.edu |& tee mirror_server.jwst.ops.err

Mirroring the server as above will restore the database backup of the OPS server to
the local DIT server and make the server file system as consistent as possible.
Missing rules or references in the local server's file cache are downloaded
from the specified source (OPS) server.  Undelivered files from OPS are placed in the 
delivery area.

Because this procedure mirrors the OPS server, while it is the mechanism used
to initialize new servers, the content copied from the OPS server will not be
frozen at the final state of the build-7 delivery.   Hence,  better mechanisms
of build-7 server *re*-initiailization would be to fall back onto VM, file system,
and database backups.

----------------------
Starting up the Server
----------------------

The server is nominally started as follows from the server source directory:

% ./run jwst dit

This starts both the Apache server and memcached.

-------------------
Stopping the Server
-------------------

The server is nominally stopped as follows from the server source directory:

% ./stop jwst dit

This stops both the Apache server and memcached.


-------------------
Cycling the Server
-------------------

The common practice of stopping, re-installing, and restarting
the CRDS server is done as follows from the server source directory:

% ./rerun

The observatory and use case do not have to be specified with ./rerun.

-------------------------
Running server unit tests
-------------------------

The server unit tests can be run as follows:

% ./runtests

The observatory and use case do not have to be specified with ./runtests.

runtests nominally produces an output file like "runtests.jwst.dit.err" in
addition to console output.

runtests takes the server offline by switching to a backup port (8002?) unless
the "live" parameter is specified.  when tests havec completed runtests 
restores the server to it's normal port.  killing tests with <control-c>
can result in the server staying configured for the backup port.  Examine
and fix using "svn diff" and/or "svn revert -R" and ./rerun.

------------------------------------------------
Versions of Conda Packages Installed for Build-7
------------------------------------------------

# packages in environment at /crds/data1/iljwdmsdcrdsv1/crds_stacks/crds_conda-3:
#
anaconda-client           1.6.0                    py27_0  
appdirs                   1.4.0                    py27_0    http://ssb.stsci.edu/conda-dev
asdf                      1.0.6.dev45         np111py27_0    http://ssb.stsci.edu/conda-dev
astroid                   1.4.7                    py27_0  
astropy                   1.3dev4377          np111py27_0    http://ssb.stsci.edu/conda-dev
backports                 1.0                      py27_0  
backports_abc             0.4                      py27_0  
beautiful-soup            4.3.2                    py27_0  
bokeh                     0.12.3                   py27_0  
cairo                     1.12.18                       6  
chest                     0.2.3                    py27_0  
cloudpickle               0.2.1                    py27_0  
clyent                    1.2.2                    py27_0  
conda                     4.2.13                   py27_0  
conda-env                 2.6.0                         0  
coverage                  4.2                      py27_0  
curl                      7.49.0                        1  
cycler                    0.10.0                   py27_0  
cython                    0.25.1                   py27_0  
dask                      0.11.1                   py27_0  
dbus                      1.10.10                       0  
decorator                 4.0.10                   py27_0  
Django                    1.8.13                    <pip>
django-dbbackup           1.80.1                    <pip>
django-json-rpc           0.6.2                     <pip>
django-nose               1.4.4                     <pip>
django-smuggler           0.7.0                     <pip>
drizzle                   v1.1.dev5           np111py27_0    http://ssb.stsci.edu/conda-dev
drizzlepac                2.1.7rc.dev0        np111py27_0    http://ssb.stsci.edu/conda-dev
enum34                    1.1.6                    py27_0  
expat                     2.1.0                         0  
fitsblender               0.2.6.dev5          np111py27_0    http://ssb.stsci.edu/conda-dev
fontconfig                2.11.1                        6  
freetype                  2.5.5                         1  
functools32               3.2.3.2                  py27_0  
future                    0.14.3                    <pip>
futures                   3.0.5                    py27_0  
get_terminal_size         1.0.0                    py27_0  
git                       2.9.3                         0  
glib                      2.43.0                        1  
gst-plugins-base          1.8.0                         0  
gstreamer                 1.8.0                         0  
gwcs                      v0.6rc1.dev31       np111py27_0    http://ssb.stsci.edu/conda-dev
h5py                      2.6.0               np111py27_2  
hdf5                      1.8.17                        1  
heapdict                  1.0.0                    py27_1  
icu                       54.1                          0  
ipython                   5.1.0                    py27_0  
ipython_genutils          0.1.0                    py27_0  
jbig                      2.1                           0  
jinja2                    2.8                      py27_1  
jpeg                      8d                            2  
jsonschema                2.5.1                    py27_0  
jwst                      ab32d86b                  <pip>
lazy-object-proxy         1.2.1                    py27_0  
libffi                    3.2.1                         0  
libgcc                    5.2.0                         0  
libgfortran               3.0.0                         1  
libiconv                  1.14                          0  
libpng                    1.6.22                        0  
libtiff                   4.0.6                         2  
libxcb                    1.12                          1  
libxml2                   2.9.4                         0  
libxslt                   1.1.29                        0  
locket                    0.2.0                    py27_1  
lxml                      3.7.0                    py27_0  
markupsafe                0.23                     py27_2  
matplotlib                1.5.3               np111py27_1  
mkl                       11.3.3                        0  
modernize                 0.4                       <pip>
mpmath                    0.19                     py27_1  
mysql-connector-python    2.0.4                    py27_0  
mysql-python              1.2.5                    py27_0  
networkx                  1.11                     py27_0  
nictools                  1.1.3.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
nose                      1.3.7                    py27_1  
numpy                     1.11.2                   py27_0  
openssl                   1.0.2j                        0  
pandas                    0.19.0              np111py27_0  
Parsley                   1.2                       <pip>
partd                     0.3.6                    py27_0  
path.py                   8.2.1                    py27_0  
pathlib2                  2.1.0                    py27_0  
pexpect                   4.0.1                    py27_0  
photutils                 v0.2.dev585         np111py27_2    http://ssb.stsci.edu/conda-dev
pickleshare               0.7.4                    py27_0  
pillow                    3.4.2                    py27_0  
pip                       8.1.2                    py27_0  
pixman                    0.32.6                        0  
prompt_toolkit            1.0.8                    py27_0  
ptyprocess                0.5.1                    py27_0  
py                        1.4.31                   py27_0  
pycairo                   1.10.0                   py27_0  
pycosat                   0.6.1                    py27_0  
pycrypto                  2.6.1                    py27_0  
pygments                  2.1.3                    py27_0  
pylint                    1.5.4                    py27_1  
pymysql                   0.7.9                    py27_0  
pyodbc                    3.0.10                   py27_1  
pyparsing                 2.1.4                    py27_0  
pyqt                      5.6.0                    py27_0  
pyregion                  1.1.2.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
pytest                    3.0.3                    py27_0  
python                    2.7.12                        1  
python-dateutil           2.5.3                    py27_0  
pytools                   2016.1                   py27_0    http://ssb.stsci.edu/conda-dev
pytz                      2016.7                   py27_0  
pyyaml                    3.12                     py27_0  
qt                        5.6.0                         1  
readline                  6.2                           2  
requests                  2.11.1                   py27_0  
ruamel_yaml               0.11.14                  py27_0  
scikit-image              0.12.3              np111py27_1  
scipy                     0.18.1              np111py27_0  
setuptools                27.2.0                   py27_0  
simplegeneric             0.8.1                    py27_1  
singledispatch            3.4.0.3                  py27_0  
sip                       4.18                     py27_0  
six                       1.10.0                   py27_0  
sqlite                    3.13.0                        0  
ssl_match_hostname        3.4.0.2                  py27_1  
stsci.convolve            2.1.3.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.distutils           0.3.8.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.image               2.2.0.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.imagemanip          1.1.2.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.imagestats          1.4.1.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.ndimage             0.10.1.dev0         np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.skypac              0.9.dev0                 py27_0    http://ssb.stsci.edu/conda-dev
stsci.sphere              0.2.dev0            np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.sphinxext           1.2.1                     <pip>
stsci.stimage             0.2.1.dev0          np111py27_0    http://ssb.stsci.edu/conda-dev
stsci.tools               3.4.1.dev11         np111py27_0    http://ssb.stsci.edu/conda-dev
stwcs                     1.3.0rc.dev3        np111py27_0    http://ssb.stsci.edu/conda-dev
tk                        8.5.18                        0  
toolz                     0.8.0                    py27_0  
tornado                   4.4.2                    py27_0  
traitlets                 4.3.1                    py27_0  
unixodbc                  2.3.4                         0    http://ssb.stsci.edu/conda-dev
verhawk                   0.0.2.dev0               py27_0    http://ssb.stsci.edu/conda-dev
wcwidth                   0.1.7                    py27_0  
wheel                     0.29.0                   py27_0  
wrapt                     1.10.8                   py27_0  
xz                        5.2.2                         0  
yaml                      0.1.6                         0  
zlib                      1.2.8                         3  

-------------------------------------
CRDS Meta Environment Custom Packages
-------------------------------------

CRDS also maintains some packages in it's own source tree managed
by git.  The sha1sum and last date of installation are recorded
for packages installed using this system as part of "build_conda."

The sha1sums apply to the source tarballs maintained in the installer4
directory.  These sources may be updated and overwritten as the nightly stack
build creates the "future stack" crds_conda-4 as part of normal operations.
The D-string server is frozen at crds_conda-3.  The original sources that
should match these sha1sums can be obtaind by performing:

% git checkout 24f6bc527882c68ef8b2416b2801b5b34b29d567

in the installer4 directory.

{'Django': {'date': '2016-12-14 14:41:47.95',
            'sha1': '02d0a5d74a6415431f2acb8ac7db70298354d809',
            'version': (1, 8, 13, 0, 0)},
 'anaconda-client': {'date': '2016-12-14 14:41:07.24',
                     'sha1': 'none',
                     'version': (0, 0, 0, 0, 0)},
 'atop': {'date': '2016-12-14 14:44:29.63',
          'sha1': '3f51d3400c4b90167f3c9e0ad9f1928f6771d703',
          'version': (2, 2, 3, 0, 0)},
 'cfitsio': {'date': '2016-12-14 14:42:58.55',
             'sha1': '2933a0bd51403eb9c42df604b2e55234e1399f40',
             'version': (3360, 0, 0, 0, 0)},
 'coverage': {'date': '2016-12-14 14:41:13.07',
              'sha1': 'none',
              'version': 'unknown'},
 'django-background-task': {'date': '2016-12-14 14:41:50.11',
                            'sha1': 'c9bede56a68a6d6960fdfa8318881441c40e57e3',
                            'version': (0, 1, 8, 0, 0)},
 'django-dbbackup': {'date': '2016-12-14 14:41:49.10',
                     'sha1': '288be43db483d189c69f838636f351cd8233fbfa',
                     'version': (1, 80, 1, 0, 0)},
 'django-json-rpc': {'date': '2016-12-14 14:41:49.00',
                     'sha1': 'b516f31f3d36894da8ad4ddf2783951e1a0a2531',
                     'version': (0, 0, 0, 0, 0)},
 'django-nose': {'date': '2016-12-14 14:41:51.17',
                 'sha1': 'd8728b1347a378f851419f259cc440ccb0fa6c56',
                 'version': (0, 0, 0, 0, 0)},
 'django-smuggler': {'date': '2016-12-14 14:41:54.02',
                     'sha1': '4b24739d34c15beb96b50e3035842a4b95519265',
                     'version': (0, 0, 0, 0, 0)},
 'fitsverify': {'date': '2016-12-14 14:42:59.13',
                'sha1': 'de5ebed16018344c23c1ac712e971b7b30123425',
                'version': (4, 17, 0, 0, 0)},
 'freetds-dev': {'date': '2016-12-14 14:44:22.16',
                 'sha1': '249ad94df6cf3e43a4fc95da6e7eba021a186ba1',
                 'version': (0, 92, 405, 0, 0)},
 'future': {'date': '2016-12-14 14:41:35.94',
            'sha1': '44fdd9323913d21068b29ecda795a98c07dc8a40',
            'version': (0, 14, 3, 0, 0)},
 'git': {'date': '2016-12-14 14:41:32.46',
         'sha1': 'none',
         'version': 'unknown'},
 'iozone': {'date': '2016-12-14 14:44:37.34',
            'sha1': 'a4ecb564901b2e70407b825f1ade0c2b5319a7c9',
            'version': (3, 444, 0, 0, 0)},
 'jwst': {'date': '2016-12-14 14:44:42.06',
          'sha1': '8bc6f00653d789ae5ab203b4d33daa939ebb6bdc',
          'version': 'unknown'},
 'libevent': {'date': '2016-12-14 14:42:42.07',
              'sha1': '2337923ddd4473ffd8bac0807e04ef8b9f0c5756',
              'version': (2, 0, 21, 0, 0)},
 'lxml': {'date': '2016-12-14 14:42:13.58',
          'sha1': 'none',
          'version': 'unknown'},
 'memcached': {'date': '2016-12-14 14:42:46.73',
               'sha1': '32a798a37ef782da10a09d74aa1e5be91f2861db',
               'version': (1, 4, 24, 0, 0)},
 'mod_wsgi': {'date': '2016-12-14 14:42:24.34',
              'sha1': '8871e5fde8e4e74372bb647445a55dac3b063691',
              'version': (0, 0, 0, 0, 0)},
 'modernize': {'date': '2016-12-14 14:41:33.50',
               'sha1': '494e0263eabb9ff75937fa6e9c721554f03eff26',
               'version': (0, 4, 0, 0, 0)},
 'mysql-connector-python': {'date': '2016-12-14 14:43:13.65',
                            'sha1': 'none',
                            'version': (0, 0, 0, 0, 0)},
 'mysql-python': {'date': '2016-12-14 14:43:28.26',
                  'sha1': 'none',
                  'version': (0, 0, 0, 0, 0)},
 'parsley': {'date': '2016-12-14 14:42:13.84',
             'sha1': '74077da63c979cab422dcb3b7aea2df6d2ca9440',
             'version': (0, 0, 0, 0, 0)},
 'pylint': {'date': '2016-12-14 14:41:21.96',
            'sha1': 'none',
            'version': 'unknown'},
 'pymysql': {'date': '2016-12-14 14:43:19.60',
             'sha1': 'none',
             'version': (0, 0, 0, 0, 0)},
 'pyodbc': {'date': '2016-12-14 14:44:26.01',
            'sha1': '70898ae1170e360af4101b913f23115fa2cec62f',
            'version': (3, 0, 7, 0, 0)},
 'python-memcached': {'date': '2016-12-14 14:42:47.79',
                      'sha1': '1a7064f913143d0279a4bd8cfc0203e30489a47a',
                      'version': (1, 54, 0, 0, 0)},
 'pytz': {'date': '2016-12-14 14:41:52.85',
          'sha1': '847536ab68c7258e891bfce89a516c39dae1ff76',
          'version': (2014, 9, 0, 0, 0)},
 'stsci.sphinxext': {'date': '2016-12-14 14:41:36.89',
                     'sha1': 'none',
                     'version': 'unknown'},
 'unixODBC': {'date': '2016-12-14 14:43:59.33',
              'sha1': '815cbc4f34e1a6d95daf3a5ab74e6ed3a586aad7',
              'version': (2, 3, 1, 0, 0)}}
