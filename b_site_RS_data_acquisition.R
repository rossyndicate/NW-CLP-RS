library(targets)
library(tarchetypes)
library(reticulate)

yaml_file <- "nw-poudre-historical-config.yml"

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

tar_source("b_RS_data_acquisition/py/pySetup.R")


# Source functions --------------------------------------------------------

tar_source("b_RS_data_acquisition/src/")


# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = c("tidyverse", "sf"))

# target objects in workflow
b_targets_list <- list(
  # read and track the config file
  tar_file_read(
    name = config_file,
    command = yaml_file,
    read = read_yaml(!!.x),
    packages = "yaml",
    cue = tar_cue("always")
  ),
  
  # load, format, save yml as a csv
  tar_target(
    name = yml_save,
    command = {
      # make sure that {targets} runs the config_file target before this target
      config_file 
      format_yaml(yml_file = yaml_file)
    },
    packages = c("yaml", "tidyverse") #for some reason, you have to load TV.
  ),
  
  # read in and track the formatted yml .csv file
  tar_file_read(
    name = yml,
    command = yml_save,
    read = read_csv(!!.x),
    packages = "readr"
  ),
  
  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = locs_save,
    command = grab_locs(yaml = yml)
  ),
  
  # read and track formatted locations shapefile
  tar_file_read(
    name = locs,
    command = locs_save,
    read = read_csv(!!.x),
    packages = "readr",
    error = "null"
  ),
  
  # # use location shapefile and configurations to get polygons from NHDPlusv2
  # tar_target(
  #   name = poly_save,
  #   command = get_NHD(locations = locs, 
  #                     yaml = yml),
  #   packages = c("nhdplusTools", "sf", "tidyverse")
  # ),
  # 
  # # load and track polygons file
  # tar_file_read(
  #   name = polygons, # this will throw an error if the configure extent does not include polygon
  #   command = tar_read(poly_save),
  #   read = read_sf(!!.x),
  #   packages = "sf",
  #   error = "null"
  # ),
  # 
  # # use `polygons` sfc to calculate Chebyshev centers
  # tar_target(
  #   name = centers_save,
  #   command = calc_center(poly = polygons, 
  #                         yaml = yml),
  #   packages = c("sf", "polylabelr", "tidyverse")
  # ),
  # 
  # # track centers file
  # tar_file_read(
  #   name = centers, # this will throw an error if the configure extent does not include center.
  #   command = tar_read(centers_save),
  #   read = read_sf(!!.x),
  #   packages = "sf",
  #   error = "null"
  # ),
  # 
  # # get WRS tile acquisition method from yaml
  # tar_target(
  #   name = WRS_detection_method,
  #   command = get_WRS_detection(yaml = yml),
  # ),
  
  # get WRS tiles
  tar_target(
    name = WRS_tiles,
    command = get_WRS_tiles(detection_method = "site", 
                            yaml = yml, 
                            locs = locs),
                            # ,
                            # centers = centers,
                            # poly = polygons),
    packages = c("readr", "sf")
  ),
  
  # run the Landsat pull as function per tile
  tar_target(
    name = eeRun,
    command = {
      yml
      locs
      # polygons
      # centers
      run_GEE_per_tile(WRS_tiles)
    },
    pattern = map(WRS_tiles),
    packages = "reticulate"
  ),
  
  # wait for all earth engine tasks to be completed
  tar_target(
    name = ee_tasks_complete,
    command = {
      eeRun
      source_python("b_RS_data_acquisition/py/poi_wait_for_completion.py")
    },
    packages = "reticulate"
  ),
  
  # download all files
  tar_target(
    name = download_files,
    command = {
      ee_tasks_complete
      download_csvs_from_drive(drive_folder_name = yml$proj_folder,
                               google_email = yml$google_email,
                               version_identifier = yml$run_date)
    },
    packages = c("tidyverse", "googledrive")
  ),
  
  # collate all files
  tar_target(
    name = make_collated_data_files,
    command = {
      download_files
      collate_csvs_from_drive(file_prefix = yml$proj, 
                              version_identifier = yml$run_date)
    },
    packages = c('tidyverse', 'feather')
  ),
  
  # and collate the data with metadata
  tar_target(
    name = make_files_with_metadata,
    command = {
      make_collated_data_files
      add_metadata(yaml = yml,
                   file_prefix = yml$proj,
                   version_identifier = yml$run_date)
    },
    packages = c("tidyverse", "feather")
  )
  
)
