#' @title Calculate POI for polygons
#' 
#' @description
#' Use polygon and 'point of inaccessibility' function (polylabelr::poi()) to 
#' determine the equivalent of Chebyshev center, furthest point from every edge 
#' of a polygon. POI function here will calculate distance in meters using the 
#' UTM coordinate system and the POI location as Latitude/Longitude in WGS84 
#' decimal degrees.
#' 
#' @param yaml contents of the yaml .csv file
#' @param poly sfc object of polygon areas for acquisition
#' @returns filepath for the .shp of the polygon centers or the message
#' 'Not configured to use polygon centers'. Silently saves 
#' the polygon centers shapefile in the `data_acquisition/in` directory path 
#' if configured for polygon centers acquisition.
#' 
#' 
calc_center <- function(poly, yaml) {
  if (grepl("center", yaml$extent[1])) {
    # create an empty tibble
    poi_df <- tibble(
      r_id = integer(),
      poi_longitude = numeric(),
      poi_latitude = numeric(),
      poi_dist_m = numeric()
    )
    # create rowids for proper indexing
    poly <- poly %>% 
      rowid_to_column("r_id")
    for (i in 1:length(poly[[1]])) {
      poi_df  <- poi_df %>% add_row()
      # grab one polygon
      one_wbd <- poly[i, ]
      # get coordinates to calculate UTM zone. This is an adaptation of code from
      # Xiao Yang's code in EE - Yang, Xiao. (2020). Deepest point calculation 
      # for any given polygon using Google Earth Engine JavaScript API 
      # (Version v1). Zenodo. https://doi.org/10.5281/zenodo.4136755
      coord_for_UTM <- one_wbd %>% st_coordinates()
      mean_x <- mean(coord_for_UTM[ ,1])
      mean_y <- mean(coord_for_UTM[ ,2])
      # calculate the UTM zone using the mean value of Longitude for the polygon
      utm_suffix <- as.character(ceiling((mean_x + 180) / 6))
      utm_code <- if_else(mean_y >= 0,
                         # EPSG prefix for N hemishpere
                         paste0("EPSG:326", utm_suffix),
                         # for S hemisphere
                         paste0("EPSG:327", utm_suffix))
      # transform wbd to UTM, as it's more accurate for distance
      one_wbd_utm <- st_transform(one_wbd, 
                                 crs = utm_code)
      # get UTM coordinates
      coord <- one_wbd_utm %>% st_coordinates()
      x <- coord[ ,1]
      y <- coord[ ,2]
      # using coordinates, get the poi distance
      poly_poi <- poi(x,y, precision = 0.01) 
        
      # add info from the original polygon and poi calcs to poi_df
      poi_df$r_id[i] <- one_wbd$r_id
      poi_df$poi_dist_m[i] <- poly_poi$dist
      # make a point feature and re-calculate decimal degrees in WGS84
      point <- st_point(x = c(as.numeric(poly_poi$x),
                             as.numeric(poly_poi$y)))
      point <- st_sfc(point, crs = utm_code)
      point <- st_transform(st_sfc(point), crs = "EPSG:4326")
      
      new_coords <- point %>% st_coordinates()
      poi_df$poi_longitude[i] <- new_coords[ ,1]
      poi_df$poi_latitude[i] <- new_coords[ ,2]    
    }
    # merge the poi information with the original polygon info
    poly_poi <- poly %>%
      st_drop_geometry() %>% 
      full_join(., poi_df)
    # and create a sf object from it based on the pois
    poi_geo <- st_as_sf(poly_poi,
                        coords = c("poi_longitude", "poi_latitude"), 
                        crs = "EPSG:4326")
    
    if (yaml$polygon[1] == FALSE) {
      write_sf(poi_geo, file.path("data_acquisition/out/NHDPlus_polygon_centers.shp"))
      poly_poi %>% 
        # mutate for python base 0
        mutate(py_id = r_id - 1) %>% 
        write_csv("data_acquisition/out/NHDPlus_polygon_centers.csv")
      return("data_acquisition/out/NHDPlus_polygon_centers.shp")
    } else {
      write_sf(poi_geo, file.path("data_acquisition/out/user_polygon_centers.shp"))
      poly_poi %>% 
        # mutate for python base 0
        mutate(py_id = r_id - 1) %>% 
        write_csv("data_acquisition/out/user_polygon_centers.csv")
      return("data_acquisition/out/user_polygon_centers.shp")
    }
  } else {
    return(message("Not configured to pull polygon center."))
  }
}

