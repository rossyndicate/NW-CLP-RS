# Source functions for this {targets} list
tar_source("f_separate_NW_CLP_data/src/")

# Separate NW and CLP data and save to Drive -------------

# This set of functions join the location information back with the collated 
# data, filters for NW and CLP reservoirs/lakes, and then saves the files in
# the ROSSyndicate Google Drive

# prep folder structure
suppressWarnings({
  dir.create('f_separate_NW_CLP_data/out/')
})

e_targets_list <- list(
  # join collated, corrected GEE output with spatial information.
  # first for points
  tar_target(
    name = f_add_spatial_info_NW_CLP_points_DSWE1,
    command = {
      e_Rrs_DSWE1_correction_figures
      add_spatial_information(e_DSWE1_corrected_file_list %>% 
                                .[grepl('Historical_point', .)], 
                              a_collated_points, 
                              'point')
    },
    packages = c('tidyverse', 'feather', 'sf')
  ),
  # track the output file
  tar_file_read(
    name = f_NW_CLP_points_dataset_with_info_DSWE1,
    command = f_add_spatial_info_NW_CLP_points_DSWE1,
    read = read_feather(!!.x),
    packages = 'feather'
  ),
  # upload to Drive
  tar_target(
    name = f_NW_CLP_points_to_Drive_DSWE1,
    command = {
      drive_auth(email = Sys.getenv('google_email'))
      folder = drive_find(pattern = 'NW_CLP_for_analysis')
      drive_upload(f_add_spatial_info_NW_CLP_points_DSWE1, 
                           path = as_id(folder$id))
      },
    packages = 'googledrive'  
  ),
  # and also for the polygons
  tar_target(
    name = f_add_spatial_info_NW_CLP_polygons_DSWE1,
    command = {
      e_Rrs_DSWE1_correction_figures
      add_spatial_information(e_DSWE1_corrected_file_list %>%
                                .[grepl('Historical_poly', .)],
                              a_NW_CLP_ROSS_polygons,
                              'poly')
    },
    packages = c('tidyverse', 'feather')
  ),
  
  # subset the files for CLP data
  tar_target(
    name = f_subset_points_for_CLP_DSWE1,
    command = subset_file_by_data_group(f_add_spatial_info_NW_CLP_points_DSWE1, 'CLP'),
    packages = c('tidyverse', 'feather'),
  ),
  # track the output file
  tar_file_read(
    name = f_CLP_points_dataset_with_info_DSWE1,
    command = f_subset_points_for_CLP_DSWE1,
    read = read_feather(!!.x),
    packages = 'feather'
  ),
  # uploaad to Drive
  tar_target(
    name = f_CLP_points_to_Drive_DSWE1,
    command = {
      drive_auth(email = Sys.getenv('google_email'))
      folder = drive_find(pattern = 'NW_CLP_for_analysis')
      drive_upload(f_subset_points_for_CLP_DSWE1, 
                   path = as_id(folder$id))
    },
    packages = 'googledrive'  
  ),
  # subset the files for ROSS CLP data
  tar_target(
    name = f_subset_points_for_ROSS_CLP_DSWE1,
    command = subset_file_by_data_group(f_add_spatial_info_NW_CLP_points_DSWE1, 
                                        'ROSS_CLP'),
    packages = c('tidyverse', 'feather')
  ),
  # track and load that file
  tar_file_read(
    name = f_ROSS_CLP_points_dataset_with_info_DSWE1,
    command = f_subset_points_for_ROSS_CLP_DSWE1,
    read = read_feather(!!.x),
    packages = 'feather'
  ),
  # uploaad to Drive
  tar_target(
    name = f_ROSS_CLP_points_to_Drive_DSWE1,
    command = {
      drive_auth(email = Sys.getenv('google_email'))
      folder = drive_find(pattern = 'NW_CLP_for_analysis')
      drive_upload(f_subset_points_for_ROSS_CLP_DSWE1, 
                   path = as_id(folder$id))
    },
    packages = 'googledrive'  
  ),
  # subset the files for NW data
  tar_target(
    name = f_subset_points_for_NW_DSWE1,
    command = subset_file_by_data_group(f_add_spatial_info_NW_CLP_points_DSWE1, 
                                        'NW'),
    packages = c('tidyverse', 'feather'),
  ),
  # track and load that file
  tar_file_read(
    name = f_NW_points_dataset_with_info_DSWE1,
    command = f_subset_points_for_NW_DSWE1,
    read = read_feather(!!.x),
    packages = 'feather'
  ),
  # upload to Drive
  tar_target(
    name = f_NW_points_to_Drive_DSWE1,
    command = {
      drive_auth(email = Sys.getenv('google_email'))
      folder = drive_find(pattern = 'NW_CLP_for_analysis')
      drive_upload(f_subset_points_for_NW_DSWE1, 
                   path = as_id(folder$id))
    },
    packages = 'googledrive'  
  )
)
  
  