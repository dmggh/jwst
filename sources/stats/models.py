import datetime
import pprint

from django.db import models

from crds import timestamp
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
    
    def __repr__(self):
        s = "[" + timestamp.reformat_date(self.date) + "] " + self.event + "_event" + "\n"
        s += pprint.pformat(eval(self.info))
        return s

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
                 # meta=meta, 
                 get=get, 
                 post=post, 
                 files=files,
                 cookies=cookies,
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
            
    @classmethod
    def dump_log(cls, kind="*", from_date=None, to_date=None):
        if from_date is None:
            from_date = cls.objects.all()[0].date
        if to_date is None:
            to_date = reversed(cls.objects.all()).next().date    
        from_date = timestamp.reformat_date(from_date)
        to_date = timestamp.reformat_date(to_date)
        if from_date <= to_date:
            logs = cls.objects.all()
            order = "forward"
        else:
            logs = reversed(cls.objects.all())
            order = "reverse"
        for entry in logs:
            edate = timestamp.reformat_date(entry.date)
            if kind != "*" and entry.event != kind:
                continue
            if order == "forward":
                if edate < from_date or edate > to_date:
                    continue
            else:
                if edate > from_date or edate < to_date:
                    continue
            print "="*80
            print repr(entry)
