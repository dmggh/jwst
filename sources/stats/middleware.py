
import crds.server.stats.models as smodels

class LogMiddleware(object):
    
    def process_request(self, request):
        try:
            smodels.LogModel.log_request(request)
        except smodels.SkipPathError:
            pass
        except Exception, exc:
            print "LogMiddleware process_request failed:", str(exc)

    def process_response(self, request, response):
        return response    # XXX TODO disabled
    
        try:
            smodels.LogModel.log_response(request, response)
        except smodels.SkipPathError:
            pass
        except Exception, exc:
            print "LogMiddleware process_response failed:", str(exc)
        return response

    def process_exception(self, request, exception):
        return None    # XXX TODO disabled
    
        try:
            smodels.LogModel.log_exception(request, exception)
        except smodels.SkipPathError:
            pass
        except Exception, exc:
            print "LogMiddleware process_exception failed:", str(exc)
            