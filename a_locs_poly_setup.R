# Source functions for this {targets} list

tar_source("a_locs_poly_setup/src/")

# Setting up the locations and polygon files for RS retrieval -------------

# this collates a few different polygon and point files into a single
# file of each type as needed for the RS workflow. CLP = Cache La Poudre, 
# NW = Northern Water.


a_locs_poly_setup <- list(
  
  # check for proper directory structure ------------------------------------
  
  tar_target(
    name = a_check_dir_structure,
    command = {
      directories = c("a_locs_poly_setup/nhd/",
                      "a_locs_poly_setup/out/")
      walk(directories, function(dir) {
        if(!dir.exists(dir)){
          dir.create(dir)
        }
      })
    }
  ),
  
  
  # get CLP polygons --------------------------------------------------------
  
  # get the polygons for CLP watershed using HUC8
  tar_target(
    name = a_CLP_polygons,
    command = {
      a_check_dir_structure
      get_polygons(HUC = "10190007", 
                   minimum_sqkm = 0.01, 
                   ftypes = c(390, 436))
    },
    packages = c("sf", "nhdplusTools", "tidyverse", "janitor")
  ),
  
  # get the NW-specific reservoirs --------------------------------------------
  
  # track and load the csv with NW locs
  tar_file_read(
    name = a_NW_locs_file,
    command = "data/spatialData/ReservoirLocations.csv",
    read = read_csv(!!.x),
    packages = "readr",
    cue = tar_cue("always")
  ),
  
  # using the locs file, get the upstream huc-4s to download NHDplusHR
  # this returns a list to branch over. 
  tar_target(
    name = a_get_NW_hucs,
    command = {
      a_check_dir_structure
      get_hucs_from_points(point_csv = a_NW_locs_file, 
                           CRS = "EPSG:4326")
    },
    packages = c("sf", "nhdplusTools", "tidyverse")
  ),
  
  # now download the polygons associated with the huc4s from previous target
  # we branch here, but return a repeated collated file name over the length of
  # the list
  tar_target(
    name = a_get_NW_NHD,
    command = get_polygons(HUC = a_get_NW_hucs, 
                           minimum_sqkm = 0, # we aren't going to filter for size here
                           ftypes =  c(390, 436)),
    packages = c("sf", "nhdplusTools", "tidyverse", "janitor"),
    pattern = map(a_get_NW_hucs)
  ),
  
  # select the NW polygons by location from the collated polygon from previous target
  tar_target(
    name = a_NW_polygons,
    command = select_polygons_by_points(polygon_files_list = a_get_NW_NHD, 
                                        points = a_NW_locs_file)
  ),
  
  # combine NW/CLP polygons -------------------------------------------------
  
  # here, we combine the NW and CLP polygons into a single file, condensing 
  # the metadata where needed 
  tar_target(
    name = a_NW_CLP_polygons,
    command = combine_and_simplify_sfs(sf_1 = read_sf(a_CLP_polygons), 
                                       data_group_1 = "CLP", 
                                       sf_2 = a_NW_polygons, 
                                       data_group_2 = "NW", 
                                       filename = "CLP_NW_polygons", 
                                       simplify = TRUE)
  ),
  
  
  # calculate centers of the polygons ---------------------------------------
  
  # from the polygons, we're going to calculate the center point for each of them
  tar_target(
    name = a_NW_CLP_centers,
    command = get_POI_centers(polygons = a_NW_CLP_polygons,
                              out_file = "NW_CLP_polygon_centers"),
    packages = c("tidyverse", "sf", "polylabelr")
  ),
  
  
  # load NW station locations --------------------------------------------------
  
  # and now we'll read in the station location information for NW
  tar_file_read(
    name = a_NW_station_locs,
    command = "data/spatialData/Northern Water Station Coordinates.xlsx",
    read = read_excel(!!.x, sheet = "Lake_Res_edit"),
    packages = "readxl"
  ),
  
  # And make it a sf object, adding in the NHD info from the upstream polygons file
  tar_target(
    name = a_NW_station_points,
    command = load_points_add_NHD_info(points = a_NW_station_locs, 
                                       polygons = a_NW_polygons, 
                                       data_grp = "NW", 
                                       loc_type = "station")
  ),
  
  
  # load ROSS CLP station locations --------------------------------------------------
  
  # let's also bring in the ROSS CLP subset of lakes, many of these are random points
  # in the lake and not specific to a sampling location
  tar_file_read(
    name = a_ROSS_CLP_file,
    command = 'data/CLP/upper_poudre_lakes_v5.csv',
    read = read_csv(!!.x),
    packages = 'readr',
    cue = tar_cue("always")
  ),
  
  # create a sf object of the ROSS CLP lakes
  tar_target(
    name = a_ROSS_CLP_points,
    command = st_as_sf(a_ROSS_CLP_file, 
                       crs = "EPSG:4326",
                       coords = c("Longitude", "Latitude")) 
  ),
  
  # now collate the ROSS sites and the NW stations
  tar_target(
    name = a_NW_ROSS_stations,
    command = {
      ross_sites <- a_ROSS_CLP_file %>% 
        filter(!is.na(site_code)) %>% 
        select(Station = site_code, 
               Description = Reservoir,
               notes = Notes,
               Longitude, Latitude)
      ross_nhd <- load_points_add_NHD_info(points = ross_sites, 
                               polygons = a_ROSS_CLP_polygons, 
                               data_grp = "ROSS", 
                               loc_type = "station") 
      bind_rows(a_NW_station_points, ross_nhd)
    },
  ),
  
  # get associated polygons for ROSS CLP -------------------------------------
  
  # get polygons info from NW/CLP sf
  tar_target(
    name = a_ROSS_CLP_polygons,
    command = a_NW_CLP_polygons[a_ROSS_CLP_points %>% 
                                  st_transform(st_crs(a_NW_CLP_polygons)) %>% 
                                  # add a little buffer so that near-shore are included
                                  st_buffer(100), ]
  ),
  
  
  # add ROSS_CLP label to data group ----------------------------------------
  
  # Some of the ROSS CLP are stations with data, others are not. 
  tar_target(
    name = a_NW_CLP_ROSS_centers,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$permanent_identifier)
      a_NW_CLP_centers %>% 
        mutate(data_group = if_else(permanent_identifier %in% NHD_perm_ids,
                                    paste(data_group, "ROSS_CLP", sep = ", "),
                                    data_group))
    }
  ),
  
  # since all the ROSS_CLP reservoirs are in NW_CLP centers and polygons files, 
  # we'll just add ROSS_CLP label to data group and make a new polygon target
  tar_target(
    name = a_NW_CLP_ROSS_sites,
    command = {
      a_NW_CLP_centers %>% 
        mutate(data_group = if_else(permanent_identifier %in% NHD_perm_ids,
                                    paste(data_group, "ROSS_CLP", sep = ", "),
                                    data_group))
    }
  ),
  
  # do the same for NW_CLP polygons
  tar_target(
    name = a_NW_CLP_ROSS_polygons,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$permanent_identifier)
      a_NW_CLP_polygons %>% 
        mutate(data_group = if_else(permanent_identifier %in% NHD_perm_ids,
                                    paste(data_group, "ROSS_CLP", sep = ", "),
                                    data_group))
    }
  ),
  
  
  # pull out the ROSS_CLP centers -------------------------------------------
  
  # and then we'll make the ROSS_CLP centers as a .csv
  tar_target(
    name = a_make_ROSS_CLP_centers,
    command = {
      NHD_perm_ids = unique(a_ROSS_CLP_polygons$permanent_identifier)
      a_ROSS_CLP_centers <- a_NW_CLP_ROSS_centers %>% 
        filter(permanent_identifier %in% NHD_perm_ids)
      points_to_csv(a_ROSS_CLP_centers, 'ROSS_CLP_centers')
    }
  ),
  
  # load and track that file
  tar_file_read(
    name = a_ROSS_CLP_centers,
    command = a_make_ROSS_CLP_centers,
    read = read_csv(!!.x),
    packages = 'readr'
  ),
  
  
  # prep for RS pull --------------------------------------------------------
  
  # we want the centers and the station locations to be in a single data set for 
  # use in the Landsat pull, and want to retain the metadata (aka, data group 
  # in this case)
  tar_target(
    name = a_collated_points,
    command = {
      combine_and_simplify_sfs(sf_1 = a_NW_CLP_ROSS_centers, data_group_1 = NA_character_,
                               sf_2 = a_NW_ROSS_stations, data_group_2 = NA_character_,
                               filename = "CLP_NW_ROSS_points", simplify = FALSE)
      
    }
  ),
  
  # and create a .csv of the file for use in the RS pull workflow
  tar_target(
    name = a_collated_pts_to_csv,
    command = points_to_csv(points = a_collated_points, 
                            filename = "NW_CLP_all_points")
  ),
  
  # get EcoRegion L3 polygons ------------------------------------------------
  
  # we're going to pull ER L3 lake centers to create a localized handoff 
  # coefficient. This is, in part, a side quest to see how the hand off
  # coefficients change regionally (if at all)
  
  tar_target(
    name = a_ecoregion_aoi,
    command = {
      temp_file <- tempfile(fileext = 'zip')
      download.file("https://dmap-prod-oms-edc.s3.us-east-1.amazonaws.com/ORD/Ecoregions/us/us_eco_l3.zip",
                    destfile = temp_file)
      temp_dir <- tempdir()
      unzip(temp_file, exdir = temp_dir)
      er_l3 <- read_sf(file.path(temp_dir, "us_eco_l3.shp"))
      # filter for zone 21 only
      er_l3 %>% filter(US_L3CODE == 21) %>% st_union()
    }
  ), 
  
  tar_target(
    name = a_aoi_hucs,
    command = get_huc(AOI = a_ecoregion_aoi,
                      type = "huc04") %>% 
      st_drop_geometry() %>% 
      pull(huc4),
    packages = c("nhdplusTools", "sf", "tidyverse")
  ),
  
  tar_target(
    name = a_make_aoi_polygons,
    command = get_polygons(HUC = a_aoi_hucs, 
                           minimum_sqkm = 0.01, 
                           ftypes = c(390, 436)),
    packages = c("sf", "nhdplusTools", "tidyverse", "janitor"),
    pattern = map(a_aoi_hucs)
  ),
  
  tar_target(
    name = a_aoi_polygons,
    command = {
      map(a_make_aoi_polygons,
          read_sf) %>% 
        bind_rows() %>% 
        # there may be some tiny polygons that squeak through because there is 
        # no minimum set for 1019 from processing the NW and CLP reservoirs
        filter(area_sq_km >= 0.01) 
    }
  ),
  
  tar_target(
    name = a_aoi_centers,
    command = get_POI_centers(polygons = a_aoi_polygons,
                              out_file = "er3z21_centers"),
    packages = c("tidyverse", "sf", "polylabelr")
  ),
  
  
  # and output a .csv for the RS pull
  tar_target(
    name = a_aoi_centers_to_csv,
    command = points_to_csv(points = a_aoi_centers, 
                            filename = "er3z21_centers")
  )
  
)
