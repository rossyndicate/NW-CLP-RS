get_HUC_polygons <-  function(HUC, resolution, minimum_sqkm, name) {
  if (dir.exists('0_locs_poly_setup/out/') == FALSE) {
    dir.create('0_locs_poly_setup/out/')
  }
  huc_type = paste0('huc', nchar(HUC))
  if (resolution == 'HR') {
  } else {
    huc_poly <- get_huc(id = HUC08, type = huctype)
    huc_wbd <- get_waterbodies(AOI = huc_poly) %>% 
      filter(areasqkm >= minimum_sqkm)
    write_sf(huc_wbd, paste0('0_locs_poly_setup/', huc_type, '_', HUC, '_NHDPlusV2_polygons.shp'))
    return(paste0('0_locs_poly_setup/', huc_type, '_', HUC, '_NHDPlusV2_polygons.shp'))
  }
}
