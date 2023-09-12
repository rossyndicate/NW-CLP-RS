#' @title Download csv files from specified Drive folder
#' 
#' @description
#' description Function to download all csv files from a specific drive folder 
#' to the untracked b_historical_RS_data_collation/in/ folder
#'
#' @param drive_folder_name text string; name of folder in Drive, must be unique
#' 
#' @returns downloads all .csvs from the specified folder name to the
#' b_historical_RS_data_collation/in/ folder
#' 
#' @note This function requires that you have created an .Renviron option whose
#' key is 'google_email' and value is the ROSS gmail
#' 
#' 
download_csvs_from_drive <- function(drive_folder_name) {
  drive_auth(email = Sys.getenv("google_email"))
  dribble_files <- drive_ls(path = drive_folder_name)
  dribble_files <- dribble_files %>% 
    filter(grepl(".csv", name))
  walk2(.x = dribble_files$id,
        .y = dribble_files$name, 
        .f = function(.x, .y) {
          try(drive_download(file = .x,
                         path = file.path("b_historical_RS_data_collation/in/", .y),
                         overwrite = FALSE)) # just pass if already downloaded
          })
}
