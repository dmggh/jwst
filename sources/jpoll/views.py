"""JPOLL supports asynchronous messaging between Django view functions and
appropriately configured pages.   Messages output to a view function JPOLL 
handler are nominally communicated to the database and downloaded to the page
by asynchonous AJAX message poll calls while a long running view is computing.
A final completion message ("done") can be sent to by-pass the nominal view 
page response;  the done response is capable of replacing the synchronous 
page response of the primary view,  sometimes made necessary by timeouts of
intermediate systems,  such as the proxy,  which would otherwise cause the
final page display to fail.
"""

# Create your views here.

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str
# from builtins import range
# from builtins import object

import sys
import time
import json
import datetime
import re
import uuid

from django.shortcuts import render as django_render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from . import models as jmodels

#---------------------------------------------------------------------------------------------

# e.g. 'JPOLL-KEY-2014-02-11-14:26:44.080829'
# JPOLL_KEY_RE_STR = r"JPOLL-KEY-\d\d\d\d-\d\d-\d\d-\d\d:\d\d:\d\d(.\d\d\d\d\d\d)?"
# JPOLL_KEY_RE = re.compile(r"^" + JPOLL_KEY_RE_STR + r"$")

JPOLL_KEY_RE_STR = r"[A-Za-z0-9]{8}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{4}\-[A-Za-z0-9]{12}"
JPOLL_KEY_RE = re.compile("^" + JPOLL_KEY_RE_STR + "$")


#---------------------------------------------------------------------------------------------
# Utility functions

def jdebug(*args):
    pass
    # print(*args, file=sys.stderr)

#---------------------------------------------------------------------------------------------

def new_key(request):
    """Create the unique identifier for this JPOLL channel."""
    request.session["jpoll_key"] = key = str(uuid.uuid4())
    return key

def get_key(request):
    """Fetch the unique JPOLL channel identifier for this request."""
    key = None
    try:
        key = request.session["jpoll_key"]
    except:
        print("Failed fetching JPOLL key from request.session.", file=sys.stderr)
    return key

def get_or_new_key(request):
    if "jpoll_key" in request.session:
        key = get_key(request)
        jdebug("JPOLL get_or_new_key() session has existing key:", key)
    else:
        key = new_key(request)
        jdebug("JPOLL get_or_new_key() creating key:", key)
    return key

def get_channel(request):
    """Based on `request`,  load the JPOLL channel for it and return it."""
    key = get_key(request)
    return get_channel_from_key(key)

def get_channel_from_key(key):
    assert JPOLL_KEY_RE.match(key), "Badly formatted jpoll_key " + repr(key)
    return jmodels.ChannelModel.open(key)

from crds import log
def log_view(func):
    """log() captures view inputs, output, and response to a log file.
    It should be called inside any error_trap() decorator so that it
    executes before error_trap() absorbs many exceptions.
    """
    def dolog(request, *args, **keys):
        """trap() is bound to the func parameter of decorator()."""
        log.info() # start with blank line to make concat logs readable
        log.info("REQUEST:", request.path, request.method, "ajax="+str(request.is_ajax()))
        # log.info("META:", log.PP(request.META))
        if request.GET:
            log.info("GET:",   repr(request.GET))
        if request.POST:
            log.info("POST:",  repr(request.POST))
#        if request.COOKIES:
#            log.info("COOKIES:", repr(request.COOKIES), stdout=None)
        # log.info("SESSION:", request.session.session_key, "expires", request.session.get_expiry_date())
        if request.FILES:
            log.info("FILES:", repr(request.FILES))
        # log.info("OUTPUT:")
        try:
            response = func(request, *args, **keys)
#            log.info("RESPONSE:\n" + response.content, stdout=None)
            return response
        except Exception as exc:
            log.info("EXCEPTION REPR:", repr(exc))
            log.info("EXCEPTION STR:", str(exc))
            log.info("EXCEPTION TRACEBACK:")
            info = sys.exc_info()
            tb_list = traceback.extract_tb(info[2])
            for line in traceback.format_list(tb_list):
                log.info(line.strip(), time=False)
            raise
        finally:
            pass
    dolog.__name__ = func.__name__
    return dolog

#---------------------------------------------------------------------------------------------------
# View functions

#@log_view
@login_required
def open_channel(request):
    """Based on `request`,  attach a new JPOLL channel to it and return it."""
    key = new_key(request)
    jdebug("jpoll: open_channel:", key)
    jmodels.ChannelModel.wipe_key(key)
    jmodels.ChannelModel.new(key)
    return HttpResponse(json.dumps(key), content_type='application/json')

# @log_view
@login_required
def close_channel(request, channel_id):
    """Based on `request`,  close the JPOLL channel associated with it,  wiping out old messages."""
    jdebug("jpoll: close_channel:", channel_id)
    channel = get_channel_from_key(channel_id)
    channel.wipe()
    return HttpResponse(json.dumps(channel_id), content_type='application/json')

# @log_view
@login_required
def pull_messages(request, channel_id, since_id=None):
    """Return any pending JPOLL messages on the channel associated with `request` as a JSON response."""
    jdebug("pull_messages entered.")
    channel = get_channel_from_key(channel_id)
    since_id = int(since_id) if since_id else None
    jdebug("pull_messages got channel:", channel)
    messages = channel.pull(since_id)
    jdebug("jpoll: pulled messages for", repr(channel.key), "=", messages)
    return HttpResponse(json.dumps(messages), content_type='application/json')

def pull_messages_core(key, since_id=0):
    channel = get_channel_from_key(key)
    messages = channel.pull(since_id)
    jdebug("jpoll: pulling messages for", repr(channel.key), "=", messages)
    return messages

#---------------------------------------------------------------------------------------------
# JPOLL Handler client functions

def get_jpoll_handler_from_key(key):
    """Return the jpoll handler associated with this key,  suitable as a Stream for logging
    and supporting a done(status, result) method for reporting request results via jpoll.
    """
    return JpollHandler(key)

def get_jpoll_handler(request):
    """Return the jpoll handler associated with this request,  suitable as a Stream for logging
    and supporting a done(status, result) method for reporting request results via jpoll.
    """
    return get_jpoll_handler_from_key(get_key(request))

class JpollHandler(object):
    """A JpollHandler is a stream handler for the Python logger which routes to the jpoll log_message stream.

    A JpollHandler also supports other messages of the jpoll protocol,  including done() for reporting
    "asynchronous" results.
    """
    def __init__(self,  key):
        try:
            self.channel = jmodels.ChannelModel.open(key)
        except Exception:
            self.channel = jmodels.ChannelModel.new(key)

    @property
    def key(self):
        return self.channel.key

    @property
    def monitor_url(self):
        from crds_server import config
        return config.CRDS_URL + "monitor/" + self.channel.key + "/"

    def write(self, message):
        """Output `message` to self's JPOLL channel."""
        try:
            if self.channel is not None:
                self.channel.log(message)
        except Exception as exc:
            sys.stderr.write("ERROR in JPOLL write() of '%s': exception '%s'" % (message, str(exc)))
            
    def flush(self):
        """Dummy to make a JpollHandler a file-like object/."""
    
    def done(self, status, result):
        """Should be called when a view is done computing to present the result."""
        try:
            if self.channel is not None:
                self.channel.done(status, result)
        except Exception as exc:
            sys.stderr.write("ERROR in JPOLL done() of %s: exception '%s'" % ((status, result), str(exc)))

#---------------------------------------------------------------------------------------------

def log_message(request, message):
    """Add `text` to the series of log messages."""
    jdebug("jpoll: log_message: ", message)
    channel = get_channel(request)
    channel.log(message)

def test_page(request):
    return django_render(request, "test_page.html")

def test_worker(request):
    handler = get_jpoll_handler(request)
    for i in range(5):
        handler.write("Doing #" + str(i))
        time.sleep(5)
    handler.done(0, "/jpoll/test_response/")
    time.sleep(10)
    return HttpResponse("OK")   # json.dumps("OK"), content_type='application/json')

def test_response(request):
    return HttpResponse("yippee!  it worked!")


