# sabnzbd_srrdb
A simple Python post-processing script for SABnzbd to interact with [pyrescene](https://github.com/srrDB/pyrescene) and the [SRRdb](https://www.srrdb.com/) API.

## Features:

- Use an srr file to rename the release file to the correct filename - this is better deobfuscation than renaming the file to `SAB_FILENAME` + '.ext'

- Extract the contents of the srr file to provide missing nfo, m3u, sfv and jpg files.

- Use rescene to verify (srr.py -q) if the scene file(s) matches the correct crc32 according to srr or sfv.

- Delete video samples e.g. `group-movie-1080p-sample.mkv`



## Installation:
If you are using bare-metal or non containerised OS you can install pyrescene via pip. I have also included a requirements.txt

Fedora
  ```
  # dnf install -y python3-pip
  ```
Debian based
  ```
  # apt-get install python3-setuptools
  ```
Finally 
  ```
  # pip3 install pyrescene
  OR
  # pip3 install -r requirements.txt
  ```
Alternatively, download [pyReScene-0.7.tar.gz](https://pypi.org/project/pyReScene/#files) and place the "pyReScene-0.7/rescene" and "pyReScene-0.7/resample" directories next to this script.

## Examples:
### Movie
```
Directory name: Big.Buck.Bunny.2008.DTS.1080p.BluRay.x264-DARM
No srr file found from release, attempting to fetch from srrdb...
SRRdb release identified by name, downloading srr...
darm-bigbuckbunny-1080p.nfo: extracted!
darm-bigbuckbunny-1080p.sfv: extracted!
Renaming abcd1234.mkv to darm-bigbuckbunny-1080p.mkv.
File OK: darm-bigbuckbunny-1080p.mkv.
```
### Music (FLAC or MP3)
```
Directory name: Arist_Name-Album_Name-CD-FLAC-0000-FOOBAR
No srr file found from release, attempting to fetch from srrdb...
SRRdb release identified by name, downloading srr...
Extracting contents of srr file...
00-artist_name-album_name-cd-flac-0000.nfo: extracted!
00-artist_name-album_name-cd-flac-0000-proof.jpg: extracted!
00-artist_name-album_name-cd-flac-0000.m3u: extracted!
00-artist_name-album_name-cd-flac-0000.sfv: extracted!
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
### Game/Software (iso)
```
Directory name: Name_Of_A_Game-Group
No srr file found from release, attempting to fetch from srrdb...
SRRdb release identified by name, downloading srr...
grp-game.nfo: extracted!
grp-game.sfv: extracted!
File OK: grp-game.iso.
```
## How do I know if a release is 'scene' when searching?!
If your indexer supports it you can filter non predb releases on their website, or thanks to [this feature](https://github.com/theotherp/nzbhydra2/issues/647) in [nzbhydra2](https://github.com/theotherp/nzbhydra2) you can return only scene releases. Otherwise, use [a public predb website](https://en.wikipedia.org/wiki/Nuke_(warez)#List_of_public_predb_websites) or more obviously [SRRdb](https://www.srrdb.com/) itself.

## How can I use this script outside of SABnzbd?
```
cd /path/to/a/release
export SAB_COMPLETE_DIR="$PWD"; export SAB_FINAL_NAME="$(basename "$PWD")"
/path/to/location/of/SABnzbd_SRRdb.py
```
## How can I configure the script's behavior?
For now, and until someone suggests a better way, find the main function and edit the following:

- `remove_valid_srr` (`False`) Deletes the srr file after succesfully verifying the release.

- `remove_samples` (`True`) Attempts to identify and remove video samples.

  - `remove_srs` (`True`) The extracted srs file used to identify the sample file is also removed.

- `archive_nzb` (`True`) Store a copy of the NZB file in the release directory. E.g. if disk space is limited, you can delete the media and keep the nzb to re-download it again in the future.

## This script killed my cat!!!
__This program comes with ABSOLUTELY NO WARRANTY.__
