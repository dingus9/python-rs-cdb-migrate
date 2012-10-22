from cdb import *
from rsauth import *
import getopt, sys, json, requests, random, string, os, math, time, subprocess, getpass
	
	
def main():
	#TODO: Make this sound professional.
	var_username = None
	var_apikey = None
	var_region = None
	var_instanceid = None
	var_flavor = None
	var_volume_size = None
	var_template_file = None
	var_infile = None
	var_instance_name = None
	motd = """Yada yada. We're not responsible. Use at your own peril.
This script will create a new database instance and copy yo shiz over to that database.

If you wish to create your users from a template file, make sure that you correctly update the password for
ALL users in the template file to correspond to your existing database passwords, otherwise your database
might not copy.

Is that cool?"""

	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], "vr:u:k:i:n:f:d:c:l:", ["region=", "user=", "apikey=", "instanceid=", "name=", "flavor=", "volumesize=", "create-template=", "load-template="])
	except getopt.GetoptError, err:
		# print help information and exit:
		print str(err) # will print something like "option -a not recognized"
		usage()
		sys.exit(2)
	verbose = False
	for o, a in opts:
		if o == "-v":
			verbose = True
		elif o in ("-r", "--region"):
			if a.lower() == "dfw":
				var_region = region.dfw
			elif a.lower() == "ord":
				var_region = region.ord
			elif a.lower() == "lon":
				var_region = region.lon
			else:
				print "Valid regions are ORD / DFW / LON"
				sys.exit(1)
		elif o in ("-u", "--user"):
			var_username = a
		elif o in ("-k", "--apikey"):
			var_apikey = a
		elif o in ("-i", "--instanceid"):
			var_instanceid = a
		elif o in ("-n", "--name"):
			var_instance_name = a
		elif o in ("-c", "--create-template"):
			var_template_file = a
		elif o in ("-l", "--load-template"):
			var_infile = a
		elif o in ("-f", "--flavor"):
			if a == "512":
				var_flavor = "1"
			elif a == "1024":
				var_flavor = "2"
			elif a == "2048":
				var_flavor = "3"
			elif a == "4096":
				var_flavor = "4"
			else:
				print "Valid flavors are: 512 / 1024 / 2048 / 4096"
				sys.exit(1)		   
		elif o in ("-d", "--volumesize"):
			sz = int(a)
			if sz < 1 or sz > 50:
				print "Volume size must be a whole number between 1 and 50."
				sys.exit(1)
			var_volume_size = sz
		else:
			assert False, "unhandled option"

	# Check for mandatory command line options.
	if var_region == None or var_username == None or var_apikey == None or var_instanceid == None:
		usage()
		sys.exit(1)

	# Authenticate
	try:
		auth = RSAuth(var_username, var_apikey)
	except requests.exceptions.HTTPError, e:
		exit("Authentication error:", e)

	# Create an instance object from the user's existing cdb instance
	print "Gathering information and generating API calls."
	try:
		instance = cdb(var_region, var_instanceid, auth)
	except requests.exceptions.HTTPError, e:
		exit("Error retrieving statistics for your database instance: " + var_instanceid, e)
	
	# We are going to write a template file and exit.
	if var_template_file:
		try:
			print "Writing template file to disk as: " + var_template_file
			write_template(var_template_file, instance.users)
			sys.exit(0)
		except IOError, e:
			exit("Error writing to file.", e)

	# Read in template file. If we are not using a template file, users should be blank.
	if var_infile:
		try:
			print "Using pre-generated template file to create users."
			instance.users = read_template(var_infile)
			instance.passwords_set = True
		except IOError, e:
			exit("Error reading input file: " + var_infile, e)
	
	# Set some variables in our instance before we create it.
	if var_flavor:
		instance.flavor = "blah"
	if var_volume_size:
		instance.volume_size = var_volume_size
	if var_instance_name:
		instance.name = var_instance_name

	try:
		instance.create()
	except requests.exceptions.HTTPError, e:
		exit("Error creating new instance: " + var_instanceid, e)
		

	print "Please wait while your new instance is created. This can take a few minutes."
	for num in range(1, 20):
		print "".ljust(num, '.')
		time.sleep(30)
		if check_build_state(var_region, var_tenantid, new_instance['instanceid'], var_token):
			print "Your database instance has completed.\nHostname: " + new_instance['hostname']
			break
		if num == 19:
		   print "Timeout waiting for database to build. Contact Rackspace Cloud Support."
		   sys.exit(1)
	
	linebreak()
	if confirm(motd):

	
def exit(msg="", e=""):
	print msg
	print str(e)
	sys.exit(1)

def read_template(filename):
	f = open(filename, 'r')
	data = f.read()
	return json.loads(data)

def write_template(filename, users):
	for user in users:
		user['password'] = 'CHANGE_ME'
	f = open(filename, 'w')
	f.write(json.dumps(users, sort_keys=True, indent=4))
	f.close()

def usage():
	print ""
	print "Usage: " + os.path.basename(__file__) + " -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size> -c <outfile> -l <infile>]"
	print ""
	print "	 -r/--region=			sets the region, should be 'ord' or 'dfw'"
	print "	 -u/--user=				Rackspace Cloud username of the customer who owns the instance"
	print "	 -k/--apikey=			API key for this Rackspace Cloud username"
	print "	 -i/--instanceid=		instance ID of the existing Cloud Database instance"
	print "	 -n/--name=				OPTIONAL: name of new Cloud Database instance\n								default: use the name of the existing instance"
	print "	 -f/--flavor=			OPTIONAL: flavor (RAM) of new instance\n							 default: use the flavor of the existing instance\n								valid flavors are: 512 / 1024 / 2048 / 4096"
	print "	 -d/--volume-size=		OPTIONAL: volume size (in gigabytes) of new instance\n							   default: use the volume size of the existing instance\n							   valid volume sizes range from 1 to 50"
	print "	 -c/--create-template=	OPTIONAL: create a template file based on the users in your instance\n							   You MUST edit the file to supply passwords for all of your existing\n							 database users and then re-import the file using the -l option"
	print "	 -l/--load-template=	OPTIONAL: import files from a template file.\n							   Import a JSON template file containing all of your usernames/passwords"
	print "	 -v						verbose output" 

def linebreak():
	print ''.ljust(80, '-')
	
def confirm(prompt=None, resp=False):
	"""prompts for yes or no response from the user. Returns True for yes and
	False for no.

	'resp' should be set to the default value assumed by the caller when
	user simply types ENTER.

	>>> confirm(prompt='Create Directory?', resp=True)
	Create Directory? [y]|n: 
	True
	>>> confirm(prompt='Create Directory?', resp=False)
	Create Directory? [n]|y: 
	False
	>>> confirm(prompt='Create Directory?', resp=False)
	Create Directory? [n]|y: y
	True

	"""

	if prompt is None:
		prompt = 'Confirm'

	if resp:
		prompt = '%s [%s/%s]: ' % (prompt, 'Y', 'n')
	else:
		prompt = '%s [%s/%s]: ' % (prompt, 'y', 'N')

	while True:
		ans = raw_input(prompt)
		if not ans:
			return resp
		if ans not in ['y', 'Y', 'n', 'N']:
			print 'please enter y or n.'
			continue
		if ans == 'y' or ans == 'Y':
			return True
		if ans == 'n' or ans == 'N':
			return False


if __name__ == "__main__":
	main()