#!/usr/bin/env python

import glob as pyglob ## pyrescene's glob causes conflicts if we don't rename
import json
import os
import posixpath
#import pprint
import requests

os.environ["RESCENE_NO_SPINNER"] = str(True)
import rescene
from rescene.srr import *
from rescene.utility import calculate_crc32, parse_sfv_file

from urllib.parse import urlsplit
import sys

def search_srrdb_api(search_query, search_type, result_type='srr'):
    '''
        Search query. Type "archive" will search via CRC or "query" for a normal search string.
        Search response. Type "srr" to return the srr download URL. If undefined, defaults to a release name.
    '''
    url_base = 'https://www.srrdb.com/api/search/'
    if search_type == 'archive':
        url_query = r'archive-crc:' + search_query
    else:
        url_query = search_query
    
    json_url = posixpath.join(url_base, url_query)
    r = requests.get(json_url)
    response = r.text

    json_response = json.loads(response)
    
    ## uncoment to view the json response from SRRdb for testing
    #pprint.pprint(json_response)

    if int(json_response['resultsCount']) > 1:
        print("More than one release returned from SRRdb. Please verify manually")
        sys.exit(0)
    
    response = None
    for item in json_response["results"]:
        if "release" in item:
            if result_type == "srr":
                response = posixpath.join("https://www.srrdb.com/download/srr/", item["release"])
            else:
                response = item["release"]
    return response
    
def download_release_srr(srr_url):
    """
        - Take as an argument the download url of the srr file,
        - Save the url to the basename of the URL with srr extension
    """
    file_name = os.path.basename(urlsplit(srr_url).path) + ".srr"
    file_path = os.path.join(release_dir, file_name)
    
    srr_file = requests.get(srr_url)
    if srr_file.status_code != 200:
        print("Warning: HTTP " + str(srr_file.status_code) + " : " + srr_file.text)
        sys.exit(0)
    else:
        with open(file_path, 'wb') as srr_file_path:
            srr_file_path.write(srr_file.content)
    
def search_for_and_download_srr(search_query, media_file):
    """
        calls method search_srrdb_api() and attempts to find an srr by searching the directory name
        if no results are found by the directory name, we calculate the crc32 of the mkv and search on that
    """
    srr_download_url = search_srrdb_api(search_query, 'query')
    if srr_download_url != None:
        print("SRRdb release identified by name, downloading srr...")
        download_release_srr(srr_download_url)
        return True
    else:
        print("No srrDB release identified by name. Attempting to find release by crc32 hash...")
        crc32_hash = "%0.8X" % rescene.utility.calculate_crc32(media_file)
        srr_download_url = search_srrdb_api(crc32_hash,'archive')
        if srr_download_url != None:
            print("Release identified by crc32 hash, downloading srr...")
            download_release_srr(srr_download_url)
            return True
        else:
            print("Unknown scene release, possibly P2P or no srr available.")
            sys.exit(0)
    
def get_srr_file(release_dir, media_file):
    srr_files = pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.srr'))
    if len(srr_files):
        for srr_file in srr_files:
            ## Some srr files contain another nested srr for the subs of the movie as the main archived file.
            if 'subs' not in srr_file:
                print("Found: %s" % os.path.basename(srr_file))
                if os.path.basename(srr_file).lower() != release_basename.lower() + ".srr":
                    print("Renaming %s to %s." % (os.path.basename(srr_file), release_basename + ".srr"))
                    os.rename(srr_file, os.path.join(release_dir, release_basename + ".srr"))
                    return os.path.join(release_dir, release_basename + ".srr")
                else:
                    return os.path.join(release_dir, os.path.basename(srr_file))
    else:
        print("No srr file found from release, attempting to fetch from srrdb...")
        if search_for_and_download_srr(release_basename, media_file):
            return pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.srr'))[0]
            
def deobfuscate_scene_file(srr_file, media_file):
    archived_files = rescene.info(srr_file)["archived_files"].values()
    if len(archived_files) > 0:
        ext_filename = None
        for afile in archived_files:
            ext_filename = afile.file_name
        
        if ext_filename != None:
            media_basename = os.path.basename(media_file)            
            if os.path.splitext(media_basename)[1].lower() == os.path.splitext(ext_filename)[1].lower():
                ## Compare the returned archived file name with our media file
                if media_basename != ext_filename:
                    print("Renaming %s to %s." % (media_basename, ext_filename) )
                    os.rename(media_file, os.path.join(release_dir, ext_filename))

def verify_scene_rls(srr_file, release_dir):
    archived_files = rescene.info(srr_file)["archived_files"].values()
    if len(archived_files) > 0:
        return rescene.srr.verify_extracted_files(srr_file, release_dir, False)
    else:
        sfv_files = pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.sfv'))
        if len(sfv_files):
            sfv_file = sfv_files[0]
            crc_fail = 0
            for sfv_entry in parse_sfv_file(sfv_file)[0]:
                audio_file = str(sfv_entry).split()[0]
                audio_crc = str(sfv_entry).split()[1]
                
                ## Some SFV files have incorrect case and were generated on Windows/non *NIX os...
                ## The proper solution would be something like a find -iname on the track name.
                audio_file_full_path = os.path.join(release_dir, audio_file)
                if not os.path.isfile(audio_file_full_path):
                    audio_file_full_path = os.path.join(release_dir, audio_file.lower())
                
                crc32_hash = "%0.8X" % rescene.utility.calculate_crc32(audio_file_full_path)
                if audio_crc.lower() == crc32_hash.lower():
                    print(audio_file + " OK")
                else:
                    crc_fail += 1
                    print(audio_file + " ERR")
            if crc_fail == 0:
                print("Everything OK")
                return 0
            else:
                print("Album SFV check Failed!")
                return 1

def return_largest_file(release_dir):
    ## https://www.daniweb.com/programming/software-development/threads/234497/find-largest-file-in-directory#post1033536
    largest = sorted( (os.path.getsize(s), s) for s in pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.*')) )[-1][1]
    return largest

if __name__ == "__main__":
    ## Change this to True to delete srr files after successful file verification
    ## https://github.com/neofright/sabnzbd_srrdb/issues/6
    remove_valid_srr = False

    release_dir = os.environ['SAB_COMPLETE_DIR'] ## for nzbget use os.environ['NZBPP_DIRECTORY']
    release_basename = os.environ['SAB_FINAL_NAME'] ## for nzbget use os.environ['NZBPP_NZBNAME']

    ## Abort post processing for releases with whitespace in their name
    if len(release_basename.split()) > 1:
        print("Literal space in release name (P2P?). Skipping.")
        sys.exit(0)

    ## Abort post processing for season pack releases
    pattern = '\.S[0-9]*\.'
    if re.search(pattern, release_basename, re.IGNORECASE):
        print("Season pack detected. Script will not run.")
        sys.exit(0)

    print("Directory name: %s" % release_basename)
    media_file = return_largest_file(release_dir)
    ## Search for existing srr file and attempt to fetch if missing (function hopefully returns the full path)...
    srr_file = get_srr_file(release_dir, media_file)
                
    ## If an srr file has been found...
    if srr_file:
        ####################################################################
        out_folder = os.path.normpath(release_dir)
        ## Extract only the file types from srr in the regex below:
        to_extract = re.compile('^.*\.(nfo|m3u|jpg|sfv)$', re.IGNORECASE)
        def decide_extraction(stored_fn):
            return to_extract.match(stored_fn)
        ####################################################################
        files = rescene.extract_files(os.path.normpath(srr_file), out_folder, False, matcher=decide_extraction)

        # show which files are extracted + success or not
        for efile, success in files:
            file_name = efile[len(out_folder) + 1:]
            if success:
                print("{0}: extracted.".format(file_name))
            else:
                print("{0}: not extracted!".format(file_name))

        if not len(files):
            print("No matching files to extract.")
        ####################################################################
        ## Rename the (video) file if it differs from the srr record (obfuscated).
        deobfuscate_scene_file(srr_file, media_file)
        ####################################################################
        ## Attempt to verify the crc32 of the (video) file and store the exit code.        
        verification_exit_code = verify_scene_rls(srr_file, release_dir)

        ## if verification was successful, check if we want to do cleanup.
        if verification_exit_code == 0:
            if remove_valid_srr:
                os.remove(srr_file)
        
        ## Exit this script with the stored exit code of the verification process.
        sys.exit(verification_exit_code)
        ####################################################################
