
add_spatial_information <- function(data_file, spatial_info, data_type) {
  # get some info for parsing out the data to be joined
  filename <- str_split(data_file, "/")[[1]][4]
  # break out file prefix
  file_prefix <- str_split(filename, "_")[[1]][1]
  # and file type so we can merge files of the same type
  file_type <- str_split(filename, "_")[[1]][2]
  # and DSWE type
  DSWE <- str_split(filename, '_')[[1]][3]
  # if data type is point, these will map 1:1 with row id
  if (data_type == 'point') {
    # left join with spatial info
    data <- read_feather(data_file) %>% 
      mutate(rowid = as.numeric(rowid)) %>% 
      left_join(., spatial_info)
  } 
  # however, if it's a polygon, the rowid is the equivalent of rowid - 1 (thanks
  # python/r)
  if (data_type == 'poly') {
    data <- read_feather(data_file) %>% 
      mutate(rowid = as.numeric(rowid) +1)
    spatial_info <- spatial_info %>% 
      rowid_to_column() %>% 
      st_drop_geometry()
    data <- left_join(data, spatial_info)
  }
  #save the file
  write_feather(data, 
                file.path('4_separate_NW_CLP_data/out/',
                          paste0(file_prefix,
                                 '_', file_type,
                                 '_', DSWE,
                                 '_for_analysis_',
                                 Sys.getenv('collate_version'),
                                 '.feather')
                                ))
  #return the filepath
  file.path('4_separate_NW_CLP_data/out/',
            paste0(file_prefix,
                   '_', file_type,
                   '_', DSWE,
                   '_for_analysis_',
                   Sys.getenv('collate_version'),
                   '.feather'))
}