#' @title Run GEE script per tile
#' 
#' @description
#' Function to run the Landsat Pull for a specified WRS2 tile.
#' 
#' @param WRS_tile tile to run the GEE pull on
#' @param parent_path parent filepath where the remote sensing pull is occurring
#' @returns Silently writes a text file of the current tile (for use in the
#' Python script). Silently triggers GEE to start stack acquisition per tile.
#' 
#' 
run_GEE_per_tile <- function(WRS_tile, parent_path) {
  write_lines(WRS_tile, file.path(parent_path, "run/current_tile.txt"), sep = "")
  source_python(file.path(parent_path, "py/runGEEperTile.py"))
}