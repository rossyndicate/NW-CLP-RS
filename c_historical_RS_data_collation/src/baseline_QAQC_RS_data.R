#' @title First-pass QAQC of RS feather file
#' 
#' @description
#' Function to make first-pass QAQC of the RS data to remove any rows where the
#' image quality is below 7 (out of 10), where the dswe1 count is less than 10, 
#' or where any of the band summaries are outside of the range expected (-0.01 - 
#' 0.20 Rrs).
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
    write_feather(file.path("c_historical_RS_data_collation/out/",
                            paste0(file_prefix, 
                                   "_filtered_",
                                   DSWE, "_",
                                   type, "_v",
                                   file_suffix
                                   )
                            )
                  )
}
