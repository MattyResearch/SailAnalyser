import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from xmlReader import read_xml
from decimal import Decimal,getcontext
from historicalWeatherData import weatherDataAtBoat
import datetime as dt
from cubicInterpolation import find_neighbours,cubicSplineInterpolation,newtons_method,h,f_1

def calculateVelocity(gpsData):
    """
    Calculate speed and heading from GPS data.
    """
    rows = []
    xdiff = np.diff(gpsData['g_x'])
    ydiff = np.diff(gpsData['g_y'])
    timeDiff = gpsData['time'].diff()
    for i in range(0, len(gpsData)-1):
        if i == 0:
            angle = 90-np.arctan2(ydiff[i+1],xdiff[i+1]) * (180 / np.pi)+360
            speed = np.sqrt(xdiff[i+1]**2+ydiff[i+1]**2)/timeDiff[i+1].total_seconds() # m/s
        else:
            if xdiff[i] == 0:
                if ydiff[i] > 0:
                    angle = 0
                else:
                    angle = 180
            else:
                angle = 90-np.arctan2(ydiff[i],xdiff[i]) * (180 / np.pi)+360
            speed = np.sqrt(xdiff[i]**2+ydiff[i]**2)/timeDiff[i].total_seconds() # m/s
        angle = np.remainder(angle, 360)

        rows.append({'time': gpsData['time'][i+1], 'lat': gpsData['lat'][i+1], 'lon': gpsData['lon'][i+1],'g_x': gpsData['g_x'][i+1], 'g_y': gpsData['g_y'][i+1], 'speed': speed, 'angle': angle})
    #gpsData['velocity'] = dist2.sqrt()
    df_cols = ['time','lat','lon','g_x','g_y','speed','angle']
    gpsData = pd.DataFrame(rows, columns=df_cols)
    return gpsData

def identifyManoeuvres(gpsData, weatherData):
    """
    Identify manoeuvres based on GPS data and wind conditions.
    """
    print("Identifying manoeuvres...")
    manoeuvreData = []
    n=0
    timeInitialUnaware = gpsData['time'][0]
    timeInitialAware = timeInitialUnaware.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for row in gpsData.iterrows():
        if row[0] == len(gpsData)-1:
            break
        cardinalWindAngle = np.interp((row[1].time-timeInitialUnaware)/dt.timedelta(seconds=1), (weatherData['date']-timeInitialAware)/dt.timedelta(seconds=1), weatherData['wind_direction_10m'])
        if np.sin((row[1].angle-cardinalWindAngle)*np.pi/180)*np.sin((gpsData['angle'][row[0]+1]-cardinalWindAngle)*np.pi/180)< 0 and np.mean([row[1]['speed'],gpsData['speed'][row[0]+1]]) > 0.2:# and np.cos(np.deg2rad((row[1].angle-gpsData['angle'][row[0]+1]))) < np.cos(np.pi/18):# and row[1]['speed'] > 0.5:
            manoeuvreData.append(row[1])
            manoeuvreData[n]['row'] = row[0]
            if np.cos(((row[1].angle+gpsData['angle'][row[0]+1])/2-cardinalWindAngle)*np.pi/180)>0:
                manoeuvreData[n]['tack'] = True
            else:
                manoeuvreData[n]['tack'] = False
            n=n+1
            

    manoeuvreData = pd.DataFrame(manoeuvreData, columns=['time','lat','lon','g_x','g_y','speed','angle','tack','row'])
    tacks = manoeuvreData.loc[manoeuvreData.tack]
    gybes = manoeuvreData.loc[~manoeuvreData.tack]
    print(len(tacks)," tacks found")
    print(len(gybes), "gybes found")
    return tacks, gybes, manoeuvreData

def identifyManoeuvresCubic(xCoeffs,yCoeffs,gpsTime, weatherData):
    """
    Identify manoeuvres based on GPS data and wind conditions.
    """
    print("Identifying manoeuvres...")
    manoeuvreDataCubic = {'time': [], 'spline': [], 'tack': []}
    n=0
    timeInitialUnaware = gpsTime[0]
    timeInitialAware = timeInitialUnaware.replace(tzinfo=weatherData.iloc[0]['date'].tzinfo)
    for t in range(1,int((gpsTime.iloc[-1]-timeInitialUnaware)/dt.timedelta(seconds=1))): # increment in seconds
        if t==1:
            prev_spline = find_neighbours(gpsTime[0]+pd.Timedelta(seconds=t-1), gpsTime)[0] # find the index of the closest time point before this time. 
            prev_gpsVector = np.array([3*xCoeffs[prev_spline*4]*t**2+2*xCoeffs[prev_spline*4+1]*t+xCoeffs[prev_spline*4+2], 3*yCoeffs[prev_spline*4]*t**2+2*yCoeffs[prev_spline*4+1]*t+yCoeffs[prev_spline*4+2]])
            prev_gpsAngle = 90-np.rad2deg(np.arctan2(prev_gpsVector[1],prev_gpsVector[0]))+360
        else:
            prev_spline = spline
            prev_gpsVector = gpsVector
            prev_gpsAngle = gpsAngle

        # interpolate to find wind angle
        cardinalWindAngle = np.interp(t, (weatherData['date']-timeInitialAware)/dt.timedelta(seconds=1), weatherData['wind_direction_10m'])
        spline = find_neighbours(gpsTime[0]+pd.Timedelta(seconds=t), gpsTime)[0] # find the index of the closest time point before this time. 
        gpsVector = np.array([3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2], 3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2]])
        gpsAngle = 90-np.rad2deg(np.arctan2(gpsVector[1],gpsVector[0]))

        # if sin of the angle difference changes sign, then a tack or gybe has occurred within the previous second
        if np.sin((gpsAngle-cardinalWindAngle)*np.pi/180)*np.sin((prev_gpsAngle-cardinalWindAngle)*np.pi/180)< 0:# and np.mean([np.sqrt(np.dot(prev_gpsVector.T,prev_gpsVector)),np.sqrt(np.dot(gpsVector.T,gpsVector))]) > 0.2:
            manoeuvreDataCubic['time'].append(gpsTime[0]+pd.Timedelta(seconds=t))
            manoeuvreDataCubic['spline'].append(spline)

            if np.cos((gpsAngle-cardinalWindAngle)*np.pi/180)>0:
                manoeuvreDataCubic['tack'].append(True)
            else:
                manoeuvreDataCubic['tack'].append(False)

            n=n+1
            
    manoeuvreDataCubic = pd.DataFrame(manoeuvreDataCubic, columns=['time','spline','tack'])
    tacks = manoeuvreDataCubic.loc[manoeuvreDataCubic.tack]
    gybes = manoeuvreDataCubic.loc[~manoeuvreDataCubic.tack]
    print(len(tacks)," tacks found")
    print(len(gybes), "gybes found")
    return tacks, gybes, manoeuvreDataCubic

def identifySingleManoeuvreCubic(xCoeffs,yCoeffs,gpsTime,windowSize,manoeuvre, localWindDirection,splines,manoeuvreSpline):
    """
    Identify manoeuvre based on GPS data and wind conditions.
    Solve for t where direction vector = local wind direction.
    """
    manoeuvreDataCubic = {'time': [], 'spline': [], 'tack': []}
    directionVector = np.array([np.sin(np.deg2rad(localWindDirection)),np.cos(np.deg2rad(localWindDirection))])
    maxIter = 20
    convergenceCriterion = 0.01 # seconds
    t0 = gpsTime[0]
    for tGuess in [0,-0.5,0.5]: # try t=0, t=-0.5 and t=0.5 seconds from the manoeuvre time
        for spline in manoeuvreSpline+np.array([0,-1,1,-2,2,-3,3,-4,4,-5,5]): # search outward from central spline
            if spline < splines[0][0] or spline > splines[1][0]:
                continue
            t = np.ones(shape=(2,1))*((manoeuvre-t0+pd.Timedelta(seconds=tGuess))/pd.Timedelta(seconds=1)) # time in seconds for x & y
            tPrev=t.copy()
            i=0
            converged=False
            while i < maxIter:
                # find the time at which the direction vector is equal to the local wind direction
                # MUST be separate for x & y, as the splines may not be the same
                t[0]=newtons_method(xCoeffs[:,0],yCoeffs[:,0],spline, t[0], directionVector)[0] # t is the time in seconds
                t[1]=newtons_method(xCoeffs[:,0],yCoeffs[:,0],spline, t[1], directionVector)[1] # t is the time in seconds
                if tPrev[0] - t[0] < convergenceCriterion: # if the time has not changed significantly in x then check y
                    if (tPrev[1] - t[1] < convergenceCriterion and abs(t[0,0]-t[1,0]) < convergenceCriterion) or (h(t[0]+convergenceCriterion/2,xCoeffs,yCoeffs,spline,directionVector)[1]*h(t[0]-convergenceCriterion/2,xCoeffs,yCoeffs,spline,directionVector)[1]) <= 0: # cross-evaluates to avoid potential osciallations in N-R
                        # if the sign changes then a root is found
                        if t[0] <= (gpsTime[spline+1]-t0)/pd.Timedelta(seconds=1) and t[0] >= (gpsTime[spline]-t0)/pd.Timedelta(seconds=1):
                            t[1]=t[0] # if x converged, then set y to x
                            converged=True
                            break
                        else:
                            #print("Warning: solution not within spline range for spline", spline)
                            break
                elif tPrev[1] - t[1] < convergenceCriterion: # if the time has not changed significantly in x then check y
                    if (tPrev[0] - t[0] < convergenceCriterion and abs(t[0,0]-t[1,0]) < convergenceCriterion) or h(t[1]+convergenceCriterion/2,xCoeffs,yCoeffs,spline,directionVector)[0]*h(t[1]-convergenceCriterion/2,xCoeffs,yCoeffs,spline,directionVector)[0] <= 0: # cross-evaluates to avoid potential osciallations in N-R
                        # if the sign changes then a root is found
                        if t[1] <= (gpsTime[spline+1]-t0)/pd.Timedelta(seconds=1) and t[1] >= (gpsTime[spline]-t0)/pd.Timedelta(seconds=1):
                            t[0]=t[1] # if y converged, then set x to y
                            converged=True
                            break
                        else:
                            #print("Warning: solution not within spline range for spline", spline)
                            break
                i+=1
                tPrev=t.copy()
                if i == maxIter-1: # if maximum iterations reached, then warn
                    #print("Warning: maximum iterations reached for spline", spline,". Not converged.")
                    pass
            if converged:
                print("Converged for spline", spline, "at time", t0+pd.Timedelta(seconds=t[0,0]))
                delkey = None
                break # if solution is converged, break out of loop
        if converged:
            break # if solution is converged, break out of loop       
        elif tGuess != 0.5:
            #print("Warning: no solution found for manoeuvre at time", manoeuvre,"\nTrying new initial guess.")
            pass
    if not converged:
        print("N-R convergence failed for manoeuvre at time", manoeuvre,"- using Binary Search")
        delkey = manoeuvre
        converged,delkey,manoeuvre=binarySearch(xCoeffs,yCoeffs,gpsTime,directionVector, manoeuvre,windowSize/(2**10),windowSize)
        t = np.ones(shape=(2,1))*((manoeuvre-t0)/pd.Timedelta(seconds=1)) # time in seconds


    # interpolate to find wind angle
    t=t[0,0] # both times should be the same, so take one
    spline = find_neighbours(t0+pd.Timedelta(seconds=t), gpsTime)[0] # find the index of the closest time point before this time. 
    gpsVector = np.array([3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2], 3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2]])
    gpsAngle = 90-np.rad2deg(np.arctan2(gpsVector[1],gpsVector[0]))

    manoeuvreDataCubic['time']=(t0+pd.Timedelta(seconds=t))
    manoeuvreDataCubic['spline']=(spline)
    if np.cos((gpsAngle-localWindDirection)*np.pi/180)>0:
        manoeuvreDataCubic['tack']=True
    else:
        manoeuvreDataCubic['tack']=False
    
    afterManoeuvreT = t+windowSize/4
    slowCount=0
    tickCount=0
    while afterManoeuvreT <= t+windowSize/2:
        slowSpline=find_neighbours(t0+pd.Timedelta(seconds=afterManoeuvreT), gpsTime)[0] # find the index of the closest time point before this time.
        if slowSpline >= len(gpsTime)-1:
            break
        gpsVector = f_1(afterManoeuvreT,xCoeffs,yCoeffs,slowSpline)
        if np.linalg.norm(gpsVector) < 0.5: # if the speed is too low, then ignore the manoeuvre (assume capsize or other problem)
            slowCount+=1
        tickCount+=1
        afterManoeuvreT+=windowSize/16
    if slowCount/tickCount>=0.75:
        print("Manoeuvre in spline",spline,"at time", manoeuvreDataCubic['time'],"has low exit speed, ignoring")
        delkey = manoeuvre
    manoeuvreDataCubic = pd.Series(manoeuvreDataCubic)
    return manoeuvreDataCubic,delkey

def binarySearch(xCoeffs,yCoeffs,gpsTime,windVector, manoeuvre,tolerance,windowSize):
    # use binary search to find approximate manoeuvre time
    t0 = gpsTime[0]
    low = (manoeuvre-t0)/pd.Timedelta(seconds=1)-windowSize/2
    high = (manoeuvre-t0)/pd.Timedelta(seconds=1)+windowSize/2
    converged=False
    delkey=None
    windAngle = np.rad2deg(np.arctan2(windVector[0],windVector[1]))
    while high-low >= tolerance:
        mid=(low+high)/2
        lowVector = f_1(low,xCoeffs,yCoeffs,find_neighbours(t0+pd.Timedelta(seconds=low), gpsTime)[0])
        midVector = f_1(mid,xCoeffs,yCoeffs,find_neighbours(t0+pd.Timedelta(seconds=mid), gpsTime)[0])
        highVector = f_1(high,xCoeffs,yCoeffs,find_neighbours(t0+pd.Timedelta(seconds=high), gpsTime)[0])
        lowAngle = np.rad2deg(np.arctan2(lowVector[0],lowVector[1]))
        midAngle = np.rad2deg(np.arctan2(midVector[0],midVector[1]))
        highAngle = np.rad2deg(np.arctan2(highVector[0],highVector[1]))
        
        if np.sin(np.deg2rad(windAngle-lowAngle))*np.sin(np.deg2rad(windAngle-midAngle)) < 0:
            # if sin changes sign then a manoeuvre exists in the first half
            if np.sin(np.deg2rad(windAngle-highAngle))*np.sin(np.deg2rad(windAngle-midAngle)) < 0:
                # there is a manoeuvre in both halves - choose the one which contains the initial manoeuvre time
                if mid-(manoeuvre-t0)/pd.Timedelta(seconds=1) > 0:
                    high=mid
                else:
                    low=mid
            else:
                high=mid
        else:
            low=mid
    if np.sin(np.deg2rad(windAngle-highAngle))*np.sin(np.deg2rad(windAngle-lowAngle)) < 0:
        converged=True
        return converged,None,t0+pd.Timedelta(seconds=mid)
    else:
        print("!!! WARNING: no solution found for manoeuvre at time", manoeuvre,"!!!")
        delkey = manoeuvre
        return converged,delkey,manoeuvre

def doubleCheck(xCoeffs,yCoeffs,gpsData,manoeuvreData,cardinalWindAngle,*args):
    """
    Plot data and angles
    """
    #doubleCheckPlot=plt.plot(gpsData['g_x'], gpsData['g_y'])
    t0 = gpsData['time'][0]
    npoints= len(gpsData['time'])
    for i in range(0, npoints-1):
        tCommon = (gpsData['time'][i]-t0)/pd.Timedelta(seconds=1)
        t = np.linspace(tCommon, (gpsData['time'][i+1]-t0)/pd.Timedelta(seconds=1), 50)
        plt.plot(xCoeffs[i*4]*t**3+xCoeffs[i*4+1]*t**2+xCoeffs[i*4+2]*t+xCoeffs[i*4+3],yCoeffs[i*4]*t**3+yCoeffs[i*4+1]*t**2+yCoeffs[i*4+2]*t+yCoeffs[i*4+3], color='blue')
    plt.title('GPS Track')
    plt.xlabel('Distance from start (m)')
    plt.ylabel('Distance from start (m)')
    plt.axis('equal')
    plt.axis('square')
    plt.tick_params(axis='both', which='major', labelsize=10)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
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
    plt.scatter(np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0], np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1], color='green', label='Manoeuvres')
    #plt.show()
    plt.scatter((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[manoeuvreData['tack']], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[manoeuvreData['tack']], color='red', label='Tacks')
    plt.scatter((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[~manoeuvreData['tack']], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[~manoeuvreData['tack']], color='blue', label='Gybes')
    for manoeuvre in range(0,len(manoeuvreData['time'])):
        t=(manoeuvreData['time'].iloc[manoeuvre]-t0)/pd.Timedelta(seconds=1) # time in seconds
        spline = find_neighbours(gpsData['time'][0]+pd.Timedelta(seconds=t), gpsData['time'])[0] # find the index of the closest time point before this time. 
        gpsVector = np.array([3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2], 3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2]])
        pos=((np.multiply(a[0],tList3)+np.multiply(b[0],tList2)+np.multiply(c[0],tList)+d[0])[manoeuvre], (np.multiply(a[1],tList3)+np.multiply(b[1],tList2)+np.multiply(c[1],tList)+d[1])[manoeuvre])
        plt.annotate("",xytext=pos,xy=(pos[0]+gpsVector[0]*40,pos[1]+gpsVector[1]*40),arrowprops=dict(arrowstyle="->",lw=1.5,color='black'),fontsize=7, ha='center', va='center')
    plt.annotate("TWA",xytext=(np.sin(np.pi+cardinalWindAngle*np.pi/180)*400,np.cos(np.pi+cardinalWindAngle*np.pi/180)*400),xy=(0,0),arrowprops=dict(arrowstyle="->",lw=1.5,color='black'),fontsize=7, ha='center', va='center')
    plt.legend()
    plt.show(block=True)

if __name__ == "__main__":
    directory = "C:\\Users\\matth\\Downloads"
    filename = "25_08_17 OSC Feva Helming.gpx"
    outputfilename = "gps_data_directions.csv"
    outputfile = directory + "\\" + outputfilename
    inputfile = directory + "\\" + filename
    cardinalWindAngle = float(85) #degrees
    trueWindSpeed = float(5.0) #m/s

    gpsData = read_xml(inputFile=inputfile,outputFile=outputfile)
    gpsData = calculateVelocity(gpsData)
    gpsData.to_csv(outputfile, index=False)
    weatherDataBoatLocation = weatherDataAtBoat(gpsData)
    xCoeffs = cubicSplineInterpolation(gpsData, 'g_x') # create surrogate cubic splines
    yCoeffs = cubicSplineInterpolation(gpsData, 'g_y')
    tacks, gybes,manoeuvreDataCubic = identifyManoeuvresCubic(xCoeffs,yCoeffs,gpsData['time'], weatherDataBoatLocation)
    doubleCheck(xCoeffs,yCoeffs,gpsData,manoeuvreDataCubic,cardinalWindAngle)