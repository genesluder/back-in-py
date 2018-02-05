#!/usr/bin/env python

# ~~~~~~~~~~~~~~~~~
# back_in_py.py
# ~~~~~~~~~~~~~~~~~
# author(s): Gene Sluder (gene@gobiko.com)
# last modified: 05/14/13
#
# Based on "Easy Automated Snapshot-Style Backups with Linux and Rsync"
# by Mike Rubel
# http://www.mikerubel.org/computers/rsync_snapshots/
#

# Usage message
USAGE = '''
Usage: back_in_py [OPTION]... [MACHINE_FILE]\n
Back up machines defined in the settings file, MACHINE_FILE.\n
  -h, --help                display this message and exit\n
  -v, --verbose             be verbose (default)\n
  -q, --quiet               be quiet\n
  -t, --type=TYPE           specify frequency type of backup: [daily(default), hourly]\n
  -n, --dry-run             do a test run- dont actually back up anything (see man rsync)\n
  -m, --mount               backup drive should be mounted before process\n
  -d, --device=DEVICE_NAME  the device to be backed up to\n
  -r, --root=BACKUP_ROOT    the backup destination root\n
'''
#
#################################

####################################
# OPTIONS 
####################################
SHORTOPTS = "hvqt:nmd:r:"
LONGOPTS = (
    "help",
    "verbose",
    "quiet",
    "type=",
    "dry-run",
    "mount",
    "device=",
    "root=",
)
####################################

############################################
# OPTION Helpers (and default opts)
############################################
_dry_run=False

TYPE_CHOICES=('hourly', 'daily')
_type='daily'

VERBOSITY_LEVELS=('message', 'warning')
_verbosity=0

_mount=False
############################################

# Settings
#################################
# Locations
BACKUP_DEVICE='/dev/sdc1'
# Be sure to include trailing slash
BACKUP_ROOT='/Users/gene/BACK_IN_PY/'
# Executables
MOUNT='/bin/mount'
CP='/bin/cp'
TOUCH='/usr/bin/touch'
RSYNC='/usr/bin/rsync'

####################################################################
# Machine definitions:
# Which machines to be backed up and settings per machine are 
# defined as a JSON object in a settings file
####################################################################

'''
# Example Machine definition
{
    # Hostname
    "name": "flying-circus",
    # IP
    "IP"  : "192.168.0.23",
    # List of sources to be backed up HOURLY
    # (not necessarily EVERY hour, but multiple times a day- as defined in crontab)
    # Be sure to use the full path
    "hourly_sources": (
    #   "/home/monty",
        ""
    ),
    # List of sources to be backed up DAILY
    # Sources listed in hourly DO NOT need to be listed here, as hourly
    # sources are included automatically in daily backups
    # Be sure to use the full path
    "daily_sources" : (
    #   "/usr/local",
        ""
    ),
    # Files/Filetypes to exclude
    # Note that the full path isn't used here, but the path relative to 
    # the parent directories of the sources above
    "exclude" : (
    #   "monty/.local",
    #   "*.mp3",
        ""
    )
}
'''

import os, sys, shutil, logging, json

from getopt import getopt, GetoptError
from subprocess import Popen, PIPE

#############################################
# Set logging
#############################################
b = logging.getLogger("basic_logger")
b.setLevel(logging.DEBUG)
h = logging.StreamHandler()
f = logging.Formatter("%(levelname)s %(asctime)s %(funcName)s %(lineno)d %(message)s")
h.setFormatter(f)
b.addHandler(h)

log = logging.getLogger("basic_logger")
#############################################


##########################################################
# HELPER variables
##########################################################
DRIVE_MOUNT_STATES={'readonly':'ro', 'readwrite':'rw'}
_drive_mount_state=DRIVE_MOUNT_STATES['readonly']
##########################################################

###########################################
# HELPER functions
###########################################

def clean_exit(status=0, msg=""):
    """
    Exit this script cleanly
    
    """
    
    global _drive_mount_state
    
    # Make sure the backup drive is mounted readonly before exiting!
    if _drive_mount_state != DRIVE_MOUNT_STATES['readonly']:
        remount_backup_drive('readonly')
    if not msg:
        sys.exit(status)
    else:
        sys.exit(u"%s Exiting..." % msg)


def execute_command(args):
    """
    Execute a shell command
    
    """
    
    try:
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        # The stdout and stderr strings are passed to variables
        out, err = p.communicate()
    # Catch exceptions
    # TODO: Make this actually useful
    except Exception, e:
        out = "Exception: %s" % e
        err = "Exception: %s" % e
    # Return messages
    finally:
        return (out, err)


def remount_backup_drive(mount_as):
    """
    Remount the backup drive readonly/readwrite
    
    """
    
    global _mount, _drive_mount_state
    
    if _mount:
        log.debug("Remounting backup drive %s...")
        out, err = execute_command([MOUNT, '-o', 
            'remount,%s' % DRIVE_MOUNT_STATES[mount_as], 
                BACKUP_DEVICE, BACKUP_ROOT])
        if err:
            clean_exit("Could not remount %s %s!" % (BACKUP_DEVICE, mount_as))
        else:
            _drive_mount_state = DRIVE_MOUNT_STATES[mount_as]
            log.debug("Done. Drive is mounted %s." % mount_as)


def backup_path(machine):
    """
    Determine a machine's backup path
    
    """

    return os.path.join(BACKUP_ROOT, machine['name'])


def backup_instance_prefix(machine):
    """
    Determine a backup instance prefix
    ie. /root/backups/hostname/hourly
    
    """
    
    global _type
    
    return os.path.join(backup_path(machine), _type)
    

def get_sources(machine):
    """
    Build the source list for a machine
    
    """
    
    global _type
    
    # First make sure that the settings file has defined sources
    sources = []
    
    for i in range(0, len(machine['%s_sources' % _type])):
        if machine['IP'] in ('local', 'localhost', '127.0.0.1'):
            sources.append(machine['%s_sources' % _type][i])
        else:
            sources.append('%s:%s' % (machine['IP'], machine['%s_sources' % _type][i]))
    
    return sources


def shuffle_backups(machine):
    """
    Delete the oldest backup, make the second oldest the oldest, etc
    in preparation for making a new backup
    
    """
    
    # Create a directory for this machine in the backup directory
    # if there isn't one
    path = backup_path(machine)
    if not os.path.isdir(path):
        log.debug("Creating directory %s." % path) 
        os.mkdir(path)
    
    instance_prefix = backup_instance_prefix(machine)
    
    if os.path.isdir('%s.3' % instance_prefix):
        log.debug("Recursively removing directory %s.3" % instance_prefix) 
        shutil.rmtree('%s.3' % instance_prefix)
    
    if os.path.isdir('%s.2' % instance_prefix):
        log.debug("Renaming %s.2 to %s.3" % (instance_prefix, instance_prefix))
        os.rename('%s.2' % instance_prefix, '%s.3' % instance_prefix)

    if os.path.isdir('%s.1' % instance_prefix):
        log.debug("Renaming %s.1 to %s.2" % (instance_prefix, instance_prefix))
        os.rename('%s.1' % instance_prefix, '%s.2' % instance_prefix)

    # Make a hard-link-only (except for dirs) copy of the latest incremental,
    # if it exists
    if os.path.isdir('%s.0' % instance_prefix):
        log.debug("Hard-linking %s.0 to %s.1" % (instance_prefix, instance_prefix))
        execute_command([CP, '-al', '%s.0' % instance_prefix, 
            '%s.1' % instance_prefix])


def rsync_args(machine):
    """
    Takes a dictionary of machine backup definitions and returns an argument list 
    digestable by subprocess.Popen() for executing an rsync statement
    
    """
    
    global _type, _dry_run

    # First add executable name, default options
    if machine['IP'] in ('local', 'localhost', '127.0.0.1'):
        args = [RSYNC, '-avz', '--delete',]
    else:
        args = [RSYNC, '-avz', '-e', 'ssh', '--delete',]

    if _dry_run:
        args.append('--dry-run')

    for exclude in machine['exclude']:
        args.append('--exclude=%s' % exclude)

    for source in get_sources(machine):
        args.append(source)

    # Append the destination directory
    args.append('%s.0' % backup_instance_prefix(machine))
    
    # If this is a dry_run print the resulting argument list
    if _dry_run:
        print args
        
    return args


####################################################
# Meat and potatoes ################################
####################################################
def main(argv):
    
    global _dry_run, _type, _mount
    
    # Sort out passed opts
    try:
        opts, args = getopt(argv, SHORTOPTS, LONGOPTS)
    except GetoptError:
        print USAGE
        clean_exit(2)
    
    for opt, arg in opts:
        
        if opt in ("-h", "--help"):
            print USAGE
            clean_exit()
        
        elif opt in ("-t", "--type"):
            if arg in TYPE_CHOICES:
                _type = arg
            else:
                clean_exit("Bad argument for --type")
        
        elif opt in ("-n", "--dry-run"):
            _dry_run = True
        
        elif opt in ("-m", "--mount"):
            _mount = True
            
        elif opt in ("-d", "--device"):
            BACKUP_DEVICE = arg
        
        elif opt in ("-r", "--root"):
            BACKUP_ROOT = arg

	log.debug("Starting the backup process...")
	
	# Load the machine list
	filename = args[0]
	log.debug("Loading machine definition file: %s" % filename)
	machine_file = open(os.path.abspath(filename))
	machines = json.loads(machine_file.read())
	log.debug("Machines...%s" % machines)
	
	#---- Before backing up... ----#
	# Make sure we're running as root
    if os.getuid() != 0:
        clean_exit(msg="Not running as root!")
    
    # If requested, attempt to remount the backup drive as read/write
    if not _dry_run and _mount:
        remount_backup_drive('readwrite')
    
    #---- Begin backups -----------#
    # Loop through machines defined in the settings file 
    for machine in machines:
        log.debug("Backing up %s" % machine['name'])
        
        if not _dry_run:
            # Remove the oldest incremental backup and move each incremental 
            # back one spot (ie incremental #2 becomes #3, #1 becomes #2, etc)
            shuffle_backups(machine)
        
        # Now build an rsync statement based on the machine definition 
        # and attempt to execute it
        statement = rsync_args(machine)
        # Execute
        out, err = execute_command(statement)

        if err:
            # If err is not None, then initiating the backup has failed
            log.error("Backup of %s FAILED with ERROR: %s" % (machine['name'], err))
        else:
            # Otherwise initiating the backup has succeeded
            log.debug("Backup of %s INITIATED.\nrsync output follows..." % machine['name'])
            log.debug(out)

        # Update the mtime of hourly.0 with the current time
        log.debug("Updating mtime of newest incremental...") 
        out, err = execute_command([TOUCH, '%shourly.0' % backup_path(machine)])

        if not err:
            log.debug("Done.")
        else:
            log.error("mtime update failed!")

    # Done backing up- use clean_exit() to terminate
    # as it will remount the backup drive readonly
    clean_exit("\nFinished backing up!")

if __name__ == '__main__':
    main(sys.argv[1:])
