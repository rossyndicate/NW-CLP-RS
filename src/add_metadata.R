#' @title Add scene metadata to RS band summary data
#' 
#' @description
#' Function to combine a reduced set of scene metadata with the upstream collated RS
#' data for downstream use
#'
#' @param yaml contents of the yaml .csv file
#' @param local_folder folder path where collated files are stored
#' @param out_folder folder path where collated files with metadata should be stored
#' @returns silently creates collated .feather files from 'local_folder' folder and 
#' dumps into specified output path 'out_folder'
#' 
#' 
add_metadata <- function(yaml,
                         local_folder,
                         out_folder) {
  
  if (!dir.exists(out_folder)) { dir.create(out_folder, recursive = TRUE) }

  file_prefix <- yaml$proj
  version_identifier <- yaml$run_date
  
  files <- list.files(local_folder,
                      pattern = file_prefix,
                      full.names = TRUE) %>% 
    # and grab the right version
    .[grepl(version_identifier, .)]
  
  # load the metadata
  meta_files <- files[grepl("metadata", files)]
  metadata <- meta_files %>% 
    map(\(m) {
      meta <- read_feather(m)
    }) %>% 
    bind_rows
  
  # get extent from yaml file
  extent <- unlist(str_split(yaml$extent, "\\+"))
  
  map(extent, function(e){
    # store extent as string present in file names
    if (e == "site") {
      ext <- "site"
    } else if (e == "polycenter") {
      ext <- "center"
    } else {
      ext <- e
    }
    
    # get files using ext
    data_files <- files[grepl(ext, files)]
    # load file
    df <- data_files %>% 
      map(\(d) read_feather(d) %>% 
            mutate(mission = case_when(grepl("LT04", `system:index`) ~ "LANDSAT_4",
                                       grepl("LT05", `system:index`) ~ "LANDSAT_5",
                                       grepl("LE07", `system:index`) ~ "LANDSAT_7",
                                       grepl("LC08", `system:index`) ~ "LANDSAT_8",
                                       grepl("LC09", `system:index`) ~ "LANDSAT_9",
                                       TRUE ~ NA_character_))
      ) %>% 
      bind_rows
    
    if (e == "site") {
      spatial_info <- read_csv(file.path(yaml$data_dir,
                                         yaml$location_file)) %>% 
        rename(r_id = yaml$unique_id)%>% 
        mutate(r_id = as.character(r_id))
    } else if (e == "polycenter") {
      if (yaml$polygon) { 
        spatial_info <- read_csv(file.path(local_folder, 
                                           "run/user_polygon_withrowid.csv")) %>% 
          mutate(r_id = as.character(r_id))
      } else {
        spatial_info <- read_csv(file.path(local_folder, 
                                           "run/NHDPlus_polygon_centers.csv")) %>% 
          mutate(r_id = as.character(r_id))
      }
    } else if (e == "polygon") {
      if (yaml$polygon) {
        spatial_info <- read_sf(file.path(yaml$poly_dir,
                                          yaml$poly_file)) %>% 
          st_drop_geometry() %>% 
          mutate(r_id = as.character(r_id))
      } else {
        spatial_info <- read_csv(file.path(local_folder, 
                                           "run/NHDPlus_stats_lakes.csv")) %>% 
          mutate(r_id = as.character(r_id))
      }
    }
    
    # format system index for join - right now it has a rowid and the unique LS id
    # could also do this rowwise, but this method is a little faster
    df$r_id <- map_chr(.x = df$`system:index`, 
                       function(.x) {
                         parsed <- str_split(.x, "_")
                         last(unlist(parsed))
                       })
    df$system.index <- map_chr(.x = df$`system:index`, 
                               #function to grab the system index
                               function(.x) {
                                 parsed <- str_split(.x, "_")
                                 str_len <- length(unlist(parsed))
                                 parsed_sub <- unlist(parsed)[1:(str_len-1)]
                                 str_flatten(parsed_sub, collapse = "_")
                               })
    
    df <- df %>% 
      left_join(., metadata) %>% 
      mutate(DSWE = str_extract(source, "DSWE\\d[a-zA-Z]?"), .by = source) %>% 
      left_join(., spatial_info)
    
    # break out the DSWE 1 data
    if (nrow(df %>% filter(DSWE == "DSWE1")) > 0) {
      DSWE1 <- df %>%
        filter(DSWE == "DSWE1")
      write_feather(DSWE1,
                    file.path(out_folder,
                              paste0(file_prefix,
                                     "_collated_DSWE1_",
                                     ext,
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    } 
    
    # and the DSWE 1a data
    if (nrow(df %>% filter(DSWE == "DSWE1a")) > 0) {
      DSWE1a <- df %>%
        filter(DSWE == "DSWE1a")
      write_feather(DSWE1a,
                    file.path(out_folder,
                              paste0(file_prefix,
                                     "_collated_DSWE1a_",
                                     ext, 
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    }
    
    # and the DSWE 3 data
    if (nrow(df %>% filter(DSWE == "DSWE3")) > 0) {
      DSWE3 <- df %>%
        filter(DSWE == "DSWE3")
      write_feather(DSWE3,
                    file.path(out_folder,
                              paste0(file_prefix,
                                     "_collated_DSWE3_",
                                     ext,
                                     "_meta_v",
                                     version_identifier,
                                     ".feather")))
    }
  })
  
  # return the list of files from this process
  list.files(out_folder,
             pattern = file_prefix,
             full.names = TRUE) %>% 
    # but make sure they are the specified version
    .[grepl(version_identifier, .)] %>% 
    # and make sure they don't contain 'filtered' which comes from a different 
    # process
    .[!grepl("filtered", .)]
  
}
