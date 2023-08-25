# Source functions for this {targets} list
tar_source("2_calculate_handoff_coefficients/src/")

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

p2_targets_list <- list(
  # set list of LS5-9 common bands
  tar_target(
    name = p2_5_9_band_list,
    command = {
      p1_QAQC_filter_data
      c('med_Red', 'med_Green', 'med_Blue', 'med_Nir', 'med_Swir1', 'med_Swir2')
    }
  ),
  # set list of common 8/9 bands
  tar_target(
    name = p2_8_9_band_list,
    command = {
      p1_QAQC_filter_data
      c('med_Aerosol', 'med_Red', 'med_Green', 'med_Blue', 'med_Nir', 'med_Swir1', 'med_Swir2')
    }
  ),
  # track and load the filtered DSWE1 regional centers file
  tar_file_read(
    name = p2_DSWE1_regional_file,
    command = '1_historical_RS_data_collation/out/NW-Poudre-Regional_filtered_DSWE1_point_v2023-08-17.feather',
    read = read_feather(!!.x),
    packages = 'feather'
  ),
  tar_target(
    name = p2_calculate_5_7_handoffs,
    command = calculate_5_7_handoff(p2_DSWE1_regional_file, p2_5_9_band_list),
    packages = 'tidyverse',
    pattern = map(p2_5_9_band_list)
  )
)
  
  
  