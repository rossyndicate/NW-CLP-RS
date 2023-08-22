get_AOI_centers <- function(polygons) {
  # create an empty tibble
  cc_df = tibble(
    Permanent_Identifier = character(),
    Longitude = numeric(),
    Latitude = numeric(),
    dist = numeric()
  )
  # for each polygon, calculate a center. Because sf doesn't map easily, using a loop.
  for (i in 1:length(polygons[[1]])) {
    coord = polygons[i,] %>% st_coordinates()
    x = coord[,1]
    y = coord[,2]
    poly_poi = poi(x,y, precision = 0.00001)
    cc_df  <- cc_df %>% add_row()
    cc_df$Permanent_Identifier[i] = polygons[i,]$Permanent_Identifier
    cc_df$Longitude[i] = poly_poi$x
    cc_df$Latitude[i] = poly_poi$y
    cc_df$dist[i] = poly_poi$dist
  }
  cc_df <- cc_df %>% 
    distinct()
  cc_dp <- polygons %>%
    st_drop_geometry() %>% 
    left_join(., cc_df) %>% 
    mutate(location_type = 'aoi_center')
  cc_geo <- st_as_sf(cc_dp, coords = c('Longitude', 'Latitude'), crs = st_crs(polygons))
  write_sf(cc_geo, file.path('0_locs_poly_setup/out/NW_CLP_polygon_centers.gpkg'))
  '0_locs_poly_setup/out/NW_CLP_polygon_centers.gpkg'
}
