#/usr/bin/env python
# *-* coding:utf-8 *-*
#countyPathsFix.py
# Created 2015-09-25
# Updated 2016-01-28
# Updated 2016-02-09

from arcpy import listmxds
from arcpy.mapping import MapDocument, ListLayers

mxdPathsList = list()

mxdPathsList.append(r"C:\Users\elaineb\Desktop\countyMapHalf18x24H4.mxd")

sdePathsList = list()

sdePathsList.append([r"Database Connections\county@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"C:\Users\kyleg\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\SDEPROD_SHARED.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Database Connections\shared@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Database Connections\city@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Database Connections\osm@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Z:\Connection_files\readonly@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Z:\Connection_files\gate@gateprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\kgate_ro@gateprod.sde"])

sdePathsList.append([r"C:\Users\dtalley\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\RailroadDBReadOnly.sde\Railroad.DBO.KDOT_RAIL", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde\GIS.KDOT_RAIL"])

sdePathsList.append([r"Database Connections\RailroadDBReadOnly.sde\Railroad.DBO.KDOT_RAIL\Railroad.DBO.Active_Railroad_Network", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde\GIS.KDOT_RAIL"])

sdePathsList.append([r"Z:\Connection_files\RO@sqlgisprod_GIS_cansys.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\RO@sqlgisprod_GIS_cansys.sde"])

sdePathsList.append([r"Database Connections\GATEprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\kgate_ro@gateprod.sde"])

sdePathsList.append([r"Z:\Connection_files\readonly@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"C:\Users\dtalley\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\GIS@sdeprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"C:\Users\elaineb\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\shared@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\shared@gisprod.sde"])

sdePathsList.append([r"C:\Users\elaineb\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\readonly@gisprod.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde"])

sdePathsList.append([r"Z:\Connection_files\geo@countyMaps.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@countyMaps.sde"])

sdePathsList.append([r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@countyMaps.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@mapAutomation.sde"])
    
sdePathsList.append([r"Z:\Connection_files\geo@countyMaps.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@countyMaps.sde"])

sdePathsList.append([r"Z:\Connection_files\geo@countyMaps.sde", 
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@mapAutomation.sde"])

featureClassDict = dict()

## How to add to the featureClassDict:
## featureClassDict["Layer's previous data source"] = ["Workspace to change to", "Workspace_Type, see examples", "Datasetname"]
## Workspace_types we use often: FILEGDB_WORKSPACE, SDE_WORKSPACE, SHAPEFILE_WORKSPACE
## Other workspace_types: ACCESS_WORKSPACE, ARCINFO_WORKSPACE, CAD_WORKSPACE, EXCEL_WORKSPACE, NONE, OLEDB_WORKSPACE,
## RASTER_WORKSPACE, TEXT_WORKSPACE, TIN_WORKSPACE, VPF_WORKSPACE

# Converting a shapefile path to a filegdb path.
featureClassDict[r"Z:\USGS\NHD\NHDArea.shp"] = [r"\\gisdata\ArcGIS\GISdata\USGS\NHD\NHDH_KS.gdb", "FILEGDB_WORKSPACE", "NHDArea"]

# From the user's perspective
featureClassDict[r"Database Connections\RailroadDBReadOnly.sde\Railroad.DBO.KDOT_RAIL\Railroad.DBO.Active_Railroad_Network"] = [
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde", "SDE_WORKSPACE", r"GIS.Active_Railroad_Network"]

# From anyone else's perspective	
featureClassDict[r"C:\Users\dtalley\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\RailroadDBReadOnly.sde\Railroad.DBO.KDOT_RAIL\Railroad.DBO.Active_Railroad_Network"] = [
    r"\\gisdata\ArcGIS\GISdata\Connection_files\readonly@gisprod.sde", "SDE_WORKSPACE", r"GIS.Active_Railroad_Network"]

# The findAndReplaceWorkspacePaths method didn't work for these features, but replaceDataSource seems to.
featureClassDict[r"Z:\Connection_files\geo@countyMaps.sde\countyMaps.GEO.countyRoadNameRosette_H"] = [
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@mapAutomation.sde", "SDE_WORKSPACE", r"GEO.countyRoadNameRosette_H"]

featureClassDict[r"Z:\Connection_files\geo@countyMaps.sde\countyMaps.GEO.CountyGradiculeShort_H"] = [
    r"\\gisdata\ArcGIS\GISdata\Connection_files\geo@mapAutomation.sde", "SDE_WORKSPACE", r"GEO.CountyGradiculeShort_H"]

# Converting to shapefile is not very intuitive. Use the folder location without the shapefile name or extension as the workspace to change to.
# Use the shapefile's name as the datasetname.
# For instance, to reverse the NHDARea.shp to NHDH_KS.gdb move made above, use the following dictionary entry:
# featureClassDict[r"\\gisdata\ArcGIS\GISdata\USGS\NHD\NHDH_KS.gdb\Hydrography\NHDArea"] = [r"Z:\USGS\NHD", "SHAPEFILE_WORKSPACE", "NHDArea"]

def generateMxdPathsList(inputFolder):
    """
    This function takes a folder and returns a list of all of the mxd files that can be found in it.
    """
    pass

def findAndReplaceOldPaths(mxdList, sdeList, featureDict):
    
    for mxdItem in mxdList:
        mxd = MapDocument(mxdItem)
        print "\nFor the mxd at " + str(mxdItem)
        print "the layers were:\n"

        # featureDict changes:
        mxdLayers = ListLayers(mxd)
        
        for mxdLayer in mxdLayers:
            # Might be causing locked data sources to not get changed.
            # If you can't access the mxdLayer source, it might not
            # use the supports method correctly.
            if mxdLayer.supports('dataSource'):
                layerSource = mxdLayer.dataSource
                print str(layerSource)
                if layerSource in featureDict.keys():
                    mxdLayer.replaceDataSource(featureDict[layerSource][0], featureDict[layerSource][1], featureDict[layerSource][2])
                else:
                    pass
            else:
                pass
        
        # sdeList changes:
        for sdeItem in sdeList:
            mxd.findAndReplaceWorkspacePaths(sdeItem[0], sdeItem[1])
            
        print "\nThe new layers are:\n"

        mxdLayers = ListLayers(mxd)

        for mxdLayer in mxdLayers:
            if mxdLayer.supports('dataSource'):
                layerSource = mxdLayer.dataSource
                print str(layerSource)
            else:
                pass

        # Make the changes permanent.
        print "\nSaving mxd...\n"
        mxd.save()

        del mxd


if __name__ == "__main__":
    print("\nStarting script...")
    #mxdPathsList = generateMxdPathsList(mxdFolder)
    findAndReplaceOldPaths(mxdPathsList, sdePathsList, featureClassDict)
    print("\nPath replacement complete.")

else:
    print('countyPathsFix script imported.')