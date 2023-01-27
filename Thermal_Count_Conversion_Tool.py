#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import re
from urllib.request import urlopen
import pandas as pd
import requests
import numpy as np
import plotly.io as pio
import plotly.express as px
from cheta import fetch_eng


# In[2]:


# If you have jupyter_black installed, you can activate it here to help format your code:
# import jupyter_black

# jupyter_black.load(
#     lab=False,
#     line_length=120,
#     verbosity="DEBUG",
# )

from IPython.core.display import display, HTML

display(HTML("<style>.container { width:90% !important; }</style>"))
pio.renderers.default = "notebook"


# In[3]:


def CtoF(cs):
    try:
        return np.array([c * 1.8 + 32 for c in cs])
    except TypeError:
        return cs * 1.8 + 32


def FtoC(cs):
    try:
        return np.array([(c - 32) / 1.8 for c in cs])
    except TypeError:
        return (cs - 32) / 1.8


def maude_query(msid, t1, t2, all_points=True):
    # (base URL)/<CHANNEL>/<querytype>.<format>?<query options separated by &>
    # https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m=STAT_1DAY_MIN_OOBTHR18&ts=2015.001&tp=2016.001

    # All Points
    if all_points is True:
        # All Points
        base_url_constructor = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m={}&ts={}&tp={}&ap=t"
    else:
        # Reduced Points
        base_url_constructor = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m={}&ts={}&tp={}"

    url = base_url_constructor.format(msid.lower(), t1, t2)

    try:
        jsondata = requests.get(url).json()
        data = pd.DataFrame(
            {
                "date": pd.to_datetime(jsondata["data-fmt-1"]["times"], format="%Y%j%H%M%S%f"),
                "data": jsondata["data-fmt-1"]["values"],
            }
        )
        data["data"] = pd.to_numeric(data["data"])
    except:
        data = pd.DataFrame(
            {
                "date": [
                    None,
                ],
                "data": [
                    None,
                ],
            }
        )

    return data


def ska_query(msid, t1, t2, stat="5min"):
    data = fetch_eng.Msid(msid, t2, t2, stat=stat)
    return pd.DataFrame({"date": data.times, "data": data.vals})


def gen_plot_data(msid, fill_color, line_color, group):
    min_msid = "STAT_1DAY_MIN_" + msid
    max_msid = "STAT_1DAY_MAX_" + msid

    return {
        "type": "scattergl",
        "x": pd.concat([maude_data[min_msid]["date"], maude_data[max_msid]["date"][::-1]], axis=0),
        "y": maude_data[min_msid]["data"] + maude_data[max_msid]["data"][::-1],
        "name": msid,
        "fill": "toself",
        "fill_color": fill_color,
        "line_color": line_color,
        "legendgroup": group,
    }


def gen_min_plot_data(msid, line_color, group):
    min_msid = "STAT_1DAY_MIN_" + msid
    print(np.median(maude_data[min_msid]["data"]))

    showlegend = True if maude_data[min_msid]["data"][0] < 55 else False
    if np.abs((np.median(maude_data[min_msid]["data"])) - 50) < 5:
        group = "Heaters: 50F"
        title = "Regions set to 50F"
        color = line_color

    elif np.median(maude_data[min_msid]["data"]) < 45:
        group = "Cold Regions"
        title = "Cold Regions"
        color = "rgba(0, 0, 200, 0.5)"
    else:
        color = line_color
        group = "Warm Regions"
        title = "Warm Regions"

    return {
        "type": "scatter",
        "x": maude_data[min_msid]["date"],
        "y": maude_data[min_msid]["data"],
        "name": msid,
        "line_color": color,
        "legendgroup": group,
        "showlegend": showlegend,
    }


def gen_full_plot_data(msid, line_color, group, showlegend):
    return {
        "type": "scattergl",
        "x": maude_data[msid]["date"],
        "y": maude_data[msid]["data"],
        "name": msid,
        "line_color": line_color,
        "legendgroup": group,
        "showlegend": showlegend,
    }


def hex_to_rgba(hexstr, opacity):
    hexstr = hexstr.lstrip("#")
    hlen = len(hexstr)
    rgba = [int(hexstr[i : i + int(hlen / 3)], 16) for i in range(0, hlen, int(hlen / 3))] + [
        opacity,
    ]
    return tuple(rgba)


time_axis_format = [
    dict(dtickrange=[None, 1000], value="%H:%M:%S.%L\n%Y:%j"),
    dict(dtickrange=[1000, 60000], value="%H:%M:%S\n%Y:%j"),
    dict(dtickrange=[60000, 86400000], value="%H:%M\n%Y:%j"),
    dict(dtickrange=[86400000, "M12"], value="%e %b\n%Y:%j"),
    dict(dtickrange=["M12", None], value="%Y"),
]

title_format = {"family": "Arial", "size": 32, "color": "#7f7f7f"}

axis_format = {"family": "Arial", "size": 20, "color": "#7f7f7f"}

y_label_format = {"family": "Arial", "size": 24, "color": "#7f7f7f"}

colors = px.colors.qualitative.D3


# ## Polynomial Calibration Conversion Function (Counts to Temp)

# In[4]:


tdb_poly_cal = pd.read_csv('C:/Users/christian.anderson/Documents/TDB_POLY_CAL.csv')


# In[5]:


tdb_poly_cal


# In[6]:


max(tdb_poly_cal['DEG'])


# In[7]:


def calc_poly(counts, poly, deg):

    if deg == 0:
        eq = poly["COEF0"][0]
        
    elif deg == 1:
        eq = poly["COEF0"][0] + poly["COEF1"][0]
        
    elif deg == 2:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 
        
    elif deg == 3:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3
        
    elif deg == 4:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4
        
    elif deg == 5:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4 + poly["COEF5"] * counts**5
        
    elif deg == 6:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4 + poly["COEF5"] * counts**5 + poly["COEF6"] * counts**6
        
    elif deg == 7:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4 + poly["COEF5"] * counts**5 + poly["COEF6"] * counts**6 + poly["COEF7"] * counts**7
        
    elif deg == 8:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4 + poly["COEF5"] * counts**5 + poly["COEF6"] * counts**6 + poly["COEF7"] * counts**7 + poly["COEF8"] * counts**8
    
    elif deg == 9:
        eq = poly["COEF0"][0] + poly["COEF1"][0] * counts + poly["COEF2"][0] * counts**2 + poly["COEF3"][0] * counts**3 + poly["COEF4"] * counts**4 + poly["COEF5"] * counts**5 + poly["COEF6"] * counts**6 + poly["COEF7"] * counts**7 + poly["COEF8"] * counts**8 + poly["COEF9"] * counts**9
        
    else:
        pass

    return eq
        
        


# In[8]:


def convert_to_temp(msid):
    
    t1 = "2022:296:00:00:00.000"
    t2 = "2022:298:00:00:00.000"

    ska_data = fetch_eng.Msid(msid, t1, t2)
    coef = ska_data.tdb.Tpc[ska_data.tdb.Tpc["CALIBRATION_SET_NUM"] == 1]

    # Get Counts
    maude_data = maude_query("RAW_" + msid, t1, t2)
    
    print("Raw Counts:")
    print(maude_data["data"].values)
    print( )
    print("converting...")
    print( )

    # Find Degree of the polynomial from TDB_tpc
    for i in range(len(tdb_poly_cal)):
        if tdb_poly_cal.at[i, 'MSID'] == msid:
            deg = tdb_poly_cal.at[i, 'DEG']

        
    temp_val = calc_poly(maude_data["data"].values, coef, deg)
    print("Temperature Values:")
    print(temp_val)
    
    return temp_val    


# In[9]:


t_OOBTHR08 = convert_to_temp("4HLL2BT")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# ## Point Pair Conversion Function (Counts to Temp) 

# In[10]:


tdb_point_pair = pd.read_csv('C:/Users/christian.anderson/Documents/TDB_POINT_PAIR.csv')
tdb_point_pair


# In[11]:


def point_pair(msid):
    
    t1 = "2022:296:00:00:00.000"
    t2 = "2022:298:00:00:00.000"
    
    # Get Counts
    maude_data = maude_query("RAW_" + msid, t1, t2)
    counts = maude_data["data"].values
    
    print("Raw Counts:")
    print(counts)
    print( )

    # Initialize dataframe for desired MSID data only:
    single_msid_df = pd.DataFrame(columns=["MSID", "CSN", "SN", "RC", "EUV"])

    for j in range(len(tdb_point_pair)):
        
        MSID = tdb_point_pair.at[j, "MSID"]
        CSN = tdb_point_pair.at[j, "CALIBRATION_SET_NUM"]
        SN = tdb_point_pair.at[j, "SEQUENCE_NUM"]
        RC = tdb_point_pair.at[j, "RAW_COUNT"]
        EUV = tdb_point_pair.at[j, "ENG_UNIT_VALUE"]
        
        if MSID == msid:
            single_msid_df.loc[len(single_msid_df)] = [MSID, CSN, SN, RC, EUV]
        else:
            continue

    # Sort the dataframe based on Sequence Number in ascending order:
    single_msid_sorted_df = single_msid_df.sort_values('SN')
    
    print("Sorted Point Pair Data for", msid, ":")
    print(single_msid_sorted_df)
    print( )
    print("converting...")
    print( )

    # Find temperature values by interpolating sorted dataframe for the given count values:
    interpolate = np.interp(counts, single_msid_sorted_df["RC"], single_msid_sorted_df["EUV"])
    
    print("Temperature Values:")
    
    return interpolate


# In[12]:


point_pair("TMZP_CNT")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# ## Thermal Health Check MSID Calculations 

# ### HRMA Strut 

# In[15]:


hrma = [
    "OOBTHR02", 
    "OOBTHR03",
    "OOBTHR04",
    "OOBTHR05",
    "OOBTHR06",
    "OOBTHR07"
]

t1 = "2022:296:00:00:00.000"
t2 = "2022:298:00:00:00.000"
maude_data = {}
for msid2 in hrma:
    maude_data[msid2] = maude_query("RAW_" + msid2, t1, t2)


# In[16]:


plot_object = {
    "data": [gen_full_plot_data(msid2, "rgba(50, 50, 0, 0.3)", msid2, showlegend=True) for msid2 in hrma],
    "layout": {
        "hovermode": "closest",
        "autosize": False,
        "width": 1900,
        "height": 700,
        "yaxis": {
            "title": {"text": "Counts", "font": y_label_format},
            "domain": [0.01, 0.99],
            "position": 0.01,
            "automargin": True,
            "range": [0, 1050],
            "tickfont": axis_format,
        },
        "xaxis": {"tickformatstops": time_axis_format, "domain": [0.02, 0.98], "position": 0, "tickfont": axis_format},
        "title": {
            "text": "HRMA Trends",
            "font": title_format,
            "y": 0.9,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
        },
        "legend": {
            "x": 1.05,
            "y": 0.12,
            "font": {"family": "sans-serif", "size": 12, "color": "black"},
        },
        "template": "none",
        "annotations": None,
        "shapes": None,
    },
    "font": {"size": 32, "color": "#7f7f7f"},
}


pio.show(plot_object)


# In[ ]:


min_count = []
max_count = []

for msid2 in hrma:
    min_count.append(maude_data2[msid2]["data"].min())
    max_count.append(maude_data2[msid2]["data"].max())
    
min_c = min(min_count)

max_c = max(max_count)

print("Observed count range is:", max_c - min_c)


# In[ ]:




