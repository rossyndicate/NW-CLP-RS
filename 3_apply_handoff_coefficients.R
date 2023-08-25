# Source functions for this {targets} list
tar_source("3_apply_handoff_coefficients/src/")

# Apply handoff coefficients to dataset(s) -------------

# This pipeline applies handoff coefficients, flags for band values outside of
# the handoff inputs, exports the analysis-ready file(s), and uploads them to 
# the ROSSyndicate Drive.

p3_targets_list <- list(
  # make a list of the filtered DSWE1 files from the p1 group
  tar_target(
    name = p3_filtered_DSWE1_data,
    command = {
      p1_QAQC_filter_data
      list.files('1_historical_RS_data_collation/out/',
                         full.names = TRUE) %>% 
      .[grepl('filtered', .)] %>% 
      .[grepl('DSWE1', .)]
    }
  ),
  # using the coefficients from the p2 group (which were DSWE1 only), we'll
  # apply those to our DSWE1 datasets
  tar_target(
    name = p3_apply_DSWE1_handoffs_to7,
    command = apply_handoffs_to7(p2_collated_handoff_coefficients, p3_filtered_DSWE1_data),
    packages = c('tidyverse', 'feather'),
    pattern = map(p3_filtered_DSWE1_data)
  ),
  tar_target(
    name = p3_apply_DSWE1_handoffs_to8,
    command = apply_handoffs_to8(p2_collated_handoff_coefficients, p3_filtered_DSWE1_data),
    packages = c('tidyverse', 'feather'),
    pattern = map(p3_filtered_DSWE1_data)
  ),
  tar_target(
    name = p3_combine_DSWE1_corrected,
    command = collate_corrected_files('v2023-08-17'),
    packages = c('tidyverse', 'feather')
  )
)