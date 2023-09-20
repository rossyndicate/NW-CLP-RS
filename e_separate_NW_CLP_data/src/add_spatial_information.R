#' @title Add location information to RS summary data by rowid
#' 
#' @description
#' This function adds location info from group -a- alongside the RS data collated
#' and collected in group -b- through -c-. This also accounts for rowid numbering
#' differences between R and Python
#' 
#' @param data_file .feather filepath; remote sensing summary data, specifically those that
#' have had the handoff coefficient applied
#' @param spatial_info sf object; polygon or point file with NHD information
#' @param data_type character string; either 'poly' or 'point' indicating what 
#' type of spatial data and RS pull the collation is based on
#' 
#' @returns filepath of resulting .feather file
#' 
#' 
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
  # however, if it's a polygon, the rowid in the spatial info is the equivalent 
  # of rowid + 1 in the RS data, since those data are pulled using python, which 
  # uses base 0 instead of base 1
  if (data_type == 'poly') {
    data <- read_feather(data_file) %>% 
      mutate(rowid = as.numeric(rowid) + 1)
    spatial_info <- spatial_info %>% 
      rowid_to_column() %>% 
      st_drop_geometry()
    data <- left_join(data, spatial_info)
  }
  #save the file
  write_feather(data, 
                file.path('e_separate_NW_CLP_data/out/',
                          paste0(file_prefix,
                                 '_', file_type,
                                 '_', DSWE,
                                 '_for_analysis_',
                                 Sys.getenv('collate_version'),
                                 '.feather')
                                ))
  #return the filepath
  file.path('e_separate_NW_CLP_data/out/',
            paste0(file_prefix,
                   '_', file_type,
                   '_', DSWE,
                   '_for_analysis_',
                   Sys.getenv('collate_version'),
                   '.feather'))
}