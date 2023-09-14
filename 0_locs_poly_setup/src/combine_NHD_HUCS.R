#' @title combine_NHD_HUCS
#' Function to combine NHD huc4 waterbody files into a single file. This 
#' function automatically grabs any files with 'huc4' in the name within the 
#' 'out' folder in the p0... directory. These .gpkg files were created in the 
#' p0_get_NW_NHD target
#' 
#' @returns {sf} object containing all polygons from the unique huc4 gpkg files
#' 
#' 
combine_NHD_HUCS <- function() {
  huc4_poly_files <- list.files('0_locs_poly_setup/out/', full.names = TRUE) %>% 
    .[grepl('huc4', .)]
  map_dfr(huc4_poly_files, read_sf)
}