#' @title Add scene metadata to RS band summary data
#' 
#' @description
#' Function to combine a reduced set of scene metadata with the upstream collated RS
#' data for downstream use
#'
#' @param file_prefix specified string that matches the file group to collate
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' @param collation_identifier user-specified string to identify the output of this
#' target
#' @returns silently creates collated .feather files from 'mid' folder and 
#' dumps into 'out'
#' 
#' 
combine_metadata_with_pulls <- function(file_prefix, version_identifier, collation_identifier) {
  files <- list.files(file.path("b_historical_RS_data_collation/mid/"),
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
  
  # check for point files
  if (any(grepl("point", files))) {
    point_file <- files[grepl("point", files)]
    points <- read_feather(point_file)
    # format system index for join - right now it has a rowid and the unique LS id
    # could also do this rowwise, but this method is a little faster
    points$rowid <- map_chr(.x = points$`system:index`, 
                            function(.x) {
                              parsed <- str_split(.x, '_')
                              str_len <- length(unlist(parsed))
                              unlist(parsed)[str_len]
                            })
    points$system.index <- map_chr(.x = points$`system:index`, 
                                   #function to grab the system index
                                   function(.x) {
                                     parsed <- str_split(.x, '_')
                                     str_len <- length(unlist(parsed))
                                     parsed_sub <- unlist(parsed)[1:(str_len-1)]
                                     str_flatten(parsed_sub, collapse = '_')
                                     })
    points <- points %>% 
      select(-`system:index`) %>% 
      left_join(., metadata_light) %>% 
      mutate(DSWE = str_sub(source, -28, -24))
    # break out the DSWE 1 data
    if (nrow(points %>% filter(DSWE == 'DSWE1') > 0)) {
      DSWE1_points <- points %>%
        filter(DSWE == 'DSWE1')
      write_feather(DSWE1_points,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE1_points_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
    # and the DSWE 3 data
    if (nrow(points %>% filter(DSWE == 'DSWE3') > 0)) {
      DSWE3_points <- points %>%
        filter(DSWE == 'DSWE3')
      write_feather(DSWE3_points,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE3_points_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
  }
  
  # check to see if there are any center point data
  if (any(grepl("centers", files))) {
    center_file <- files[grepl("centers", files)]
    centers <- read_feather(center_file)
    # format system index for join - right now it has a rowid and the unique LS id
    # could also do this rowwise, but this method is a little faster
    centers$rowid <- map_chr(.x = centers$`system:index`, 
                             function(.x) {
                               parsed <- str_split(.x, '_')
                               str_len <- length(unlist(parsed))
                               unlist(parsed)[str_len]
                               })
    centers$system.index <- map_chr(.x = centers$`system:index`, 
                                    #function to grab the system index
                                    function(.x) {
                                      parsed <- str_split(.x, '_')
                                      str_len <- length(unlist(parsed))
                                      parsed_sub <- unlist(parsed)[1:(str_len-1)]
                                      str_flatten(parsed_sub, collapse = '_')
                                    })
    centers <- centers %>% 
      select(-`system:index`) %>% 
      left_join(., metadata_light) %>% 
      mutate(DSWE = str_sub(source, -28, -24))
    # break out the DSWE 1 data
    if (nrow(centers %>% filter(DSWE == 'DSWE1') > 0)) {
      DSWE1_centers <- centers %>%
        filter(DSWE == 'DSWE1')
      write_feather(DSWE1_centers,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE1_centers_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
    # and the DSWE 3 data
    if (nrow(centers %>% filter(DSWE == 'DSWE3') > 0)) {
      DSWE3_centers <- centers %>%
        filter(DSWE == 'DSWE3')
      write_feather(DSWE3_centers,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE3_centers_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
  }
  
  # check for polygons files
  if (any(grepl("poly", files))) {
    poly_file <- files[grepl("poly", files)]
    poly <- read_feather(poly_file)
    # format system index for join - right now it has a rowid and the unique LS id
    # could also do this rowwise, but this method is a little faster
    poly$rowid <- map_chr(.x = poly$`system:index`, 
                          function(.x) {
                            parsed <- str_split(.x, '_')
                            str_len <- length(unlist(parsed))
                            unlist(parsed)[str_len]
                          })
    poly$system.index <- map_chr(.x = poly$`system:index`, 
                                 #function to grab the system index
                                 function(.x) {
                                   parsed <- str_split(.x, '_')
                                   str_len <- length(unlist(parsed))
                                   parsed_sub <- unlist(parsed)[1:(str_len-1)]
                                   str_flatten(parsed_sub, collapse = '_')
                                 })
    poly <- poly %>% 
      select(-`system:index`) %>% 
      left_join(., metadata_light) %>% 
      mutate(DSWE = str_sub(source, -28, -24))
    # break out the DSWE 1 data
    if (nrow(poly %>% filter(DSWE == 'DSWE1') > 0)) {
      DSWE1_poly <- poly %>%
        filter(DSWE == 'DSWE1')
      write_feather(DSWE1_poly,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE1_poly_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
    # and the DSWE 3 data
    if (nrow(poly %>% filter(DSWE == 'DSWE3') > 0)) {
      DSWE3_poly <- poly %>%
        filter(DSWE == 'DSWE3')
      write_feather(DSWE3_poly,
                    file.path("b_historical_RS_data_collation/out/",
                              paste0(file_prefix,
                                     "_collated_DSWE3_poly_meta_v",
                                     collation_identifier,
                                     ".feather")))
    }
  }
}
