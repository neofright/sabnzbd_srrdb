# sabnzbd_srrdb
A simple Python post-processing script for SABnzbd to interact with [pyrescene](https://bitbucket.org/Gfy/pyrescene/src) and the SRRdb API.

## Features:

- Check if srr exists in release folder; if exists rename srr to SAB_FILENAME.

- If an srr file does not exist; search for the srr by name with SRRdb API and download.

- If no srr results by name are found, search for the srr by crc32.

- Abort the post processing script if the SRRdb API returns more than one result.

- Warn and exit if you are above your daily file quota from SRRdb.

- If no srr can be found, exit. Maybe this is not a scene release or maybe multi episode tv nzb etc....

- Use srr file to rename the release file to correct name - this is better deobfuscation than renaming the file to SAB_FILENAME + '.ext'

- Extract the contents of the srr file to provide missing nfo etc.

- Use rescene to verify (srr.py -q) if the scene file(s) matches the correct crc32 according to srr or sfv.


## TODO:
- Abort if literal " " detected anywhere in release name (against scene rules) as it is likely p2p.

- Add the ability to supply credentials for SRRdb

- Check if rescene is installed and alert the user to install manually or attempt to auto-install via pip.

  ```
  # dnf install -y python3-pip
  # apt-get install python3-setuptools
  # pip3 install pyrescene
  ```

## Examples:
### Movie
```
Directory name: Big.Buck.Bunny.2008.DTS.1080p.BluRay.x264-DARM
No srr file found from release, attempting to fetch from srrdb...
SRRdb release identified name, downloading srr...
Extracting contents of srr file...
Renaming abcd1234.mkv to darm-bigbuckbunny-1080p.mkv.
Attempting to verify darm-bigbuckbunny-1080p.mkv against Big.Buck.Bunny.2008.DTS.1080p.BluRay.x264-DARM.srr...
File OK: darm-bigbuckbunny-1080p.mkv.
```
### Music
```
Directory name: Arist_Name-Album_Name-CD-FLAC-0000-FOOBAR
No srr file found from release, attempting to fetch from srrdb...
SRRdb release identified name, downloading srr...
Extracting contents of srr file...
01-artist_name-track_name.flac OK
02-artist_name-track_name.flac OK
03-artist_name-track_name.flac OK
04-artist_name-track_name.flac OK
05-artist_name-track_name.flac OK
06-artist_name-track_name.flac OK
07-artist_name-track_name.flac OK
08-artist_name-track_name.flac OK
09-artist_name-track_name.flac OK
10-artist_name-track_name.flac OK
11-artist_name-track_name.flac OK
Everything OK
```
