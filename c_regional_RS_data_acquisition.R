library(targets)
library(tarchetypes)
library(reticulate)

yaml_file <- "nw-poudre-regional-config.yml"

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

tar_source("pySetup.R")


# Source functions --------------------------------------------------------

tar_source("src/")


# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = c("tidyverse", "sf"))

# target objects in workflow
c_regional_RS_data <- list(
  
  # check for proper directory structure ------------------------------------
  
  tar_target(
    name = c_check_dir_structure,
    command = {
      directories = c("c_regional_RS_data_acquisition/run/",
                      "c_regional_RS_data_acquisition/mid/",
                      "c_regional_RS_data_acquisition/down/",
                      "c_regional_RS_data_acquisition/out/")
      walk(directories, function(dir) {
        if(!dir.exists(dir)){
          dir.create(dir)
        }
      })
    }
  ),
  
  
  # set up ee run configuration -----------------------------------------------
  
  # read and track the config file
  tar_file_read(
    name = c_config_file,
    command = yaml_file,
    read = read_yaml(!!.x),
    packages = "yaml",
    cue = tar_cue("always")
  ),
  
  # load, format, save yml as a csv
  tar_target(
    name = c_yml,
    command = {
      c_check_dir_structure
      format_yaml(yaml = c_config_file,
                  parent_path = "c_regional_RS_data_acquisition")
    },
    packages = c("yaml", "tidyverse") #for some reason, you have to load TV.
  ),
  
  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = c_locs,
    command = {
      c_check_dir_structure
      grab_locs(yaml = c_yml,
                parent_path = "c_regional_RS_data_acquisition")
    }
  ),
  
  # get WRS tiles
  tar_target(
    name = c_WRS_tiles,
    command = get_WRS_tiles(detection_method = "site", 
                            yaml = c_yml, 
                            locs = c_locs,
                            parent_path = "c_regional_RS_data_acquisition"),
    packages = c("readr", "sf")
  ),
  
  
  # send the tasks to earth engine! -----------------------------------------
  
  # run the Landsat pull as function per tile
  tar_target(
    name = c_eeRun,
    command = {
      c_yml
      c_locs
      run_GEE_per_tile(WRS_tile = c_WRS_tiles,
                       parent_path = "c_regional_RS_data_acquisition")
    },
    pattern = map(c_WRS_tiles),
    packages = "reticulate"
  ),
  
  # wait for all earth engine tasks to be completed
  tar_target(
    name = c_ee_tasks_complete,
    command = {
      c_eeRun
      source_python("c_regional_RS_data_acquisition/py/poi_wait_for_completion.py")
    },
    packages = "reticulate"
  ),
  
  
  # download and collate files ----------------------------------------------
  
  # download all files
  tar_target(
    name = c_download_files,
    command = {
      c_ee_tasks_complete
      download_csvs_from_drive(drive_folder_name = c_yml$proj_folder,
                               google_email = c_yml$google_email,
                               version_identifier = c_yml$run_date,
                               parent_path = "c_regional_RS_data_acquisition")
    },
    packages = c("tidyverse", "googledrive")
  ),
  
  # collate all files
  tar_target(
    name = c_make_collated_data_files,
    command = {
      c_download_files
      collate_csvs_from_drive(file_prefix = c_yml$proj, 
                              version_identifier = c_yml$run_date,
                              parent_path = "c_regional_RS_data_acquisition")
    },
    packages = c("tidyverse", "feather")
  ),
  
  # and collate the data with metadata
  tar_target(
    name = c_make_files_with_metadata,
    command = {
      c_make_collated_data_files
      add_metadata(yaml = c_yml,
                   parent_path = "c_regional_RS_data_acquisition")
    },
    packages = c("tidyverse", "feather")
  )
  
)
