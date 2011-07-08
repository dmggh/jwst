# Create your views here.

from django.http import HttpResponse
from django.shortcuts import render_to_response

import crds.rmap as rmap

def _get_ctx(imap):
    ctx = rmap.get_cached_mapping(imap)
    assert isinstance(ctx, rmap.InstrumentContext), "Invalid instrument context " + repr(imap)
    return ctx

def bestrefs_input(request, imap):
    ctx = _get_ctx(imap)
    required_keys = list(ctx.get_required_parkeys())
    return render_to_response("bestrefs_input.html", locals())

def bestrefs_compute(request):
    context = request.POST["instrument-context"]
    ctx = _get_ctx(context)
    header_text = request.POST["header-key-values"]
    header = {}
    for line in header_text.split("\n"):
        words = line.split()
        if words:
            header[words[0]] = " ".join(words[1:])
    bestrefs = ctx.get_best_references(header)
    return render_to_reponse("bestrefs_results.html", locals())