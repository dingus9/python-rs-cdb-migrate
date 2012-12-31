python-rs-cdb-migrate
=====================

An end-user python script to migrate and/or resize CDB (DBaaS) instances.

Uses the Cloud Databases API to clone a new instance based off an existing instance. Allows for quick resizing. Copies all data in all databases.

    Usage: migrate_cdb.py -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size>]

    -r/--region=           sets the region, should be 'ord' or 'dfw'
    -u/--user=             Rackspace Cloud username of the customer who owns the instance
    -k/--apikey=           API key for this Rackspace Cloud username
    -i/--instanceid=       instance ID of the existing Cloud Database instance
    -n/--name=             OPTIONAL: name of new Cloud Database instance
                               default: use the name of the existing instance
    -f/--flavor=           OPTIONAL: flavor (RAM) of new instance
                               default: use the flavor of the existing instance
                               valid flavors are: 512 / 1024 / 2048 / 4096
    -d/--volume-size=      OPTIONAL: volume size (in gigabytes) of new instance
                               default: use the volume size of the existing instance
                               valid volume sizes range from 1 to 50
    -c/--create-template=  OPTIONAL: create a template file based on the users in your instance
                               You MUST edit the file to supply passwords for all of your existing
                               database users and then re-import the file using the -l option
    -l/--load-template=    OPTIONAL: import files from a template file.
                               Import a JSON file containing all of your usernames/passwords
    -v                     verbose output
    
PREREQUISITES:

    Python2.7+
    mysql-client (Ubuntu: apt-get install mysql-client | RedHat/CentOS: yum install mysql-client)
    pip (Most systems: easy_install pip | Ubuntu: apt-get install python-pip)
    python-requests (With pip installed: pip install -I requests==0.14.1)

The commands 'mysqldump' and 'mysql' must be in your $PATH.

INSTALLATION:

Install migrate_cdb.py onto a RS Cloud Server in the same region/datacenter of the databases you want to migrate.

    Read only:
        git clone https://github.com/tofarley/python-rs-cdb-migrate.git
    Read/write:
        git clone git@github.com:tofarley/python-rs-cdb-migrate.git

    $ cd python-rs-cdb-migrate
    $./migrate_cdb.py -r <region> -u <username> -k <api_key> -i <instance_id> [-n <instance_name> -f <flavor> -d <volume_size>]

LIMITATIONS:

This script must be run from a Cloud Server in the same datacenter (region) as the database instance you are cloning.

We STRONGLY SUGGEST using screen on your ssh session to your Rackspace cloud server when running this tool.  This will ensure that if you lose your connection while running the script, that it continues to run.  For a tutorial on screen please see:  http://www.howtoforge.com/linux_screen

KNOWN-BUGS:

None yet, but I'm sure they're out there.

USAGE TUTORIAL: COMING SOON

Using the -c <filename> option, you can create a users template file. You MUST edit this file and replace all
instances of "CHANGE_ME" with your database user password. Here is an example template:

    [
        {
            "databases": [
                {
                    "name": "sampledb"
                }
            ], 
            "name": "demouser", 
            "password": "CHANGE_ME"
        }
    ]

In the example above, you would replace "CHANGE_ME" with the password for your user 'demouser'.
IF YOU DO NOT MAKE THIS CHANGE, YOUR DATABASES WILL NOT BE COPIED, AND YOUR USERS WILL ALL HAVE GENERIC PASSWORDS!

LICENSE:

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
