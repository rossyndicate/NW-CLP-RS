#' @title Landsat 8 to 7 Handoff Coefficients
#' 
#' @description
#' Function to calculate the handoff coefficients between Landsat 8 and 7, which
#' will be used to normalize the LS 8 to relative LS 7 values
#' 
#' @param filtered filtered regional dataset used to calculate handoffs
#' @param band any band name that is shared between the two satellites
#' @returns silently returns summary .csvs in the mid folder, and figures of the
#' polynomial regression
#' 
#' 
calculate_8_7_handoff <- function(filtered, band){
  # filter for the overlapping date range from sites that have at least 10y of data
  filter_summary <- filtered %>%
    filter(date > ymd("2013-02-11"), 
           date < ymd("2022-04-16"), 
           mission %in% c("LANDSAT_8", "LANDSAT_7")) %>% 
    group_by(mission, rowid) %>% 
    summarize(n_years = length(unique(year(date)))) %>% 
    filter(n_years >= 10) %>% 
    ungroup()
  
  # filter out for Landsat 7, limiting input sites to those with 10y
  y <- filtered %>% 
    filter(date > ymd("2013-02-11"), 
           date < ymd("2022-04-16"), 
           mission == "LANDSAT_7") %>% 
    inner_join(., filter_summary)
  y_q <- y %>%
    .[,band] %>%
    as.vector(.)
  # and calculate quantiles, dropping 0 and 1
  y_q <- y_q[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  # do the same for LS 8
  x <- filtered %>%
    filter(date > ymd("2013-02-11"), 
           date < ymd("2022-04-16"), 
           mission == "LANDSAT_8") %>% 
    inner_join(., filter_summary)
  x_q <- x %>%
    .[,band] %>%
    as.vector(.)
  x_q <- x_q[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  poly <- lm(y_q ~ poly(x_q, 2, raw = T))
  
  # plot and save handoff fig
  jpeg(file.path("c_calculate_handoff_coefficients/figs/", 
       paste0(band, "_8_7_poly_handoff.jpg")), 
       width = 350, height = 350)
  plot(y_q ~ x_q,
       main = paste0(band, " LS 8-7 handoff"),
       ylab = "0.01 Quantile Values for LS7 Rrs",
       xlab = "0.01 Quantile Values for LS8 Rrs")
  lines(sort(x_q),
        fitted(poly)[order(x_q)],
        col = "blue",
        type = "l")
  dev.off()
  
  # plot and save residuals from fit
  jpeg(file.path("c_calculate_handoff_coefficients/figs/", 
                 paste0(band, "_8_7_poly_residuals.jpg")), 
       width = 350, height = 200)
  plot(poly$residuals,
       main = paste0(band, " LS 8-7 poly handoff residuals"))
  dev.off()
  
  # create a summary table
  summary <- tibble(band = band, 
               intercept = poly$coefficients[[1]], 
               B1 = poly$coefficients[[2]], 
               B2 = poly$coefficients[[3]],
               min_in_val = min(x_q),
               max_in_val = max(x_q),
               sat_corr = "LANDSAT_8",
               sat_to = "LANDSAT_7",
               L7_scene_count = length(unique(y$system.index)),
               L8_scene_count = length(unique(x$system.index))) 
  write_csv(summary, file.path("c_calculate_handoff_coefficients/mid/",
                               paste0(band, "_8_7_poly_handoff.csv")))
}
