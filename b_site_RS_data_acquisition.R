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


# Set up python virtual environment ---------------------------------------

tar_source("b_site_RS_data_acquisition/py/pySetup.R")

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
    command = format_yaml(yaml = b_config_file,
                          parent_path = "b_site_RS_data_acquisition"),
    packages = c("yaml", "tidyverse") #for some reason, you have to load TV.
  ),
  
  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = b_locs,
    command = grab_locs(yaml = b_yml,
                        parent_path = "b_site_RS_data_acquisition")
  ),
  
  # get WRS tiles
  tar_target(
    name = b_WRS_tiles,
    command = get_WRS_tiles(detection_method = "site", 
                            yaml = b_yml, 
                            locs = b_locs,
                            parent_path = "b_site_RS_data_acquisition"),
    packages = c("readr", "sf")
  ),
  
  # run the Landsat pull as function per tile
  tar_target(
    name = b_eeRun,
    command = {
      b_yml
      b_locs
      run_GEE_per_tile(WRS_tile = b_WRS_tiles,
                       parent_path = "b_site_RS_data_acquisition")
    },
    pattern = map(b_WRS_tiles),
    packages = "reticulate"
  ),
  
  # wait for all earth engine tasks to be completed
  tar_target(
    name = b_ee_tasks_complete,
    command = {
      b_eeRun
      source_python("b_site_RS_data_acquisition/py/poi_wait_for_completion.py")
    },
    packages = "reticulate"
  ),
  
  # download all files
  tar_target(
    name = b_download_files,
    command = {
      b_ee_tasks_complete
      download_csvs_from_drive(drive_folder_name = b_yml$proj_folder,
                               google_email = b_yml$google_email,
                               version_identifier = b_yml$run_date,
                               parent_path = "b_site_RS_data_acquisition")
    },
    packages = c("tidyverse", "googledrive")
  ),
  
  # collate all files
  tar_target(
    name = b_make_collated_data_files,
    command = {
      b_download_files
      collate_csvs_from_drive(file_prefix = b_yml$proj, 
                              version_identifier = b_yml$run_date,
                              parent_path = "b_site_RS_data_acquisition")
    },
    packages = c("tidyverse", "feather")
  ),
  
  # and collate the data with metadata
  tar_target(
    name = b_make_files_with_metadata,
    command = {
      b_make_collated_data_files
      add_metadata(yaml = b_yml,
                   parent_path = "b_site_RS_data_acquisition")
    },
    packages = c("tidyverse", "feather")
  )
  
)
