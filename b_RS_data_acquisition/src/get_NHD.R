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
  if (grepl("poly", yaml$extent[1])) { # if polygon is specified in desired extent - either polycenter or polgon
    if (yaml$polygon[1] == "False") { # and no polygon is provided, then use nhdplustools
      # create sf
      wbd_pts <- st_as_sf(locations, 
                          crs = yaml$location_crs[1], 
                          coords = c("Longitude", "Latitude"))
      id = locations$id
      for (w in 1:length(id)) {
        aoi_name <- wbd_pts[wbd_pts$id == id[w],]
        lake <- get_waterbodies(AOI = aoi_name)
        if (w == 1) {
          all_lakes <- lake
        } else {
          all_lakes <- rbind(all_lakes, lake)
        }
      }
      all_lakes <- all_lakes %>% 
        select(id, comid, gnis_id:elevation, meandepth:maxdepth)
      write_csv(st_drop_geometry(all_lakes), 
                "data_acquisition/out/NHDPlus_stats_lakes.csv")
      all_lakes <- all_lakes %>% select(id, comid, gnis_name)
      st_write(all_lakes, "data_acquisition/out/NHDPlus_polygon.shp", append = F)
      return("data_acquisition/out/NHDPlus_polygon.shp")
    } else { # otherwise read in specified file
      polygons <- read_sf(file.path(yaml$poly_dir[1], yaml$poly_file[1])) 
      polygons <- st_zm(polygons)#drop z or m if present
      polygons <- st_make_valid(polygons)
      st_drop_geometry(polygons) %>% 
        rowid_to_column("r_id") %>% 
        mutate(py_id = r_id - 1) %>% #subract 1 so that it matches with Py output
        write_csv(., "data_acquisition/out/user_polygon_withrowid.csv")
      st_write(polygons, "data_acquisition/out/user_polygon.shp", append = F)
      return("data_acquisition/out/user_polygon.shp")
    }
  } else {
    return(message("Not configured to use polygon area."))
  }
}

