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

import sys
import time
import json
import datetime
import re

from django.shortcuts import render as django_render
from django.http import HttpResponse

from . import models as jmodels

#---------------------------------------------------------------------------------------------

def jdebug(*args):
    '''print(*args, file=sys.stderr)'''

def new_key(request):
    """Create the unique identifier for this JPOLL channel."""
    key = "JPOLL-KEY-" + str(datetime.datetime.now()).replace(" ","-")
    request.session["jpoll_key"] = key
    return key

# e.g. 'JPOLL-KEY-2014-02-11-14:26:44.080829'
JPOLL_KEY_RE = re.compile(r"^JPOLL-KEY-\d\d\d\d-\d\d-\d\d-\d\d:\d\d:\d\d(.\d\d\d\d\d\d)?$")

def get_key(request):
    """Fetch the unique JPOLL channel identifier for this request."""
    key = request.session["jpoll_key"]
    assert JPOLL_KEY_RE.match(key), "Badly formatted jpoll_key " + repr(key)
    return key
 
def get_channel(request):
    """Based on `request`,  load the JPOLL channel for it and return it."""
    key = get_key(request)
    return jmodels.ChannelModel.open(key)

def open_channel(request):
    """Based on `request`,  attach a new JPOLL channel to it and return it."""
    key = new_key(request)
    jdebug("jpoll: open_channel:", key)
    jmodels.ChannelModel.wipe_key(key)
    jmodels.ChannelModel.new(key)
    return HttpResponse(json.dumps(key), mimetype='application/json')

def close_channel(request):
    """Based on `request`,  close the JPOLL channel associated with it,  wiping out old messages."""
    key = get_key(request)
    jdebug("jpoll: close_channel:", key)
    channel = get_channel(request)
    channel.wipe()
    return HttpResponse(json.dumps(key), mimetype='application/json')

def pull_messages(request):
    """Return any pending JPOLL messages on the channel associated with `request` as a JSON response."""
    channel = get_channel(request)
    messages = channel.pull()
    jdebug("jpoll: pulling messages for", repr(channel.key), "=", messages)
    return HttpResponse(json.dumps(messages), mimetype='application/json')

#---------------------------------------------------------------------------------------------

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
            self.channel = None

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
    return HttpResponse("OK")   # json.dumps("OK"), mimetype='application/json')

def test_response(request):
    return HttpResponse("yippee!  it worked!")


