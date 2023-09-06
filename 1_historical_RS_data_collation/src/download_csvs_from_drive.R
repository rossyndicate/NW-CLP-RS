#' Function to download all csv files from a specific drive folder to the untracked
#' 1_historical_RS_data_collation/in/ folder
#'
#' @param drive_folder_name name of folder in Drive, must be unique
#' @returns downloads all .csvs from the specified folder name to the
#' 1_historical_RS_data_collation/in/ folder
#' 
#' @note This function requires that you have created an .Renviron option whose
#' key is 'google_email' and value is the ROSS gmail
#' 
#' 
download_csvs_from_drive <- function(drive_folder_name) {
  dir.create("1_historical_RS_data_collation/in/")
  drive_auth(email = Sys.getenv("google_email"))
  dribble_files <- drive_ls(path = drive_folder_name)
  dribble_files <- dribble_files %>% 
    filter(grepl(".csv", name))
  walk2(.x = dribble_files$id,
        .y = dribble_files$name, 
        .f = function(.x, .y) {
          try(drive_download(file = .x,
                         path = file.path("1_historical_RS_data_collation/in/", .y),
                         overwrite = FALSE)) # just pass if already downloaded
          })
}
