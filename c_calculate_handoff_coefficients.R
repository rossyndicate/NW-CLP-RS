# Source functions for this {targets} list
tar_source("c_calculate_handoff_coefficients/src/")

# Using the regional data, calculate handoff coefficients -------------

# This pipeline calculates handoff coefficients from the regional pull. Landsat 
# 4-7 and 8-9 surface reflectance data go through two different atmospheric 
# corrections (LEDAPS and LaSRC). Additionally, each band wavelength can vary 
# between missions. This script uses an adapted version of the methods in Topp, 
# et al. 2021 to correct for each satellite handoff, correction to LS 7 values.
# Additionally, a handoff between Landsat 7, 8, and 9 is calculated to harmonize 
# those values for workflows that do not require the entire LS record, and a
# Landsat 8/9 handoff for workflows that would benefit from a harmonized Aerosol
# band

# create folder structure
suppressWarnings({
  dir.create("c_calculate_handoff_coefficients/mid/")
  dir.create("c_calculate_handoff_coefficients/out/")
  dir.create("c_calculate_handoff_coefficients/figs/")
})

c_targets_list <- list(
  # set list of LS5-9 common bands
  tar_target(
    name = c_5_9_band_list,
    command = {
      b_QAQC_filtered_data
      c("med_Red", "med_Green", "med_Blue", "med_Nir", "med_Swir1", "med_Swir2")
    }
  ),
  # set list of common 8/9 bands
  tar_target(
    name = c_8_9_band_list,
    command = {
      b_QAQC_filtered_data
      c("med_Aerosol", "med_Red", "med_Green", "med_Blue", "med_Nir", "med_Swir1", "med_Swir2")
    }
  ),
  # track and load the filtered DSWE1 regional centers file
  tar_file_read(
    name = c_DSWE1_regional_file,
    command = {
      b_QAQC_filtered_data
      "b_historical_RS_data_collation/out/NW-Poudre-Regional_filtered_DSWE1_point_v2023-08-17.feather"
      },
    read = read_feather(!!.x),
    packages = "feather"
  ),
  # calculate handoff for LS 5 to LS 7
  tar_target(
    name = c_regional_5_7_handoff,
    command = calculate_5_7_handoff(c_DSWE1_regional_file, c_5_9_band_list),
    packages = "tidyverse",
    pattern = map(c_5_9_band_list)
  ),
  # calculate handoff for LS 8 to LS 7
  tar_target(
    name = c_regional_8_7_handoff,
    command = calculate_8_7_handoff(c_DSWE1_regional_file, c_5_9_band_list),
    packages = "tidyverse",
    pattern = map(c_5_9_band_list)
  ),
  # calculate handoff for LS 7 to LS 8
  tar_target(
    name = c_regional_7_8_handoff,
    command = calculate_7_8_handoff(c_DSWE1_regional_file, c_5_9_band_list),
    packages = "tidyverse",
    pattern = map(c_5_9_band_list)
  ),
  # calculate handoff for LS 9 to LS 8
  tar_target(
    name = c_regional_9_8_handoff,
    command = calculate_9_8_handoff(c_DSWE1_regional_file, c_8_9_band_list),
    packages = "tidyverse",
    pattern = map(c_8_9_band_list)
  ),
  # collate all the coefficient calcs into one file
  tar_target(
    name = c_make_collated_handoff_coefficients,
    command = {
      c_regional_5_7_handoff
      c_regional_8_7_handoff
      c_regional_7_8_handoff
      c_regional_9_8_handoff
      collate_handoff_coefficients()
    },
    packages = "tidyverse"
  ),
  # load and track the coefficient file
  tar_file_read(
    name = c_collated_handoff_coefficients,
    command = c_make_collated_handoff_coefficients,
    read = read_csv(!!.x),
    packages = "readr"
  )
)

  
  