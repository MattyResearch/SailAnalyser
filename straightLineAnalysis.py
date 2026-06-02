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
def extractStraightLines(gpsData, manoeuvreData, xCoeffs,yCoeffs,windowSize=20):
    '''
    Use manoeuvre data to remove manoeuvres from gpsData
    '''
    manoeuvre=0
    i=0
    localTWA = []
    straightLineData = gpsData.copy()
    while i < len(gpsData) and manoeuvre < len(manoeuvreData):
        skip = False
        if gpsData.iloc[i]['time'] > manoeuvreData.iloc[manoeuvre]['time']-dt.timedelta(seconds=windowSize/2):
            if gpsData.iloc[i]['time'] < manoeuvreData.iloc[manoeuvre]['time']+dt.timedelta(seconds=windowSize/2):
                straightLineData = straightLineData.drop(labels=i)
                skip = True # flag to skip assigning local wind direction to dropped dataframe rows
                # localWindAngle is now defined as the mean wind angle for that straight line.
                # This is calculated by taking the mean wind direction from the two nearest manoeuvres.
            else:
                if manoeuvre < len(manoeuvreData)-2:
                    manoeuvre+=1
        if not skip:
            tSpline = int((gpsData['time'][i]-gpsData['time'][0])/dt.timedelta(seconds=1))
            t1 = int((manoeuvreData.iloc[manoeuvre]['time']-gpsData['time'][0])/dt.timedelta(seconds=1))
            t2 = int((manoeuvreData.iloc[manoeuvre+1]['time']-gpsData['time'][0])/dt.timedelta(seconds=1))
            if gpsData.iloc[i]['time'] < manoeuvreData.iloc[0]['time']: # case before the first manoeuvre
                boatVelocity = f_1(t1,xCoeffs,yCoeffs,manoeuvreData.iloc[0]['spline'])
                if manoeuvreData.iloc[manoeuvre]['tack']:
                    pointTWA =  (np.pi+np.arctan2(boatVelocity[0],boatVelocity[1]))[0]# tack direction is directly head to wind
                else:
                    pointTWA = (np.arctan2(boatVelocity[0],boatVelocity[1]))[0]# gybe direction is directly downwind

            elif gpsData.iloc[i]['time'] > manoeuvreData['time'][len(manoeuvreData)-1]: # case after the last manoeuvre
                t1 = int((manoeuvreData.iloc[manoeuvre+1]['time']-gpsData['time'][0])/dt.timedelta(seconds=1))
                boatVelocity = f_1(t1,xCoeffs,yCoeffs,manoeuvreData.iloc[manoeuvre+1]['spline'])
                if manoeuvreData.iloc[manoeuvre+1]['tack']:
                    pointTWA =  (np.pi+np.arctan2(boatVelocity[0],boatVelocity[1]))[0]# tack direction is directly head to wind
                else:
                    pointTWA = (np.arctan2(boatVelocity[0],boatVelocity[1]))[0]# gybe direction is directly downwind

            else: # other cases where straight line is bounded by manoeuvres
                boatVelocityStart = f_1(t1,xCoeffs,yCoeffs,manoeuvreData.iloc[manoeuvre]['spline']) # manoeuvre pre-line
                if not manoeuvreData.iloc[manoeuvre]['tack']:
                    boatVelocityStart = -boatVelocityStart

                boatVelocityEnd = f_1(t2,xCoeffs,yCoeffs,manoeuvreData.iloc[manoeuvre+1]['spline']) # manoeuvre post-line
                if not manoeuvreData.iloc[manoeuvre+1]['tack']:
                    boatVelocityEnd = -boatVelocityEnd

                boatStartNorm = boatVelocityStart/np.linalg.norm(boatVelocityStart)
                boatEndNorm = boatVelocityEnd/np.linalg.norm(boatVelocityEnd)
                
                twaInterp = np.atan2(np.interp(tSpline,[t1,t2],[boatStartNorm[0][0],boatEndNorm[0][0]]),np.interp(tSpline,[t1,t2],[boatStartNorm[1][0],boatEndNorm[1][0]])) # interpolate unit vectors to find total wind angle

                pointTWA = twaInterp
            localTWA.append(np.remainder(pointTWA*180/np.pi,360))
        i+=1
    straightLineData = straightLineData.assign(localTWA=localTWA)
    return straightLineData

def straightLineInterpCubic(xCoeffs,yCoeffs,straightLineData,gpsTime, weatherData, nPoints=2):
    print("Calculating straight line performance...")
    # For each "straight line" spline, integrate the variables to find time-weighted averages.
    upwind = {'vmg':[],'twa':[],'speed':[]}
    downwind = {'vmg':[],'twa':[],'speed':[]}
    reaching = {'vmg':[],'twa':[],'speed':[]}
    t0 = gpsTime.iloc[0]  # time of first point
    t0aware = t0.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for spline in straightLineData.index:
        if spline == len(gpsTime)-1:
            break # no spline after last point
        t1 = (gpsTime[spline]-t0)/pd.Timedelta(seconds=1) # time at the start of spline since t0
        t2 = (gpsTime[spline+1]-t0)/pd.Timedelta(seconds=1) # time at the end of spline
        localWindAngle = straightLineData['localTWA'][spline]
        windVector = np.array([np.sin(np.deg2rad(localWindAngle)), np.cos(np.deg2rad(localWindAngle))]) # unit wind vector
        boatVector = (f(t2,xCoeffs,yCoeffs,spline)-f(t1,xCoeffs,yCoeffs,spline))/(t2-t1) # boat direction vector at point t - mean boat vector for spline
        boatAngle = np.rad2deg(np.arctan2(boatVector[0], boatVector[1])) # angle of boat vector
        pointVMG = np.dot(boatVector.T,windVector) # VMG at point t
        pointTWA = np.rad2deg(np.arctan2(np.sin(np.deg2rad(boatAngle-localWindAngle)),np.cos(np.deg2rad(boatAngle-localWindAngle))))
        pointSpeed = np.linalg.norm(boatVector) # speed at point t

        pointTWA=pointTWA-360 if pointTWA>180 else pointTWA
        pointTWA=abs(pointTWA)

        if np.arccos(np.dot(boatVector.T/np.linalg.norm(boatVector),windVector/np.linalg.norm(windVector)))< np.deg2rad(105):
            if np.arccos(np.dot(boatVector.T/np.linalg.norm(boatVector),windVector/np.linalg.norm(windVector)))< np.deg2rad(75):
                # Upwind
                upwind['vmg'].append(pointVMG[0])
                upwind['twa'].append(pointTWA[0])
                upwind['speed'].append(pointSpeed)
            else:
                # Reaching
                courseVector = np.array([np.sin(np.deg2rad(localWindAngle+90)), np.cos(np.deg2rad(localWindAngle+90))]) # unit wind vector
                pointVMG = abs(np.dot(boatVector.T,courseVector)) # VMG at point t
                reaching['vmg'].append(pointVMG[0])
                reaching['twa'].append(pointTWA[0])
                reaching['speed'].append(pointSpeed)
        else:
            # Downwind
            downwind['vmg'].append(pointVMG[0])
            downwind['twa'].append(pointTWA[0])
            downwind['speed'].append(pointSpeed)

    keys = ['vmg','twa','speed']
    for key in keys:
        upwind[key] = np.array(upwind[key])
        downwind[key] = np.array(downwind[key])
        reaching[key] = np.array(reaching[key])

    return upwind, downwind,reaching
    
def straightLineNoInterp(straightLineData, weatherData, nPoints=2000):
    print("Calculating straight line performance...")
    upwind = {'vmg':[],'twa':[],'speed':[]}
    downwind = {'vmg':[],'twa':[],'speed':[]}
    reaching = {'vmg':[],'twa':[],'speed':[]}
    timeInitialUnaware = straightLineData.iloc[0]['time']
    timeInitialAware = timeInitialUnaware.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for i in range(0, len(straightLineData)-1):
        cardinalWindAngle = np.interp((straightLineData.iloc[i]['time']-timeInitialUnaware)/dt.timedelta(seconds=1), (weatherData['date']-timeInitialAware)/dt.timedelta(seconds=1), weatherData['wind_direction_10m'])
        pointVMG = np.multiply(straightLineData.iloc[i]['speed'],np.cos(np.deg2rad(straightLineData.iloc[i]['angle']-cardinalWindAngle)))
        pointTWA=np.arctan2(np.sin(np.deg2rad(np.array(straightLineData.iloc[i]['angle']-cardinalWindAngle))),np.cos(np.deg2rad(np.array(straightLineData.iloc[i]['angle']-cardinalWindAngle))))
        pointTWA=np.rad2deg(pointTWA)
        pointTWA=pointTWA-360 if pointTWA>180 else pointTWA
        pointTWA=abs(pointTWA)
        localWindAngle = np.interp((gpsData.iloc[i]['time']-timeInitialUnaware)/pd.Timedelta(seconds=1), (weatherData['date']-timeInitialAware)/pd.Timedelta(seconds=1), weatherData['wind_direction_10m']) # spline midpoint
        windVector = np.array([np.sin(np.deg2rad(localWindAngle)), np.cos(np.deg2rad(localWindAngle))]) # unit wind vector
        boatVector = -np.array([straightLineData.iloc[i]['g_x'], straightLineData.iloc[i]['g_y']]) + np.array([straightLineData.iloc[i+1]['g_x'], straightLineData.iloc[i+1]['g_y']])

        if straightLineData.iloc[i+1].name.astype(int)-straightLineData.iloc[i].name.astype(int)==1: # check consecutive points
            if np.arccos(np.dot(boatVector.T/np.linalg.norm(boatVector),windVector/np.linalg.norm(windVector)))< np.deg2rad(105):
                if np.arccos(np.dot(boatVector.T/np.linalg.norm(boatVector),windVector/np.linalg.norm(windVector)))< np.deg2rad(75):
                    # Upwind
                    for j in range(0,int(np.floor((straightLineData.iloc[i+1]['time']-straightLineData.iloc[i]['time'])/pd.Timedelta(seconds=1)))):
                        upwind['vmg'].append(pointVMG)
                        upwind['twa'].append(pointTWA)
                        upwind['speed'].append(straightLineData.iloc[i]['speed'])
                else:
                    # Reaching
                    courseVector = np.array([np.sin(np.deg2rad(localWindAngle+90)), np.cos(np.deg2rad(localWindAngle+90))])
                    pointVMG = abs(np.dot(boatVector.T,courseVector)) # VMG at point t
                    for j in range(0,int(np.floor((straightLineData.iloc[i+1]['time']-straightLineData.iloc[i]['time'])/pd.Timedelta(seconds=1)))):
                        reaching['vmg'].append(pointVMG)
                        reaching['twa'].append(pointTWA)
                        reaching['speed'].append(straightLineData.iloc[i]['speed'])
            else:
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
    reaching['vmg'] = np.array(reaching['vmg'])
    reaching['twa'] = np.array(reaching['twa'])
    reaching['speed'] = np.array(reaching['speed'])
    return upwind, downwind, reaching

def violinPlotter(upwind, downwind,reaching,violinPlotDict,colour):
    print("Plotting straight line performance...")
    plottedPercentile = 95
    if len(upwind['vmg'])==0:
        upwind['vmg']=np.array([0])
        upwind['speed']=np.array([0])
        upwind['twa']=np.array([0])
    if len(downwind['vmg'])==0:
        downwind['vmg']=np.array([0])
        downwind['speed']=np.array([0])
        downwind['twa']=np.array([0])
    if len(reaching['vmg'])==0:
        reaching['vmg']=np.array([0])
        reaching['speed']=np.array([0])
        reaching['twa']=np.array([0])

    LimVMG=max(np.percentile(upwind['vmg'], plottedPercentile),np.percentile(reaching['vmg'], plottedPercentile),-np.percentile(downwind['vmg'], 100-plottedPercentile))
    LimSpeed=max(np.percentile(upwind['speed'], plottedPercentile),np.percentile(reaching['speed'], plottedPercentile),np.percentile(downwind['speed'], plottedPercentile))
    if violinPlotDict==None:
        violinFig, violinAx = plt.subplots(3, 3, figsize=(10, 8),sharey=False,sharex=True,layout='constrained')
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
    plots[6]=violinAx[0,2].violinplot(reaching['vmg'], showmedians=False,showextrema=False)
    plots[7]=violinAx[1,2].violinplot(reaching['speed'], showmedians=False,showextrema=False)
    plots[8]=violinAx[2,2].violinplot(-reaching['twa'], showmedians=False,showextrema=False)
    keys = ['vmg','speed','twa']

    for k in range(0,len(plots)):
        plot=plots[k]
        if k <3:
            mean=np.mean(upwind[keys[k]])
        elif k <6:
            mean=np.mean(downwind[keys[k-3]])
        else:
            mean=np.mean(reaching[keys[k-6]])
        if k == 3 or k==2 or k==8:
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
    violinAx[2,0].set_ylim(-75, 0)

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
    violinAx[2,1].set_ylim(105, 180)

    violinAx[0,2].set_title('Reaching')
    violinAx[0,2].set_xticks([])
    #violinAx[0,1].set_ylabel('VMG (m/s)')
    violinAx[0,2].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[0,2].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[0,2].minorticks_on()
    violinAx[0,2].set_ylim(0, lims['vmg'])

    #violinAx[1,1].set_ylabel('Boatspeed (m/s)')
    violinAx[1,2].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[1,2].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[1,2].minorticks_on()
    violinAx[1,2].set_ylim(0, lims['speed'])

    #violinAx[2,1].set_ylabel('TWA (deg)')
    violinAx[2,2].grid(True, which='major', linestyle='-', linewidth=0.5)
    violinAx[2,2].grid(True, which='minor', linestyle='--', linewidth=0.5,alpha=0.5)
    violinAx[2,2].minorticks_on()
    violinAx[2,2].set_ylim(-105, -75)

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
        upwind, downwind, reaching = straightLineNoInterp(straightLineData, weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,reaching,violinPlotDict if i>0 else None,colours[i])
        label = filenameList[i].rsplit('/', 1)[1]
        legends.append(label)
        legends.append("Mean") if i==0 else legends.append("")
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][2,1].legend(legends,prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')

    return violinPlotDict

def straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize,colours):
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
        straightLineData = extractStraightLines(gpsData, manoeuvreData, xCoeffs,yCoeffs,windowSize=windowSize)
        upwind, downwind,reaching = straightLineInterpCubic(xCoeffs,yCoeffs,straightLineData,gpsData['time'], weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,reaching,violinPlotDict if i>0 else None,colours[i][1])
        label = filenameList[i].rsplit('/', 1)[1].rsplit('.', 1)[0]
        legends.append(label)
        legends.append("Mean") if i==0 else legends.append("")
        straightLineDataDict[i] = {'upwind':upwind,'downwind':downwind,'reaching':reaching}
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][2,2].legend(legends,prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')
        
    return violinPlotDict,straightLineDataDict

def polarPlotter(filenameList,polarDataDict,polarPlotDict,colours,name,i):
    print("Plotting Polar Plots...")
    LimTWA = [0,180]
    LimSpeed = max(polarDataDict['medians']['r'])
    if polarPlotDict == None:
        polarFig = plt.figure(figsize=(10, 8),layout='constrained')
        polarAx = filenameList.copy()
        if len(filenameList)==1:
            polarAx=polarFig.add_subplot(1,1,1,projection='polar')
        else:
            polarAx=polarFig.add_subplot(1,1,1,projection='polar')
        polarFig.suptitle('Polar Performance Plots\nSpeed (m/s)', fontsize=16)
        lims={'twa':LimTWA,'speed':LimSpeed}
    else:
        lims=polarPlotDict['lims']
        polarFig=polarPlotDict['fig']
        polarAx=polarPlotDict['ax']
        #polarAx[i]=polarFig.add_subplot(1,2,2,projection='polar')
        lims['speed']=LimSpeed if lims['speed']<LimSpeed else lims['speed']
    if i==1:
        polarDataDict['TWAlist']=(polarDataDict['TWAlist']*-1)+np.ones(polarDataDict['TWAlist'].shape)*2*np.pi
        polarDataDict['medians']['theta']=(np.array(polarDataDict['medians']['theta'])*-1)+2*np.pi

    polarAx.scatter(polarDataDict['TWAlist'],polarDataDict['speedList'],c=colours,alpha=0.05,label=name)
    polarAx.plot(polarDataDict['medians']['theta'],polarDataDict['medians']['r'],c=colours,label=name)
    #polarAx[i].set_thetamin(0)
    #polarAx[i].set_thetamax(180)
    polarAx.set_rorigin(0)
    polarAx.set_theta_zero_location('N')
    polarAx.grid(True)
    polarAx.set_ylim(0,lims['speed'])
    polarAx.legend(prop={'size': 6},bbox_to_anchor=(0.5, -0.2), loc='upper center')
    
    polarPlotDict = {'lims':lims,'fig':polarFig,'ax':polarAx}
    return polarPlotDict

def polarPlotsCubic(filenameList,straightLineDataDict,colours):
    polarDataDict = {}
    polarPlotDict={}
    for i in range(len(filenameList)):
        speedList = [*straightLineDataDict[i]['upwind']['speed'],*straightLineDataDict[i]['reaching']['speed'],*straightLineDataDict[i]['downwind']['speed']]
        TWAList = [*straightLineDataDict[i]['upwind']['twa'],*straightLineDataDict[i]['reaching']['twa'],*straightLineDataDict[i]['downwind']['twa']]
        pairedDataset = pd.DataFrame({'speedList':speedList,'TWAlist':TWAList})
        pairedDataset = pairedDataset.sort_values('TWAlist') # order by TWA list
        step=1
        window=20
        theta = []
        r = []
        for angle in range(20,171,step):
            validPoints = []
            theta.append(np.deg2rad(angle))
            validPoints = pairedDataset[(pairedDataset['TWAlist']>=(angle-window/2))*(pairedDataset['TWAlist']<=(angle+window/2))]
            validPoints=validPoints[validPoints['speedList']>=1.5]
            if not validPoints.empty:
                r.append(np.nanmean(validPoints['speedList']))
            else:
                r.append(np.nan)
        medians={'theta':theta,'r':r}
        polarDataDict[i]={'speedList':speedList,'TWAlist':np.deg2rad(TWAList),'medians':medians}
        polarPlotDict = polarPlotter(filenameList,polarDataDict[i],polarPlotDict if i>0 else None,colours[i][1],filenameList[i].rsplit('/', 1)[1],i)
    return polarPlotDict,polarDataDict

if __name__ == "__main__":
    filenameList=["C:\\Users\\matth\\Documents\\SailAnalyser\\2025_06_15 OSC Race 1.gpx","C:\\Users\\matth\\Documents\\SailAnalyser\\2025_06_15 OSC Race 2.gpx"]
    #labels=[]
    windAngleList=[86,86]
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = "C:\\Users\\matth\\Documents\\SailAnalyser"
        filename = filenameList[i]
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename
        inputfile = directory + "\\" + filename

        windowSize = 20 # seconds either side
        manoeuvreLength=2 # seconds either side
        colours = ['blue','magenta']

        gpsData = read_xml(inputFile=filenameList[i],outputFile=outputfile)
        weatherDataBoatLocation = weatherDataAtBoat(gpsData)
        gpsData = calculateVelocity(gpsData)
        tacks, gybes,manoeuvreData = identifyManoeuvres(gpsData, weatherDataBoatLocation)
        straightLineData = extractStraightLines(gpsData, manoeuvreData, windowSize=windowSize)
        upwind, downwind,reaching = straightLineNoInterp(straightLineData, weatherDataBoatLocation)
        violinPlotDict=violinPlotter(upwind,downwind,reaching,violinPlotDict if 'violinPlotDict' in globals() else None,colours[i])
        #addLabel(colours,filenameList[i],i)
    #violinPlotDict['ax'][0,0].legend(*zip(*labels))
    violinPlotDict['ax'][0,1].legend([filenameList[0].rsplit('/', 1)[1],"Mean",filenameList[1].rsplit('/', 1)[1],"Mean"],prop={'size': 6})
    plt.show(block=True)