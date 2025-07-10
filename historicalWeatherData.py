import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry
from xmlReader import read_xml
import datetime as dt
import numpy as np

def retreiveHistoricalWeatherData(parameters):
    '''
    Retreives only hourly wind speed and direction
    '''
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": parameters[0],
        "longitude": parameters[1],
        "start_date": parameters[2].strftime("%Y-%m-%d"),
        "end_date": parameters[3].strftime("%Y-%m-%d"),
        "hourly": ["wind_direction_100m", "wind_speed_100m"],
        "models": "ecmwf_ifs"
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_wind_direction_10m = hourly.Variables(0).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    #print(hourly_dataframe)
    return hourly_dataframe

def retreiveForecastWeatherData(parameters):
    '''
    Retreives only hourly wind speed and direction
    Open-Meteo API uses forecast data for the previous 5 days
    '''
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": parameters[0],
        "longitude": parameters[1],
        "start_date": parameters[2].strftime("%Y-%m-%d"),
        "end_date": parameters[3].strftime("%Y-%m-%d"),
        "hourly": ["wind_direction_120m", "wind_speed_120m"],
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_wind_direction_120m = hourly.Variables(0).ValuesAsNumpy()
    hourly_wind_speed_120m = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}

    hourly_data["wind_direction_10m"] = hourly_wind_direction_120m
    hourly_data["wind_speed_10m"] = hourly_wind_speed_120m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    #print(hourly_dataframe)
    return hourly_dataframe

def hourlyLocationExtract(gpsData):
    """
    Extracts the date and longitude from the GPS data
    """
    avg_lat = {}
    avg_lon = {}
    hour = []
    for i in range(gpsData.iloc[0]['time'].hour, gpsData.iloc[-1]['time'].hour + 1):
        # Extract the GPS data for the current hour

        hour_data = gpsData[(gpsData['time'].dt.hour == i)]
        if not hour_data.empty:
            # Get the average latitude and longitude for the hour
            avg_lat[i]=hour_data['lat'].mean()
            avg_lon[i]=hour_data['lon'].mean()
            #print(f"Hour {i}: Avg Lat: {avg_lat}, Avg Lon: {avg_lon}")
        else:
            avg_lat[i]=gpsData.iloc[-1]['lat']  # Use the last lat if no data for the hour
            avg_lon[i]=gpsData.iloc[-1]['lon']  # Use the last lon if no data for the hour
        hour.append(i)
    return {'avg_lat': avg_lat, 'avg_lon': avg_lon, 'hour': hour}

def weatherDataFollowBoat(gpsData):
    """
    Retrieves weather data for the boat's GPS locations
    """
    startTime = gpsData.iloc[0]['time']
    endTime = gpsData.iloc[-1]['time']
    startLat = gpsData.iloc[0]['lat']
    startLon = gpsData.iloc[0]['lon']
    if endTime.replace(tzinfo=None) > dt.datetime.now()-dt.timedelta(days=6):
        # If the GPS data is within 5 days past, use forecast data
        weatherDataHourly = retreiveForecastWeatherData([startLat, startLon, startTime, endTime])
    else:
        weatherDataHourly = retreiveHistoricalWeatherData([startLat, startLon, startTime, endTime])
    if gpsData.iloc[-1]['time'] - gpsData.iloc[0]['time'] > dt.timedelta(hours=1):
        # If the GPS data spans more than one hour, extract hourly locations and retrieve weather data for each hour
        weatherLocations=hourlyLocationExtract(gpsData)
        for i in range(gpsData.iloc[0]['time'].hour, gpsData.iloc[-1]['time'].hour + 1):
            if endTime > dt.datetime.now()-dt.timedelta(days=6):
                # If the GPS data is within 5 days past, use forecast data
                hourlyWeatherOnePoint = retreiveForecastWeatherData([weatherLocations['avg_lat'][i],weatherLocations['avg_lon'][i],startTime,endTime])
            else:
                # Otherwise, use historical data
                hourlyWeatherOnePoint = retreiveHistoricalWeatherData([weatherLocations['avg_lat'][i],weatherLocations['avg_lon'][i],startTime,endTime])
            weatherDataHourly.loc[i] = pd.DataFrame(hourlyWeatherOnePoint).iloc[i][:]
    print(weatherDataHourly)
    return weatherDataHourly

def postProcessWeatherData(weatherData):
    """
    Post-processes the weather data to avoid 360 degree jumps in wind direction
    """
    #weatherData['hours'].replace(tzinfo=None)
    for i in range(1, len(weatherData)):
        if weatherData.iloc[i]['wind_direction_10m'] - weatherData.iloc[i-1]['wind_direction_10m'] >= 180:
            weatherData.loc[i:23,'wind_direction_10m'] -= np.float32(360)
        elif weatherData.iloc[i]['wind_direction_10m'] - weatherData.iloc[i-1]['wind_direction_10m'] < -180:
            weatherData.loc[i:23,'wind_direction_10m'] += np.float32(360)
    return weatherData

def weatherDataAtBoat(gpsData):
    try:
        weatherDataBoatLocation = weatherDataFollowBoat(gpsData)
        weatherDataBoatLocation = postProcessWeatherData(weatherDataBoatLocation)
    except:
        print("Error retrieving weather data. Check your internet connection or the Open-Meteo API status.")
        cardinalWindAngle = np.ones(24)*0 # degrees
        trueWindSpeed = np.ones(24)*5.0 # m/s
        hours = [dt.datetime(year=gpsData.iloc[0]['time'].year,month=gpsData.iloc[0]['time'].month,day=gpsData.iloc[0]['time'].day)+pd.Timedelta(hours=i) for i in range(24)]
        weatherDataBoatLocation = pd.DataFrame({'date':hours,'wind_direction_10m':cardinalWindAngle,'wind_speed_10m':trueWindSpeed})
    print("Open_Meteo API weather:")
    print(weatherDataBoatLocation)
    return weatherDataBoatLocation

def manualWindInput(inputSpeed,inputAngle,gpsData):
    cardinalWindAngle = np.ones(24)*float(inputAngle)
    trueWindSpeed = np.ones(24)*float(inputSpeed)
    hours = [dt.datetime(year=gpsData.iloc[0]['time'].year,month=gpsData.iloc[0]['time'].month,day=gpsData.iloc[0]['time'].day)+pd.Timedelta(hours=i) for i in range(24)]
    weatherDataBoatLocation = pd.DataFrame({'date':hours,'wind_direction_10m':cardinalWindAngle,'wind_speed_10m':trueWindSpeed})
    weatherDataBoatLocation['date'] = weatherDataBoatLocation['date'].dt.tz_localize('UTC')  # Ensure timezone is UTC
    print(weatherDataBoatLocation)
    return weatherDataBoatLocation

if __name__ == "__main__":
    filenameList=["oscKieran13_06_25"]
    for i in range(0,len(filenameList)):
        directory = "C:\\Users\\matth\\Documents\\SailAnalyser"
        filename = filenameList[i]+".gpx"
        outputfilename = "gps_data.csv"
        outputfile = directory + "\\" + outputfilename
        inputfile = directory + "\\" + filename

        windowSize = 20 # seconds either side
        manoeuvreLength=2 # seconds either side
        colours = ['blue','magenta']

        gpsData = read_xml(inputFile=inputfile,outputFile=outputfile)
        #weatherDataBoatLocation = weatherDataAtBoat(gpsData)
        try:
            weatherDataBoatLocation = weatherDataFollowBoat(gpsData)
            weatherDataBoatLocation = postProcessWeatherData(weatherDataBoatLocation)
        except:
            print("Error retrieving weather data. Check your internet connection or the Open-Meteo API status.")
            inputAngle = input("Input wind direction (deg):")
            inputSpeed = input("Input wind speed (m/s):")
            cardinalWindAngle = np.ones(24)*float(inputAngle) if inputAngle != '' else 87 # degrees
            trueWindSpeed = np.ones(24)*float(inputSpeed) if inputSpeed != '' else 5 # m/s
            hours = [dt.datetime(year=gpsData.iloc[0]['time'].year,month=gpsData.iloc[0]['time'].month,day=gpsData.iloc[0]['time'].day)+pd.Timedelta(hours=i) for i in range(24)]
            weatherDataBoatLocation = pd.DataFrame({'hours':hours,'wind_direction_10m':cardinalWindAngle,'wind_speed_10m':trueWindSpeed})
        print(weatherDataBoatLocation)
    '''
    if gps Data is longer than 1 hr
    find the locations of each hour
    retreive weather data for each point
    build up dataframe for all weather data points
    '''