#' @title Download csv files from specified Drive folder
#' 
#' @description
#' description Function to download all csv files from a specific drive folder 
#' to the untracked data_acquisition/in/ folder
#'
#' @param drive_folder_name text string; name of folder in Drive, must be unique
#' @param google_email text string; google email address for Drive authentication
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' 
#' @returns downloads all .csvs from the specified folder name to the
#' data_acquisition/in/ folder
#' 
#' 
download_csvs_from_drive <- function(drive_folder_name, google_email, version_identifier) {
  drive_auth(email = google_email)
  dribble_files <- drive_ls(path = drive_folder_name)
  dribble_files <- dribble_files %>% 
    filter(grepl(".csv", name))
  # make sure directory exists, create it if not
  if(!dir.exists(file.path("data_acquisition/down/", 
                           version_identifier))) {
    dir.create(file.path("data_acquisition/down/", 
                         version_identifier), recursive = TRUE)
  }
  walk2(.x = dribble_files$id,
        .y = dribble_files$name, 
        .f = function(.x, .y) {
          try(drive_download(file = .x,
                         path = file.path("data_acquisition/down/", 
                                          version_identifier,
                                          .y),
                         overwrite = FALSE)) # just pass if already downloaded
          })
}
