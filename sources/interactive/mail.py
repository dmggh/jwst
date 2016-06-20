"""This module supports sending e-mails from the CRDS servers using the basic VM
SMTP/LMTP setup.  It is an unauthenticated send,  easy.
"""

import sys 
import smtplib
import os.path

from email.mime.text import MIMEText

from crds import log
from crds.server import config as sconfig

# =============================================================================================

GENERIC_STARTED_BODY = """
SUBMITTED '{results_kind}' for '{username}'.

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
{status} '{results_kind}' for '{username}'.

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
{disposition} '{results_kind}' for '{username}'.

Final Results:
--------------
{repeatable_url}

{description}
{uploaded_files}
{added_files}
{deleted_files}
{generated_files}
"""

# =============================================================================================

def mail(from_address, to_addresses, subject, body, **keys):
    """Basic API for sending e-mails,  only tested with simple @-style email names."""
    msg = MIMEText(body.format(**keys))
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
        # with log.error_on_exception("Failed sending results e-mail"):

        subject = subject or (status + " " + results_kind + " for " + username)
        subject = "CRDS " + sconfig.observatory.upper() + " " + sconfig.server_usecase.upper() + " " + subject

        from_address = from_address or sconfig.CRDS_STATUS_FROM_ADDRESS
        to_addresses = to_addresses or sconfig.CRDS_STATUS_TO_ADDRESSES[:]

        if user_email is not None:
            to_addresses.append(user_email)

        description = label_with_text("Description:", description)
        
        keys = dict(keys.items() + locals().items())
        
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
    return label_with_text(label, "\n".join(sorted([os.path.basename(old) + " --> " + os.path.basename(new)
                                                    for (old, new) in dict(files).items()])))

def optional_parameter(keys, param):
    label = "\n" + " ".join([word.capitalize() for word in param.split("_")]) + ":"
    keys[param] = file_list(label, keys[param])
    return keys
