import pandas as pd
import numpy as np
from xmlReader import read_xml
from manoeuvreIdentifier import calculateVelocity, identifyManoeuvres,doubleCheck,identifyManoeuvresCubic
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from performancePlotters import tackPlots, gybePlots
from historicalWeatherData import weatherDataAtBoat
from cubicInterpolation import f,f_1,cubicSplineInterpolation

'''
These functions take the straight line portions of the data and draw violin plots to show performance.
'''
def extractStraightLines(gpsData, manoeuvreData, windowSize=20):
    '''
    Use manoeuvre data to remove manoeuvres from gpsData
    '''
    manoeuvre=0
    i=0
    straightLineData = gpsData.copy()
    while i < len(gpsData) and manoeuvre < len(manoeuvreData):
        if gpsData.iloc[i]['time'] > manoeuvreData.iloc[manoeuvre]['time']-dt.timedelta(seconds=windowSize/2):
            if gpsData.iloc[i]['time'] < manoeuvreData.iloc[manoeuvre]['time']+dt.timedelta(seconds=windowSize/2):
                straightLineData = straightLineData.drop(labels=i)
            else:
                manoeuvre+=1
        i+=1
    return straightLineData

def straightLineInterpCubic(xCoeffs,yCoeffs,straightLineData,gpsTime, weatherData, nPoints=2):
    print("Calculating straight line performance...")
    # For each "straight line" spline, integrate the variables to find time-weighted averages.
    upwind = {'vmg':[],'twa':[],'speed':[]}
    downwind = {'vmg':[],'twa':[],'speed':[]}
    t0 = gpsTime.iloc[0]  # time of first point
    t0aware = t0.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for spline in straightLineData.index:
        if spline == len(gpsTime)-1:
            break # no spline after last point
        t1 = (gpsTime[spline]-t0)/pd.Timedelta(seconds=1) # time at the start of spline since t0
        t2 = (gpsTime[spline+1]-t0)/pd.Timedelta(seconds=1) # time at the end of spline
        localWindAngle = np.interp((t1+t2)/2, (weatherData['date']-t0aware)/pd.Timedelta(seconds=1), weatherData['wind_direction_10m']) # spline midpoint
        windVector = np.array([np.sin(np.deg2rad(localWindAngle)), np.cos(np.deg2rad(localWindAngle))]) # unit wind vector
        boatVector = (f(t2,xCoeffs,yCoeffs,spline)-f(t1,xCoeffs,yCoeffs,spline))/(t2-t1) # boat direction vector at point t
        boatAngle = np.rad2deg(np.arctan2(boatVector[0], boatVector[1])) # angle of boat vector
        pointVMG = np.dot(boatVector.T,windVector) # VMG at point t
        pointTWA = np.rad2deg(np.arctan2(np.sin(np.deg2rad(boatAngle-localWindAngle)),np.cos(np.deg2rad(boatAngle-localWindAngle))))
        pointSpeed = np.linalg.norm(boatVector) # speed at point t

        pointTWA=pointTWA-360 if pointTWA>180 else pointTWA
        pointTWA=abs(pointTWA)

        if pointVMG > 0:
            # Upwind
            upwind['vmg'].append(pointVMG[0])
            upwind['twa'].append(pointTWA[0])
            upwind['speed'].append(pointSpeed)
        else:
            # Downwind
            downwind['vmg'].append(pointVMG[0])
            downwind['twa'].append(pointTWA[0])
            downwind['speed'].append(pointSpeed)

    keys = ['vmg','twa','speed']
    for key in keys:
        upwind[key] = np.array(upwind[key])
        downwind[key] = np.array(downwind[key])

    return upwind, downwind
    
def straightLineNoInterp(straightLineData, weatherData, nPoints=2000):
    print("Calculating straight line performance...")
    upwind = {'vmg':[],'twa':[],'speed':[]}
    downwind = {'vmg':[],'twa':[],'speed':[]}
    timeInitialUnaware = straightLineData.iloc[0]['time']
    timeInitialAware = timeInitialUnaware.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for i in range(0, len(straightLineData)-1):
        cardinalWindAngle = np.interp((straightLineData.iloc[i]['time']-timeInitialUnaware)/dt.timedelta(seconds=1), (weatherData['date']-timeInitialAware)/dt.timedelta(seconds=1), weatherData['wind_direction_10m'])
        pointVMG = np.multiply(straightLineData.iloc[i]['speed'],np.cos(np.deg2rad(straightLineData.iloc[i]['angle']-cardinalWindAngle)))
        pointTWA=np.arctan2(np.sin(np.deg2rad(np.array(straightLineData.iloc[i]['angle']-cardinalWindAngle))),np.cos(np.deg2rad(np.array(straightLineData.iloc[i]['angle']-cardinalWindAngle))))
        pointTWA=np.rad2deg(pointTWA)
        pointTWA=pointTWA-360 if pointTWA>180 else pointTWA
        pointTWA=abs(pointTWA)
        if pointVMG > 0 and straightLineData.iloc[i+1].name.astype(int)-straightLineData.iloc[i].name.astype(int)==1:
            # Upwind
            for j in range(0,int(np.floor((straightLineData.iloc[i+1]['time']-straightLineData.iloc[i]['time'])/pd.Timedelta(seconds=1)))):
                upwind['vmg'].append(pointVMG)
                upwind['twa'].append(pointTWA)
                upwind['speed'].append(straightLineData.iloc[i]['speed'])
        elif straightLineData.iloc[i+1].name.astype(int)-straightLineData.iloc[i].name.astype(int)==1:
            # Downwind
            for j in range(0,int(np.floor((straightLineData.iloc[i+1]['time']-straightLineData.iloc[i]['time'])/pd.Timedelta(seconds=1)))):
                downwind['vmg'].append(pointVMG)
                downwind['twa'].append(pointTWA)
                downwind['speed'].append(straightLineData.iloc[i]['speed'])

    upwind['vmg'] = np.array(upwind['vmg'])
    upwind['twa'] = np.array(upwind['twa'])
    upwind['speed'] = np.array(upwind['speed'])
    downwind['vmg'] = np.array(downwind['vmg']) 
    downwind['twa'] = np.array(downwind['twa'])
    downwind['speed'] = np.array(downwind['speed'])
    return upwind, downwind

def violinPlotter(upwind, downwind,violinPlotDict,colour):
    print("Plotting straight line performance...")
    plottedPercentile = 95
    LimVMG=max(np.percentile(upwind['vmg'], plottedPercentile),-np.percentile(downwind['vmg'], 100-plottedPercentile))
    LimSpeed=max(np.percentile(upwind['speed'], plottedPercentile),np.percentile(downwind['speed'], plottedPercentile))
    if violinPlotDict==None:
        violinFig, violinAx = plt.subplots(3, 2, figsize=(10, 8),sharey=False,sharex=True,layout='constrained')
        violinFig.suptitle('Straight Line Performance', fontsize=16)
        lims={'vmg':LimVMG,'speed':LimSpeed}
    else:
        lims=violinPlotDict['lims'] 
        violinFig=violinPlotDict['fig']
        violinAx=violinPlotDict['ax']
        lims['vmg']=LimVMG if lims['vmg']<LimVMG else lims['vmg']
        lims['speed']=LimSpeed if lims['speed']<LimSpeed else lims['speed']
    
    plots={}
    plots[0]=violinAx[0,0].violinplot(upwind['vmg'], showmedians=False,showextrema=False)
    plots[1]=violinAx[1,0].violinplot(upwind['speed'], showmedians=False,showextrema=False)
    plots[2]=violinAx[2,0].violinplot(-upwind['twa'], showmedians=False,showextrema=False)
    plots[3]=violinAx[0,1].violinplot(-downwind['vmg'], showmedians=False,showextrema=False)
    plots[4]=violinAx[1,1].violinplot(downwind['speed'], showmedians=False,showextrema=False)
    plots[5]=violinAx[2,1].violinplot(downwind['twa'], showmedians=False,showextrema=False)
    keys = ['vmg','speed','twa']

    for k in range(0,len(plots)):
        plot=plots[k]

        mean=np.mean(upwind[keys[k]] if k<3 else downwind[keys[k-3]])
        if k == 3 or k==2:
            mean=-mean
        for pc in plot['bodies']:
            pc.set_facecolor(colour)
            pc.set_edgecolor('black')
            pc.set_alpha(0.5)
        violinAx[np.remainder(k,3),int(np.floor(k/3))].scatter(1,mean,marker='o',color=colour,edgecolor='black',zorder=10,label='Means')

    violinAx[0,0].set_title('Upwind')
    violinAx[0,0].set_xticks([])
    violinAx[0,0].set_ylabel('VMG (m/s)')
    violinAx[0,0].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[0,0].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[0,0].minorticks_on()
    violinAx[0,0].set_ylim(0, lims['vmg'])

    violinAx[1,0].set_ylabel('Boatspeed (m/s)')
    violinAx[1,0].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[1,0].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[1,0].minorticks_on()
    violinAx[1,0].set_ylim(0, lims['speed'])

    violinAx[2,0].set_ylabel('TWA (deg)')
    violinAx[2,0].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[2,0].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[2,0].minorticks_on()
    violinAx[2,0].set_ylim(-90, 0)

    violinAx[0,1].set_title('Downwind')
    violinAx[0,1].set_xticks([])
    #violinAx[0,1].set_ylabel('VMG (m/s)')
    violinAx[0,1].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[0,1].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[0,1].minorticks_on()
    violinAx[0,1].set_ylim(0, lims['vmg'])

    #violinAx[1,1].set_ylabel('Boatspeed (m/s)')
    violinAx[1,1].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[1,1].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[1,1].minorticks_on()
    violinAx[1,1].set_ylim(0, lims['speed'])

    #violinAx[2,1].set_ylabel('TWA (deg)')
    violinAx[2,1].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[2,1].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[2,1].minorticks_on()
    violinAx[2,1].set_ylim(90, 180)

    violinPlotDict={'lims':lims,'fig':violinFig,'ax':violinAx}

    return violinPlotDict
'''
def addLabel(colours,name,j):
    labels.append([mpatches.Patch(color=colours[j]),name])
'''


def straightLineAnalysisMain(filenameList, windAngleList,analysedDataDict):
    legends = []
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = filenameList[i].rsplit('/', 1)[0]
        filename = filenameList[i]
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename

        windowSize = 20 # seconds either side
        manoeuvreLength=2 # seconds either side
        colours = ['blue','magenta']
        if 'analysedDataDict' not in locals():
            gpsData = read_xml(inputFile=filename,outputFile=outputfile)
            weatherDataBoatLocation = weatherDataAtBoat(gpsData)
            gpsData = calculateVelocity(gpsData)
            tacks, gybes,manoeuvreData = identifyManoeuvres(gpsData, weatherDataBoatLocation)
        else:
            gpsData=analysedDataDict[i]['gpsData']
            weatherDataBoatLocation=analysedDataDict[i]['weatherDataBoatLocation']
            manoeuvreData=analysedDataDict[i]['manoeuvreData']
        straightLineData = extractStraightLines(gpsData, manoeuvreData, windowSize=windowSize)
        upwind, downwind = straightLineNoInterp(straightLineData, weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,violinPlotDict if i>0 else None,colours[i])
        label = filenameList[i].rsplit('/', 1)[1]
        legends.append(label)
        legends.append("Mean") if i==0 else legends.append("")
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][2,1].legend(legends,prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')

    return violinPlotDict

def straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize):
    legends = []
    straightLineDataDict = {}
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = filenameList[i].rsplit('/', 1)[0]
        filename = filenameList[i]
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename

        manoeuvreLength=2 # seconds either side
        colours = ['blue','magenta']
        if 'analysedDataDict' not in locals():
            gpsData = read_xml(inputFile=filename,outputFile=outputfile)

            xCoeffs = cubicSplineInterpolation(gpsData, 'g_x') # create surrogate cubic splines
            yCoeffs = cubicSplineInterpolation(gpsData, 'g_y')
            
            weatherDataBoatLocation = weatherDataAtBoat(gpsData)
            gpsData = calculateVelocity(gpsData)
            tacks, gybes,manoeuvreData = identifyManoeuvresCubic(gpsData, weatherDataBoatLocation)
        else:
            gpsData=analysedDataDict[i]['gpsData']
            weatherDataBoatLocation=analysedDataDict[i]['weatherDataBoatLocation']
            manoeuvreData=analysedDataDict[i]['manoeuvreData']
            xCoeffs=analysedDataDict[i]['xCoeffs']
            yCoeffs=analysedDataDict[i]['yCoeffs']
        straightLineData = extractStraightLines(gpsData, manoeuvreData, windowSize=windowSize)
        upwind, downwind = straightLineInterpCubic(xCoeffs,yCoeffs,straightLineData,gpsData['time'], weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,violinPlotDict if i>0 else None,colours[i])
        label = filenameList[i].rsplit('/', 1)[1].rsplit('.', 1)[0]
        legends.append(label)
        legends.append("Mean") if i==0 else legends.append("")
        straightLineDataDict[i] = {'upwind':upwind,'downwind':downwind}
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][2,1].legend(legends,prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')
        
    return violinPlotDict,straightLineDataDict

if __name__ == "__main__":
    filenameList=["2025_06_15 OSC Race 1","2025_06_15 OSC Race 2"]
    #labels=[]
    windAngleList=[86,86]
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = "C:\\Users\\matth\\Documents\\SailAnalyser"
        filename = filenameList[i]+".gpx"
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename
        inputfile = directory + "\\" + filename

        windowSize = 20 # seconds either side
        manoeuvreLength=2 # seconds either side
        colours = ['blue','magenta']

        gpsData = read_xml(inputFile=inputfile,outputFile=outputfile)
        weatherDataBoatLocation = weatherDataAtBoat(gpsData)
        gpsData = calculateVelocity(gpsData)
        tacks, gybes,manoeuvreData = identifyManoeuvresCubic(gpsData, weatherDataBoatLocation)
        straightLineData = extractStraightLines(gpsData, manoeuvreData, windowSize=windowSize)
        upwind, downwind = straightLineNoInterp(straightLineData, weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,violinPlotDict if 'violinPlotDict' in globals() else None,colours[i])
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][0,1].legend([filenameList[0].rsplit('/', 1)[1],"Mean",filenameList[1].rsplit('/', 1)[1],"Mean"],prop={'size': 6})
    plt.show(block=True)