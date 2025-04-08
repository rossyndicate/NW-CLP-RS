#' @title Export a csv from a {sf} object
#' 
#' @description
#' Function to convert a {sf} of points to a .csv, retaining the Latitude and 
#' Longitude measures
#' 
#' @param points a {sf} points object 
#' @param filename a text string that will become the filename of the output .csv
#' @returns filepath for new .csv file that contains the point tibble with
#' Latitude and Longitude measures in EPSG:4326 (WGS84)
#' 
#' 
points_to_csv <- function(points, filename){
  if(st_crs(points) != "EPSG:4326") {
    points <- st_transform(points, "EPSG:4326")
  }
  st_coordinates(points)
  points_lat_long <- points %>% 
    rowwise() %>% 
    mutate(Latitude = (geometry[[1]][2]),
           Longitude = (geometry[[1]][1])) %>% 
    st_drop_geometry() %>% 
    rowid_to_column() 
  write_csv(points_lat_long, paste0("a_locs_poly_setup/out/", filename, ".csv"))
  paste0("a_locs_poly_setup/out/", filename, ".csv")
}