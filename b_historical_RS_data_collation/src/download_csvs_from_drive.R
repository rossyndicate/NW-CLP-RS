#' @title Download csv files from specified Drive folder
#' 
#' @description
#' description Function to download all csv files from a specific drive folder 
#' to the untracked b_historical_RS_data_collation/in/ folder
#'
#' @param drive_folder_name text string; name of folder in Drive, must be unique
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' 
#' @returns downloads all .csvs from the specified folder name to the
#' b_historical_RS_data_collation/in/ folder
#' 
#' @note This function requires that you have created an .Renviron option whose
#' key is 'google_email' and value is the ROSS gmail
#' 
#' 
download_csvs_from_drive <- function(drive_folder_name, version_identifier) {
  drive_auth(email = Sys.getenv("google_email"))
  dribble_files <- drive_ls(path = drive_folder_name)
  dribble_files <- dribble_files %>% 
    filter(grepl(".csv", name))
  # make sure directory exists, create it if not
  if(!dir.exists(file.path("b_historical_RS_data_collation/in/", 
                           version_identifier))) {
    dir.create(file.path("b_historical_RS_data_collation/in/", 
                         version_identifier))
  }
  walk2(.x = dribble_files$id,
        .y = dribble_files$name, 
        .f = function(.x, .y) {
          try(drive_download(file = .x,
                         path = file.path("b_historical_RS_data_collation/in/", 
                                          version_identifier,
                                          .y),
                         overwrite = FALSE)) # just pass if already downloaded
          })
}
