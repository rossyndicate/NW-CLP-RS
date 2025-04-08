
# Load packages required to define the pipeline:
library(targets)
library(tarchetypes)
library(reticulate)
library(crew)

# Set up python virtual environment ---------------------------------------

tar_source("pySetup.R")

# Set up crew controller for multicore processing ------------------------

controller_cores <- crew_controller_local(
  workers = parallel::detectCores()-1,
  seconds_idle = 12
)

# Set target options: ---------------------------------------

tar_option_set(
  # packages that {targets} need to run for this workflow
  packages = c("tidyverse", "sf"),
  memory = "transient",
  garbage_collection = TRUE,
  # set up crew controller
  controller = controller_cores
)

# collate targets lists and files ----------------------------

config_list <- list(
  
  # project config settings (you must use the `config::` style here)
  tar_target(
    name = general_config,
    command = config::get(),
    cue = tar_cue("always")
  ),
  
  tar_target(
    name = config_check_drive_parent_folder,
    command = tryCatch({
      drive_auth(general_config$google_email)
      drive_ls(path = general_config$drive_parent_folder, type = "folder")
    }, error = function(e) {
      drive_mkdir(str_sub(general_config$drive_parent_folder, 1, -2))  
    }),
    packages = "googledrive",
    cue = tar_cue("always"),
    deployment = "main"
  )
)

# source functions
tar_source(files = c(
  "a_locs_poly_setup.R",
  "b_site_RS_data_acquisition.R",
  "c_regional_RS_data_acquisition.R"
  ))
#,  "d_baseline_QAQC.R",
#   "e_calculate_handoff_coefficients.R",
#   "f_apply_handoff_coefficients.R",
#   "g_separate_NW_CLP_data.R"
# ))

# Full targets list 
c(config_list,
  a_locs_poly_setup,
  b_site_RS_data,
  c_regional_RS_data
)
# ,
# d_baseline_QAQC,
# e_calculate_handoff_coefficients
