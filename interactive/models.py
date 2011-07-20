from django.db import models

# Create your models here.

from crds.compat import literal_eval

class DataBlob(models.Model):
    """A generic data format based which lets us transactionally store anything
    which has a repr() which can be literal_eval()'ed back to life.
    """
    kind  = models.CharField(
            max_length = 64,
            help_text = "string identifying the type of this blob")

    blob  = models.TextField( 
            help_text  = "repr() of dict with blob contents")
    
    def freeze(self, contents):
        self.blob = repr(contents)
        self.save()
    
    def thaw(self):
        return literal_eval(self.blob)