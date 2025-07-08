import matplotlib.pyplot as plt
from xmlReader import read_xml

def plotTrack(gpsData):
    plt.plot(gpsData['g_x'], gpsData['g_y'])
    plt.title('GPS Track')
    plt.xlabel('Distance from start (m)')
    plt.ylabel('Distance from start (m)')
    plt.axis('equal')
    plt.axis('square')
    plt.tick_params(axis='both', which='major', labelsize=10)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.show()

if __name__ == "__main__":
    directory = "C:\\Users\\matth\\Documents\\SailAnalyser"
    filename = "activity_19011820231.gpx"
    outputfilename = "gps_data.csv"
    outputfile = directory + "\\" + outputfilename
    inputfile = directory + "\\" + filename

    gpsData = read_xml(inputFile=inputfile,outputFile=outputfile)
    plotTrack(gpsData)