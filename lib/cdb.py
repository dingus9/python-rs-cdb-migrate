import requests, rsauth, json, math, sys

class cdb:

	def __init__(self, region, instance_id, auth):
		self.endpoint = auth.get_endpoint(rsauth.service.clouddatabases, region) + '/instances/' + instance_id
		self.base_endpoint = auth.get_endpoint(rsauth.service.clouddatabases, region) + '/instances'
		self.region = region
		self.headers = auth.headers
		self.instance_id = instance_id
		self.auth = auth
		self.instance_id = instance_id
						
		for api_correction in range(0,5):
			r = requests.get(self.endpoint, headers=self.headers)
			r.raise_for_status()
			# The API does not always return 'used'. Let's try to get it!
			try:
				self.volume_used = r.json['instance']['volume']['used']
				# No exception? Sweet, let's move on...
				break
			except KeyError:
				# 'used' doesn't exist. Let's try again...
				continue
				
		#for item in r.json['instance']['links']:
		#	if item['rel'] == "self":
		#		self.endpoint = item['href']
		self.status = r.json['instance']['status']
		self.updated = r.json['instance']['updated']
		self.name = r.json['instance']['name']
		self.created = r.json['instance']['created']
		self.hostname = r.json['instance']['hostname']
		self.volume_size = r.json['instance']['volume']['size']
		self.flavor_id = r.json['instance']['flavor']['id']
		self.passwords_set = False
		self.databases = self.__get_databases()
		self.users = self.__get_users()

	
	def create(self):
		r = requests.post(self.base_endpoint, data=self.json(), headers=self.headers)
		r.raise_for_status()
		for item in r.json['instance']['links']:
			if item['rel'] == "self":
				endpoint = item['href']
		return { 'hostname': r.json['instance']['hostname'], 'endpoint': endpoint, 'id' : r.json['instance']['id'] }
	
	def build_status(self, endpoint):
		r = requests.get(endpoint, headers=self.headers)
		r.raise_for_status()
		return r.json['instance']['status']
	
	def add_user(self, username, password, databases, endpoint):
		payload = json.dumps({
		    "users": [ 
		        {
		            "databases":
				databases
		            , 
		            "name": username, 
		            "password": password
		        }
		    ]
		}, sort_keys=True, indent=4)
		r = requests.post(endpoint + "/users", data=payload, headers=self.headers)
		r.raise_for_status()
				
	def root_enabled(self):
		r = requests.get(self.endpoint + "/root", headers=self.headers)
		r.raise_for_status()
		if r.json['rootEnabled'] == "true":
			return True
		else:
			return False
		
	def __get_users(self):
		r = requests.get(self.endpoint + "/users", headers=self.headers)
		r.raise_for_status()
		all_users = r.json['users']
		for user in all_users:
			user['password'] = 'CHANGE_ME'
		return all_users
		
	def __get_databases(self):
		r = requests.get(self.endpoint + "/databases", headers=self.headers)
		r.raise_for_status()
		return r.json['databases']

	def json(self):
		# A JSON string suitable for creating a new instance based on this one.
		return json.dumps({
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

		
