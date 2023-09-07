# Source functions for this {targets} list
tar_source("0_locs_poly_setup/src/")


# Setting up the locations and polygon files for RS retrieval -------------

# this collates a few different polygon and point files into a single
# file of each type as needed for the RS workflow. CLP = Cache La Poudre, 
# NW = Northern Water.

# create folder structure
dir.create("0_locs_poly_setup/nhd/")
dir.create("0_locs_poly_setup/out/")

p0_targets_list <- list(
  # get the polygons for CLP watershed using HUC8
  tar_target(
    name = p0_make_CLP_polygon,
    command = get_polygons("10190007", 0.01),
    packages = c("sf", "nhdplusTools", "tidyverse")
  ),
  # track and load the CLP polygons
  tar_file_read(
    name = p0_CLP_polygons,
    command = p0_make_CLP_polygon,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # track and load the csv with NW locs
  tar_file_read(
    name = p0_NW_locs_file,
    command = "data/spatialData/ReservoirLocations.csv",
    read = read_csv(!!.x),
    packages = "readr"
  ),
  # using the locs file, get the upstream huc-4s to download NHDplusHR
  # this returns a list to branch over
  tar_target(
    name = p0_get_NW_hucs,
    command = get_hucs_from_points(p0_NW_locs_file, "EPSG:4326"),
    packages = c("sf", "nhdplusTools", "tidyverse")
  ),
  # now download the polygons associated with the huc4s from previous target
  # we branch here, but return a repeated collated file name over the length of
  # the list
  tar_target(
    name = p0_get_NW_NHD,
    command = get_polygons(p0_get_NW_hucs, 0.1),
    packages = c("sf", "nhdplusTools", "tidyverse"),
    pattern = map(p0_get_NW_hucs)
  ),
  # select the NW polygons by location from the collated polygon from previous target
  tar_target(
    name = p0_get_NW_polygons,
    command = select_polygons_by_points(p0_get_NW_NHD, p0_NW_locs_file),
    packages = c("sf", "tidyverse"),
    pattern = p0_get_NW_hucs
  ),
  # track and load the polygons file for NW sites
  tar_file_read(
    name = p0_NW_polygons,
    command = p0_get_NW_polygons[1], # output from p0_NW_polygons is a list! the values are the same for all list members 
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # here, we combine the NW and CLP polygons into a single file, condensing the metadata
  # where needed 
  tar_target(
    name = p0_make_NW_CLP_polygons,
    command = combine_and_simplify_sfs(p0_CLP_polygons, "CLP", p0_NW_polygons, "NW", "CLP_NW_polygons"),
    packages = c("sf", "tidyverse")
  ),
  # and then track and load the resulting polygon file
  tar_file_read(
    name = p0_NW_CLP_polygons,
    command = p0_make_NW_CLP_polygons,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # from the polygons, we're going to calculate the center point for each of them
  tar_target(
    name = p0_make_NW_CLP_centers,
    command = get_POI_centers(p0_NW_CLP_polygons),
    packages = c("tidyverse", "sf", "polylabelr")
  ),
  # and then track and load the centers file
  tar_file_read(
    name = p0_NW_CLP_centers,
    command = p0_make_NW_CLP_centers,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # and now we'll read in the station location information for NW
  tar_file_read(
    name = p0_NW_station_locs,
    command = "data/spatialData/Northern Water Station Coordinates.xlsx",
    read = read_excel(!!.x, sheet = "Lake_Res_edit"),
    packages = "readxl"
  ),
  # And make it a sf object, adding in the NHD info from the upstream polygons file
  tar_target(
    name = p0_make_NW_station_points,
    command = load_points_add_NHD_info(p0_NW_station_locs, p0_NW_polygons),
    packages = c("tidyverse", "sf")
  ),
  # here we track and load that simple features file
  tar_file_read(
    name = p0_NW_station_points,
    command = p0_make_NW_station_points,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # we want the centers and the station locations to be in a single data set for 
  # use in the Landsat pull, and want to retain the metadata (aka, data group 
  # in this case)
  tar_target(
    name = p0_make_collated_points,
    command = combine_and_simplify_sfs(p0_NW_station_points, NA_character_, 
                                       p0_NW_CLP_centers, NA_character_,
                                       "p0_NW_CLP_all_points"),
    packages = c("sf", "tidyverse")
  ),
  # and track and load that simple feature
  tar_file_read(
    name = p0_collated_points,
    command = p0_make_collated_points,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # and create a .csv of the file for use in the RS pull workflow
  tar_target(
    name = p0_collated_pts_to_csv,
    command = points_to_csv(p0_collated_points, "NW_CLP_all_points"),
    packages = c("tidyverse", "sf")
  ),
  # and track and load that file
  tar_file_read(
    name = p0_collated_pts_file,
    command = p0_collated_pts_to_csv,
    read = read_csv(!!.x),
    packages = c("tidyverse", "sf")
  )
)