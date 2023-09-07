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
  "c_calculate_handoff_coefficients.R"
))

# Full targets list 
c(a_locs_poly_setup_list,
  b_historical_RS_data_collation_list,
  c_calculate_handoff_coefficients_list)
