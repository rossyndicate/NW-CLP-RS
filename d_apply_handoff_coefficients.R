# Source functions for this {targets} list
tar_source("d_apply_handoff_coefficients/src/")

# Apply handoff coefficients to dataset(s) -------------

# This pipeline applies handoff coefficients, flags for band values outside of
# the handoff inputs, exports the analysis-ready file(s), and uploads them to 
# the ROSSyndicate Drive.

# create folder structure
suppressWarnings({
  dir.create("d_apply_handoff_coefficients/mid/")
})

d_targets_list <- list(
  # make a list of the filtered DSWE1 files from the b group
  tar_target(
    name = d_filtered_DSWE1_data,
    command = {
      b_QAQC_filtered_data
      list.files("b_historical_RS_data_collation/out/",
                         full.names = TRUE) %>% 
        .[grepl("filtered", .)] %>% 
        .[grepl("DSWE1", .)] %>% 
        .[grepl(Sys.getenv("collation_date"), .)]
    }
  ),
  # using the coefficients from the c group (which were DSWE1 only), we"ll
  # apply those to our DSWE1 datasets
  # first for the relative-to-LS7 values
  tar_target(
    name = d_DSWE1_handoffs_to7,
    command = apply_handoffs_to7(c_collated_handoff_coefficients, d_filtered_DSWE1_data),
    packages = c("tidyverse", "feather"),
    pattern = map(d_filtered_DSWE1_data)
  ),
  # and do it for the relative-to-LS8 values
  tar_target(
    name = d_DSWE1_handoffs_to8,
    command = apply_handoffs_to8(c_collated_handoff_coefficients, d_filtered_DSWE1_data),
    packages = c("tidyverse", "feather"),
    pattern = map(d_filtered_DSWE1_data)
  ),
  # and now compile them so that all data: raw, corrected to LS7, and corrected
  # to LS8 are all stored together
  tar_target(
    name = d_combined_DSWE1_corrected,
    command = {
      d_DSWE1_handoffs_to7
      d_DSWE1_handoffs_to8
      collate_DSWE1_corrected_files(Sys.getenv("collation_date"))
      },
    packages = c("tidyverse", "feather")
  ),
  # list the file names to map over
  tar_target(
    name = d_DSWE1_corrected_file_list,
    command = {
      d_combined_DSWE1_corrected
      list.files("d_apply_handoff_coefficients/out/",
                 pattern = Sys.getenv("collation_date"),
                 full.names = TRUE)
    }
  ),
  # using the collated file names from the previous target, create figures for
  # quick comparison of the raw, LS7 corrected, and LS8 corrected values
  tar_target(
    name = d_Rrs_DSWE1_correction_figures,
    command = make_Rrs_correction_figures(d_DSWE1_corrected_file_list,
                                          c_5_9_band_list),
    packages = c("tidyverse", "feather", "cowplot"),
    pattern = map(d_DSWE1_corrected_file_list)
  )
)
