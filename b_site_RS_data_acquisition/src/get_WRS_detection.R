#' @title Determine WRS selection method
#' 
#' @description
#' Function to use the yaml file extent to define the optimal shapefile for 
#' determining the WRS paths that need to be extracted.
#' 
#' @param yaml contents of the yaml .csv file
#' @returns text string
#' 
#' @details Polygons are the first choice for WRS overlap, as they cover more
#' area and are most likely to cross the boundaries of WRS tiles. 
#' 
#' 
get_WRS_detection <- function(yaml) {
  extent = yaml$extent[1]
  if (grepl('poly', extent)) {
    return('polygon')
  } else {
    if (grepl('site', extent)) {
      return('site')
    } else {
      if (grepl('center', extent)) {
        return('center')
      }
    }
  }
}


