import crds.server.stats.models as smodels

class LogMiddleware(object):
    
    def process_request(self, request):
        smodels.LogModel.log_request(request)
        
