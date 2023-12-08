# Source functions for this {targets} list
tar_source("b_historical_RS_data_collation/src/")

# Download and process GEE output from historical pulls -------------

# this pipeline collates all of the GEE output files for the NW and CLP projects
# Note: this portion of the workflow is dependent on the successful run of two 
# branches of the Landsat_C2_SRST repository: nw-poudre-historical and nw-er3z21-historical.
# At this time, this is run outside of the {targets} workflow presented here. 

# prep folder structure
suppressWarnings({
  dir.create("b_historical_RS_data_collation/in/")
  dir.create("b_historical_RS_data_collation/mid/")
  dir.create("b_historical_RS_data_collation/out/")
})

b_targets_list <- list(
  # download the NW and CLP data from Google Drive
  tar_target(
    name = b_downloaded_historical_NW_CLP,
    command = {
      a_collated_pts_to_csv 
      download_csvs_from_drive(paste0("LS-C2-SR-NW_CLP_Poly-Points-v", 
                                      Sys.getenv("nw_clp_pull_version_date")), 
                               Sys.getenv("nw_clp_pull_version_date"))
      },
    packages = c("tidyverse", "googledrive"),
    cue = tar_cue(depend = T)
  ),
  # and do the same for the regional data
  tar_target(
    name = b_downloaded_historical_regional,
    command = {
      a_collated_pts_to_csv
      download_csvs_from_drive(paste0("LS-C2-SR-RegionalPoints-v", 
                                      Sys.getenv("regional_pull_version_date")),
                               Sys.getenv("regional_pull_version_date"))
      },
    packages = c("tidyverse", "googledrive")
  ),
  # and load/collate those data, with each type as a new feather file
  # first with the NW/CLP data
  tar_target(
    name = b_collated_historical_NW_CLP,
    command = {
      b_downloaded_historical_NW_CLP
      collate_csvs_from_drive("NW-Poudre-Historical", Sys.getenv("nw_clp_pull_version_date"))
      },
    packages = c("tidyverse", "feather")
  ),
  # and now for the regional data
  tar_target(
    name = b_collated_historical_regional,
    command = {
      b_downloaded_historical_regional
      collate_csvs_from_drive("NW-Poudre-Regional", Sys.getenv("regional_pull_version_date"))
      },
    packages = c("tidyverse", "feather")
  ),
  # now, add metadata to tabular summaries and break out the DSWE 1/3 data
  # first for the regional data
  tar_target(
    name = b_combined_regional_metadata_data,
    command = {
      b_collated_historical_regional
      combine_metadata_with_pulls("NW-Poudre-Regional", 
                                  Sys.getenv("regional_pull_version_date"),
                                  Sys.getenv("collation_date"))
    },
    packages = c("tidyverse", "feather")
  ),
  # and then for the NW/CLP data
  tar_target(
    name = b_combined_NW_CLP_metadata_data,
    command = {
      b_collated_historical_NW_CLP
      combine_metadata_with_pulls("NW-Poudre-Historical", 
                                  Sys.getenv("nw_clp_pull_version_date"),
                                  Sys.getenv("collation_date"))
    },
    packages = c("tidyverse", "feather")
  ),
  # make a list of the collated files to branch over
  tar_target(
    name = b_collated_files,
    command = {
      b_combined_NW_CLP_metadata_data
      b_combined_regional_metadata_data
      list.files('b_historical_RS_data_collation/out/', 
                 full.names = T,
                 pattern = Sys.getenv("collation_date")) %>% 
        .[grepl('collated', .)]
      }
  ),
  # pass the QAQC filter over each of the listed files, creating filtered files
  tar_target(
    name = b_QAQC_filtered_data,
    command = baseline_QAQC_RS_data(b_collated_files),
    packages = c("tidyverse", "feather"),
    pattern = map(b_collated_files)
  )
)