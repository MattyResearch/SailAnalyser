import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from xmlReader import read_xml

def cubicSplinePositionMatrix(z,t):
    '''
    z = numpy array of two position points (bounding the spline)
    t = numpy array of time parameter (bounding the spline)
    Returns 4x2 matrix of of time values and 2x1 vector of position values
    '''

    T = np.ndarray(shape=(2,4),dtype=float)
    T=[[t[0]**3,t[0]**2,t[0],1],[t[1]**3,t[1]**2,t[1],1]]
    X = np.ndarray(shape=(2,1),dtype=float)
    X=[z[0],z[1]]

    return T,X

def cubicSplineDerivativeMatrix(t):
    '''
    Position data is not needed, only time parameter, since d/dx 1 = d/dx 2 => d/dx 1 - d/dx 2 = 0
    t = numpy array of one time parameter (common to adjacent splines)
    Returns 1x8 matrix of time values and 1x1 vector of zero
    '''

    #T = np.ndarray(shape=(1,8),dtype=float)
    T=[3*t**2,2*t,1,0,-3*t**2,-2*t,-1,0]
    X = np.ndarray(shape=(1,1),dtype=float)
    X=[0]

    return T,X

def cubicSplineSecondDerivativeMatrix(t):
    '''
    Position data is not needed, only time parameter, since d/dx 1 = d/dx 2 => d/dx 1 - d/dx 2 = 0
    t = numpy array of one time parameter (common to adjacent splines)
    Returns 1x8 matrix of time values and 1x1 vector of zero
    '''

    #T = np.ndarray(shape=(1,8),dtype=float)
    T=[6*t,2,0,0,-6*t,-2,0,0]
    X = np.ndarray(shape=(1,1),dtype=float)
    X=[0]

    return T,X

def cubicSplineNaturalBCsMatrix(t):
    '''
    Position data is not needed, only time parameter, since d/dx 1 = d/dx 2 => d/dx 1 - d/dx 2 = 0
    t = numpy array of one time parameter (boundary node)
    Returns 1x4 matrix of time values and 1x1 vector of zero
    '''

    #T = np.ndarray(shape=(1,8),dtype=float)
    T=[6*t,2,0,0]
    X = np.ndarray(shape=(1,1),dtype=float)
    X=[0]

    return T,X

def cubicSplineContinuation(z1,z2,z,t):
    '''
    z = numpy array of two position points (z[0] is common)
    t = numpy array of time parameter (t[0] is common)
    z1 = first derivative at common point (t[0])
    z2 = second derivative at common point (t[0])
    Returns cubic spline coefficients for one point z[1] at time t[1]
    Requires two new points and one coincident spline (this gives more information to the spline)
    '''

    T = np.ndarray(shape=(4,4),dtype=float)
    T=[[t[1]**3,t[1]**2,t[1],1],[t[0]**3,t[0]**2,t[0],1],[3*t[0]**2,2*t[0],1,0],[6*t[0],2,0,0]]
    X = np.ndarray(shape=(4,1),dtype=float)
    X=[z[1],z[0],z1,z2]
    coeffs = np.ndarray(shape=(1,4),dtype=float)
    coeffs[0,:] = np.linalg.solve(T,X)

    return coeffs

def firstCubicSpline(z,t):
    '''
    z = numpy array of four position points
    t = numpy array of time parameter
    Returns cubic spline coefficients for four points
    '''

    T = np.ndarray(shape=(4,4),dtype=float)
    T=[[t[0]**3,t[0]**2,t[0],1],[t[1]**3,t[1]**2,t[1],1],[t[2]**3,t[2]**2,t[2],1],[t[3]**3,t[3]**2,t[3],1]]
    X = np.ndarray(shape=(4,1),dtype=float)
    X=[z[0],z[1],z[2],z[3]]
    coeffs = np.linalg.solve(T,X)
    coeffsOut = np.ndarray(shape=(4,4),dtype=float)
    coeffsOut[0:] = coeffs

    return coeffsOut

def cubicSplineInterpolation(gpsData,chosenVariable):
    '''
    gpsData = pandas DataFrame with columns 'time' and <chosenVariable> i.e. 'g_x', 'g_y', 'lat', 'lon'
    '''
# Initialise variable & allocate array sizes
    t0 = gpsData['time'][0]

    npoints = len(gpsData['time']) # number of data points - there are n-1 splines

    Tpos = np.zeros(shape=((npoints-1)*2,(npoints-1)*4),dtype=float) # two position constraints per spline
    Xpos = np.zeros(shape=((npoints-1)*2,1),dtype=float) # two position constraints per spline

    TfirstDerivative = np.zeros(shape=(npoints-2,(npoints-1)*4),dtype=float) # one derivative constraint per spline
    XfirstDerivative = np.zeros(shape=(npoints-2,1),dtype=float) # one derivative constraint per spline

    TsecondDerivative = np.zeros(shape=((npoints-2),(npoints-1)*4),dtype=float) # one second derivative constraint per spline
    XsecondDerivative = np.zeros(shape=((npoints-2),1),dtype=float) # one second derivative constraint per spline

    T_BCs = np.zeros(shape=(2,(npoints-1)*4),dtype=float) # one second derivative constraint per spline
    X_BCs = np.zeros(shape=(2,1),dtype=float) # one second derivative constraint per spline

    for i in range(0,npoints-2): # is is the spline index, beginning at 0
        Tpos[i*2:i*2+2,i*4:i*4+4],Xpos[i*2:i*2+2,0]=cubicSplinePositionMatrix((gpsData[chosenVariable][i:i+2]).to_numpy(), ((gpsData['time'][i:i+2]-t0)/pd.Timedelta(seconds=1)).to_numpy())
        [TfirstDerivative[i,i*4:i*4+8],XfirstDerivative[i]] = cubicSplineDerivativeMatrix((gpsData['time'][i+1]-t0)/pd.Timedelta(seconds=1)) # point i+1 is common between this spline and the next
        [TsecondDerivative[i,i*4:i*4+8],XsecondDerivative[i]] = cubicSplineSecondDerivativeMatrix((gpsData['time'][i+1]-t0)/pd.Timedelta(seconds=1)) # point i+1 is common between this spline and the next
    # last spline
    i=npoints-2
    Tpos[i*2:i*2+2,i*4:i*4+4],Xpos[i*2:i*2+2,0]=cubicSplinePositionMatrix((gpsData[chosenVariable][i:i+2]).to_numpy(), ((gpsData['time'][i:i+2]-t0)/pd.Timedelta(seconds=1)).to_numpy())

    [T_BCs[0,0:4],X_BCs[0]]= cubicSplineNaturalBCsMatrix((gpsData['time'][0]-t0)/pd.Timedelta(seconds=1)) # first spline has natural boundary conditions
    [T_BCs[1,(npoints-2)*4:(npoints-1)*4+1],X_BCs[1]]= cubicSplineNaturalBCsMatrix((gpsData['time'][npoints-1]-t0)/pd.Timedelta(seconds=1)) # last spline has natural boundary conditions

    T = np.append(Tpos,TfirstDerivative,axis=0)
    T = np.append(T,TsecondDerivative,axis=0)
    T = np.append(T,T_BCs,axis=0)
    X = np.append(Xpos,XfirstDerivative,axis=0)
    X = np.append(X,XsecondDerivative,axis=0)
    X = np.append(X,X_BCs,axis=0)

    return np.linalg.solve(T,X)

def find_neighbours(value, df):
    exactmatch = df[df == value]
    if not exactmatch.empty:
        return exactmatch.index[0],None
    else:
        lowerneighbour_ind = [df[df < value].idxmax()]
        upperneighbour_ind = [df[df > value].idxmin()]
        return lowerneighbour_ind[-1], upperneighbour_ind[0]
    
def a(t,xCoeffs,yCoeffs,spline):
    return (3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2])**2+(3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2])**2

def a_1(t,xCoeffs,yCoeffs,spline):
    return 2*(3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2])*(6*xCoeffs[spline*4]*t+2*xCoeffs[spline*4+1])+2*(3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2])*(6*yCoeffs[spline*4]*t+2*yCoeffs[spline*4+1])

def g(t,xCoeffs,yCoeffs,spline):
    return a(t,xCoeffs,yCoeffs,spline)**0.5

def g_1(t,xCoeffs,yCoeffs,spline):
    return 0.5*a(t,xCoeffs,yCoeffs,spline)**(-0.5)*a_1(t,xCoeffs,yCoeffs,spline)

def f(t,xCoeffs,yCoeffs,spline):
    '''
    f(t) is the boat position at time t
    therefore f(t) - windUnitVector*|f(t)|=0
    evaluates boat position at time t, for a known spline
    '''
    return np.array([np.polyval(xCoeffs[spline*4:spline*4+4],t),np.polyval(yCoeffs[spline*4:spline*4+4],t)])

def f_1(t,xCoeffs,yCoeffs,spline):
    '''
    f(t) is the boat position at time t
    therefore f_1(t) - windUnitVector*|f_1(t)|=0
    evaluates boat direction vector at time t, for a known spline
    '''
    return np.array([3*xCoeffs[spline*4]*t**2+2*xCoeffs[spline*4+1]*t+xCoeffs[spline*4+2],3*yCoeffs[spline*4]*t**2+2*yCoeffs[spline*4+1]*t+yCoeffs[spline*4+2]])

def f_2(t,xCoeffs,yCoeffs,spline):
    # second derivative of f(t)
    return np.array([6*xCoeffs[spline*4]*t+2*xCoeffs[spline*4+1],6*yCoeffs[spline*4]*t+2*yCoeffs[spline*4+1]])

def h(t,xCoeffs,yCoeffs,spline,directionVector):
    '''
    h(t) = f_1(t) - directionVector*g(t) = 0 at the root
    '''
    return f_1(t,xCoeffs,yCoeffs,spline)-directionVector*g(t,xCoeffs,yCoeffs,spline)

def newtons_method(xCoeffs,yCoeffs,spline, t, directionVector):
    '''
    coeffs = cubic spline coefficients
    t = time parameter
    directionVector = local wind direction vector
    Returns time where the direction vector is equal to the local wind direction
    '''
    # t1 = t0-h(0)/h_1(0)
    h = f_1(t,xCoeffs,yCoeffs,spline)-directionVector*g(t,xCoeffs,yCoeffs,spline)
    h_1 = f_2(t,xCoeffs,yCoeffs,spline)-directionVector*g_1(t,xCoeffs,yCoeffs,spline)
    t1=t-np.divide(h,h_1)
    return t1

if __name__ == "__main__":
    # Test case
    filename = "2025_06_15 OSC Race 1.gpx"
    outputfile = "gpsData.csv"
    gpsData = read_xml(inputFile=filename,outputFile=outputfile) # pandas DataFrame
    npoints = len(gpsData['time'])
    t0 = gpsData['time'][0]  # time of first point

    xCoeffs = cubicSplineInterpolation(gpsData, 'g_x')
    yCoeffs = cubicSplineInterpolation(gpsData, 'g_y')

    for i in range(0, npoints-1):
        tCommon = (gpsData['time'][i]-t0)/pd.Timedelta(seconds=1)
        t = np.linspace(tCommon, (gpsData['time'][i+1]-t0)/pd.Timedelta(seconds=1), 50)
        plt.plot(xCoeffs[i*4]*t**3+xCoeffs[i*4+1]*t**2+xCoeffs[i*4+2]*t+xCoeffs[i*4+3],yCoeffs[i*4]*t**3+yCoeffs[i*4+1]*t**2+yCoeffs[i*4+2]*t+yCoeffs[i*4+3], color='blue')
        plt.scatter(gpsData['g_x'][i],gpsData['g_y'][i], color='red')

    '''
    tx= np.linspace(gpsData['time'][0], gpsData['time'][-1], 5000)
    plt.plot(tx,coeffs[0]*tx**3+coeffs[1]*tx**2+coeffs[2]*tx+coeffs[3])
    plt.scatter(t, z, color='red')  # Plot the original points
    plt.title("Cubic Spline Continuation")
    '''
    #plt.xlim(0, (gpsData['time'].iloc[-1]-t0)/pd.Timedelta(seconds=1))
    plt.grid()
    plt.show()