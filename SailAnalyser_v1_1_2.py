from GUI import fileSelectionWindow, passToTk, saveGraph, manualWindAngles, versionChecker, setCrops, updateCropSliders
from tackAnalysis import analyseManoeuvresMain,analyseManoeuvresCubicInterp
from straightLineAnalysis import straightLineAnalysisMain,straightLineAnalysisCubic
from mapPlots import plotMaps,plotmapsCubic
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

# Placeholders for plots
tackPlotDict = None
gybePlotDict = None
violinPlotDict = None
mapPlotDict = None
version = 'v1.1.2'

def MainUpdateGraphs(filenameList,windAngleList,satelliteBool,crops):
    global tackPlotDict, gybePlotDict, violinPlotDict, mapPlotDict
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
            #app_window.children["!notebook"].children["!frame2"].children["!frame"].pack(side='top', fill=None,expand=True)
    elif filenameList[0] == "":
        print ("No files selected.")
        return
    if len(filenameList) ==1:
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!entry"].get()],satBool.get(),browseData.crops))
        #app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack(side='top', fill=None,expand=True)

    tackPlotDict,gybePlotDict,analysedDataDict = analyseManoeuvresCubicInterp(filenameList, windAngleList,windowSize,crops)
    tackCanvas = FigureCanvasTkAgg(tackPlotDict['fig'], master=app_window.children["!notebook"].children["!frame3"])  
    gybeCanvas= FigureCanvasTkAgg(gybePlotDict['fig'], master=app_window.children["!notebook"].children["!frame4"]) 
    tackCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)
    gybeCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    violinPlotDict,straightLineDataDict = straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize)
    violinCanvas= FigureCanvasTkAgg(violinPlotDict['fig'], master=app_window.children["!notebook"].children["!frame5"]) 
    violinCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)
    
    updateCropSliders(app_window,filenameList,analysedDataDict)
    '''if len(filenameList) >1:
        # adjust slider scales for cropping
        maxTime = int(np.floor((analysedDataDict[0]['gpsData'].iloc[-1]['time']-analysedDataDict[0]['gpsData'].iloc[0]['time'])/ pd.Timedelta(minutes=1))+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))

        maxTime = int(np.floor((analysedDataDict[1]['gpsData'].iloc[-1]['time']-analysedDataDict[0]['gpsData'].iloc[0]['time'])/ pd.Timedelta(minutes=1))+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))

        app_window.children["!notebook"].children["!frame2"].children["!frame"].pack(side='top', fill=None,expand=True)
    else:
        # adjust slider scales for cropping
        maxTime = int(np.floor((analysedDataDict[0]['gpsData'].iloc[-1]['time']-analysedDataDict[0]['gpsData'].iloc[0]['time'])/ pd.Timedelta(minutes=1))+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))

        app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack(side='top', fill=None,expand=True)'''

    mapPlotDict = plotmapsCubic(filenameList, analysedDataDict,straightLineDataDict,satelliteBool)
    mapCanvas= FigureCanvasTkAgg(mapPlotDict['fig'], master=app_window.children["!notebook"].children["!frame2"]) 
    mapCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    print("Graphs updated successfully.")
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