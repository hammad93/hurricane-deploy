# -*- coding: utf-8 -*-
"""
Created on Tue Sep 15 01:04:55 2020

@author: Hammad
"""

import xmltodict
import requests
from datetime import datetime
from pytz import timezone
import zipfile
import io

# this link can be reused to download the most recent data
static_link = 'https://www.nhc.noaa.gov/gis/kml/nhc_active.kml'


def past_track(link):
    '''
    From a KMZ file of a storm in the NHC format, we extract the history

    Parameters
    ----------
    link string
        The network link or downloadable KMZ href file

    Returns
    -------
    dict
    '''
    kmz = requests.get(link)
    uncompressed = zipfile.ZipFile(io.BytesIO(kmz.content))

    # get the kml name
    for name in uncompressed.namelist():
        # all kml file names begin with al, e.g. 'al202020.kml'
        if name[:2] == 'al':
            file_name = name

    # read the contents of the kml file in the archive
    kml = xmltodict.parse(uncompressed.read(file_name))
    for attribute in kml['kml']['Document']['Folder']:
        if attribute['name'] == 'Data':
            for entry in attribute['Placemark']:
                print(datetime.strptime(entry['atcfdtg'],
                                        '%Y%m%d%H').replace(
                    tzinfo=timezone('UTC')))

    return kml


# create data structure as dictionary
request = requests.get(static_link)
data = xmltodict.parse(request.text)

# parse in storms
for folder in data['kml']['Document']['Folder'] :
    # the id's that start with 'at' are the storms we are interested in
    # others can include 'wsp' for wind speed probabilities
    if folder['@id'][:2] == 'at' :
        # some storms don't have any data because they are so weak
        if not 'ExtendedData' in folder.keys() :
            continue

        storm = {
            'metadata' : folder
        }
        for attribute in folder['ExtendedData'][1] :
            if attribute == 'tc:atcfID' :
                storm['id'] = folder['ExtendedData'][1][attribute]
            if attribute == 'tc:name' :
                print(folder['ExtendedData'][1][attribute])
        print(storm['id'])
        # get network link and extract past history
        for links in folder['NetworkLink'] :
            if links['@id'] == 'pasttrack' :
                past_track(links['Link']['href'])