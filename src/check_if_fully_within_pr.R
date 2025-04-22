#' @title Check to see if point is completely contained within path-row
#' 
#' @description
#' Add WRS pathrow information to the locations 
#' file, remove buffered points that are not completely within the 
#' path row geometry.
#' 
#' @param WRS_pathrows list of pathrows to iterate over
#' @param locations dataframe of locations
#' @param yml contents of the reformatted yaml .csv file
#' @param parent_path parent filepath where the remote sensing pull is occurring
#' 
#' @returns tibble of locations that includes WRS2 pathrow if, when buffered, they 
#' are fully contained by the WRS2 pathrow extent
#' 
#' @note
#' This step will result in more rows than the locations file, because a single 
#' location in space can fall into multiple pathrows.
#' 
#' 
check_if_fully_within_pr <- function(WRS_pathrow, locations, yml, parent_path) {
  # make a directory of locations for use in python workflow
  if (!dir.exists(file.path(parent_path, "out/locations/"))) {
    dir.create(file.path(parent_path, "out/locations/"))
  }
  # get the WRS2 shapefile
  WRS <- read_sf(file.path(parent_path, "in/WRS2_descending.shp"))
  # make locations into a {sf} object
  locs <- st_as_sf(locations, 
                   coords = c("Longitude", "Latitude"), 
                   crs = yml$location_crs)
  # make sure that the locs are in WGS84 if they aren't already
  if (yml$location_crs != "EPSG:4326") {
    locs <- st_transform(locs, "EPSG:4326")
  }
  # map over each path-row, adding the pathrow to the site. Note, this will create
  # a larger number of rows than the upstream file, because sites can be in more
  # than one pathrow. 
  # filter for one path-row
  one_PR <- WRS %>% filter(PR == WRS_pathrow) 
  # get the locs within the path-row
  x <- locs[one_PR, ]
  x <- x %>% 
    mutate(WRS2_PR = WRS_pathrow) 
  
  # in order to apply a buffer in sf, we need to convert to UTM, otherwise 
  # it's assumed to be decimal degrees
  # we'll use the WRS to calculate the appropriate UTM to use here.
  
  # just for kicks, make sure that the PR file is in EPSG:4326. It should be, 
  # but this is our sanity check!
  if (st_crs(one_PR) != "EPSG:4326") {
    wrs <- st_transform(one_PR, crs = "EPSG:4326")
  }
  
  # get coordinates to calculate UTM zone. This is an adaptation of code from
  # Xiao Yang's code in EE - Yang, Xiao. (2020).
  coord_for_UTM <- wrs %>% st_coordinates()
  mean_x <- mean(coord_for_UTM[,1])
  mean_y <- mean(coord_for_UTM[,2])
  # calculate the UTM zone using the mean value of Longitude for the polygon
  utm_suffix <- as.character(ceiling((mean_x + 180) / 6))
  utm_code <- if_else(mean_y >= 0,
                      # EPSG prefix for N hemisphere
                      paste0('EPSG:326', utm_suffix),
                      # for S hemisphere
                      paste0('EPSG:327', utm_suffix))
  # transform points and wrs to UTM
  wrs <- st_transform(wrs, 
                      crs = utm_code) %>% 
    st_make_valid()
  x_trans <- st_transform(x, 
                          crs = utm_code) 
  x_buffd <- st_buffer(x_trans, dist = as.numeric(yml$site_buffer)) %>% 
    st_make_valid()
  # see if the buffered points are completely contained  
  is_contained_by_WRS = tibble(st_within(x_buffd,
                                         wrs,
                                         sparse = FALSE))   
  names(is_contained_by_WRS) = "is_contained_by_WRS"
  # and bind cols
  filtered <- bind_cols(x, is_contained_by_WRS) %>% 
    st_drop_geometry() %>% 
    # only select the points completely contained by the WRS
    filter(is_contained_by_WRS == TRUE) %>% 
    select(-is_contained_by_WRS) %>% 
    left_join(., locations)
  write_csv(filtered,
            file.path(parent_path,
                      paste0("out/locations/locations_", 
                             WRS_pathrow, 
                             ".csv")))
  filtered
}
