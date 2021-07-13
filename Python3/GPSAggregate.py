# Author:   ben.bond
# Description:  This Script compiles shapefiles exported by a Trimble GPS
#   Handheld into a single file as denoted in the Arguments or default vars
# Args: -d: Directory file to search, -o: output shapefile to compile results to

import arcpy
import os
from time import time
import tqdm
import argparse

# took out to require parameters
defaultDirectory = r"C:\user\Desktop\GPS"
defaultTargetFile = r"C:\user\Desktop\GPS\Aggregate\2020.shp"

archiveDict, updateDict = {}, {}
sr = arcpy.SpatialReference(2965)  # reference for state plane
# Template File for shapefile creation
tf = r"X:\user\GPSAggregation\Template.shp"


# argument Parser
def arg_parse(directory, target_file):
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", default=directory,
                        help="Directory to search for GPS shpFiles to Aggregate")
    parser.add_argument("-o", "--outputFile", default=target_file, help="Output shapefile location")

    args = parser.parse_args()
    return args


# Generator for Directory Search
def directory_walk(directory_to_search):
    for path, dirs, files in os.walk(directory_to_search):
        for file in files:
            if file.endswith(".shp"):
                shpfile = os.path.join(path, file)
                yield (shpfile, file)


# Generator returns row of shpfile
def read_shp(shpfile):
    try:
        # added check for if its an aggregated vs files straight from gps to preserve original filename
        if len(arcpy.ListFields(shpfile[0])) == 7:
            with arcpy.da.SearchCursor(shpfile[0], ["SHAPE@", "Name", "Code", "Northing", "Easting", "Elevation"], spatial_reference=sr) as cursor:
                for row in cursor:
                    yield [*row, shpfile[1]]
        else:
            with arcpy.da.SearchCursor(shpfile[0], ["SHAPE@", "Name", "Code", "Northing", "Easting", "Elevation", "JobID"], spatial_reference=sr) as cursor:
                for row in cursor:
                    yield row
    except:
        print(f"Error on {shpfile}")


# Create Dict of shp rows.
def assemble_dic(shp, dictionary):
    shp_iterator = read_shp(shp)
    for row in shp_iterator:
        dictionary[row[0].getGeohash(20)] = row


# Compare dictionary of gps Data with existing Dictionary to see what needs to be added
def compare_dic(shp, archive_dict, update_dict):
    shp_iterator = read_shp(shp)
    for row in shp_iterator:
        geo_hash = row[0].getGeohash(20)
        if geo_hash not in archive_dict and geo_hash not in update_dict:
            update_dict[geo_hash] = row


# Check if specified target file exists or if it needs to be created.
def check_target_file(target_file):
    if os.path.exists(target_file):
        shpfile = [target_file, os.path.basename(target_file)]
        assemble_dic(shpfile, archiveDict)
        print("File Found")
    else:
        print("CreatingFile")
        file_name = os.path.basename(target_file)
        path = os.path.dirname(target_file)
        arcpy.CreateFeatureclass_management(path, file_name, "POINT", template=tf, spatial_reference=sr)


# Write Changes to shapefile
def update_target_file(target_file, update_dict):
    with arcpy.da.InsertCursor(target_file, ["SHAPE@", "Name", "Code", "Northing", "Easting", "Elevation", "JobID"]) as cursor:
        for row in update_dict.values():
            cursor.insertRow(row)


if __name__ == '__main__':
    t0 = time()  # some timin stuff for speed testing
    args = arg_parse(defaultDirectory, defaultTargetFile)
    check_target_file(args.outputFile)
    t1 = time() - t0
    print(f"CheckTarget {t1:.2f}")
    totalCounter = 0
    for file in directory_walk(args.directory):
        totalCounter += 1

    for file in tqdm.tqdm(directory_walk(args.directory), total=totalCounter):
        compare_dic(file, archiveDict, updateDict)
    t3 = time() - t0
    tqdm.tqdm.write(f"update Dict {t3:.2f}")  # Fancy Progressbar thingy
    update_target_file(args.outputFile, updateDict)
    print(f"Complete, added {len(updateDict)} points")

    print(f"Final {time()-t0:.2f}")


