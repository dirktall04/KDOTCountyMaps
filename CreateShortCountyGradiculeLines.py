#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CreateShortCountyGradiculeLines.py

# Enhancement to the map

import os
from arcpy import (AddField_management, Buffer_analysis,
                   CreateFeatureclass_management, CopyFeatures_management,
                   Delete_management, 
                   DeleteRows_management, Describe,
                   env, Erase_analysis,
                   GetCount_management, Intersect_analysis,
                   ListFields, MakeFeatureLayer_management,
                   MultipartToSinglepart_management,
                   SelectLayerByAttribute_management)
from arcpy.da import (InsertCursor as daInsertCursor, # @UnresolvedImport
                      SearchCursor as daSearchCursor)  # @UnresolvedImport

env.overwriteOutput = True
env.outputZFlag = "Disabled"

sdeProdLocation = r'Database Connections\GIS@sdeprod.sde'
sdeProdUser  = 'SHARED.'
sharedCounties = os.path.join(sdeProdLocation, sdeProdUser + 'COUNTIES')
sharedNonStateSystem = os.path.join(sdeProdLocation, sdeProdUser + 'Non_State_System')
countyCountyGradicule = os.path.join(sdeProdLocation, 'COUNTY.COUNTY_GRATICULE')

# Changed to the countyMaps SQL server instance. & Changed to the Geo user from SDE.
sqlGdbLocation = r'Database Connections\geo@countyMaps.sde' 
sqlGDBUser = 'countyMaps.GEO.'

# Silly way of specifying the same thing three different ways
# because some of the arcpy tools make sense and some don't so much.
countyGradiculeShortNoPath = 'CountyGradiculeShort_H'
countyGradiculeShortWithUser = os.path.join(sqlGDBUser, countyGradiculeShortNoPath)
countyGradiculeShortPath = os.path.join(sqlGdbLocation, sqlGDBUser + countyGradiculeShortNoPath)

## In_Memory Layers start here:
inMemGDB = "in_memory"

countiesBuffered = os.path.join(inMemGDB, 'CountiesBuffered')
countiesMiniBuffered = os.path.join(inMemGDB, 'countiesMiniBuffered')
countyGradiculeCopied= os.path.join(inMemGDB, 'countyGradiculeCopied')

xyToleranceVal = "5 Feet"


# Need to make a feature layer of the sharedCounties, then
# "save" it to the inMemGDB, then make a feature layer from
# that. Then, use that in the processes incase the ordering
# gets mixed up, so that the sharedCounties layer is not
# modified.
# Even better would be to make sure that you're connecting
# as read only and do that above, however, so try that also.


def createShortGradiculeLinesForEachCounty():
    # Get/use the same projection as the one used for the county roads.
    spatialReferenceProjection = Describe(sharedNonStateSystem).spatialReference
    
    env.workspace = sqlGdbLocation
    
    inputCountyGradicule = countyCountyGradicule
    bufferedCounties = 'bufferedCounties'
    countiesToCopy = 'countiesToCopy'
    gradiculeToCopy = 'gradiculeToCopy'
    loadedGradiculeCopy = 'loadedGradiculeCopy'
    loadedTempGradicule = 'loadedTempGradicule'
    #unBufferedCounties = 'unBufferedCounties'
    # Using the miniBuffered process changes it from
    # 1457 total output features to 1481 (at 2.1k)
    # total output features.
    miniBufferedCounties = 'miniBufferedCounties'
    loadedOutputGradicule = 'loadedOutputGradicule'
    tempCounties = r'in_memory\tempCounties'
    tempCountyGradicule = r'in_memory\tempCountyGradicule'
    tempCountyGradiculePostErase = r'in_memory\tempCountyGradiculePostErase'
    tempCountyGradiculeSinglePart = r'in_memory\tempCountyGradiculeSinglePart'
    bufferCursorFields = ["OBJECTID", "COUNTY_NAME"]
    
    MakeFeatureLayer_management(sharedCounties, countiesToCopy)
    
    MakeFeatureLayer_management(countyCountyGradicule, gradiculeToCopy)
    CopyFeatures_management(gradiculeToCopy, countyGradiculeCopied)
    MakeFeatureLayer_management(countyGradiculeCopied, loadedGradiculeCopy)
    
    # Might be worth dissolving based on COORD & County_Name prior
    # to removing the County_Name field, if that's a possibility.
    
    # Or better yet, just make it so that the Gradicule lines for
    # a particular county are eligible for intersecting and
    # erasing with that same county's polygon's.  All we're
    # trying to do here is make it so that the county's original
    # gradicule lines are about half of their original size.
    # Don't need to find out which gradicule lines are close to
    # the county or anything else like that. Just need to reduce
    # the size of the lines and keep the parts that are nearest
    # the county that they go with.
    
    # Remove the County_Name field so that the intersect can add it
    # back and populate it only where the county buffer actually
    # intersects the lines.
    #DeleteField_management(countyGradiculeCopied, "County_Name")
    
    # Elaine requested that this be 1000 Feet shorter.
    # I made it 2000 feet shorter, because it still seemed too big.
    Buffer_analysis(sharedCounties, countiesBuffered, "8000 Feet")
    Buffer_analysis(sharedCounties, countiesMiniBuffered, "1500 Feet")
    
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
    
    MakeFeatureLayer_management(countiesBuffered, bufferedCounties)
    MakeFeatureLayer_management(countiesMiniBuffered, miniBufferedCounties)
    
    loadedCountiesFields = ListFields(bufferedCounties)
    
    for loadedCountiesField in loadedCountiesFields:
        print "A loadedCountiesField was found: " + str(loadedCountiesField.name)
    
    countyGradiculeFields = ListFields(loadedGradiculeCopy)
    
    for countyGradiculeField in countyGradiculeFields:
        print "A countyGradiculeField was found: " + str(countyGradiculeField.name)
    
    for listedRow in bufferedCountyPolygonList:
        print str(listedRow)
        selectCounty = listedRow[1]
        
        whereClause = """ "COUNTY_NAME" = '""" + str(selectCounty) + """' """
        print "The whereClause is " + str(whereClause)
        SelectLayerByAttribute_management(bufferedCounties, "NEW_SELECTION", whereClause)
        
        SelectLayerByAttribute_management(loadedGradiculeCopy, "NEW_SELECTION", whereClause)
        
        Intersect_analysis([loadedGradiculeCopy, bufferedCounties], tempCountyGradicule, "ALL")
        
        MultipartToSinglepart_management(tempCountyGradicule, tempCountyGradiculeSinglePart)
        
        # Selects the same county as the other Select, but does it from the miniBufferedCounties
        # so that the lines which lay inside of the county and running just along its edges
        # are erased, as they should only exist as gradicules for the counties adjoining this
        # one, but not for this one itself.
        SelectLayerByAttribute_management(miniBufferedCounties, "NEW_SELECTION", whereClause)
        
        MakeFeatureLayer_management(tempCountyGradiculeSinglePart, loadedTempGradicule)
        
        SelectLayerByAttribute_management(loadedTempGradicule, "NEW_SELECTION", whereClause)
        
        secVerGradiculeFields = ListFields(loadedTempGradicule)
    
        #for secVerGradiculeField in secVerGradiculeFields:
        #    print "A secVerGradiculeField was found: " + str(secVerGradiculeField.name)
        
        Erase_analysis(loadedTempGradicule, miniBufferedCounties, tempCountyGradiculePostErase, xyToleranceVal)
        
        fieldsToCopy = ["SHAPE@", "County_Number", "County_Name", "DIRECTION", "COORD"]
        
        # 2nd SearchCursor
        newCursor = daSearchCursor(tempCountyGradiculePostErase, fieldsToCopy)
        for newRow in newCursor:
            outputFeatureList.append(newRow)
        
        if 'newCursor' in locals():
            del newCursor
        else:
            pass
    
    try:
        Delete_management(countyGradiculeShortWithUser)
    except:
        pass
    
    CreateFeatureclass_management(sqlGdbLocation, countyGradiculeShortNoPath, "POLYLINE", "", "", "", spatialReferenceProjection)
    
    AddField_management(countyGradiculeShortNoPath, "County_Number", "DOUBLE", "", "", "")
    
    AddField_management(countyGradiculeShortNoPath, "County_Name", "TEXT", "", "", "55")
    
    AddField_management(countyGradiculeShortNoPath, "DIRECTION", "TEXT", "", "", "5")
    
    AddField_management(countyGradiculeShortNoPath, "COORD", "TEXT", "", "", "30")
    
    print "First Intersected County Gradicule Row: " + str(outputFeatureList[0])
    
    newCursor = daInsertCursor(countyGradiculeShortPath, fieldsToCopy)
    counter = 1
    for outputFeature in outputFeatureList:
        rowToInsert = ([outputFeature])
        
        insertedOID = newCursor.insertRow(outputFeature)
        
        counter += 1
        
        print "Inserted Row with Object ID of " + str(insertedOID)
    
    # Load the feature class. Remove anything shorter than 850 feet.
    MakeFeatureLayer_management(countyGradiculeShortPath, loadedOutputGradicule)
    
    # Select the rows that have geometry which is shorter than 850 feet.
    ## Note that Shape.STLength() returns units in the projection
    ## or coordinate system that it the feature class is stored in.
    whereClause = """ Shape.STLength() <  850 """
    print "The whereClause is " + str(whereClause)
    SelectLayerByAttribute_management(loadedOutputGradicule, "NEW_SELECTION", whereClause)
    
    # If there is at least one row selected, delete each selected row.
    if int(GetCount_management(loadedOutputGradicule).getOutput(0)) > 0:
        print str(GetCount_management(loadedOutputGradicule).getOutput(0)) + "rows selected."
        DeleteRows_management(loadedOutputGradicule)
    else:
        print "No rows were selected to delete."
    
    if 'newCursor' in locals():
        del newCursor
    else:
        pass


if __name__ == "__main__":
    createShortGradiculeLinesForEachCounty()

else:
    pass