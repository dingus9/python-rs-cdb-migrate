#!/usr/bin/python
# Written by Tim Farley. Please direct all complaints to /dev/null

import getopt, sys, json, requests, random, string, os, math, time, subprocess, getpass 

var_hostname = None

class VolumeTooSmallException(Exception):
    pass

class BuildFailedException(Exception):
    pass

#TODO: Add some freaking objects for crying out loud. Stop passing so many parameters.

def main():
    # TODO: Rework the code so that var_hostname doesn't need to be global
    global var_hostname

    var_username = None
    var_apikey = None
    var_tenantid = None
    var_token = None
    var_region = None
    var_instanceid = None
    var_instance_name = None
    var_flavor = None
    var_volume_size = None

    #TODO: Make this sound professional.
    motd = """Yada yada. We're not responsible. Use at your own peril.
This script will create a new database instance and copy yo shiz over to that database.
Is that cool?"""

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "vr:u:k:i:n:f:d:", ["region=", "user=", "apikey=", "instanceid=", "name=", "flavor=", "volumesize="])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    output = None
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-r", "--region"):
            var_region = a
        elif o in ("-u", "--user"):
            var_username = a
        elif o in ("-k", "--apikey"):
            var_apikey = a
        elif o in ("-i", "--instanceid"):
            var_instanceid = a
        elif o in ("-n", "--name"):
            var_instance_name = a
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

    if var_region == None or var_username == None or var_apikey == None or var_instanceid == None:
        usage()
        sys.exit(1)

    try:
        var_token = auth(var_username, var_apikey)
        var_tenantid = var_token['tenantid']
        var_token = var_token['tokenid']
    except requests.exceptions.HTTPError, e:
        print "Authentication error: " + str(e)
        sys.exit(1)

    linebreak()
    if confirm(motd):
        linebreak()
        try:
            print "Gathering information and generating API calls."
            users = get_database_users(var_region, var_tenantid, var_instanceid, var_token)
            payload = generate_payload(var_region, var_tenantid, var_instanceid, var_token, users, name=var_instance_name, flavor=var_flavor, volume_size=var_volume_size)
            if verbose:
                linebreak()
                print str(payload)
                linebreak()
            new_instance = create_database_instance(var_region, var_tenantid, var_token, payload)
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
            print ""
            print "Now copying your data from your old mysql databases to your new instances..."
            print "Depending on how much data you have, this could take a while, so be patient!"
            dbs_completed = [] 
            for user in users: 
                tmp = []
                for db in user['databases']:
                    for key, value in db.iteritems():
                        if value not in dbs_completed:
                            tmp.append({ 'name': user['name'], 'password': user['password'], 'database': value })
                            dbs_completed.append(value)

            for entry in tmp:
                pw = getpass.getpass("Enter password for user " + entry['name'] + " on database " + entry['database'] + ": ")
                run_command = "mysqldump --opt -h " + var_hostname + " -u " + entry['name'] + " -p" + pw + " " + entry['database'] + " | mysql -u " + entry['name'] + " -p" + entry['password'] + " -h " + new_instance['hostname'] + " " + entry['database'] 
                print run_command 
                output = subprocess.check_output(run_command, stderr=subprocess.STDOUT, shell=True)
                print output

        except requests.exceptions.HTTPError, e:
            print "Error returned from Cloud Databases API: " + str(e)
            sys.exit(1)
        except VolumeTooSmallException, e:
            print str(e)
            sys.exit(1)
        except BuildFailedException, e:
            print str(e)
            sys.exit(1)

    else:
        print "Bye."
        sys.exit(0)

def usage():
    print ""
    print "Usage: " + os.path.basename(__file__) + " -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size>]"
    print ""
    print "  -r/--region=       sets the region, should be 'ord' or 'dfw'"
    print "  -u/--user=         Rackspace Cloud username of the customer who owns the instance"
    print "  -k/--apikey=       API key for this Rackspace Cloud username"
    print "  -i/--instanceid=   instance ID of the existing Cloud Database instance"
    print "  -n/--name=         OPTIONAL: name of new Cloud Database instance\n                        default: use the name of the existing instance"
    print "  -f/--flavor=       OPTIONAL: flavor (RAM) of new instance\n                        default: use the flavor of the existing instance\n                        valid flavors are: 512 / 1024 / 2048 / 4096"
    print "  -d/--volume-size=  OPTIONAL: volume size (in gigabytes) of new instance\n                        default: use the volume size of the existing instance\n                        valid volume sizes range from 1 to 50"
    print "  -v                 verbose output" 

def password_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def linebreak():
    print ''.ljust(80, '-')

def check_http_response_status(result, location=""):
    if result.status_code == 413:
        print "\nThis error usually implies that the API server does\nnot want to process our request right now\nPlease try again in a few minutes."
    if result.status_code != requests.codes.ok:
        print location
        result.raise_for_status()

def auth(username, apikey):
    url='https://identity.api.rackspacecloud.com/v2.0/tokens'
    auth_payload = {
        "auth": {
           "RAX-KSKEY:apiKeyCredentials": {  
              "username": username,  
              "apiKey": apikey
           }
        }
    }
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, data=json.dumps(auth_payload), headers=headers)
    # check r.status_code for 200 and raise an exception if !=
    check_http_response_status(r, "Exception raised in function: auth()")
    return { 'tokenid': r.json['access']['token']['id'], 'tenantid': r.json['access']['token']['tenant']['id'] }

def create_database_instance(region, tenant, token, payload):
    url = 'https://' + region + '.databases.api.rackspacecloud.com/v1.0/' + tenant + '/instances'
    headers = {'X-Auth-Token': token, 'Content-Type': 'application/json'}
    r = requests.post(url, payload, headers=headers)
    # check r.status_code for 200 and raise an exception if !=
    check_http_response_status(r, "Exception raised in function: create_database_instance()")
    return { 'hostname': r.json['instance']['hostname'], 'instanceid': r.json['instance']['id'] }

def check_build_state(region, tenant, instance, token):
    url = 'https://' + region + '.databases.api.rackspacecloud.com/v1.0/' + tenant + '/instances/' + instance
    headers = {'X-Auth-Token': token, 'Content-Type': 'application/json'}
    r = requests.get(url, headers=headers)
    check_http_response_status(r, "Exception raised in function: check_build_state()")
    if r.json['instance']['status'] == "ACTIVE":
        return True
    elif r.json['instance']['status'] == "ERROR":
        raise BuildFailedException("The database instance creation failed. Contact Rackspace Cloud Support.")
    return False

def get_database_users(region, tenant, instance, token):
    url = 'https://' + region + '.databases.api.rackspacecloud.com/v1.0/' + tenant + '/instances/' + instance + '/users'
    headers = {'X-Auth-Token': token, 'Content-Type': 'application/json'}
    r = requests.get(url, headers=headers)
    check_http_response_status(r, "Exception raised in function: get_database_users()")
    all_users = r.json['users']
    print "\n\nThe following usernames were found in your existing database instance.\nThey will be imported to your new instance with the following randomized passwords: (you can change these passwords from the control panel)\n"
    print "Username".ljust(10) + ''.ljust(10) + "Password".ljust(10) + ''.ljust(10) + "Databases for user"
    linebreak()
    for user in all_users:
        user['password'] = password_generator()
        tmp = []
        for db in user['databases']:
            for key, value in db.iteritems():
                tmp.append(value)
        print user['name'].ljust(10) + ''.ljust(10) + user['password'].ljust(10) + ''.ljust(10) + "".join(tmp)
    linebreak()
    return all_users

def get_instance_details(region, tenant, instance, token):
    global var_hostname
    url = 'https://' + region + '.databases.api.rackspacecloud.com/v1.0/' + tenant + '/instances/' + instance
    headers = {'X-Auth-Token': token, 'Content-Type': 'application/json'}
    r = requests.get(url, headers=headers)
    check_http_response_status(r, "get_instance_details()")
    #instance_details = { 'name': r.json['instance']['name'], 'hostname': r.json['instance']['hostname'], 'volume_size': r.json['instance']['volume']['size'], 'flavor': r.json['instance']['flavor']['id'], 'used': r.json['instance']['volume']['used'] }
    var_hostname = r.json['instance']['hostname']
    instance_details = { 'name': r.json['instance']['name'], 'hostname': r.json['instance']['hostname'], 'volume_size': r.json['instance']['volume']['size'], 'flavor': r.json['instance']['flavor']['id'] }
    return instance_details 

def get_databases(region, tenant, instance, token):
    url = 'https://' + region + '.databases.api.rackspacecloud.com/v1.0/' + tenant + '/instances/' + instance + '/databases'
    headers = {'X-Auth-Token': token, 'Content-Type': 'application/json'}
    r = requests.get(url, headers=headers)
    check_http_response_status(r, "Exception raised in function: get_databases()")
    return r.json['databases']

def generate_payload(region, tenant, instance, token, users, name=None, flavor=None, volume_size=None):
    instance_details = get_instance_details(region, tenant, instance, token)

    if volume_size == None:
       volume_size = instance_details['volume_size'] 
    if name == None:
       name = instance_details['name'] 
    if flavor == None:
       flavor = instance_details['flavor'] 

    #if math.ceil(float(instance_details['used'])) > volume_size:
    #   raise VolumeTooSmallException("The volume of the new instance is too small to contain your data. Use a larger volume.")

    payload = {
        "instance": {
            "databases": #[
            #    {
            #        "character_set": "utf8", 
            #        "collate": "utf8_general_ci", 
            #        "name": "sampledb"
            #    }, 
            #    {
            #        "name": "nextround"
            #    }
            get_databases(region, tenant, instance, token)
            #], 
            ,
            "flavorRef": "https://" + region + ".databases.api.rackspacecloud.com/v1.0/1234/flavors/" + flavor, 
            "name": name, 
            "users": #[
                #{
                #    "databases": [
                #        {
                #            "name": "sampledb"
                #        }
                #    ], 
                #    "name": "demouser", 
                #    "password": "demopassword"
                #}
            #],
            #get_database_users(region, tenant, instance, token)
            users
            ,
            "volume": {
                "size": volume_size 
            }
        }
    }
    return json.dumps(payload)

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

