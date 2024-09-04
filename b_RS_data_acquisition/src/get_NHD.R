#' @title Create polygon file using NHDPlusTools
#' 
#' @description
#' Use NHDPlusTools to create a polygon shapefile if user wants whole-lake 
#' summaries, or use the user-specified shapefile.
#' 
#' @param yaml contents of the yaml .csv file
#' @param locations contents of the formatted locations file
#' @returns filepath for the .shp of the polygons or the message
#' 'Not configured to use polygons'. Silently saves 
#' the .shp in the `data_acquisition/in` directory path if configured for polygon
#' acquisition.
#' 
#' 
get_NHD <- function(locations, yaml) {
  if (!dir.exists("data_acquisition/out/")) {
    dir.create("data_acquisition/out/")
  }
  if (grepl("poly", yaml$extent)) { # if polygon is specified in desired extent - either polycenter or polgon
    if (!yaml$polygon) { # and no polygon is provided, then use nhdplustools
      for (w in 1:nrow(locations)) {
        id <- locations$id[w]
        # create sf
        point <- st_as_sf(locations[w,], 
                            crs = yaml$location_crs, 
                            coords = c("Longitude", "Latitude"))
        wbd <- get_waterbodies(AOI = point) 
        # if there is now waterbody, skip to next iteration
        if (is.null(wbd)) {
          next
        } else { 
          # otherwise add the r_id
          wbd <- wbd %>% 
            mutate(r_id = id)
        }
        if (!exists("all_lakes")) {
          all_lakes <- wbd 
        } else {
          all_lakes <- rbind(all_lakes, wbd)
        }
      }
      all_lakes <- all_lakes %>% 
        select(r_id, comid, gnis_id:elevation, meandepth:maxdepth)
      write_csv(st_drop_geometry(all_lakes), 
                "data_acquisition/out/NHDPlus_stats_lakes.csv")
      all_lakes <- all_lakes %>% select(r_id, comid, gnis_name)
      st_write(all_lakes, "data_acquisition/out/NHDPlus_polygon.shp", append = F)
      return("data_acquisition/out/NHDPlus_polygon.shp")
    } else { # otherwise read in specified file
      polygons <- read_sf(file.path(yaml$poly_dir[1], yaml$poly_file[1])) 
      polygons <- st_zm(polygons)#drop z or m if present
      polygons <- st_make_valid(polygons) %>% 
        rename(r_id = yaml$unique_id)
      st_drop_geometry(polygons) %>% 
        mutate(py_id = r_id - 1) %>% #subtract 1 so that it matches with Py output
        write_csv(., "data_acquisition/out/user_polygon_withrowid.csv")
      st_write(polygons, "data_acquisition/out/user_polygon.shp", append = F)
      return("data_acquisition/out/user_polygon.shp")
    }
  } else {
    return(message("Not configured to use polygon area."))
  }
}

