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
  pts_sf <- st_as_sf(points, 
                     crs = 'EPSG:4326', 
                     coords = c('Longitude', 'Latitude')) %>% 
    mutate(data_group = data_grp,
           location_type = loc_type)
  poly_crs <- st_crs(polygons)
  pts_sf <- st_transform(pts_sf, poly_crs)
  select_poly <- polygons[pts_sf,]
  pts_with_info <- st_join(pts_sf, select_poly)
  st_write(pts_with_info, file.path("a_locs_poly_setup/out/",
                                    paste0(data_grp,
                                           "_points_NHD_info.gpkg")), append = F)
  file.path("a_locs_poly_setup/out/",
            paste0(data_grp,
                   "_points_NHD_info.gpkg"))
}