#' Function to calculate the handoff coefficients between Landsat 9 and 8, which
#' will be used to normalize the LS 9 to relative LS 8 values
#' 
#' @param filtered filtered regional dataset used to calculate handoffs
#' @param band any band name that is shared between the two satellites
#' @returns silently returns summary .csvs in the mid folder, and figures of the
#' polynomial regression
#' 
#' 
calculate_9_8_handoff <- function(filtered, band){
  # make sure folder paths exist
  dir.create('2_calculate_handoff_coefficients/mid/')
  dir.create('2_calculate_handoff_coefficients/figs/')
  # note that the filter is not as stringent, since we have a much smaller 
  # timeframe to work from. 
  filter_summary <- filtered %>%
    filter(date > ymd('2021-09-27'), 
           mission %in% c('LANDSAT_8', 'LANDSAT_9')) %>% 
    group_by(mission, rowid) %>% 
    summarize(n_years = length(unique(year(date)))) %>% 
    filter(n_years >= 2) %>% 
    ungroup()
  
  # filter out for Landsat 8, limiting input sites to those with 1y
  y <- filtered %>%
    filter(date > ymd('2021-09-27'), 
           mission == 'LANDSAT_8') %>% 
    inner_join(., filter_summary)
  y_q <- y %>%
    .[,band] %>%
    as.vector(.)
  y_q <- y_q[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  # do the same for LS 9
  x <- filtered %>% 
    filter(date > ymd('2021-09-27'), 
           mission == 'LANDSAT_9') %>% 
    inner_join(., filter_summary)
  x_q <- x %>%
    .[,band] %>%
    as.vector(.)
  # and calculate quantiles, dropping 0 and 1
  x_q <- x_q[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  poly <- lm(y_q ~ poly(x_q, 2, raw = T))
  
  # plot and save handoff fig
  jpeg(file.path('2_calculate_handoff_coefficients/figs/', 
       paste0(band, '_9_8_poly_handoff.jpg')), 
       width = 350, height = 350)
  plot(y_q ~ x_q,
       main = paste0(band, ' LS 9-8 handoff'),
       ylab = '0.01 Quantile Values for LS8 Rrs',
       xlab = '0.01 Quantile Values for LS7 Rrs')
  lines(sort(x_q),
        fitted(poly)[order(x_q)],
        col = "blue",
        type = "l")
  dev.off()
  
  # plot and save residuals from fit
  jpeg(file.path('2_calculate_handoff_coefficients/figs/', 
                 paste0(band, '_9_8_poly_residuals.jpg')), 
       width = 350, height = 200)
  plot(poly$residuals,
       main = paste0(band, ' LS 9-8 poly handoff residuals'))
  dev.off()
  
  # create a summary table
  summary <- tibble(band = band, 
               intercept = poly$coefficients[[1]], 
               B1 = poly$coefficients[[2]], 
               B2 = poly$coefficients[[3]],
               min_in_val = min(x_q),
               max_in_val = max(x_q),
               sat_corr = 'LANDSAT_9',
               sat_to = 'LANDSAT_8',
               L8_scene_count = length(unique(y$system.index)),
               L9_scene_count = length(unique(x$system.index))) 
  write_csv(summary, file.path('2_calculate_handoff_coefficients/mid/',
                               paste0(band, '_9_8_poly_handoff.csv')))
}
