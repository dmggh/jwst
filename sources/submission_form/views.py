from django.shortcuts import render
from django.utils import timezone
from .models import Submission
from .forms import SubmissionForm
from django.shortcuts import redirect
from django.http import HttpResponseNotFound
import crds_server.interactive

from ..interactive.views import error_trap, log_view, login_required, group_required, instrument_lock_required

def redcat_list(request):
    submissions = Submission.objects.filter(published_date__lte=timezone.now()).order_by('published_date').reverse()
    return render(request, 'submission_list.html', {'submissions': submissions})

#def most_recent(request):
#    try:
#        s = Submission.objects.order_by('-published_date')[0].__dict__
#    except IndexError:
#        return HttpResponseNotFound('<h2>No submissions found</h2>'.format(id))
#    return render(request, 'submission_form/most_recent.html', {'submission': s})

def redcat_id_detail(request, id):
    #print ('ID:  ', id)
    try:
        s = Submission.objects.filter(id=id)[0].__dict__
    except IndexError:
        return HttpResponseNotFound('<h2>Submission ID={} not found</h2>'.format(id))
    return render(request, 'submission_id_detail.html', {'submission': s})

@error_trap("submission_edit.html")
@log_view
@login_required
@group_required("file_submission")
@instrument_lock_required
def redcat_submit(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        form = SubmissionForm()
        input_pars = {"form":form}
        return crds_server.interactive.views.batch_submit_references(
            request, input_pars, "submission_edit.html")
    else:
        form = SubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.published_date = timezone.now()
            submission.publish()
            
            # Call function in CRDS to ingest delivery here:
            print ('CALL CRDS FUNCTION HERE...')
            s = {k: str(v) for k, v in Submission.objects.order_by('-published_date')[0].__dict__.items()}
            s.pop('_state')
            print (s)
            
            output_pars = {"submission" : s}
            return crds_server.interactive.views.batch_submit_references_post(
                request, output_pars, "submission_detail.html")
        else:
            input_pars = {"form":form}
            request.method = 'GET'
            return crds_server.interactive.views.batch_submit_references(
                request, input_pars, "submission_edit.html")

