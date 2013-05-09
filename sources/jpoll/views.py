# Create your views here.

from __future__ import print_function

import sys
import time
import json

from django.shortcuts import render as django_render
from django.http import HttpResponse, HttpResponseRedirect

from crds.server.jpoll import models as jmodels

def open_channel(request):
    channel = jmodels.ChannelModel.open(request.session.session_key)
    return HttpResponse(json.dumps(channel.key), mimetype='application/json')

def close_channel(request):
    channel = jmodels.ChannelModel.open(request.session.session_key)
    channel.wipe()
    return HttpResponse(json.dumps(channel.key), mimetype='application/json')

def pull_messages(request):
    channel = jmodels.ChannelModel.open(request.session.session_key)
    messages = channel.pull()
    return HttpResponse(json.dumps(messages), mimetype='application/json')

def log_message(request, message):
    """Add `text` to the series of log messages."""
    jmodels.ChannelModel.open(request.session.session_key).log(message)
    
def test_page(request):
    return django_render(request, "test_page.html")

def test_worker(request):
    for i in range(20):
        log_message(request, "Doing #" + str(i))
        time.sleep(2)
    return HttpResponse(json.dumps("OK"), mimetype='application/json')
    
