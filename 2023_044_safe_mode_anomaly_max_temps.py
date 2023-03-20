#!/usr/bin/env python
# coding: utf-8

# # Determine MSIDs reaching mission max/min temperatures duing 2023:044 Safe Mode Anomaly 

# ## Imports 

# In[1]:


import os
os.environ['SKA_DATA'] = 'C:/Users/christian.anderson/Documents/MATLAB/FOT_Tools/Ska_data'


# In[2]:


import json
import re
from urllib.request import urlopen
import pandas as pd
import requests
import numpy as np
import plotly.io as pio
import plotly.express as px
from cheta import fetch_eng
import Ska.engarchive.fetch_eng as fetch_eng2
import Chandra.Time
from cxotime import CxoTime


# In[3]:


from IPython.core.display import display, HTML
display(HTML("<style>.container { width:90% !important; }</style>"))
pio.renderers.default = "notebook"


# ## Local Function Definitions 

# In[4]:


def maude_query(msid, t1, t2, all_points=True):
    # (base URL)/<CHANNEL>/<querytype>.<format>?<query options separated by &>
    # https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m=STAT_1DAY_MIN_OOBTHR18&ts=2015.001&tp=2016.001
    
    # All Points
    if all_points is True:
        # All Points
        base_url_constructor = 'https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m={}&ts={}&tp={}&ap=t'
    else:
        # Reduced Points
        base_url_constructor = 'https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m={}&ts={}&tp={}'

    url = base_url_constructor.format(msid.lower(), t1, t2)

    try:
        jsondata = requests.get(url).json()
        data = pd.DataFrame({'date':pd.to_datetime(jsondata['data-fmt-1']['times'], format='%Y%j%H%M%S%f'),
                       'data':jsondata['data-fmt-1']['values']})
        data["data"] = pd.to_numeric(data["data"])
    except:
        data = pd.DataFrame({'date':[None,], 'data':[None,]})

    return data


def ska_query(msid, t1, t2, stat='daily'):
    data = fetch_eng.Msid(msid, t1, t2, stat=stat)
    return pd.DataFrame({'date': data.times, 'data': data.vals})


def get_warning_low(msid):
    tdb_lim = pd.read_csv('C:/Users/christian.anderson/Documents/Thermal/293_safe_mode_anomaly/TDB_LIMIT.csv')
    
    for i in range(len(tdb_lim)):
        x = tdb_lim.at[i, 'MSID']
        
        if x == msid:
            warning_low = tdb_lim.at[i, 'WARNING_LOW']
        else:
            continue  
            
        return warning_low

    
def get_warning_high(msid):
    tdb_lim = pd.read_csv('C:/Users/christian.anderson/Documents/Thermal/293_safe_mode_anomaly/TDB_LIMIT.csv')
    
    for i in range(len(tdb_lim)):
        x = tdb_lim.at[i, 'MSID']
        
        if x == msid:
            warning_high = tdb_lim.at[i, 'WARNING_HIGH']    
        else:
            continue
            
        return warning_high
                


# In[5]:


import sys
from os.path import expanduser

home = expanduser("~")
sys.path.append(home + "/AXAFLIB/pylimmon/")
import pylimmon

msid = "oobthr10"
safety_limits = pylimmon.get_mission_safety_limits(msid)

current_warning_high = safety_limits["warning_high"][-1]
current_warning_low  = safety_limits["warning_low"][-1]

safety_limits


# ## TDB Limit Table (exported from Microsoft Access) 

# In[6]:


tdb_lim = pd.read_csv('C:/Users/christian.anderson/Documents/Anomalies/2023/2023_44_Safe_Mode/TDB_LIMIT.csv')


# In[7]:


tdb_lim


# ## Read in Thermal MSID List 

# In[8]:


therm_list = pd.read_csv('//noodle/greta/mdahmer/AXAFDATA/weekly_report_data/thermlist.csv')


# In[9]:


therm_list


# ## Filter out non-numerical MSIDs 

# In[10]:


# Extract the "ska_msids"
thermal_MSIDs = therm_list.iloc[:,1]
msids = [v.strip() for v in thermal_MSIDs.values if 'None' not in v]
t1 = '2000:200:00:00:00.000' 
t2 = '2023:051:00:00:00.000'

# List of numeric MSIDs
num_msid = []
# List of the numeric values
num_vals = []

for msid in msids:
    data = fetch_eng.Msid(msid, t1, t2, stat='daily')
    max_temp = max(data.vals)
        
        
    # consider modifying float32 to account for more general cases
    if isinstance(max_temp, np.float32) == True:
        num_vals.append(max_temp)
        num_msid.append(msid)  #these are the  msids with numerical values (not states)
        
    else:
        continue
        
print(num_vals)
    


# ## Determine If max/min occurred during anomaly 

# In[36]:


# Safe Mode Anomaly Time Range
t_anom_start = Chandra.Time.DateTime('2023:044:17:41:00').secs
t_anom_stop = Chandra.Time.DateTime('2023:055:00:00:00').secs

# Data for numeric MSIDs
data_num = {}

# List of MSIDs achieving max temperatures during anomaly:
msid_anom_max = []
msid_anom_min = []
anom_max_df = pd.DataFrame(columns=['MSID', 'Technical Name', 'Max Temp', 'Units', 'Caution High', 'Warning High', 'Time of Max'])
anom_min_df = pd.DataFrame(columns=['MSID', 'Technical Name', 'Min Temp', 'Units', 'Caution Low', 'Warning Low', 'Time  of Min'])


# Iterate through numeric MSIDs
for m in num_msid:
    fetch_eng.data_source.set('cxc')
    data_num[m] = fetch_eng.Msid(m, t1, t2,stat="5min")
    data_num[m].filter_bad(copy=True)
   
    # Technical Name
    try: 
        tech_name = data_num[m].tdb.technical_name
        
    except KeyError:
        tech_name = "Not in TDB"
       
    
    # Units
    try:
        units = data_num[m].unit
        print(units)
    except KeyError:
        units = "None Found"
    
    
    # Limits
    try:    
        safety_limits = pylimmon.get_mission_safety_limits(m)
        
    except IndexError:
        safety_limits = None
    
    if safety_limits:
        current_warning_high = safety_limits["warning_high"][-1]
        current_warning_low  = safety_limits["warning_low"][-1]
        current_caution_high = safety_limits["caution_high"][-1]
        current_caution_low  = safety_limits["caution_low"][-1]
        print(m, 'tdb warning high is:',current_warning_high, 'tdb caution high is', current_caution_high)

    elif safety_limits is None:
        
        try:
            current_warning_high = pylimmon.get_latest_glimmon_limits(m)["warning_high"]
            current_warning_low = pylimmon.get_latest_glimmon_limits(m)["warning_low"]
            current_caution_high = pylimmon.get_latest_glimmon_limits(m)["caution_high"]
            current_caution_low = pylimmon.get_latest_glimmon_limits(m)["caution_low"]
            print(m, 'glimmon warning high is:',current_warning_high, 'glimmon caution high is:', current_caution_high)
            
        except TypeError:
            current_warning_high = 9999
            current_warning_low  = -9999
            current_caution_high = 9999
            current_caution_low = -9999
    
    else:
        print('no tdb or glimmon limits for:', msid_anom)
    
    
    print(m, "-->", "CH =", current_caution_high, ' ', "WH = ", current_warning_high)
    
    
    # Spacecraft Mode Transition Filters
    pad = 300 # seconds
    ind1 = data_num[m].times < (CxoTime('2022:293:16:27:49.000').secs - pad) # 2023:293 Safe Mode transition
    ind2 = data_num[m].times > (CxoTime('2022:293:16:27:49.000').secs + pad)
    ind3 = data_num[m].times < (CxoTime('2023:044:17:41:07.000').secs - pad) # 2023:044 Safe Mode transition 
    ind4 = data_num[m].times > (CxoTime('2023:044:17:41:07.000').secs + pad)
    ind5 = data_num[m].times < (CxoTime('2023:045:03:32:39.000').secs - pad) # 2023:045 Swap to CTU-A
    ind6 = data_num[m].times > (CxoTime('2023:045:03:32:39.000').secs + pad)
    ind7 = data_num[m].times < (CxoTime('2023:047:07:33:47.000').secs - pad) # 2023:047 Safe Mode transition
    ind8 = data_num[m].times > (CxoTime('2023:047:07:33:47.000').secs + pad)
    ind9 = data_num[m].times < (CxoTime('2023:048:03:17:11.000').secs - pad) # 2023:048 Swap to CTU-A
    ind10 = data_num[m].times > (CxoTime('2023:048:03:17:11.000').secs + pad)
    good_ind_1 = ind1 | ind2
    good_ind_2 = ind3 | ind4
    good_ind_3 = ind5 | ind6
    good_ind_4 = ind7 | ind8
    good_ind_5 = ind9 | ind10
    good_ind_6 = data_num[m].vals < 250
     
    pad2 = 70 # seconds
    ind11 = data_num[m].times < (CxoTime('2023:045:03:29:49.010').secs - pad2) # 2023:045 Thermal Control Disabled
    ind12 = data_num[m].times > (CxoTime('2023:045:04:48:37.150').secs + pad2)
    ind13 = data_num[m].times < (CxoTime('2023:047:07:33:33.163').secs - pad2) # 2023:047 Thermal Control Disabled
    ind14 = data_num[m].times > (CxoTime('2023:047:07:34:48.125').secs + pad2)
    ind15 = data_num[m].times < (CxoTime('2023:048:03:14:30.531').secs - pad2) # 2023:048 Thermal Control Disabled
    ind16 = data_num[m].times > (CxoTime('2023:048:03:56:31.086').secs + pad2)
    good_ind_7 = ind11 | ind12
    good_ind_8 = ind13 | ind14
    good_ind_9 = ind15 | ind16
     
    good_ind_all = good_ind_1 & good_ind_2 & good_ind_3 & good_ind_4 & good_ind_5 & good_ind_6 & good_ind_7 & good_ind_8 & good_ind_9
  

    # Max temps
    try:
        max_t_array = data_num[m].maxes[good_ind_all]       # array of max temps @ every 5-min interval
        max_t = max(max_t_array)                            # max temp value over entire mission
    except ValueError as msg:
        # add message
        print()
        continue
    index_max = np.argmax(max_t_array)                      # index of mission high
    time_of_max = data_num[m].times[index_max]              # time of mission high
    time_of_max_1 = Chandra.Time.secs2date(time_of_max)
    
    print('max temp =', max_t, '---', 'time of max =', time_of_max_1)
    
    # Min temps
    try:
        min_t_array = data_num[m].mins[good_ind_all]
        min_t = min(min_t_array)
    except ValueError:
        continue
    index_min = np.argmin(min_t_array)
    time_of_min = data_num[m].times[index_min]
    time_of_min_1 = Chandra.Time.secs2date(time_of_min)
    
    
    # If mission max temp occurred during anomaly, append to "anom_max_df"
    if (time_of_max > t_anom_start) and (time_of_max < t_anom_stop):
        msid_anom_max.append(m)
        anom_max_df.loc[len(anom_max_df)] = [m, tech_name, max_t, units, current_caution_high, current_warning_high,  time_of_max_1]
    
    # If mission min temp occurred during anomaly, append to "anom_min_df"
    elif (time_of_min > t_anom_start) and (time_of_min < t_anom_stop):
        msid_anom_min.append(m)
        anom_min_df.loc[len(anom_min_df)] = [m, tech_name, min_t, units, current_caution_high, current_warning_high, time_of_min_1]
        
    else:
        continue

print(msid_anom_max)
#print(max_t_array)


# In[37]:


len(anom_max_df.iloc[:,0])


# In[38]:


anom_max_df


# In[39]:


for ww in range(len(anom_min_df)):
    if anom_min_df.at[ww, 'Warning Low'] == None and anom_min_df.at[ww, 'Warning High'] == None:
        anom_min_df.at[ww, 'Warning Low'] = 'Not in TDB'
        anom_min_df.at[ww, 'Warning High'] = 'Not in TDB'
    else:
        continue
anom_min_df


# In[41]:


# Write Dataframe to .csv
anom_max_df.to_csv('C:/Users/christian.anderson/Documents/Anomalies/2023/2023_44_Safe_Mode/max_min_data/2023_044_anomaly_mission_maxes_v3.csv')
anom_min_df.to_csv('C:/Users/christian.anderson/Documents/Anomalies/2023/2023_44_Safe_Mode/max_min_data/2023_044_anomaly_mission_mins.csv')


# ### MSID Quick Check

# In[42]:


import plotly.io as pio
import plotly.express as px

data5 = fetch_eng.Msid('aacccdpt', '2023:044', '2023:052')
#data5 = maude_query('aacccdpt', '2023:040', '2023:041')

# Technical Name
try: 
    tech_name = data5.tdb.technical_name
        
except KeyError:
    tech_name = "Not in TDB"
    
# Units
try:
    units = data5.unit
    print(units)
except KeyError:
    units = "None Found"

data5.iplot()


# # LIMIT VIOLATION CATEGORIZATION 

# In[43]:


# Safe Mode Anomaly Time Range
t_anom_start = Chandra.Time.DateTime('2023:044:17:41:00').secs
t_anom_stop = Chandra.Time.DateTime('2023:055:00:00:00').secs

warning_limit_violations = pd.DataFrame(columns=['MSID', 'Technical Name', 'Max Temp', 'Units', 'Warning High', 'Time Spent Above Limit (Hours)'])
caution_limit_violations = pd.DataFrame(columns=['MSID', 'Technical Name', 'Max Temp', 'Units', 'Caution High', 'Time Spent Above Limit (Hours)'])

data_anomaly = {}

for msid_anom in num_msid:
    fetch_eng.data_source.set('maude') #cxc
    # when pulling from ska, default is 5min. For full res, stat=None
    data_anomaly[msid_anom] = fetch_eng.Msid(msid_anom, t_anom_start, t_anom_stop)
    data_anomaly[msid_anom].filter_bad(copy=True)
    
    print(msid_anom)
    
    # Technical Name
    try: 
        tech_name = data_anomaly[msid_anom].tdb.technical_name
        
    except KeyError:
        tech_name = "Not in TDB"
       
    
    # Units
    try:
        units = data_anomaly[msid_anom].unit
        print(units)
    except KeyError:
        units = "None Found"
    

    # Limits
    try:    
        safety_limits = pylimmon.get_mission_safety_limits(msid_anom)
    
    except IndexError:
        safety_limits = None
    
    
    if safety_limits:
        current_warning_high = safety_limits["warning_high"][-1]
        current_warning_low  = safety_limits["warning_low"][-1]
        current_caution_high = safety_limits["caution_high"][-1]
        current_caution_low  = safety_limits["caution_low"][-1]
        print(msid_anom, 'tdb warning high is:',current_warning_high, 'tdb caution high is', current_caution_high)

    elif safety_limits is None:
        
        try:
            current_warning_high = pylimmon.get_latest_glimmon_limits(msid_anom)["warning_high"]
            current_warning_low  = pylimmon.get_latest_glimmon_limits(msid_anom)["warning_low"]
            current_caution_high = pylimmon.get_latest_glimmon_limits(msid_anom)["caution_high"]
            current_caution_low = pylimmon.get_latest_glimmon_limits(msid_anom)["caution_low"]
            print(msid_anom, 'glimmon warning high is:',current_warning_high, 'glimmon caution high is:', current_caution_high)
            
        except TypeError:
            # add message
            current_warning_high = 9999
            current_warning_low  = -9999
            current_caution_high = 9999
            current_caution_low = -9999
    
    else:
        print('no tdb or glimmon limits for:', msid_anom)
    
    
    # Spacecraft Mode Transition Filters
    pad = 300 # seconds
    ind1 = data_anomaly[msid_anom].times < (CxoTime('2022:293:16:27:49.000').secs - pad) # 2023:293 Safe Mode transition
    ind2 = data_anomaly[msid_anom].times > (CxoTime('2022:293:16:27:49.000').secs + pad)
    ind3 = data_anomaly[msid_anom].times < (CxoTime('2023:044:17:41:07.000').secs - pad) # 2023:044 Safe Mode transition 
    ind4 = data_anomaly[msid_anom].times > (CxoTime('2023:044:17:41:07.000').secs + pad)
    ind5 = data_anomaly[msid_anom].times < (CxoTime('2023:045:03:32:39.000').secs - pad) # 2023:045 Swap to CTU-A
    ind6 = data_anomaly[msid_anom].times > (CxoTime('2023:045:03:32:39.000').secs + pad)
    ind7 = data_anomaly[msid_anom].times < (CxoTime('2023:047:07:33:47.000').secs - pad) # 2023:047 Safe Mode transition
    ind8 = data_anomaly[msid_anom].times > (CxoTime('2023:047:07:33:47.000').secs + pad)
    ind9 = data_anomaly[msid_anom].times < (CxoTime('2023:048:03:17:11.000').secs - pad) # 2023:048 Swap to CTU-A
    ind10 = data_anomaly[msid_anom].times > (CxoTime('2023:048:03:17:11.000').secs + pad)
    good_ind_1 = ind1 | ind2
    good_ind_2 = ind3 | ind4
    good_ind_3 = ind5 | ind6
    good_ind_4 = ind7 | ind8
    good_ind_5 = ind9 | ind10
    good_ind_6 = data_anomaly[msid_anom].vals < 250
    
    pad2 = 70 # seconds
    ind11 = data_anomaly[msid_anom].times < (CxoTime('2023:045:03:29:49.010').secs - pad2) # 2023:045 Thermal Control Disabled
    ind12 = data_anomaly[msid_anom].times > (CxoTime('2023:045:04:48:37.150').secs + pad2)
    ind13 = data_anomaly[msid_anom].times < (CxoTime('2023:047:07:33:33.163').secs - pad2) # 2023:047 Thermal Control Disabled
    ind14 = data_anomaly[msid_anom].times > (CxoTime('2023:047:07:34:48.125').secs + pad2)
    ind15 = data_anomaly[msid_anom].times < (CxoTime('2023:048:03:14:30.531').secs - pad2) # 2023:048 Thermal Control Disabled
    ind16 = data_anomaly[msid_anom].times > (CxoTime('2023:048:03:56:31.086').secs + pad2)
    good_ind_7 = ind11 | ind12
    good_ind_8 = ind13 | ind14
    good_ind_9 = ind15 | ind16
     
    all_good_ind = good_ind_1 & good_ind_2 & good_ind_3 & good_ind_4 & good_ind_5 & good_ind_6 & good_ind_7 & good_ind_8 & good_ind_9
    print(all_good_ind)
    

    # Calculate Warning Violation time duration: 
    warning_violation_bools = data_anomaly[msid_anom].vals[all_good_ind] > current_warning_high
    warning_time_spans = pylimmon.pylimmon.find_violation_time_spans(data_anomaly[msid_anom].times[all_good_ind], warning_violation_bools)
    time_bounds_warning = warning_time_spans[0]
    index_bounds_warning = warning_time_spans[1]
    t_tot_warning = np.sum([stop - start for start, stop in time_bounds_warning])
    t_tot_warning_hours = t_tot_warning*(1/60)*(1/60)
    
    # Calculate Caution Violation time duration:
    caution_violation_bools = data_anomaly[msid_anom].vals[all_good_ind] > current_caution_high
    caution_time_spans = pylimmon.pylimmon.find_violation_time_spans(data_anomaly[msid_anom].times[all_good_ind], caution_violation_bools)
    time_bounds_caution = caution_time_spans[0]
    index_bounds_caution = caution_time_spans[1]        
    t_tot_caution = np.sum([stop - start for start, stop in time_bounds_caution])
    t_tot_caution_hours = t_tot_caution*(1/60)*(1/60)
    
    print('WARNING DURATION IS:', t_tot_warning_hours)
    print('CAUTION DURATION IS:', t_tot_caution_hours)

    
    # Calculate Maximum temperature:
    try:
        max_temp_array = data_anomaly[msid_anom].vals[all_good_ind]       # array of max temps
        max_temp = max(max_temp_array)
        ind_max = np.argmax(max_temp_array)                               # index of anomaly high
        t_array = data_anomaly[msid_anom].times[all_good_ind]             # time of anomaly high
        t_max = t_array[ind_max]
        t_max_1 = Chandra.Time.secs2date(t_max)
        print('TIME OF MAX TEMP:', t_max_1)                                # max temp value over anomaly time range
    except ValueError:
        max_temp = 9999

    print('------------------------------------------')
    
    if t_tot_warning != 0:
        warning_limit_violations.loc[len(warning_limit_violations)] = [msid_anom, tech_name, max_temp, units, current_warning_high, t_tot_warning_hours]
    else:
        pass
    
    if t_tot_caution != 0:
        caution_limit_violations.loc[len(caution_limit_violations)] = [msid_anom, tech_name, max_temp, units, current_caution_high, t_tot_caution_hours]
    else:
        pass



# In[45]:


warning_limit_violations.to_csv('C:/Users/christian.anderson/Documents/Anomalies/2023/2023_44_Safe_Mode/max_min_data/WARNING_LIMIT_VIOLATIONS_v3.csv')
caution_limit_violations.to_csv('C:/Users/christian.anderson/Documents/Anomalies/2023/2023_44_Safe_Mode/max_min_data/CAUTION_LIMIT_VIOLATIONS_v3.csv')


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[19]:


g = pd.DataFrame(data_anomaly['TSSMIN'].vals[all_good_ind])
pd.set_option('display.max_rows', None)


# In[20]:


g


# In[21]:


print(len(data_anomaly['TSSMIN'].vals[all_good_ind]), len(data_anomaly['TSSMIN'].vals))


# In[ ]:




