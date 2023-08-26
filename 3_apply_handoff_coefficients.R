# Source functions for this {targets} list
tar_source("3_apply_handoff_coefficients/src/")

# Apply handoff coefficients to dataset(s) -------------

# This group of functions applies the handoff coefficients to dataset(s), flags for band 
# values outside of the handoff inputs that created the correction coefficients,
# and saves the analysis-ready file(s). Additionally, figures are created to 
# compare the raw, LS7-corrected, and LS8-corrected figures.

p3_targets_list <- list(
  # make a list of the filtered DSWE1 files from the p1 group
  tar_target(
    name = p3_filtered_DSWE1_data,
    command = {
      p1_QAQC_filter_data
      list.files("1_historical_RS_data_collation/out/",
                         full.names = TRUE) %>% 
        .[grepl("filtered", .)] %>% 
        .[grepl("DSWE1", .)] %>% 
        .[grepl("v2023-08-17", .)]
    }
  ),
  # using the coefficients from the p2 group (which were DSWE1 only), we"ll
  # apply those to our DSWE1 datasets
  # first for the relative-to-LS7 values
  tar_target(
    name = p3_apply_DSWE1_handoffs_to7,
    command = apply_handoffs_to7(p2_collated_handoff_coefficients, p3_filtered_DSWE1_data),
    packages = c("tidyverse", "feather"),
    pattern = map(p3_filtered_DSWE1_data)
  ),
  # and do it for the relative-to-LS8 values
  tar_target(
    name = p3_apply_DSWE1_handoffs_to8,
    command = apply_handoffs_to8(p2_collated_handoff_coefficients, p3_filtered_DSWE1_data),
    packages = c("tidyverse", "feather"),
    pattern = map(p3_filtered_DSWE1_data)
  ),
  # and now compile them so that all data: raw, corrected to LS7, and corrected
  # to LS8 are all stored together
  tar_target(
    name = p3_combine_DSWE1_corrected,
    command = {
      p3_apply_DSWE1_handoffs_to7
      p3_apply_DSWE1_handoffs_to8
      collate_DSWE1_corrected_files("v2023-08-17")
      },
    packages = c("tidyverse", "feather")
  ),
  # list the file names to map over
  tar_target(
    name = p3_DSWE1_corrected_file_list,
    command = {
      p3_combine_DSWE1_corrected
      list.files("3_apply_handoff_coefficients/out/",
                 full.names = TRUE)
    }
  ),
  # using the collated file names from the previous target, create figures for
  # quick comparison of the raw, LS7 corrected, and LS8 corrected values
  tar_target(
    name = p3_make_DSWE1_correction_figures,
    command = make_Rrs_correction_figures(p3_DSWE1_corrected_file_list),
    packages = c("tidyverse", "feather", "cowplot"),
    pattern = map(p3_DSWE1_corrected_file_list)
  )
)