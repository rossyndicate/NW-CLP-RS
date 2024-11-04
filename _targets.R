# Load packages required to define the pipeline:
library(targets)
library(tarchetypes) # Load other packages as needed.

# Set target options:
tar_option_set(
  packages = c("tidyverse", "sf")
)

# source functions
tar_source(files = c(
  "a_locs_poly_setup.R",
  "b_site_RS_data_acquisition.R",
  "c_regional_RS_data_acquisition.R"
))

# Full targets list 
c(a_locs_poly_setup,
  b_site_RS_data,
  c_regional_RS_data
  )
