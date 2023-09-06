# Source functions for this {targets} list
tar_source("1_historical_RS_data_collation/src/")

# Download and process GEE output from historical pulls -------------

# this pipeline collates all of the GEE output files for the NW and CLP projects
# Note: this portion of the workflow is dependent on the successful run of two 
# branches of the Landsat_C2_SRST repository: nw-poudre-historical and nw-er3z21-historical.
# At this time, this is run outside of the {targets} workflow presented here. 

# prep folder structure
dir.create("1_historical_RS_data_collation/in/")
dir.create("1_historical_RS_data_collation/mid/")
dir.create("1_historical_RS_data_collation/out/")

p1_targets_list <- list(
  # download the NW and CLP data from Google Drive
  tar_target(
    name = p1_download_historical_NW_CLP,
    command = {
      p0_collated_pts_file
      download_csvs_from_drive("LS-C2-SR-NW_CLP_-Poly-Points-v2023-08-17")
      },
    packages = c("tidyverse", "googledrive")
  ),
  # and do the same for the regional data
  tar_target(
    name = p1_download_historical_regional,
    command = {
      p0_collated_pts_file
      download_csvs_from_drive("LS-C2-SR-RegionalPoints-v2023-08-17")
      },
    packages = c("tidyverse", "googledrive")
  ),
  # and load/collate those data, with each type as a new feather file
  # first with the NW/CLP data
  tar_target(
    name = p1_collate_historical_NW_CLP,
    command = {
      p1_download_historical_NW_CLP
      collate_csvs_from_drive("NW-Poudre-Historical", "v2023-08-17")
      },
    packages = c("tidyverse", "feather")
  ),
  # and now for the regional data
  tar_target(
    name = p1_collate_historical_regional,
    command = {
      p1_download_historical_regional
      collate_csvs_from_drive("NW-Poudre-Regional", "v2023-08-17")
      },
    packages = c("tidyverse", "feather")
  ),
  # now, add metadata to tabular summaries and break out the DSWE 1/3 data
  # first for the regional data
  tar_target(
    name = p1_combined_regional_metadata_data,
    command = {
      p1_collate_historical_regional
      combine_metadata_with_pulls("NW-Poudre-Regional", "v2023-08-17")
    },
    packages = c("tidyverse", "feather")
  ),
  # and then for the NW/CLP data
  tar_target(
    name = p1_combined_NW_CLP_metadata_data,
    command = {
      p1_collate_historical_NW_CLP
      combine_metadata_with_pulls("NW-Poudre-Historical", "v2023-08-17")
    },
    packages = c("tidyverse", "feather")
  ),
  # make a list of the collated files to branch over
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
  # pass the QAQC filter over each of the listed files, creating filtered files
  tar_target(
    name = p1_QAQC_filter_data,
    command = baseline_QAQC_RS_data(p1_collated_files),
    packages = c("tidyverse", "feather"),
    pattern = map(p1_collated_files)
  )
)