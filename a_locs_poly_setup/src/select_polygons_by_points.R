#' @title Collate and filter {sf} polygon files
#' 
#' @description
#' Function to collate multiple {sf} polygon files together, load points as a {sf} 
#' object from a tibble, and select the polygons that intersect with the points.
#' 
#' @param polygons {sf} polygon object
#' @param points a tibble of locations with columns Latitude and Longitude in
#' EPSG:4326 (WGS 84)
#' @returns {sf} object that contains the polygons that contained 
#' points
#' 
#' 
select_polygons_by_points <- function(polygon_files_list, points){
  shps <- map(polygon_files_list, read_sf) %>% bind_rows
  poly_crs <- st_crs(shps)
  # load points - crs is WGS84
  pts <- st_as_sf(points, crs = "EPSG:4326", coords = c("Longitude", "Latitude"))
  # transform pts to same crs
  pts <- st_transform(pts, poly_crs)
  # filter polygons for those that are intersected by reservoir locs
  select_polygons <- shps[pts, ]
  write_sf(select_polygons, "a_locs_poly_setup/out/NW_polygons.gpkg")
  select_polygons
}