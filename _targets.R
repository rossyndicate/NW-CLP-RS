# Load packages required to define the pipeline:
library(targets)
library(tarchetypes) # Load other packages as needed.

# Set target options:
tar_option_set(
  packages = c("tidyverse")
)

# source functions
tar_source(files = c(
  '0_locs_poly_setup.R'
))

# Full targets list
c(p0_targets_list)
