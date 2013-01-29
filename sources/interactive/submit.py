"""This module defines the functions used to submit references and mappings to CRDS.  

Functions performed:

0. Authentication and multiple login prevention?
* Verify username and password against CRDS database.

1. Input sanity checking and security screening.
* Ensure no submitted file is a copy of an existing file.
* Ensure inputs aren't trojaned.

2. File certification, dependency existence and blacklist checking.
* Optional file comparisons to prior references.

3. Optional file renaming to official CRDS names.
* If not renamed,  ensure not existing.

4. Optional generation of supporting mappings, including limited updates to multiple rmaps.
* Warn if any submitted or generated file, other than the .pmap,  is not mentioned 
  in a difference as an addition or replacement.

5. Entry into the CRDS database,  audit trail.

6. Presentation of preliminary persistent results, including an emphatic summary 
of errors and/or warnings.
* possibly present results as text or HTML by virtue of template expanded.

7. Delivery confirmation or rejection.  audit trail,  accept/reject reason?
* accept comments about what were fatal problems or why warnings were ignored.

8. Final acceptance processing.   (potentially long running)
* Data transfer from ingest to storage directories.  Ownership transfer.
* Sha1sum generation for future verification of file integrity.
* File delivery for archive pickup.

9. Final rejection processing
* Possible recovery of official CRDS file serial numbers.
* Removal or sealing of database traces.

10. Removal of delivered files from ingest area.
11. Presentation of final result,  including an emphatic summary of errors and/or warnings.
"""
from crds import cmdline, log

class SubmitFilesScript(cmdline.Script):
    """Command line version of CRDS file submissions."""
    
    description = """Submit files to CRDS relative to the specified context.
    
    There are two broad scenarios which have several use cases.
    
    I.  Submit primitive files.   
    
        Other than basic certification,  CRDS will accept the files as is.
        CRDS does not attempt to interrelate these files.  The given context is
        used to locate existing files which correspond to the submitted files
        for differencing and certification,  particularly for references.
    
        a. Submit references, of any known instruments or types.

        b. Submit .rmap's, .imap's, or .pmap's,  in any relation
    
    II. Submit files and generate mappings.
    
        CRDS accepts related primitive files, but then automatically generates
        related higher level mapping files.
        
        a. Submit references for one instrument but possibly several types,  
                and generate .rmap's, .imap, and .pmap.
                
        b. Submit .rmap's,  generate .imap's and .pmap's. 
    """
    
    def add_args(self):
        self.add_argument("files", nargs="+", help="Paths of references and mappings to add to CRDS.""")
        self.add_argument("--derive-from-context", store_in="derive_from_context",
                          help=".pmap used for certification or basis for new mappings/.pmap")
        self.add_argument("--change-level", choices=["trivial","medium","severe"], store_in="change_level", default="severe",
                          help="Degree to which submitted files impact science results.")
        self.add_argument("--description", help="Free text description of file submission.")
        self.add_argument("--auto-rename", action="store_true", default=False,
                          help="If specified,  automatically rename files to CRDS-style versioned names.")
        self.add_argument("--compare-old-references", action="store_true", default=False,
                          help="If specified, check references against the files they replace in derive-from-context, where applicable.")
        self.add_argument("--generate-rules", action="store_true", default=False,
                          help="If specified, generate mappings as required to add the submitted files to the derived-from-context.")
        
    def main(self):
        submit_files(self.args.derive_from_context, self.args.files)
        
if __name__ == "__main__":
    NewContextScript()()
