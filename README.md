# Filebase
### 2026-09-21

### Importing

python cli.py import /path/to/directory/on/computer

It will update the database linked to DATABASE_PATH_STR, and copy the files
to OUTGOING_PATH_STR

Manually copy files from outgoing to storage with 
cp -R /path/to/outgoing/ /path/to/storage
(trailing slash on source to copy contents into destination)

### Retrieving

python cli.py retrieve a1d28570-2cb0-4013-a317-d20f8e407185 /path/to/destination