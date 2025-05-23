#' @title Collate handoff coefficients
#' 
#' @description
#' Function to collate the files created by the handoff targets in this group of
#' targets
#' 
#' @returns file name of collated handoff coefficients .csv stored in the out
#' folder
#' 
#' 
collate_handoff_coefficients <- function() {
  #list the files in coefficients
  files <- list.files("d_calculate_handoff_coefficients/mid",
                      full.names = TRUE)
  # collate those suckers
  collated <- map_dfr(files, read_csv)
  #save the file and return the file name
  write_csv(collated, 
            file.path("d_calculate_handoff_coefficients/out/",
                      "Landsat_handoff_coefficients.csv"))
  file.path("d_calculate_handoff_coefficients/out/",
            "Landsat_handoff_coefficients.csv")
}
