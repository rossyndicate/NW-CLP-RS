#' @title subset the RS summary data to those belonging to specific ROSS projects
#' 
#' @description
#' This function splits data into specified data groups, as defined in group -a-
#' 
#' @param data_file .feather filepath; remote sensing summary data, specifically those that
#' have had the handoff coefficient applied. 
#' @param data_grp character string; in this case, "NW" or "CLP", but could be any
#' data group specified in group -a-
#' 
#' @returns filepath of resulting .feather file
#' 
#' 
subset_file_by_data_group <- function(data_file, data_grp) {
  data <- read_feather(data_file)
  subset <- data %>% 
    filter(grepl(data_grp, data_group))
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
                                 Sys.getenv('collate_version'),
                                 '.feather')))
  file.path('e_separate_NW_CLP_data/out/',
            paste0(data_grp,
                   '_', file_type,
                   '_', DSWE,
                   '_for_analysis_',
                   Sys.getenv('collate_version'),
                   '.feather'))
}
