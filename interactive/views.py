# Create your views here.

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

import crds.rmap as rmap

def _get_ctx(imap):
    ctx = rmap.get_cached_mapping(imap)
    assert isinstance(ctx, rmap.InstrumentContext), "Invalid instrument context " + repr(imap)
    return ctx

def render(request, template, dict_):
    return render_to_response(template, RequestContext(request, dict_))

def bestrefs_input(request, imap):
    ctx = _get_ctx(imap)
    required_keys = list(ctx.get_required_parkeys())
    parkey_map_items = sorted(ctx.get_parkey_map().items())
    return render(request, "bestrefs_input.html", locals())

def bestrefs_compute(request, imap):
    ctx = _get_ctx(imap)
    header = {}
    needed_keys = list(ctx.get_required_parkeys())
    needed_keys.remove("REFTYPE")
    for key in needed_keys:
        if key.startswith("*"):
            key = key[1:]
        header[str(key)] = str(request.POST[key])
    bestrefs = ctx.get_best_references(header)
    bestrefs_items = [ (key.upper(), val) for (key, val) in sorted(bestrefs.items())]
    return render(request, "bestrefs_results.html", locals())
