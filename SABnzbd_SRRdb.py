#!/usr/bin/env python

import contextlib
import glob as pyglob ## pyrescene's glob causes conflicts if we don't rename
import io
import json
import os
import posixpath
import requests
import shutil

os.environ["RESCENE_NO_SPINNER"] = str(True)
import rescene
from rescene.srr import *
from rescene.utility import calculate_crc32, parse_sfv_file
import resample

from urllib.parse import urlsplit
import sys

def search_srrdb_api(search_query, search_type, result_type='srr'):
    '''
        search_type. "archive" searches via CRC instead of a search string.
        result_type. "srr" returns the srr download URL. Otherwise returns found release name.
    '''
    if '.XXX.' not in search_query:
        url = 'https://www.srrdb.com'
    else:
        url = 'https://www.srrxxx.com'
    url_base = url + '/api/search/'

    if search_type == 'archive':
        url_query = r'archive-crc:' + search_query
    else:
        url_query = search_query

    json_url = posixpath.join(url_base, url_query)
    r = requests.get(json_url)
    response = r.text

    json_response = json.loads(response)

    if int(json_response['resultsCount']) > 1:
        print("More than one release returned from SRRdb. Please verify manually")
        sys.exit(0)

    response = None
    for item in json_response["results"]:
        if "release" in item:
            if result_type == "srr":
                response = posixpath.join( url + '/download/srr/', item["release"])
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
        if no results are found by the directory name, we calculate the crc32 of the largest file and search on that
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
        ## Pretty safe assumption, mostly follows rescene logic.
        ## Globals are looked down upon, but I'm going for it!
        global release_is_music
        release_is_music = True

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
                
                if os.path.isfile(audio_file_full_path):
                    crc32_hash = "%0.8X" % rescene.utility.calculate_crc32(audio_file_full_path)
                    if audio_crc.lower() == crc32_hash.lower():
                        print(audio_file + " OK")
                    else:
                        crc_fail += 1
                        print(audio_file + " ERR")
                else:
                        crc_fail += 1
                        print(audio_file + " MISSING")
            if crc_fail == 0:
                print("Everything OK")
                return 0
            else:
                print("Album SFV check failed!")
                return 1

def return_largest_file(release_dir):
    ## https://www.daniweb.com/programming/software-development/threads/234497/find-largest-file-in-directory#post1033536
    file_list = sorted( (os.path.getsize(s), s) for s in pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.*')) if os.path.isfile(s) )
    if len(file_list) > 0:
        return file_list[-1][1]
    else:
        print(f"No files found in directory root. Exiting!")
        sys.exit(0)

"""
    - Extract the '*sample.srs' file from the srr file (if one exists).
        - List the sample filename from the srs file.
        - Search for the sample file and remove it.
        - Remove the srs file from disk (configurable).
    - Note that I supply 'extract_paths=False' to 'extract_files'
      which makes "./Sample/foo.srs" "./foo.srs"
    - If SABnzbd is set to "Ignore any folders inside archives"
      Then your sample file will be "./group-movie-1080p-sample.ext" instead of "./Sample/group-movie-1080p-sample.ext"
    This function is pretty messy (so many path manipulations), but it works!
    Maybe in the future it would be better to just recursively search for "group-movie-1080p-sample.ext"
"""
def delete_video_sample_files(srr_file, release_dir):
    stored_files = rescene.info(srr_file)["stored_files"]
    for sfile in stored_files.keys():
        if sfile.endswith('.srs') and 'sample' in sfile:
            files = rescene.extract_files(os.path.normpath(srr_file), release_dir, False, sfile)

            # show which files are extracted + success or not
            for efile, success in files:
                file_name = efile[len(out_folder) + 1:]
                if success:
                    print("{0}: extracted.".format(file_name))
                else:
                    print("{0}: not extracted!".format(file_name))

            ifile = os.path.join(release_dir, os.path.basename(sfile))
            ftype = resample.file_type_info(ifile).file_type
            sample = resample.sample_class_factory(ftype)
            srs_data, tracks = sample.load_srs(ifile)

            sample_file = None
            ## './group-movie-1080p-sample.mkv'
            if os.path.isfile(os.path.join(release_dir, srs_data.name)):
                sample_file = os.path.join(release_dir, srs_data.name)

            ## './Sample/group-movie-1080p-sample.mkv'
            elif os.path.isfile(os.path.join(release_dir, os.path.join(os.path.dirname(sfile), srs_data.name))):
                sample_file = os.path.join(release_dir, os.path.join(os.path.dirname(sfile), srs_data.name))

            if sample_file != None:
                os.remove(sample_file)
                print("{0}: deleted!".format(os.path.relpath(sample_file, release_dir)))

            if remove_srs:
                os.remove(ifile)
                print("{0}: deleted!".format(os.path.basename(ifile)))

if __name__ == "__main__":
    # VARS
    remove_valid_srr = False # https://github.com/neofright/sabnzbd_srrdb/issues/6
    remove_samples = True # https://github.com/sabnzbd/sabnzbd/issues/2296
    remove_srs = True
    archive_nzb = True
    move_albums = False

    release_is_music = False

    run_from_sab = True
    if 'SAB_COMPLETE_DIR' in os.environ:
        release_dir = os.environ['SAB_COMPLETE_DIR'] ## for nzbget use os.environ['NZBPP_DIRECTORY']
    else:
        release_dir = sys.argv[1]
        run_from_sab = False

    ## Things break if the path ends with a slash...
    if release_dir.endswith('/'):
        release_dir = release_dir[:-1]

    release_basename = os.path.basename(release_dir)
    print("Directory name: %s" % release_basename)

    ## Abort post processing for releases with whitespace in their name
    if len(release_basename.split()) > 1:
        print("Literal space in release name (P2P?). Skipping.")
        sys.exit(0)

    ## Abort post processing for season pack releases
    pattern = '\\.S[0-9]+\\.'
    if re.search(pattern, release_basename, re.IGNORECASE):
        print("Season pack detected. Script will not run.")
        sys.exit(0)

    media_file = return_largest_file(release_dir)
    ## Search for existing srr file and attempt to fetch if missing (function hopefully returns the full path)...
    srr_file = get_srr_file(release_dir, media_file)

    ## If an srr file has been found...
    if srr_file:
        ####################################################################
        out_folder = os.path.normpath(release_dir)
        ## Extract only the file types from srr in the regex below:
        to_extract = re.compile('^.*\\.(nfo|m3u|jpg|sfv)$', re.IGNORECASE)
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
        ## Verify the crc32 hash(es) of the release and store the exit code and stdout.
        with contextlib.redirect_stdout(io.StringIO()) as f:
            verification_exit_code = verify_scene_rls(srr_file, release_dir)
        srr_stdout = f.getvalue()

        ## if verification was successful
        if verification_exit_code == 0:
            ## check if we want to do cleanup
            if not release_is_music:
                if remove_samples:
                    delete_video_sample_files(srr_file, release_dir)

            ## wait until after sample detection to decide on removing srr
            if remove_valid_srr:
                os.remove(srr_file)
                print("{0}: deleted!".format(os.path.basename(srr_file)))

            ## archive the nzb file?
            if archive_nzb:
                nzb_files = pyglob.glob(os.path.join(pyglob.escape(release_dir), '*.nzb'))
                ## if the uploader didn't already include the nzb file...
                if not len(nzb_files):
                    ## are we calling the script from sabnzbd? the nzb won't exist if we are calling it manually...
                    if run_from_sab:
                        ## https://stackoverflow.com/a/44712152
                        import gzip
                        import shutil
                        with gzip.open(os.environ['SAB_ORIG_NZB_GZ'], 'rb') as f_in:
                            with open(os.path.join(os.path.join(release_dir, release_basename + ".nzb")), 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)

            ## move albums to artist dirs
            if release_is_music and run_from_sab and move_albums:
                artist_name_clean = release_basename.split('-')[0].replace('_',' ').strip()
                if artist_name_clean.lower() not in ['va', 'ost']:
                    artist_dir = os.path.join(os.path.dirname(release_dir), artist_name_clean)
                    if not os.path.isdir(artist_dir):
                        os.mkdir(artist_dir)

                    if not os.path.isdir(os.path.join(artist_dir,release_basename)):
                        shutil.move(release_dir, artist_dir)
                    else:
                        print('You already have this album dummy!!!')
                        sys.exit(10)

        ## Exit this script with the stored exit code (and stdout) of the verification process.
        print(srr_stdout)
        sys.exit(verification_exit_code)
        ####################################################################
