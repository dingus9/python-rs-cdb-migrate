python-rs-cdb-migrate
=====================

An end-user python script to migrate and/or resize CDB (DBaaS) instances.

Uses the Cloud Databases API to clone a new instance based off an existing instance. Allows for quick resizing. Copies all data in all databases.

    Usage: migrate_cdb.py -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size>]

    -r/--region=       sets the region, should be 'ord' or 'dfw'
    -u/--user=         Rackspace Cloud username of the customer who owns the instance
    -k/--apikey=       API key for this Rackspace Cloud username
    -i/--instanceid=   instance ID of the existing Cloud Database instance
    -n/--name=         OPTIONAL: name of new Cloud Database instance
                        default: use the name of the existing instance
    -f/--flavor=       OPTIONAL: flavor (RAM) of new instance
                        default: use the flavor of the existing instance
                        valid flavors are: 512 / 1024 / 2048 / 4096
    -d/--volume-size=  OPTIONAL: volume size (in gigabytes) of new instance
                        default: use the volume size of the existing instance
                        valid volume sizes range from 1 to 50
    -v                 verbose output
      (-v- NOT YET IMPLEMENTED -v-)
    -c                 OPTIONAL: create a template file of the users on your instance
                        You can edit the file to supply passwords for all of
                        your users, and then re-import the file using the -p option
    -p                 OPTIONAL: import files from 
                        Import a JSON file containing all of your usernames/passwords
                        
PREREQUISITES:
    Python2.7+
    mysql-client (Ubuntu: apt-get install mysql-client | RedHat/CentOS: yum install mysql-client)
    pip (Most systems: easy_install pip | Ubuntu: apt-get install python-pip)
    python-requests (With pip installed: pip install requests)

The commands 'mysqldump' and 'mysql' must be in your $PATH.

INSTALLATION:
Install migrate_cdb.py onto a RS Cloud Server in the same region/datacenter of the databases you want to migrate.

    Read only:
        git clone https://github.rackspace.com/tim-farley/python-rs-cdb-migrate.git
    Read/write:
        git clone git@github.rackspace.com:tim-farley/python-rs-cdb-migrate.git

    $ cd python-rs-cdb-migrate
    $./migrate_cdb.py -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size>]

LIMITATIONS:
The CDB API does not allow users to change passwords once they are created. The current script generates a
random 8-character password for use in the new database. At this time, the script creates the users at the time
the instance is created, and thus the passwords are locked-in. In a later update, it should be changed so that the
database users are created after the instance has already been setup. This way we can use existing passwords.

Right now you must manually enter a password for each of your existing databases before the process can begin.
I need to implement a -p/--password-file= command line argument that will read in a JSON formatted file of all usernames/passwords,
and the databases they belong to.

KNOWN-BUGS:
None yet, but I'm sure they're out there.

LICENSE:
No idea. Not sure what Rackspace allows.