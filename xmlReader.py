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

    xtree = et.parse(inputFile)
    xroot = xtree.getroot()
    ns = {'topografix':'http://www.topografix.com/GPX/1/1'}

    for track in xroot.findall("./topografix:trk",ns):
        for trackSegment in track.findall("./topografix:trkseg",ns):
            for trackPoint in trackSegment.findall("./topografix:trkpt",ns):
                g_time = trackPoint.find('./topografix:time',ns).text
                g_lat = Decimal(trackPoint.attrib.get("lat"))
                g_lon = Decimal(trackPoint.attrib.get("lon"))
        
                rows.append({"time": g_time, "lat": g_lat, "lon": g_lon})

    gps_out = pd.DataFrame(rows, columns=df_cols)
    gps_out['time'] = pd.to_datetime(gps_out['time'], format='%Y-%m-%dT%H:%M:%S.%fZ')
    gps_out['g_x'] = np.float32((gps_out['lon']-gps_out['lon'][0])*110922) # metres
    gps_out['g_y'] = np.float32((gps_out['lat']-gps_out['lat'][0])*110922) # metres

    #gps_out.to_csv(outputFile, index=False)
    print("Data imported successfully.")

    return gps_out

if __name__ == "__main__":
    directory = "C:\\Users\\matth\\Documents\\SailAnalyser"
    filename = "activity_19011820231.gpx"
    outputfilename = "gps_data.csv"
    outputfile = directory + "\\" + outputfilename
    inputfile = directory + "\\" + filename

    gpsData = read_xml(inputfile,outputfile)