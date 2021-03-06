#this was copied from /afs/cern.ch/user/d/dsperka/public/forGeorgia/compareWBMTriggerRates.py

import os
import argparse

from cernSSOWebParser import parseURLTables

def getPSAndInstLumis(runnr):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/LumiSections?RUN=%s" % runnr 
    tables=parseURLTables(url)

    psAndInstLumis={}
    
    for line in tables[0]:
        offset=0
        if line[0]=="L S": offset=41
        
        lumiSec=int(line[0+offset])
        preScaleColumn=int(line[1+offset])
        instLumi=float(line[3+offset])
        if instLumi==0.0: instLumi=50
        psAndInstLumis[lumiSec]=(preScaleColumn,instLumi)
    return psAndInstLumis


def getAveInstLumi(psAndInstLumis,minLS,maxLS):
    lumiSum=0.;
    nrLumis=0;
    if maxLS==-1: maxLS=max(psAndInstLumis.keys())
    for lumi in range(minLS,maxLS+1):
        if lumi in psAndInstLumis:
            nrLumis+=1
            lumiSum+=psAndInstLumis[lumi][1]
    if nrLumis!=0: return lumiSum/nrLumis
    else: return 0


def getTriggerRates(runnr,minLS,maxLS):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/HLTSummary?fromLS=%s&toLS=%s&RUN=%s" % (minLS,maxLS,runnr)
    #print url
    tables=parseURLTables(url)

    hltRates={}
    for line in tables[1][2:]:
        rates=[]
#        print line
        for entry in line[3:7]:
            rates.append(float(entry.replace(",","")))
                        
        hltRates[line[1].split("_v")[0]]=(rates,line[9])
#    print hltRates
    return hltRates

def getL1Prescales(runnr):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=default" % (runnr)
    tables=parseURLTables(url)
    l1_hlt_mode=tables[1][1][3]

    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/TriggerMode?KEY=%s" % (l1_hlt_mode)
    tables=parseURLTables(url)

    prescales={}

    # l1 algo paths/prescales
    for line in tables[3]:
        #                path     7e33    1e32
        try:
            prescales[line[1]] = (int(line[4]),int(line[13]))
        except:
            prescales[line[1]] = (-1,-1)

    #l1 tech paths/prescales
    for line in tables[4]:
        #                path     7e33    1e32
        try:
            prescales[line[1]] = (int(line[4]),int(line[13]))
        except:
            prescales[line[1]] = (-1,-1)

    return prescales


def getHLTPrescales(runnr):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=default" % (runnr)
    tables=parseURLTables(url)
    l1_hlt_mode=tables[1][1][3]

    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/TriggerMode?KEY=%s" % (l1_hlt_mode)
    tables=parseURLTables(url)

    prescales={}

    #HLT paths/prescales
    for line in tables[5]:
        if ('Output' in line[1].split('_v')[0]): continue
        #                path     7e33    1e32
        try:
            prescales[line[1].split('_v')[0]] = (int(line[4]),int(line[13]))
        except:
            prescales[line[1].split('_v')[0]] = (-1,-1)

    return prescales

def getSteamRates(steamFile):
    data={}
    import csv
    with open(steamFile) as csvfile:
        steamReader=csv.reader(csvfile)
        for line in steamReader:
#            path = line[0].split("_v")[0]
            path = line[1].split("_v")[0]

            if path.find("HLT_")!=-1:
                try:
#                    print path,line[0],line[3],line[5]
                    rate = float(line[3])
                    rateErr = float(line[5])
                    prescale = int(line[0])
                except:
                    #print path,line[51],line[53]
                    rate = -1
                    rateErr = -1
                    prescale = -1

                data[path]=(rate,rateErr,prescale)
    return data
           
                        
         

parser = argparse.ArgumentParser(description='compare hlt reports')

parser.add_argument('runnr',help='runnr')
parser.add_argument('--minLS',help='minimum LS (inclusive)',default=1,type=int)
parser.add_argument('--maxLS',help='maximum LS (inclusive)',default=-1,type=int)
parser.add_argument('--targetLumi',help='lumi to scale to (units of 1E30, so 7E33 is 7000)',default=-1.0,type=float)
parser.add_argument('--steamRates',help='csv steam rate google doc',default="")
args = parser.parse_args()

steamRates=getSteamRates(args.steamRates)


psAndInstLumis=getPSAndInstLumis(args.runnr)
aveLumi=getAveInstLumi(psAndInstLumis,args.minLS,args.maxLS)
#print aveLumi

lumiScale=1.
if args.targetLumi!=-1: lumiScale=args.targetLumi/float(aveLumi)

#print aveLumi,lumiScale

hltRates=getTriggerRates(args.runnr,args.minLS,args.maxLS)
l1Prescales=getL1Prescales(args.runnr)
hltPrescales=getHLTPrescales(args.runnr)

spreadSheetHeader="Path,,Data Rate (Hz),,,Data Rate scaled (Hz),,,Steam Rate (Hz),,,Data - Steam (Hz),,,(Data - Steam)/Steam"
spreadSheetStr="%s,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f" 

print spreadSheetHeader
for path in hltRates:

    rates=hltRates[path][0]
    l1seeds=hltRates[path][1]

    import math

    prescaledPath=False
    hltPrescaleOnline=1
    if rates[1]!=0 and rates[1]!=rates[0]: 
        prescaledPath=True
        hltPrescaleOnline = float(rates[1]/rates[0])
        
    l1Prescale1e32=9999999
    l1Prescale7e33=99999999
    for l1seed in l1Prescales:
        if l1seed!='' and (l1seed in l1seeds): 
            if (l1Prescales[l1seed][1]<l1Prescale1e32):
                l1Prescale1e32=l1Prescales[l1seed][1]
            if (l1Prescales[l1seed][0]<l1Prescale7e33):
                l1Prescale7e33=l1Prescales[l1seed][0]

    hltPrescale1e32=1
    hltPrescale7e33=1
    if (path in hltPrescales):
        hltPrescale1e32=hltPrescales[path][1]
        hltPrescale7e33=hltPrescales[path][0]

    steamRate=0
    steamRateErr=0
    hltPrescaleSteam=1
    if path in steamRates:
        steamRate=steamRates[path][0]
        steamRateErr=steamRates[path][1]
        hltPrescaleSteam=steamRates[path][2]

    rate =rates[3]
    rateErr=0
    if rates[2]!=0: rateErr=math.sqrt(rates[2])/rates[2]*rate
    #print path,rates[3]*lumiScale,l1PrescaleSteam,hltPrescaleSteam,hltPrescaleOnline,l1PrescaleOnline
    #print path,rates[3]*lumiScale,l1Prescale7e33,hltPrescale7e33,hltPrescale1e32,l1Prescale1e32
    try:
        #rateScaled=rates[3]*lumiScale*(hltPrescaleOnline*l1PrescaleOnline)/(l1PrescaleSteam*hltPrescaleSteam)
        #rateScaled=rates[3]*lumiScale*(hltPrescale1e32*l1Prescale1e32)/(l1Prescale7e33*hltPrescale7e33)
        rateScaled=rates[3]*lumiScale
        rateScaledErr=(rateErr/rates[3])*rateScaled
    except:
        rateScaled=rates[3]*lumiScale
        rateScaledErr=rateErr*lumiScale
    
    rateUnprescaledScaled=0
    rateUnprescaledScaledErr=0
    if rates[1]!=0:
        rateUnprescaledScaled=rates[3]*rates[0]/rates[1]*lumiScale
        rateUnprescaledScaledErr=rateErr*rates[0]/rates[1]*lumiScale

    rateDiff = rateScaled-steamRate
    rateDiffErr = math.sqrt(rateScaledErr**2 + steamRateErr**2)

    relDiff = 999
    relDiffErr = 0
    if steamRate!=0:
        relDiff = rateDiff/steamRate
        relDiffErr = rateScaledErr**2/steamRate**2 + rateScaled**2*steamRateErr**2/steamRate**4
    
   # print "%s : rate %f rate unprescaled %f steam rate %f +/- %f" % (path,rateScaled,rateUnprescaledScaled,steamRate,steamRateErr)


    #if (hltPrescaleOnline==1 and l1PrescaleOnline==1 and l1PrescaleSteam==1 and hltPrescaleSteam==1):
    #    print spreadSheetStr %(path,rate,rateErr,rateScaled,rateScaledErr,steamRate,steamRateErr,rateDiff,rateDiffErr,relDiff,relDiffErr)
    print spreadSheetStr %(path,rate,rateErr,rateScaled,rateScaledErr,steamRate,steamRateErr,rateDiff,rateDiffErr,relDiff,relDiffErr)
    
