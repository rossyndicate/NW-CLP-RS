#' @title Load location information
#' 
#' @description
#' Load in and format location file using config settings
#' 
#' @param yaml the formatted, unnested yaml dataframe
#' @param parent_path parent filepath where the RS run is occurring
#' 
#' @returns reformateed location data or the message
#' 'Not configured to use site locations'. Silently saves 
#' the .csv in the `/run/` directory path if configured 
#' for site acquisition.
#' 
#' 
grab_locs <- function(yaml, parent_path) {
  if (grepl("site", yaml$extent[1])) {
    locs <- read_csv(file.path(yaml$data_dir, yaml$location_file))
    # store yaml info as objects
    lat <- yaml$latitude
    lon <- yaml$longitude
    id <- yaml$unique_id
    # apply objects to tibble
    locs <- locs %>% 
      rename_with(~c("Latitude", "Longitude", "id"), any_of(c(lat, lon, id)))
    # write a .csv to be pulled in by the python code
    write_csv(locs, 
              file.path(parent_path, "run/locs.csv"))
    locs
  } else {
    message("Not configured to use site locations.")
  }
}

