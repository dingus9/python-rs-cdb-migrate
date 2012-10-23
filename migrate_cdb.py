import getopt, sys, json, requests, random, string, os, math, time, subprocess, getpass, copy
sys.path.append('./lib')
from cdb import *
from rsauth import *
	
def main():
	#TODO: Make this sound professional.
	opt_username = None
	opt_apikey = None
	opt_region = None
	opt_instance_id = None
	opt_flavor_id = None
	opt_volume_size = None
	opt_template_file = None
	opt_infile = None
	opt_instance_name = None
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
				opt_region = region.dfw
			elif a.lower() == "ord":
				opt_region = region.ord
			elif a.lower() == "lon":
				opt_region = region.lon
			else:
				print "Valid regions are ORD / DFW / LON"
				sys.exit(1)
		elif o in ("-u", "--user"):
			opt_username = a
		elif o in ("-k", "--apikey"):
			opt_apikey = a
		elif o in ("-i", "--instanceid"):
			opt_instance_id = a
		elif o in ("-n", "--name"):
			opt_instance_name = a
		elif o in ("-c", "--create-template"):
			opt_template_file = a
		elif o in ("-l", "--load-template"):
			opt_infile = a
		elif o in ("-f", "--flavor"):
			if a == "512":
				opt_flavor_id = "1"
			elif a == "1024":
				opt_flavor_id = "2"
			elif a == "2048":
				opt_flavor_id = "3"
			elif a == "4096":
				opt_flavor_id = "4"
			else:
				print "Valid flavors are: 512 / 1024 / 2048 / 4096"
				sys.exit(1)		   
		elif o in ("-d", "--volumesize"):
			sz = int(a)
			if sz < 1 or sz > 50:
				print "Volume size must be a whole number between 1 and 50."
				sys.exit(1)
			opt_volume_size = sz
		else:
			assert False, "unhandled option"

	# Check for mandatory command line options.
	if opt_region == None or opt_username == None or opt_apikey == None or opt_instance_id == None:
		usage()
		sys.exit(1)

	# Authenticate
	try:
		auth = RSAuth(opt_username, opt_apikey)
	except requests.exceptions.HTTPError, e:
		exit("Authentication error:", e)

	# Create an instance object from the user's existing cdb instance
	print "Gathering information and generating API calls."
	try:
		src_instance = cdb(opt_region, opt_instance_id, auth)
	except requests.exceptions.HTTPError, e:
		exit("Error retrieving statistics for your database instance: " + opt_instance_id, e)
	
	# We are going to write a template file and exit.
	if opt_template_file:
		try:
			print "Writing template file to disk as: " + opt_template_file
			write_template(opt_template_file, src_instance.users)
			sys.exit(0)
		except IOError, e:
			exit("Error writing to file.", e)

	# Read in template file. If we are not using a template file, users should be blank.
	if opt_infile:
		try:
			print "Using pre-generated template file to create users."
			src_instance.users = read_template(opt_infile)
			src_instance.passwords_set = True
		except IOError, e:
			exit("Error reading input file: " + opt_infile, e)

	# Set our variables.
	if opt_instance_name:
		src_instance.name = opt_instance_name
	if opt_flavor_id:
		src_instance.flavor_id = opt_flavor_id
	if opt_volume_size:
		src_instance.volume_size = opt_volume_size
		
	try:
		dst_instance = src_instance.create()
	except requests.exceptions.HTTPError, e:
		exit("Error creating new instance: " + opt_instance_id, e)
		
	try:	
		print "Please wait while your new instance is created. This can take a few minutes."
		for num in range(1, 20):
			print "".ljust(num, '.')
			time.sleep(30)
			status = src_instance.build_status(dst_instance['endpoint'])
			
			if status == "ACTIVE":
				print "Your database instance has been created.\nHostname: " + dst_instance['hostname']
				break
			elif status == "ERROR":
				print "Your database instance failed to build. Please try again and contact Rackspace Cloud Support to remove the failed build."
				sys.exit(1)
			if num == 19:
			   print "Timeout waiting for database to build. Please try again and contact Rackspace Cloud Support to remove the failed build."
			   sys.exit(1)
	except requests.exceptions.HTTPError, e:
		exit("Error creating new instance: " + opt_instance_id, e)
	
	dbs_completed = []
	for user in src_instance.users:
		for attempt in range(0,2):
			pw = getpass.getpass("Enter password for " + user['name'])
			# Check to see if the password is good...
			command = "mysql -h " + src_instance.hostname + " -u " + user['name'] + " -p" + pw + " " + "-e 'select 1 from dual;'" + " " + db['name']
			exit_code = subprocess.check_call(command, stderr=subprocess.STDOUT, shell=True)
			if exit_code != 0:
				print "Incorrect password for " + user['name']
				if attempt == 2:
					print "Three unsuccessful attempts. We'll try another user who might be able to copy this database."
			elif exit_code == 0:
				print "Preparing to copy any uncopided databases for this user..."
				src_instance.add_user(user['name'], pw, user['databases'])
				# How long does the API take to complete this? hrmm?
				time.sleep(5)
				for db in user['databases']:
					# Only copy a database if it hasn't been completed already.
					if db['name'] not in dbs_completed:
						print "Copying database " + db['name'] + ". This can take a while... Please be patient."
						command = "mysqldump --opt -h " + src_instance.hostname + " -u " + user['name'] + " -p" + pw + " " + db['name'] + " | mysql -u " + user['name'] + " -p" + pw + " -h " + dst_instance['hostname'] + " " + db['name']
						exit_code = subprocess.check_call(command, stderr=subprocess.STDOUT, shell=True)
						if exit_code == 0:
							dbs_completed.append(db['name'])
						elif exit_code != 0:
							print "Hrm. It looks like this db copy failed. You might have to copy this one manually."
	
	print "COMPLETE!"
	print "The following databases were copied successfully: " + ', '.join(dbs_completed)


	
def exit(msg="", e=""):
	print msg
	print e.message
	sys.exit(1)

def read_template(filename):
	f = open(filename, 'r')
	data = f.read()
	return json.loads(data)

def write_template(filename, users):
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
