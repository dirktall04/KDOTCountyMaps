#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CountyMapRoadNameBorderCreation.py

# TODO: Add logic to improve the process of 
# choosing which points to keep.
# Important to make sure that the poitns


# Takes the data from the excel file and puts it into
# an ESRI geodatabase for easier use in other scripts.

# Use a searchcursor to read in the rows here
# and apply them to other data.

import os
import xlrd
from arcpy import (AddField_management, Append_management, Array as ArcgisArray,
                   Buffer_analysis, CopyFeatures_management,
                   CreateFeatureclass_management, Delete_management,
                   DeleteFeatures_management, DeleteRows_management, Describe,
                   env, Erase_analysis, ExecuteError, ExcelToTable_conversion,
                   Exists, Dissolve_management, GetCount_management,
                   GetMessages, Intersect_analysis, ListFields,
                   MakeFeatureLayer_management, MultipartToSinglepart_management,
                   Point as ArcgisPoint, Polyline as ArcgisPolyLine,
                   SelectLayerByAttribute_management)
import sys
from arcpy.da import (SearchCursor as daSearchCursor, InsertCursor as daInsertCursor, # @UnresolvedImport @UnusedImport
                        UpdateCursor as daUpdateCursor, Editor as daEditor)  # @UnresolvedImport @UnusedImport

from generate_rs_and_hwy_endings import route_endings_generation

excelSettingsLocation = r'\\dt00mh02\Planning\Cart\Maps\MXD\Update\CountyMapDataDrivenSettings.xlsx'

from county_map_config import sdeProdLocation, sqlGdbLocation

sdeProdUser  = 'SHARED.'
sharedNonStateSystem = os.path.join(sdeProdLocation, sdeProdUser + 'Non_State_System')
sharedCounties = os.path.join(sdeProdLocation, sdeProdUser + 'COUNTIES')
sharedNonStateBridges = os.path.join(sdeProdLocation, sdeProdUser + 'NON_STATE_BRIDGES')
sharedStateBridges = os.path.join(sdeProdLocation, sdeProdUser + 'GIS_BRIDGE_DETAILS_LOC')
sharedCityLimits = os.path.join(sdeProdLocation, sdeProdUser + 'CITY_LIMITS')
sharedCountyLines = os.path.join(sdeProdLocation, sdeProdUser + 'COUNTY_LINES')


sqlGdbUser = 'countyMaps.GEO.'
countyMapSizes = os.path.join(sqlGdbLocation, sqlGdbUser + 'CountyMapSizes')
countyStateBridges= os.path.join(sqlGdbLocation, sqlGdbUser + 'County_State_Bridges')
countyNonStateBridges = os.path.join(sqlGdbLocation, sqlGdbUser + 'County_Non_State_Bridges')
countyLinesIntersectedNoPath = 'CountyLinesIntersected'
countyLinesIntersectedWithUser = os.path.join(sqlGdbUser, countyLinesIntersectedNoPath)
countyLinesIntersectedPath = os.path.join(sqlGdbLocation, sqlGdbUser + countyLinesIntersectedNoPath)

## In_Memory Layers start here:
inMemGDB = "in_memory"

countiesNoZ = os.path.join(inMemGDB, 'Counties_No_Z')
nSSNoZ = os.path.join(inMemGDB, 'Non_State_System_No_Z')
nSSNoZCounty = os.path.join(inMemGDB, 'Non_State_System_No_Z_County')
nSSNoZCountyDS = os.path.join(inMemGDB, 'Non_State_System_No_Z_County_DS')
nSSNoZCountyClean = os.path.join(inMemGDB, 'Non_State_System_No_Z_County_Cleaned')
countiesNoZEraseBuffer = os.path.join(inMemGDB, 'Counties_No_Z_Erase_Buffer')
countiesNoZExtensionBuffer_Q = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_Q')
countiesNoZExtensionBuffer_H = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_H')
nSSForPointCreation = os.path.join(inMemGDB, 'Non_State_System_For_Point_Creation')
countyLinesDissolved = os.path.join(inMemGDB, 'CountyLinesDissolved')
countiesBuffered = os.path.join(inMemGDB, 'CountiesBuffered')

# Get/use the same projection as the one used for the county roads.
spatialReferenceProjection = Describe(sharedNonStateSystem).spatialReference


def ImportAllSheets(inExcel):
    workbook = xlrd.open_workbook(inExcel)
    sheets = [sheet.name for sheet in workbook.sheets()]
    
    print('{} sheets found: {}'.format(len(sheets), ','.join(sheets)))
    sheetCounter = 0
    
    for sheet in sheets:
        # The out_table is based on the input excel file name
        # an underscore (_) separator followed by the sheet name
        if sheetCounter == 0:
            try:
                try:
                    Delete_management(countyMapSizes)
                except:
                    pass
                
                print('Converting {} to {}'.format(sheet, countyMapSizes))
                
                # Perform the conversion
                ExcelToTable_conversion(inExcel, countyMapSizes, sheet)
            except:
                print "There was an error in writing the countyMapSizes table."
            
        else:
            pass
        
        sheetCounter = sheetCounter + 1
    
    print "Sheet import complete!"


def nonStateAndCountyImport():
    
    # Copy the county polygons and the
    # non_state_system from Oracle.
    env.workspace = inMemGDB
    
    Delete_management(inMemGDB)
    
    print "Importing the Non_State_System..."
    nonStateSystemToCopy = sharedNonStateSystem
    nonStateSystemOutput = nSSNoZ
    CopyFeatures_management(nonStateSystemToCopy, nonStateSystemOutput)    
    
    print "Importing the Counties..."
    countyPolygonsToCopy = sharedCounties # Changed to sdeprod
    countyPolygonsOutput = countiesNoZ
    CopyFeatures_management(countyPolygonsToCopy, countyPolygonsOutput)


def countyAndRoadPreprocessing():
    
    print "Removing non-County roads and other roads not displayed on the map..."
    featureClass1 = nSSNoZ
    featureClass1Out = nSSNoZCounty
    
    inMemoryRoadsLayer1 = "roadsToCounty"
    
    # Need to delete out the non-county roads.
    CopyFeatures_management(featureClass1, featureClass1Out)
    
    # Load the feature class with all non_state roads.    
    MakeFeatureLayer_management(featureClass1Out, inMemoryRoadsLayer1)
    
    
    # Now select & delete all the roads that do not have 999 as their city number, which would mean
    # that they are in the county.
    # Also select any roads that will not be shown in the map per Elaine's query:
    # (SURFACE <> 'Propose' AND SURFACE IS NOT NULL) AND VISIBILITY = 'Y'
    selectionString = """ "CITYNUMBER" <> 999 OR SURFACE = 'Propose' OR SURFACE IS NULL OR VISIBILITY <> 'Y' """
    
    SelectLayerByAttribute_management(inMemoryRoadsLayer1, "NEW_SELECTION", selectionString)
    
    countNumber = GetCount_management(inMemoryRoadsLayer1)
    
    if countNumber >= 1:
        try:
            DeleteFeatures_management(inMemoryRoadsLayer1)
        except Exception as e:
            # If an error occurred, print line number and error message
            tb = sys.exc_info()[2]
            print("Line {0}".format(tb.tb_lineno))
            print(e.message)
    else:
        pass
    
    # Cleanup
    if 'inMemoryRoadsLayer1' in locals():
        del inMemoryRoadsLayer1
    else:
        pass
    
    featureClass2 =  nSSNoZCounty
    fieldListForRoads = ["RD_NAMES", "COUNTY_NUMBER"]
    featureClass2Out = nSSNoZCountyDS
    
    featureClass3 = featureClass2Out
    featureClass3Out = nSSNoZCountyClean
    
    inMemoryRoadsLayer2 = "roadsToDissolve"
    inMemoryRoadsLayer3 = "roadsToClean"
    
    
    print "Dissolving road segments by Name & County..."
    # Load the undissolved feature class.    
    MakeFeatureLayer_management(featureClass2, inMemoryRoadsLayer2)
    
    # Dissolve based on RD_NAMES and COUNTY_NUMBER.    
    Dissolve_management(inMemoryRoadsLayer2, featureClass2Out, fieldListForRoads, "", 
                          "SINGLE_PART", "DISSOLVE_LINES")
    
    # Cleanup
    if 'inMemoryRoadsLayer2' in locals():
        del inMemoryRoadsLayer2
    else:
        pass
    
    
    print "Deleting unnamed road segments..."
    # Copy the feature class to prepare for deleting unnamed roads.
    CopyFeatures_management(featureClass3, featureClass3Out)
    
    # Load the copied feature class.
    MakeFeatureLayer_management(featureClass3Out, inMemoryRoadsLayer3)
    
    # Now select & delete all the roads that have <null> or "" as their roadname.
    selectionString = """ "RD_NAMES" IS NULL OR "RD_NAMES" = '' OR "COUNTY_NUMBER" = 0 OR "COUNTY_NUMBER" >= 106"""
    
    
    SelectLayerByAttribute_management(inMemoryRoadsLayer3, "NEW_SELECTION", selectionString)
    
    countNumber = GetCount_management(inMemoryRoadsLayer3)
    
    print "For " + selectionString + ", selected = " + str(countNumber)
    
    if countNumber >= 1:
        try:
            DeleteFeatures_management(inMemoryRoadsLayer3)
        except Exception as e:
            # If an error occurred, print line number and error message
            tb = sys.exc_info()[2]
            print("Line {0}".format(tb.tb_lineno))
            print(e.message)
            try:
                del tb
            except:
                pass
    else:
        pass
    
    # Cleanup
    if 'inMemoryRoadsLayer3' in locals():
        del inMemoryRoadsLayer3
    else:
        pass
    
    
    print "Preprocessing for county road label points is complete!"


def countyBuffersAndNon_StateErase():
    # Need to do this for _Q and also for _H
    print "Now adding county polygon buffers..."
    
    countyPolygonsMain = countiesNoZ
    countyPolygonsEraseBuffer = countiesNoZEraseBuffer
    
    # Buffer distance to 11000 for H, 20000 for Q.
    bufferDistance_Q = 20000
    bufferDistance_H = 13250
    bufferDistance_Erase = 11000
    print "Creating the Extension Buffer"
    Buffer_analysis(countyPolygonsMain, countiesNoZExtensionBuffer_Q, bufferDistance_Q, "FULL", "", "NONE")
    Buffer_analysis(countyPolygonsMain, countiesNoZExtensionBuffer_H, bufferDistance_H, "FULL", "", "NONE")
    
    print "Creating the Erase Buffer"
    Buffer_analysis(countyPolygonsMain, countyPolygonsEraseBuffer, (-1 * bufferDistance_Erase), "FULL", "", "NONE")
    
    print "Done adding county polygon buffers!"
    
    print "Starting road feature erase."
    
    xyToleranceVal = "5 Feet"
    featureClass4 = nSSNoZCountyClean
    featureClass4Out = nSSForPointCreation
    
    Erase_analysis(featureClass4, countyPolygonsEraseBuffer, featureClass4Out, xyToleranceVal)
    
    print "Road feature erase complete!"


# This function makes two new datasets for bridges that include only bridges outside of the city boundaries.
def countyOnlyBridgeExport():
    xyToleranceVal = "5 Feet"
    nonStateBridgeLayerIn = sharedNonStateBridges
    stateBridgeLayerIn = sharedStateBridges
    cityPolygons = sharedCityLimits
    
    nonStateBridgeLayerOut = countyNonStateBridges
    stateBridgeLayerOut = countyStateBridges
    
    # Will contain only Non-State Bridges outside of Cities
    Erase_analysis(nonStateBridgeLayerIn, cityPolygons, nonStateBridgeLayerOut, xyToleranceVal)
    
    # Will contain only State Bridges outside of Cities
    Erase_analysis(stateBridgeLayerIn, cityPolygons, stateBridgeLayerOut, xyToleranceVal)


def createCountyLinesForEachCounty():
    
    env.workspace = sqlGdbLocation
    
    inputCountyLines = sharedCountyLines
    inputCountyPolygons = sharedCounties
    dissolvedCountyLines = countyLinesDissolved
    loadedCounties = 'loadedCounties'
    tempCountyLines = r'in_memory\tempCountyLines'
    outputCountyLines = countyLinesIntersectedNoPath
    bufferCursorFields = ["OBJECTID"]
    
    # Dissolve all of those county lines into one set of lines
    # then, need to create 105 features that are are intersected
    # with the polygons from said line dissolve.
    
    Dissolve_management(inputCountyLines, dissolvedCountyLines)
    Buffer_analysis(inputCountyPolygons, countiesBuffered, "15500 Feet")
    
    bufferedCountyPolygonList = list()
    outputFeatureList = list()
    
    # 1st SearchCursor
    newCursor = daSearchCursor(countiesBuffered, bufferCursorFields)
    for newRow in newCursor:
        bufferedCountyPolygonList.append(list(newRow))
        
    if 'newCursor' in locals():
        del newCursor
    else:
        pass
    
    MakeFeatureLayer_management(countiesBuffered, loadedCounties)
    
    loadedCountiesFields = ListFields(loadedCounties)
    
    for loadedCountiesField in loadedCountiesFields:
        print "A loadedCountiesField was found: " + str(loadedCountiesField.name)
    
    for listedRow in bufferedCountyPolygonList:
        selectNumber = listedRow[0]
        
        whereClause = """ "OBJECTID" = """ + str(selectNumber)
        print "The whereClause = " + str(whereClause)
        SelectLayerByAttribute_management(loadedCounties, "NEW_SELECTION", whereClause)
        
        Intersect_analysis([dissolvedCountyLines, loadedCounties], tempCountyLines, "ALL")
        
        # 2nd SearchCursor
        newCursor = daSearchCursor(tempCountyLines, ["SHAPE@", "County_Number", "County_Name"])
        for newRow in newCursor:
            outputFeatureList.append(newRow)
        
        if 'newCursor' in locals():
            del newCursor
        else:
            pass
    
    try:
        Delete_management(countyLinesIntersectedWithUser)
    except:
        pass
    
    CreateFeatureclass_management(sqlGdbLocation, outputCountyLines, "POLYLINE", "", "", "", spatialReferenceProjection)
    
    AddField_management(outputCountyLines, "County_Number", "DOUBLE", "", "", "")
    
    AddField_management(outputCountyLines, "County_Name", "TEXT", "", "", "55")
    
    print "First Intersected County Row: " + str(outputFeatureList[0])
    
    countyLinesIntersectFields = ["SHAPE@", "County_Number", "County_Name"]
    
    newCursor = daInsertCursor(countyLinesIntersectedPath, countyLinesIntersectFields)
    counter = 1
    for outputFeature in outputFeatureList:
        rowToInsert = ([outputFeature])
        
        insertedOID = newCursor.insertRow(outputFeature)
        
        counter += 1
        
        print "Inserted Row with Object ID of " + str(insertedOID)
        
    if 'newCursor' in locals():
        del newCursor
    else:
        pass


    #
    ######################### End of MapPreprocessing
    #


# When finished, work on the script logging function and then add it into this script.
# Also, move this script to a server and schedule it to run once a month.


import math
from math import radians, sin, cos, floor, sqrt, pow  # @UnusedImport
import datetime

env.workspace = inMemGDB
env.overwriteOutput = True
env.outputZFlag = "Disabled"


# Actually persist these feature class
#countyRoadsFeature = os.path.join(sqlGdbLocation, sqlGdbUser + 'Non_State_System_For_Point_Creation')
countyRoadNameRosette_Q = os.path.join(sqlGdbLocation, sqlGdbUser + "countyRoadNameRosette_Q") # quarter
countyRoadNameRosette_H = os.path.join(sqlGdbLocation, sqlGdbUser + "countyRoadNameRosette_H") # half -- Still need to build the logic to create this.

# These to in_memory, no persistence. Most of these are dependent upon scaling, right? Check that.
countyBorderFeature_Q = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_Q')
countyBorderFeature_H = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_H')
countyRoadsFeature = os.path.join(inMemGDB, 'Non_State_System_For_Point_Creation')
createdExtensionLines_Q = os.path.join(inMemGDB, "createdExtensionLines_Q")
createdExtensionLines_H = os.path.join(inMemGDB, "createdExtensionLines_H")
tempRoadNameRosette_Q = os.path.join(inMemGDB, "tempRoadNameRosette_Q")
tempRoadNameRosette_H = os.path.join(inMemGDB, "tempRoadNameRosette_H")
tempRoadNameRosetteSinglePoint_Q = os.path.join(inMemGDB, "tempRoadNameRosetteSinglePoint_Q")
tempRoadNameRosetteSinglePoint_H = os.path.join(inMemGDB, "tempRoadNameRosetteSinglePoint_H")

# Not sure why I need two ID columns here... -- can't I change it to just 1?
# Trying with just one on 8/21/2015
roadCursorFields = ["OID@", "SHAPE@", "RD_NAMES", "COUNTY_NUMBER"] 
countyBorderFields = ["OBJECTID", "SHAPE@XY", "COUNTY_NAME", "COUNTY_NUMBER"]
countyRoadNameRosetteFields = ["LabelAngle", "COUNTY_NAME", "COUNTY_NUMBER"]
countyRoadNameRosetteFieldsObjShape = ["OID@", "SHAPE@XY", "roadNameForSplit", "COUNTY_NUMBER", "COUNTY_NAME"]


def FindDuration(endTime, startTime):
    #Takes two datetime.datetime objects, subtracting the 2nd from the first
    #to find the duration between the two.
    duration = endTime - startTime
    
    dSeconds = int(duration.seconds)
    durationp1 = str(int(dSeconds // 3600)).zfill(2)
    durationp2 = str(int((dSeconds % 3600) // 60)).zfill(2)
    durationp3 = str(int(dSeconds % 60)).zfill(2)
    durationString = durationp1 + ':' +  durationp2 + ':' + durationp3
    
    return durationString


def getBorderFeatureList(quarterOrHalf):
    
    if quarterOrHalf.lower() == "quarter":
        countyBorderFeature = countyBorderFeature_Q
    elif quarterOrHalf.lower() == "half":
        countyBorderFeature = countyBorderFeature_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf error."))
    
    print "Getting border feature list."
    
    borderFeatureCursor = daSearchCursor(countyBorderFeature, countyBorderFields)
    
    borderFeaturesToReturn = list()
    
    for borderFeature in borderFeatureCursor:
        borderFeaturesToReturn.append(borderFeature)
        
    return borderFeaturesToReturn


def calcPointDistance(point1, point2):
    
    point2X = point2[0]
    point1X = point1[0]
    
    point2Y = point2[1]
    point1Y = point1[1]
    
    xDifference = point2X - point1X
    yDifference = point2Y - point1Y
    
    distanceBetweenPoints = math.sqrt( xDifference * xDifference + yDifference * yDifference )
    
    return distanceBetweenPoints


def getRoadLinesList():
    
    print "Getting the road lines list."
    # Need a new function here. -- Instead of calling this twice, have a main-style funtion
    # call it once and then pass it as an argument to both functions.
    roadCursor = daSearchCursor(countyRoadsFeature, roadCursorFields)  # @UndefinedVariable
    
    roadLinesToReturn = list()
    
    for roadPolyline in roadCursor:
        roadLinesToReturn.append(list(roadPolyline))
        
    if "roadCursor" in locals():
        del roadCursor
    else:
        pass
    
    return roadLinesToReturn


def removeSmallRoads():
    
    # Going to have to build a list of OIDs for roads
    # with a Shape length less than or equal to 1500.
    # Not going to have the SQL information to do a
    # selection based on a clause.
    
    # Could also add a field and then calculate the
    # length into it prior to running this selection.
    
    # Need to make a search cursor that gets the ObjectID and ShapeLength
    # for each road.
    
    # Then, need to add the ObjectID for roads with ShapeLength less than
    # 1500 to a list, then build SQL queries dynamically to select
    # and add features from that list, until the list is exhausted
    # and all features have been selected.
    
    print "Removing the small roads from the data."
    
    #CopyFeatures_management(countyRoadsFeature, countyRoadsFeaturePrereduction_Q)
    
    inMemoryRoadsLayer = 'inMemoryRoadsLayerFC'
    
    MakeFeatureLayer_management(countyRoadsFeature, inMemoryRoadsLayer)
    
    inMemRoadsFields = ListFields(inMemoryRoadsLayer)
    
    for inMemRoadField in inMemRoadsFields:
        print str(inMemRoadField.name)
    
    smallRoadsSCFields = ['ID2', 'Shape@Length']
    
    smallRoadsSearchCursor = daSearchCursor(inMemoryRoadsLayer, smallRoadsSCFields)
    
    roadIDsToRemove = list()
    
    '''
    for smallRoadRow in smallRoadsSearchCursor:
        if int(str(smallRoadRow[0])) % 500 == 0:
            print str(smallRoadRow[0])
        else:
            pass
        
    raise("Stop error.")
    '''
    
    for smallRoadRow in smallRoadsSearchCursor:
        if smallRoadRow[1] <= 1500:
            roadIDsToRemove.append(smallRoadRow[0])
        else:
            pass
    
    roadRemovalCounter = 0
    
    roadsReductionWhereClause = """ "ID2" IN ("""
    
    for roadID in roadIDsToRemove:
        if roadRemovalCounter <= 998:
            roadsReductionWhereClause = roadsReductionWhereClause + str(roadID) + """, """
            roadRemovalCounter += 1
        else:
            # Remove the trailing ", " and add a closing parenthesis.
            roadsReductionWhereClause = roadsReductionWhereClause[:-2] + """) """ 
            SelectLayerByAttribute_management(inMemoryRoadsLayer, "ADD_TO_SELECTION", roadsReductionWhereClause)
            
            # Debug only
            print "Selecting..."
            selectedRoadsResult = GetCount_management(inMemoryRoadsLayer)
            selectedRoadsCount = int(selectedRoadsResult.getOutput(0))
            print "Number of roads selected: " + str(selectedRoadsCount)
            
            roadRemovalCounter = 0
            roadsReductionWhereClause = """ "ID2" IN ("""
            roadsReductionWhereClause = roadsReductionWhereClause + str(roadID) + """, """
    
    # Remove the trailing ", " and add a closing parenthesis.
    roadsReductionWhereClause = roadsReductionWhereClause[:-2] + """) """ 
    SelectLayerByAttribute_management(inMemoryRoadsLayer, "ADD_TO_SELECTION", roadsReductionWhereClause)
    
    # Debug only
    print "Selecting..."
    selectedRoadsResult = GetCount_management(inMemoryRoadsLayer)
    selectedRoadsCount = int(selectedRoadsResult.getOutput(0))
    print "Number of roads selected: " + str(selectedRoadsCount)
    
    selectedRoadsResult = GetCount_management(inMemoryRoadsLayer)
    
    selectedRoadsCount = int(selectedRoadsResult.getOutput(0))
    
    if selectedRoadsCount >= 1:
        DeleteFeatures_management(inMemoryRoadsLayer)
    else:
        pass


# Improve this with the changes made to the angle test employed by the AccidentDirectionMatrixOffset code.
def extendAndIntersectRoadFeatures(quarterOrHalf): # Place the operations that extend each road line segment by a certain distance here.
    # Should extend all the features that exist in the post-erase dataset. Might be more difficult
    # to calculate the angle of these lines accurately, but it should be easier to figure out
    # than trying to get the lines to split correctly with the buggy SplitLineAtPoint tool.
    
    if quarterOrHalf.lower() == "quarter":
        extensionLinesTextName = "createdExtensionLines_Q"
        createdExtensionLines = createdExtensionLines_Q
        # 9000 ft increase for _Q version.
        # Must be larger than the county bufferDistance (20000)
        extensionDistance = 31176
        extensionLinesTextName = "createdExtensionLines_Q"
        countyRoadNameRosette = countyRoadNameRosette_Q
        rosetteTextName = "countyRoadNameRosette_Q"
        tempRoadNameRosette = tempRoadNameRosette_Q
        tempRosetteTextName = "tempRoadNameRosette_Q"
        tempRoadNameRosetteSP = tempRoadNameRosetteSinglePoint_Q
        tempRosetteSPTextName = "tempRoadNameRosetteSinglePoint_Q"
        countyBorderFeature = countyBorderFeature_Q
    elif quarterOrHalf.lower() == "half":
        extensionLinesTextName = "createdExtensionLines_H"
        createdExtensionLines = createdExtensionLines_H
        # Must be larger than the county bufferDistance (11000)
        extensionDistance = 22176
        extensionLinesTextName = "createdExtensionLines_H"
        countyRoadNameRosette = countyRoadNameRosette_H
        rosetteTextName = "countyRoadNameRosette_H"
        tempRoadNameRosette = tempRoadNameRosette_H
        tempRosetteTextName = "tempRoadNameRosette_H"
        tempRoadNameRosetteSP = tempRoadNameRosetteSinglePoint_H
        tempRosetteSPTextName = "tempRoadNameRosetteSinglePoint_H"
        countyBorderFeature = countyBorderFeature_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf value error."))
    
    print "Starting to extend and intersect road features."
    
    if Exists(createdExtensionLines):
        Delete_management(createdExtensionLines)
    else:
        pass
    
    
    CreateFeatureclass_management(inMemGDB, extensionLinesTextName, "POLYLINE", "", "", "", spatialReferenceProjection)
    
    # Add a column for roadname called roadNameForSplit.
    AddField_management(createdExtensionLines, "roadNameForSplit", "TEXT", "", "", "55")
    
    # Add a column which stores the angle to display a label called called LabelAngle.
    AddField_management(createdExtensionLines, "LabelAngle", "DOUBLE", "", "", "") # Change to double.
    
    # Add a column which stores the County Number.
    AddField_management(createdExtensionLines, "County_Number", "DOUBLE", "", "", "")
    
    roadLinesToInsertList = list()
    
    roadLinesList = getRoadLinesList()
    
    for roadLinesItem in roadLinesList:
        
        roadNameToUse = roadLinesItem[2]
        countyNumber = roadLinesItem[3]
        
        linePointsArray = ArcgisArray()
        
        firstPointTuple = (roadLinesItem[1].firstPoint.X, roadLinesItem[1].firstPoint.Y)
        lastPointTuple = (roadLinesItem[1].lastPoint.X, roadLinesItem[1].lastPoint.Y)
        
        
        # Make this a two-step process.
        # Might be as simple as
        # adding _1 to the end of the first set of variables,
        # adding _2 to the end of the second set of variables,
        # then making the extensions in both directions
        # and creating a new line that has the endpoints
        # from both sides as it's first and last point.
        # if necessary, could add the other points in between
        # but probably not necessary just for generating
        # an intersection point.
        
        
        yValue_1 = -(lastPointTuple[1] - firstPointTuple[1]) # made y value negative
        xValue_1 = lastPointTuple[0] - firstPointTuple[0]
        
        lineDirectionAngle_1 = math.degrees(math.atan2(xValue_1, yValue_1)) # reversed x and y
        
        lineDirectionAngle_1 = -(((lineDirectionAngle_1 + 180) % 360) - 180) # correction for certain quadrants
        #print "lineDirectionAngle: " + str(lineDirectionAngle_1)
        
        origin_x_1 = firstPointTuple[0]
        origin_y_1 = firstPointTuple[1]
        
        
        yValue_2 = -(firstPointTuple[1] - lastPointTuple[1]) # made y value negative
        xValue_2 = firstPointTuple[0] - lastPointTuple[0]
        
        lineDirectionAngle_2 = math.degrees(math.atan2(xValue_2, yValue_2)) # reversed x and y
        
        lineDirectionAngle_2 = -(((lineDirectionAngle_2 + 180) % 360) - 180) # correction for certain quadrants
        #print "lineDirectionAngle: " + str(lineDirectionAngle_2)
        
        origin_x_2 = lastPointTuple[0]
        origin_y_2 = lastPointTuple[1]
        
        (disp_x_1, disp_y_1) = (extensionDistance * math.sin(math.radians(lineDirectionAngle_1)),
                          extensionDistance * math.cos(math.radians(lineDirectionAngle_1)))
        
        (end_x_1, end_y_1) = (origin_x_1 + disp_x_1, origin_y_1 + disp_y_1)
        
        
        (disp_x_2, disp_y_2) = (extensionDistance * math.sin(math.radians(lineDirectionAngle_2)),
                          extensionDistance * math.cos(math.radians(lineDirectionAngle_2)))
        
        (end_x_2, end_y_2) = (origin_x_2 + disp_x_2, origin_y_2 + disp_y_2)
        
        startPoint = ArcgisPoint()
        endPoint = ArcgisPoint()
        
        startPoint.ID = 0
        startPoint.X = end_x_1
        startPoint.Y = end_y_1
        
        endPoint.ID = 1
        endPoint.X = end_x_2
        endPoint.Y = end_y_2
        
        linePointsArray.add(startPoint)
        linePointsArray.add(endPoint)
        
        newLineFeature = ArcgisPolyLine(linePointsArray)
        
        # Need to create an extension for both ends of the line and add them
        # to the array.
        
        #newLineFeature = createdExtensionLinesCursor.newRow()
        
        #newLineFeature.SHAPE = linePointsArray
        
        lineDirectionOutput = "0"
        
        if lineDirectionAngle_1 > 0:
            lineDirectionOutput = lineDirectionAngle_1
        elif lineDirectionAngle_2 > 0:
            lineDirectionOutput = lineDirectionAngle_2
        else:
            pass
        
        
        roadLinesToInsertList.append([newLineFeature, roadNameToUse, lineDirectionOutput, countyNumber])
        
        #createdExtensionLinesCursor.insertRow([newLineFeature, roadNameToUse, lineDirectionOutput])
        
        if "newLineFeature" in locals():
            del newLineFeature
        else:
            pass
    
    # Consider building this as a separate list and then just looping
    # through the list to put it into the cursor instead
    # of doing logic and inserting into the cursor at the same place.
    
    
    #start editing session
    #newEditingSession = daEditor(sqlGdbLocation)
    #newEditingSession.startEditing()
    #newEditingSession.startOperation()
    
    createdExtensionLinesCursor = daInsertCursor(createdExtensionLines, ["SHAPE@", "roadNameForSplit", "LabelAngle", "County_Number"])
    
    for roadLinesToInsertItem in roadLinesToInsertList:
        createdExtensionLinesCursor.insertRow(roadLinesToInsertItem)
    
    
    # End editing session
    #newEditingSession.stopOperation()
    #newEditingSession.stopEditing(True)
    
    if "createdExtensionLinesCursor" in locals():
        del createdExtensionLinesCursor
    else:
        pass
    
    # Remove the previous countyRoadNameRosette so that it can be recreated.
    if Exists(rosetteTextName):
        Delete_management(rosetteTextName)
    else:
        pass
    
    CreateFeatureclass_management(sqlGdbLocation, rosetteTextName, "POINT", "", "", "", spatialReferenceProjection)
    
    AddField_management(countyRoadNameRosette, "roadNameForSplit", "TEXT", "", "", "55")
    
    AddField_management(countyRoadNameRosette, "LabelAngle", "DOUBLE", "", "", "") # Change to double.
    
    AddField_management(countyRoadNameRosette, "County_Number", "DOUBLE", "", "", "")
    
    AddField_management(countyRoadNameRosette, "COUNTY_NAME", "TEXT", "", "", "55")
    
    
    # Now then, need to check for the existence
    # of and delete the point intersection layer
    # if it exists.
    
    # Then, recreate it and the proper fields.
    
    inMemoryCountyBorderExtension = "aCountyBorderExtensionBuffer"
    inMemoryExtensionLines = "aLoadedExtensionLines"
    
    try:
        Delete_management(inMemoryCountyBorderExtension)
    except:
        pass
    
    try:
        Delete_management(inMemoryExtensionLines)
    except:
        pass
    
    # Temporary layer, use CopyFeatures_management to persist to disk.
    MakeFeatureLayer_management(countyBorderFeature, inMemoryCountyBorderExtension) # County Border extension feature
    
    # Temporary layer, use CopyFeatures_management to persist to disk.
    MakeFeatureLayer_management(createdExtensionLines, inMemoryExtensionLines) # Line extension feature
    
    borderFeatureList = getBorderFeatureList(quarterOrHalf)
    
    borderFeatureList = sorted(borderFeatureList, key=lambda feature: feature[3])
    
    for borderFeature in borderFeatureList:
        borderFeatureName = borderFeature[2]
        borderFeatureNumber = borderFeature[3]
        print "borderFeatureName: " + str(borderFeatureName) + " & borderFeatureNumber: " + str(int(borderFeatureNumber))
        
        countyBorderWhereClause = ' "COUNTY_NUMBER" = ' + str(int(borderFeatureNumber)) + ' '
        
        SelectLayerByAttribute_management(inMemoryCountyBorderExtension, "NEW_SELECTION", countyBorderWhereClause)
        
        countyBorderSelectionCount = GetCount_management(inMemoryCountyBorderExtension)
        
        print "County Borders Selected: " + str(countyBorderSelectionCount)
        
        # Had to single-quote the borderFeatureNumber because it is stored as a string in the table.
        # Unsingle quoted because it was changed to a float.
        extensionLinesWhereClause = ' "COUNTY_NUMBER" = ' + str(int(borderFeatureNumber)) + ' '
        
        SelectLayerByAttribute_management(inMemoryExtensionLines, "NEW_SELECTION", extensionLinesWhereClause)
        
        extensionLineSelectionCount = GetCount_management(inMemoryExtensionLines)
        
        print "Extension Lines Selected: " + str(extensionLineSelectionCount)
        
        if Exists(tempRosetteTextName):
            Delete_management(tempRosetteTextName)
        else:
            pass
        
        if Exists(tempRosetteSPTextName):
            Delete_management(tempRosetteSPTextName)
        else:
            pass
        
        Intersect_analysis([inMemoryCountyBorderExtension, inMemoryExtensionLines], tempRoadNameRosette, "ALL", "", "POINT")
        
        # Intersect to an output temp layer.
        
        # Next, need to loop through all of the counties.
        
        # Get the county number and use it to select
        # a county extension buffer in the county
        # extension buffers layer.
        
        # Then, use the county number to select
        # all of the lines for that county
        # in the extension lines layer.
        
        # Then, export those to a temp layer in the fgdb.
        
        # Change multipoint to singlepoint.
        
        # Was working until I moved from gisprod to sdedev for the data source.
        # not sure why. Check to make sure projections match.
        # ^ Fixed.
        
        try:
            
            # Run the tool to create a new fc with only singlepart features
            MultipartToSinglepart_management(tempRoadNameRosette, tempRoadNameRosetteSP)
            
            # Check if there is a different number of features in the output
            #   than there was in the input
            inCount = int(GetCount_management(tempRoadNameRosette).getOutput(0))
            outCount = int(GetCount_management(tempRoadNameRosetteSP).getOutput(0))
             
            if inCount != outCount:
                print "Found " + str(outCount - inCount) + " multipart features."
                #print "inCount, including multipart = " + str(inCount)
                #print "outCount, singlepart only = " + str(outCount)
                
            else:
                print "No multipart features were found"
        
        except ExecuteError:
            print GetMessages()
        except Exception as e:
            print e
        
        print "Appending the temp point layer to the county point intersection layer."
        
        Append_management([tempRoadNameRosetteSP], countyRoadNameRosette, "NO_TEST")
        
        # K, worked correctly. Just need to change LabelAngle to a float and it might be what
        # I want.
        
        print "Done adding points to the countyRoadNameRosette feature class."
    
    ## Might need to add another field to this feature class for the offset on
    ## labels, then calculate it based off of the SQRT_DIV8 field.
    
    # Might also need to check for and erase points that have a label angle which
    # is more than 20 degrees off from 0, 90, 180, 270, as these are likely to
    # be minor roads.
    # ^ Currently do this.
    
    # Consider reorganizing to be more than one function instead of being a ~300 line long function.


def labelAngleNormalization(quarterOrHalf):
    
    if quarterOrHalf.lower() == "quarter":
        countyBorderFeature = countyBorderFeature_Q
        countyRoadNameRosette = countyRoadNameRosette_Q
    elif quarterOrHalf.lower() == "half":
        countyBorderFeature = countyBorderFeature_H
        countyRoadNameRosette = countyRoadNameRosette_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf error."))
    
    print "Normalizing the label angle values."
    
    if "COUNTY_NAME" not in ListFields(countyRoadNameRosette):
        AddField_management(countyRoadNameRosette, "COUNTY_NAME", "TEXT", "", "", "55")
    else:
        pass
    
    newCursor = daSearchCursor(countyBorderFeature, countyBorderFields)
    
    countyTranslationDictionary = dict()
    
    # countyBorderItem[3] is the number, countyBorderItem[2] is the name.
    # -- Use for translating from county number to county name.
    for countyBorderItem in newCursor:
        if countyBorderItem[3] not in countyTranslationDictionary: 
            countyTranslationDictionary[countyBorderItem[3]] = countyBorderItem[2]
        else:
            pass
    
    if "newCursor" in locals():
        del newCursor
    else:
        pass
    
    
    newCursor = daUpdateCursor(countyRoadNameRosette, countyRoadNameRosetteFields)
    
    for countyPointItem in newCursor:
        countyPointItem = list(countyPointItem)
        
        # Takes the remainder of the angle divided by 360.
        # Uses fmod due to floating point issues with the normal modulo operator in python.
        countyPointItem[0] = math.fmod(countyPointItem[0], 360) 
        
        # countyPointItem[1] is County Name, countyPointItem[2] is County Number.
        if countyPointItem[0] >= 250 and countyPointItem[0] <= 290:
            countyPointItem[0] = 270
            if countyPointItem[2] in countyTranslationDictionary:
                countyPointItem[1] = countyTranslationDictionary[countyPointItem[2]]
            else:
                countyPointItem[1] = ""
            newCursor.updateRow(countyPointItem)
            
        elif countyPointItem[0] >= 160 and countyPointItem[0] <= 200:
            countyPointItem[0] = 180
            if countyPointItem[2] in countyTranslationDictionary:
                countyPointItem[1] = countyTranslationDictionary[countyPointItem[2]]
            else:
                countyPointItem[1] = ""
            newCursor.updateRow(countyPointItem)
            
        elif countyPointItem[0] >= 70 and countyPointItem[0] <= 110:
            countyPointItem[0] = 90
            if countyPointItem[2] in countyTranslationDictionary:
                countyPointItem[1] = countyTranslationDictionary[countyPointItem[2]]
            else:
                countyPointItem[1] = ""
            newCursor.updateRow(countyPointItem)
            
        elif (countyPointItem[0] >= 0 and countyPointItem[0] <= 20) or (countyPointItem[0] >= 340 and countyPointItem[0] <= 360):
            countyPointItem[0] = 0
            if countyPointItem[2] in countyTranslationDictionary:
                countyPointItem[1] = countyTranslationDictionary[countyPointItem[2]]
            else:
                countyPointItem[1] = ""
            newCursor.updateRow(countyPointItem)
            
        else:
            print "Deleting a row for having an angle more than 20 degrees away from a cardinal direction."
            newCursor.deleteRow()
            
         
    if "newCursor" in locals():
        del newCursor
    else:
        pass
    
    
    print "Label angle normalization complete!"
    print "Done extending and intersecting road features." # Need to break this into two pieces and pass some of the inmemorylayers
    # from the first function to the 2nd or similar.
    # the function is just too long to be easily readable/debuggable.


def thresholdRemoval(quarterOrHalf):
    # Change to look at the number of roads that are in the
    # county's erased polygon. -- the erased?
    # Then, if there are not at least that % of the
    # roads labeled as points in the pointIntersection
    # layer, remove ALL points for that county.
    
    # Rewrite this to test for the number of null points.
    
    # 1 through 100, percentage as integer. ## 25 seems to work well. Results in only 12 counties not having enough points.
    thresholdValue = 25 
    # One county (42) doesn't have enough roads information for this script to do anything at all.
    
    if quarterOrHalf.lower() == "quarter":
        countyRoadNameRosette = countyRoadNameRosette_Q
    elif quarterOrHalf.lower() == "half":
        countyRoadNameRosette = countyRoadNameRosette_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf error."))
    
    #makefeaturelayer1
    MakeFeatureLayer_management(countyRoadsFeature, "loadedCountyRoads")
    #makefeaturelayer2
    MakeFeatureLayer_management(countyRoadNameRosette, "loadedRoadNameRosette")
    
    for i in xrange(1, 106):
        roadThresholdWhereClause = """ "COUNTY_NUMBER" = """ + str(i) + """ """
        rosetteThresholdWhereClause = """ "COUNTY_NUMBER" = ' """ + str(i) + """ ' """
        
        #selectfeatures1
        SelectLayerByAttribute_management("loadedCountyRoads", "NEW_SELECTION", roadThresholdWhereClause)
        #selectfeatures2
        SelectLayerByAttribute_management("loadedRoadNameRosette", "NEW_SELECTION", rosetteThresholdWhereClause)
        
        #createfeaturelayer with whereclause, or do this then make a select clause.
        countyRoadsCount = GetCount_management("loadedCountyRoads")
        countyPointsCount = GetCount_management("loadedRoadNameRosette")
        
        countyRoadsCount = int(countyRoadsCount.getOutput(0))
        countyPointsCount = int(countyPointsCount.getOutput(0))
        
        if countyRoadsCount >= 1:
            if (float(countyPointsCount) / float(countyRoadsCount)) >= (float(thresholdValue) / float(100)) and countyPointsCount >= 20:
                print "Threshold value OK for County Number: " + str(i) + "."
                pass
            else:
                print "Threshold value not met for County Number: " + str(i) + "."
                if countyPointsCount >= 1:
                    print "Removing road name rosette points from this county."
                    DeleteRows_management("loadedRoadNameRosette")
                else:
                    print "Would have deleted the points for this county, but none exist to delete."
        else:
            print "No County Roads found for County Number: " + str(i) + "."


def duplicateNameRemoval(quarterOrHalf):
    
    if quarterOrHalf.lower() == "quarter":
        countyRoadNameRosette = countyRoadNameRosette_Q
    elif quarterOrHalf.lower() == "half":
        countyRoadNameRosette = countyRoadNameRosette_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf error."))
    
    print "Starting duplicate name removal."
    
    countyRoadNameRosetteFields = ListFields(countyRoadNameRosette)
    
    print "countyRoadNameRosetteFields: "
    
    for fieldItem in countyRoadNameRosetteFields:
        print str(fieldItem.name)
    
    newCursor = daSearchCursor(countyRoadNameRosette, countyRoadNameRosetteFieldsObjShape)
    
    # Debug only
    #print "Created a new cursor..."
    
    countyNamePointList = list()
    
    for eachPoint in newCursor:
        countyNamePointList.append(eachPoint)
    
    try:
        del newCursor
    except:
        pass
    
    # Debug only
    #print "Completed using the new cursor."
    
    pointDeleteList = list()
    
    for pointItem in countyNamePointList:
        for pointToCheck in countyNamePointList:
            # If the points share a road name, and a county number, but not the same ObjectID...
            if pointItem[0] not in pointDeleteList:
                if pointItem[3] == pointToCheck[3] and str(pointItem[2]).upper() == str(pointToCheck[2]).upper() and (not pointItem[0] == pointToCheck[0]):
                    # Use the distance formula to check to see if these points are within a
                    # certain distance from one another.
                    # If so, add the pointToCheck to the pointDeleteList.
                    distance = 0
                    point1 = pointItem[1]
                    point2 = pointToCheck[1]
                    
                    
                    distance = calcPointDistance(point1, point2)
                    
                    
                    # Change this to add just the objectid to the pointDeleteList
                    # instead of the whole point row to increase the speed
                    # of the check when the list grows to a decent size.
                    # Distance of 10000 seems to give good results.
                    if distance >= 0 and distance < 10000 and pointToCheck[0] not in pointDeleteList:
                        pointDeleteList.append(pointToCheck[0])
                    else:
                        pass
                else:
                    pass
            else:
                pass
    
    newCursor = daUpdateCursor(countyRoadNameRosette, countyRoadNameRosetteFieldsObjShape)
    
    for updateableRow in newCursor:
        for pointToDeleteOID in pointDeleteList:
            if updateableRow[0] == pointToDeleteOID:
                print "Selected a point for " + str(updateableRow[2]) + " in " + str(updateableRow[4]) + " county to delete."
                newCursor.deleteRow()
                print "Point deleted."
            else:
                pass
        #updateCursor
        #delete pointToDelete from countyRoadNameRosette.
        #print a message saying that the point was deleted.
    
    try:
        del newCursor
    except:
        pass


if __name__ == "__main__":
    startingTime = datetime.datetime.now()

    ######################### From MapPreprocessing
    #
    route_endings_generation()
    env.workspace = inMemGDB
    env.overwriteOutput = True
    env.outputZFlag = "Disabled"
    ImportAllSheets(excelSettingsLocation)
    nonStateAndCountyImport()
    countyAndRoadPreprocessing()
    countyBuffersAndNon_StateErase()
    countyOnlyBridgeExport()
    createCountyLinesForEachCounty()

    ######################### End of MapPreprocessing
    #
    
    
    removeSmallRoads()
    
    scaleValue = "quarter"
    
    extendAndIntersectRoadFeatures(scaleValue)
    labelAngleNormalization(scaleValue)
    thresholdRemoval(scaleValue)
    duplicateNameRemoval(scaleValue)
    
    scaleValue = "half"
    extendAndIntersectRoadFeatures(scaleValue)
    labelAngleNormalization(scaleValue)
    thresholdRemoval(scaleValue)
    duplicateNameRemoval(scaleValue)
    
    endingTime = datetime.datetime.now()
    
    scriptDuration = FindDuration(endingTime, startingTime)
    
    print "\n" # Newline for better readability.
    print "For the main/complete script portion..."
    print "Starting Time: " + str(startingTime)
    print "Ending Time: " + str(endingTime)
    print "Elapsed Time: " + scriptDuration
    # Tested good on 2015-08-20
    
else:
    pass

## Next script: CountyMapDataDrivenPagesToPDF.py