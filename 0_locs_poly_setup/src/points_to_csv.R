points_to_csv <- function(points, filename){
  points_lat_long <- points %>% 
    rowwise() %>% 
    mutate(Latitude = (geom[[1]][2]),
           Longitude = (geom[[1]][1])) %>% 
    st_drop_geometry() %>% 
    rowid_to_column()
  write_csv(points_lat_long, paste0('0_locs_poly_setup/out/', filename, '.csv'))
  paste0('0_locs_poly_setup/out/', filename, '.csv')
}