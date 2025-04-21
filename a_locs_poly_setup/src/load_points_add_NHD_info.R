#' @title Add NHD information to a tibble containing points 
#' 
#' @description
#' Function to load a {sf} of points from a tibble and add the associated information
#' from the NHDPlusHR polygon associated with that point.
#' 
#' @param points a tibble of locations with columns Latitude and Longitude in
#' EPSG:4326 (WGS 84)
#' @param polygons {sf} object; NHDPlusHR polygons {sf}
#' @param data_grp character string; user-defined group identifier to populate
#' a column called "data group"
#' @param loc_type character string; user-defined indicator of location type to
#' populate a column called "location type"
#' 
#' @returns filepath for new {sf} file that contains the information from the 
#' NHDPlusHR polygon associated with it
#' 
#' 
load_points_add_NHD_info <- function(points, polygons, data_grp, loc_type) {
  # create simple feature
  pts_sf <- st_as_sf(points, 
                     crs = 'EPSG:4326', 
                     coords = c('Longitude', 'Latitude')) %>% 
    mutate(location_type = loc_type)
  # get crs of polygons to transform points to
  poly_crs <- st_crs(polygons)
  pts_sf <- st_transform(pts_sf, poly_crs)
  # grab only the polygons that have points in them
  select_poly <- polygons[pts_sf %>% st_buffer(100), ]
  # and grab info
  pts_with_info <- st_join(pts_sf, select_poly)
  if (is.null(pts_with_info$data_group)) {
    pts_with_info <- pts_with_info %>% 
      mutate(data_group = data_grp)
  } else {
    pts_with_info <- pts_with_info %>% 
      mutate(data_group = if_else(is.na(data_group), 
                                  data_grp, 
                                  paste0(data_group, ", ", data_grp)))
  }
  
  # and now add dist to shore
  # get coordinates to calculate UTM zone. This is an adaptation of code from
  # Xiao Yang's code in EE - Yang, Xiao. (2020). Deepest point calculation 
  # for any given polygon using Google Earth Engine JavaScript API 
  # (Version v1). Zenodo. https://doi.org/10.5281/zenodo.4136755
  # we're going to make the assumption that all points in the HUC4 are in the
  # same UTM zone
  coord_for_UTM <- pts_sf %>% st_coordinates()
  mean_x <- mean(coord_for_UTM[, 1])
  mean_y <- mean(coord_for_UTM[, 2])
  # calculate the UTM zone using the mean value of Longitude for the sites
  utm_suffix <- as.character(ceiling((mean_x + 180) / 6))
  utm_code <- if_else(mean_y >= 0,
                      # EPSG prefix for N hemisphere
                      paste0('EPSG:326', utm_suffix),
                      # for S hemisphere
                      paste0('EPSG:327', utm_suffix))
  # transform points and waterbodies to UTM
  transformed_waterbodies <- st_transform(select_poly, 
                                          crs = utm_code)
  transformed_points <- st_transform(pts_sf,
                                     crs = utm_code)
  # cast the waterbodies into a linestrings to measure distance
  waterbody_boundary <- st_cast(st_geometry(transformed_waterbodies), "MULTILINESTRING") %>% 
    # dissolve these into a single geometry, since the identity of the line doesn't
    # matter
    st_union()
  
  # measure the distance, rounded to one place after decimal, set as numeric (otherwise comes back as a matrix)
  pts_with_info$dist_to_shore <- as.numeric(round(st_distance(transformed_points, waterbody_boundary)), 1)
  
  st_write(pts_with_info, file.path("a_locs_poly_setup/out/",
                                    paste0(data_grp,
                                           "_points_NHD_info.gpkg")), append = F)
  
  pts_with_info
}