from GUI import fileSelectionWindow, passToTk, saveGraph, manualWindAngles
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

def MainUpdateGraphs(filenameList,windAngleList,satBool):
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
            app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry"].get(),app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry2"].get()]))
            app_window.children["!notebook"].children["!frame2"].children["!frame"].pack(side='top', fill=None,expand=True)
    elif filenameList[0] == "":
        print ("No files selected.")
        return
    if len(filenameList) ==1:
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!entry"].get()]))
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack(side='top', fill=None,expand=True)

    tackPlotDict,gybePlotDict,analysedDataDict = analyseManoeuvresCubicInterp(filenameList, windAngleList,windowSize)
    tackCanvas = FigureCanvasTkAgg(tackPlotDict['fig'], master=app_window.children["!notebook"].children["!frame3"])  
    gybeCanvas= FigureCanvasTkAgg(gybePlotDict['fig'], master=app_window.children["!notebook"].children["!frame4"]) 
    tackCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)
    gybeCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    violinPlotDict,straightLineDataDict = straightLineAnalysisCubic(filenameList, windAngleList,analysedDataDict,windowSize)
    violinCanvas= FigureCanvasTkAgg(violinPlotDict['fig'], master=app_window.children["!notebook"].children["!frame5"]) 
    violinCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    mapPlotDict = plotmapsCubic(filenameList, analysedDataDict,straightLineDataDict,satBool)
    mapCanvas= FigureCanvasTkAgg(mapPlotDict['fig'], master=app_window.children["!notebook"].children["!frame2"]) 
    mapCanvas.get_tk_widget().pack(side='top', fill='both', expand=True)

    print("Graphs updated successfully.")
    app_window.children["!notebook"].select(app_window.children["!notebook"].children["!frame2"])  # Switch to the map tab after updating graphs


browseData = passToTk()  # Create an instance of passToTk to hold filenames and initial directory
windAngleList=[None,None]
app_window = fileSelectionWindow()
satBool=tk.IntVar()
app_window.children["!notebook"].children["!frame2"].children["!button"].configure(command=lambda:saveGraph(mapPlotDict['fig']))
app_window.children["!notebook"].children["!frame3"].children["!button"].configure(command=lambda:saveGraph(tackPlotDict['fig']))
app_window.children["!notebook"].children["!frame4"].children["!button"].configure(command=lambda:saveGraph(gybePlotDict['fig']))
app_window.children["!notebook"].children["!frame5"].children["!button"].configure(command=lambda:saveGraph(violinPlotDict['fig']))
app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!button"].configure(command=lambda:MainUpdateGraphs(browseData.filenameList,[app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry"].get(),app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!entry2"].get()],satBool))
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton"].configure(variable=satBool,value=True)
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton2"].configure(variable=satBool,value=False)
app_window.children["!notebook"].children["!frame"].children["!frame2"].children["!frame"].children["!radiobutton2"].select()
app_window.children["!notebook"].children["!frame"].children["!frame"].children["!button3"].configure(
                                                                            command=lambda: MainUpdateGraphs(browseData.filenameList, windAngleList,satBool.get()))  # Update the command to pass filenameList and windAngleList
app_window.mainloop()  # Start the Tkinter event loop