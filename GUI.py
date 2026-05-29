import tkinter as tk
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk
import ctypes
import requests
import numpy as np
import pandas as pd

'''
GUI to import files into SailAnalyser
'''

class passToTk:
    filenameList=["", ""]  # List to store filenames
    initialdir = "/"  # Initial directory for file dialog
    crops = [0,0,0,0]

    def test(self, filenameList, initialdir, crops):
        self.filenameList = filenameList
        self.initialdir = initialdir
        self.crops = crops

browseData= passToTk()  # Create an instance of passToTk to hold filenames and initial directory

def browseFiles(file_number=1,fileFrame=None):
    filename = filedialog.askopenfilename(initialdir = browseData.initialdir,
                                          title = "Select a File",
                                          filetypes = (("Garmin GPX files",
                                                        "*.gpx*"),
                                                       ("all files",
                                                        "*.*")))
    browseData.initialdir = filename.rsplit('/', 1)[0]  # Update initial directory to the selected file's directory
    # Change label contents
    if file_number == 1:
        fileFrame.children["!label"].configure(text="File 1: "+filename)
        browseData.filenameList[0] = filename
    elif file_number == 2:
        fileFrame.children["!label2"].configure(text="File 2: "+filename)
        if len(browseData.filenameList) < 2:
            browseData.filenameList.append("")
        browseData.filenameList[1] = filename
    fileFrame.grid(column = 0, row = 0, rowspan=2,sticky="e")

def saveGraph(plotFig):
    filename = filedialog.asksaveasfilename(initialdir = browseData.initialdir,
                                            title= "Save Graph",
                                            filetypes = (("PNG files", "*.png"),("all files", "*.*")))
    if filename!= "":
        plotFig.savefig(filename)

def manualWindAngles(input):
    '''
    Allows manual input of wind angles when historical data is faulty or missing.
    '''
    windAngleList = [None, None]  # Default values for wind angles
    match len(input):
        case 0:
            print("No wind angle input provided.")
            windAngleList = ["", ""]
        case 1:
            windAngleList = input if input[0] != "" else [None]
        case 2:
            windAngleList[0] = input[0] if input[0] != "" else None
            windAngleList[1] = input[1] if input[1] != "" else None

    return windAngleList

def updateCropSliders(app_window,filenameList,analysedDataDict):
    if len(filenameList) >1:
        # adjust slider scales for cropping
        maxTime = int(np.floor(analysedDataDict[0]['duration'])+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))

        maxTime = int(np.floor(analysedDataDict[1]['duration'])+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame"].children["!frame2"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))
        # Pack map data selction frames
        app_window.children["!notebook"].children["!frame2"].children["!frame"].pack(side='top', fill=None,expand=True)
    else:
        # adjust slider scales for cropping
        maxTime = int(np.floor(analysedDataDict[0]['duration'])+1) # wrong place, needs ot be decided separately for both files
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].configure(to=maxTime)
        app_window.children["!notebook"].children["!frame2"].children["!frame2"].children["!scale"].configure(tickinterval=np.floor(maxTime/4))

        app_window.children["!notebook"].children["!frame2"].children["!frame2"].pack(side='top', fill=None,expand=True)

def setCrops(index,input):
    '''
    Sets given crop times for GPS data cropping
    '''
    browseData.crops[index]=input
    return

def _quit(window):
    window.quit()
    window.destroy()
     
def create_window(version):                                                                                                 
    # Create the root window
    window = Tk()

    # Set window title
    window.title('SailAnalyser '+ version)

    # Set window size
    window.geometry("800x800")

    #Set window background color
    window.config(background = "white")

    tabControl = ttk.Notebook(window)

    fileSelectionTab = ttk.Frame(tabControl)
    mapsTab = ttk.Frame(tabControl)
    tacksTab = ttk.Frame(tabControl)
    gybesTab = ttk.Frame(tabControl)
    straightLinesTab = ttk.Frame(tabControl)

    tabControl.add(fileSelectionTab, text='File Selection')
    tabControl.add(mapsTab, text='GPS Maps')
    tabControl.add(tacksTab, text='Tacks')
    tabControl.add(gybesTab, text='Gybes')
    tabControl.add(straightLinesTab, text='Straight Lines')
    tabControl.pack(expand=1, fill="both")

    ttk.Label(fileSelectionTab,
                text="Select GPS data",
                font=("Helvetica", 16)).pack(pady=10)
    
    saveimgButton1 = ttk.Button(tacksTab,
                            text="Save Graph",
                            command=lambda: saveGraph("tack"))
    saveimgButton2 = ttk.Button(gybesTab,
                            text="Save Graph",
                            command=lambda: saveGraph("gybe"))
    saveimgButton3 = ttk.Button(straightLinesTab,
                            text="Save Graph",
                            command=lambda: saveGraph("violin"))
    saveimgButton4 = ttk.Button(mapsTab,
                            text="Save Graph",
                            command=lambda: saveGraph("maps"))
    saveimgButton1.pack(side='top')
    saveimgButton2.pack(side='top')
    saveimgButton3.pack(side='top')
    saveimgButton4.pack(side='top')
    
    #ttk.Label(gybesTab).pack(pady=10)
    
    #ttk.Label(straightLinesTab).pack(pady=10)

    fullFrame = ttk.Frame(fileSelectionTab,borderwidth=1, relief="solid")
    fileFrame = ttk.Frame(fullFrame)
    advancedOptionsFrame = ttk.Frame(fileSelectionTab,borderwidth=1, relief="solid")
    radioGroup = ttk.Frame(advancedOptionsFrame)
    donationFrame = ttk.Frame(fileSelectionTab)
    tutorialFrame = ttk.Frame(fileSelectionTab)
    windAngleInputs = ttk.Frame(mapsTab)
    windAngleInputSingle = ttk.Frame(mapsTab)
    refframe = ttk.Frame(fileSelectionTab)

    manualWindAngleLabel1 = ttk.Label(windAngleInputs,
                                    text="Manually input wind direction:\n (compass heading the wind is coming from)",
                                    font=("Helvetica", 12))
    
    manualWindAngleLabel2 = ttk.Label(windAngleInputSingle,
                                    text="Manually input wind direction:\n (compass heading the wind is coming from)",
                                    font=("Helvetica", 12))

    manualWindAngleTextSingle = ttk.Entry(windAngleInputSingle,
                                    width=10,
                                    font=("Helvetica", 12))
    
    manualWindInputButtonSingle = ttk.Button(windAngleInputSingle,
                                    text="Confirm",
                                    command=manualWindAngles([1]))

    manualWindAngleText1 = ttk.Entry(windAngleInputs,
                                    width=10,
                                    font=("Helvetica", 12))
    manualWindAngleText2 = ttk.Entry(windAngleInputs,
                                    width=10,
                                    font=("Helvetica", 12))

    manualWindInputButton1 = ttk.Button(windAngleInputs,
                                    text="Confirm",
                                    command=manualWindAngles([1]))
    
    cropSlider1 = Scale(windAngleInputs,
                        from_=0, to=180,
                        orient="horizontal",
                        label="Crop GPS Data (minutes)",
                        length=250,
                        tickinterval=15,
                        resolution=1)
    cropSlider1.set(0)  # Set default value to 0 minutes

    cropSlider2 = Scale(windAngleInputs,
                        from_=0, to=180,
                        orient="horizontal",
                        label="Crop GPS Data (minutes)",
                        length=250,
                        tickinterval=15,
                        resolution=1)
    cropSlider2.set(0)  # Set default value to 0 minutes

    cropSliderSingle = Scale(windAngleInputSingle,
                        from_=0, to=180,
                        orient="horizontal",
                        label="Crop GPS Data (minutes)",
                        length=500,
                        tickinterval=15,
                        resolution=1)
    cropSliderSingle.set(0)  # Set default value to 0 minutes

    cropsFrame1 = ttk.Frame(windAngleInputs)
    cropsStart1 = Button(cropsFrame1,
                        text="Set Start",
                        command=setCrops(0,0))
    cropsEnd1 = Button(cropsFrame1,
                        text="Set End",
                        command=setCrops(1,0))
    cropsStart1.pack(side='left',fill='both',expand=True)
    cropsEnd1.pack(side='left',fill='both',expand=True)
    
    cropsFrame2 = ttk.Frame(windAngleInputs)
    cropsStart2 = Button(cropsFrame2,
                        text="Set Start",
                        command=setCrops(2,0))
    cropsEnd2 = Button(cropsFrame2,
                        text="Set End",
                        command=setCrops(3,0))
    cropsStart2.pack(side='left',fill='both',expand=True)
    cropsEnd2.pack(side='left',fill='both',expand=True)

    cropsFrameSingle = ttk.Frame(windAngleInputSingle)
    cropsStartSingle = Button(cropsFrameSingle,
                        text="Set Start",
                        command=setCrops(0,0))
    cropsEndSingle = Button(cropsFrameSingle,
                        text="Set End",
                        command=setCrops(1,0))
    cropsStartSingle.pack(side='left',fill='both',expand=True)
    cropsEndSingle.pack(side='left',fill='both',expand=True)
    
    
    manualWindAngleLabel1.grid(row=0, column=0, pady=20,columnspan=2)
    manualWindAngleLabel2.grid(row=0, column=0, pady=20,columnspan=2)
    manualWindAngleText1.grid(row=1, column=0, padx=50, pady=5)
    manualWindAngleText2.grid(row=1, column=1, padx=50, pady=5)
    cropSlider1.grid(row=2,column=0,pady=20)
    cropSlider2.grid(row=2,column=1,pady=20)
    cropsFrame1.grid(row=3,column=0,padx=0,pady=0)
    cropsFrame2.grid(row=3,column=1,padx=0,pady=0)
    manualWindInputButton1.grid(row=4, column=0, padx=50, pady=5, columnspan=2)
    windAngleInputs.pack(side='top', fill=None,expand=True)

    manualWindAngleTextSingle.grid(row=1, column=0, padx=50, pady=5)
    cropSliderSingle.grid(row=2,column=0,padx=50,pady=5)
    cropsFrameSingle.grid(row=3,column=0)
    manualWindInputButtonSingle.grid(row=4, column=0, padx=50, pady=5)
    

    # Create a File Explorer label
    label_file_1 = Label(fileFrame, 
                        text = "Select GPS data file",
                        width = 50, height = 2, 
                        fg = "blue",
                        justify="right",
                        anchor="e").pack(side="top")

    label_file_2 = Label(fileFrame, 
                        text = "[Optional] Select another GPS data file for comparison",
                        width = 50, height = 2, 
                        fg = "blue",
                        justify="right",
                        anchor="e").pack(side="top")

    button_explore_1 = Button(fullFrame, 
                            text = "Browse Files",
                            width=10,height=2,
                            command = lambda: browseFiles(1,fileFrame))

    button_explore_2 = Button(fullFrame, 
                            text = "Browse Files",
                            width=10,height=2,
                            command = lambda: browseFiles(2,fileFrame))

    button_confirm = Button(fullFrame, 
                        text = "Confirm\n&\nAnalyse",
                        width=10,
                        height=4,
                        command = lambda:_quit(window)) 

    button_exit = Button(fullFrame, 
                        text = "Exit",
                        command = lambda:exit()) 

    # Advanced options frame:
    optionsLabel = Label(advancedOptionsFrame,
                        text = "Advanced Options:",
                        width = 50, height = 2, 
                        fg = "blue",
                        justify="center",
                        anchor="n")
    satBool = False
    satelliteLabel = Label(radioGroup,
                        text = "Plot satellite image?\nWARNING!! Large performance impact!\nDo not use for quick data analysis",
                        height = 3,
                        fg = "blue",
                        justify="left",
                        anchor="n")
    satelliteYes = Radiobutton(radioGroup,
                                    text="Plot satellite image\n!WARNING!",
                                    variable = satBool,
                                    value=False)
    
    satelliteNo = Radiobutton(radioGroup,
                                text="Plot on blank grid",
                                variable = satBool,
                                value=True)
    
    windowSlider = Scale(advancedOptionsFrame,
                        from_=10, to=50,
                        orient="horizontal",
                        label="Manoeuvre window size (seconds)",
                        length=200,
                        tickinterval=4,
                        resolution=2)  # Placeholder command
    windowSlider.set(30)  # Set default value to 30 seconds

    donationLabel = Label(donationFrame,
                          text="Continued development of this project is made possible\nby donations from sailors like you!\nIf this app has helped you, please consider supporting SailAnalyser.",
                          height=3)

    donationButton = Button(donationFrame,
                            text="Click here to donate",
                            #image=paypalImg,
                            command=lambda: webbrowser.open("https://www.paypal.com/donate/?hosted_button_id=MQM88AB3EK6FN"),
                            #image=paypalImg,  # Adjust subsampling as needed
                            compound=LEFT,
                            width=20,
                            height=2)

    
    optionsLabel.grid(column=0, row=0, padx=10, pady=10, columnspan=2)
    satelliteLabel.pack(side="top", anchor=W,fill=None, expand=True)
    satelliteNo.pack(side="top",anchor = W, fill=None, expand=True)
    satelliteYes.pack(side="top",anchor = W, fill=None, expand=True)
    radioGroup.grid(column=0, row=1, padx=10, pady=10)
    windowSlider.grid(column=1, row=1, padx=10, pady=10)
    donationLabel.grid(column=0, row=0, padx=10, pady=0)
    donationButton.grid(column=0, row=1, padx=10, pady=0)
    
    
    tutorialLabel = Label(tutorialFrame,
                        text="For a tutorial on how to use SailAnalyser,\nclick the button below!",
                        height=3,
                        justify="center")
    moreInfoLabel = Label(tutorialFrame,
                        text="For more information and source code, visit:\nhttps://github.com/MattyResearch/SailAnalyser",
                        height=3,
                        justify=CENTER)
    tutorialButton = Button(tutorialFrame,
                            text="Tutorial Video",
                            command=lambda: webbrowser.open("https://youtu.be/Q7Joq_pVw6M"),
                            height=2,
                            width=20)
    
    tutorialLabel.pack(side="top", anchor=CENTER, fill=None, expand=True)
    tutorialButton.pack(side="top", anchor=CENTER, fill=None, expand=True)
    moreInfoLabel.pack(side="top", anchor=CENTER, fill=None, expand=True)
    moreInfoLabel.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/MattyResearch/SailAnalyser"))

    meteoRefLabel = Label(refframe,
                            text="Weather data by Open-Meteo.com:\nhttps://open-meteo.com/",
                            justify="center",
                            height=2)
    satelliteRefLabel= Label(refframe,
                            text="Satellite imagery from ArcGIS",
                            justify="center",
                            height=1)
    meteoRefLabel.grid(row=0, column=0,  padx=10, pady=5)
    satelliteRefLabel.grid(row=1, column=0,  padx=10, pady=5)
    meteoRefLabel.bind("<Button-1>", lambda e: webbrowser.open("https://open-meteo.com/"))
    satelliteRefLabel.bind("<Button-1>", lambda e: webbrowser.open("https://www.arcgis.com/home/"))
    # Pack/grid the file selection tab together
    fileFrame.grid(column = 0, row = 0, rowspan=2,sticky="e")

    button_explore_1.grid(column = 1, row = 0,sticky="w")
    button_explore_2.grid(column = 1, row = 1,sticky="w")

    button_confirm.grid(column = 2, row = 0,rowspan=2,sticky="w")
    #button_exit.grid(column = 2,row = 2)

    fullFrame.pack(side="top",anchor=E, expand=True, padx=10, pady=10)
    #fullFrame.configure(highlightbackground="black", highlightthickness=1)
    advancedOptionsFrame.pack(side="top",anchor=N, fill=None, expand=True)
    refframe.pack(side="top", anchor=N, fill=None, expand=True)
    donationFrame.pack(side="left", anchor=N, fill=None, expand=True)
    tutorialFrame.pack(side="left", anchor=N, fill=None, expand=True)
    

    window.protocol("WM_DELETE_WINDOW", lambda: _quit(window))  # Handle window close event
    myappid = 'tkinter.python.test'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    except:
        pass
    try:
        window.iconbitmap("rs800.ico")
    except:
        pass
    return window

def _quit(window):
    window.quit()
    window.destroy()

def fileSelectionWindow(version):
    app_window = create_window(version)

    #print("Selected files:", filenameList)
    return app_window

def versionChecker(version):
    try:
        response = requests.get("https://api.github.com/repos/MattyResearch/SailAnalyser/releases/latest")
    except:
        print("Could not check for updates. Check your internet connection.")
    if 'SailAnalyser '+version != response.json()["name"]:
        window = Tk()
        window.title("Update Available")
        label = Label(window, text="A new version is available: " + response.json()["name"])
        label.pack()
        button = Button(window, text="Take me there", command=lambda: webbrowser.open(response.json()["html_url"]))
        button.pack()
        cancel = Button(window, text="Remind me later", command=window.destroy)
        cancel.pack()
        try:
            window.iconbitmap("rs800.ico")
        except:
            pass
        window.mainloop()

if __name__ == "__main__":
    browseData = passToTk()  # Create an instance of passToTk to hold data
    app_window = fileSelectionWindow('v1.1.2')
    pass
    app_window.mainloop()
    pass