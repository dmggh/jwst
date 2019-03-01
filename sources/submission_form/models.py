from django.conf import settings
from django.db import models
from django.utils import timezone
from functools import partial

INSTR = ['ACS', 'COS', 'STIS', 'WFC3']
CHANGE = ['SEVERE', 'MODERATE', 'TRIVIAL']
TRINARY = ['N/A', 'Yes', 'No']  # Use models.NullBooleanField() instead of CharField?

class Submission(models.Model):
    created_date              = models.DateTimeField(default=timezone.now)
    published_date            = models.DateTimeField(blank=True, null=True)
    
    deliverer                 = models.CharField(max_length=100)
    other_email               = models.CharField(max_length=500, blank=True, null=True)  #EmailField(blank=True, null=True)
    #delivery_date             = models.DateTimeField()
    instrument                = models.CharField(max_length=20, choices=zip(INSTR, INSTR), default=INSTR[0])
    file_type                 = models.CharField(max_length=100)
    history_updated           = models.BooleanField()
    keywords_checked          = models.BooleanField()
    descrip_updated           = models.BooleanField()
    useafter_matches          = models.CharField(max_length=20, choices=zip(TRINARY, TRINARY), default=TRINARY[0])
    compliance_verified       = models.CharField(max_length=20, choices=zip(TRINARY, TRINARY), default=TRINARY[0])
    ingest_files              = models.TextField()
    etc_delivery              = models.CharField(max_length=20, choices=zip(TRINARY, TRINARY), default=TRINARY[0])
    jwst_etc                  = models.CharField(max_length=20, choices=zip(TRINARY, TRINARY), default=TRINARY[0])
    calpipe_version           = models.CharField(max_length=500)
    replacement_files         = models.BooleanField()
    old_reference_files       = models.TextField(blank=True, null=True)  # Clean and search CRDS database?
    replacing_badfiles        = models.CharField(max_length=20, choices=zip(TRINARY, TRINARY), default=TRINARY[0])
    was_jira_issue_filed      = models.BooleanField()
    jira_issue                = models.CharField(max_length=100, blank=True, null=True)  # Clean and search JIRA issues?
    change_level              = models.CharField(max_length=100, choices=zip(CHANGE, CHANGE), default=CHANGE[0])
    table_rows_changed        = models.TextField()
    modes_affected            = models.TextField()
    correctness_testing       = models.TextField()
    additional_considerations = models.TextField()
    #disk_files                = models.TextField()
    delivery_reason           = models.TextField()
    
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return '{} {}'.format(self.deliverer, self.instrument)
