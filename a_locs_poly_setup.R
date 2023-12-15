# Source functions for this {targets} list
tar_source("a_locs_poly_setup/src/")


# Setting up the locations and polygon files for RS retrieval -------------

# this collates a few different polygon and point files into a single
# file of each type as needed for the RS workflow. CLP = Cache La Poudre, 
# NW = Northern Water.

# create folder structure
suppressWarnings({
  dir.create("a_locs_poly_setup/nhd/")
  dir.create("a_locs_poly_setup/out/")
})

a_targets_list <- list(
  # get the polygons for CLP watershed using HUC8
  tar_target(
    name = a_make_CLP_polygon,
    command = get_polygons(HUC = "10190007", 
                           minimum_sqkm = 0.01),
    packages = c("sf", "nhdplusTools", "tidyverse")
  ),
  # track and load the CLP polygons
  tar_file_read(
    name = a_CLP_polygons,
    command = a_make_CLP_polygon,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # track and load the csv with NW locs
  tar_file_read(
    name = a_NW_locs_file,
    command = "data/spatialData/ReservoirLocations.csv",
    read = read_csv(!!.x),
    packages = "readr"
  ),
  
  # using the locs file, get the upstream huc-4s to download NHDplusHR
  # this returns a list to branch over
  tar_target(
    name = a_get_NW_hucs,
    command = get_hucs_from_points(point_csv = a_NW_locs_file, 
                                   CRS = "EPSG:4326"),
    packages = c("sf", "nhdplusTools", "tidyverse")
  ),
  # now download the polygons associated with the huc4s from previous target
  # we branch here, but return a repeated collated file name over the length of
  # the list
  tar_target(
    name = a_get_NW_NHD,
    command = get_polygons(HUC = a_get_NW_hucs, 
                           minimum_sqkm = 0.1),
    packages = c("sf", "nhdplusTools", "tidyverse"),
    pattern = map(a_get_NW_hucs)
  ),
  # select the NW polygons by location from the collated polygon from previous target
  tar_target(
    name = a_get_NW_polygons,
    command = select_polygons_by_points(shapefiles = a_get_NW_NHD, 
                                        points = a_NW_locs_file),
    packages = c("sf", "tidyverse"),
    pattern = a_get_NW_hucs
  ),
  # track and load the polygons file for NW sites
  tar_file_read(
    name = a_NW_polygons,
    command = a_get_NW_polygons[1], # output from a_NW_polygons is a list! the values are the same for all list members 
    read = read_sf(!!.x),
    packages = "sf"
  ),
  
  
  # here, we combine the NW and CLP polygons into a single file, condensing the metadata
  # where needed 
  tar_target(
    name = a_make_NW_CLP_polygons,
    command = combine_and_simplify_sfs(sf_1 = a_CLP_polygons, 
                                       data_group_1 = "CLP", 
                                       sf_2 = a_NW_polygons, 
                                       data_group_2 = "NW", 
                                       filename = "CLP_NW_polygons", 
                                       simplify = TRUE),
    packages = c("sf", "tidyverse")
  ),
  # and then track and load the resulting polygon file
  tar_file_read(
    name = a_NW_CLP_polygons,
    command = a_make_NW_CLP_polygons,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # from the polygons, we're going to calculate the center point for each of them
  tar_target(
    name = a_make_NW_CLP_centers,
    command = get_POI_centers(polygons = a_NW_CLP_polygons),
    packages = c("tidyverse", "sf", "polylabelr")
  ),
  # and then track and load the centers file
  tar_file_read(
    name = a_NW_CLP_centers,
    command = a_make_NW_CLP_centers,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  
  
  # and now we'll read in the station location information for NW
  tar_file_read(
    name = a_NW_station_locs,
    command = "data/spatialData/Northern Water Station Coordinates.xlsx",
    read = read_excel(!!.x, sheet = "Lake_Res_edit"),
    packages = "readxl"
  ),
  # And make it a sf object, adding in the NHD info from the upstream polygons file
  tar_target(
    name = a_make_NW_station_points,
    command = load_points_add_NHD_info(points = a_NW_station_locs, 
                                       polygons = a_NW_polygons, 
                                       data_grp = "NW", 
                                       loc_type = "station"),
    packages = c("tidyverse", "sf")
  ),
  # here we track and load that simple features file
  tar_file_read(
    name = a_NW_station_points,
    command = a_make_NW_station_points,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  
  
  # let's also bring in the ROSS CLP subset of lakes, these are random points
  # in the lake and not specific to a sampling location
  tar_file_read(
    name = a_ROSS_CLP_file,
    command = 'data/CLP/upper_poudre_lakes_v2.csv',
    read = read_csv(!!.x),
    packages = 'readr'
  ),
  # create a sf object of the ROSS CLP lakes
  tar_target(
    name = a_ROSS_CLP_points,
    command = st_as_sf(a_ROSS_CLP_file, 
                       crs = "EPSG:4269",
                       coords = c("Longitude", "Latitude")),
    packages = "sf"
  ),
  # get polygons info from NW/CLP sf
  tar_target(
    name = a_ROSS_CLP_polygons,
    command = a_NW_CLP_polygons[a_ROSS_CLP_points, ],
    packages = 'sf'
  ),
  # since all the ROSS_CLP reservoirs are in NW_CLP centers and polygons files, 
  # we'll just add ROSS_CLP label to data group and make a new polygon target
  tar_target(
    name = a_NW_CLP_ROSS_centers,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$Permanent_Identifier)
      a_NW_CLP_centers %>% 
        mutate(data_group = if_else(Permanent_Identifier %in% NHD_perm_ids,
                                    paste(data_group, "ROSS_CLP", sep = ", "),
                                    data_group))
    },
    packages = c("tidyverse", "sf")
  ),
  # do the same for NW_CLP polygons
  tar_target(
    name = a_NW_CLP_ROSS_polygons,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$Permanent_Identifier)
      a_NW_CLP_polygons %>% 
        mutate(data_group = if_else(Permanent_Identifier %in% NHD_perm_ids,
                                    paste(data_group, "ROSS_CLP", sep = ", "),
                                    data_group))
    },
    packages = c("tidyverse", "sf")
  ),
  # and then we'll make the ROSS_CLP centers as a .csv
  tar_target(
    name = a_make_ROSS_CLP_centers,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$Permanent_Identifier)
      a_ROSS_CLP_centers <- a_NW_CLP_ROSS_centers %>% 
        filter(Permanent_Identifier %in% NHD_perm_ids)
      points_to_csv(a_ROSS_CLP_centers, 'ROSS_CLP_centers')
      },
    packages = c("tidyverse", "sf")
  ),
  # load and track that file
  tar_file_read(
    name = a_ROSS_CLP_centers,
    command = a_make_ROSS_CLP_centers,
    read = read_csv(!!.x),
    packages = 'readr'
  ),
  
  # we want the centers and the station locations to be in a single data set for 
  # use in the Landsat pull, and want to retain the metadata (aka, data group 
  # in this case)
  tar_target(
    name = a_make_collated_points,
    command = combine_and_simplify_sfs(sf_1 = a_NW_CLP_ROSS_centers, data_group_1 = NA_character_,
                                       sf_2 = a_NW_station_points, data_group_2 = NA_character_,
                                       filename = "CLP_NW_ROSS_points", simplify = FALSE),
    packages = c("sf", "tidyverse")
  ),
  # and track and load that simple feature
  tar_file_read(
    name = a_collated_points,
    command = a_make_collated_points,
    read = read_sf(!!.x),
    packages = "sf"
  ),
  # and create a .csv of the file for use in the RS pull workflow
  tar_target(
    name = a_collated_pts_to_csv,
    command = points_to_csv(points = a_collated_points, 
                            filename = "NW_CLP_all_points"),
    packages = c("tidyverse", "sf")
  )
)