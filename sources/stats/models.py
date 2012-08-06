import datetime
import pprint
import json

from django.db import models

from crds import timestamp, compat
from crds.server import config

# Create your models here.

def double(xs):
    return zip(xs,xs)

def make_dict(name, obj):
    try:
        return { key:value for (key,value) in obj.items() }
    except:
        return "error capturing " + name

class LogModel(models.Model):
    """A generic model for logging stuff,  request, responses, and messages."""

    class Meta:
        db_table = config.table_prefix + "_log" # rename SQL table from interactive_fileblob
        
    date = models.DateTimeField(auto_now_add=True)
    event = models.CharField(max_length=32, choices=double(["request","response","log"]), default="log")
    info = models.TextField()
    
    @property
    def liveinfo(self):
        if not hasattr(self, "_liveinfo"):
            self._liveinfo = compat.literal_eval(self.info)
        return self._liveinfo
        
    @property
    def jsonpars(self):
        if not hasattr(self, "_jsonpars"):
            self._jsonpars = json.loads(self.liveinfo["POST"].keys()[0])
        return self._jsonpars

    @property
    def datestr(self):
        return "[" + timestamp.reformat_date(self.date)[:-4] + "]"
    
    def __unicode__(self):
        if self.liveinfo["path"].startswith("/json"):
            s = self.datestr + " " + self.liveinfo["host"] + " JSON " + \
                self.jsonpars["method"] + " " + str(self.jsonpars["params"])
        else:
            s = self.datestr + " " + self.liveinfo["host"] + " " + self.liveinfo["method"] + \
                 " " + self.liveinfo["path"]
            if self.liveinfo["method"] == "GET":
                s += " " + str(self.liveinfo["GET"])
            else:
                s += " " + str(self.liveinfo["PUT"])
        return s
    
    def __repr__(self):
        return self.datestr + " " + self.event + "\n" + pprint.pformat(eval(self.info))

    @classmethod
    def log_string(cls, info, event="log"):
        l = cls()
        l.event = event
        l.info = info
        l.save()
        
    @classmethod
    def log_request(cls, request):
        meta = make_dict("META", request.META)
        get = make_dict("GET", request.GET)
        post = make_dict("POST", request.POST)
        cookies = make_dict("COOKIES", request.COOKIES)
        files = [ (f.name, f.size) for f in request.FILES ]
        d = dict(
                 # META=meta, 
                 GET=get, 
                 POST=post, 
                 FILES=files,
                 COOKIES=cookies,
                 method=request.method,
                 path=request.path,
                 full_path=request.get_full_path(),
                 ajax=request.is_ajax(),
                 user=str(request.user), 
                 encoding=request.encoding,
                 host=request.get_host(),
                 secure=request.is_secure(),
                 authenticated=request.user.is_authenticated())
        cls.log_string(repr(d), event="request")

    @classmethod
    def wipe(cls):
        for obj in cls.objects.all():
            obj.delete()
