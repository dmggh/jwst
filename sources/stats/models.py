import datetime
import pprint
import json

from django.db import models

from crds import timestamp, compat
from crds.server import config

MAX_RESPONSE_LEN = 100000
SKIP_PATHS = ('/admin',)

class SkipPathError(Exception):
    """Paths listed in SKIP_PATHS are not logged.   Instead this exception is raised."""
    
# Create your models here.

def double(xs):
    return zip(xs,xs)

def de_unicode(obj):
    if isinstance(obj, basestring):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return obj.__class__([de_unicode(x) for x in obj])
    elif isinstance(obj, dict):
        return dict({ de_unicode(x) : de_unicode(obj[x]) for x in obj })
    else:
        return str(obj)

def make_dict(name, obj):
    try:
        return de_unicode(obj)
    except:
        return "error capturing " + name
    

class LogModel(models.Model):
    """A generic model for logging stuff,  request, responses, and messages."""

    class Meta:
        db_table = config.table_prefix + "_log" # rename SQL table from interactive_fileblob
        
    date = models.DateTimeField(auto_now_add=True)
    event = models.CharField(max_length=32, 
                             choices=double(["request","response","log", "exception"]), 
                             default="log")
    blob = models.TextField()
    
    @property
    def liveblob(self):
        if not hasattr(self, "_liveblob"):
            self._liveblob = de_unicode(compat.literal_eval(self.blob))
        return self._liveblob
        
    @property
    def jsonpars(self):
        if not hasattr(self, "_jsonpars"):
            self._jsonpars = de_unicode(
                json.loads(self.liveblob["POST"].keys()[0]))
        return self._jsonpars

    @property
    def datestr(self):
        return "[" + timestamp.reformat_date(self.date)[:-4] + "]"
    
    def __unicode__(self):
        if self.event == "request":
            return self.__unicode__request()
        elif self.event == "response":
            return self.__unicode__response()
        elif self.event == "log":
            return self.__unicode__log()
        elif self.event == "exception":
            return self.__unicode__exception()
        else:
            return self.__unicode__prefix()

    @property
    def is_json(self):
        return self.liveblob["path"].startswith("/json")

    def __unicode__prefix(self):
        event = { "request":"REQ", "response":"RESP", }[self.event]
        s = self.datestr + " " + event.upper() + " " + \
            self.liveblob["HTTP_HOST"] + " (" + self.liveblob["REMOTE_ADDR"] + ")"
        if self.is_json:
             s += " JSON " + self.jsonpars["method"] 
        else:
            s += " " + self.liveblob["method"] + " " + self.liveblob["path"]
        return s
        
    def __unicode__request(self):
        s = self.__unicode__prefix()
        if self.is_json:
            s += " " + str(self.jsonpars["params"])
        else:
            if self.liveblob["method"] == "GET":
                s += " " + str(self.liveblob["GET"])
            else:
                s += " " + str(self.liveblob["POST"])
        return s
    
    def __unicode__response(self):
        return self.__unicode__prefix() + " " + str(self.liveblob["status_code"])

    def __unicode__exception(self):
        return self.__unicode__prefix() + " " + str(self.liveblob["exception_str"])

    def __unicode__log(self):
        return self.__unicode__prefix() + " " + str(self.liveblob["message"])

    def __repr__(self):
        return self.datestr + " " + self.event + "\n" + \
            pprint.pformat(compat.literal_eval(self.blob))

    @classmethod
    def log_string(cls, blob, event="log"):
        l = cls()
        l.event = event
        l.blob = blob
        l.save()

    @classmethod    
    def stdblob(cls, request, **keys):
        if request.path == "/" or request.path.startswith(SKIP_PATHS):
            raise SkipPathError(request.path)
        
        get = make_dict("GET", request.GET)
        post = make_dict("POST", request.POST)
        meta = make_dict("META", request.META)
        
        d = dict(
                # REMOTE_HOST = meta.get("REMOTE_HOST", "unknown"),
                REMOTE_ADDR = meta.get("REMOTE_ADDR", "unknown"),
                HTTP_HOST = meta.get("HTTP_HOST", "unknown"),
                HTTP_USER_AGENT = meta.get("HTTP_USER_AGENT", "unknown"),
                HTTP_REFERRER = meta.get("HTTP_REFERRER", "unknown"),
                user=str(request.user), 
                method=str(request.method),
                path=str(request.path),
                GET=get, 
                POST=post, 
                )
        d.update(**keys)
        return d
        
    @classmethod
    def log_request(cls, request):
        meta = make_dict("META", request.META)
        cookies = make_dict("COOKIES", request.COOKIES)
        files = [ (f.name, f.size) for f in request.FILES.values() ]
        d = cls.stdblob(
            request,
            # META=meta, 
            FILES=files,
            COOKIES=cookies,
            full_path=request.get_full_path(),
            ajax=request.is_ajax(),
            encoding=request.encoding,
            secure=request.is_secure(),
            authenticated=request.user.is_authenticated())
        cls.log_string(repr(d), event="request")

    @classmethod
    def log_response(cls, request, response):
        d = cls.stdblob(request,
                status_code = response.status_code,
                ajax=request.is_ajax(),
                encoding=request.encoding,
                )
        cls.log_string(repr(d), event="response")

    @classmethod
    def log_exception(cls, request, exception):
        d = cls.stdblob(request,
                exception_repr = repr(exception),
                exception_str = str(exception),
                )
        cls.log_string(repr(d), event="exception")

    @classmethod
    def log_message(cls, request, message):
        d = cls.stdblob(request)
        d.update(dict(
                message = message
                ))
        cls.log_string(repr(d), event="log")

    @classmethod
    def wipe(cls):
        for obj in cls.objects.all():
            obj.delete()
