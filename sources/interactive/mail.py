"""This module supports sending e-mails from the CRDS servers using the basic VM
SMTP/LMTP setup.  It is an unauthenticated send,  easy.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import smtplib
import os.path

from email.mime.text import MIMEText

from crds.core import log
from .. import config as sconfig
from . import common

# =============================================================================================

MARK_BAD_BODY = """
Marked Files '{badflag}' by '{username}'.

{description}

Affected Files:
---------------
{affected_files}

"""

# =============================================================================================

SUBMISSION_FAILURE  = """ 
An unanticipated error occurred for this file submission.

Request Type:
-------------
{task}

{username_if_any}

Description:
------------
{description}

Exception Info:
---------------
{traceback}
"""

def submission_fail_email(task, description, user, exc_obj):
    """This e-mail is issued for unanticipated file submission errors which may or 
    may not be server failures.
    """
    with log.error_on_exception("Failed sending CRDS critical error e-mail"):
        
        body = SUBMISSION_FAILURE

        subject = "CRDS " + sconfig.observatory.upper() + " " + sconfig.server_usecase.upper()
        subject += f" FAILED for {task}"
    
        if user:
            user_email = user.email
            username = (user.first_name + " " + user.last_name).title()
            username_if_any = label_with_text("Acting User:", username)
        else:
            username_if_any = ""
    
        description = label_with_text("Description:", description)
            
        from_address = sconfig.CRDS_STATUS_FROM_ADDRESS
        to_addresses = sconfig.CRDS_STATUS_TO_ADDRESSES[:]
    
        if user_email is not None:
            to_addresses.append(user_email)
            
        traceback = common.get_traceback_str(exc_obj)
    
        mail(**locals())


# =============================================================================================

UPDATE_CONTEXT_BODY = """
Update Context by '{username}'.

Changed '{state}' context from '{old_default} to '{new_default}'.

{description}

"""

# =============================================================================================

GENERIC_STARTED_BODY = """
SUBMITTED '{results_kind}' by '{username}'.

Monitor at: 
-----------
{monitor_url}

{description}
{uploaded_files}
{added_files}
{deleted_files}
"""

# =============================================================================================

GENERIC_READY_BODY = """
{status} '{results_kind}' by '{username}'.

Review/Confirm at:
------------------
{repeatable_url}

{description}
{uploaded_files}
{added_files}
{deleted_files}
"""

# =============================================================================================

GENERIC_CONFIRMED_BODY = """
{disposition} '{results_kind}' by '{username}'.

Final Results:
--------------
{repeatable_url}

Confirm/Cancel Url:
-------------------
{prior_results_url}

{description}
{uploaded_files}
{added_files}
{deleted_files}
{generated_files}

"""

# =============================================================================================

def mail(from_address, to_addresses, subject, body, **keys):
    """Basic API for sending e-mails,  only tested with simple @-style email names."""
    body = body.format(**keys)
    while "\n\n\n" in body:
        body = body.replace("\n\n\n","\n\n")
    msg = MIMEText(body)

    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = "; ".join(to_addresses)
    
    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.LMTP()
    s.connect()
    s.sendmail(from_address, to_addresses, msg.as_string())
    s.quit()
    

# =============================================================================================

def crds_notification(subject=None, from_address=None, to_addresses=None, body=None, status="",
                      username="anonymous", user_email=None, files=("none",), results_kind=None, 
                      added_files=[], deleted_files=[], uploaded_files=[], generated_files=[],
                      description="", **keys):
    with log.error_on_exception("Failed sending CRDS notification e-mail"):

        subject = subject or (status + " " + results_kind + " by " + username)
        subject = "CRDS " + sconfig.observatory.upper() + " " + sconfig.server_usecase.upper() + " " + subject

        if "disposition" in keys:
            keys["disposition"] = keys["disposition"].upper()

        from_address = from_address or sconfig.CRDS_STATUS_FROM_ADDRESS
        to_addresses = to_addresses or sconfig.CRDS_STATUS_TO_ADDRESSES[:]

        if user_email is not None:
            to_addresses.append(user_email)

        description = label_with_text("Description:", description)
        
        keys = dict(list(keys.items()) + list(locals().items()))
        
        keys = optional_parameter(keys, "uploaded_files")
        keys = optional_parameter(keys, "added_files")
        keys = optional_parameter(keys, "deleted_files")
        keys = optional_parameter(keys, "generated_files")

        mail(**keys)


# =============================================================================================

def label_with_text(label, text):
    """If `text` is not empty,  return `label` underlined followed by `text`.  Otherwise empty string."""
    return label + "\n" + "-" * len(label) + "\n" + text + "\n"  if text else ""

def file_list(label, files):
    # log.info("file_list:", repr(label), "files:", files)
    # files could be: list of filenames, list of upload items, dict of upload items

    if isinstance(files, dict):
        files = list(files.items())

    files_str = ""
    for name  in sorted(files):
        if isinstance(name, tuple):
            old, new = name
            files_str += os.path.basename(old) + " --> " + os.path.basename(new) + "\n"
        else:
            files_str += os.path.basename(name) + "\n"

    return label_with_text(label, files_str)

def optional_parameter(keys, param):
    label = "\n" + " ".join([word.capitalize() for word in param.split("_")]) + ":"
    keys[param] = file_list(label, keys[param])
    return keys
