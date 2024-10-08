#' @title Add scene metadata to RS band summary data
#' 
#' @description
#' Function to combine a reduced set of scene metadata with the upstream collated RS
#' data for downstream use
#'
#' @param yaml contents of the yaml .csv file
#' @param file_prefix specified string that matches the file group to collate
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' @returns silently creates collated .feather files from 'mid' folder and 
#' dumps into 'data'
#' 
#' 
add_metadata <- function(yaml,
                         file_prefix, 
                         version_identifier) {
  
  files <- list.files(file.path("data_acquisition/mid/"),
                      pattern = file_prefix,
                      full.names = TRUE) %>% 
    # and grab the right version
    .[grepl(version_identifier, .)]
  
  # load the metadata
  meta_file <- files[grepl("metadata", files)]
  metadata <- read_feather(meta_file)
  # do some metadata formatting
  metadata_light <- metadata %>% 
    # Landsat 4-7 and 8/9 store image quality differently, so here, we"re harmonizing this.
    mutate(IMAGE_QUALITY = if_else(is.na(IMAGE_QUALITY), 
                                   IMAGE_QUALITY_OLI, 
                                   IMAGE_QUALITY)) %>% 
    rename(system.index = `system:index`) %>% 
    select(system.index, 
           WRS_PATH, 
           WRS_ROW, 
           "mission" = SPACECRAFT_ID, 
           "date" = DATE_ACQUIRED, 
           "UTC_time" = SCENE_CENTER_TIME, 
           CLOUD_COVER,
           IMAGE_QUALITY, 
           IMAGE_QUALITY_TIRS, 
           SUN_AZIMUTH, 
           SUN_ELEVATION) 
  
  # get extent from yaml file
  extent <- unlist(str_split(yaml$extent, "\\+"))
  
  # make sure directory exists, create it if not
  if(!dir.exists(file.path("data_out/"))) {
    dir.create(file.path("data_out/"))
  }
  
  map(extent, function(e){
    # store extent as string present in file names
    if (e == "site") {
      ext <- "point"
    } else if (e == "polycenter") {
      ext <- "center"
    } else {
      ext <- e
    }
    
    # get file using ext
    file <- files[grepl(ext, files)]
    # load file
    df <- read_feather(file) %>% 
      mutate(mission = case_when(grepl("LT04", `system:index`) ~ "LANDSAT_4",
                                 grepl("LT05", `system:index`) ~ "LANDSAT_5",
                                 grepl("LE07", `system:index`) ~ "LANDSAT_7",
                                 grepl("LC08", `system:index`) ~ "LANDSAT_8",
                                 grepl("LC09", `system:index`) ~ "LANDSAT_9",
                                 TRUE ~ NA_character_)) 
    
    if (e == "site") {
      spatial_info <- read_csv(file.path(yaml$data_dir,
                                         yaml$location_file)) %>% 
        rename(r_id = yaml$unique_id)%>% 
        mutate(r_id = as.character(r_id))
    } else if (e == "polycenter") {
      if (yaml$polygon) { 
        spatial_info <- read_csv("data_acquisition/out/user_polygon_withrowid.csv") %>% 
          mutate(r_id = as.character(r_id))
      } else {
        spatial_info <- read_csv("data_acquisition/out/NHDPlus_polygon_centers.csv") %>% 
          mutate(r_id = as.character(r_id))
      }
    } else if (e == "polygon") {
      if (yaml$polygon) {
        spatial_info <- read_sf(file.path(yaml$poly_dir,
                                          yaml$poly_file)) %>% 
          st_drop_geometry() %>% 
          mutate(r_id = as.character(r_id))
      } else {
        spatial_info <- read_csv('data_acquisition/out/NHDPlus_stats_lakes.csv') %>% 
          mutate(r_id = as.character(r_id))
      }
    }
    
    # format system index for join - right now it has a rowid and the unique LS id
    # could also do this rowwise, but this method is a little faster
    df$r_id <- map_chr(.x = df$`system:index`, 
                       function(.x) {
                         parsed <- str_split(.x, '_')
                         last(unlist(parsed))
                       })
    df$system.index <- map_chr(.x = df$`system:index`, 
                               #function to grab the system index
                               function(.x) {
                                 parsed <- str_split(.x, '_')
                                 str_len <- length(unlist(parsed))
                                 parsed_sub <- unlist(parsed)[1:(str_len-1)]
                                 str_flatten(parsed_sub, collapse = '_')
                               })
    
    # dswe info is stored differently in each mission group because of character length
    # so grab out mission-specific dswe info and use that to define dswe
    mission_dswe <- df %>% 
      group_by(mission) %>% 
      slice(1) %>% 
      ungroup()
    dswe_loc <- as_tibble(str_locate(mission_dswe$source, "DSWE")) %>% 
      rowid_to_column() %>% 
      left_join(., mission_dswe %>% rowid_to_column()) %>% 
      select(rowid, mission, start, end) %>% 
      mutate(end = end + 2)
    
    df <- df %>% 
      select(-`system:index`) %>% 
      left_join(., metadata_light) %>% 
      left_join(., dswe_loc) %>% 
      mutate(DSWE = str_sub(source, start, end), .by = mission) %>% 
      mutate(DSWE = str_remove(DSWE, "_")) %>%
      left_join(., spatial_info)
    
    # break out the DSWE 1 data
    if (nrow(df %>% filter(DSWE == 'DSWE1')) > 0) {
      DSWE1 <- df %>%
        filter(DSWE == 'DSWE1')
      write_feather(DSWE1,
                    file.path("data_out/",
                              paste0(file_prefix,
                                     "_collated_DSWE1_",
                                     ext,
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    } 
    
    # and the DSWE 1a data
    if (nrow(df %>% filter(DSWE == 'DSWE1a')) > 0) {
      DSWE1a <- df %>%
        filter(DSWE == 'DSWE1a')
      write_feather(DSWE1a,
                    file.path("data_out",
                              paste0(file_prefix,
                                     "_collated_DSWE1a_",
                                     ext, 
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    }
    
    # and the DSWE 3 data
    if (nrow(df %>% filter(DSWE == 'DSWE3')) > 0) {
      DSWE3 <- df %>%
        filter(DSWE == 'DSWE3')
      write_feather(DSWE3,
                    file.path("data_out",
                              paste0(file_prefix,
                                     "_collated_DSWE3_",
                                     ext,
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    }
  })
  
  # return the list of files from this process
  list.files("data_out",
             pattern = file_prefix,
             full.names = TRUE) %>% 
    #but make sure they are the specified version
    .[grepl(version_identifier, .)] %>% 
    .[!grepl('filtered', .)]
  
}
