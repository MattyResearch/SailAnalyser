import xml as xml
import xml.etree.ElementTree as et 
import pandas as pd
from decimal import Decimal,getcontext
import numpy as np

def read_xml(inputFile,outputFile):
    """
    Reads Garmin input file and returns data to Python format.
    """
    print("Importing data...")
    getcontext().prec = 30

    df_cols = ['time','lat','lon']
    rows = []

    try:
        xtree = et.parse(inputFile)
        
    except:
        murbitHotFix(inputFile)
        xtree = et.parse(inputFile)

    xroot = xtree.getroot()
    ns = {'topografix':'http://www.topografix.com/GPX/1/1'}
    if xroot.get('creator') == 'murbit SailAnalyser hotfix':
        timeformat = 'ISO8601'
    else:
        timeformat = '%Y-%m-%dT%H:%M:%S.%fZ'
    for track in xroot.findall("./topografix:trk",ns):
        for trackSegment in track.findall("./topografix:trkseg",ns):
            for trackPoint in trackSegment.findall("./topografix:trkpt",ns):
                g_time = trackPoint.find('./topografix:time',ns).text
                g_lat = Decimal(trackPoint.attrib.get("lat"))
                g_lon = Decimal(trackPoint.attrib.get("lon"))
        
                rows.append({"time": g_time, "lat": g_lat, "lon": g_lon})

    gps_out = pd.DataFrame(rows, columns=df_cols)
    gps_out['time'] = pd.to_datetime(gps_out['time'], format=timeformat)
    gps_out['g_x'] = np.float32((gps_out['lon']-gps_out['lon'][0])*110922) # metres
    gps_out['g_y'] = np.float32((gps_out['lat']-gps_out['lat'][0])*110922) # metres

    #gps_out.to_csv(outputFile, index=False)
    print("Data imported successfully.")

    return gps_out

def murbitHotFix(inputFile):
    """
    Fixes the murbit GPX Tracker file by adding quotation marks after latitude entry.
    """
    with open(inputFile, 'r') as file:
        content = file.read()
        file.close()
        contentPass =0
        while contentPass <2:
            for charpos in range(len(content)-5):
                if content[charpos] == '>' and content[charpos+1] == '<' and content[charpos+2] == 'e' and content[charpos+3] == 'l' and content[charpos+4] == 'e':
                    if content[charpos-1] == '"':
                        # Already fixed
                        continue
                    content = content[:charpos] + '"' + content[charpos:]

                if content[charpos] == '"' and content[charpos+1] == 'l' and content[charpos+2] == 'a' and content[charpos+3] == 't' and content[charpos+4] == '=':
                    content = content[:charpos+1]+' '+ content[charpos+1:]

                if content[charpos:charpos+9]== '</speed>\n':
                    content = content[:charpos]+ ' </speed></trkpt>\n' + content[charpos+9:]
            
            tagContent = content.replace('murbit GPX Tracker','murbit SailAnalyser hotfix')
            contentPass +=1
        
    with open(inputFile, 'w',encoding="utf-8") as file:
        file.write(tagContent)
        file.close()

if __name__ == "__main__":
    directory = "C:\\Users\\matth\\Downloads"
    filename = "moGPXTracker_20250709033732.gpx"
    outputfilename = "gps_data.csv"
    outputfile = directory + "\\" + outputfilename
    inputfile = directory + "\\" + filename

    gpsData = read_xml(inputfile,outputfile)