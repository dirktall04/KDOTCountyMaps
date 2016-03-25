#!/usr/bin/env python
# -*- coding: utf-8 -*-
# county_map_copy_files_to_server.py

## The purpose of this script is to provide
## the logic used to move pdfs and pngs
## from the \\dt00mh02\planning\cart\
## location to the location used for serving
## those pdfs and pngs to the end user
## in KanPlan.
##
## Attempts to semi-intelligently deal with
## locking and related file movement
## issues that may arise.

import os
from shutil import copy2
import time
import fnmatch
import random

import datetime

from county_map_config import pythonLogTable, copy_map_server

try:
    from KDOT_Imports.dt_logging import scriptSuccess # @UnresolvedImport
except:
    print "Failed to import scriptSuccess"

try:
    from KDOT_Imports.dt_logging import scriptFailure # @UnresolvedImport
except:
    print "Failed to import scriptFailure"

try:
    from KDOT_Imports.dt_logging import ScriptStatusLogging # @UnresolvedImport
    print "ScriptStatusLogging imported."
except:
    print "Failed to import from KDOT_Imports.dt_logging"
    scriptSuccess = ""
    scriptFailure = ""
    def ScriptStatusLogging(taskName = 'county_map_copy_files_to_server',
                        taskTarget = r'\\' + copy_map_server + '\D$\arcgisserver\directories\arcgisoutput\County',
                        completionStatus = scriptFailure, taskStartDateTime = datetime.datetime.now(), 
                        taskEndDateTime = datetime.datetime.now(), completionMessage = 'Unexpected Error.',
                        tableForLogs = pythonLogTable):
        print "ScriptStatusLogging import failed."


sourceLocation = r"\\dt00mh02\planning\Cart\Maps\County" ## Upper level folder that contains the half and quarter inch folders
targetLocation = r'\\' + copy_map_server + '\D$\arcgisserver\directories\arcgisoutput\County' ## Upper level folder that contains the half and quarter inch folders.

quarterDirName = r"quarterInch"
halfDirName = r"halfInch"

## Build the the quarter inch and half inch folders from the sourceLocation.

quarterSourceLocation = os.path.join(sourceLocation, quarterDirName)
halfSourceLocation = os.path.join(sourceLocation, halfDirName)

## Build the quarter inch and half inch folders from the targetLocation.

quarterTargetLocation = os.path.join(targetLocation, quarterDirName)
halfTargetLocation = os.path.join(targetLocation, halfDirName)


def mapFilesTransfer():
    # Get the list of quarter inch maps.
    mapFileList = [mapFileName for mapFileName in os.listdir(quarterSourceLocation) if (fnmatch.fnmatch(mapFileName, "*.pdf") or fnmatch.fnmatch(mapFileName, "*.png") == True)]
    
    errorList = list()
    
    for mapFileItem in mapFileList:
        print mapFileItem
        mapFileItemSourcePath = os.path.join(quarterSourceLocation, mapFileItem)
        mapFileItemTargetPath = os.path.join(quarterTargetLocation, mapFileItem)
        try:
            copy2(mapFileItemSourcePath, mapFileItemTargetPath)
        except:
            print("Error copying the map from %s to %s.") % (mapFileItemSourcePath, mapFileItemTargetPath)
            errorList.append((mapFileItemSourcePath, mapFileItemTargetPath))
    
    
    # Clear the mapFileList list and reuse it for the half inch maps.
    try:
        del mapFileList
    except:
        pass
    
    
    # Get the list of half inch maps.
    mapFileList = [mapFileName for mapFileName in os.listdir(halfSourceLocation) if (fnmatch.fnmatch(mapFileName, "*.pdf") or fnmatch.fnmatch(mapFileName, "*.png") == True)]
    
    for mapFileItem in mapFileList:
        print mapFileItem
        mapFileItemSourcePath = os.path.join(halfSourceLocation, mapFileItem)
        mapFileItemTargetPath = os.path.join(halfTargetLocation, mapFileItem)
        try:
            copy2(mapFileItemSourcePath, mapFileItemTargetPath)
        except:
            print("Error copying the map from %s to %s.") % (mapFileItemSourcePath, mapFileItemTargetPath)
            errorList.append((mapFileItemSourcePath, mapFileItemTargetPath))
    
    
    ## Don't need to do retries if the lists are empty, so
    ## check their length before attempting each retry iteration.
    # Test the retry logic by having a map open in the targetLocation.
    
    errorListLength = len(errorList)
    
    retryFailList = list()
    secondRetryList = list()
    thirdRetryList = list()
    
    if errorListLength >= 1:
        
        for errorItem in errorList:
            splitMapPath = os.path.split(str(errorItem[0]))
            mapNameNoPath = str(splitMapPath[-1])
            print "Was initially unable to copy the map called %s." % (mapNameNoPath)
            print "Retrying..."
            try: 
                copy2(str(errorItem[0]), str(errorItem[1]))
                print("Successfully retried copying the map called: %s") % (mapNameNoPath)
            except:
                print("Error copying the map called %s.") % (mapNameNoPath)
                print "Retry attempt failed."
                retryFailList.append((errorItem[0], errorItem[1]))
    
    retryFailListLength = len(retryFailList)
    
    if retryFailListLength >= 1:
        # Back off for a random period of time, then try again.
        randomWaitTime = random.randint(7, 77)
        
        print("Will wait %s seconds before trying again.") % (randomWaitTime)
        
        time.sleep(randomWaitTime)
        
        # Retry a second time
        
        for retryFailItem in retryFailList:
            splitMapPath = os.path.split(str(retryFailItem[0]))
            mapNameNoPath = str(splitMapPath[-1])
            print "Second retry attempt to copy the map called %s." % (mapNameNoPath)
            print "Retrying..."
            try: 
                copy2(str(retryFailItem[0]), str(retryFailItem[1]))
                print("Successfully retried copying the map called: %s") % (mapNameNoPath)
            except:
                print("Error copying the map called %s.") % (mapNameNoPath)
                print "Retry attempt failed."
                secondRetryList.append((retryFailItem[0], retryFailItem[1]))
    
    secondRetryListLength = len(secondRetryList)
    
    if secondRetryListLength >= 1:
        # Back off for a random period of time, then try again.
        randomWaitTime = random.randint(7, 77)
        
        print("Will wait %s seconds before trying again.") % (randomWaitTime)
        
        time.sleep(randomWaitTime)
        
        # Retry a third time
        
        for secondRetryItem in secondRetryList:
            splitMapPath = os.path.split(str(secondRetryItem[0]))
            mapNameNoPath = str(splitMapPath[-1])
            print "Last attempt to copy the map called %s." % (mapNameNoPath)
            print "Retrying..."
            try: 
                copy2(str(secondRetryItem[0]), str(secondRetryItem[1]))
                splitMapPath = os.path.split(str(secondRetryItem[0]))
                print("Successfully retried copying the map called: %s") % (mapNameNoPath)
            except:
                print("Error copying the map called %s.") % (mapNameNoPath)
                print "Retry attempt failed."
                thirdRetryList.append((secondRetryItem[0], secondRetryItem[1]))
    
    # After three retry attempts, exit and worry about it next time.
    
    thirdRetryFailCount = len(thirdRetryList)
    
    if thirdRetryFailCount == 0:
        print("\nAll maps were successfully copied to the KanPlan server.")
    elif thirdRetryFailCount == 1:
        print("\nMaps were copied to the KanPlan server with 1 failure.")
    else:
        print("\nMaps were copied to the KanPlan server with %d failures.") % (thirdRetryFailCount)
    
    return thirdRetryFailCount


if __name__ == "__main__":
    startTime = (datetime.datetime.now()) 
    print str(startTime) + " starting script"
    failedToTransfer = mapFilesTransfer()
    endTime = datetime.datetime.now()
    runTime = endTime - startTime
    print str(endTime) + " script completed in " + str(runTime)
    if failedToTransfer == 0:
        completionStatus = 'Completed Successfully.'
    elif failedToTransfer == 1:
        completionStatus = 'Completed successfully, with ' + failedToTransfer + ' map not transferred.'
    else:
        completionStatus = 'Completed successfully, with ' + failedToTransfer + ' maps not transferred.'
    ScriptStatusLogging('county_map_copy_files_to_server',
        r'\\' + copy_map_server + '\D$\arcgisserver\directories\arcgisoutput\County',
        scriptSuccess, startTime, endTime, completionStatus, pythonLogTable)
    
else:
    print "county_map_copy_files_to_server script imported"