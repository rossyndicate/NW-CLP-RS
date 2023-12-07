#' @title Apply to LS8 relative correction coefficients 
#' 
#' @description
#' Function to apply the handoff coefficients for LS 7-9 shared bands to 
#' create Rrs values relative to LS 8 Rrs
#' 
#' @param coefficients collated coefficent file created in the 
#' p2_collated_handoff_coefficients target
#' @param data_filepath filepath of filtered data that will be passed through
#' the coefficient calculations, in this workflow the data_filepath is a list
#' of filepaths created by target p3_filtered_DSWE1_data 
#' @returns silently saves a feather file with added band columns in the mid 
#' folder, corrected to LS78 Rrs
#' 
#' 
#' 
apply_handoffs_to8 <- function(coefficients, data_filepath) {
  #get some info for saving the file
  filename <- str_split(data_filepath, "/")[[1]][4]
  file_prefix <- str_split(filename, "_")[[1]][1]
  file_suffix <- str_split(filename, "_v")[[1]][2]
  DSWE <- if_else(grepl("DSWE1", data_filepath), "DSWE1", "DSWE3")
  type <- case_when(grepl("point", data_filepath) ~ "point",
                    grepl("poly", data_filepath) ~ "poly",
                    grepl("center", data_filepath) ~ "center")
  
  # read in data
  data <- read_feather(data_filepath)
  # filter coefficients for those that correct to LS8 and reformat
  coeff <- coefficients %>% 
    rename(mission = sat_corr) %>%  
    filter(sat_to == "LANDSAT_8") %>% 
    select(band:mission) %>% 
    pivot_longer(names_to = "coeff",
                 values_to = "value",
                 cols = c("intercept", "B1", "B2", "min_in_val", "max_in_val")) %>% 
    pivot_wider(names_from = c("band", "coeff"),
                values_from = "value")
  
  # join data with coefficients by mission
  # LS 8 will be blank, as will LS 4 and LS5
  data <- full_join(data, coeff)
  # calculate corr8 value - that is the Rrs in relative corrected to LS8
  data_out <- data %>% 
    mutate(med_Aerosol_corr8 = med_Aerosol_intercept + med_Aerosol_B1*med_Aerosol + med_Aerosol_B2*med_Aerosol^2,
           med_Blue_corr8 = med_Blue_intercept + med_Blue_B1*med_Blue + med_Blue_B2*med_Blue^2,
           med_Red_corr8 = med_Red_intercept + med_Red_B1*med_Red + med_Red_B2*med_Red^2,
           med_Green_corr8 = med_Green_intercept + med_Green_B1*med_Green + med_Green_B2*med_Green^2,
           med_Nir_corr8 = med_Nir_intercept + med_Nir_B1*med_Nir + med_Nir_B2*med_Nir^2,
           med_Swir1_corr8 = med_Swir1_intercept + med_Swir1_B1*med_Swir1 + med_Swir1_B2*med_Swir1^2,
           med_Swir2_corr8 = med_Swir2_intercept + med_Swir2_B1*med_Swir2 + med_Swir2_B2*med_Swir2^2) %>%
    # there LS8 values *are* LS8-correct 
    mutate(med_Aerosol_corr8 = ifelse(mission == "LANDSAT_8", med_Aerosol, med_Aerosol_corr8),
           med_Blue_corr8 = ifelse(mission == "LANDSAT_8", med_Blue, med_Blue_corr8),
           med_Red_corr8 = ifelse(mission == "LANDSAT_8", med_Red, med_Red_corr8),
           med_Green_corr8 = ifelse(mission == "LANDSAT_8", med_Green, med_Green_corr8),
           med_Nir_corr8 = ifelse(mission == "LANDSAT_8", med_Nir, med_Nir_corr8),
           med_Swir1_corr8 = ifelse(mission == "LANDSAT_8", med_Swir1, med_Swir1_corr8),
           med_Swir2_corr8 = ifelse(mission == "LANDSAT_8", med_Swir2, med_Swir2_corr8)) %>% 
    # and add flags for corrections outside of input data
    mutate(flag_Aerosol_8 = ifelse((med_Aerosol > med_Aerosol_max_in_val |
                                      med_Aerosol < med_Aerosol_min_in_val) &
                                      mission == "LANDSAT_9",
                                    "extreme value",
                                   NA_character_),
           flag_Blue_8 = ifelse((med_Blue < med_Blue_max_in_val & 
                                  med_Blue > med_Blue_min_in_val) |
                                 is.na(med_Blue_max_in_val),
                               NA_character_, 
                               "extreme value"),
           flag_Red_8 = ifelse((med_Red < med_Red_max_in_val & 
                                  med_Red > med_Red_min_in_val) |
                                 is.na(med_Red_max_in_val),
                               NA_character_, 
                               "extreme value"),
           flag_Green_8 = ifelse((med_Green < med_Green_max_in_val & 
                                    med_Green > med_Green_min_in_val) |
                                   is.na(med_Green_max_in_val),
                                 NA_character_, 
                                 "extreme value"),
           flag_Nir_8 = ifelse((med_Nir < med_Nir_max_in_val & 
                                  med_Nir > med_Nir_min_in_val) |
                                  is.na(med_Nir_max_in_val),
                               NA_character_, 
                               "extreme value"),
           flag_Swir1_8 = ifelse((med_Swir1 < med_Swir1_max_in_val & 
                                    med_Swir1 > med_Swir1_min_in_val) |
                                   is.na(med_Swir1_max_in_val),
                                 NA_character_, 
                                 "extreme value"),
           flag_Swir2_8 = ifelse((med_Swir2 < med_Swir2_max_in_val & 
                                    med_Swir2 > med_Swir2_min_in_val) |
                                   is.na(med_Swir2_max_in_val),
                                 NA_character_, 
                                 "extreme value"))
  #remove those pesky extra columns from the coefficient file
  data_out <- data_out %>% select(-c(med_Aerosol_intercept:med_Swir2_max_in_val))
  
  #save the file!
  write_feather(data_out, 
                file.path("d_apply_handoff_coefficients/mid/",
                          paste0(file_prefix, 
                                 "_filtered_corr8_",
                                 DSWE, "_",
                                 type, "_v",
                                 Sys.getenv("collate_version"))))
}
