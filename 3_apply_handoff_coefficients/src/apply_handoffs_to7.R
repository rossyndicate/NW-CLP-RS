apply_handoffs_to7 <- function(coefficients, data_filepath) {
  # check for dir
  dir.create('3_apply_handoff_coefficients/out/')
  
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
  # filter coefficients for those that correct to LS7 and reformat
  coeff <- coefficients %>% 
    rename(mission = sat_corr) %>%  
    filter(sat_to == 'LANDSAT_7') %>% 
    select(band:mission) %>% 
    pivot_longer(names_to = 'coeff',
                 values_to = 'value',
                 cols = c('intercept', 'B1', 'B2', 'min_in_val', 'max_in_val')) %>% 
    pivot_wider(names_from = c('band', 'coeff'),
                values_from = 'value')
  # we assume the handoff is comparable for LS 9 -> 7 as LS 8. Because there are
  # so few values, we apply the 8 -> 7 handoff for LS 9
  L9_dummy <- coeff %>% 
    filter(mission == 'LANDSAT_8') %>% 
    mutate(mission = 'LANDSAT_9')
  coeff <- full_join(coeff, L9_dummy)
  # join data with coefficients by mission - LS 7 will be blank, as will LS 4
  data <- full_join(data, coeff)
  # calculate corr7 value - that is the Rrs in relative corrected to LS7
  data_out <- data %>% 
    mutate(med_Blue_corr7 = med_Blue_intercept + med_Blue_B1*med_Blue + med_Blue_B2*med_Blue^2,
           med_Red_corr7 = med_Red_intercept + med_Red_B1*med_Red + med_Red_B2*med_Red^2,
           med_Green_corr7 = med_Green_intercept + med_Green_B1*med_Green + med_Green_B2*med_Green^2,
           med_Nir_corr7 = med_Nir_intercept + med_Nir_B1*med_Nir + med_Nir_B2*med_Nir^2,
           med_Swir1_corr7 = med_Swir1_intercept + med_Swir1_B1*med_Swir1 + med_Swir1_B2*med_Swir1^2,
           med_Swir2_corr7 = med_Swir2_intercept + med_Swir2_B1*med_Swir2 + med_Swir2_B2*med_Swir2^2) %>%
    # there LS7 values *are* LS7-correct 
    mutate(med_Blue_corr7 = ifelse(mission == 'LANDSAT_7', med_Blue, med_Blue_corr7),
           med_Red_corr7 = ifelse(mission == 'LANDSAT_7', med_Red, med_Red_corr7),
           med_Green_corr7 = ifelse(mission == 'LANDSAT_7', med_Green, med_Green_corr7),
           med_Nir_corr7 = ifelse(mission == 'LANDSAT_7', med_Nir, med_Nir_corr7),
           med_Swir1_corr7 = ifelse(mission == 'LANDSAT_7', med_Swir1, med_Swir1_corr7),
           med_Swir2_corr7 = ifelse(mission == 'LANDSAT_7', med_Swir2, med_Swir2_corr7)) %>% 
    # and add flags for corrections outside of input data
    mutate(flag_Blue_7 = ifelse((med_Blue < med_Blue_max_in_val & 
                                  med_Blue > med_Blue_min_in_val) |
                                  is.na(med_Blue_max_in_val),
                               '', 
                               'extreme value'),
           flag_Red_7 = ifelse((med_Red < med_Red_max_in_val & 
                                  med_Red > med_Red_min_in_val) |
                                 is.na(med_Red_max_in_val),
                               '', 
                               'extreme value'),
           flag_Green_7 = ifelse((med_Green < med_Green_max_in_val & 
                                    med_Green > med_Green_min_in_val) |
                                   is.na(med_Green_max_in_val),
                                 '', 
                                 'extreme value'),
           flag_Nir_7 = ifelse((med_Nir < med_Nir_max_in_val & 
                                  med_Nir > med_Nir_min_in_val) |
                                  is.na(med_Nir_max_in_val),
                               '', 
                               'extreme value'),
           flag_Swir1_7 = ifelse((med_Swir1 < med_Swir1_max_in_val & 
                                    med_Swir1 > med_Swir1_min_in_val) |
                                   is.na(med_Swir1_max_in_val),
                                 '', 
                                 'extreme value'),
           flag_Swir2_7 = ifelse((med_Swir2 < med_Swir2_max_in_val & 
                                    med_Swir2 > med_Swir2_min_in_val) |
                                   is.na(med_Swir2_max_in_val),
                                 '', 
                                 'extreme value'))
  #remove those pesky extra columns from the coefficient file
  data_out <- data_out %>% select(-c(med_Blue_intercept:med_Swir2_B2))
  
  #save the file!
  write_feather(data_out, 
                file.path('3_apply_handoff_coefficients/out/',
                          paste0(file_prefix, 
                                 "_filtered_corr7_",
                                 DSWE, "_",
                                 type, "_v",
                                 file_suffix)))
}
