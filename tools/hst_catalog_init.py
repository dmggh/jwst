from crds import log

from crds_server.interactive import models, database as db

"""
{u'archive_date': '1999-10-19 19:22:01',
 u'comment': 'test image for integrated software test\n',
 u'comparison_file_name': '(initial)',
 u'delivery_number': '10429',
 u'expansion_number': '0',
 u'file_name': 'j2o15065j_a2d.fits',
 u'general_availability_date': '1999-02-25 18:45:11.156666',
 u'opus_flag': 'y',
 u'opus_load_date': '1999-02-25 16:04:00',
 u'otfc_date': 'none',
 u'reference_file_type': 'a2d',
 u'reject_by_expansion_number': '0',
 u'reject_by_file_name': 'j4d1435hj_a2d.fits',
 u'reject_delivery_number': '10466',
 u'reject_flag': 'y',
 u'useafter_date': '1991-01-01 00:00:00'}
"""

class Initializer(object):
    def __init__(self):
        self.info = {}
        self.reffile_ops = db.get_reffile_ops()
        for instr in models.INSTRUMENTS:
            self.info.update(self.dump_instrument_files(instr))

    def dump_instrument_files(self, instr):
        log.info("Fetching reffile_ops info for", repr(instr))
        if instr == "nicmos": instr = "nic"
        return { o["file_name"]: o for o in self.reffile_ops.make_dicts(instr.lower() + "_file") }

    def init_reference(self, refname):
        log.info("Initializing", repr(refname))
        blob = models.FileBlob.load(refname)
        if refname.endswith(("d",)):
            refname = refname[:-1] + "d"
        with log.error_on_exception("Failed getting opus_load_date for", repr(refname)):
            blob.activation_date = self.info[refname]["opus_load_date"]
        repairs = failed = None
        with log.error_on_exception("Failed repairing", repr(blob.name)):
            defects = blob.get_defects()
            repairs, failed = blob.repair_defects(defects)
            for rep in list(repairs.values()) + list(failed.values()):
                log.info("Repair", repr(blob.name), rep)
        if not repairs:
            blob.save()

    def init_references(self):
        for file in models.FileBlob.objects.all():
            if file.type == "reference":
                self.init_reference(file.name)

def main():
    I = Initializer()
    I.init_references()

if __name__ == "__main__":
    main()

