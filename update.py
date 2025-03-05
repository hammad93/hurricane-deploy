# -*- coding: utf-8 -*-
"""
Scientific units used are as follows,
Coordinates (Lat, Lon) : Decimal Degrees (DD)
Timestamp : Python Datetime
Barometric pressure : mb
Wind Intensity: Knots
"""

from curses import meta
import xmltodict
import requests
from datetime import datetime
import dateutil.parser
from pytz import timezone
import zipfile
import io
from bs4 import BeautifulSoup
import pandas as pd
import hashlib
import db
import sqlalchemy
from sqlalchemy import MetaData, Table
import json
import re
import config

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
    kml['results'] = []
    for attribute in kml['kml']['Document']['Folder']:
        if attribute['name'] == 'Data':
            for entry in attribute['Placemark']:
                # parse time information
                time = datetime.strptime(entry['atcfdtg'],
                                        '%Y%m%d%H').replace(
                    tzinfo=timezone('UTC'))

                # add to results
                kml['results'].append({
                    'time' : time,
                    'wind' : float(entry['intensity']),
                    'lat' : float(entry['lat']),
                    'lon' : float(entry['lon']),
                    'pressure' : float(entry['minSeaLevelPres'])
                })
                print(kml['results'][-1])

    return kml

def nhc() :
    '''
    Runs the NHC update and populates current Atlantic storms

    Returns
    -------
    array of dict
        Each dictionary is in the following form,
        {
            "storm" : string # the storm ID from the NHC
            "metadata" : dict # the kml files used to create the results
            "entries" : array of dict # The data for the storm in the form,
                {
                    'time' : Datetime,
                    'wind' : Knots,
                    'lat' : Decimal Degrees,
                    'lon' : Decimal Degrees,
                    'pressure' : Barometric pressure (mb)
                }
        }
    '''
    # this link can be reused to download the most recent data
    static_link = 'https://www.nhc.noaa.gov/gis/kml/nhc_active.kml'
    # common timezones for parsing with dateutil. offset by seconds
    timezones = {
        "ADT": 4 * 3600,
        "AST": 3 * 3600,
        "CDT": -5 * 3600,
        "CST": -6 * 3600,
        "CT": -6 * 3600,
        "EDT": -4 * 3600,
        "EST": -5 * 3600,
        "ET": -5 * 3600,
        "GMT": 0 * 3600,
        "PST": -8 * 3600,
        "PT": -8 * 3600,
        "UTC": 0 * 3600,
        "Z": 0 * 3600,
    }

    # create data structure as dictionary
    request = requests.get(static_link)
    data = xmltodict.parse(request.text)
    results = []
    
    # return if no storms
    if 'Folder' not in data['kml']['Document'].keys() :
        return results
    
    # parse in storms
    for folder in data['kml']['Document']['Folder']:
        # the id's that start with 'at' are the storms we are interested in
        # others can include 'wsp' for wind speed probabilities
        if folder['@id'][:2] == 'at':
            # some storms don't have any data because they are so weak
            if not 'ExtendedData' in folder.keys():
                continue

            # storm data structure
            storm = {
                'metadata': folder,
                'entries': []
            }
            entry = {}

            for attribute in folder['ExtendedData'][1]:
                if attribute == 'tc:atcfID':  # NHC Storm ID
                    storm['id'] = folder['ExtendedData'][1][attribute]
                elif attribute == 'tc:name':  # Human readable name
                    storm['name'] = folder['ExtendedData'][1][attribute]
                    print(folder['ExtendedData'][1][attribute])
                elif attribute == 'tc:centerLat':  # Latitude
                    entry['lat'] = float(folder['ExtendedData'][1][attribute])
                elif attribute == 'tc:centerLon':  # Longitude
                    entry['lon'] = float(folder['ExtendedData'][1][attribute])
                elif attribute == 'tc:dateTime':  # Timestamp
                    entry['time'] = dateutil.parser.parse(
                        folder['ExtendedData'][1][attribute],
                        tzinfos=timezones)
                elif attribute == 'tc:minimumPressure':  # Barometric pressure
                    entry['pressure'] = float(folder['ExtendedData'][1]
                                              [attribute].split(' ')[0])
                elif attribute == 'tc:maxSustainedWind':  # Wind Intensity
                    # note that we are converting mph to knots
                    entry['wind'] = float(folder['ExtendedData'][1][attribute].
                                          split(' ')[0]) / 1.151

            print(storm['id'])
            print(entry)

            # add entry to storm
            storm['entries'].append(entry)
            # get network link and extract past history
            for links in folder['NetworkLink']:
                if links['@id'] == 'pasttrack':
                    kml = past_track(links['Link']['href'])
                    # add history to entries
                    storm['entries'].extend(kml['results'])

                    # add history to storm metadata
                    storm['metadata']['history'] = kml

            # add to results
            results.append(storm)

    return results

def update_global_hwrf():
    '''
    Provides data based on current global storms based on the HWRF data

    https://dtcenter.org/sites/default/files/community-code/hwrf/docs/users_guide/HWRF-UG-2018.pdf
    - Page 154 column and data descriptions
    Returns
    -------
    array of dict
        Each dictionary is in the following form,
        {
            "id" : string,
        }
    '''
    config = {
        'url': 'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS/',
        'freq': 21600, # (6 hours) frequency, in seconds
        'time_column': 'Last Change',
        'column_names': ['basin', 'id', 'time', 'is_f', 'model', 'lead_time',
                        'lat', 'lon', 'wind', 'pressure', 'label', 'radii_threshold', 'radii_begin',
                        'wind_radii_1', 'wind_radii_2', 'wind_radii_3', 'wind_radii_4', 'isobar_pressure',
                        'isobar_radius', 'max_wind_radius', 'var_1', 'var_2', 'var_3', 'var_4', 'var_5', 
                        'var_6', 'var_7', 'name', 'var_8'],
        'column_buffer': 20,
    }
    # read in table from link, this is the only (first) table
    update_table = pd.read_html(config['url'])[0]
    # get relevant table
    update_table['timestamp'] = [time.timestamp() for time in pd.to_datetime(update_table[config['time_column']], utc=True)]
    # the table has many entries, so we only parse the most recent one
    # according to the frequency. We use the most recent in a day
    timestamp_threshold = datetime.now().timestamp() - (config['freq'] * 4)
    data = update_table[update_table['timestamp'] > timestamp_threshold]
    # construct links to applicable data
    links = [config['url'] + fname for fname in data['File Name']]
    '''
    example,
    ['https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS/ash972023.dat',
    'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS/bsh972023.dat',
    'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS/ash162023.dat',
     :
     :
    'https://www.emc.ncep.noaa.gov/gc_wmb/vxt/DECKS/bsh162023.dat',]
    '''
    # filter it to just the track, has a b in the first letter of the name
    filtered_links = [link for link in links if link.split('/')[-1][0] == 'b']
    # for each link, download it and append to an array
    column_names = config['column_names'] + [f'unk_{i + 1}' for i in range(config['column_buffer'])]
    active_storms = pd.concat([pd.read_csv(link, names=column_names, engine='python') for link in filtered_links],
        ignore_index = True)
    # trim buffered columns
    active_storms = active_storms.dropna(axis=1, how='all')
    # change data types of columns
    active_storms['time'] = [datetime.strptime(str(time), '%Y%m%d%H').replace(tzinfo=timezone('utc')) for time in active_storms['time']]
    
    def process_coord(c):
        '''
        The coordinates in the files are in a different 
        coordinate format like 262N. The data description
        claims that we can divide by 10 and get the 
        decimal representation. This function tries to output
        in decimal degrees. A positive value for North and East,
        a negative value for South and West. 
        '''
        value = float(c[:-1]) / 10
        direction = c[-1:]
        return value if direction in ['N', 'E'] else -value
    
    active_storms['lat'] = [process_coord(c) for c in active_storms['lat']]
    active_storms['lon'] = [process_coord(c) for c in active_storms['lon']]
    active_storms['storm_id'] = [f'{ids[0]}{ids[1]}{ids[2].year}' for ids in zip(
        active_storms['basin'],
        active_storms['id'],
        active_storms['time'])]
    
    # drop duplicates that might have some extra data
    postprocessed_data = active_storms.drop_duplicates(
        subset=['basin', 'id', 'time', 'model', 'lead_time', 'lat', 'lon', 'wind', 'pressure'])
    # rename columns to match data structure
    postprocessed_data = postprocessed_data.rename(columns = {'wind': 'int', 'id': '_id'})
    postprocessed_data = postprocessed_data.rename(columns = {'storm_id': 'id'})
    postprocessed_data['source'] = f"HWRF emc.ncep.noaa.gov"
    postprocessed_data['trans_time'] = datetime.now().isoformat() # transfer time
    postprocessed_data['time'] = [timestamp.isoformat() for timestamp in postprocessed_data['time']]
    return postprocessed_data

def update_global_rammb():
    '''
    Provides data based on current global storms based on the RAMMB data

    Returns
    -------
    array of dict
        Each dictionary is in the following form,
        {
            "id" : string,
            "urls" : dict,
            "data" : {
            # note that this data depends on the data source
                'track_history' : {

                },
                'forecast_track' : {

                }
            }
        }
    '''
    config = {
        'url' : 'http://rammb-data.cira.colostate.edu/tc_realtime/',
        'ir_img_url' : 'http://rammb-data.cira.colostate.edu/tc_realtime/archive.asp?product=4kmirimg&storm_identifier=',
        'base_url' :  'http://rammb-data.cira.colostate.edu'
    }
    page = requests.get(config['url'])
    soup = BeautifulSoup(page.text, 'html.parser')
    data = soup.findAll('div',attrs={'class':'basin_storms'})
    storms = []
    for div in data:
        links = div.findAll('a')
        for a in links:
            storm = {
                'id' : a.text[:8],
                'urls' : {
                  'base' : config['url'] + a['href'],
                  'img_url' : config['ir_img_url'] + a.text[:8].lower() 
                }
            }
            print(f'[id]: {storm["id"]}')
            print(f'[url]: {storm["urls"]["base"]}')
            print(f'[img_url]: {storm["urls"]["img_url"]}')
            
            # get dataframe from url
            current_page = requests.get(storm['urls']['base'])
            current_soup = BeautifulSoup(current_page.text, 'html.parser')
            tables = current_soup.findAll('table')
            
            # we manually input the table names because they're the same
            # for every storm
            has_forecast = len(tables) > 1
            storm['data'] = {
                'forecast_track' : pd.read_html(
                  str(tables[0]),
                  header = 0)[0].to_dict() if has_forecast else None,
                'track_history' : pd.read_html(
                  str(tables[1]),
                  header = 0)[0].to_dict() if has_forecast else pd.read_html(
                    str(tables[0]),
                    header = 0)[0].to_dict()
            }
            print(f'[track_history] : {storm["data"]["track_history"]}')
            print(f'[forecast_track] : {storm["data"]["forecast_track"]}')
            
            # begin getting img url links
            current_page = requests.get(storm['urls']['img_url'])
            current_soup = BeautifulSoup(current_page.text, 'html.parser')
            img_urls = [config['base_url'] + img_href['href'] for img_href in current_soup.findAll('table')[0].findAll('a')]
            storm['urls']['img_urls'] = img_urls
            print(f'[1st img_url]: {storm["urls"]["img_urls"][0]}')
            storms.append(storm)
    
    return storms

def update_global():
    '''
    This function decides which global ingestion to use
    '''
    return update_global_hwrf()

def data_to_hash(data) :
    '''
    Takes in a Pandas DataFrame and creates a MD5 hash
    in order to quickly compare if we have the same data
    '''
    return hashlib.md5(json.dumps(data).encode()).hexdigest()

def upload_hash(data) :
    '''
    Checks if the data has already been ingested and returns a
    False if it has. It returns the hash if it was successfully uploaded

    References
    ----------
    - https://docs.sqlalchemy.org/en/14/tutorial/data_insert.html
    '''
    hashx = data_to_hash(data)
    results = db.query(
        f"select hash from ingest_hash where hash = '{hashx}'"
        )
    if len(results) < 1 : # sqlalchemy 1.4.39
        engine = db.get_engine('hurricane_live')
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables['ingest_hash']
        stmnt = table.insert().values(
            hash = hashx,
            data = {"ingest" : data},
            time = datetime.now().isoformat()
        )
        db.query(q = (stmnt,), write = True)
    return {
        'hash' : hashx,
        'unique' : (len(results) < 1)
    }

def global_pipeline() :
    '''
    Here, we run the webscraper for the live tropical storm data and do some post processing.
    '''
    data = update_global()
    # generate data
    hurricanes = data[['id', 'time', 'lat', 'lon', 'int']].drop_duplicates()
    # check if data is unique
    hashx = upload_hash(hurricanes.to_dict('records'))
    print(f'data hash: {hashx["hash"]}')
    if hashx['unique'] :
        # create table parameters
        engine = db.get_engine('hurricane_live')
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables['hurricane_live']
        # process the data into the live database
        data['hash'] = hashx['hash']
        hurricanes = data[['id', 'time', 'lat', 'lon', 'int', 'hash', 'trans_time', 'source']]
        # reset live table
        db.query(q = ('DELETE FROM hurricane_live',), write = True)
        db.query(q = (table.insert(), hurricanes.to_dict('records')), write = True)
    return {
        'dataframe' : hurricanes,
        'hash' : hashx['hash'],
        'unique' : hashx['unique']
    }

def live_deltas():
    '''
    Returns a representation of the changes in the live data
    '''
    df = db.query('select data from ingest_hash')
    deltas = []
    prev = None
    for row in df.iterrows() :
        row['data']
    return df

def update_global_hfsa():
    '''
    Provides data based on current global storms based on the HFSA data

    Returns
    -------
    array of dict
        Each dictionary is in the following form,
        {
            "id" : string,
        }
    '''
    # request the HFSA data through web url
    request = requests.get(config.hfsa_url)
    content = request.content.decode('utf8')

    # begin parsing current tropical storms
    # extract variables using regular expressions
    actstorm = json.loads(re.search(r'var actstorm\s*=\s*({.*?});', content, re.DOTALL).group(1))
    actcycle = json.loads(re.search(r'var actcycle\s*=\s*({.*?});', content, re.DOTALL).group(1))
    basins = json.loads(re.search(r'var basins\s*=\s*(\[.*?\]);', content, re.DOTALL).group(1))

    # generate URLs based on the JavaScript logic
    urls = []
    for basin_idx, basin in enumerate(basins):
        key = str(basin_idx)
        if key in actstorm and key in actcycle:
            for storm, cycle in zip(actstorm[key], actcycle[key]):
                # Extract components from storm/cycle names
                sId_part = storm[-3:].lower()  # Last 3 chars of storm name, lowercase
                acycle_part = cycle.split('.')[1]  # Get the date portion
                
                # Construct URL components
                datadir = f"https://www.emc.ncep.noaa.gov/{basin['reldir']}"
                filename = f"{sId_part}.{acycle_part}.hfsa.trak.atcfunix"
                
                # Full URL path
                full_url = f"{datadir}/{storm}/{cycle}/{filename}"
                urls.append(full_url)
    
    # drill down and request the raw data for each tropical storm
    raw_data = [{'url': url, 'content': requests.get(url).content} for url in urls]
    
    return raw_data

if __name__ == "__main__" :
    update_global()