#!/usr/bin/env python
# -*- coding: utf-8 -*-
# countymapdatadrivenpagestopdfmulti.py

#-------------------------------------------------------------------------
### IMPORTANT:
### When this script is called, you must call it with
### the exact same capitalization
### that the script is saved with.
### Windows and Python will run it just fine
### without matching capitalization, but the
### multiprocessing module's fork script WILL NOT.
#-------------------------------------------------------------------------

## The purpose of this script is to provide
## flow control and related logic for the
## data driven pages export process for
## the county maps.

## There are currently three county map
## MXDs for the quarter inch county maps
## that are to be used with this
## script which act as the Data Driven
## Page templates.

## Quarter Inch Maps:
## countyMapQuarter10x12H.mxd
## countyMapQuarter12x15H.mxd
## countyMapQuarter15x19H.mxd

## There are also three county map
## MXDs for the half inch count maps:

## Half Inch Maps:
## countyMapHalf18x24H.mxd
## countyMapHalf24x30H.mxd
## countyMapHalf24x36H.mxd

## Call CountyMapPreprocessing.py first to
## pull the excel data into the geodatabase
## as the CountyMapSizes table.

import os
import sys
import shutil
import time

import arcpy
import arcpy.da as da
from arcpy import env, GetMessages, Result  # @UnusedImport

import multiprocessing as mp
from multiprocessing import Process, Manager  # @UnusedImport

import datetime

from county_map_config import pythonLogTable, searchFC  # @UnusedImport


mapsDirectory = r"\\gisdata\Planning\Cart\Maps\County"
originalMapType = r"countyMap"
env.workspace = mapsDirectory

# Look at changing this this to a local disk location and then copy from that location to
# the F drive location after the subprocesses have completed.

outputDirectory = r"\\gisdata\Planning\Cart\Maps\County"

exportPDFs = 0
exportPNGs = 1
exportPDFsAndPNGs = 2


def FindDuration(endTime, startTime):
    #Takes two datetime.datetime objects, subtracting the 2nd from the first
    #to find the duration between the two.
    duration = endTime - startTime
    #print str(duration)
    
    dSeconds = int(duration.seconds)
    durationp1 = str(int(dSeconds // 3600)).zfill(2)
    durationp2 = str(int((dSeconds % 3600) // 60)).zfill(2)
    durationp3 = str(int(dSeconds % 60)).zfill(2)
    durationString = durationp1 + ':' +  durationp2 + ':' + durationp3
    
    return durationString


def subProcessMapExports(compressedProcessInfo):
    """ Multiprocessing version of the CountyMapDataDrivenPagesToPDF script. 
        Uses multiple cores to export pdfs. Should be significantly faster
        than waiting on one core to do all of the processing work on its own."""
    
    # In the county map road name border creation script
    # the results queue needs to have information
    # on the rows, stored in a list format
    # that can be transferred back easily.
    # Since the only output here should be the pdfs
    # or the pngs there should be no need to pass
    # any such information back to the main process.
    # Instead, we can pass back completion/performance
    # information, if so desired.
    processInfo = compressedProcessInfo[0]
    outputPDFParentFolder = compressedProcessInfo[1]
    whatToExport = compressedProcessInfo[2]
    mapPath = processInfo[0]
    exportList = processInfo[1]
    mapScaleName = processInfo[2]
    mapScaleName = mapScaleName.upper()
    '''
    print "In subprocess."
    print "Map: " + mapPath
    print "exportList: "
    for exportItem in exportList:
        print exportItem
    print "mapScaleName: " + mapScaleName
    print "whatToExport: " + str(whatToExport)
    '''
    # The main process assigns an mxd to each
    # created process.
    
    ### Improvement: All of the print statements in this need to be
    ### messages passed to the main function so that there are
    ### not situations where more than one subfunction is attempting
    ### to write to the terminal window at once.
    
    try:
        #print "trying to open" + str(foundMap)
        mxd = arcpy.mapping.MapDocument(mapPath)
        
        dataDrivenPagesObject = mxd.dataDrivenPages
        
        for exportItem in exportList:
            
            if mapScaleName == "QUARTER":
                quarterOrHalfFolder = "quarterInch"
                countyMapOutNamePDF = exportItem + "CountyQt.pdf" #+ foundMapOutName
                countyMapOutNamePNG = exportItem + "CountyQt.png"
            elif mapScaleName == "HALF":
                quarterOrHalfFolder = "halfInch"
                countyMapOutNamePDF = exportItem + "County.pdf" #+ foundMapOutName
                countyMapOutNamePNG = exportItem + "County.png"
            else:
                print "Map scale information not correctly supplied."
            
            ddpPageIndex = dataDrivenPagesObject.getPageIDFromName(exportItem)
            dataDrivenPagesObject.currentPageID = ddpPageIndex
            
            PDFOutpath = os.path.join(outputPDFParentFolder, quarterOrHalfFolder, countyMapOutNamePDF)
            PNGOutpath = os.path.join(outputPDFParentFolder, quarterOrHalfFolder, countyMapOutNamePNG)
            
            # Exporting to png requires a different bit of code than exporting to pdf.
            
            try:
                if whatToExport == 0: # export pdfs
                    dataDrivenPagesObject.exportToPDF(PDFOutpath, "CURRENT")
                elif whatToExport == 1: # export pngs
                    arcpy.mapping.ExportToPNG(mxd, PNGOutpath, "PAGE_LAYOUT", 0, 0, 300)
                elif whatToExport == 2: # export pngs & pdfs
                    arcpy.mapping.ExportToPNG(mxd, PNGOutpath, "PAGE_LAYOUT", 0, 0, 300)
                    dataDrivenPagesObject.exportToPDF(PDFOutpath, "CURRENT")
                else:
                    print "whatToExport value not set correctly. Will not export."
            except:
                if whatToExport == 0: # could not export pdfs
                    print "Could not export. to " + str(PDFOutpath) + "."
                elif whatToExport == 1: # could not export pngs
                    print "Could not export. to " + str(PNGOutpath) + "."
                elif whatToExport == 2: # could not export pngs & pdfs
                    print "Could not export. to " + str(PNGOutpath) + "."
                    print "Could not export. to " + str(PDFOutpath) + "."
                else:
                    print "Could not export."
                print arcpy.GetMessages()
            
        del mxd
        
        #### Don't print things from subprocesses. ####
        # I know, there are several print statements above.
        # They need to be changed so that they're passing
        # messages to the main process instead of printing
        # individually.
        #print mapPath + "'s process has completed."
        
    except Exception as e:
        # If an error occurred, print line number and error message
        tb = sys.exc_info()[2]
        print "Line %i" % tb.tb_lineno
        print e.message
    
    except:
        print "An error occurred." # Need to get the error from the arcpy object or result to figure out what's going on.
        print arcpy.GetMessages()
        pass


def mainProcessMapExports(mapPrefixName, mapsLocation, outputLocation, exportValue):
    '''
    Call with arguments in the format of ..., ..., exportValue, where the export value is
    one of the following: exportPDFs, exportPNGs, or exportPDFsAndPNGs.
    These should be imported/defined as exportPDFs = 0,  = 1, exportPDFsAndPNGs = 2.
    '''
    
    # Dynamically lists the files in the mxd folder (current workspace).
    # Then, add mirror-copies for each map to use, with the number of
    # mirror-copies made being higher for the most used mxds.
    
    mapsToUseList = list()
    
    # Get the map size information from the geodatabase.
    # searchFC comes from the config file.
    #searchFC = r'Database Connections\geo@countyMaps.sde\CountyMapSizes' #r'\\gisdata\ArcGIS\GISdata\GDB\CountyMappingDataMulti.gdb\CountyMapSizes'
    
    searchFieldList = ['County','quarterInchSize', 'mapOrientationDir', 'halfInchSize']
    
    countyMapSizeInfo = list()
    
    cursor = da.SearchCursor(searchFC, searchFieldList)  # @UndefinedVariable
    for row in cursor:
        countyMapSizeInfo.append(list(row))
    
    if 'cursor' in locals():
        del cursor
    else:
        pass
    if 'row' in locals():
        del row
    else:
        pass
    
    # Sort the list based on the County Name values.
    countyMapSizeInfo = sorted(countyMapSizeInfo, key=lambda countySize: str(countySize[0]))
    
    # Create a dictionary here to count the instances
    # of a particular map size.
    
    mirrorDict = dict()
    exportTargetList = list()
    
    for countyMapSize in countyMapSizeInfo:
        countyMapOrientation = str(countyMapSize[2])
        countyMapSizeQuarterString = str(countyMapSize[1])
        countyMapSizeHalfString = str(countyMapSize[3])
        countyMapName = str(countyMapSize[0])
        
        quarterKey = countyMapSizeQuarterString + countyMapOrientation
        halfKey = countyMapSizeHalfString + countyMapOrientation
        
        try:
            quarterValue = mirrorDict[quarterKey][0]
        except KeyError:
            blankList = list()
            mirrorDict[quarterKey] = [0, "Quarter", blankList]
        
        quarterValue = mirrorDict[quarterKey][0]
        quarterValue = quarterValue + 1
        exportTargetList = mirrorDict[quarterKey][2]
        exportTargetList.append(countyMapName)
        mirrorDict[quarterKey][0] = quarterValue
        mirrorDict[quarterKey][2] = exportTargetList
        
        try:
            halfValue = mirrorDict[halfKey][0]
        except KeyError:
            blankList = list()
            mirrorDict[halfKey] = [0, "Half", blankList]
        
        halfValue = mirrorDict[halfKey][0]
        halfValue = halfValue + 1
        exportTargetList = mirrorDict[halfKey][2]
        exportTargetList.append(countyMapName)
        mirrorDict[halfKey][0] = halfValue
        mirrorDict[halfKey][2] = exportTargetList
        
    mapMirrorList = list()
    subprocessInfoList = list()
    
    # When the map size is used 25 or more times,
    # it should be mirrored to improve performance,
    # up to 9 times.
    
    for mirrorDictKey in mirrorDict.keys():
        mapScale = mirrorDict[mirrorDictKey][1]
        mirrorDictValue = mirrorDict[mirrorDictKey][0]
        mirrorDictExportList = mirrorDict[mirrorDictKey][2]
        mirrorCount = (mirrorDictValue / 25) + 1 # If less than 25, will result in 1, so just use one mirror.
        if mirrorCount > 9:
            mirrorCount = 9
        else:
            pass
        mapMirrorList.append((mapScale, mirrorDictKey, mirrorCount, mirrorDictExportList))
        print "mirrorDictKey: " + mirrorDictKey
        print "mirrorDictValue: " + str(mirrorDictValue)
        print "mirrorDictExportList"
        for mirrorDictExportItem in mirrorDictExportList:
            print mirrorDictExportItem
    
    for mapToCopyInfo in mapMirrorList:
        mapSuffixName = mapToCopyInfo[0] + mapToCopyInfo[1]
        print "Will make " + str(mapToCopyInfo[2]) + " mirror(s) of " + mapPrefixName + mapSuffixName
        totalMirrors = mapToCopyInfo[2]
        countRange = range(0, totalMirrors)
        exportTargetList = mapToCopyInfo[3]
        originalFileFullPath = os.path.join(mapsLocation, mapPrefixName + mapSuffixName + ".mxd")
        for countItem in countRange:
            destinationFileFullPath = os.path.join(mapsLocation, mapPrefixName + mapSuffixName + "_Mirror" + str(countItem) + ".mxd")
            print destinationFileFullPath
            try:
                shutil.copy2(originalFileFullPath, destinationFileFullPath)
                print "Added " + str(destinationFileFullPath) + " to the filesystem."
                # Add the map to the mxdList so that it can be found/used in the subprocesses.
                # Do this part after the shutil.copy2 attempt so that if it fails
                # it doesn't get added to the mapsToUseList.
                if destinationFileFullPath not in mapsToUseList:
                    dividedExportTargets = list()
                    exportRemainder = countItem
                    exportCounter = 0
                    for exportTargetItem in exportTargetList:
                        if exportCounter % totalMirrors == exportRemainder:
                            dividedExportTargets.append(exportTargetItem)
                        else:
                            pass
                        exportCounter += 1
                    subprocessInfoList.append([destinationFileFullPath, dividedExportTargets, mapToCopyInfo[0]])
                    mapsToUseList.append(destinationFileFullPath)
                else:
                    pass
            except:
                print "Could not add " + str(destinationFileFullPath) + " to the filesystem."
                print "It may already exist."
                
    print "Maps to use:"
    for mapToUse in mapsToUseList:
        print str(mapToUse)
    
    # mirrorOffset = 0 # Is the first mirror.
    # mirrorOffset = 1 # Is the second mirror, etc.
    
    #outputQueue = mp.Queue()
    
    ### Mirror copy/use should be setup prior to creating the processes. ###
    
    # Predivide the list of data driven pages that each process needs to run
    # and pass it as a list of exportItems.
    
    coreCount = mp.cpu_count()
    
    # Setup a list of processes that we want to run
    # pass in full map location, export targets for that map
    ###processes = [mp.Process(target=subProcessMapExports, args=(subprocessInfoItem, outputLocation, exportValue)) for subprocessInfoItem in subprocessInfoList]
    #old#processes = [mp.Process(target=subProcessMapExports, args=(countyMapSizeInfo, mapsLocation, outputLocation, targetMapName, exportValue)) for targetMapName in mxdList]
    #old#2#processes = [mp.Process(target=exportMapPDFs, args=(outputQueue, countyMapSizeInfo, mapsLocation, outputLocation, targetMapName)) for targetMapName in mxdList]
    
    formattedInfoList = [(subprocessInfoItem, outputLocation, exportValue) for subprocessInfoItem in subprocessInfoList]
    
    # To support use on the slow AR60, reduce the coreCount used to try to keep this script from
    # crashing.
    if coreCount >= 3:
        coreCount = coreCount - 2
    else:
        coreCount = 1
        
    # Two subprocess testing -- see if this can be done on AR60 without crashing.
    coreCount = 2
    
    workPool = mp.Pool(processes=coreCount)
    # Note: This is a different usage of the word map than the one generally used in GIS.
    workPool.map(subProcessMapExports, formattedInfoList)#[(subprocessInfoItem, outputLocation, exportValue) for subprocessInfoItem in subprocessInfoList])
    print "Job's done!"
    
    # Run processes
    #for p in processes:
        #p.start()
    
    # Exit the completed processes
    #for p in processes:
        #p.join()
    
    # Get process results from the output queue
    #results = [outputQueue.get() for p in processes]
    
    #for resultItem in results:
    #    print (resultItem + "\n " + 
    #    "Retrieved time: " + str(datetime.datetime.now()))
    
    # Wait for several seconds for the locks to be released on the
    # maps prior to deletion.
    print "Waiting a moment to be sure that all of the locks have been removed..."
    time.sleep(100)
    # Remove the _Mirrored maps so that they can be recreated
    # with updated data next time.
    # Map directory cleanup. Removes the mirrored files so they can be rebuilt fresh next run.
    for mapToCopyInfo in mapMirrorList:
        mapSuffixName = mapToCopyInfo[0] + mapToCopyInfo[1]
        totalMirrors = mapToCopyInfo[2]
        countRange = range(0, totalMirrors)
        #originalFileFullPath = os.path.join(mapsLocation, mapPrefixName + mapSuffixName + ".mxd")
        for countItem in countRange:
            destinationFileFullPath = os.path.join(mapsLocation, mapPrefixName + mapSuffixName + "_Mirror" + str(countItem) + ".mxd")
            try:
                os.remove(destinationFileFullPath)
                print "Removed " + str(destinationFileFullPath) + " from the filesystem."
            except:
                print "Could not remove " + str(destinationFileFullPath) + " from the filesystem."
                print "It may be in use or might not exist."
    

if __name__ == "__main__":
    # try setting up a list of the maps
    # then, call a process for each map.
    
    startingTime = datetime.datetime.now()
    
    print "Starting Time: " + str(startingTime)
    
    mainProcessMapExports(originalMapType, mapsDirectory, outputDirectory, exportPDFsAndPNGs)
    # Don't forget to uncomment the rest of this.
    
    endingTime = datetime.datetime.now()
    
    scriptDuration = FindDuration(endingTime, startingTime)
    
    print "\n" # Newline for better readability.
    print "For the main/complete script portion..."
    print "Starting Time: " + str(startingTime)
    print "Ending Time: " + str(endingTime)
    print "Elapsed Time: " + scriptDuration
    
    # Doesn't work well on dt00ar60. Try on the geoprocessing server, if/when we get one.
    
    # Make a mainProcess & subProcess function, like in countymappdfcompositormulti.py
    # so that you can call it with options for pdf/jpg/png export.
    
    # mainProcessMapExports(mapsFolder, outputFolder, exportType)
    # subProcessMapExports(sizeInfo, mapsFolder, outputFolder, targetMapName, exportType) # sizeInfo and targetMapName assigned by mainProcess...
    
else:
    pass

# Change this to allow for the exporting of pdfs, jpgs, or pdfs + jpgs.
# Also, find out of you can use pngs instead of jpgs on the webpage.

# Next Script: countymappdfcompositormulti.py