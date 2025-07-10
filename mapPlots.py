import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from xmlReader import read_xml
from cubicInterpolation import find_neighbours
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from tackAnalysis import analyseManoeuvresCubicInterp
from manoeuvreIdentifier import identifyManoeuvres
from straightLineAnalysis import straightLineAnalysisCubic
from cubicInterpolation import f_1
'''
map = Basemap(llcrnrlon=3.75,llcrnrlat=39.75,urcrnrlon=4.35,urcrnrlat=40.15, epsg=5520)
#http://server.arcgisonline.com/arcgis/rest/services

map.arcgisimage(service='ESRI_Imagery_World_2D', xpixels = 1500, verbose= True)
plt.show()
'''


def plotMaps(filenameList,analysedDataDict):
    '''
    Plot the GPS data track, adding points for each manoeuvre and arrows for wind direction and direction of travel.
    '''
    mapFig, mapAx = plt.subplots(1, len(filenameList), figsize=(10, 8), sharex=False,layout='constrained')
    for i in range(0,len(filenameList)):
        gpsData = analysedDataDict[i]['gpsData']
        manoeuvreData = analysedDataDict[i]['manoeuvreData']
        weatherDataBoatLocation = analysedDataDict[i]['weatherDataBoatLocation']
        name = filenameList[i].rsplit('/', 1)[1]

        arrowLen = max(gpsData['g_x'].max()-gpsData['g_x'].min(), gpsData['g_y'].max()-gpsData['g_y'].min())/5
        scatterSize = max(gpsData['g_x'].max()-gpsData['g_x'].min(), gpsData['g_y'].max()-gpsData['g_y'].min())/70
        mapFig.suptitle('GPS Track', fontsize=16)
        narrows= 20

        xLims = [gpsData['g_x'].min()-0.1*arrowLen, gpsData['g_x'].max()+0.1*arrowLen]
        yLims = [gpsData['g_y'].min()-0.1*arrowLen, gpsData['g_y'].max()+0.1*arrowLen]
        if len(filenameList) == 1:
            mapAx = [mapAx]

        # draw basemap
        map = Basemap(llcrnrlon=xLims[0]/110922+gpsData['lon'].iloc[0],llcrnrlat=yLims[0]/110922+gpsData['lat'].iloc[0],urcrnrlon=xLims[1]/110922+gpsData['lon'].iloc[0],urcrnrlat=yLims[1]/110922+gpsData['lat'].iloc[0], epsg=5520)
        #http://server.arcgisonline.com/arcgis/rest/services

        map.arcgisimage(service='ESRI_Imagery_World_2D', xpixels = 1500, verbose= True)
        mapAx[i]=map

        for j in range(0,narrows):
            index = np.floor(len(gpsData)*j/narrows).astype(int)
            windAngle = 180+np.interp((gpsData.iloc[index]['time'].replace(tzinfo=weatherDataBoatLocation.iloc[0]['date'].tzinfo)-pd.Timestamp.today(tz='UTC'))/pd.Timedelta(seconds=1),(weatherDataBoatLocation['date']-pd.Timestamp.today(tz='UTC'))/pd.Timedelta(seconds=1),weatherDataBoatLocation['wind_direction_10m'])
            zeroPos = [gpsData['g_x'][index]- 0.5*arrowLen*np.sin(windAngle*np.pi/180),gpsData['g_y'][index]- 0.5*arrowLen*np.cos(windAngle*np.pi/180)]
            endPos = [gpsData['g_x'][index]+ 0.5*arrowLen*np.sin(windAngle*np.pi/180),gpsData['g_y'][index]+ 0.5*arrowLen*np.cos(windAngle*np.pi/180)]
            if j ==narrows-1:
                mapAx[i].annotate("",xytext=(zeroPos[0], zeroPos[1]),xy=(endPos[0],endPos[1]),arrowprops=dict(arrowstyle="->",lw=0.5,color=[0.3,0.3,0.3]),fontsize=7, ha='center', va='center')
            else:
                mapAx[i].annotate("",xytext=(zeroPos[0], zeroPos[1]),xy=(endPos[0],endPos[1]),arrowprops=dict(arrowstyle="->",lw=0.5,color=[0.3,0.3,0.3]),fontsize=7, ha='center', va='center')
        mapAx[i].plot(gpsData['g_x'], gpsData['g_y'], color='k', linewidth=1.5,label='GPS Track')
        mapAx[i].scatter(manoeuvreData[manoeuvreData['tack']==True]['g_x'], manoeuvreData[manoeuvreData['tack']==True]['g_y'], s=scatterSize, color='b', label='Tacks')
        mapAx[i].scatter(manoeuvreData[manoeuvreData['tack']==False]['g_x'], manoeuvreData[manoeuvreData['tack']==False]['g_y'], s=scatterSize, color='g', label='Gybes')
        mapAx[i].set_title(name)
        mapAx[i].set_xlabel('Distance from start (m)')
        mapAx[i].set_ylabel('Distance from start (m)')
        mapAx[i].set_xlim(xLims)
        mapAx[i].set_ylim(yLims)
        mapAx[i].axis('equal')
        mapAx[i].axis('square')
        mapAx[i].tick_params(axis='both', which='major', labelsize=10)
        mapAx[i].grid(True, which='both', linestyle='--', linewidth=0.5)
        mapAx[i].legend(prop={'size': 6})

        #mapFig.show()

    mapPlotDict = {'fig': mapFig, 'ax': mapAx}
    return mapPlotDict

def plotmapsCubic(filenameList,analysedDataDict,straightLineDataDict,callImgBackground=False):
    '''
    Plot the GPS data track, adding points for each manoeuvre and arrows for wind direction and direction of travel.
    '''
    mapFig = plt.figure(figsize=(10, 8),layout='constrained')
    mapAx = filenameList.copy()  # Create a list for subplots
    for i in range(0,len(filenameList)):
        imgBackground=callImgBackground
        colorMap = np.array([np.concatenate([np.zeros(shape=(128,)),np.linspace(0,1,128)]),np.concatenate([np.zeros(shape=(64,)),np.linspace(0,1,64),np.linspace(1,0,64),np.zeros(shape=(64,))]),np.concatenate([np.linspace(1,0,128),np.zeros(shape=(128,))])])
        speedRange = [0,max(max(straightLineDataDict[i]['upwind']['speed']),max(straightLineDataDict[i]['downwind']['speed']))]
        mapAx[i] = mapFig.add_subplot(1, len(filenameList), i+1)
        gpsData = analysedDataDict[i]['gpsData']
        manoeuvreData = analysedDataDict[i]['manoeuvreData']
        weatherDataBoatLocation = analysedDataDict[i]['weatherDataBoatLocation']
        name = filenameList[i].rsplit('/', 1)[1].rsplit('.', 1)[0]
        xCoeffs = analysedDataDict[i]['xCoeffs']
        yCoeffs = analysedDataDict[i]['yCoeffs']

        arrowLen = max(gpsData['g_x'].max()-gpsData['g_x'].min(), gpsData['g_y'].max()-gpsData['g_y'].min())/5
        scatterSize = max(gpsData['g_x'].max()-gpsData['g_x'].min(), gpsData['g_y'].max()-gpsData['g_y'].min())/70
        mapFig.suptitle('GPS Track', fontsize=16)
        narrows= 20

        xLims = [gpsData['g_x'].min()-0.1*arrowLen, gpsData['g_x'].max()+0.1*arrowLen]
        yLims = [gpsData['g_y'].min()-0.1*arrowLen, gpsData['g_y'].max()+0.1*arrowLen]

        # draw basemap
        #map = Basemap(llcrnrlon=xLims[0]/110922+float(gpsData['lon'].iloc[0]),llcrnrlat=yLims[0]/110922+float(gpsData['lat'].iloc[0]),urcrnrlon=xLims[1]/110922+float(gpsData['lon'].iloc[0]),urcrnrlat=yLims[1]/110922+float(gpsData['lat'].iloc[0]), epsg=5520)
        #http://server.arcgisonline.com/arcgis/rest/services
        
        #mapimg=map.arcgisimage(server='http://server.arcgisonline.com/arcgis',service='World_Imagery', xpixels = 1500, verbose= True)
        if callImgBackground:
            try:
                image=Basemap(llcrnrlon=xLims[0]/110922+float(gpsData['lon'].iloc[0]),llcrnrlat=yLims[0]/110922+float(gpsData['lat'].iloc[0]),urcrnrlon=xLims[1]/110922+float(gpsData['lon'].iloc[0]),urcrnrlat=yLims[1]/110922+float(gpsData['lat'].iloc[0]), epsg=5520).arcgisimage(server='http://server.arcgisonline.com/arcgis',service='World_Imagery', xpixels = 1920, verbose= True)
                windColor = [0.7,0.7,0.7]
                directionColor = [1,1,1]
            except:
                imgBackground = False
                print(f"Error loading background image. Plotted without background")
        if not imgBackground:
            windColor = [0.3,0.3,0.3]
            directionColor = [0,0,0]

        for j in range(0,narrows):
            index = np.floor(len(gpsData)*j/narrows).astype(int)
            windAngle = 180+np.interp((gpsData.iloc[index]['time'].replace(tzinfo=weatherDataBoatLocation.iloc[0]['date'].tzinfo)-pd.Timestamp.today(tz='UTC'))/pd.Timedelta(seconds=1),(weatherDataBoatLocation['date']-pd.Timestamp.today(tz='UTC'))/pd.Timedelta(seconds=1),weatherDataBoatLocation['wind_direction_10m'])
            zeroPos = [gpsData['g_x'][index]- 0.5*arrowLen*np.sin(windAngle*np.pi/180),gpsData['g_y'][index]- 0.5*arrowLen*np.cos(windAngle*np.pi/180)]
            endPos = [gpsData['g_x'][index]+ 0.5*arrowLen*np.sin(windAngle*np.pi/180),gpsData['g_y'][index]+ 0.5*arrowLen*np.cos(windAngle*np.pi/180)]
            if j ==narrows-1:
                mapAx[i].annotate("",xytext=(zeroPos[0], zeroPos[1]),xy=(endPos[0],endPos[1]),arrowprops=dict(arrowstyle="->",lw=0.5,color=windColor),fontsize=7, ha='center', va='center')
            else:
                mapAx[i].annotate("",xytext=(zeroPos[0], zeroPos[1]),xy=(endPos[0],endPos[1]),arrowprops=dict(arrowstyle="->",lw=0.5,color=windColor),fontsize=7, ha='center', va='center')
        t0 = gpsData['time'][0]
        npoints= len(gpsData['time'])
        for k in range(0, npoints-1):
            tCommon = (gpsData['time'][k]-t0)/pd.Timedelta(seconds=1)
            t = np.linspace(tCommon, (gpsData['time'][k+1]-t0)/pd.Timedelta(seconds=1), 50)
            speed = np.linalg.norm(f_1(t[24],xCoeffs,yCoeffs,k))
            colorInd = int(np.round(speed*256/speedRange[1]))
            if colorInd > 255:
                colorInd =255
            elif colorInd<0:
                colorInd=0
            colour = colorMap[:,colorInd]/max(colorMap[:,colorInd])
            mapAx[i].plot(xCoeffs[k*4]*t**3+xCoeffs[k*4+1]*t**2+xCoeffs[k*4+2]*t+xCoeffs[k*4+3],yCoeffs[k*4]*t**3+yCoeffs[k*4+1]*t**2+yCoeffs[k*4+2]*t+yCoeffs[k*4+3], color=colour, linewidth=1.5)

        '''if imgBackground:
            try:
                image=Basemap(llcrnrlon=xLims[0]/110922+float(gpsData['lon'].iloc[0]),llcrnrlat=yLims[0]/110922+float(gpsData['lat'].iloc[0]),urcrnrlon=xLims[1]/110922+float(gpsData['lon'].iloc[0]),urcrnrlat=yLims[1]/110922+float(gpsData['lat'].iloc[0]), epsg=5520).arcgisimage(server='http://server.arcgisonline.com/arcgis',service='World_Imagery', xpixels = 1920, verbose= True)
            except:
                print(f"Error loading background image. Plotted without background")'''
        mapAx[i].tick_params(axis='both', which='major', labelsize=10)
        mapAx[i].grid(True, which='both', linestyle='--', linewidth=0.5)
        tList = np.ndarray(shape=(len(manoeuvreData['time']),1))
        tList[:,0]=(manoeuvreData['time']-t0)/pd.Timedelta(seconds=1)
        tList3=np.power(tList,3)
        tList2=np.power(tList,2)
        a=np.array([xCoeffs[manoeuvreData['spline']*4],yCoeffs[manoeuvreData['spline']*4]])
        b=np.array([xCoeffs[manoeuvreData['spline']*4+1],yCoeffs[manoeuvreData['spline']*4+1]])
        c=np.array([xCoeffs[manoeuvreData['spline']*4+2],yCoeffs[manoeuvreData['spline']*4+2]])
        d=np.array([xCoeffs[manoeuvreData['spline']*4+3],yCoeffs[manoeuvreData['spline']*4+3]])
        #randomIndex = np.random.randint(0, len(gpsData)-1)
        #plt.annotate("",xytext=(gpsData['g_x'][randomIndex], gpsData['g_y'][randomIndex]),xy=(gpsData['g_x'][randomIndex]+40*np.sin(gpsData['angle'][randomIndex]*np.pi/180),gpsData['g_y'][randomIndex]+40*np.cos(gpsData['angle'][randomIndex]*np.pi/180)),arrowprops=dict(arrowstyle="->",lw=1.5,color='black'),fontsize=7, ha='center', va='center')
        mapAx[i].scatter(np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0], np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1], color='green', label='Manoeuvres')
        #plt.show()
        mapAx[i].scatter((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[manoeuvreData['tack']], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[manoeuvreData['tack']], color='red', label='Tacks')
        mapAx[i].scatter((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[~manoeuvreData['tack']], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[~manoeuvreData['tack']], color='blue', label='Gybes')
        for manoeuvre in range(0,len(manoeuvreData['time'])):
            t=(manoeuvreData['time'].iloc[manoeuvre]-t0)/pd.Timedelta(seconds=1) # time in seconds
            spline = find_neighbours(gpsData['time'][0]+pd.Timedelta(seconds=t), gpsData['time'])[0] # find the index of the closest time point before this time. 
            gpsVector = np.array([3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2], 3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2]])
            pos=((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[manoeuvre], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[manoeuvre])
            mapAx[i].annotate("",xytext=pos,xy=(pos[0]+gpsVector[0]*40,pos[1]+gpsVector[1]*40),arrowprops=dict(arrowstyle="->",lw=1.5,color=directionColor),fontsize=7, ha='center', va='center')

        mapAx[i].set_title(name)
        #mapAx[i].axis('equal')
        
        mapAx[i].legend(prop={'size': 6})
        mapAx[i].grid(True, which='both', linestyle='--', linewidth=0.5)
        mapAx[i].tick_params(axis='both', which='major', labelsize=10)
        #mapAx[i].set_xbound(xLims[0], xLims[1])
        if imgBackground:
            image.set(extent=(xLims[0], xLims[1], yLims[0], yLims[1]))
        else:
            mapAx[i].axis('equal')
            mapAx[i].set_xlabel('Distance from start (m)')
            mapAx[i].set_ylabel('Distance from start (m)')
        mapFig.axes[i].set_xlim(xLims[0],xLims[1])
        mapFig.axes[i].set_ylim(yLims[0],yLims[1])
        #mapFig.show()

    mapPlotDict = {'fig': mapFig, 'ax': mapAx}
    return mapPlotDict

if __name__ == '__main__':
    filenameList = ["C:/Users/matth/Documents/SailAnalyser/2025_06_15 OSC Race 1.gpx"]
    windAngleList = [None, None]
    windowSize =30
    tackPlotDict,gybePlotDict,analysedDataDict = analyseManoeuvresCubicInterp(filenameList, windAngleList,windowSize)
    violinPlotDict,straightLineDataDict=straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize)
    mapPlotDict = plotmapsCubic(filenameList, analysedDataDict,straightLineDataDict,True)
    plt.show()