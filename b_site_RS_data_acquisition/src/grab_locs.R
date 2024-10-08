#' @title Load location information
#' 
#' @description
#' Load in and format location file using config settings
#' 
#' @param yaml contents of the yaml .csv file
#' @returns filepath for the .csv of the reformatted location data or the message
#' 'Not configured to use site locations'. Silently saves 
#' the .csv in the `data_acquisition/in` directory path if configured for site
#' acquisition.
#' 
#' 
grab_locs <- function(yaml) {
  if (grepl("site", yaml$extent[1])) {
    locs <- read_csv(file.path(yaml$data_dir, yaml$location_file))
    # store yaml info as objects
    lat <- yaml$latitude
    lon <- yaml$longitude
    id <- yaml$unique_id
    # apply objects to tibble
    locs <- locs %>% 
      rename_with(~c("Latitude", "Longitude", "id"), any_of(c(lat, lon, id)))
    write_csv(locs, "data_acquisition/in/locs.csv")
    return("data_acquisition/in/locs.csv")
  } else {
    message("Not configured to use site locations.")
  }
}

