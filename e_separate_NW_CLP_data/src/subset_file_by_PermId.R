#' @title subset the RS point-type summary data to those belonging to specific 
#' ROSS projects to be further subset
#' 
#' @description
#' This function subsets point data that have been filtered for NW and CLP data
#' in the `subset_file_by_data_group` function when there is not an upstream rowid
#' or datagroup to subset by. This is currently specific to point-type data and 
#' the ROSS CLP subgroup.
#' 
#' @param data_file .feather filepath; remote sensing summary data, specifically those that
#' have had the handoff coefficient applied and have been filtered to include only
#' the point data for NW and CLP waterbodies
#' @param Perm_Id_list list of character strings; list of Permanent_Identifiers
#' from the NHDPlusHR data to subset the RS summary data by. 
#' 
#' @returns filepath of resulting .feather file
#' 
#' 
subset_file_by_PermId <- function(data_file, Perm_Id_list, data_grp) {
  data <- read_feather(data_file) 
  subset <- data %>% 
    filter(Permanent_Identifier %in% !!Perm_Id_list)
  # get some info for parsing out the data to be joined
  filename <- str_split(data_file, "/")[[1]][4]
  # break out file prefix
  file_prefix <- str_split(filename, "_")[[1]][1]
  # and file type so we can merge files of the same type
  file_type <- str_split(filename, "_")[[1]][2]
  # and DSWE type
  DSWE <- str_split(filename, '_')[[1]][3]
  write_feather(subset,
                file.path('e_separate_NW_CLP_data/out/',
                          paste0(data_grp,
                                 '_', file_type,
                                 '_', DSWE,
                                 '_for_analysis_',
                                 Sys.getenv('collation_date'),
                                 '.feather')))
  file.path('e_separate_NW_CLP_data/out/',
            paste0(data_grp,
                   '_', file_type,
                   '_', DSWE,
                   '_for_analysis_',
                   Sys.getenv('collation_date'),
                   '.feather'))}