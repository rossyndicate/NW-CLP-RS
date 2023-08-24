# Source functions for this {targets} list
tar_source("1_historical_RS_data_collation/src/")

# Download and process GEE output from historical pulls -------------

# this pipeline collates all of the GEE output files for the NW and CLP projects
# Note: this portion of the workflow is dependent on the successful run of two 
# branches of the Landsat_C2_SRST repository: nw-poudre-historical and nw-er3z21-historical.
# At this time, this is run outside of the {targets} workflow presented here. 

p1_targets_list <- list(
  tar_target(
    name = p1_download_historical_NW_CLP,
    command = {
      p0_collated_pts_file
      download_csvs_from_drive("LS-C2-SR-NW_CLP_-Poly-Points-v2023-08-17")
      },
    packages = c("tidyverse", "googledrive")
  ),
  tar_target(
    name = p1_download_historical_regional,
    command = {
      p0_collated_pts_file
      download_csvs_from_drive("LS-C2-SR-RegionalPoints-v2023-08-17")
      },
    packages = c("tidyverse", "googledrive")
  ),
  tar_target(
    name = p1_collate_historical_NW_CLP,
    command = {
      p1_download_historical_NW_CLP
      collate_csvs_from_drive("NW-Poudre-Historical", "v2023-08-17")
      },
    packages = c("tidyverse", "feather")
  ),
  tar_target(
    name = p1_collate_historical_regional,
    command = {
      p1_download_historical_regional
      collate_csvs_from_drive("NW-Poudre-Regional", "v2023-08-17")
      },
    packages = c("tidyverse", "feather")
  ),
  tar_target(
    name = p1_combined_regional_metadata_data,
    command = {
      p1_collate_historical_regional
      combine_metadata_with_pulls("NW-Poudre-Regional", "v2023-08-17")
    },
    packages = c("tidyverse", "feather")
  ),
  tar_target(
    name = p1_combined_NW_CLP_metadata_data,
    command = {
      p1_collate_historical_NW_CLP
      combine_metadata_with_pulls("NW-Poudre-Historical", "v2023-08-17")
    },
    packages = c("tidyverse", "feather")
  ),
  tar_target(
    name = p1_collated_files,
    command = {
      p1_combined_NW_CLP_metadata_data
      p1_combined_regional_metadata_data
      list.files('1_historical_RS_data_collation/out/', 
                 full.names = T,
                 pattern = 'v2023-08-17') %>% 
        .[grepl('collated', .)]
      }
  ),
  tar_target(
    name = p1_QAQC_filter_data,
    command = baseline_QAQC_RS_data(p1_collated_files),
    packages = c("tidyverse", "feather"),
    pattern = map(p1_collated_files)
  )
)