#' Function to get huc 4 codes for a set of points from a tibble
#' 
#' @param points_csv a tibble of locations with columns Latitude and Longitude in
#' user-specified CRS
#' @param CRS EPSG code for Latitude and Longitude
#' @returns list of huc4s that contain the points in the points_csv using the 
#' NHDPlusV2
#' 
#' 
get_hucs_from_points <- function(point_csv, CRS) {
  # store csv
  pts <- point_csv
  #prep new column
  pts$huc4 <- NA_character_
  for (p in 1:nrow(pts)) {
    pt <- st_as_sf(pts[p,], coords = c('Longitude', 'Latitude'), crs = CRS)
    pts$huc4[p] = get_huc(pt, type = 'huc04')$huc4
  }
  unique(pts$huc4)
}
