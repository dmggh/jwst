from django.shortcuts import render

import crds_server.interactive.views

# Create your views here.

def test_batch_submit_references(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        input_pars = {}
        return crds_server.interactive.views.batch_submit_references(
            request, input_pars, "batch_submit_reference_input_2.html")
    else:
        output_pars = {}
        return crds_server.interactive.views.batch_submit_references_post(
            request, output_pars, "batch_submit_reference_results_2.html")
