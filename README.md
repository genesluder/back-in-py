# back-in-py

A backup script based on [Easy Automated Snapshot-Style Backups with Linux and Rsync](http://www.mikerubel.org/computers/rsync_snapshots/) by Mike Rubel

```
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
```


```
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
```