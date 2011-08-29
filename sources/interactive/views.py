# Create your views here.
import os.path
import re
import hashlib
import xml.sax.saxutils as saxutils

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import django.utils.safestring as safestring

import django.contrib.auth
from django.contrib.auth.decorators import login_required

from crds import (rmap, utils, certify, timestamp, uses, newcontext)

import crds.server.config as config
import crds.server.interactive.models as models
import crds.pysh as pysh

from crds.server.interactive.models import FieldError, MissingInputError

# ===========================================================================

def _get_imap(request):
    """Convert a request into an instrument context name."""
    post = request.POST
    try:
        mode = post["context-mode"]
        print mode
    except KeyError:
        return post["instrument-context"]
    else:
        return post["context-user"] if mode == "user" else post["context-default"]

def _get_ctx(request):
    """Convert a request into an instrument context object."""
    imap = _get_imap(request)
    ctx = rmap.get_cached_mapping(imap)
    assert isinstance(ctx, rmap.InstrumentContext), "Invalid instrument context " + repr(imap)
    return ctx

def check_value(value, pattern, msg):
    value = str(value)
    if isinstance(pattern, type(check_value)):
        try: 
            return pattern(value)
        except AssertionError, exc:
            raise FieldError(msg + " : " + str(exc))
    elif isinstance(pattern, list):
        for choice in pattern:
            assert "|" not in choice, "Found | in choice " + repr(choice) + \
                " seen as regex special char"
        pattern = "|".join(pattern)
    if not re.match(pattern, value):
        raise FieldError(msg)
    return value

def validate_post(request, variable, choices):
    value = str(request.POST[variable])
    return check_value(value, choices, "Invalid value " + repr(value) + 
                                        " for " + repr(variable))
def validate_get(request, variable, choices):
    value = str(request.GET[variable])
    return check_value(value, choices, "Invalid value " + repr(value) + 
                                        " for " + repr(variable))

def render(request, template, dict_=None):
    """Top level index page."""
    rdict = {}
    for key, value in request.GET.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.POST.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.FILES.items():
        rdict[key] = safestring.mark_for_escaping(value)
    if dict_ is not None:
        for key, value in dict_.items():
            rdict[key] = value
    rdict["is_authenticated"] = request.user.is_authenticated()
    return render_to_response(template, RequestContext(request, rdict))

def handle_known_or_uploaded_file(request, name, modevar, knownvar, uploadvar):
    """Process file variables for a file which is either known to CRDS
    and simply named,  or which is uploaded by the user.
    
    Return (uploaded_flag, name_on_users_system,  temporary_file_path)
    """
    if request.POST[modevar] == knownvar:
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = check_value(request.POST[knownvar],
            "[A-Za-z0-9._]+", 
            "Filename " + name + " must consist of letters, numbers, periods, "
            "or underscores.")
        filepath = get_known_filepath(original_name)
        uploaded = False
    else:
        ufile = get_uploaded_file(request, uploadvar)
        filepath = ufile.temporary_file_path()
        original_name = ufile.name
        uploaded = True
    return uploaded, original_name, filepath

def get_known_filepath(original_name):
    if rmap.is_mapping(original_name):
        try:
            filepath = models.MappingBlob.load(original_name).pathname
        except LookupError:
            try:
                loc = utils.get_locator_module("hst")
                filepath = loc.locate_server_mapping(original_name)
            except Exception, exc:
                raise FieldError(
                    "Couldn't find mapping " + original_name)
    elif original_name.endswith(".fits"):
        try:
            filepath = models.ReferenceBlob.load(original_name).pathname
        except LookupError:
            try:
                loc = utils.get_locator_module("hst")
                filepath = loc.locate_server_reference(original_name)
            except Exception, exc:
                raise FieldError(
                    "Couldn't find reference file " + original_name)
    else:
        raise FieldError(
            original_name + " should have .pmap, .imap, .rmap, or .fits extension.")
    return filepath


def remove_temporary(filepath):
    """Attempt to remove `filepath`.  Ignore errors."""
    try:
        assert not filepath.startswith("/grp"), \
            "ERROR -- attempt to delete from Central Store"
        os.remove(filepath)
    except OSError:
        pass
    

# ===========================================================================

class CrdsError(Exception):
    """Something bad but understood happened in CRDS processing."""

def error_trap(template):
    """error_trap() is a 'decorator maker' which returns a decorator which traps 
    exceptions in views and re-issues the input `template` with an 
    appropriate error message so the user can try again.
    """
    def decorator(func):
        def trap(request, *args, **keys):
            try:
                return func(request, *args, **keys)
            except CrdsError, exc:
                return render(request, template, {"error_message" : str(exc)})
            except FieldError, exc:
                return render(request, template, {"error_message" : str(exc)})
        trap.func_name = func.func_name
        return trap
    return decorator

# ===========================================================================

def index(request):
    return render(request, "index.html", {})

# ===========================================================================

def logout(request):
    django.contrib.auth.logout(request)
    return render(request, "logout.html", {})
        
# ===========================================================================

def bestrefs_index(request):
    return render(request, "bestrefs_index.html", {})

def bestrefs_input(request):
    """Prompt for best ref inputs."""
    ctx = _get_ctx(request)
    required_keys = list(ctx.get_required_parkeys())
    parkey_map_items = sorted(ctx.get_parkey_map().items())
    return render(request, "bestrefs_input.html", locals())

def bestref_link(ctx, reference):
    """Return an appropriate anchor tag for `reference`."""
    if not reference.startswith("NOT FOUND"):
        try:
            url = ctx.locate.reference_url(config.CRDS_REFERENCE_URL, reference)
            return '<a href="%s">%s</a>' % (url, reference)
        except:
            return reference
    else:
        return reference[len("NOT FOUND "):]
    
def bestrefs_compute(request):
    """Compute and display best reference results."""
    ctx = _get_ctx(request)
    header = {}
    needed_keys = list(ctx.get_required_parkeys())
    needed_keys.remove("REFTYPE")
    for key in needed_keys:
        if key.startswith("*"):
            key = key[1:]
        header[str(key)] = str(request.POST[key])
    bestrefs = ctx.get_best_references(header)
    header_items = sorted(header.items())
    bestrefs_items = [ (key.upper(), bestref_link(ctx, val)) for (key, val) in sorted(bestrefs.items())]
    return render(request, "bestrefs_results.html", locals())

# ============================================================================

@error_trap("submit_input.html")
@login_required
def submit_file(request):
    """Handle file submission."""
    if request.method == 'POST':
        baseperm = submit_file_post(request)
        return render(request, 'submit_results.html', {"baseperm":baseperm})
    else: # GET
        return render(request, 'submit_input.html')
    
def submit_file_post(request):
    """Handle the POST case of submit_file,   returning dict of template vars.
    """
    observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
    
    # Get the UploadedFile object
    ufile = get_uploaded_file(request, "filename")

    original_name = ufile.name

    # Determine the temporary and permanent file paths, keeping file temporary.
    upload_location, permanent_location = handle_crds_locations(ufile)

    # Check the file,  leaving no server state if it fails.  Give error results.
    do_certify_file(original_name, upload_location)
    
    # Make sure none of the dependencies are blacklisted,  else fail w/o state.
    blacklisted_by, exceptions = get_blacklists(original_name, upload_location)
    if blacklisted_by:
        raise CrdsError("File " + repr(original_name) + 
                        " is blacklisted by " + repr(blacklisted_by))
    if exceptions:
        raise CrdsError("Exceptions during blacklisting check: " + 
                        repr(exceptions))

    # Copy the temporary file to its permanent location.
    upload_file(ufile, permanent_location)
    
    modifier_name = check_value(request.POST["modifier_name"], "[A-Za-z0-9 _.@]+",
                              "Invalid modifier name.")

    description = check_value(request.POST["description"], "[^<>]+",
                              "Invalid description.")

    # Make a database record of this delivery.
    create_delivery_blob(observatory, original_name, permanent_location,
        request.user, request.user.email, modifier_name, description)
    
    return os.path.basename(permanent_location)


def do_certify_file(basename, certifypath, check_references=True):
    """Run un-trapped components of crds.certify and re-raise any exception
    as a CrdsError which will be displayed as a form error on the submission
    page.
    """
    try:
        if rmap.is_mapping(basename):
            certify.certify_mapping(
                certifypath, check_references=check_references)
        else:
            certify.certify_fits(certifypath)
    except Exception, exc:
        raise CrdsError(str(exc))

def get_blacklists(basename, certifypath, ignore_self=True):
    """Raise an exception if any of the child mappings or references of
    `basename` are blacklisted,  i.e. don't allow submissions which reference
    blacklisted files.
    """
    if rmap.is_mapping(basename):
        blacklisted_by = set()
        try:
            mapping = rmap.load_mapping(certifypath)
        except Exception, exc:
            raise CrdsError("Error loading " + repr(basename) + 
                            "for blacklist checking." + str(exc))
        map_names = mapping.mapping_names()
        exceptions = []
        for child in map_names:
            if ignore_self and child == os.path.basename(certifypath): 
                continue
            try:
                child_blob = models.MappingBlob.load(child)
            except LookupError:
                exceptions.append("File " + repr(child) + 
                                  " is not known to CRDS.")
                continue
            if child_blob.blacklisted_by:
                blacklisted_by = blacklisted_by.union(
                                    set(child_blob.blacklisted_by))
        ref_names = mapping.reference_names()
        for child in ref_names:
            try:
                child_blob = models.ReferenceBlob.load(child)
            except LookupError:
                exceptions.append("File " + repr(child) + 
                                  " is not known to CRDS.")
                continue
            if child_blob.blacklisted_by:  # must be blacklisted by self
                blacklisted_by = blacklisted_by.union(
                                    set(child_blob.blacklisted_by)) 
        return sorted(list(blacklisted_by)), []
    else:
        return [], []
    
def get_uploaded_file(
    request, formvar, legal_exts=(".fits", ".pmap", ".imap", ".rmap")):
    """Return the DJango UploadedFile associated with `request` and `formavar`,
    raising an exception if it's original name does not end with one of
    `legal_exts` file extensions.
    """
    try:
        ufile = request.FILES[formvar]
    except KeyError:
        raise MissingInputError("Specify a file to upload.")
    if not ufile.name.endswith(legal_exts):
        raise FieldError("File extension for " + repr(str(ufile.name)) + \
                 " not one of: " + ", ".join(legal_exts))
    return ufile

def handle_crds_locations(uploaded_file, clobber=False):
    """Given a Django `uploaded_file` object, determine where it should reside
    permanently.  If `clobber` is False ensure that the permanent filename does
    not already exist on the file system or in the database,  raising an
    exception if it does exist.   Return both the temporary upload path and
    the location the file should reside permanently.
    """
    # determine where to store
    upload_location = uploaded_file.temporary_file_path()
    permanent_location = create_crds_name(upload_location, uploaded_file.name)
    baseperm = os.path.basename(str(permanent_location))
    if not clobber and \
       (os.path.exists(permanent_location) or models.FileBlob.exists(baseperm)):
        raise FieldError("File " + repr(baseperm) + " already exists.")    
    return upload_location, permanent_location

def upload_file(ufile, where):
    """Copy the Django UploadedFile to it's permanent location."""
    utils.ensure_dir_exists(where)
    destination = open(where, 'wb+')
    for chunk in ufile.chunks():
        destination.write(chunk)
    destination.close()
    
def create_crds_name(upload_location, upload_name):
    """Determine where a file should be stored on a permanent basis,  assigning
    it both an appropriate path and (possibly) a unique name.  `upload_location`
    is the file's temporary upload path.  upload_name is how the file was named
    on the user's computer,  not the temporary file.
    """
    return upload_name   # XXX Fake for now

def create_delivery_blob(observatory, upload_name, permanent_location, 
        deliverer_user, deliverer_email, modifier_name, description, 
        add_slow_fields=True):
    """Make a record of this delivery in the CRDS database."""
    if upload_name.endswith(".fits"):
        blob = models.ReferenceBlob()
    elif rmap.is_mapping(upload_name):
        blob = models.MappingBlob()
    else:
        raise ValueError("Unknown file extension for " + repr(upload_name) +
                         " should be one of: .fits, .pmap, .imap, .rmap")
    blob.uploaded_as = upload_name
    blob.pathname = permanent_location
    blob.delivery_date = timestamp.now()
    blob.deliverer_user = deliverer_user
    blob.deliverer_email = deliverer_email
    blob.modifier_name = modifier_name
    blob.description = description
    blob.observatory = observatory
    if add_slow_fields:
        blob.sha1sum = blob.checksum()
    instrument, filekind, serial = utils.get_file_properties(
        observatory, permanent_location)
    blob.instrument = instrument
    blob.filekind= filekind
    blob.serial = serial
    blob.blacklisted_by = []
    blob.save()
    
    # XXX some redundancy here
    models.AuditBlob.create_record(
        deliverer_user, "submit file", blob.filename, description, "",
        observatory=observatory, instrument=instrument,  filekind=filekind,
        date=blob.delivery_date,)

# ===========================================================================

@error_trap("blacklist_input.html")
@login_required
def blacklist_file(request):
    if request.method == "GET":
        return render(request, "blacklist_input.html")
    else:
        return blacklist_file_post(request)

def blacklist_file_post(request):
    observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
    blacklist_root = check_value(request.POST["file_known"],
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
    badflag = check_value(request.POST["badflag"], "bad|ok",
            "badflag must be either 'bad' or 'ok'")
    why = check_value(request.POST["why"],
            "[A-Za-z0-9._ ]+", 
            "Reason description is limited to letters, "
            "numbers, period, underscore and space.   Cannot be blank.")
    
    # Figure out all files which indirectly or directly reference `blacklist_root`
    uses_files = uses.uses([blacklist_root], observatory)

    all_blacklisted = [blacklist_root] + uses_files
    
    for also_blacklisted in all_blacklisted:
        do_blacklist(
            blacklist_root, also_blacklisted, badflag, why, request.user)
    
    instrument, filekind, serial = utils.get_file_properties(
            observatory, blacklist_root)

    models.AuditBlob.create_record(
        request.user, "blacklist", blacklist_root, why, "marked as " + badflag,
        observatory=observatory, instrument=instrument, filekind=filekind)

    return render(request, "blacklist_results.html", 
                  { "all_blacklisted": all_blacklisted })

def do_blacklist(blacklist_root, blacklisted, badflag, why, user):
    """Mark one file, `blacklisted`, with status `badflag` and reason `why`."""
    try: 
        if rmap.is_mapping(blacklisted):
            blob = models.MappingBlob.load(blacklisted)
        elif blacklisted.endswith(".fits"):
            blob = models.ReferenceBlob.load(blacklisted)
        else:
            raise FieldError("Bad file extension for file " + repr(blacklisted))
    except LookupError:
        raise FieldError("Unknown file " + repr(blacklisted))
    if badflag == "bad":
        if blacklist_root not in blob.blacklisted_by:
            blob.blacklisted_by.append(blacklist_root)
    else:
        while blacklist_root in blob.blacklisted_by:
            blob.blacklisted_by.remove(blacklist_root)
    blob.save()
    
        
# ===========================================================================

@error_trap("certify_input.html")
@login_required
def certify_file(request):
    """Check for the existence and validity
    """
    if request.method == "GET":
        return render(request, "certify_input.html")
    else:
        return certify_post(request)

def certify_post(request):

    uploaded, original_name, certified_file = handle_known_or_uploaded_file(
        request, "File", "filemode", "file_known", "file_uploaded")
            
    check_references = request.POST.get("check_references", False)
    shallow = "--shallow" if not check_references else ""
    mapping = "--mapping" if rmap.is_mapping(original_name) else ""

    certify_lines = pysh.lines(
        "python -m crds.certify ${certified_file} ${shallow} ${mapping}")
    certify_status = "OK" if "0 errors" in \
        [ x.strip() for x in certify_lines] else "Failed."    
    
    if not rmap.is_mapping(original_name):
        fitscheck_lines = pysh.lines("fitscheck ${certified_file}")
        fitscheck_status = "OK" if "0 errors" in \
            [x.strip() for x in fitscheck_lines] else "Failed."
    else:
        fitscheck_status = ""
        fitscheck_lines = []
        
    blacklisted_by, blacklist_exceptions = get_blacklists(
        original_name, certified_file, ignore_self=False)
    blacklist_status = "OK" if not (blacklisted_by or blacklist_exceptions) \
        else "BLACKLISTED"
    
    if uploaded:
        remove_temporary(certified_file)
        
    return render(request, "certify_results.html", 
            {"certify_status":certify_status,
             "fitscheck_status":fitscheck_status, 
             "blacklist_status":blacklist_status,
             "is_reference": not rmap.is_mapping(original_name),
             "certify_lines":certify_lines,
             "fitscheck_lines":fitscheck_lines,
             "blacklisted_by" : blacklisted_by,
             "blacklist_exceptions" : blacklist_exceptions,
             "certified_file":original_name})

# ===========================================================================

@error_trap("using_file_inputs.html")
def using_file(request):
    if request.method == "GET":
        return render(request, "using_file_inputs.html")
    else:
        observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
        referred_file = check_value(request.POST["referred_file"], 
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
        uses_files = uses.uses([referred_file], observatory)
        if not "".join(uses_files).strip():
            uses_files = ["no files"]
        return render(request, "using_file_results.html", locals())

# ===========================================================================

def extension(filename): 
    """Return the file extension of `filename`."""
    return os.path.splitext(filename)[1]

@error_trap("difference_input.html")
def difference_files(request):
    """Compare two files,  either known or uploaded,  and display the diffs."""
    if request.method == "GET":
        return render(request, "difference_input.html")
    else:
        uploaded1, file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "File1", "filemode1", "file_known1", "file_uploaded1")
        uploaded2, file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "File2", "filemode2", "file_known2", "file_uploaded2")
        
        if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
            extension(file1_orig) == extension(file2_orig):
            diff_lines = pysh.lines("diff ${file1_path} ${file2_path}")
            diff_lines = format_mappingdiffs(diff_lines, file1_path, file2_path)
        elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
            diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
            diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path)
        else:
            raise CrdsError("Files should be either CRDS mappings of the same type or .fits files")
        
        if uploaded1: 
            remove_temporary(file1_path)
        if uploaded2:
            remove_temporary(file2_path)
            
        if not "".join(diff_lines).strip():
            diff_lines = ["no differences"]

        return render(request, "difference_results.html", 
                      {
                       "diff_lines" : diff_lines,
                       "file1" : file1_orig,
                       "file2" : file2_orig,
                       })

def format_fitsdiffs(lines, file1, file2):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        lines[i] = clean_path(lines[i], file1)
        lines[i] = clean_path(lines[i], file2)
        if "Primary HDU" in lines[i] or re.search("Extension \d+ HDU", lines[i]):
            lines[i] = "<h3>" + lines[i] + "</h3>"
        lines[i] = re.sub(r"([Kk]eyword)\s*([A-Za-z0-9_]*)",
                          r"\1 <span class='green'>\2</span>",
                          lines[i])
    return lines

def format_mappingdiffs(lines, file1, file2):
    return lines

def clean_path(line, path):
    """Replace occurrences of `path` in `line` with a greyed version of
    the `path`s basename.
    """
    base = "<span class='grey'>" + os.path.basename(path) + "</span>"
    return line.replace(path, base)

# ===========================================================================

@error_trap("browse_input.html")
def browse_files(request):
    if request.method == "GET":
        return render(request, "browse_input.html")
    else:
        return browse_files_post(request)
    
def browse_files_post(request):
    uploaded, original_name, browsed_file = handle_known_or_uploaded_file(
        request, "File", "filemode", "file_known", "file_uploaded")
    return browse_files_post_guts(
        request, uploaded, original_name, browsed_file)

def browse_files_post_guts(request, uploaded, original_name, browsed_file):
    if not uploaded:
        browse_lines = get_database_lines(original_name, browsed_file)      
    else:
        browse_lines = [
            "<h3>Uploaded file <span class='grey'>%s</span></h3>" % uploaded 
        ]
        
    browse_lines += ["<h3>File Contents</h3>"]
    if rmap.is_mapping(original_name):
        browse_lines += browsify_mapping(original_name, browsed_file)
    else:
        browse_lines += browsify_reference(original_name, browsed_file)
    
    if uploaded:
        remove_temporary(browsed_file)

    return render(request, "browse_results.html", 
            {"browse_lines":browse_lines,
             "browsed_file":original_name})

def get_database_lines(original_name, browsed_file):
    """Return the CRDS database information for this file as a list of HTML
    table lines.
    """
    browse_lines = ["<h3>CRDS Database</h3>"]
    try:
        if rmap.is_mapping(original_name):
            blob = models.MappingBlob.load(os.path.basename(browsed_file))
        else:
            blob = models.ReferenceBlob.load(os.path.basename(browsed_file))
    except LookupError:
        return browse_lines + ['<h3 class="error">database entry not found</h3>']
     
    browse_lines += ["<table>"]
    for fld in sorted(blob.fields):
        browse_lines += [
            "<tr><td class='label''>%s</td>"
            "<td class='value'>%s</td></tr>" % (fld, getattr(blob, fld))
        ]
    browse_lines += ["</table>"]
    
    return browse_lines

def browsify_mapping(original_name, browsed_file):
    lines = []
    try:
        linegen = open(browsed_file).readlines()
    except OSError:
        return ["<h3 class='error'>File <span class='grey'>%s<span> not found</h3>" % \
                (original_name,)]
    for line in linegen:
        lines.append(browsify_mapping_line(line))
    return lines

def browsify_mapping_line(line):
    # header
    line = re.sub(r"(header)(\s*=\s*)",
                  r"<span class='green'>\1</span>\2",
                  line)
    # selector
    line = re.sub(r"(selector)(\s*=\s*)",
                  r"<span class='green'>\1</span>\2",
                  line) 
    # Match
    line = re.sub(r"(Match)(\()",
                  r"<span class='green'>\1</span>\2",
                  line)
    # UseAfter
    line = re.sub(r"(UseAfter)(\()",
                  r"<span class='green'>\1</span>\2",
                  line)
    
    # Tabs -->   4 spaces
    line = re.sub(r"\t", r"&nbsp;"*4, line)
    
    # HACK:  replace any sequence of whitespace with one "tab"
    line = re.sub(r"^\s+", r"&nbsp;"*4, line)
    
    # HACK:  add an extra level of indentation to any line ending with .fits',
    line = re.sub(r"'(.*\.fits',)$",
                  r"&nbsp;"*4 + r"\1",
                  line)
    # mapping or reference filename --> /browse/<file> link
    line = re.sub(r"'([A-Za-z_0-9]+.(fits|pmap|imap|rmap))'",
                  r"""<a href='/browse/\1'>'\1'</a>""",
                  line)

    return "<p>" + line + "</p>"

# Using TPN,  extract interesting header keywords or tables???
def browsify_reference(original_name, browsed_file):
    return []

@error_trap("browse_known_file_error.html")
def browse_known_file(request, original_name):
    browsed_file = get_known_filepath(original_name)
    uploaded = False
    return browse_files_post_guts(
        request, uploaded, original_name, browsed_file)

# ===========================================================================

@error_trap("reserve_name_input.html")
@login_required
def reserve_name(request):
    if request.method == "GET":
        return render(request, "reserve_name_input.html",
                      {"instruments":models.INSTRUMENTS+[""],
                       "filekinds":models.FILEKINDS+[""],
                       "extensions":models.EXTENSIONS})
    else:
        return reserve_name_post(request)

def reserve_name_post(request):
    observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
    mode = check_value(request.POST["filemode"], "file_known|by_field", "Invalid input mode")
    if mode == "file_known":
        known_file = check_value(request.POST["file_known"],
                                 "[A-Za-z0-9_.]+", "Invalid known filename.")
        instrument, filekind, serial = utils.get_file_properties(
                observatory, rmap.locate_file(observatory, known_file))
        extension = os.path.splitext(known_file)[-1]
    else:
        instrument = request.POST["instrument"]
        filekind = request.POST["filekind"]
        extension = request.POST["extension"]
    
    instrument = check_value(instrument, "|".join(models.INSTRUMENTS+[""]), "Invalid instrument")
    filekind = check_value(filekind, "|".join(models.FILEKINDS+[""]), "Invalid file kind")
    extension = check_value(extension, "|".join(models.EXTENSIONS), "Invalid file extension")
    
    try:
        if extension == ".pmap":
            assert instrument == "", "Instrument must be blank for .pmap"
            assert filekind == "", "File kind must be blank for .pmap"
        elif extension == ".imap":
            assert filekind == "", "File kind must be blank for .imap"
        elif extension in [".rmap",".fits"]:
            assert instrument != "", "Instrument must be specified for .rmap, .fits"
            assert filekind != "", "File kind must be specified for .rmap, .fits"
    except AssertionError, exc:
        raise CrdsError(str(exc))
    
    num = get_new_serial(observatory, instrument, filekind, extension)
    
    parts = [x for x in [observatory, instrument, filekind, "%04d" % num] if x]
    reserved_name = "_".join(parts) + extension
    
    models.AuditBlob.create_record(
        request.user, "reserve name", reserved_name, "none", "none",
        observatory=observatory, instrument=instrument, filekind=filekind)

    return render(request, "reserve_name_results.html",
                  {"reserved_name" : reserved_name})
    
def get_new_serial(observatory, instrument, filekind, extension):
    """Return the next reference or mapping serial number associated with the
    given parameters and update the database.
    """
    return models.CounterBlob.next(observatory, instrument, filekind, extension)
    

# ===========================================================================

@error_trap("recent_activity_input.html")
@login_required
def recent_activity(request):
    if request.method == "GET":
        return render(request, "recent_activity_input.html", {
            "actions":["*"]+models.AUDITED_ACTIONS,
            "observatories":["*"]+models.OBSERVATORIES,
            "instruments":["*"]+models.INSTRUMENTS,
            "filekinds":["*"]+models.FILEKINDS,
            "extensions":["*"]+models.EXTENSIONS,
            })
    else:
        return recent_activity_post(request)

def recent_activity_post(request):
    action = validate_post(
        request, "action", models.AUDITED_ACTIONS+[r"\*"])
    observatory = validate_post(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate_post(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate_post(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate_post(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate_post(
        request, "filename", r"[A-Za-z0-9_.\*]+")
    user = validate_post(
        request, "user", r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["action","observatory","instrument","filekind","extension",
                "filename","user"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_activities = models.AuditBlob.filter(**filters)
    return render(request, "recent_activity_results.html", {
                "filters": filters,
                "filtered_activities" : filtered_activities,
            })

# ===========================================================================

def common_updates(request):
    return render(request, "common_updates.html", {})

@error_trap("create_contexts_input.html")
@login_required
def create_contexts(request):
    if request.method == "GET":
        return render(request, "create_contexts_input.html")
    else:
        return create_contexts_post(request)

def create_contexts_post(request):
    pipeline = validate_post(
            request, "pipeline", is_pipeline_mapping)
    updated_rmaps = validate_post(
            request, "rmaps", is_list_of_rmaps)
    description = validate_post(request, "description", "[^<>]+")

    # Get the mapping from old imap to new rmap, basically the imaps that
    # must be updated onto the list of rmap updates to do.
    updates_by_instrument = newcontext.get_update_map(
        pipeline, updated_rmaps)
    
    # For each imap being edited,  and the pipeline context,  reserve new
    # official names and return the dictionary { old_mapping : new_mapping }.
    new_name_map = generate_new_names(pipeline, updates_by_instrument)
    
    # Actually generate the new mappings,  by first copying the old mappings 
    # and then substituting old names with their updated equivalents.
    new_contexts = newcontext.generate_new_contexts(
        pipeline, updates_by_instrument, new_name_map)

    # Create delivery records for each of the new files
    observatory = rmap.get_cached_mapping(pipeline).observatory
    for ctx in new_contexts:
        create_delivery_blob(observatory, ctx, rmap.locate_mapping(ctx), 
            request.user, request.user.email, "generated", description)
    
    # Track this since it generates two or more new official mappings.
    models.AuditBlob.create_record(
        request.user, "new context", new_contexts[0], description, 
        ", ".join(new_contexts[1:]), observatory=observatory, 
        instrument="", filekind="")

    return render(request, "create_contexts_results.html", {
                "new_contexts" : new_contexts,
            })

def is_pipeline_mapping(filename):
    """Verify that `filename` names a known CRDS pipeline mapping.
    Otherwise raise AssertionError.
    """
    assert re.match("\w+\.pmap", filename), "invalid pipeline mapping filename."
    try:
        rmap.get_cached_mapping(filename)
    except Exception:
        assert False, "can't load.   Must name a known CRDS pipeline mapping."
    return filename

def is_reference_mapping(filename):
    """Verify that `filename` names a known CRDS reference mapping.
    Otherwise raise AssertionError.
    """
    assert re.match("\w+\.rmap", filename), "invalid reference mapping filename."
    try:
        rmap.get_cached_mapping(filename)
    except Exception:
        assert False, "can't load.   Must name a known CRDS reference mapping."
    return filename

def is_list_of_rmaps(text):
    """Assert that `text` contains a list of comma for newline separated rmap
    names.
    """
    text = str(text)
    text = text.replace("\n"," ")
    text = text.replace("\r", "")
    text = " ".join(text.split(","))
    rmaps = [r.strip() for r in text.split()]
    for rmap in rmaps:
        is_reference_mapping(rmap)
    return rmaps

def generate_new_names(old_pipeline, updates):
    """Generate a map from old pipeline and instrument context names to the
    names for their replacements.
    """
    new_names = {}
    new_names[old_pipeline] = new_name(old_pipeline)
    for old_imap in updates:
        new_names[old_imap] = new_name(old_imap)
    return new_names

def new_name(old_map):
    """Given and old mapping name, `old_map`, adjust the serial number to 
    create a new mapping name of the same series.
    """
    observatory = rmap.get_cached_mapping(old_map).observatory
    instrument, filekind, serial = utils.get_file_properties(observatory, old_map)
    extension = os.path.splitext(old_map)[-1]
    newserial = get_new_serial(observatory, instrument, filekind, extension)
    if re.search(r"_\d+\.[pir]map", old_map):
        new_map = re.sub(r"_\d+(\.[pir]map)", r"_%04d\1" % newserial, old_map)
    elif re.match(r"\w+\.[pir]map", old_map):   # if no serial,  start off existing sequence as 0
        parts = os.path.splitext(old_map)
        new_map = parts[0] + "_%04d" % newserial + parts[1]
    else:
        raise ValueError("Unrecognized mapping filename " + repr(old_map))
    assert not os.path.exists(rmap.locate_mapping(new_map)), \
        "Program error.  New mapping already exists."
    return new_map

