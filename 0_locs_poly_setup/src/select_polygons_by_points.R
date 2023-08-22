select_polygons_by_points <- function(shapefiles, points){
  # load and collate all NHD polygons
  shps <- map(shapefiles, read_sf) %>% 
    bind_rows()
  # load points - crs is WGS84
  pts <- st_as_sf(points, crs = 'EPSG:4326', coords = c('Longitude', 'Latitude'))
  # get the crs of polygons
  poly_crs <- st_crs(shps)
  # transform pts to same crs
  pts <- st_transform(pts, poly_crs)
  # filter polygons for those that are intersected by reservoir locs
  select_polygons <- shps[pts, ]
  write_sf(select_polygons, '0_locs_poly_setup/out/NW_polygons.gpkg')
  '0_locs_poly_setup/out/NW_polygons.gpkg'
}