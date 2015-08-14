from crds.server.jwst import restful
from crds.server import config
from crds import log

BASE_URL = "http://jwdmsdevvm4:8888/crds"

# ================================================================================================== 

class SimpleIntArchiveService(restful.GetService):
   
    base_url = BASE_URL

    def format_result(self, result):
        varname = self.service_name[0].capitalize() + self.service_name[1:]
        return int(result[varname])

max_header_block_size = SimpleIntArchiveService("maxHeaderBlockSize")

datasets_count = SimpleIntArchiveService("datasetsCount")

# ================================================================================================== 

class BatchStringListService(restful.GetService):

    base_url = BASE_URL

    def format_result(self, result):
        return [str(name) for name in list(result)]

datasets = BatchStringListService("datasets")

# ================================================================================================== 

def get_dataset_ids(instrument, datasets_since=None):
    if datasets_since:
        datasets_since = datasets_since.replace(" ","T").split(".")[0]
    expected_count = datasets_count(instrument=instrument, minDate=datasets_since)
    total_ids = []
    result = ["throwaway starter result"]
    batch = 0
    while len(total_ids) < expected_count and result:
        result = datasets(instrument=instrument, minDate=datasets_since, batchNum=batch)
        batch += 1
        total_ids += result
        log.verbose("get_dataset_ids:", len(result), "/", len(total_ids), "/", expected_count)
    return total_ids

# ================================================================================================== 

class ArchivePostService(restful.PostService):
    base_url = BASE_URL

headers = ArchivePostService("headers")

# ================================================================================================== 

def get_header_block(dataset_ids, matching_parameters):
    return headers(CRDSHeaderQueryInput=dict(
            datasetIds=dataset_ids, parameters=matching_parameters))

def get_dataset_headers_by_id(dataset_ids, matching_parameters):
    max_headers = max_header_block_size()
    total_headers = {}
    for i in range(0, len(dataset_ids), max_headers):
        results = get_header_block(
            dataset_ids[i:min(i+max_headers, len(dataset_ids))], matching_parameters)
        total_headers.update(results)
    for did in dataset_ids:
        if did not in total_headers:
            total_headers[did] = "UNDEFINED"
    return total_headers

