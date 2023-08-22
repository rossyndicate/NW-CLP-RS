get_polygons <-  function(HUC, minimum_sqkm) {
  #check for out folder, create if not present
  if (dir.exists('0_locs_poly_setup/out/') == FALSE) {
    dir.create('0_locs_poly_setup/out/')
  }
  
  # create temp directory for download of HR .gdb files
  try(dir.create('tmp'))
  #set timeout for longer per issue #341: https://github.com/DOI-USGS/nhdplusTools/issues
  options(timeout = 60000)

  huc_type = paste0('huc', nchar(HUC))
  # and download the HUC4 HR file
  huc4 <- str_sub(HUC, 1, 4)
  
  # check to see if huc4 exists yet
  file_list <- list.files('0_locs_poly_setup/out/', pattern = c('^huc4.*\\.gpkg$'))
  if (length(file_list) == 0 | any(!grepl(huc4, file_list))) {
    fp <- download_nhdplushr(nhd_dir = 'tmp', huc4)
    # open the waterbody and catchment files
    wbd <- get_nhdplushr(fp, layers = 'NHDWaterbody') %>% 
      bind_rows() %>% 
      st_as_sf() %>% 
      st_make_valid() #make sure they are complete polygons
    catch <- get_nhdplushr(fp, layers = paste0('WBDHU', nchar(HUC))) %>% 
      bind_rows() %>% 
      filter(.[[12]] == HUC) %>%  #filter the 12th column for the huc provided
      st_as_sf() %>% 
      st_make_valid()
    #filter for wbd in catchment
    huc_wbd <- wbd[catch,] 
    huc_wbd <- huc_wbd %>% 
      filter(AreaSqKM >= minimum_sqkm)
    write_sf(huc_wbd, paste0('0_locs_poly_setup/out/', huc_type, '_', HUC, '_NHDPlusHR_polygons.gpkg'), append = F)
  }
  return(paste0('0_locs_poly_setup/out/', huc_type, '_', HUC, '_NHDPlusHR_polygons.gpkg'))
  # remove tmp folder and contents
  unlink('tmp', recursive = T)
}
