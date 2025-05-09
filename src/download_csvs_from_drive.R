#' @title Download csv files from specified Drive folder
#' 
#' @description
#' description Function to download all csv files from a specific drive folder 
#' to the untracked `local_folder`
#'
#' @param local_folder file path of folder to which the Drive files should be 
#' downloaded.
#' @param file_type text string; unique string for filtering files to be 
#' downloaded from Drive - current options: "LS457", "LS89", "metadata", 
#' "pekel", NULL. Defaults to NULL.
#' @param yml dataframe; name of the targets object that
#' stores the GEE run configuration settings as a data frame.
#' @param drive_contents dataframe; name of the target object that contains the 
#' Drive folder contents of the destination folder specified in the GEE run 
#' configuration
#' @param depends target object; any target that must be run prior to this 
#' function. Defaults to NULL.
#' 
#' @returns downloads all .csvs from the specified folder name to the
#' `local_folder` folder
#' 
#' 
download_csvs_from_drive <- function(local_folder,
                                     file_type = NULL, 
                                     yml, 
                                     drive_contents, 
                                     depends = NULL) {
  
  if (!is.null(file_type)) {
    if (!file_type %in% c("LS457", "LS89", "metadata", "pekel")) {
      warning("The file type argument provided is not recognized.\n
              This may result in unintended downloads.")
    }
  }
  
  # authorize Google
  drive_auth(email = yml$google_email)
  # make sure they are only .csv files
  drive_contents <- drive_contents %>% 
    filter(grepl(".csv", name))
  # check to see if any further filtering needs to be done per file_type argument
  if (!is.null(file_type)) {
    drive_contents <- drive_contents %>% 
      filter(grepl(file_type, name))
    # if file type is not metadata, further filtering to remove metadata necessary
    if (file_type != "metadata") {
      drive_contents <- drive_contents %>% 
        filter(!grepl("metadata", name))
    }
  }
  # make sure run date folder has been created
  directory <- file.path(local_folder, yml$run_date)
  if (!dir.exists(directory)) {
    dir.create(directory)
  }
  if (!is.null(file_type)) {
    directory <- file.path(local_folder, yml$run_date, file_type)
    if (!dir.exists(directory)) {
      dir.create(directory)
    }
  }
  
  walk2(.x = drive_contents$id,
        .y = drive_contents$name, 
        .f = function(.x, .y) {
          try(drive_download(file = .x,
                             path = file.path(directory,
                                              .y),
                             overwrite = FALSE)) # just pass if already downloaded
        })
}
