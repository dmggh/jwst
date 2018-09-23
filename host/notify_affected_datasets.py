#! /usr/bin python
#-*-python-*-
import sys

from crds.core import heavy_client, log, pysh, timestamp

def context_updated(observatory):
    """Check the cache and server to see if the operational context
    has changed.
    """
    # cached context 
    old_info = heavy_client.load_server_info(observatory)            
    old_context = old_info["operational_context"]

    # sync now context
    connected, new_info = heavy_client.get_config_info(observatory)
    new_context = new_info["operational_context"]

    if not connected:
        log.warning("Server sync failed.  Last synced:", 
                    repr(new_info["last_synced"]), 
                    "No context update possible.")
        return False

    if new_context != old_context:
        log.info("Detected context update from", repr(old_context), 
                 "to", repr(new_context))
        return (old_context, new_context)
    else:
        log.info("No change from context", repr(old_context))
        return False

def compute_affected_datasets(observatory, old_context, new_context):
    date = timestamp.now().replace(" ", "T")
    pysh.out_err("python -m crds.bestrefs --old-context ${old_context} --new-context ${new_context} --diffs-only --datasets-since=auto --print-affected-details >affected.datasets.${date}", raise_on_error=True)
    

def main(observatory):
    # check for updated operational context and exit
    updated = context_updated(observatory)
    if updated:
        old_context, new_context = updated
        
