library(targets)
library(tarchetypes)
library(reticulate)

site_yaml_file <- "nw-poudre-historical-config.yml"

# MUST READ ---------------------------------------------------------------

# IMPORTANT NOTE:
#
# you must execute the command 'earthengine authenticate' in a zsh terminal
# before initializing this workflow. See the repository README for complete
# dependencies and troubleshooting.

# RUNNING {TARGETS}:
#
# use the file 'run_targets.Rmd', which includes EE authentication.


# Source functions --------------------------------------------------------

tar_source("src/")


# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = c("tidyverse", "sf"))

# target objects in workflow
b_site_RS_data <- list(
  
  # check for proper directory structure ------------------------------------
  
  tar_target(
    name = b_check_dir_structure,
    command = {
      directories = c("b_site_RS_data_acquisition/run/",
                      "b_site_RS_data_acquisition/mid/",
                      "b_site_RS_data_acquisition/down/",
                      "b_site_RS_data_acquisition/out/")
      walk(directories, function(dir) {
        if(!dir.exists(dir)){
          dir.create(dir)
        }
      })
    }
  ),
  
  tar_target(
    name = b_check_Drive_NW_CLP,
    command = {
      config_check_drive_parent_folder
      tryCatch({
        drive_auth(b_yml$google_email)
        drive_ls(paste(b_yml$proj_folder, b_yml$run_date, sep = "_v"))
      }, error = function(e) {
        # if the outpath doesn't exist, create it
        drive_mkdir(name = paste(b_yml$proj_folder, b_yml$run_date, sep = "_v"),
                    path = b_yml$drive_parent_folder)
      })
    },
    packages = c("googledrive")
  ),
  
  
  # set up ee run configuration -----------------------------------------------
  
  # read and track the config file
  tar_file_read(
    name = b_config_file,
    command = site_yaml_file,
    read = read_yaml(!!.x),
    packages = "yaml",
    cue = tar_cue("always")
  ),
  
  # load, format, save yml as a csv
  tar_target(
    name = b_yml,
    command = {
      b_check_dir_structure
      format_yaml(yaml = b_config_file,
                  parent_path = "b_site_RS_data_acquisition")
    },
    packages = c("yaml", "tidyverse"),
    cue = tar_cue("always")
  ),
  
  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = b_locs,
    command = {
      b_check_dir_structure
      grab_locs(yaml = b_yml,
                parent_path = "b_site_RS_data_acquisition")
    },
    cue = tar_cue("always")
  ),
  
  # get WRS tiles
  tar_target(
    name = b_WRS_tiles,
    command = get_WRS_tiles(detection_method = "site", 
                            yaml = b_yml, 
                            locs = b_locs,
                            parent_path = "b_site_RS_data_acquisition"),
  ),
  
  # check to see that all sites and buffers are completely contained by each pathrow
  # and assign wrs path-rows for all sites based on configuration buffer.
  tar_target(
    name = b_locs_filtered,
    command = check_if_fully_within_pr(WRS_pathrow = b_WRS_tiles, 
                                       locations = b_locs, 
                                       parent_path = "b_site_RS_data_acquisition",
                                       yml = b_yml),
    pattern = map(b_WRS_tiles),
    packages = c("tidyverse", "sf", "arrow")
  ),
  
  
  # send the tasks to earth engine! -----------------------------------------
  
  # run the Landsat pull as function per tile
  tar_target(
    name = b_eeRun_NW_CLP,
    command = {
      b_yml
      b_locs_filtered
      run_GEE_per_tile(WRS_tile = b_WRS_tiles,
                       parent_path = "b_site_RS_data_acquisition")
    },
    pattern = b_WRS_tiles,
    packages = "reticulate",
    deployment = "main"
  ),
  
  # wait for all earth engine tasks to be completed
  tar_target(
    name = b_ee_tasks_complete,
    command = {
      b_eeRun_NW_CLP
      source_python("b_site_RS_data_acquisition/py/poi_wait_for_completion.py")
    },
    packages = "reticulate",
    deployment = "main"
  ),
  
  
  # download and collate files ----------------------------------------------
  
  tar_target(
    name = b_NW_CLP_contents,
    command = {
      # assure tasks complete
      b_ee_tasks_complete
      drive_auth(email = b_yml$google_email)
      drive_folder <- paste0(b_yml$drive_parent_folder, 
                             b_yml$proj_folder, 
                             "_v", b_yml$run_date)
      drive_ls(path = drive_folder) %>% 
        select(name, id)
    },
    packages = c("tidyverse", "googledrive")
  ),
  
  
  # download all files
  tar_target(
    name = b_download_files,
    command = download_csvs_from_drive(local_folder = "b_site_RS_data_acquisition/down/",
                                       yml = b_yml,
                                       drive_contents = b_NW_CLP_contents),
    packages = c("tidyverse", "googledrive")
  ),
  
  # detect dswe types
  tar_target(
    name = b_DSWE_types,
    command = {
      dswe = NULL
      if (grepl("1", b_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE1")
      } 
      if (grepl("1a", b_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE1a")
      } 
      if (grepl("3", b_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE3")
      } 
      dswe
    }
  ),
  
  # collate all files
  tar_target(
    name = b_make_collated_data_files,
    command = {
      b_download_files
      collate_csvs_from_drive(local_folder = "b_site_RS_data_acquisition/down/",
                              yaml = b_yml,
                              out_folder = "b_site_RS_data_acquisition/mid/",
                              dswe = b_DSWE_types)
    },
    pattern = map(b_DSWE_types),
    packages = c("data.table", "tidyverse", "arrow")
  ),
  
  # and collate the data with metadata
  tar_target(
    name = b_make_files_with_metadata,
    command = {
      b_make_collated_data_files
      add_metadata(yaml = b_yml,
                   local_folder = file.path("b_site_RS_data_acquisition/mid/", b_yml$run_date),
                   out_folder = file.path("b_site_RS_data_acquisition/out", b_yml$run_date))
    },
    packages = c("tidyverse", "arrow")
  )
  
)
