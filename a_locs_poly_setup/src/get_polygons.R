#' @title Get waterbodies within HUC4 from NHD
#' 
#' @description
#' Function to download NHDPlusHR HUC-4 geopackages that contain all NHD layers from 
#' a HUC. Filter for waterbodies larger than a minimum area using the AreaSqKm
#' column in the NHD file.
#' 
#' @param HUC a 4-digit or 8-digit HUC value
#' @param minimum_sqkm a numeric threshold value to filter waterbodies, in square 
#' kilometers; if specified as NA_real_, no filter will be applied
#' @param ftypes a list of FTYPE (3-digit) values to filter the waterbodies. 390 
#' = lake/pond; 436 = res; 361 = playa
#' @returns filepath for new {sf} file that contains the filtered polygons
#' 
#' 
#' 
get_polygons <-  function(HUC, minimum_sqkm, ftypes) {
  #set timeout for longer per issue #341: https://github.com/DOI-USGS/nhdplusTools/issues
  options(timeout = 60000)
  
  huc_type <- paste0("huc", nchar(HUC))
  # and download the HUC4 HR file
  h4 <- str_sub(HUC, 1, 4)
  h8 <- HUC
  
  # check to see if file exists yet, this is done via huc type, since the file naming
  # conventions are a bit different
  if (huc_type == "huc4") {
    file_list <- list.files("a_locs_poly_setup/out/", pattern = c("^huc4.*\\.gpkg$"))
  } else {
    file_list <- list.files("a_locs_poly_setup/out/", pattern = c("^huc8.*\\.gpkg$"))
  }
  if (length(file_list) == 0 | all(!grepl(HUC, file_list))) {
    fp <- download_nhdplushr(nhd_dir = "a_locs_poly_setup/nhd/", h4)
    # open the waterbody and catchment files
    wbd <- get_nhdplushr(fp, layers = "NHDWaterbody") %>% 
      bind_rows() %>% 
      # clean up the names for later... stinking HR
      clean_names(case = "snake") %>% 
      st_as_sf() %>% 
      st_make_valid() # make sure they are complete polygons
    catch <- get_nhdplushr(fp, layers = paste0("WBDHU", nchar(HUC))) %>% 
      bind_rows() %>% 
      # clean up the names for later... stinking HR
      clean_names(case = "snake")  %>%  
      st_as_sf() %>% 
      st_make_valid()
    # filter to the huc(s) of interest based on huc type
    if (huc_type == "huc4") {
      catch <- catch %>% 
        filter(huc4 == h4)
    } else {
      catch <- catch %>% 
        filter(huc8 == h8)
    }
    #filter for wbd in catchment, minimum size, and waterbody FTYPE
    huc_wbd <- wbd[catch,] 
    huc_wbd <- huc_wbd %>% 
      filter(area_sq_km >= minimum_sqkm & ftype %in% ftypes) %>% 
      select(any_of(c("permanent_identifier", "comid", "resolution", "gnis_id", 
                      "gnis_name", "area_sq_km", "reachcode", "ftype", "fcode", 
                      "vpuid")))
    write_sf(huc_wbd, paste0("a_locs_poly_setup/out/", huc_type, "_", HUC, "_NHDPlusHR_polygons.gpkg"), append = F)
  }
  return(paste0("a_locs_poly_setup/out/", huc_type, "_", HUC, "_NHDPlusHR_polygons.gpkg"))
}
