#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CountyMapRoadNameBorderCreation.py

# Takes the data from the excel file and puts it into
# an ESRI geodatabase for easier use in other scripts.

# Use a searchcursor to read in the rows there
# and apply them to other data.

# 2016-03-17 Update -- Added logic to improve
# the process of choosing which points to keep.
# Also included a fix for certain features
# not getting extended correctly.
# Improved formatting for functions
# after the End of MapPreprocessing.


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

excelSettingsLocation = r'\\dt00mh02\Planning\Cart\Maps\County\CountyMapDataDrivenSettings.xlsx'

from county_map_config import sdeProdLocation, sqlGdbLocation

# Modify this so that it gets the correct sqlGdbLocation from
# the county_map_config file using the socket module.
# Override sqlGdbLocation for testing
##sqlGdbLocation = r'C:\KDOT_Python\DB_Connections\geo@countyMaps.sde'

sdeProdUser  = 'SHARED.'
sharedNonStateSystem = os.path.join(sdeProdLocation, sdeProdUser + 'Non_State_System')
sharedCounties = os.path.join(sdeProdLocation, sdeProdUser + 'COUNTIES')
sharedNonStateBridges = os.path.join(sdeProdLocation, sdeProdUser + 'NON_STATE_BRIDGES')
sharedStateBridges = os.path.join(sdeProdLocation, sdeProdUser + 'GIS_BRIDGE_DETAILS_LOC')
sharedCityLimits = os.path.join(sdeProdLocation, sdeProdUser + 'CITY_LIMITS')
sharedCountyLines = os.path.join(sdeProdLocation, sdeProdUser + 'COUNTY_LINES')

#Override sqlGdbUser for testing
##sqlGdbUser = 'countyMaps.GEO.'
sqlGdbUser = 'mapAutomation.GEO.'
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
nSSForPointCreationSP = os.path.join(inMemGDB, 'Non_State_System_For_Point_Creation_SP')
countyLinesDissolved = os.path.join(inMemGDB, 'CountyLinesDissolved')
countiesBuffered = os.path.join(inMemGDB, 'CountiesBuffered')

bufferDistance_Short = 1200
shortExtensionDistance = 7500

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
    
    # Doing a Dissolve followed by an Erase can lead to multipart features.
    # Multipart features can cause problems in the road line extension function.
    # Fixed by making all the road lines single part after the Dissolve & Erase functions.
    try:
        # Run the tool to create a new fc with only singlepart features
        MultipartToSinglepart_management(featureClass4Out, nSSForPointCreationSP)
    
    except ExecuteError:
        print GetMessages()
    except Exception as e:
        print e
    
    # Take the single-part features and replace the previous features with them.
    Delete_management(featureClass4Out)
    CopyFeatures_management(nSSForPointCreationSP, featureClass4Out)
    
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
from math import fabs, radians, sin, cos, floor, sqrt, pow  # @UnusedImport
import datetime

env.workspace = inMemGDB
env.overwriteOutput = True
env.outputZFlag = "Disabled"


# Actually persist these feature class
#countyRoadsFeature = os.path.join(sqlGdbLocation, sqlGdbUser + 'Non_State_System_For_Point_Creation')
countyRoadNameRosette_Q = os.path.join(sqlGdbLocation, sqlGdbUser + "countyRoadNameRosette_Q") # quarter
countyRoadNameRosette_H = os.path.join(sqlGdbLocation, sqlGdbUser + "countyRoadNameRosette_H") # half -- Still need to build the logic to create this.

# These go to in_memory, no persistence. Most of these are dependent upon scaling.
shortCountiesBuffer = os.path.join(inMemGDB, 'shortCountiesBuffer')
shortExtensionLines = os.path.join(inMemGDB, "shortExtensionLines")
shortTempRosettePoints = os.path.join(inMemGDB, "shortTempRosettePoints")
shortTempRosettePointsSP = os.path.join(inMemGDB, "shortTempRosettePointsSP")
countyBorderFeature_Q = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_Q')
countyBorderFeature_H = os.path.join(inMemGDB, 'Counties_No_Z_Extension_Buffer_H')
countyRoadsFeature = os.path.join(inMemGDB, 'Non_State_System_For_Point_Creation')
createdExtensionLines_Q = os.path.join(inMemGDB, "createdExtensionLines_Q")
createdExtensionLines_H = os.path.join(inMemGDB, "createdExtensionLines_H")
tempRoadNameRosette_Q = os.path.join(inMemGDB, "tempRoadNameRosette_Q")
tempRoadNameRosette_H = os.path.join(inMemGDB, "tempRoadNameRosette_H")
tempRoadNameRosetteSinglePoint_Q = os.path.join(inMemGDB, "tempRoadNameRosetteSinglePoint_Q")
tempRoadNameRosetteSinglePoint_H = os.path.join(inMemGDB, "tempRoadNameRosetteSinglePoint_H")

shortExtensionLinesText = 'shortExtensionLines'
shortTempRosettePointsText = 'shortTempRosettePoints'

# Successfully changed to just one ID column on 8/21/2015
roadCursorFields = ["OID@", "SHAPE@", "RD_NAMES", "COUNTY_NUMBER"] 
countyBorderFields = ["OBJECTID", "SHAPE@XY", "COUNTY_NAME", "COUNTY_NUMBER"]
countyRoadNameRosetteFields = ["LabelAngle", "COUNTY_NAME", "COUNTY_NUMBER"]
countyRoadNameRosetteFieldsObjShape = ["OID@", "SHAPE@XY", "roadNameForSplit", "COUNTY_NUMBER", "COUNTY_NAME", "LabelAngle"]
countyRoadNameRosetteFieldsNoOID = ["SHAPE@XY", "roadNameForSplit", "COUNTY_NUMBER", "COUNTY_NAME", "LabelAngle"]

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
    # Need a new function here. -- Instead of calling this twice, have a main-style function
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
    # 750 to a list, then build SQL queries dynamically to select
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
    
    for smallRoadRow in smallRoadsSearchCursor:
        if smallRoadRow[1] <= 750:
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
    
    # Debug info
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


# Reorganized to call several smaller functions instead of having
# all of the logic in one large function that was more difficult to follow.
def extendAndIntersectRoadFeatures(quarterOrHalf):
    # Reorganize variables
    
    if quarterOrHalf.lower() == "quarter":
        createdExtensionLines = createdExtensionLines_Q
        extensionLinesTextName = "createdExtensionLines_Q"
        # 9000 ft increase for _Q version.
        # Must be larger than the county bufferDistance (20000)
        # Boosted extension distance for non-square counties
        extensionDistance = 61176
        countyRoadNameRosette = countyRoadNameRosette_Q
        rosetteTextName = "countyRoadNameRosette_Q"
        tempRoadNameRosette = tempRoadNameRosette_Q
        #tempRosetteTextName = "tempRoadNameRosette_Q"
        tempRoadNameRosetteSP = tempRoadNameRosetteSinglePoint_Q
        #tempRosetteSPTextName = "tempRoadNameRosetteSinglePoint_Q"
        countyBorderFeature = countyBorderFeature_Q
    elif quarterOrHalf.lower() == "half":
        createdExtensionLines = createdExtensionLines_H
        extensionLinesTextName = "createdExtensionLines_H"
        # Must be larger than the county bufferDistance (11000)
        # Boosted extension distance for non-square counties
        extensionDistance = 52176
        countyRoadNameRosette = countyRoadNameRosette_H
        rosetteTextName = "countyRoadNameRosette_H"
        tempRoadNameRosette = tempRoadNameRosette_H
        #tempRosetteTextName = "tempRoadNameRosette_H"
        tempRoadNameRosetteSP = tempRoadNameRosetteSinglePoint_H
        #tempRosetteSPTextName = "tempRoadNameRosetteSinglePoint_H"
        countyBorderFeature = countyBorderFeature_H
    else:
        print "quarterOrHalf variable not correctly defined."
        raise(Exception("quarterOrHalf value error."))
    
    print "Starting to extend and intersect road features."
    
    
    # Create the extension lines layer
    initializeExtensionLines(shortExtensionLines, shortExtensionLinesText)
    
    roadLinesList = getRoadLinesList()
    
    # Roadlines extension and angle calculation function
    extendLinesFromLines(roadLinesList, shortExtensionLines, shortExtensionDistance)
    
    # Create blank county rosette layers.
    initializeRosettePoints(inMemGDB, shortTempRosettePoints, shortTempRosettePointsText)
    initializeRosettePoints(sqlGdbLocation, countyRoadNameRosette, rosetteTextName)
    
    layerShortCountiesBufferExtension = r"layerShortCountiesBufferExtension"
    layerShortExtensionLines = r"layerShortExtensionLines"
    
    
    try:
        Delete_management(layerShortCountiesBufferExtension)
    except:
        pass
    
    try:
        Delete_management(layerShortExtensionLines)
    except:
        pass
    
    
    shortCountyBuffer(countiesNoZ, shortCountiesBuffer, bufferDistance_Short)
    
    # Temporary layers, use CopyFeatures_management to persist to disk.
    MakeFeatureLayer_management(shortCountiesBuffer, layerShortCountiesBufferExtension)
    MakeFeatureLayer_management(shortExtensionLines, layerShortExtensionLines)
   
    borderFeatureList = getBorderFeatureList(quarterOrHalf)
    
    borderFeatureList = sorted(borderFeatureList, key=lambda feature: feature[3])
    
    pointsToOutput = list()
    
    
    for borderFeature in borderFeatureList:
        borderFeatureName = borderFeature[2]
        borderFeatureNumber = borderFeature[3]
        print "borderFeatureName: " + str(borderFeatureName) + " & borderFeatureNumber: " + str(int(borderFeatureNumber))
        
        countyBorderWhereClause = ' "COUNTY_NUMBER" = ' + str(int(borderFeatureNumber)) + ' '
        
        SelectLayerByAttribute_management(layerShortCountiesBufferExtension, "NEW_SELECTION", countyBorderWhereClause)
        
        countyBorderSelectionCount = GetCount_management(layerShortCountiesBufferExtension)
        
        print "County Borders Selected: " + str(countyBorderSelectionCount)
        
        # Had to single-quote the borderFeatureNumber because it is stored as a string in the table.
        # Unquoted because it was changed to a float.
        extensionLinesWhereClause = """ "COUNTY_NUMBER" = """ + str(int(borderFeatureNumber)) + """ """
        
        SelectLayerByAttribute_management(layerShortExtensionLines, "NEW_SELECTION", extensionLinesWhereClause)
        
        extensionLineSelectionCount = GetCount_management(layerShortExtensionLines)
        
        print "Extension Lines Selected: " + str(extensionLineSelectionCount)
        
        if Exists(shortTempRosettePoints):
            Delete_management(shortTempRosettePoints)
        else:
            pass
        
        if Exists(shortTempRosettePointsSP):
            Delete_management(shortTempRosettePointsSP)
        else:
            pass
        
        Intersect_analysis([layerShortCountiesBufferExtension, layerShortExtensionLines], shortTempRosettePoints, "ALL", "", "POINT")
        
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
        
        try:
            
            # Run the tool to create a new fc with only singlepart features
            MultipartToSinglepart_management(shortTempRosettePoints, shortTempRosettePointsSP)
            
            # Check if there is a different number of features in the output
            #   than there was in the input
            inCount = int(GetCount_management(shortTempRosettePoints).getOutput(0))
            outCount = int(GetCount_management(shortTempRosettePointsSP).getOutput(0))
             
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
        
        # Call the function to select points from a 
        
        ## Actually won't do this, there will be another couple of steps
        ## to deal with moving the points prior to writing it out.
        ###print "Appending the temp point layer to the county point intersection layer."
        
        ### Debug Block Start ###
        '''
        Append_management([shortTempRosettePointsSP], countyRoadNameRosette_Test_Fork, "NO_TEST")
        '''
        ### Debug Block End ###
        
        ###print "Done adding points to the countyRoadNameRosette feature class."
        
        ## Might need to add another field to this feature class for the offset on
        ## labels, then calculate it based off of the SQRT_DIV8 field.
        
        # Might also need to check for and erase points that have a label angle which
        # is more than 20 degrees off from 0, 90, 180, 270, as these are likely to
        # be minor roads.
        # ^ Currently doing this.
        
        # Consider reorganizing to be more than one function instead of being a ~300 line long function.
        
        # Build a drop-in replacement that calls several smaller functions instead of trying to
        # modify the entire function in place.
        
        # Expects a single part point input layer.
        returnedPoints = duplicateNameAndLabelAngleFixes(shortTempRosettePointsSP)
        
        # Spammy debug info.
        #print "pointsToOutput: " + str(pointsToOutput)
        #print "returnedPoints: " + str(returnedPoints)
        
        pointsToOutput = pointsToOutput + returnedPoints
        ## ||||||||
        ## VVVVVVVV
        # This function will need changes.
        # 1. Make it intersect the county's actual border,
        # or a very slightly buffered version of the border first.
        ### to create a set of points on the county's border.
        # -- From here on should be in separate function.
        # 2. Find the points that share a name and are within
        ### a measured distance of one another.
        # 2a. Of the points which share names and are within
        ### a measured distance of one another, find the one
        ### that has the closest angle to a cardinal direction.
        # 2b. Delete the points which are not the closest
        ### to a cardinal direction.
        ###
        # Add the first points to a gdb or a map so that they can be viewed and
        # checked for accuracy.
        
        #### Need a hybridized workflow between the previous
        #### labelAngleNormalization function and the
        #### duplicateNameRemoval function.
        
        #### Break the functionality into smaller
        #### steps, then recombine them in an order
        #### that makes more sense.
    
    
    ### * Preferred solution -- 
    ### : For each point iterated over,
    ### : Build a list/selection all of the points with the same name.
    ###################################################################
    ### : For each of the selected points within a given distance of
    ### : the point that is being iterated over,
    ###################################################################
    ### : Search the already created sets for the point iterated over.
    ### : If there is not already a set with that point in it,
    ### : add both points to a new set.
    ### : If there is already a set with the iterated over point,
    ### : add both points to that set and stop searching the sets.
    ###################################################################
    ### : Within each set, keep the one that is the closest
    ### : to a cardinal angle and dismiss all the others.
    ###################################################################
    ### : Should end up with sets that contain a single point.
    ### : Add this single point to a list of OIDs to transfer
    ### : From the shortTempCountyRoadNameRosette to an
    ### : intermediateCountyRoadNameRosette.
    
    ### Visual test output prior to moving to the next portion.
    
    '''
    pointsToOutputNoOID = [outPoint[1:] for outPoint in pointsToOutput]
    countyRoadNameRosette_Test_Fork_Text = "countyRoadNameRosette_Test_Fork"
    countyRoadNameRosette_Test_Fork = os.path.join(sqlGdbLocation, sqlGdbUser + countyRoadNameRosette_Test_Fork_Text)
    
    initializeRosettePoints(sqlGdbLocation, countyRoadNameRosette_Test_Fork, countyRoadNameRosette_Test_Fork_Text)
    
    countyRosettePreExtPointsText = "countyRosettePreExtPoints"
    countyRosettePreExtPoints = os.path.join(inMemGDB, countyRosettePreExtPointsText)
    
    initializeRosettePoints(inMemGDB, countyRosettePreExtPoints, countyRosettePreExtPointsText)
    
    newCursor = daInsertCursor(countyRosettePreExtPoints, countyRoadNameRosetteFieldsNoOID)
    
    for pointToWrite in pointsToOutputNoOID:
        newCursor.insertRow(pointToWrite)
    
    try:
        del newCursor
    except ExecuteError:
        print GetMessages()
    except Exception as e:
        print e
    '''
    
    initializeExtensionLines(createdExtensionLines, extensionLinesTextName)
    
    createdExtensionLines = extendLinesFromPoints(pointsToOutput, createdExtensionLines, extensionDistance)
    
    layerCountyBorderExtension = "aCountyBorderExtensionBuffer"
    layerExtensionLines = "aLoadedExtensionLines"
    
    try:
        Delete_management(layerCountyBorderExtension)
    except:
        pass
    
    try:
        Delete_management(layerExtensionLines)
    except:
        pass
    
    # Temporary layer, use CopyFeatures_management to persist to disk.
    MakeFeatureLayer_management(countyBorderFeature, layerCountyBorderExtension)
    MakeFeatureLayer_management(createdExtensionLines, layerExtensionLines)
    
    borderFeatureList = getBorderFeatureList(quarterOrHalf)
    
    borderFeatureList = sorted(borderFeatureList, key=lambda feature: feature[3])
    
    ## Can probably define a new function for this loop and it's logic.
    ## Test without that first though to see if it works correctly before
    ## the change.
    
    for borderFeature in borderFeatureList:
        borderFeatureName = borderFeature[2]
        borderFeatureNumber = borderFeature[3]
        print "borderFeatureName: " + str(borderFeatureName) + " & borderFeatureNumber: " + str(int(borderFeatureNumber))
        
        countyBorderWhereClause = ' "COUNTY_NUMBER" = ' + str(int(borderFeatureNumber)) + ' '
        
        SelectLayerByAttribute_management(layerCountyBorderExtension, "NEW_SELECTION", countyBorderWhereClause)
        
        countyBorderSelectionCount = GetCount_management(layerCountyBorderExtension)
        
        print "County Borders Selected: " + str(countyBorderSelectionCount)
        
        # Had to single-quote the borderFeatureNumber because it is stored as a string in the table.
        # Unquoted because it was changed to a float.
        extensionLinesWhereClause = """ "COUNTY_NUMBER" = """ + str(int(borderFeatureNumber)) + """ """
        
        SelectLayerByAttribute_management(layerExtensionLines, "NEW_SELECTION", extensionLinesWhereClause)
        
        extensionLineSelectionCount = GetCount_management(layerExtensionLines)
        
        print "Extension Lines Selected: " + str(extensionLineSelectionCount)
        
        if Exists(tempRoadNameRosette):
            Delete_management(tempRoadNameRosette)
        else:
            pass
        
        if Exists(tempRoadNameRosetteSP):
            Delete_management(tempRoadNameRosetteSP)
        else:
            pass
        
        Intersect_analysis([layerCountyBorderExtension, layerExtensionLines], tempRoadNameRosette, "ALL", "", "POINT")
        
        # Intersect to an output temp layer.
        
        # Next, need to loop through all of the counties.
        
        # Get the county number and use it to select
        # a county extension buffer in the county
        # extension buffers layer.
        
        # Then, use the county number to select
        # all of the lines for that county
        # in the extension lines layer.
        
        # Then, export those to a temp layer in the fgdb.
        
        # Convert multipart to singlepart point features.
        
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
        
        print "Done adding points to the countyRoadNameRosette feature class."
    
    # Alternatively, you could insert to an in_memory feature class
    # then CopyFeatures_management from there to disk.
    #CopyFeatures_management(pointsToOutput, countyRoadNameRosette_Test_Fork)
    
    ## Then, add these points to an in_memory layer
    ## Next, create new extension lines for them.
    ## Afterwards, intersect those lines with the 
    ## full county boundary to move the points
    ## from the short boundary location out to
    ## the full boundary location -- Will need
    ## to do this part for both the Half-Inch
    ## and Quarter-Inch versions, but it might
    ## be possible to do both at once...
    ## Check on that as it could speed things
    ## up significantly, though this might need
    ## to have some of it's Q vs. H processes
    ## run earlier in the process if that is
    ## the case.
    
    ###################################################################
    ### : From the intermediateCountyRoadNameRosette, correct the angles
    ### : on each of the remaining points so that they are in the
    ### : label cardinal direction.
    ###################################################################
    ### : Then create extension lines from each point.
    ### : Intersect the extension lines with the Q and H county border
    ### : buffers to "move" the points to new positions on those buffers
    ### : instead of having them on the short county border buffer.
    ################################################################### 
    ### : Then convert multipart to singlepart and run the name and
    ### : distance test again to make sure that there are no new
    ### : duplicates that have been formed.
    ###################################################################
    ### : Add the points that pass the test to the output rosette
    ### : layers that are persisted to disk and make sure that they
    ### : look right in the map!
    ###################################################################
    ### * Pretty long bit of pseudocode, but I'm not sure there's a
    ### * shorter path that would still make it work accurately.


def duplicateNameAndLabelAngleFixes(shortTempRosette): # Rename later.
    
    print "Starting hybrid duplicate name and label angle fixes."
    
    newCursor = daSearchCursor(shortTempRosette, countyRoadNameRosetteFieldsObjShape)
    
    countyNamePointList = list()
    
    for eachPoint in newCursor:
        countyNamePointList.append(eachPoint)
    
    try:
        del newCursor
    except:
        pass
    
    
    # Create a grouping from all of the points which share a name
    # within a particular distance.
    
    # From that grouping, see which one has an angle closest
    # to a cardinal direction (0, 90, 180, 270).
    
    pointKeepList = list()
    
    ##pointDeleteList = list()
    
    pointCheckedList = list()
    
    pointsToCompareContainer = list()
    
    
    for pointItem in countyNamePointList:
        pointsToCompare = list()
        # Part 1 that prevents putting all the points in the list.
        #############Debug#####################################
        if pointItem[3] == 57: # Marion county issue resolution.
            print 'PointItem OID to consider for adding to comparison lists.' + str(pointItem[0])
        else:
            pass
        if pointItem[0] not in pointCheckedList: 
            for pointToCheck in countyNamePointList:
                # If the points share a road name, but not the same ObjectID...
                # County number check is unnecessary since this called from the border features
                # loop which processes by county.
                if  (str(pointItem[2]).lower() == str(pointToCheck[2]).lower()) and (not pointItem[0] == pointToCheck[0]): # and pointItem[3] == pointToCheck[3]
                    if pointToCheck[3] == 57: # Marion county issue resolution.
                        print 'pointToCheck OID to consider for adding to comparison lists.' + str(pointToCheck[0])
                        print 'pointToCheck Road Name: ' + str(pointToCheck[2])
                    else:
                        pass
                    
                    # Use the distance formula to check to see if these points are within a
                    # certain distance from one another.
                    # If so, add the pointToCheck to the pointDeleteList.
                    distance = 0
                    point1 = pointItem[1]
                    point2 = pointToCheck[1]
                    
                    distance = calcPointDistance(point1, point2)
                    
                    # Part 2 that prevents putting all the points in the list.
                    if distance >= 0 and distance < 10500 and pointToCheck[0] not in pointCheckedList:
                        #print "Appending point with OID: " + str(pointToCheck[0])
                        pointCheckedList.append(pointToCheck[0])
                        pointsToCompare.append(pointToCheck)
                    else:
                        pass
                else:
                    pass
            
            pointCheckedList.append(pointItem[0])
            pointsToCompare.append(pointItem)
            
        else:
            pass
        
        if (len(pointsToCompare) > 0):
            pointsToCompareContainer.append(pointsToCompare)
        else:
            pass
    
    
    # For each list of points that share a name and are within a particular geographic distance
    highestKeptOID = 0
    
    for pointsList in pointsToCompareContainer:
        # Sort by each point's label angle difference from a cardinal direction angle.
        # Select the point that has the smallest difference.
        sortablePoints = list()
        
        for pointItem in pointsList:
            pointAngle = pointItem[5]
            pointFromCardinal = getDifferenceFromCardinal(pointAngle)
            pointItem = list(pointItem)
            pointItem.append(pointFromCardinal)
            sortablePoints.append(pointItem)
        
        sortedPoints = sorted(sortablePoints, key = lambda listedPoint: listedPoint[6])
        
        if len(sortedPoints) > 0:
            pointToKeep = sortedPoints[0]
            pointToKeepOID = pointToKeep[0]
            pointKeepList.append(pointToKeepOID)
            highestKeptOID = pointToKeep[0]
        else:
            pass
    
    print "Highest kept OID: " + str(highestKeptOID)
    
    ## List comprehension instead of updatecursor/searchcursor.
    ## Normalize label angles here.
    keptPointsList = [normalizeAngle(pointItem) for pointItem in countyNamePointList if pointItem[0] in pointKeepList]
    
    return keptPointsList


def getDifferenceFromCardinal(passedAngle):    
    differencesList = list()
    
    zeroTest = fabs(passedAngle - 0)
    ninetyTest = fabs(passedAngle - 90)
    oneEightyTest = fabs(passedAngle - 180)
    twoSeventyTest = fabs(passedAngle - 270)
    threeSixtyTest = fabs(passedAngle - 360)
    
    differencesList.append(zeroTest)
    differencesList.append(ninetyTest)
    differencesList.append(oneEightyTest)
    differencesList.append(twoSeventyTest)
    differencesList.append(threeSixtyTest)
    
    differencesList = sorted(differencesList)
    
    absAngleDistance = differencesList[0]
    
    return absAngleDistance


def getClosestCardinal(passedAngle):
    cardinalsList = list()
    
    zeroTest = [fabs(passedAngle - 0), 0]
    ninetyTest = [fabs(passedAngle - 90), 90]
    oneEightyTest = [fabs(passedAngle - 180), 180]
    twoSeventyTest = [fabs(passedAngle - 270), 270]
    threeSixtyTest = [fabs(passedAngle - 360), 0]
    
    cardinalsList.append(zeroTest)
    cardinalsList.append(ninetyTest)
    cardinalsList.append(oneEightyTest)
    cardinalsList.append(twoSeventyTest)
    cardinalsList.append(threeSixtyTest)
    
    cardinalsList = sorted(cardinalsList)
    
    closestCardinal = cardinalsList[0][1]
    
    return closestCardinal


def normalizeAngle(inputPoint):
    inputAngle = inputPoint[5]
    normalizedAngle = getClosestCardinal(inputAngle)
    if normalizedAngle == 270:
        normalizedAngle = 90
    else:
        pass
    normalizedPoint = list(inputPoint)
    normalizedPoint[5] = normalizedAngle
    
    return normalizedPoint


def shortCountyBuffer(buffInput, buffOutput, buffDist):
    print "Now adding the short county polygon buffer..."
    
    Buffer_analysis(buffInput, buffOutput, buffDist, "FULL", "", "NONE")
    
    print "Done adding the short county polygon buffers!"


def initializeExtensionLines(extLines, extLinesText):
    if Exists(extLines):
        Delete_management(extLines)
    else:
        pass
    
    CreateFeatureclass_management(inMemGDB, extLinesText, "POLYLINE", "", "", "", spatialReferenceProjection)
    
    # Add a column for roadname called roadNameForSplit.
    AddField_management(extLines, "roadNameForSplit", "TEXT", "", "", "55")
    
    # Add a column which stores the angle to display a label called called LabelAngle.
    AddField_management(extLines, "LabelAngle", "DOUBLE", "", "", "") # Change to double.
    
    # Add a column which stores the County Number.
    AddField_management(extLines, "County_Number", "DOUBLE", "", "", "")


def extendLinesFromLines(linesSource, outputExtLines, lineExtensionDistance): # Give this a better name.
    roadLinesToInsertList = list()
    
    for roadLinesItem in linesSource:
        
        roadLineGeometry = roadLinesItem[1]

        roadNameToUse = roadLinesItem[2]
        countyNumber = roadLinesItem[3]
        
        newGeomAndAngle = extendLine(roadLineGeometry, lineExtensionDistance)
        
        newLineFeature = newGeomAndAngle[0]
        
        lineDirectionOutput = newGeomAndAngle[1]
        
        roadLinesToInsertList.append([newLineFeature, roadNameToUse, lineDirectionOutput, countyNumber])
        
        if "newLineFeature" in locals():
            del newLineFeature
        else:
            pass
    
    
    extensionLinesCursor = daInsertCursor(outputExtLines, ["SHAPE@", "roadNameForSplit", "LabelAngle", "County_Number"])
    
    for roadLinesToInsertItem in roadLinesToInsertList:
        extensionLinesCursor.insertRow(roadLinesToInsertItem)
    
    if "extensionLinesCursor" in locals():
        del extensionLinesCursor
    else:
        pass


def extendLine(lineGeometry, extDistance):
    # Take a polyline geometry, then extend it
    # by the passed distance and return it. 
    
    firstPointTuple = (lineGeometry.firstPoint.X, lineGeometry.firstPoint.Y)
    lastPointTuple = (lineGeometry.lastPoint.X, lineGeometry.lastPoint.Y)
    
    
    yValue_1 = -(lastPointTuple[1] - firstPointTuple[1]) # made y value negative
    xValue_1 = lastPointTuple[0] - firstPointTuple[0]
    
    lineDirectionAngle_1 = math.degrees(math.atan2(xValue_1, yValue_1)) # reversed x and y
    
    lineDirectionAngle_1 = -(((lineDirectionAngle_1 + 180) % 360) - 180) # correction for certain quadrants
    
    origin_x_1 = firstPointTuple[0]
    origin_y_1 = firstPointTuple[1]
    
    
    yValue_2 = -(firstPointTuple[1] - lastPointTuple[1]) # made y value negative
    xValue_2 = firstPointTuple[0] - lastPointTuple[0]
    
    lineDirectionAngle_2 = math.degrees(math.atan2(xValue_2, yValue_2)) # reversed x and y
    
    lineDirectionAngle_2 = -(((lineDirectionAngle_2 + 180) % 360) - 180) # correction for certain quadrants
    
    origin_x_2 = lastPointTuple[0]
    origin_y_2 = lastPointTuple[1]
    
    
    (disp_x_1, disp_y_1) = (extDistance * math.sin(math.radians(lineDirectionAngle_1)),
                      extDistance * math.cos(math.radians(lineDirectionAngle_1)))
    
    (end_x_1, end_y_1) = (origin_x_1 + disp_x_1, origin_y_1 + disp_y_1)
    
    (disp_x_2, disp_y_2) = (extDistance * math.sin(math.radians(lineDirectionAngle_2)),
                      extDistance * math.cos(math.radians(lineDirectionAngle_2)))
    
    (end_x_2, end_y_2) = (origin_x_2 + disp_x_2, origin_y_2 + disp_y_2)
    
    
    startPoint = ArcgisPoint()
    endPoint = ArcgisPoint()
    
    startPoint.ID = 0
    startPoint.X = end_x_1
    startPoint.Y = end_y_1
    
    endPoint.ID = 1
    endPoint.X = end_x_2
    endPoint.Y = end_y_2
    
    linePointsArray = ArcgisArray()
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
    
    returnGeomAndAngle = [newLineFeature, lineDirectionOutput]
    
    return returnGeomAndAngle


def extendLinesFromPoints(pointsSource, outputExtLines, pointExtensionDistance):
    roadLinesToInsertList = list()
    
    for roadPointsItem in pointsSource:
        roadPointGeometry = roadPointsItem[1]
        
        roadNameToUse = roadPointsItem[2]
        countyNumber = roadPointsItem[3]
        lineDirectionInput = roadPointsItem[5]
        
        newGeomAndAngle = extendPoint(roadPointGeometry, lineDirectionInput, pointExtensionDistance)
        
        newLineFeature = newGeomAndAngle[0]
        
        lineDirectionOutput = newGeomAndAngle[1]
        
        roadLinesToInsertList.append([newLineFeature, roadNameToUse, lineDirectionOutput, countyNumber])
        
        if "newLineFeature" in locals():
            del newLineFeature
        else:
            pass
    
    
    extensionLinesCursor = daInsertCursor(outputExtLines, ["SHAPE@", "roadNameForSplit", "LabelAngle", "County_Number"])
    
    for roadLinesToInsertItem in roadLinesToInsertList:
        extensionLinesCursor.insertRow(roadLinesToInsertItem)
    
    if "extensionLinesCursor" in locals():
        del extensionLinesCursor
    else:
        pass


def extendPoint(pointGeometry, pointAngle, extDistance):
    # Take a point geometry, then extend it along the point angle
    # by the passed distance and return it. 
    
    origin_x = pointGeometry[0]
    origin_y = pointGeometry[1]
    
    lineDirectionAngle_1 = pointAngle
    lineDirectionAngle_2 = (pointAngle + 180) % 360
    
    
    (disp_x_1, disp_y_1) = (extDistance * math.sin(math.radians(lineDirectionAngle_1)),
                      extDistance * math.cos(math.radians(lineDirectionAngle_1)))
    
    (end_x_1, end_y_1) = (origin_x + disp_x_1, origin_y + disp_y_1)
    
    (disp_x_2, disp_y_2) = (extDistance * math.sin(math.radians(lineDirectionAngle_2)),
                      extDistance * math.cos(math.radians(lineDirectionAngle_2)))
    
    (end_x_2, end_y_2) = (origin_x + disp_x_2, origin_y + disp_y_2)
    
    
    startPoint = ArcgisPoint()
    endPoint = ArcgisPoint()
    
    startPoint.ID = 0
    startPoint.X = end_x_1
    startPoint.Y = end_y_1
    
    endPoint.ID = 1
    endPoint.X = end_x_2
    endPoint.Y = end_y_2
    
    linePointsArray = ArcgisArray()
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
    
    returnGeomAndAngle = [newLineFeature, lineDirectionOutput]
    
    return returnGeomAndAngle


def initializeRosettePoints(gdbToUse, countyRosette, countyRosetteText):
    if Exists(countyRosette):
        Delete_management(countyRosette)
    else:
        pass
    
    CreateFeatureclass_management(gdbToUse, countyRosetteText, "POINT", "", "", "", spatialReferenceProjection)
    
    AddField_management(countyRosette, "roadNameForSplit", "TEXT", "", "", "55")
    
    AddField_management(countyRosette, "LabelAngle", "DOUBLE", "", "", "") # Changed to double.
    
    AddField_management(countyRosette, "County_Number", "DOUBLE", "", "", "")
    
    AddField_management(countyRosette, "COUNTY_NAME", "TEXT", "", "", "55")


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
    print "Done extending and intersecting road features."
    # Need to break this into two pieces and pass some of the inmemorylayers
    # from the first function to the 2nd or similar.
    # the function is just too long to be easily readable/debuggable.
    
    ## 2016-02-18:
    ## For best results, need to call this after the duplicate name removal
    ## and duplicate name removal needs to use the point's angle in it's
    ## decision about which points to remove.


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
    #thresholdRemoval(scaleValue)
    #duplicateNameRemoval(scaleValue)
    #labelAngleNormalization(scaleValue)
    
    scaleValue = "half"
    
    extendAndIntersectRoadFeatures(scaleValue)
    ##thresholdRemoval(scaleValue)
    ##duplicateNameRemoval(scaleValue)
    ##labelAngleNormalization(scaleValue)
    
    endingTime = datetime.datetime.now()
    
    scriptDuration = FindDuration(endingTime, startingTime)
    
    print "\n" # Newline for improved readability.
    print "For the main/complete script portion..."
    print "Starting Time: " + str(startingTime)
    print "Ending Time: " + str(endingTime)
    print "Elapsed Time: " + scriptDuration
    # Tested good on 2015-08-20
    
else:
    pass

## Next script: CountyMapDataDrivenPagesToPDF.py