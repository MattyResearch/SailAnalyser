from GUI import fileSelectionWindow, passToTk, saveGraph, manualWindAngles, versionChecker, setCrops, updateCropSliders
from tackAnalysis import analyseManoeuvresMain,analyseManoeuvresCubicInterp, crop
from straightLineAnalysis import straightLineAnalysisMain,straightLineAnalysisCubic
from mapPlots import plotMaps,plotmapsCubic
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
import numpy as np
import copy

# Placeholders for plots
tackPlotDict = None
gybePlotDict = None
violinPlotDict = None
mapPlotDict = None
analysedDataDict = None
straightLineDataDict = None
version = 'v1.1.3'

def setCropButtons(index,input,filenameList,analysedDataDict,straightLineDataDict,satelliteBool):
    cropInput = copy.deepcopy(browseData.crops)
    cropInput[index]=input
    if (cropInput[1]!=0 and cropInput[0]>=cropInput[1]) or (cropInput[3]!=0 and cropInput[2]>=cropInput[3]):
        print("Cannot set End Time before Start Time")
        return
    browseData.crops[index]=input
    if len(app_window.children["!notebook"].children["!frame2"].pack_slaves()) > 1:
        app_window.children["!notebook"].children["!frame2"].pack_slaves()[2].destroy()  # Destroy the old canvas if it exists
        mapInputDict = copy.deepcopy(analysedDataDict) # copy to stop it referencing & modifying analysedDataDict
    for i in range(len(filenameList)):
        if analysedDataDict[i]['cropped'][0]>browseData.crops[i*2]:
            cropInput[i*2]=0 # cropInput exists only for the map plot.
        if analysedDataDict[i]['cropped'][1]!= 0 and analysedDataDict[i]['cropped'][1]<browseData.crops[i*2+1]:
            cropInput[i*2+1]=0
        mapInputDict[i]['t0'] = mapInputDict[i]['gpsData']['time'][0]
        mapInputDict[i]['gpsData'],cuts = crop(mapInputDict[i]['gpsData'],cropInput,i)
        mapInputDict[i]['manoeuvreData']['spline']=mapInputDict[i]['manoeuvreData']['spline'].sub(cuts['start']) # subtract cropped spline numbers
        mapInputDict[i]['manoeuvreData']=mapInputDict[i]['manoeuvreData'][mapInputDict[i]['manoeuvreData']['spline']<len(mapInputDict[i]['gpsData']['time'])-1]
        mapInputDict[i]['manoeuvreData']=mapInputDict[i]['manoeuvreData'][mapInputDict[i]['manoeuvreData']['spline']>0]
        # 4 cubic coefficients per spline need to be deleted for each cropped data point
        # this enables the same algorithms to work when plotting maps.
        for axis in ['xCoeffs','yCoeffs']:
            if cuts['end']!=0:
                mapInputDict[i][axis]=mapInputDict[i][axis][cuts['start']*4:-cuts['end']*4]
            else:
                mapInputDict[i][axis]=mapInputDict[i][axis][cuts['start']*4:]
    mapPlotDict = plotmapsCubic(filenameList,mapInputDict,straightLineDataDict,satelliteBool)
    if len(filenameList)>1:
        app_window.children["!notebook"].children["!frame2"].children["!frame"].pack(side='top', fill=None,expand=True)
    else:
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack(side='top', fill=None,expand=True)
    mapCanvas= FigureCanvasTkAgg(mapPlotDict['fig'], master=app_window.children["!notebook"].children["!frame2"]) 
    mapCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

def MainUpdateGraphs(filenameList,windAngleList,satelliteBool,crops):
    global tackPlotDict, gybePlotDict, violinPlotDict, mapPlotDict, analysedDataDict, straightLineDataDict

    if (len(windAngleList)<2 or windAngleList[1] == None) and len(filenameList)>1: # clears up bug where only one windAngle is input
        windAngleList[1] = windAngleList[0]

    # read advanced settings from GUI
    windowSize =app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!scale"].get()  # Get the window size from the scale widget
    app_window.children["!notebook"].children["!frame2"].children["!frame"].pack_forget()
    app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack_forget()

    if len(app_window.children["!notebook"].children["!frame3"].children) > 1:
        app_window.children["!notebook"].children["!frame2"].pack_slaves()[1].destroy()  # Destroy the old canvas if it exists
        app_window.children["!notebook"].children["!frame3"].pack_slaves()[1].destroy()
        app_window.children["!notebook"].children["!frame4"].pack_slaves()[1].destroy()
        app_window.children["!notebook"].children["!frame5"].pack_slaves()[1].destroy()

    if filenameList==["",""]:
        print ("No files selected.")
        return
    if len(filenameList) >1:
        if filenameList[0] == "" or filenameList[1] == "":
            filenameList.remove("")  # Remove empty strings from the list if any
        else:
            app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry"].get(),app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry2"].get()],satBool.get(),browseData.crops))
    elif filenameList[0] == "":
        print ("No files selected.")
        return
    if len(filenameList) ==1:
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!entry"].get(),None],satBool.get(),browseData.crops))

    tackPlotDict,gybePlotDict,analysedDataDict = analyseManoeuvresCubicInterp(filenameList, windAngleList,windowSize,crops)
    tackCanvas = FigureCanvasTkAgg(tackPlotDict['fig'], master=app_window.children["!notebook"].children["!frame3"])  
    gybeCanvas= FigureCanvasTkAgg(gybePlotDict['fig'], master=app_window.children["!notebook"].children["!frame4"]) 
    tackCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)
    gybeCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    violinPlotDict,straightLineDataDict = straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize)
    violinCanvas= FigureCanvasTkAgg(violinPlotDict['fig'], master=app_window.children["!notebook"].children["!frame5"]) 
    violinCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)
    
    updateCropSliders(app_window,filenameList,analysedDataDict)

    mapPlotDict = plotmapsCubic(filenameList, analysedDataDict,straightLineDataDict,satelliteBool)
    mapCanvas= FigureCanvasTkAgg(mapPlotDict['fig'], master=app_window.children["!notebook"].children["!frame2"]) 
    mapCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    print("Graphs updated successfully.")
    # Update crop button definitions
    app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!button"].configure(command=lambda:setCropButtons(0,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!button2"].configure(command=lambda:setCropButtons(1,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!button"].configure(command=lambda:setCropButtons(2,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale2"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!button2"].configure(command=lambda:setCropButtons(3,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale2"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!frame"].children["!button"].configure(command=lambda:setCropButtons(0,app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!frame"].children["!button2"].configure(command=lambda:setCropButtons(1,app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].get(),filenameList,analysedDataDict,straightLineDataDict,satBool.get()))
    
    app_window.children["!notebook"].select(app_window.children["!notebook"].children["!frame2"])  # Switch to the map tab after updating graphs

browseData = passToTk()  # Create an instance of passToTk to hold filenames and initial directory
windAngleList=[None,None]
app_window = fileSelectionWindow(version)
satBool=tk.IntVar()
app_window.children["!notebook"].children["!frame2"].children["!button"].configure(command=lambda:saveGraph(mapPlotDict['fig']))
app_window.children["!notebook"].children["!frame3"].children["!button"].configure(command=lambda:saveGraph(tackPlotDict['fig']))
app_window.children["!notebook"].children["!frame4"].children["!button"].configure(command=lambda:saveGraph(gybePlotDict['fig']))
app_window.children["!notebook"].children["!frame5"].children["!button"].configure(command=lambda:saveGraph(violinPlotDict['fig']))
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton"].configure(variable=satBool,value=True)
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton2"].configure(variable=satBool,value=False)
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton2"].select()
app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry"].get(),app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry2"].get()],satBool.get(),browseData.crops))
app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!entry"].get()],satBool.get(),browseData.crops))
app_window.children["!notebook"].children["!frame"].children["!frame"].children["!button3"].configure(
                                                                            command=lambda: MainUpdateGraphs(browseData.filenameList, windAngleList,satBool.get(),browseData.crops))  # Update the command to pass filenameList and windAngleList
# Update crop button definitions
app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!button"].configure(command=lambda:setCrops(0,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale"].get()))
app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!button2"].configure(command=lambda:setCrops(1,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale"].get()))
app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!button"].configure(command=lambda:setCrops(2,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale2"].get()))
app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!button2"].configure(command=lambda:setCrops(3,app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!scale2"].get()))
app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!frame"].children["!button"].configure(command=lambda:setCrops(0,app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].get()))
app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!frame"].children["!button2"].configure(command=lambda:setCrops(1,app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].get()))
versionChecker(version)
app_window.mainloop()  # Start the Tkinter event loop
