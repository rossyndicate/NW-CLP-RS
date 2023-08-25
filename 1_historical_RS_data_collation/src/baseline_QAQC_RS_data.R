#' Function to make first-pass QAQC of the RS data
#'
#' @param filepath filepath of a collated .feather file output from the 
#' function "combine_metadatat_with_pulls.R"
#' @returns silently creates filtered .feather file from collated files in out 
#' folder and dumps filtered into out folder
#' 
#' 
baseline_QAQC_RS_data <- function(filepath) {
  collated <- read_feather(filepath)
  #get some info for saving the file
  filename <- str_split(filepath, "/")[[1]][4]
  file_prefix <- str_split(filename, "_")[[1]][1]
  file_suffix <- str_split(filename, "_v")[[1]][2]
  DSWE <- if_else(grepl("DSWE1", filepath), "DSWE1", "DSWE3")
  type <- case_when(grepl("point", filepath) ~ "point",
                          grepl("poly", filepath) ~ "poly",
                          grepl("center", filepath) ~ "center")
  # do the actual QAQC pass and save the filtered file
  collated %>%
    filter(IMAGE_QUALITY >= 7, pCount_dswe1 >= 10) %>% 
    filter_at(vars(med_Red, med_Green, med_Blue, med_Nir, med_Swir1, med_Swir2),
              all_vars(.<0.2 & .>-0.01)) %>% 
    write_feather(file.path("1_historical_RS_data_collation/out/",
                            paste0(file_prefix, 
                                   "_filtered_",
                                   DSWE, "_",
                                   type, "_v",
                                   file_suffix
                                   )
                            )
                  )
}
