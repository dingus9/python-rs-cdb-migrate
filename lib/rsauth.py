import requests, os, json


class RSAuth:
    """A reusable class for storing auth information. Constructor takes an optional argument auth_endpointurl"""

    def __init__(self, username, apikey, auth_endpointurl='https://identity.api.rackspacecloud.com/v2.0/tokens'):
        self.token = None
        self.expiration = None
        self.tenant_id = None
        self.headers = {'Content-Type': 'application/json'}
        self.authurl = auth_endpointurl
        self.service_catalog = None
        
        self.authenticate(username, apikey, auth_endpointurl)
        

    # authenticate() will be called for us when we create an object, but we want to make it callable on it's own
    def authenticate(self, username, apikey, auth_endpointurl='https://identity.api.rackspacecloud.com/v2.0/tokens'):
        auth_payload = {
            "auth": {
               "RAX-KSKEY:apiKeyCredentials": {  
                  "username": username,  
                  "apiKey": apikey
               }
            }
        }
        r = requests.post(auth_endpointurl, data=json.dumps(auth_payload), headers=self.headers)
        # raise an exception if we don't get a 200 response.
        self.check_http_response_status(r)
        self.token = r.json['access']['token']['id']
        self.expiration = r.json['access']['token']['expires']
        self.tenant_id = r.json['access']['token']['tenant']['id']
        # set our headers with the token!
        self.headers['X-Auth-Token'] = self.token
        self.service_catalog = r.json['access']['serviceCatalog']

    def get_token(self):
        return self.token
    
    def get_tenant_id(self):
        return self.tenant_id
    
    def get_endpoint(self, service, region):
        for item in self.service_catalog:
            if item['name'] == service:
                for endpoint in item['endpoints']:
                    if endpoint['region'] == region:
                        return endpoint['publicURL']
                        
    def check_http_response_status(self, result):
        if result.status_code == 413:
            print "\nThis error usually implies that the API server does\nnot want to process our request right now\nPlease try again in a few minutes."
        if result.status_code != requests.codes.ok:
            result.raise_for_status()

class service:
    """Helper class to store all the various proper names of the various services"""
    clouddatabases = "cloudDatabases"
    cloudservers = "cloudServers"
    cloudfilescdn = "cloudFilesCDN"
    clouddns = "cloudDNS"
    cloudfiles = "cloudFiles"
    cloudloadbalancers= "cloudLoadBalancers"
    cloudmonitoring = "cloudMonitoring"
    cloudserversopenstack = "cloudServersOpenStack"

class region:
    dfw = "DFW"
    ord = "ORD"
    lon = "LON"