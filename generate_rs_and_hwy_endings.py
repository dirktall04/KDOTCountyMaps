# Import from arcpy module
from arcpy import env, Dissolve_management, Select_analysis


def route_endings_generation():
    # Overwrite tables
    env.overwriteOutput = True
    
    # May need to check locks
    
    # Local variables:
    SHARED_NON_STATE_SYSTEM = r"\\gisdata\ArcGIS\GISdata\Connection_files\kdot_gis@sdeprod.sde\SHARED.NON_STATE_SYSTEM"
    RS_Routes = r"\\gisdata\Planning\Cart\Maps\MXD\County\County_Maps.gdb\RS_Routes"
    RS_Endings_Dissolve = r"\\gisdata\Planning\Cart\Maps\MXD\County\County_Maps.gdb\RS_Endings_Dissolve"
    
    C_Routes_Temp = r"in_memory\C_Routes_Temp"
    C_Endings_Dissolve = r"\\gisdata\Planning\Cart\Maps\MXD\County\County_Maps.gdb\C_Endings_Dissolve"
    
    MCS_Routes_Temp = r"in_memory\MCS_Routes_Temp"
    MCS_Endings_Dissolve = r"\\gisdata\Planning\Cart\Maps\MXD\County\County_Maps.gdb\MCS_Endings_Dissolve"
    
    SHARED_STATE_SYSTEM = r"\\gisdata\ArcGIS\GISdata\Connection_files\kdot_gis@sdeprod.sde\SHARED.STATE_SYSTEM"
    State_Routes_Dissolve = r"\\gisdata\Planning\Cart\Maps\MXD\County\County_Maps.gdb\STATE_SYSTEM_Dissolve"
    
    # Process: Select
    Select_analysis(SHARED_NON_STATE_SYSTEM, RS_Routes, "LRS_ROUTE_PREFIX = 'R'")
    
    # Process: Dissolve
    Dissolve_management(RS_Routes, RS_Endings_Dissolve, "LRS_KEY", "", "SINGLE_PART", "DISSOLVE_LINES")
    
    # Process: Select
    Select_analysis(SHARED_NON_STATE_SYSTEM, C_Routes_Temp, "LRS_ROUTE_PREFIX = 'C'")
    
    # Process: Dissolve
    Dissolve_management(C_Routes_Temp, C_Endings_Dissolve, "LRS_KEY", "", "MULTI_PART", "DISSOLVE_LINES")
    
    # Process: Select
    Select_analysis(SHARED_NON_STATE_SYSTEM, MCS_Routes_Temp, "LRS_ROUTE_PREFIX = 'M'")
    
    # Process: Dissolve
    Dissolve_management(MCS_Routes_Temp, MCS_Endings_Dissolve, "LRS_KEY", "", "SINGLE_PART", "DISSOLVE_LINES")
    
    # Process: Dissolve
    Dissolve_management(SHARED_STATE_SYSTEM, State_Routes_Dissolve, "LRS_ROUTE;LRS_PREFIX", "", "MULTI_PART", "DISSOLVE_LINES")


if __name__ == "__main__":
    route_endings_generation()
else:
    pass