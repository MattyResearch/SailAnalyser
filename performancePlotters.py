import matplotlib.pyplot as plt

def tackPlots(tackAnalysed,windowSize,avgTack,tackPlotDict,colour,name):
    """
    Plots analysed tack and gybe data
    """
    print("Plotting tacks...")
    timeLim=windowSize/2
    LimVMG=max(avgTack[:,2])*1.1
    LimSpeed=max(avgTack[:,1])*1.1
    LimMetresLost=[min(avgTack[:,4])*1.1,max(avgTack[:,4])*1.1]
    if tackPlotDict == None:
        tackfig, tackAx = plt.subplots(2, 2, figsize=(10, 8),sharex=True,layout='constrained')
        tackfig.suptitle('Tack Analysis', fontsize=16)
        lims={'vmg':LimVMG,'speed':LimSpeed,'metresLost':LimMetresLost}
    else:
        lims=tackPlotDict['lims']
        tackfig=tackPlotDict['fig']
        tackAx=tackPlotDict['ax']
        lims['vmg']=LimVMG if lims['vmg']<LimVMG else lims['vmg']
        lims['speed']=LimSpeed if lims['speed']<LimSpeed else lims['speed']
        lims['metresLost'][1]=LimMetresLost[1] if lims['metresLost'][1]<LimMetresLost[1] else lims['metresLost'][1]
        lims['metresLost'][0]=LimMetresLost[0] if (lims['metresLost'][0]>LimMetresLost[0]) else lims['metresLost'][0]

    for i in range(len(tackAnalysed)+1):
        if i == len(tackAnalysed):
            tackAx[0,0].plot(avgTack[:,0], avgTack[:,1],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            tackAx[0,1].plot(avgTack[:,0], avgTack[:,2],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            tackAx[1,0].plot(avgTack[:,0], avgTack[:,3],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            tackAx[1,1].plot(avgTack[:,0], avgTack[:,4],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)

            '''tackAx[0,0].legend(prop={'size': 6})
            tackAx[0,1].legend(prop={'size': 6})
            tackAx[1,0].legend(prop={'size': 6})
            tackAx[1,1].legend(prop={'size': 6})'''

            tackAx[0,0].set_ylabel('Speed (m/s)')
            tackAx[0,0].set_xlabel('Time (s)')
            tackAx[0,0].set_title('Boatspeed')
            tackAx[0,0].grid(True, which='both', linestyle='--', linewidth=0.5)
            tackAx[0,0].set_xlim(-timeLim,timeLim)
            tackAx[0,0].set_ylim(0, lims['speed'])

            tackAx[0,1].set_ylabel('VMG (m/s)')
            tackAx[0,1].set_xlabel('Time (s)')
            tackAx[0,1].set_title('VMG')
            tackAx[0,1].grid(True, which='both', linestyle='--', linewidth=0.5)
            tackAx[0,1].set_xlim(-timeLim,timeLim)
            tackAx[0,1].set_ylim(0, lims['vmg'])
            tackAx[0,1].yaxis.set_label_position("right")
            tackAx[0,1].yaxis.tick_right()

            tackAx[1,0].set_ylabel('TWA (degrees)')
            tackAx[1,0].set_xlabel('Time (s)')
            tackAx[1,0].set_title('TWA')
            tackAx[1,0].grid(True, which='both', linestyle='--', linewidth=0.5)
            tackAx[1,0].set_xlim(-timeLim,timeLim)
            tackAx[1,0].set_ylim(0, 90)

            tackAx[1,1].set_ylabel('Metres lost (m)')
            tackAx[1,1].set_xlabel('Time (s)')
            tackAx[1,1].set_title('Metres Lost')
            tackAx[1,1].grid(True, which='both', linestyle='--', linewidth=0.5)
            tackAx[1,1].set_xlim(-timeLim,timeLim)
            tackAx[1,1].set_ylim(0, lims['metresLost'][1])
            tackAx[1,1].yaxis.set_label_position("right")
            tackAx[1,1].yaxis.tick_right()

            tackAx[1,1].legend(prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')
        elif i not in tackAnalysed:
            continue
        elif tackAnalysed[i] != {}:
            tackAx[0,0].plot(tackAnalysed[i]['time'], tackAnalysed[i]['boatspeed'],linestyle=":",color=colour,alpha=0.3)
            tackAx[0,1].plot(tackAnalysed[i]['time'], tackAnalysed[i]['vmg'],linestyle=":",color=colour,alpha=0.3)
            tackAx[1,0].plot(tackAnalysed[i]['time'], tackAnalysed[i]['twa'],linestyle=":",color=colour,alpha=0.3)
            tackAx[1,1].plot(tackAnalysed[i]['time'], tackAnalysed[i]['metresLost'],linestyle=":",color=colour,alpha=0.3)
    tackAx[0,0].set_ylim(0, lims['speed'])
    tackAx[0,1].set_ylim(0,lims['vmg'])
    tackAx[1,0].set_ylim(0, 90)
    tackAx[1,1].set_ylim(min(0,lims['metresLost'][0]), lims['metresLost'][1])

    tackPlotDict={'lims':lims,'fig':tackfig,'ax':tackAx}
    return tackPlotDict

def gybePlots(gybeAnalysed,windowSize,avgGybe,gybePlotDict,colour,name):
    """
    Plots analysed tack and gybe data
    """
    print("Plotting gybes...")
    timeLim=windowSize/2
    LimVMG=max(avgGybe[:,2])*1.1
    LimSpeed=max(avgGybe[:,1])*1.1
    LimMetresLost=[min(avgGybe[:,4])*1.1,max(avgGybe[:,4])*1.1]
    if gybePlotDict == None:
        gybefig, gybeAx = plt.subplots(2, 2, figsize=(10, 8), sharex=True,layout='constrained')
        gybefig.suptitle('Gybe Analysis', fontsize=16)
        lims={'vmg':LimVMG,'speed':LimSpeed,'metresLost':LimMetresLost}
    else:
        lims=gybePlotDict['lims']
        gybefig=gybePlotDict['fig']
        gybeAx=gybePlotDict['ax']
        lims['vmg']=LimVMG if lims['vmg']<LimVMG else lims['vmg']
        lims['speed']=LimSpeed if lims['speed']<LimSpeed else lims['speed']
        lims['metresLost'][1]=LimMetresLost[1] if lims['metresLost'][1]<LimMetresLost[1] else lims['metresLost'][1]
        lims['metresLost'][0]=LimMetresLost[0] if (lims['metresLost'][0]>LimMetresLost[0]) else lims['metresLost'][0]

    for i in range(len(gybeAnalysed)+1):
        if i == len(gybeAnalysed):
            plots={}
            plots[0]=gybeAx[0,0].plot(avgGybe[:,0], avgGybe[:,1],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            plots[1]=gybeAx[0,1].plot(avgGybe[:,0], avgGybe[:,2],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            plots[2]=gybeAx[1,0].plot(avgGybe[:,0], avgGybe[:,3],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)
            plots[3]=gybeAx[1,1].plot(avgGybe[:,0], avgGybe[:,4],lw=2,linestyle="-",color=colour,label=name,zorder=100,alpha=1)

            '''gybeAx[0,0].legend(prop={'size': 6})
            gybeAx[0,1].legend(prop={'size': 6})
            gybeAx[1,0].legend(prop={'size': 6})
            gybeAx[1,1].legend(prop={'size': 6})'''

            gybeAx[0,0].set_ylabel('Speed (m/s)')
            gybeAx[0,0].set_xlabel('Time (s)')
            gybeAx[0,0].set_title('Boatspeed')
            gybeAx[0,0].grid(True, which='both', linestyle='--', linewidth=0.5)
            gybeAx[0,0].set_xlim(-timeLim,timeLim)
            gybeAx[0,0].set_ylim(0, lims['speed'])

            gybeAx[0,1].set_ylabel('VMG (m/s)')
            gybeAx[0,1].set_xlabel('Time (s)')
            gybeAx[0,1].set_title('VMG')
            gybeAx[0,1].grid(True, which='both', linestyle='--', linewidth=0.5)
            gybeAx[0,1].set_xlim(-timeLim,timeLim)
            gybeAx[0,1].set_ylim(0,lims['vmg'])
            gybeAx[0,1].yaxis.set_label_position("right")
            gybeAx[0,1].yaxis.tick_right()

            gybeAx[1,0].set_ylabel('TWA (degrees)')
            gybeAx[1,0].set_xlabel('Time (s)')
            gybeAx[1,0].set_title('TWA')
            gybeAx[1,0].grid(True, which='both', linestyle='--', linewidth=0.5)
            gybeAx[1,0].set_xlim(-timeLim,timeLim)
            gybeAx[1,0].set_ylim(90, 180)

            gybeAx[1,1].set_ylabel('Metres lost (m)')
            gybeAx[1,1].set_xlabel('Time (s)')
            gybeAx[1,1].set_title('Metres Lost')
            gybeAx[1,1].grid(True, which='both', linestyle='--', linewidth=0.5)
            gybeAx[1,1].set_xlim(-timeLim,timeLim)
            gybeAx[1,1].set_ylim(0, lims['metresLost'][1])
            gybeAx[1,1].yaxis.set_label_position("right")
            gybeAx[1,1].yaxis.tick_right()

            gybeAx[1,1].legend(prop={'size': 6},bbox_to_anchor=(0.5, -0.4), loc='lower right')
        elif i not in gybeAnalysed:
            continue
        elif gybeAnalysed[i] != {}:
            gybeAx[0,0].plot(gybeAnalysed[i]['time'], gybeAnalysed[i]['boatspeed'],linestyle=":",color=colour,alpha=0.3)
            gybeAx[0,1].plot(gybeAnalysed[i]['time'], gybeAnalysed[i]['vmg'],linestyle=":",color=colour,alpha=0.3)
            gybeAx[1,0].plot(gybeAnalysed[i]['time'], gybeAnalysed[i]['twa'],linestyle=":",color=colour,alpha=0.3)
            gybeAx[1,1].plot(gybeAnalysed[i]['time'], gybeAnalysed[i]['metresLost'],linestyle=":",color=colour,alpha=0.3)
        gybeAx[0,0].set_ylim(0, lims['speed'])
        gybeAx[0,1].set_ylim(0,lims['vmg'])
        gybeAx[1,0].set_ylim(90, 180)
        gybeAx[1,1].set_ylim(min(0,lims['metresLost'][0]), lims['metresLost'][1])

    gybePlotDict={'lims':lims,'fig':gybefig,'ax':gybeAx}
    return gybePlotDict