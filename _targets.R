# Load packages required to define the pipeline:
library(targets)
library(tarchetypes) # Load other packages as needed.

# Set target options:
tar_option_set(
  packages = c("tidyverse")
)

# source functions
tar_source(files = c(
  "a_locs_poly_setup.R",
  "b_historical_RS_data_collation.R",
  "c_calculate_handoff_coefficients.R",
  "d_apply_handoff_coefficients.R",
  "e_separate_NW_CLP_data.R"
))

# Full targets list 
c(a_targets_list,
  b_targets_list,
  c_targets_list,
  d_targets_list,
  e_targets_list
  )
