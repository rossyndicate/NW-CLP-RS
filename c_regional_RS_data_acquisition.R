library(targets)
library(tarchetypes)
library(reticulate)

yaml_file <- "nw-poudre-regional-config.yml"


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
  
  tar_target(
    name = c_check_Drive_regional,
    command = {
      config_check_drive_parent_folder
      tryCatch({
        drive_auth(c_yml$google_email)
        drive_ls(paste(c_yml$proj_folder, c_yml$run_date, sep = "_v"))
      }, error = function(e) {
        # if the outpath doesn't exist, create it
        drive_mkdir(name = paste(c_yml$proj_folder, c_yml$run_date, sep = "_v"),
                    path = c_yml$drive_parent_folder)
      })
    },
    packages = c("googledrive"),
    deployment = "main"
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
    packages = c("yaml", "tidyverse"), 
    cue = tar_cue("always")
  ),
  
  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = c_locs,
    command = {
      a_aoi_centers_to_csv
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
                            parent_path = "c_regional_RS_data_acquisition")
  ),
  
  # check to see that all sites and buffers are completely contained by each pathrow
  # and assign wrs path-rows for all sites based on configuration buffer.
  tar_target(
    name = c_locs_filtered,
    command = check_if_fully_within_pr(WRS_pathrow = c_WRS_tiles, 
                                       locations = c_locs, 
                                       parent_path = "c_regional_RS_data_acquisition",
                                       yml = c_yml),
    pattern = map(c_WRS_tiles),
    packages = c("tidyverse", "sf", "arrow")
  ),
  
  # send the tasks to earth engine! -----------------------------------------
  
  # run the Landsat pull as function per tile
  tar_target(
    name = c_eeRun_regional,
    command = {
      c_yml
      c_locs_filtered
      run_GEE_per_tile(WRS_tile = c_WRS_tiles,
                       parent_path = "c_regional_RS_data_acquisition")
    },
    pattern = map(c_WRS_tiles),
    packages = "reticulate",
    deployment = "main"
  ),
  
  # wait for all earth engine tasks to be completed
  tar_target(
    name = c_ee_tasks_complete,
    command = {
      c_eeRun_regional
      source_python("c_regional_RS_data_acquisition/py/poi_wait_for_completion.py")
    },
    packages = "reticulate",
    deployment = "main"
  ),
  
  
  # download and collate files ----------------------------------------------
  
  tar_target(
    name = c_regional_contents,
    command = {
      # assure tasks complete
      c_ee_tasks_complete
      drive_auth(email = c_yml$google_email)
      drive_folder <- paste0(c_yml$drive_parent_folder, 
                             c_yml$proj_folder, 
                             "_v", c_yml$run_date)
      drive_ls(path = drive_folder) %>% 
        select(name, id)
    },
    packages = c("tidyverse", "googledrive")
  ),
  
  # download all files
  tar_target(
    name = c_download_files,
    command = download_csvs_from_drive(local_folder = "c_regional_RS_data_acquisition/down/",
                                       yml = c_yml,
                                       drive_contents = c_regional_contents),
    packages = c("tidyverse", "googledrive")
  ),
  
  # detect dswe types
  tar_target(
    name = c_DSWE_types,
    command = {
      dswe = NULL
      if (grepl("1", c_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE1")
      } 
      if (grepl("1a", c_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE1a")
      } 
      if (grepl("3", c_yml$DSWE_setting)) {
        dswe = c(dswe, "DSWE3")
      } 
      dswe
    }
  ),
  
  # collate all files
  tar_target(
    name = c_make_collated_data_files,
    command = {
      c_download_files
      collate_csvs_from_drive(local_folder = "c_regional_RS_data_acquisition/down/",
                              yaml = c_yml,
                              out_folder = "c_regional_RS_data_acquisition/mid/",
                              dswe = c_DSWE_types)
    },
    pattern = map(c_DSWE_types),
    packages = c("data.table", "tidyverse", "arrow")
  ),
  
  # and collate the data with metadata
  tar_target(
    name = c_make_files_with_metadata,
    command = {
      c_make_collated_data_files
      add_metadata(yaml = c_yml,
                   local_folder = file.path("c_regional_RS_data_acquisition/mid/", c_yml$run_date),
                   out_folder = file.path("c_regional_RS_data_acquisition/out", c_yml$run_date))
    },
    packages = c("tidyverse", "arrow")
  )
  
)
