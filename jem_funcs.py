# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 11:19:34 2017

@author: agatab
"""

import os
import fnmatch
import numpy as np
import pandas as pd
from pandas.io.json import json_normalize
from datetime import datetime
from dateutil import parser





"""-------------------------FUNCTION DEFINITIONS--------------------------------"""

def get_similar_values(invalid_val, valid_vals):
    '''Look for valid values that start with the first letter of user entry'''
    if len(invalid_val) > 0:
        first = invalid_val[0]
        result = [v for v in valid_vals if v.startswith(first)]
    else:
        result = []
    return result


def get_response_to_invalid(invalid_val, invalid_response, valid_vals=None):
    '''Return a non-specific error message, or similar valid values if they exist'''
    if valid_vals:
        similar = get_similar_values(invalid_val, valid_vals)
        if len(similar) > 0:
            return "\nPerhaps you meant one of the following? \n%s " %similar
        else:
            return invalid_response
    else:
        return invalid_response

def validated_input(prompt_text, invalid_response, valid_options=None):
    '''Keep asking user for input until a valid input has been entered'''
    while True:
        result = raw_input(prompt_text)
        result = result.lower()
        if (valid_options) and (result not in valid_options):
            response = get_response_to_invalid(result, invalid_response, valid_options)
            print response
            continue
        else:
            break
    return result

def validated_date_input(prompt_text, invalid_response, valid_options=None):
    """Prompt user to enter date, and check whether date is valid input.
    Keep prompting until a valid input has been entered.
    
    Parameters
    ----------
    prompt_text : string
    invalid_response : string
        A message to return to user if entry was invalid.
    valid_options: None or list
        Optional argument with valid options
        
    Returns
    -------
    result : string
        User's validated response to prompt text.
    """

    while True:
        result = raw_input(prompt_text)
        result = result.lower()
        try:
            datetime.strptime(result, "%y%m%d")
        except:
            response = get_response_to_invalid(result, invalid_response, valid_options)
            print response
            continue
        else:
            break
    return result


def _connect(user="limsreader", host="limsdb2", database="lims2", password="limsro", port=5432):
    import pg8000
    conn = pg8000.connect(user=user, host=host, database=database, password=password, port=port)
    return conn, conn.cursor()

def _select(cursor, query):
    cursor.execute(query)
    columns = [ d[0] for d in cursor.description ]
    return [ dict(zip(columns, c)) for c in cursor.fetchall() ]

def limsquery(query, user="limsreader", host="limsdb2", database="lims2", password="limsro", port=5432):
    conn, cursor = _connect(user, host, database, password, port)
    try:
        results = _select(cursor, query)
    finally:
        cursor.close()
        conn.close()
    return results

def get_prep_from_specimen_name(name):
    """Return prep name (LabTracksID or Human Case ID).
    
    Parameters
    ----------
    name : string
        A Mouse or Human specimen name
    
    Returns
    -------
    string
        LabTracksID or Human Case ID
    """
    lims_query_str = "SELECT DISTINCT d.external_donor_name AS labtracksID, \
    d.name AS donor_name, \
    org.name AS organism_name \
    FROM specimens cell \
    LEFT JOIN donors d ON d.id = cell.donor_id \
    JOIN organisms org ON d.organism_id = org.id \
    WHERE cell.name = '%s'" %name
    
    results = limsquery(lims_query_str)
    if len(results) > 0:
        organism = results[0]["organism_name"]
        labtracks = results[0]["labtracksid"]
        donorname = results[0]["donor_name"]  
        if organism == "Mus musculus":
            return labtracks
        else:
            return donorname
    else:
        try:
            return name.split(".")[0].split("-")[-1]
        except:
            return "Not found."
            
def get_jsons(dirname, expt, delta_days):
    """Return filepaths of metadata files that were created within
    delta_days of today.
    
    Parameters
    ----------
    dirname : string
        Path to metadata file directory.
    expt : string
        Experiment type for filename match ("PS" or "IVSCC").
    delta_days : int
        A number of days in the past.

    Returns
    -------
    json_paths : list
        A list of filepaths that are a expt string match and were
        created within delta_days of today.
    """

    json_paths = []
    comparison_date = datetime.today()
    
    for jfile in os.listdir(dirname):
        if fnmatch.fnmatch(jfile,'*.%s.json' %expt):
            jpath = os.path.join(dirname, jfile)
            created_date = datetime.fromtimestamp(os.path.getctime(jpath))
            if abs((comparison_date - created_date ).days) < delta_days:
                json_paths.append(jpath)
    return json_paths


def flatten_attempts(slice_info, form_version):
    """Return flattened slice metadata dataframe.
    
    Parameters
    ----------
    slice_info : dict
        A dictionary of slices with nested pipette attempts.
    
    form_version : string
        A string containing the JEM form version.
        (Pre-version 2 contains IVSCC, PatchSeq and Electroporation arrays)
    Returns
    -------
    attempts_slice_df : pandas dataframe
        A dataframe of all pipette attempts along with all slice metadata.
    """
    
    df = json_normalize(slice_info)
    if form_version >= "2":
        ps_array_name = "pipettes"
    else:
        ps_array_name = "pipettesPatchSeqPilot"
    
    attempts_df = json_normalize(slice_info[ps_array_name])
    attempts_df["limsSpecName"] = df["limsSpecName"].values[0]
    attempts_df["attempt"] = [p+1 for p in attempts_df.index.values]
    attempts_slice_df = pd.merge(df, attempts_df, how="outer", on="limsSpecName")
    attempts_slice_df.drop(ps_array_name, axis=1, inplace=True)
    return attempts_slice_df

def is_field(df, colname):
    """Determine whether a column name exists in a dataframe.
    
    Parameters
    ----------
    df : a Pandas dataframe
    colname : string
        
    Returns
    -------
    Boolean
        Boolean value indicating if the colname exists in the dataframe.
    """
    
    try:
        df[colname]
        return True
    except KeyError:
        return False


def normalize_MMDDYYYY(val):
    """Determine whether a value is a string in the correct MMDDYYYY format, and if not, convert it.
    
    Parameters
    ----------
    val : string or np.nan
        
    Returns
    -------
    val : string or np.nan
    
    """
    
    try:
        datetime.strptime(val, "%m/%d/%Y")
        return val
    except TypeError:
        return np.nan
    except ValueError:
        if len(val) == 8:
            return datetime.strptime(val, "%m/%d/%y").strftime("%m/%d/%Y")
        else:
            return val


#def utc_colon_remover(utc_date):
#    """Removes colon from -UTC (HH:SS), so that Python's strptime can see it. 
#    
#    Parameters
#    ----------
#    utc_date :  string
#        a date in the format "%Y-%m-%d %H:%M:%S -%H:%M"
#        
#    Returns
#    -------
#    python_utc_date : string
#        a date in the format "%Y-%m-%d %H:%M:%S -%H%M"
#    
#    """
#    
#    if ":" == utc_date[-3:-2]:
#        python_utc_date = utc_date[:-3] + utc_date[-2:]
#    else:
#        return utc_date
#    return python_utc_date


def format_MMDDYY(val, date_field, jem_version):
    """Return dates formatted for Kim's sheet (MM/DD/YY). 
    Accounts for shift to ISO 8601 -UTC, implemented in version 2.0.3.
    
    Parameters
    ----------
    val : 
    date_field : string or np.nan
    jem_version : string
        
    Returns
    -------
    date : string or np.nan
    
    """
    if jem_version >= "2.0.3":
        return parser.parse(val).strftime("%m/%d/%y")
        #datetime_fmt = "%Y-%m-%d %H:%M:%S -%z"
        #date_fmt = "%Y-%m-%d"
        #val = utc_colon_remover(val)
    else:
        datetime_fmt = "%m/%d/%Y %H:%M"
        date_fmt = "%m/%d/%Y"
        
    if date_field == "date":
        
        try:
            datetime.strptime(val, datetime_fmt)
            return datetime.strptime(val, datetime_fmt).strftime("%m/%d/%y")
        except TypeError:
            return np.nan
    else:
        try:
            datetime.strptime(val, date_fmt)
            return datetime.strptime(val, date_fmt).strftime("%m/%d/%y")
        except TypeError:
            return np.nan
        
        
def normalize_dates(df):
    """Normalize date format in available date fields (from different JEM versions) as "MM/DD/YYYY".
    
    Parameters
    ----------
    df : a Pandas dataframe
        
    Returns
    -------
    df : a Pandas dataframe
    """
    
    date_fields =["acsfProductionDate", "internalFillDate", "blankFillDate"]
    for d in date_fields:
        if is_field(df, d):
            df[d] = df[d].apply(normalize_MMDDYYYY)            
    return df



def fillna_rois(df):
    """Fill nans in all available roi fields (from different JEM versions) with "None, None".
    
    Parameters
    ----------
    df : a Pandas dataframe
        
    Returns
    -------
    df : a Pandas dataframe
    """
    
    roi_fields =["autoRoi", "manualRoi", "approach.autoRoi", "approach.manualRoi", "approach.anatomicalLocation"]
    for roi in roi_fields:
        if is_field(df, roi):
            df[roi].fillna("None, None", inplace=True)
            df[roi].replace("None", "None, None", inplace=True)
            
    return df

def select_report_date_attempts(df, report_dt):
    """Return recordings from a specific report_date, or between two report dates.
    
    Parameters
    ----------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempts.
    report_dt : list
        A list of datetime.date values
        
    Returns
    -------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempts from the report date.
    """
    
    df["date_dt"] = df["date"].apply(lambda x: parser.parse(x).date())
    if len(report_dt) == 1:
        df = df[df["date_dt"] == report_dt[0]]
    else:
        df = df[(df["date_dt"] >= report_dt[0]) & (df["date_dt"] <= report_dt[1])]
    return df

def remove_failed(df, j_cols):
    """Remove records that did not result in either a PS data sample, or a Tissue Touch sample.
    
    Parameters
    ----------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempts.
    j_cols : list
        A list of JEM form column names
        
    Returns
    -------
    df
        A pandas dataframe of successful PatchSeq recordings + Tissue Touch samples.
    """
    
    
    df_cols = df.columns
    if "extraction.tubeID" in df_cols and "approach.pilotTest05" in df_cols:
        df = df.dropna(subset=["extraction.tubeID", "approach.pilotTest05"], how="all")
    elif "extraction.tubeID" in df_cols:
        df = df.dropna(subset=["extraction.tubeID"])
    elif "approach.pilotTest05" in df_cols:
        df = df.dropna(subset=["approach.pilotTest05"])
    else:
        df = pd.DataFrame(columns=j_cols)
    return df



def is_num(val):
    """Determine whether a value can be converted to an integer.
    
    Parameters
    ----------
    val : string or float
        
    Returns
    -------
    Boolean
        Boolean value indicating if the value can be converted to an integer.
    """
    
    try:
        int(val)
        return True
    except ValueError:
        return False

def generate_PS_lims_tube_id(row):
    """Generate LIMS tube ID (aka Patch Container) for a PatchSeq sample
    or Tissue Touch from user, date and tube ID in pre-2.0.2 JEM versions, 
    or take directly from extraction.tubeID in >= 2.0.2 JEM versions.
    
    Parameters
    ----------
    row : pandas dataframe row containing metadata for a PatchSeq sample.
        
    Returns
    -------
    lims_tube_id : string
         LIMS tube ID (aka Patch Container).
    """

    user = row["user"]
    date = row["date_dt"].strftime("%y%m%d")
    if is_field(row, "formVersion"):
        jem_version = row["formVersion"]
    else:
        jem_version = "1.0.0"
    
    if jem_version >= "2.0.2":
        return row["extraction.tubeID"]
    else:
        if row["approach.pilotName"] == "Tissue_Touch":
            tube_id = row["approach.pilotTest05"]
        else:
            tube_id = row["extraction.tubeID"]
        
        if is_num(tube_id):
            tube_str = str(int(tube_id))
            if len(tube_str) == 2:
                tube_str = '0' + tube_str
            elif len(tube_str) == 1:
                tube_str = '00' + tube_str
            else:
                tube_str = tube_str  
            lims_tube_id = '%sS4_%s_%s_A01' %(user, date, tube_str)
        else:
            return None
        
    return lims_tube_id


def extract_timestamps(row):
    """Return recording/extraction/retraction timestamps.
    
    Parameters
    ----------
    row : a pandas dataframe row 
    
    Returns
    -------
    tuple
        Tuple with time_experiment_start, time_extraction_start, time_extraction_end, time_retraction_end.
    """
    
    jem_version = row["formVersion"]
    if jem_version >= "2":
        rec_start = row["recording.timeWholeCellStart"]
        extr_start = row["extraction.timeExtractionStart"]
        retr_start = row["extraction.timeExtractionEnd"]
        retr_end = row["extraction.timeRetractionEnd"]
        
    else:
        rec_start = row["recording.timeWholeCellStart"]
        extr_start = row["extraction.timeExtractionStart"]
        retr_start = row["extraction.timeEnd"]
        retr_end = None

    return rec_start, extr_start, retr_start, retr_end
      

def extract_essential_metadata(df, p_users, roi_df):
    """Extract essential metadata (patch container, roi major/minor...)
    
    Parameters
    ----------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempt metadata from JSON files.
        
    p_users : dict
        A mapping of user names to user 'codes' for patch containers.
    
    roi_df : pandas dataframe
        A mapping of LIMS structure acronyms to comma separated major, minor areas
        
    Returns
    -------
    df2 : pandas dataframe
        A minimal dataframe with essential metadata.
    """
    
    df2 = df.copy()
    #df2["rigOperator"].replace(p_users, inplace=True)
    df2["user"] = df["rigOperator"].apply(lambda x: p_users[x])
    df2["json_patch_container"] = df2.apply(generate_PS_lims_tube_id, axis=1)    
    df2["roi_major"], df2["roi_minor"], df2["approach.manualRoi"] =  zip(*df2.apply(extract_roi, args=(roi_df,), axis=1))
    
    
    if "blankFillDate" not in df2.columns:
        df2["blankFillDate"] = np.nan

    return df2
      

def extract_metadata(df, p_users, roi_df):
   """Extract essential metadata (patch container, roi major/minor...)
   
   Parameters
   ----------
   df : pandas dataframe
       A dataframe of PatchSeq recording attempt metadata from JSON files.
       
   p_users : dict
       A mapping of user names to user 'codes' for patch containers.
   roi_df : pandas dataframe
       A mapping of LIMS structure acronyms to comma separated major, minor areas
        
   Returns
   -------
   df2 : pandas dataframe
       A minimal dataframe with essential metadata.
   """
   
   df2 = df.copy()
   df2["user"] = df["rigOperator"].apply(lambda x: p_users[x])
   df2["extraction.tubeID"] = df2.apply(generate_PS_lims_tube_id, axis=1)   
   df2["roi_major"], df2["roi_minor"], df2["approach.manualRoi"] =  zip(*df2.apply(extract_roi, args=(roi_df, ), axis=1))
   df2["approach.autoRoi"] = None
   df2["recording.timeWholeCellStart"], df2["extraction.timeExtractionStart"], df2["extraction.timeExtractionEnd"], df2["extraction.timeRetractionEnd"] = zip(*df2.apply(extract_timestamps, axis=1))
   #df2["pilot_name"] = df["approach.pilotName"].apply(lambda x: x if x=="Tissue_Touch" else None)
   
   if "blankFillDate" not in df2.columns:
       df2["blankFillDate"] = None

   return df2


def extract_roi(row, roi_df):
    """Return ROI major, ROI minor and acronym from autoRoi or manualRoi or anatomicalLocation (old JEM) fields in dataframe.
    
    Parameters
    ----------
    row : a pandas dataframe row 
    roi_df : a dataframe translating roi names to comma separated major and minor areas, and acronym
    
    Returns
    -------
    tuple
        Tuple with major recording region, minor recording region and acronym.
    """
    
    if is_field(row, "formVersion"):
        jem_version = row["formVersion"]
    else:
        jem_version = "1.0.0"
        
    if jem_version >= "2.0.2":
        auto_roi = row["autoRoi"]
        manual_roi = row["manualRoi"]
        if auto_roi == "None, None":
            roi = manual_roi
        else:
            roi = auto_roi

    elif jem_version >= "2":
        auto_roi = row["approach.autoRoi"]
        manual_roi = row["approach.manualRoi"]
        
        if auto_roi == "None, None":
            roi = manual_roi
        else:
            roi = auto_roi
        
    else:
        roi = row["approach.anatomicalLocation"]


    if roi in roi_df.index:
        roi_major, roi_minor, roi_acronym = roi_df.loc[roi][["roi_major", "roi_minor", "acronym"]]
    else:
        roi_major, roi_minor, roi_acronym = None, None, roi
    
    return roi_major, roi_minor, roi_acronym
