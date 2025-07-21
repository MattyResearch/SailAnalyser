import numpy as np
import pandas as pd
from xmlReader import read_xml
from manoeuvreIdentifier import calculateVelocity, identifyManoeuvres, identifyManoeuvresCubic, identifySingleManoeuvreCubic, doubleCheck
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from performancePlotters import tackPlots, gybePlots
from historicalWeatherData import weatherDataAtBoat, manualWindInput
from GUI import fileSelectionWindow,passToTk
from cubicInterpolation import cubicSplineInterpolation, find_neighbours,f_1,f

def manoeuvreWindowExtractor(gpsData, manoeuvreData, windowSize, manoeuvre_n,manoeuvreLength=5):
    """
    Extract a single manoeuvre window from GPS data.
    windowSize in sec
    manoeuvreLength in sec
    """
    windowSize=windowSize
    if manoeuvre_n>=len(manoeuvreData):
        print("No more manoeuvres to extract")
        return pd.DataFrame()
    print("Extracting manoeuvre number: ", manoeuvre_n+1," ...")
    starttime = max(gpsData.iloc[manoeuvreData['row'].iloc[manoeuvre_n]]['time']-dt.timedelta(seconds=windowSize), gpsData.iloc[0]['time'],gpsData.iloc[manoeuvreData['row'].iloc[manoeuvre_n-1]]['time'] if manoeuvre_n-1>=0 else gpsData.iloc[0]['time'])
    endtime = min(gpsData.iloc[manoeuvreData['row'].iloc[manoeuvre_n]]['time']+dt.timedelta(seconds=windowSize), gpsData.iloc[len(gpsData)-1]['time'],gpsData.iloc[manoeuvreData['row'].iloc[manoeuvre_n+1]]['time'] if manoeuvre_n+1<len(manoeuvreData) else gpsData.iloc[len(gpsData)-1]['time'])
    startbool=gpsData['time']>starttime
    endbool = gpsData['time']<endtime
    bools = startbool & endbool
    manoeuvreWindow=gpsData.loc[bools]
    manoeuvreWindow.iloc[:]['tack'] = manoeuvreData.iloc[manoeuvre_n]['tack']
    if manoeuvreWindow.empty:
        print("\nEmpty manoeuvre window",manoeuvre_n+1,": tacks are too close together or wind direction is incorrect\n...     Skipping    ...\n")
        manoeuvreData.drop(index=manoeuvreData.iloc[manoeuvre_n]['row'],inplace=True)
        return pd.DataFrame()
    return manoeuvreWindow
'''
def windowPlotter(gpsData,manoeuvreWindow, manoeuvre_n):
    """
    Plot data and angles
    """
    print("Plotting manoeuvre ",manoeuvre_n," window...")
    plt.plot(gpsData['g_x'], gpsData['g_y'])
    plt.title('GPS Track')
    plt.xlabel('Distance from start (m)')
    plt.ylabel('Distance from start (m)')
    plt.axis('equal')
    plt.axis('square')
    plt.tick_params(axis='both', which='major', labelsize=10)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.plot(manoeuvreWindow['g_x'], manoeuvreWindow['g_y'], color='red',linestyle=':', lw=2, label='Manoeuvre window')
    plt.annotate("TWA",xytext=(max(tacks['g_x'][:]+250),max(tacks['g_y'][:]+250)),xy=(max(tacks['g_x'][:]+250)+np.sin(np.pi+cardinalWindAngle*np.pi/180)*200,max(tacks['g_y'][:]+250)+np.cos(np.pi+cardinalWindAngle*np.pi/180)*200),arrowprops=dict(arrowstyle="->",lw=1.5,color='black'),fontsize=7, ha='center', va='center')
    plt.legend()
    plt.show()
'''
def timeRangeData(data,starttime,endtime):
    """
    Extract range of data between start and end time
    """
    startbool=data['time']>starttime
    endbool = data['time']<=endtime
    bools = startbool & endbool
    if bools.any():
        dataOut = data.loc[bools]
    elif endtime > data.iloc[-1]['time']:
        dataOut=data.iloc[-1]
    else:
        dataOut = data.iloc[0]

    return dataOut

def manoeuvreAnalysis(manoeuvreWindow, manoeuvre_n,manoeuvreData,gpsData,windowSize,manoeuvreLength=5,repoAllowed=False):
    """
    Analyses a single tack or gybe
    Outputs Boatspeed, TWA, VMG, metres lost into a dict for all manoeuvres
    """
    if manoeuvreWindow.empty:
        print("Empty manoeuvre window",manoeuvre_n+1,": tacks are too close together or wind direction is incorrect\n...     Skipping    ...")
        return {}, {},False,manoeuvreData,gpsData,999
    print("Analysing manoeuvre number:  ", manoeuvre_n+1," ...")
    time = np.array((manoeuvreWindow['time']-manoeuvreData.iloc[manoeuvre_n]['time']))/np.timedelta64(1000000000,'ns') # time in seconds
    
    # Extract data outside of manoeuvre padding (to allow averaged vmg calc)
    starttime = manoeuvreData.iloc[manoeuvre_n]['time']-dt.timedelta(seconds=windowSize/2)
    endtime = manoeuvreData.iloc[manoeuvre_n]['time']-dt.timedelta(seconds=manoeuvreLength)
    manoeuvreEntry=timeRangeData(manoeuvreWindow, starttime, endtime)

    starttime = manoeuvreData.iloc[manoeuvre_n]['time']+dt.timedelta(seconds=manoeuvreLength)
    endtime = manoeuvreData.iloc[manoeuvre_n]['time']+dt.timedelta(seconds=windowSize/2)
    manoeuvreExit=timeRangeData(manoeuvreWindow, starttime, endtime)

    vecBefore = np.array([np.sin(np.mean(manoeuvreEntry[:]['angle'])*np.pi/180),np.cos(np.mean(manoeuvreEntry[:]['angle'])*np.pi/180)]) # unit direction vector
    vecAfter = np.array([np.sin(np.mean(manoeuvreExit[:]['angle'])*np.pi/180),np.cos(np.mean(manoeuvreExit[:]['angle'])*np.pi/180)]) # unit direction vector

    if np.remainder(manoeuvreWindow.iloc[0]['angle']-manoeuvreWindow.iloc[len(manoeuvreWindow)-1]['angle'],360)>180: # there is a weird condition here that needs tobe cleaned up - what happens when we snap across the 0 degree line? np.remainder(manoeuvreWindow.iloc[len(manoeuvreWindow)-1]['angle']-manoeuvreWindow.iloc[0]['angle'])
        direction = 'right'
        localWindDirection =  np.rad2deg(np.arctan2(vecBefore[0],vecBefore[1]))+np.arccos(np.dot(vecBefore,vecAfter))*90/np.pi # turning right - bisects the turning angle
    else:
        direction = 'left'
        localWindDirection =  np.rad2deg(np.arctan2(vecBefore[0],vecBefore[1]))-np.arccos(np.dot(vecBefore,vecAfter))*90/np.pi # turning left - bisects the turning angle
    #doubleCheck(gpsData,manoeuvreData,cardinalWindAngle,localWindDirection,manoeuvre_n)
    boatspeed = np.array(manoeuvreWindow['speed']) # m/s
    vmg = np.array(np.cos(np.deg2rad(localWindDirection-manoeuvreWindow['angle']))*boatspeed) # m/s w.r.t. local wind direction
    rowOffset = (manoeuvreEntry.index.astype(int)[0] if manoeuvreEntry.index[0]!='time' else manoeuvreEntry.name.astype(int))- manoeuvreWindow.index.astype(int)[0] # index of the first row in the manoeuvre window

    '''
    Deprecated code for vmg calculation before the manoeuvre
    for v in range(1+rowOffset,len([manoeuvreEntry['time']])+1+rowOffset):
        # weighted average of vmg before the manoeuvre
        vmgBefore = 0.5*(vmg[v]+vmg[v-1])*(manoeuvreWindow.iloc[v]['time']-manoeuvreWindow.iloc[v-1]['time'])/dt.timedelta(seconds=1) # m/s w.r.t. local wind direction
    vmgBefore = vmgBefore/((manoeuvreWindow.iloc[v]['time']-manoeuvreWindow.iloc[rowOffset]['time'])/dt.timedelta(seconds=1))
    '''

    twa = np.remainder(np.array(localWindDirection-manoeuvreWindow['angle']),360)
    twa[twa>180] = twa[twa>180]-360 # convert to -180 to 180 degrees
    twa = abs(twa) # convert to 0 to 180 degrees
    unitWindVector = np.array([np.sin(np.deg2rad(localWindDirection)),np.cos(np.deg2rad(localWindDirection))])
    if manoeuvreData.iloc[manoeuvre_n]['tack']:
        if rowOffset == 0: # if the manoeuvre is at the start of the window
            vmgBefore = vmg[0] # use the first vmg value
        else:
            courseMadeGoodBefore=np.dot(np.array([manoeuvreWindow['g_x'].iloc[len([manoeuvreEntry['time']])+rowOffset]-manoeuvreWindow['g_x'].iloc[rowOffset],manoeuvreWindow['g_y'].iloc[len([manoeuvreEntry['time']])+rowOffset]-manoeuvreWindow['g_y'].iloc[rowOffset]]),unitWindVector)
            vmgBefore = courseMadeGoodBefore/(manoeuvreWindow.iloc[len([manoeuvreEntry['time']])+rowOffset]['time']-manoeuvreWindow.iloc[rowOffset]['time']).total_seconds() # m/s w.r.t. local wind direction

        metresLost = np.zeros(len(manoeuvreWindow))
        for i in range(len(manoeuvreWindow)):
            metresLost[i] = vmgBefore*(manoeuvreWindow.iloc[i]['time']-manoeuvreWindow.iloc[0]['time'])/dt.timedelta(seconds=1)-np.dot(np.array([manoeuvreWindow['g_x'].iloc[i]-manoeuvreWindow['g_x'].iloc[0],manoeuvreWindow['g_y'].iloc[i]-manoeuvreWindow['g_y'].iloc[0]]),unitWindVector)
        metresLost = metresLost-np.interp((manoeuvreData.iloc[manoeuvre_n]['time']-pd.Timestamp.today()-pd.Timedelta(seconds=windowSize/2))/dt.timedelta(seconds=1),(manoeuvreWindow['time']-pd.Timestamp.today())/dt.timedelta(seconds=1),metresLost) # adjust to zero at beginning of manoeuvre window
        singleTackAnalysed = {'time':time,'boatspeed':boatspeed,'vmg':vmg,'twa':twa,'metresLost':metresLost}
        singleGybeAnalysed = {}
    else:
        localWindDirection=localWindDirection+180
        twa = np.remainder(np.array(localWindDirection-manoeuvreWindow['angle']),360) # deg +ve indicates starboard tack
        twa[twa>180]=twa[twa>180]-360
        twa = abs(twa) # convert to 0 to 180 degrees
        unitWindVector = np.array([np.sin(np.deg2rad(localWindDirection)),np.cos(np.deg2rad(localWindDirection))])

        if rowOffset == 0: # if the manoeuvre is at the start of the window
            vmgBefore = vmg[0] # use the first vmg value
        else:
            courseMadeGoodBefore=np.dot(np.array([manoeuvreWindow['g_x'].iloc[len([manoeuvreEntry['time']])+rowOffset]-manoeuvreWindow['g_x'].iloc[rowOffset],manoeuvreWindow['g_y'].iloc[len([manoeuvreEntry['time']])+rowOffset]-manoeuvreWindow['g_y'].iloc[rowOffset]]),unitWindVector)
            vmgBefore = courseMadeGoodBefore/(manoeuvreWindow.iloc[len([manoeuvreEntry['time']])+rowOffset]['time']-manoeuvreWindow.iloc[rowOffset]['time']).total_seconds() # m/s w.r.t. local wind direction

        metresLost = np.zeros(len(manoeuvreWindow))
        for i in range(len(manoeuvreWindow)):
            metresLost[i] = vmgBefore*(manoeuvreWindow.iloc[i]['time']-manoeuvreWindow.iloc[0]['time'])/dt.timedelta(seconds=1)-np.dot(np.array([manoeuvreWindow['g_x'].iloc[i]-manoeuvreWindow['g_x'].iloc[0],manoeuvreWindow['g_y'].iloc[i]-manoeuvreWindow['g_y'].iloc[0]]),unitWindVector)
        metresLost = metresLost-np.interp((manoeuvreData.iloc[manoeuvre_n]['time']-pd.Timestamp.today()-pd.Timedelta(seconds=windowSize/2))/dt.timedelta(seconds=1),(manoeuvreWindow['time']-pd.Timestamp.today())/dt.timedelta(seconds=1),metresLost) # adjust to zero at beginning of manoeuvre window
        singleTackAnalysed = {}
        singleGybeAnalysed = {'time':time,'boatspeed':boatspeed,'vmg':vmg,'twa':twa,'metresLost':-metresLost}
    
    repositioned = False
    if repoAllowed and abs(np.cos(np.deg2rad(gpsData.iloc[manoeuvreData['row'].iloc[manoeuvre_n]]['angle']-localWindDirection)))<max(abs(np.cos(singleTackAnalysed['twa']*np.pi/180) if singleTackAnalysed !={} else np.cos(singleGybeAnalysed['twa']*np.pi/180))): # if cos(gps point angle - local wind direction) for the chosen manoeuvre point < max cos(twa)
        sortFlag = np.argsort(abs(np.cos(singleTackAnalysed['twa']*np.pi/180) if singleTackAnalysed !={} else np.cos(singleGybeAnalysed['twa']*np.pi/180)))
        inputdf = gpsData.iloc[manoeuvreWindow.index[0]+sortFlag[-1]]
        inputdf=pd.concat([inputdf,pd.Series({'tack':True if singleTackAnalysed !={} else False,'row':manoeuvreWindow.index[0]+sortFlag[-1]})])
        #inputdf.iloc['tack'] = True if singleTackAnalysed !={} else False
        #inputdf.iloc['row'] = manoeuvreWindow.index[0]+sortFlag[-1]
        manoeuvreData.iloc[manoeuvre_n]=inputdf # reposition the manoeuvre to the middle of the window
        manoeuvreData.drop(manoeuvreData.index[manoeuvre_n])
        manoeuvreData.set_index(manoeuvreData['row'])
        manoeuvreData.sort_values(by=['row'],inplace=True)
        repositioned = True

    return singleTackAnalysed,singleGybeAnalysed,repositioned,manoeuvreData,gpsData,localWindDirection if manoeuvreData.iloc[manoeuvre_n]['tack'] else localWindDirection-180

def averageAnalysis(tackAnalysed,gybeAnalysed,windowSize,manoeuvre_n,avgTack,avgGybe):
    """
    Gives linearly interpolated averages of all manoeuvres per second
    """
    timeLims = np.int8([np.floor(-windowSize/2), np.ceil(windowSize/2)+1])
    for j in range(timeLims[0],timeLims[1]):
        if manoeuvre_n not in tackAnalysed or tackAnalysed[manoeuvre_n] == {}:
            continue
        avgTack[windowSize+j,0]=j # time
        if j<tackAnalysed[manoeuvre_n]['time'][0]:
            continue
        elif j>tackAnalysed[manoeuvre_n]['time'][-1]:
            break
        avgTack[windowSize+j,1]+=np.interp(j,tackAnalysed[manoeuvre_n]['time'],tackAnalysed[manoeuvre_n]['boatspeed']) # boatspeed 
        avgTack[windowSize+j,2]+=np.interp(j,tackAnalysed[manoeuvre_n]['time'],tackAnalysed[manoeuvre_n]['vmg']) # vmg
        avgTack[windowSize+j,3]+=np.interp(j,tackAnalysed[manoeuvre_n]['time'],tackAnalysed[manoeuvre_n]['twa']) # twa
        avgTack[windowSize+j,4]+=np.interp(j,tackAnalysed[manoeuvre_n]['time'],tackAnalysed[manoeuvre_n]['metresLost']) # metres lost
        avgTack[windowSize+j,5]+=1 # count

    for j in range(timeLims[0],timeLims[1]):
        avgGybe[windowSize+j,0]=j # time
        if manoeuvre_n not in gybeAnalysed or gybeAnalysed[manoeuvre_n] == {}:
            continue
        if j<gybeAnalysed[manoeuvre_n]['time'][0]:
            continue
        elif j>gybeAnalysed[manoeuvre_n]['time'][-1]:
            break
        avgGybe[windowSize+j,1]+=np.interp(j,gybeAnalysed[manoeuvre_n]['time'],gybeAnalysed[manoeuvre_n]['boatspeed']) # boatspeed 
        avgGybe[windowSize+j,2]+=np.interp(j,gybeAnalysed[manoeuvre_n]['time'],gybeAnalysed[manoeuvre_n]['vmg']) # vmg
        avgGybe[windowSize+j,3]+=np.interp(j,gybeAnalysed[manoeuvre_n]['time'],gybeAnalysed[manoeuvre_n]['twa']) # twa
        avgGybe[windowSize+j,4]+=np.interp(j,gybeAnalysed[manoeuvre_n]['time'],gybeAnalysed[manoeuvre_n]['metresLost']) # metres lost
        avgGybe[windowSize+j,5]+=1 # count

    return avgTack, avgGybe

def averageAnalysisCubic(tackAnalysed,gybeAnalysed,windowSize,manoeuvre_n,avgTack,avgGybe,nPoints):
    """
    Gives averages of all manoeuvres for the number of points in the graph
    """
    if manoeuvre_n in tackAnalysed and tackAnalysed[manoeuvre_n] != {}:
        avgTack[:,0]=tackAnalysed[manoeuvre_n]['time']
        for j in range(0,nPoints):
            avgTack[j,1]+=tackAnalysed[manoeuvre_n]['boatspeed'][j]
            avgTack[j,2]+=tackAnalysed[manoeuvre_n]['vmg'][j] # vmg
            avgTack[j,3]+=tackAnalysed[manoeuvre_n]['twa'][j] # twa
            avgTack[j,4]+=tackAnalysed[manoeuvre_n]['metresLost'][j] # metres lost
            avgTack[j,5]+=1 # count

    if manoeuvre_n in gybeAnalysed and gybeAnalysed[manoeuvre_n] != {}:
        avgGybe[:,0]=gybeAnalysed[manoeuvre_n]['time']
        for j in range(0,nPoints):
            avgGybe[j,1]+=gybeAnalysed[manoeuvre_n]['boatspeed'][j]
            avgGybe[j,2]+=gybeAnalysed[manoeuvre_n]['vmg'][j] # vmg
            avgGybe[j,3]+=gybeAnalysed[manoeuvre_n]['twa'][j] # twa
            avgGybe[j,4]+=gybeAnalysed[manoeuvre_n]['metresLost'][j] # metres lost
            avgGybe[j,5]+=1 # count

    return avgTack, avgGybe

def averageManoeuvres(avgTack,avgGybe):
    """
    Clean up manoeuvre averages
    """
    delBool = np.zeros(len(avgTack),dtype=bool)
    #avgTack[:,1:5] = None if avgTack[:,5].any() == 0 else avgTack[:,1:5]
    for i in range(len(avgTack)):
        if avgTack[i,5] != 0:
            for col in range(1,5):
                avgTack[i,col] = avgTack[i,col]/avgTack[i,5]
            '''avgTack[i,2] = avgTack[i,2]/avgTack[i,5]
            avgTack[i,3] = avgTack[i,3]/avgTack[i,5]
            avgTack[i,4] = avgTack[i,4]/avgTack[i,5]'''
            delBool[i]=False
        else:
            delBool[i]=True
    avgTack = np.delete(avgTack,delBool,axis=0)

    delBool = np.zeros(len(avgGybe),dtype=bool)
    #avgGybe[:,1:5] = None if avgGybe[:,1:5].any() == 0 else avgGybe[:,1:5]
    for i in range(len(avgGybe)):
        if avgGybe[i,5] != 0:
            for col in range(1,5):
                avgGybe[i,col] = avgGybe[i,col]/avgGybe[i,5]
            '''avgGybe[i,2] = avgGybe[i,2]/avgGybe[i,5]
            avgGybe[i,3] = avgGybe[i,3]/avgGybe[i,5]
            avgGybe[i,4] = avgGybe[i,4]/avgGybe[i,5]'''
            delBool[i]=False
        else:
            delBool[i]=True
    avgGybe = np.delete(avgGybe,delBool,axis=0)

    return avgTack, avgGybe

def analyseManoeuvresMain(filenameList, windAngleList):
    analysedDataDict = {}
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = filenameList[i].rsplit('/', 1)[0]
        filename = filenameList[i]
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename

        windowSize = 30 # seconds either side total
        manoeuvreLength=3 # seconds either side
        colours = ['blue','magenta']

        gpsData = read_xml(inputFile=filename,outputFile=outputfile)
        gpsData = calculateVelocity(gpsData)
        if windAngleList[i] is not None:
            weatherDataBoatLocation = manualWindInput(0,windAngleList[i],gpsData)
        else:
            weatherDataBoatLocation = weatherDataAtBoat(gpsData)
        tacks, gybes,manoeuvreData = identifyManoeuvres(gpsData, weatherDataBoatLocation)

        tackAnalysed = {}
        gybeAnalysed = {}
        avgTack = np.zeros([len(range(-windowSize,windowSize)),6])
        avgGybe = np.zeros([len(range(-windowSize,windowSize)),6])
        windAngles=[]
        delKeys = {'indices':[],'dataFrameRows':[]}
        originalDataFrameRows = manoeuvreData['row'].copy()  # Store original DataFrame rows for reference
        for manoeuvre_n in range(len(manoeuvreData)-1):
            repositioned = True
            tickCount = 0
            while repositioned and tickCount <= 2:
                repoAllowed = True
                manoeuvreWindow = manoeuvreWindowExtractor(gpsData, manoeuvreData,windowSize,manoeuvre_n,manoeuvreLength)
                tackAnalysed[manoeuvre_n], gybeAnalysed[manoeuvre_n],repositioned,manoeuvreData,gpsData,localWindDirection= manoeuvreAnalysis(manoeuvreWindow,manoeuvre_n,manoeuvreData,gpsData,windowSize,manoeuvreLength,repoAllowed)
                tickCount += 1
            if localWindDirection == 999:
                delKeys['indices'].append(manoeuvre_n) # set key to delete manoeuvre if it is too short or invalid
                delKeys['dataFrameRows'].append(manoeuvreData['row'].iloc[manoeuvre_n])
            elif (tackAnalysed[manoeuvre_n]!={} and tackAnalysed[manoeuvre_n]['twa'][tackAnalysed[manoeuvre_n]['time']==0] > 80) or (gybeAnalysed[manoeuvre_n] !={} and gybeAnalysed[manoeuvre_n]['twa'][gybeAnalysed[manoeuvre_n]['time']==0] < 170):
                # if the twa at the midpoint of the manoeuvre is wrong, then this will mess with analysis. Could be something like a penalty turn. Delete it.
                delKeys['indices'].append(manoeuvre_n) # set key to delete manoeuvre if it is too short or invalid
                delKeys['dataFrameRows'].append(originalDataFrameRows.iloc[manoeuvre_n])
            else:
                windAngles.append(localWindDirection)
        #avgWindAngle=np.arctan2(np.sum(np.sin(np.deg2rad(np.array(windAngles)))),np.sum(np.cos(np.deg2rad(np.array(windAngles))))) # this currently doesn't work, since it cannot distinguish between the "wind angle" for tacks and gybes
        #avgWindAngle=avgWindAngle+2*np.pi if avgWindAngle<0 else avgWindAngle
        for dels in delKeys['indices']:
            del tackAnalysed[dels]
            del gybeAnalysed[dels]
        manoeuvreData.drop(delKeys['dataFrameRows'],inplace=True) # delete manoeuvre if it is too short or invalid

        #doubleCheck(gpsData,manoeuvreData,cardinalWindAngle)
        #print("Recommended cardinal wind angle: ",np.rad2deg(avgWindAngle))
        print("Averaging manoeuvres...")
        for manoeuvre_n in range(len(manoeuvreData)):
            avgTack,avgGybe = averageAnalysis(tackAnalysed,gybeAnalysed,windowSize,manoeuvre_n,avgTack,avgGybe)
        avgTack,avgGybe=averageManoeuvres(avgTack,avgGybe)

        #tackAnalysed['averages'] = tackAnalysed[:]
        #gybeAnalysed['averages'] = gybeAnalysed.mean(axis=0)
        tackPlotDict=tackPlots(tackAnalysed,windowSize,avgTack,tackPlotDict if i>0 else None,colours[i],filenameList[i].rsplit('/', 1)[1])
        gybePlotDict=gybePlots(gybeAnalysed,windowSize,avgGybe,gybePlotDict if i>0 else None,colours[i],filenameList[i].rsplit('/', 1)[1])

        analysedDataDict[i] = {'gpsData': gpsData, 'manoeuvreData': manoeuvreData, 'weatherDataBoatLocation': weatherDataBoatLocation}

    #analysedDataDict={'gpsData':gpsData,'manoeuvreData':manoeuvreData,'weatherDataBoatLocation':weatherDataBoatLocation}
    return tackPlotDict, gybePlotDict, analysedDataDict

def analyseManoeuvresCubicInterp(filenameList,windAngleList,windowSize):
    analysedDataDict = {}
    for i in range(0,len(filenameList)):
        cardinalWindAngle = windAngleList[i] #degrees
        trueWindSpeed = float(5.0) #m/s

        directory = filenameList[i].rsplit('/', 1)[0]
        filename = filenameList[i]
        outputfilename = "gps_data.csv"
        #outputfile = directory + "\\" + outputfilename
        outputfile = outputfilename

        manoeuvreLength=6 # seconds total
        colours = ['blue','magenta']
        nPoints = 501 # number of points in each graph

        gpsData = read_xml(inputFile=filename,outputFile=outputfile)

        xCoeffs = cubicSplineInterpolation(gpsData, 'g_x') # create surrogate cubic splines
        yCoeffs = cubicSplineInterpolation(gpsData, 'g_y')

        if windAngleList[i] != None and windAngleList[i] != '':
            weatherDataBoatLocation = manualWindInput(0,windAngleList[i],gpsData)
        else:
            weatherDataBoatLocation = weatherDataAtBoat(gpsData)
        tacks, gybes,manoeuvreData = identifyManoeuvresCubic(xCoeffs,yCoeffs,gpsData['time'], weatherDataBoatLocation)

        tackAnalysed = {}
        gybeAnalysed = {}
        avgTack = np.zeros(shape=(nPoints,6))
        avgGybe = np.zeros(shape=(nPoints,6))
        delKeys = []
        dictKeys=[]
        for manoeuvre_n in range(0,len(manoeuvreData)):
            repositioned = True
            tickCount = 0
            while repositioned and tickCount < 2: # number of repositions allowed
                repoAllowed = True
                manoeuvreWindow,manoeuvreData,localWindDirection,delkey,directionBefore = manoeuvreWindowExtractorCubic(xCoeffs,yCoeffs,gpsData,manoeuvreData,windowSize,manoeuvre_n,manoeuvreLength,repoAllowed)
                if not delkey:
                    tackAnalysed[manoeuvre_n], gybeAnalysed[manoeuvre_n]= manoeuvreAnalysisCubic(xCoeffs,yCoeffs,manoeuvreWindow,manoeuvre_n,manoeuvreData,gpsData['time'],windowSize,localWindDirection,directionBefore,nPoints)
                else:
                    tackAnalysed[manoeuvre_n] = {}
                    gybeAnalysed[manoeuvre_n] = {}
                tickCount += 1
            
            if delkey is not None:
                delKeys.append(True) # set key to delete manoeuvre if it is too short or invalid
                dictKeys.append(manoeuvre_n) # store the key to delete the manoeuvre
            else:
                delKeys.append(False)
        #doubleCheck(xCoeffs,yCoeffs,gpsData,manoeuvreData,localWindDirection)
        
        # delete flagged manoeuvres
        for dels in dictKeys:
            del tackAnalysed[dels]
            del gybeAnalysed[dels]
        
        manoeuvreData=manoeuvreData[~pd.Series(delKeys)]

        #doubleCheck(xCoeffs,yCoeffs,gpsData,manoeuvreData,localWindDirection)
        #print("Recommended cardinal wind angle: ",np.rad2deg(avgWindAngle))
        print("Averaging manoeuvres...")
        for manoeuvre_n in range(len(manoeuvreData)):
            avgTack,avgGybe = averageAnalysisCubic(tackAnalysed,gybeAnalysed,windowSize,manoeuvre_n,avgTack,avgGybe,nPoints)
        avgTack,avgGybe=averageManoeuvres(avgTack,avgGybe)

        #tackAnalysed['averages'] = tackAnalysed[:]
        #gybeAnalysed['averages'] = gybeAnalysed.mean(axis=0)
        tackPlotDict=tackPlots(tackAnalysed,windowSize,avgTack,tackPlotDict if i>0 else None,colours[i],filenameList[i].rsplit('/', 1)[1].rsplit('.', 1)[0])
        gybePlotDict=gybePlots(gybeAnalysed,windowSize,avgGybe,gybePlotDict if i>0 else None,colours[i],filenameList[i].rsplit('/', 1)[1].rsplit('.', 1)[0])

        analysedDataDict[i] = {'gpsData': gpsData, 'manoeuvreData': manoeuvreData, 'weatherDataBoatLocation': weatherDataBoatLocation, 'xCoeffs': xCoeffs, 'yCoeffs': yCoeffs}

    #analysedDataDict={'gpsData':gpsData,'manoeuvreData':manoeuvreData,'weatherDataBoatLocation':weatherDataBoatLocation}
    return tackPlotDict, gybePlotDict, analysedDataDict

def boundTimes(splineLower,splineUpper,t):
    '''
    Bounds the time into the current spline
    '''
    if t < splineLower:
        t = splineLower
    elif t > splineUpper:
        t = splineUpper
    return t

def manoeuvreWindowExtractorCubic(xCoeffs,yCoeffs,gpsData,manoeuvreData,windowSize,manoeuvre_n,manoeuvreLength,repoAllowed=True):
    '''
    Extracts the lower and upper bounds of t for each manoeuvre, based on a local wind direction around the manoeuvre.
    Repositions the manoeuvre to the middle of the window, within 0.01s
    '''
    if repoAllowed and manoeuvreData['time'].iloc[manoeuvre_n] < (gpsData['time'].iloc[-1] - pd.Timedelta(seconds=windowSize/2)):
        # Find the local wind direction
        # Find the associated splines and relevant time values (seconds since beginning of gpsData)
        splines = [find_neighbours(manoeuvreData['time'].iloc[manoeuvre_n]-pd.Timedelta(seconds=windowSize/2),gpsData['time']),find_neighbours(manoeuvreData['time'].iloc[manoeuvre_n]+pd.Timedelta(seconds=windowSize/2),gpsData['time'])]
        if splines[0][0]==None:
            splines[0]=(splines[0][1],splines[0][1]) # if the first spline is None, then use the second spline
        if splines[1][1]==None:
            splines[1]=(splines[1][0],splines[1][0])
        manoeuvreSpline = find_neighbours(manoeuvreData['time'].iloc[manoeuvre_n],gpsData['time'])[0] # find the spline for the manoeuvre
        t0 = gpsData['time'].iloc[0]
        tInit = manoeuvreData['time'].iloc[manoeuvre_n]-pd.Timedelta(seconds=windowSize/2) # start time of the manoeuvre window
        tPre = manoeuvreData['time'].iloc[manoeuvre_n]-pd.Timedelta(seconds=manoeuvreLength/2) # time at which manoeuvre starts
        tPost = manoeuvreData['time'].iloc[manoeuvre_n]+pd.Timedelta(seconds=manoeuvreLength/2) # time at which manoeuvre ends
        tEnd = manoeuvreData['time'].iloc[manoeuvre_n]+pd.Timedelta(seconds=windowSize/2) # end time of the manoeuvre window
        # Local wind direction is the average of angles before and after the manoeuvre (from -windowSize/2< t <manoeuvreTime-manoeuvreLength and the same on the other side of the manoeuvre)
        # Calculated by integrating the direction vector and dividing by the time axis
        integralBefore = np.zeros(shape=(2,1))
        integralAfter = np.zeros(shape=(2,1))

        if splines[0][0]==splines[1][0]:
            # single spline is involved - no need to do piecewise calc
            integralBefore = np.array([np.polyval(xCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tPre-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tPre-t0)/pd.Timedelta(seconds=1))])-np.array([np.polyval(xCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tInit-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tInit-t0)/pd.Timedelta(seconds=1))])
            integralAfter = np.array([np.polyval(xCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tEnd-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tEnd-t0)/pd.Timedelta(seconds=1))])-np.array([np.polyval(xCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tPost-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[splines[0][0]*4:splines[0][0]*4+3],(tPost-t0)/pd.Timedelta(seconds=1))])
        else:
            # multiple splines are involved, piecewise calc is necessary
            for spline in range(splines[0][0],manoeuvreSpline+1):
                # integrate across the start splines
                splinetInit = boundTimes(gpsData['time'].iloc[spline],gpsData['time'].iloc[spline+1],tInit)
                splinetPre = boundTimes(gpsData['time'].iloc[spline],gpsData['time'].iloc[spline+1],tPre)
                integralBefore += np.array([np.polyval(xCoeffs[spline*4:spline*4+4],(splinetPre-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[spline*4:spline*4+4],(splinetPre-t0)/pd.Timedelta(seconds=1))])-np.array([np.polyval(xCoeffs[spline*4:spline*4+4],(splinetInit-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[spline*4:spline*4+4],(splinetInit-t0)/pd.Timedelta(seconds=1))])
            for spline in range(manoeuvreSpline,splines[1][0]+1):
                if spline == len(gpsData['time'])-1:
                    spline-=1
                # integrate across the following splines
                splinetPost = boundTimes(gpsData['time'].iloc[spline],gpsData['time'].iloc[spline+1],tPost)
                splinetEnd = boundTimes(gpsData['time'].iloc[spline],gpsData['time'].iloc[spline+1],tEnd)
                integralAfter += np.array([np.polyval(xCoeffs[spline*4:spline*4+4],(splinetEnd-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[spline*4:spline*4+4],(splinetEnd-t0)/pd.Timedelta(seconds=1))])-np.array([np.polyval(xCoeffs[spline*4:spline*4+4],(splinetPost-t0)/pd.Timedelta(seconds=1)),np.polyval(yCoeffs[spline*4:spline*4+4],(splinetPost-t0)/pd.Timedelta(seconds=1))])
        
        directionBefore = integralBefore/((windowSize-manoeuvreLength)/2) # divide by time length
        directionAfter = integralAfter/((windowSize-manoeuvreLength)/2)
        
        directionBeforeNorm = directionBefore/np.linalg.norm(directionBefore) # normalise the direction vectors
        directionAfterNorm = directionAfter/np.linalg.norm(directionAfter)

        if np.remainder(np.rad2deg(np.arctan2(directionAfterNorm[0],directionAfterNorm[1]))-np.rad2deg(np.arctan2(directionBeforeNorm[0],directionBeforeNorm[1])),360)<180: # there is a weird condition here that needs tobe cleaned up - what happens when we snap across the 0 degree line? np.remainder(manoeuvreWindow.iloc[len(manoeuvreWindow)-1]['angle']-manoeuvreWindow.iloc[0]['angle'])
            direction = 'right'
            localWindDirection =  np.rad2deg(np.arctan2(directionBeforeNorm[0],directionBeforeNorm[1]))+np.arccos(np.sum(np.multiply(directionBeforeNorm,directionAfterNorm)))*90/np.pi # turning right - bisects the turning angle
        else:
            direction = 'left'
            localWindDirection =  np.rad2deg(np.arctan2(directionBeforeNorm[0],directionBeforeNorm[1]))-np.arccos(np.sum(np.multiply(directionBeforeNorm,directionAfterNorm)))*90/np.pi # turning left - bisects the turning angle
        # local wind direction has been found. now reposition the manoeuvre by solving for the local wind direction
        storeTack = manoeuvreData.iloc[manoeuvre_n]['tack']
        if not manoeuvreData.iloc[manoeuvre_n]['tack']:
            localWindDirection+=180
        newRow,delkey = identifySingleManoeuvreCubic(xCoeffs,yCoeffs,gpsData['time'],windowSize,manoeuvreData['time'].iloc[manoeuvre_n], localWindDirection if manoeuvreData.iloc[manoeuvre_n]['tack'] else localWindDirection+180,splines)
        newRow['tack']= storeTack # restore the tack value (corrupted by single manoeuvre identification direction vector)
        manoeuvreData.iloc[manoeuvre_n] = newRow if newRow['time'] !=[] else manoeuvreData.iloc[manoeuvre_n]

    manoeuvreWindow = [manoeuvreData['time'].iloc[manoeuvre_n]-pd.Timedelta(seconds=windowSize/2),manoeuvreData['time'].iloc[manoeuvre_n]+pd.Timedelta(seconds=windowSize/2)]
    if manoeuvreWindow[1] > gpsData['time'].iloc[-2]:
        delkey = True
        localWindDirection = [999]
        directionBefore = 999
    return manoeuvreWindow,manoeuvreData,localWindDirection[0],delkey,directionBefore

def manoeuvreAnalysisCubic(xCoeffs,yCoeffs,manoeuvreWindow,manoeuvre_n,manoeuvreData,gpsTime,windowSize,localWindDirection,directionBefore,nPoints=501):
    spline = find_neighbours(manoeuvreWindow[0],gpsTime)[0] # find the first spline for the manoeuvre
    t0 = gpsTime.iloc[0] # time of the first gps point
    boatspeed = np.zeros(nPoints) # boatspeed in m/s
    twa = np.zeros(nPoints) # true wind angle in degrees
    vmg = np.zeros(nPoints) # velocity made good in m/s
    metresLost = np.zeros(nPoints) # metres lost in m
    time = np.linspace(-windowSize/2,windowSize/2,nPoints) # time in seconds of manoeuvreWindow
    windVector = np.array([np.sin(np.deg2rad(localWindDirection)),np.cos(np.deg2rad(localWindDirection))]) # unit wind vector in the local wind direction
    vmgBefore = np.dot(directionBefore.T,windVector) # velocity made good before the manoeuvre in m/s
    pos0 = f((manoeuvreWindow[0]-t0)/pd.Timedelta(seconds=1),xCoeffs,yCoeffs,spline) # initial position vector at the start of the manoeuvre window

    for i in range(0,nPoints):
        t = i*windowSize/nPoints+ (manoeuvreWindow[0]-t0)/pd.Timedelta(seconds=1) # time in seconds since the start of the gps data
        if t0+pd.Timedelta(seconds=t) > gpsTime.iloc[spline+1]:
            spline+=1 # if the time is greater than the current spline, move to the next spline
        if spline >= len(gpsTime)-1: # if the spline is out of bounds, break
            singleTackAnalysed = {}
            singleGybeAnalysed = {}
            break
        # evaluate boat direction vector at time t:
        boatVector = f_1(t,xCoeffs,yCoeffs,spline)
        boatspeed[i]=np.linalg.norm(boatVector)
        twa[i]= np.rad2deg(np.arctan2(boatVector[0][0],boatVector[1][0]))-localWindDirection
        twa[i] = np.remainder(twa[i],360)
        
        vmg[i] = np.dot(boatVector.T,windVector)[0]
        posT = f(t,xCoeffs,yCoeffs,spline) # position vector at time t
        cmg = posT - pos0 # course made good vector
        metresLost[i] = vmgBefore[0]*(time[i]+windowSize/2)-np.dot(cmg.T,windVector)[0] # metres lost in the manoeuvre. cmg dot windVector gives direction travelled in direction of the wind
    
    twa[twa>180] = twa[twa>180]-360 # convert to -180 to 180 degrees
    twa = abs(twa) # convert to 0 to 180 degrees
    if manoeuvreData.iloc[manoeuvre_n]['tack']:
        singleTackAnalysed = {'time':time,'boatspeed':boatspeed,'vmg':vmg,'twa':twa,'metresLost':metresLost}
        singleGybeAnalysed = {}
    else:
        singleTackAnalysed = {}
        singleGybeAnalysed = {'time':time,'boatspeed':boatspeed,'vmg':-vmg,'twa':twa,'metresLost':-metresLost}

    return singleTackAnalysed,singleGybeAnalysed


if __name__ == "__main__":
    browseData=passToTk()
    browseData.filenameList=["C:/Users/matth/Documents/SailAnalyser/2025_06_15 OSC Race 2.gpx","C:/Users/matth/Downloads/moGPXTracker_20250709033732.gpx"]
    browseData.initialdir = "/"  # Initial directory for file dialog
    #app_window = fileSelectionWindow()
    #app_window.mainloop()  # Start the Tkinter event loop
    windAngleList=[None,None]
    windowSize=30
    filenameList = browseData.filenameList
    tackPlotDict, gybePlotDict, analysedDataDict=analyseManoeuvresCubicInterp(filenameList, windAngleList,windowSize)
    plt.show()