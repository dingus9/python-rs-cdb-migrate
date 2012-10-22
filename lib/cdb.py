import requests, rsauth, json, math, sys
from dbs import *

class cdb:

	def __init__(self, region, instance_id, auth):
		self.endpoint = auth.get_endpoint(rsauth.service.clouddatabases, region) + '/instances/' + instance_id
		self.base_endpoint = auth.get_endpoint(rsauth.service.clouddatabases, region) + '/instances'

		for api_correction in range(0,5):
			r = requests.get(self.endpoint, headers=auth.headers)
			# The API does not always return 'used'. Let's try to get it!
			try:
				self.volume_used = r.json['instance']['volume']['used']
				# No exception? Sweet, let's move on...
				break
			except KeyError:
				# 'used' doesn't exist. Let's try again...
				continue
				
		self.status = r.json['instance']['status']
		self.updated = r.json['instance']['updated']
		self.name = r.json['instance']['name']
		self.created = r.json['instance']['created']
		self.hostname = r.json['instance']['hostname']
		self.volume_size = r.json['instance']['volume']['size']
		self.flavor_id = r.json['instance']['flavor']['id']
		self.headers = auth.headers
		self.passwords_set = False
		self.databases = self.__get_databases()
		self.users = self.__get_users()
		self.region = region
		
		# A JSON string suitable for creating a new instance based on this one.
		self.json = json.dumps({
		    "instance": {
		        "databases": 
					self.databases
		        , 
		        "flavorRef": "https://" + self.region.lower() + ".databases.api.rackspacecloud.com/v1.0/1234/flavors/" + self.flavor_id, 
		        "name": self.name, 
		        "users": 
					self.users if self.passwords_set else []
		        , 
		        "volume": {
		            "size": int(self.volume_size)
		        }
		    }
		}, sort_keys=True, indent=4)
	
	def create(self):
		"""Returns False if the volume is not large enough. Throws an exception if there is a problem with the API"""
		if math.ceil(float(self.volume_used)) > self.volume_size:
			return False
		r = requests.post(self.base_endpoint, data=self.json, headers=self.headers)
		return True
	
	def update_status(self):
		r = requests.get(self.endpoint, headers=self.headers)
		self.status = r.json['instance']['status']
		return self.status
		
	def __get_users(self):
		r = requests.get(self.endpoint + "/users", headers=self.headers)
		return r.json['users']
		
	def __get_databases(self):
		r = requests.get(self.endpoint + "/databases", headers=self.headers)
		return r.json['databases']
	
	def http_response(r):
		pass
		