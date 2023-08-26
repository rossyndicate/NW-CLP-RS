# Source functions for this {targets} list
tar_source("4_separate_NW_CLP_data/src/")

# Separate NW and CLP data and save to Drive -------------

# This set of functions join the location information back with the collated 
# data, filters for NW and CLP reservoirs/lakes, and then saves the files in
# the ROSSyndicate Google Drive

p4_targets_list <- list(
  
  