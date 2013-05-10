# Create your views here.

from __future__ import print_function

import sys
import time
import json
import logging

from django.shortcuts import render as django_render
from django.http import HttpResponse, HttpResponseRedirect

from . import models as jmodels

#---------------------------------------------------------------------------------------------

def jdebug(*args):
    """print(*args, file=sys.stderr)"""

def new_key(request):
    return request.session.session_key

def get_key(request):
     return request.session.session_key
     
def get_channel(request):
    key = get_key(request)
    return jmodels.ChannelModel.open(key)

def open_channel(request):
    key = new_key(request)
    jdebug("jpoll: open_channel:", key)
    jmodels.ChannelModel.wipe_key(key)
    jmodels.ChannelModel.new(key)
    return HttpResponse(json.dumps(key), mimetype='application/json')

def close_channel(request):
    key = get_key(request)
    jdebug("jpoll: close_channel:", key)
    channel = get_channel(request)
    channel.wipe()
    return HttpResponse(json.dumps(key), mimetype='application/json')

def pull_messages(request):
    channel = get_channel(request)
    messages = channel.pull()
    jdebug("jpoll: pulling messages for", repr(channel.key),"=", messages)
    return HttpResponse(json.dumps(messages), mimetype='application/json')

#---------------------------------------------------------------------------------------------

def get_jpoll_log_handler(request):
    return JpollStream(get_key(request))

class JpollStream(object):
    """A stream handler for the Python logger which routes to the jpoll log_message stream."""
    def __init__(self,  key):
        try:
            self.channel = jmodels.ChannelModel.open(key)
        except:
            self.channel = None

    def write(self, message):
        if self.channel is not None:
            self.channel.log(message)
        
    def flush(self):
        pass
    
#---------------------------------------------------------------------------------------------

def log_message(request, message):
    """Add `text` to the series of log messages."""
    jdebug("jpoll: log_message: ", message)
    channel = get_channel(request)
    channel.log(message)

def test_page(request):
    return django_render(request, "test_page.html")

def test_worker(request):
    for i in range(5):
        log_message(request, "Doing #" + str(i))
        time.sleep(2)
    return HttpResponse("OK")   # json.dumps("OK"), mimetype='application/json')

