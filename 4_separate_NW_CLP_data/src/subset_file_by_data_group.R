subset_file_by_data_group <- function(data_file, data_grp) {
  data <- read_feather(data_file)
  subset <- data %>% 
    filter(data_group == !!data_grp)
  # get some info for parsing out the data to be joined
  filename <- str_split(data_file, "/")[[1]][4]
  # break out file prefix
  file_prefix <- str_split(filename, "_")[[1]][1]
  # and file type so we can merge files of the same type
  file_type <- str_split(filename, "_")[[1]][2]
  # and DSWE type
  DSWE <- str_split(filename, '_')[[1]][3]
  write_feather(subset,
                file.path('4_separate_NW_CLP_data/out/',
                          paste0(data_grp,
                                 '_', file_type,
                                 '_', DSWE,
                                 '_for_analysis_',
                                 Sys.getenv('collate_version'),
                                 '.feather')))
  file.path('4_separate_NW_CLP_data/out/',
            paste0(data_grp,
                   '_', file_type,
                   '_', DSWE,
                   '_for_analysis_',
                   Sys.getenv('collate_version'),
                   '.feather'))
}
