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
