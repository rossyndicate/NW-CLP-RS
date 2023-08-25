lm75 <- function(filtered_dataset, band){
  print(paste0(band, ' model summary'))
  x <- filtered %>%
    filter(date > as.Date('1999-04-15'), date < as.Date('2013-06-05'), mission == 'LANDSAT_7')
  print(paste0('LS7 scenes: ', length(unique(y$`system:index`)), ' values: ', nrow(y)))
  x <- x %>%
    .[,band] %>%
    as.vector(.)
  x <- x[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  y = filtered %>%
    filter(date > as.Date('1999-04-15'), date < as.Date('2013-06-05'), mission == 'LANDSAT_5')
  print(paste0('LS5 scenes: ', length(unique(x$`system:index`)), ' values: ', nrow(x)))
  y <- y %>%
    .[,band] %>%
    as.vector(.)
  y <- y[[1]] %>%
    quantile(., seq(.01,.99, .01))
  
  poly <- lm(y~poly(x, 2, raw = T))
  print(summary(poly))
  
  lm <- lm(y~x)
  print(summary(lm))
  
  plot(y~x,
       main = paste0(band, ' LS5-7 handoff'),
       xlab = '0.01 Quantile Values for LS7 Rrs',
       ylab = '0.01 Quantile Values for LS5 Rrs')
  
  lines(sort(x),
        fitted(lm)[order(x)],
        col = "red",
        type = "l")
  
  df <- tibble(band = band, intercept = lm$coefficients[[1]], B1 = lm$coefficients[[2]], B2 = lm$coefficients[[3]])
  return(df)
}