"""This module supports sending e-mails from the CRDS servers using the basic VM
SMTP/LMTP setup.  It is an unauthenticated send,  easy.
"""

import sys 
import smtplib

from email.mime.text import MIMEText

def mail(from_addr, to_addrs, subject, body, **keys):
    """Basic API for sending e-mails,  only tested with simple @-style email names."""
    msg = MIMEText(body.format(**keys))
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = "; ".join(to_addrs)
    
    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.LMTP()
    s.connect()
    s.sendmail(from_addr, to_addrs, msg.as_string())
    s.quit()
    
