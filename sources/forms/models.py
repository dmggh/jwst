from django.db import models

# Create your models here.

def zip_choices(choices):
    return zip(*(choices, choices))


REQUESTER_CHOICES  = \
    [
    "ReDCaT",
    "MESA",
    "CRDS",
    "CAL",
    "Archive",
    "SDP",
    "Other"
    ]

RESOLUTION_CHOICES = \
    [
    "opened", 
    "assigned", 
    "completed", 
    "rejected",
    ]

AFFECTED_CRDS_SYSTEMS = "core, bestrefs, certify, diff, rules updates, miscellaneous tools, server database features, server reference submissions, server rules submissions, command line submissions, server bestrefs functions, server RPC functions, web formatting, documentation"

RELATED_EXTERNAL_SYSTEMS = "ReDCaT submission front end, CAL code, Archive Delivery, Pipeline Syncing, Pipeline repro fetch, CRDS services to Archive, Archive repro parameters for CRDS, Remote Users, Remote Institutions, Archive Databases"

class CrdsRequestModel(models.Model):

    def __str__(self):
        return "{}('{}', '{}')".format(self.__class__.__name__, self.id, self.title)

    title = models.CharField("Title", max_length=128, unique=True)

    date_needed = models.DateField("Date Needed")

    affected_projects = models.CharField("Affected Projects", max_length=64, default="", help_text="HST, JWST, ...")

    fte_estimate = models.FloatField("FTE Estimate (days)",  default=0.0)

    requester = models.CharField("Requester", choices=zip_choices(REQUESTER_CHOICES), max_length=64, blank=True, default="")

    resolution  = models.CharField("Resolution", choices=zip_choices(RESOLUTION_CHOICES), max_length=64, default="opened")

    description_of_functionality = models.TextField("Description of Functionality")

    benefit = models.TextField("Benefit")

    cost_of_not_implementing = models.TextField("Cost of not Implementing")

    alternative_methods_of_achieving = models.TextField("Alternative Methods")

    additional_notes = models.TextField("Additional Notes")

    required_support = models.TextField("Required Support", help_text= "specs, VMs, storage, proxies, reviews, ...", blank=True, default="")

    affected_crds_systems = models.TextField("Affected CRDS Systems", help_text=AFFECTED_CRDS_SYSTEMS, blank=True, default="")

    related_external_systems = models.TextField("Related External Systems",  help_text=RELATED_EXTERNAL_SYSTEMS, blank=True, default="")

    implementing_groups = models.TextField("Implementing Groups", help_text="CRDS,  ReDCaT,  SDP,  Archive, CAL, ...", blank=True, default="")

