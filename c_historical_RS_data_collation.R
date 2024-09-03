# Source functions for this {targets} list
tar_source("c_historical_RS_data_collation/src/")

# Download and process GEE output from historical pulls -------------

# this pipeline collates all of the GEE output files for the NW and CLP projects
# Note: this portion of the workflow is dependent on the successful run of two 
# branches of the Landsat_C2_SRST repository: nw-poudre-historical and nw-er3z21-historical.
# At this time, this is run outside of the {targets} workflow presented here. 

# prep folder structure
suppressWarnings({
  dir.create("c_historical_RS_data_collation/in/")
  dir.create("c_historical_RS_data_collation/mid/")
  dir.create("c_historical_RS_data_collation/out/")
})

c_targets_list <- list(
  # download the NW and CLP data from Google Drive
  tar_target(
    name = c_downloaded_historical_NW_CLP,
    command = {
      a_collated_pts_to_csv 
      download_csvs_from_drive(drive_folder_name = paste0("LS-C2-SR-NW_CLP_Poly-Points-v", 
                                      Sys.getenv("nw_clp_pull_version_date")), 
                               version_identifier = Sys.getenv("nw_clp_pull_version_date"))
      },
    packages = c("tidyverse", "googledrive"),
    cue = tar_cue(depend = T)
  ),
  # and do the same for the regional data
  tar_target(
    name = c_downloaded_historical_regional,
    command = {
      a_collated_pts_to_csv
      download_csvs_from_drive(drive_folder_name = paste0("LS-C2-SR-RegionalPoints-v", 
                                      Sys.getenv("regional_pull_version_date")),
                               version_identifier = Sys.getenv("regional_pull_version_date"))
      },
    packages = c("tidyverse", "googledrive")
  ),
  # and load/collate those data, with each type as a new feather file
  # first with the NW/CLP data
  tar_target(
    name = c_collated_historical_NW_CLP,
    command = {
      c_downloaded_historical_NW_CLP
      collate_csvs_from_drive(file_prefix = "NW-Poudre-Historical", 
                              version_identifier = Sys.getenv("nw_clp_pull_version_date"))
      },
    packages = c("tidyverse", "feather")
  ),
  # and now for the regional data
  tar_target(
    name = c_collated_historical_regional,
    command = {
      c_downloaded_historical_regional
      collate_csvs_from_drive(file_prefix = "NW-Poudre-Regional", 
                              version_identifier = Sys.getenv("regional_pull_version_date"))
      },
    packages = c("tidyverse", "feather")
  ),
  # now, add metadata to tabular summaries and break out the DSWE 1/3 data
  # first for the regional data
  tar_target(
    name = c_combined_regional_metadata_data,
    command = {
      c_collated_historical_regional
      combine_metadata_with_pulls(file_prefix = "NW-Poudre-Regional", 
                                  version_identifier = Sys.getenv("regional_pull_version_date"),
                                  collation_identifier = Sys.getenv("collation_date"))
    },
    packages = c("tidyverse", "feather")
  ),
  # and then for the NW/CLP data
  tar_target(
    name = c_combined_NW_CLP_metadata_data,
    command = {
      c_collated_historical_NW_CLP
      combine_metadata_with_pulls(file_prefix = "NW-Poudre-Historical", 
                                  version_identifier = Sys.getenv("nw_clp_pull_version_date"),
                                  collation_identifier = Sys.getenv("collation_date"))
    },
    packages = c("tidyverse", "feather")
  ),
  # make a list of the collated files to branch over
  tar_target(
    name = c_collated_files,
    command = {
      c_combined_NW_CLP_metadata_data
      c_combined_regional_metadata_data
      list.files('c_historical_RS_data_collation/out/', 
                 full.names = T,
                 pattern = Sys.getenv("collation_date")) %>% 
        .[grepl('collated', .)]
      }
  ),
  # pass the QAQC filter over each of the listed files, creating filtered files
  tar_target(
    name = c_QAQC_filtered_data,
    command = baseline_QAQC_RS_data(filepath = c_collated_files),
    packages = c("tidyverse", "feather"),
    pattern = map(c_collated_files)
  )
)