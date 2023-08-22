#' Function to load a {sf} of points from a tibble and add the associated information
#' from the NHDPlusHR polygon associated with that point.
#' 
#' @param points a tibble of locations with columns Latitude and Longitude in
#' EPSG:4326 (WGS 84)
#' @param polygons NHDPlusHR polygons {sf}
#' @returns filepath for new {sf} file that contains the information from the 
#' NHDPlusHR polygon associated with it
#' 
#' @note This has a hardcoded `data_group` and `location_type` variable in it
#' such that this function is not generalizable.
#' 
#' 
load_points_add_NHD_info <- function(points, polygons) {
  pts_sf <- st_as_sf(points, 
           crs = 'EPSG:4326', 
           coords = c('Longitude', 'Latitude')) %>% 
    mutate(data_group = 'NW',
           location_type = 'station')
  poly_crs <- st_crs(polygons)
  pts_sf <- st_transform(pts_sf, poly_crs)
  select_poly <- polygons[pts_sf,]
  pts_with_info <- st_join(pts_sf, select_poly)
  st_write(pts_with_info, '0_locs_poly_setup/out/NW_points_NHD_info.gpkg', append = F)
  '0_locs_poly_setup/out/NW_points_NHD_info.gpkg'
}