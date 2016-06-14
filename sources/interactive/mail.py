
"""This module supports sending e-mails from the CRDS servers using the basic VM
SMTP/LMTP setup.  It is an unauthenticated send,  easy.
"""

import sys 
import smtplib

from email.mime.text import MIMEText

from crds import log
from crds.server import config as sconfig

# =============================================================================================

GENERIC_STARTED_BODY = """

Job {results_kind} for {username}.

Monitor at: {monitor_url}

Files:

{files}

{description}
"""

# =============================================================================================

GENERIC_RESULT_BODY = """

Job {results_kind} for {username}.

Results at: {repeatable_url}

Files:

{files}

{description}
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

def crds_notification(subject=None, from_address=None, to_addresses=None, body=None,
                      username="anonymous", user_email=None, files=("none",), results_kind=None, 
                      description="", extras={}, **keys):
    with log.error_on_exception("Failed sending results e-mail"):
        body = body or GENERIC_RESULT_BODY
        subject = subject or (results_kind + " for " + username)
        subject = "CRDS " + sconfig.observatory.upper() + " " + sconfig.server_usecase.upper() + " " + subject
        from_address = from_address or sconfig.CRDS_STATUS_FROM_ADDRESS
        to_addresses = to_addresses or sconfig.CRDS_STATUS_TO_ADDRESSES[:]
        if user_email is not None:
            to_addresses.append(user_email)
        if description:
            description =  "Description:\n\n" + description
        files = "\n".join(files)
        keys = dict(keys.items() + locals().items() + extras.items())
        mail(**keys)
