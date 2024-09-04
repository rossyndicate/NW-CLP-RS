#import modules
import ee
import time
import fiona
from datetime import date, datetime
import os 
from pandas import read_csv

# LOAD ALL THE CUSTOM FUNCTIONS -----------------------------------------------
# pull code begins on line 1222

def csv_to_eeFeat(df, proj):
  """Function to create an eeFeature from the location info

  Args:
      df: point locations .csv file with Latitude and Longitude
      proj: CRS projection of the points

  Returns:
      ee.FeatureCollection of the points 
  """
  features=[]
  for i in range(df.shape[0]):
    x,y = df.Longitude[i],df.Latitude[i]
    latlong =[x,y]
    loc_properties = {'system:index':str(df.id[i]), 'id':str(df.id[i])}
    g=ee.Geometry.Point(latlong, proj) 
    feature = ee.Feature(g, loc_properties)
    features.append(feature)
  ee_object = ee.FeatureCollection(features)
  return ee_object


def apply_scale_factors(image):
  """ Applies scaling factors for Landsat Collection 2 surface reflectance 
  and surface temperature products

  Args:
      image: one ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with band values overwritten by scaling factors
  """
  opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
  thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
  return image.addBands(opticalBands, None, True).addBands(thermalBands, None,True)


def dp_buff(image):
  """ Buffer ee.FeatureCollection sites from csv_to_eeFeat by user-specified radius

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.FeatureCollection of polygons resulting from buffered points
  """
  return image.buffer(ee.Number.parse(str(buffer)))


def add_rad_mask(image):
  """Mask out all pixels that are radiometrically saturated using the QA_RADSAT
  QA band.

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with additional band called 'radsat', where pixels with a value 
      of 0 are saturated for at least one SR band and a value of 1 is not saturated
  """
  #grab the radsat band
  satQA = image.select('radsat_qa')
  # all must be non-saturated per pixel
  satMask = satQA.eq(0).rename('radsat')
  return image.addBands(satMask).updateMask(satMask)


def cf_mask(image):
  """Masks any pixels obstructed by clouds and snow/ice

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with additional band called 'cfmask', where pixels are given values
      based on the QA_PIXEL band informaiton. Generally speaking, 0 is clear, values 
      greater than 0 are obstructed by clouds and/or snow/ice
  """
  #grab just the pixel_qa info
  qa = image.select('pixel_qa')
  cloudqa = (qa.bitwiseAnd(1 << 1).rename('cfmask') #dialated clouds value 1
    # high aerosol for LS8/9 is taken care of in sr_aerosol function
    .where(qa.bitwiseAnd(1 << 3), ee.Image(2)) # clouds value 2
    .where(qa.bitwiseAnd(1 << 4), ee.Image(3)) # cloud shadows value 3
    .where(qa.bitwiseAnd(1 << 5), ee.Image(4))) # snow value 4
  return image.addBands(cloudqa)


def sr_aerosol(image):
  """Flags any pixels in Landsat 8 and 9 that have 'medium' or 'high' aerosol QA flags from the
  SR_QA_AEROSOL band.

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with additional band called 'medHighAero', where pixels are given a value of 1
      if the aerosol QA flag is medium or high and 0 otherwise
  """
  aerosolQA = image.select('aerosol_qa')
  medHighAero = aerosolQA.bitwiseAnd(1 << 7).rename('medHighAero')# pull out mask out where aeorosol is med and high
  return image.addBands(medHighAero)


def Mndwi(image):
  """calculate the modified normalized difference water index per pixel

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      band where values calculated are the MNDWI value per pixel
  """
  return (image.expression('(GREEN - SWIR1) / (GREEN + SWIR1)', {
    'GREEN': image.select(['Green']),
    'SWIR1': image.select(['Swir1'])
  })).rename('mndwi')
  

def Mbsrv(image):
  """calculate the multi-band spectral relationship visible per pixel

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      band where values calculated are the MBSRV value per pixel
  """
  return (image.select(['Green']).add(image.select(['Red'])).rename('mbsrv'))


def Mbsrn(image):
  """calculate the multi-band spectral relationship near infrared per pixel

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      band where values calculated are the MBSRN value per pixel
  """
  return (image.select(['Nir']).add(image.select(['Swir1'])).rename('mbsrn'))


def Ndvi(image):
  """calculate the normalized difference vegetation index per pixel

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      band where values calculated are the NDVI value per pixel
  """
  return (image.expression('(NIR - RED) / (NIR + RED)', {
    'RED': image.select(['Red']),
    'NIR': image.select(['Nir'])
  })).rename('ndvi')


def Awesh(image):
  """calculate the automated water extent shadow per pixel

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      band where values calculated are the AWESH value per pixel
  """
  return (image.expression('Blue + 2.5 * Green + (-1.5) * mbsrn + (-0.25) * Swir2', {
    'Blue': image.select(['Blue']),
    'Green': image.select(['Green']),
    'mbsrn': Mbsrn(image).select(['mbsrn']),
    'Swir2': image.select(['Swir2'])
  })).rename('awesh')


## The DSWE Function itself    
def DSWE(image):
  """calculate the dynamic surface water extent per pixel
  
  Args:
      image: ee.Image of an ee.ImageCollection
      
  Returns:
      band where values calculated are the DSWE value per pixel
  """
  mndwi = Mndwi(image)
  mbsrv = Mbsrv(image)
  mbsrn = Mbsrn(image)
  awesh = Awesh(image)
  swir1 = image.select(['Swir1'])
  nir = image.select(['Nir'])
  ndvi = Ndvi(image)
  blue = image.select(['Blue'])
  swir2 = image.select(['Swir2'])
  # These thresholds are taken from the LS Collection 2 DSWE Data Format Control Book
  # Inputs are meant to be scaled reflectance values 
  t1 = mndwi.gt(0.124) # MNDWI greater than Wetness Index Threshold
  t2 = mbsrv.gt(mbsrn) # MBSRV greater than MBSRN
  t3 = awesh.gt(0) #AWESH greater than 0
  t4 = (mndwi.gt(-0.44)  #Partial Surface Water 1 thresholds
   .And(swir1.lt(0.09)) #900 for no scaling (LS Collection 1)
   .And(nir.lt(0.15)) #1500 for no scaling (LS Collection 1)
   .And(ndvi.lt(0.7)))
  t5 = (mndwi.gt(-0.5) #Partial Surface Water 2 thresholds
   .And(blue.lt(0.1)) #1000 for no scaling (LS Collection 1)
   .And(swir1.lt(0.3)) #3000 for no scaling (LS Collection 1)
   .And(swir2.lt(0.1)) #1000 for no scaling (LS Collection 1)
   .And(nir.lt(0.25))) #2500 for no scaling (LS Collection 1)
  t = (t1
    .add(t2.multiply(10))
    .add(t3.multiply(100))
    .add(t4.multiply(1000))
    .add(t5.multiply(10000)))
  noWater = (t.eq(0)
    .Or(t.eq(1))
    .Or(t.eq(10))
    .Or(t.eq(100))
    .Or(t.eq(1000)))
  hWater = (t.eq(1111)
    .Or(t.eq(10111))
    .Or(t.eq(11011))
    .Or(t.eq(11101))
    .Or(t.eq(11110))
    .Or(t.eq(11111)))
  mWater = (t.eq(111)
    .Or(t.eq(1011))
    .Or(t.eq(1101))
    .Or(t.eq(1110))
    .Or(t.eq(10011))
    .Or(t.eq(10101))
    .Or(t.eq(10110))
    .Or(t.eq(11001))
    .Or(t.eq(11010))
    .Or(t.eq(11100)))
  pWetland = t.eq(11000)
  lWater = (t.eq(11)
    .Or(t.eq(101))
    .Or(t.eq(110))
    .Or(t.eq(1001))
    .Or(t.eq(1010))
    .Or(t.eq(1100))
    .Or(t.eq(10000))
    .Or(t.eq(10001))
    .Or(t.eq(10010))
    .Or(t.eq(10100)))
  iDswe = (noWater.multiply(0)
    .add(hWater.multiply(1))
    .add(mWater.multiply(2))
    .add(pWetland.multiply(3))
    .add(lWater.multiply(4)))
  return iDswe.rename('dswe')


def calc_hill_shades(image, geo):
  """ caluclate the hill shade per pixel

  Args:
      image: ee.Image of an ee.ImageCollection
      geo: geometry of the WRS tile as wrs.geometry() in script

  Returns:
      a band named 'hillShade' where values calculated are the hill shade per 
      pixel. output is 0-255. 
  """
  MergedDEM = ee.Image("MERIT/DEM/v1_0_3").clip(geo.buffer(3000))
  hillShade = ee.Terrain.hillshade(MergedDEM, 
    ee.Number(image.get('SUN_AZIMUTH')), 
    ee.Number(image.get('SUN_ELEVATION')))
  hillShade = hillShade.rename(['hillShade'])
  return hillShade


def calc_hill_shadows(image, geo):
  """ caluclate the hill shadow per pixel
  
  Args:
      image: ee.Image of an ee.ImageCollection
      geo: geometry of the WRS tile as wrs.geometry() in script
  
  Returns:
      a band named 'hillShadow' where values calculated are the hill shadow per 
      pixel. output 1 where pixels are illumunated and 0 where they are shadowed.
  """
  MergedDEM = ee.Image("MERIT/DEM/v1_0_3").clip(geo.buffer(3000))
  hillShadow = ee.Terrain.hillShadow(MergedDEM, 
    ee.Number(image.get('SUN_AZIMUTH')),
    ee.Number(90).subtract(image.get('SUN_ELEVATION')), 
    30)
  hillShadow = hillShadow.rename(['hillShadow'])
  return hillShadow


## Remove geometries
def remove_geo(image):
  """ Funciton to remove the geometry from an ee.Image
  
  Args:
      image: ee.Image of an ee.ImageCollection
      
  Returns:
      ee.Image with the geometry removed
  """
  return image.setGeometry(None)

def apply_fill_mask_457(image):
  """ mask any fill values (0) in scaled raster for Landsat 4, 5, 7
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any values previously 0 are masked
  """
  b1_mask = image.select('SR_B1').gt(0)
  b2_mask = image.select('SR_B2').gt(0)
  b3_mask = image.select('SR_B3').gt(0)
  b4_mask = image.select('SR_B4').gt(0)
  b5_mask = image.select('SR_B5').gt(0)
  b7_mask = image.select('SR_B7').gt(0)
  fill_mask = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask()
    )
  return image.updateMask(fill_mask.eq(1))

def apply_fill_mask_89(image):
  """ mask any fill values (0) in scaled raster for Landsat 8,9
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any values previously 0 are masked
  """
  b1_mask = image.select('SR_B1').gt(0)
  b2_mask = image.select('SR_B2').gt(0)
  b3_mask = image.select('SR_B3').gt(0)
  b4_mask = image.select('SR_B4').gt(0)
  b5_mask = image.select('SR_B5').gt(0)
  b6_mask = image.select('SR_B6').gt(0)
  b7_mask = image.select('SR_B7').gt(0)
  fill_mask = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b6_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask()
    )
  return image.updateMask(fill_mask.eq(1))


# This should be applied AFTER scaling factors
# Mask values less than -0.01
def apply_realistic_mask_457(image):
  """ mask out unrealistic SR values (those less than -0.01) in Landsat 4, 5, 7
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any re-scaled values <-0.01 are masked
  """
  b1_mask = image.select('SR_B1').gt(-0.01)
  b2_mask = image.select('SR_B2').gt(-0.01)
  b3_mask = image.select('SR_B3').gt(-0.01)
  b4_mask = image.select('SR_B4').gt(-0.01)
  b5_mask = image.select('SR_B5').gt(-0.01)
  b7_mask = image.select('SR_B7').gt(-0.01)
  realistic = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask())
  return image.updateMask(realistic.eq(1))

def apply_realistic_mask_89(image):
  """ mask out unrealistic SR values (those less than -0.01) in Landsat 8, 9
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any re-scaled values <-0.01 are masked
  """
  b1_mask = image.select('SR_B1').gt(-0.01)
  b2_mask = image.select('SR_B2').gt(-0.01)
  b3_mask = image.select('SR_B3').gt(-0.01)
  b4_mask = image.select('SR_B4').gt(-0.01)
  b5_mask = image.select('SR_B5').gt(-0.01)
  b6_mask = image.select('SR_B6').gt(-0.01)
  b7_mask = image.select('SR_B7').gt(-0.01)
  realistic = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b6_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask())
  return image.updateMask(realistic.eq(1))

# mask high opacity (>0.3 after scaling) pixels
def apply_opac_mask(image):
  """ mask out instances where atmospheric opacity is greater than 0.3 in Landsat 
      5&7
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any pixels with SR_ATMOS_OPACITY greater than 0.3 are
      masked
  """
  opac = image.select("SR_ATMOS_OPACITY").multiply(0.001).lt(0.3)
  return image.updateMask(opac)


# function to split QA bits
def extract_qa_bits(qa_band, start_bit, end_bit, band_name):
  """
  Extracts specified quality assurance (QA) bits from a QA band. This function originated
  from https://calekochenour.github.io/remote-sensing-textbook/03-beginner/chapter13-data-quality-bitmasks.html

  Args:
      qa_band (ee.Image): The earth engine image QA band to extract the bits from.
      start_bit (int): The start bit of the QA bits to extract.
      end_bit (int): The end bit of the QA bits to extract (not inclusive)
      band_name (str): The name to give to the output band.

  Returns:
      ee.Image: A single band image of the extracted QA bit values.
  """
  # Initialize QA bit string/pattern to check QA band against
  qa_bits = 0
  # Add each specified QA bit flag value/string/pattern to the QA bits to check/extract
  for bit in range(end_bit):
    qa_bits += (1 << bit)
  # Return a single band image of the extracted QA bit values
  return (qa_band
    # Rename output band to specified name
    .select([0], [band_name])
    # Check QA band against specified QA bits to see what QA flag values are set
    .bitwiseAnd(qa_bits)
    # Get value that matches bitmask documentation
    # (0 or 1 for single bit,  0-3 or 0-N for multiple bits)
    .rightShift(start_bit))


# mask for high aerosol
def apply_high_aero_mask(image):
  """ mask out high aerosol pixels in Landsat 8/9 images
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image where any pixels with SR_QA_AEROSOL greater than or equal to 
      3 are masked
  """
  qa_aero = image.select('SR_QA_AEROSOL')
  aero = extract_qa_bits(qa_aero, 6, 8, 'aero_level')
  aero_mask = aero.lt(3)
  return image.updateMask(aero_mask)


## Set up the reflectance pull
def ref_pull_457_DSWE1(image):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # where the f mask is > 1, call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  
  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                        'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                        'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                        ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                        'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                        'med_emsd', 'med_trad', 'med_urad'])
            .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                    ['min_SurfaceTemp', 'min_cloud_dist']))
            .addBands(image.select(['Blue', 'Green', 'Red', 
                                    'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                  ['sd_Blue', 'sd_Green', 'sd_Red', 
                                  'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 
                                    'Swir1', 'Swir2', 
                                    'SurfaceTemp'],
                                  ['mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                  'mean_Swir1', 'mean_Swir2', 
                                  'mean_SurfaceTemp']))
            .addBands(image.select(['SurfaceTemp']))
            .updateMask(d.eq(1)) # only high confidence water
            .updateMask(hs.eq(1)) # only illuminated pixels
            .updateMask(f.eq(0))
            .updateMask(r.eq(1))
            .addBands(gt0) 
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(dswe1a)
            .addBands(clouds) 
            .addBands(hs)
            .addBands(h)
            ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out

## Set up the reflectance pull
def ref_pull_457_DSWE1a(image):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)
  or where the algal mask threshold is met

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1 or where
      the algal mask threshold is met
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  
  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                        'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                        'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                        ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                        'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                        'med_emsd', 'med_trad', 'med_urad'])
            .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                    ['min_SurfaceTemp', 'min_cloud_dist']))
            .addBands(image.select(['Blue', 'Green', 'Red', 
                                    'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                  ['sd_Blue', 'sd_Green', 'sd_Red', 
                                  'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 
                                    'Swir1', 'Swir2', 
                                    'SurfaceTemp'],
                                  ['mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                  'mean_Swir1', 'mean_Swir2', 
                                  'mean_SurfaceTemp']))
            .addBands(image.select(['SurfaceTemp']))
            .updateMask(dswe1a.eq(1)) # mask for dswe1a
            .updateMask(hs.eq(1)) # only illuminated pixels
            .updateMask(f.eq(0))
            .updateMask(r.eq(1))
            .addBands(gt0) 
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(dswe1a)
            .addBands(clouds) 
            .addBands(hs)
            .addBands(h)
            ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
      )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out

def ref_pull_457_DSWE3(image):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 3 (high confidence
  vegetated pixel)

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 3
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  
  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                      'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                      'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                      ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                      'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                      'med_emsd', 'med_trad', 'med_urad'])
          .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                  ['min_SurfaceTemp', 'min_cloud_dist']))
          .addBands(image.select(['Blue', 'Green', 'Red', 
                                  'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                ['sd_Blue', 'sd_Green', 'sd_Red', 
                                'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 
                                    'Swir1', 'Swir2', 
                                    'SurfaceTemp'],
                                  ['mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                  'mean_Swir1', 'mean_Swir2', 
                                  'mean_SurfaceTemp']))
          .addBands(image.select(['SurfaceTemp']))
          .updateMask(d.eq(3)) # only vegetated water
          .updateMask(hs.eq(1)) # only illuminated pixels
          .updateMask(f.eq(0))
          .updateMask(r.eq(1))
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
      )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE1(image):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # process image with st SR cloud mask
  a = sr_aerosol(image).select('medHighAero')
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                      'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                      'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                      'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                      'med_emsd', 'med_trad', 'med_urad'])
          .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                  ['min_SurfaceTemp', 'min_cloud_dist']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 
                                  'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                ['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 
                                'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 
                                  'Swir1', 'Swir2', 
                                  'SurfaceTemp'],
                                ['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                'mean_Swir1', 'mean_Swir2', 
                                'mean_SurfaceTemp']))
          .addBands(image.select(['SurfaceTemp']))
          .updateMask(d.eq(1)) # only high confidence water
          .updateMask(hs.eq(1)) # only illuminated pixels
          .updateMask(f.eq(0))
          .updateMask(r.eq(1))
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE1a(image):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)
  or the algal threshold has been met

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1 or the algal 
      threshold has been met
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # process image with st SR cloud mask
  a = sr_aerosol(image).select('medHighAero')
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')

  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                      'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                      'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                      'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                      'med_emsd', 'med_trad', 'med_urad'])
          .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                  ['min_SurfaceTemp', 'min_cloud_dist']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 
                                  'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                ['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 
                                'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 
                                  'Swir1', 'Swir2', 
                                  'SurfaceTemp'],
                                ['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                'mean_Swir1', 'mean_Swir2', 
                                'mean_SurfaceTemp']))
          .addBands(image.select(['SurfaceTemp']))
          .updateMask(dswe1a.eq(1)) # only algal mask
          .updateMask(hs.eq(1)) # only illuminated pixels
          .updateMask(f.eq(0))
          .updateMask(r.eq(1))
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE3(image):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 3 (high confidence vegetated
  pixels)

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 3
  """
  # process image with the radsat mask
  r = add_rad_mask(image).select('radsat')
  # process image with cfmask
  f = cf_mask(image).select('cfmask')
  # process image with st SR cloud mask
  a = sr_aerosol(image).select('medHighAero')
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  
  #apply dswe function
  d = DSWE(image).select('dswe')
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # band where dswe is 3 and apply all masks
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    )
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    .updateMask(f.eq(0))
    .updateMask(r.eq(1))
    .selfMask()
    )
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                      'SurfaceTemp', 'temp_qa', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
                      'ST_EMSD', 'ST_TRAD', 'ST_URAD'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                      'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                      'med_emsd', 'med_trad', 'med_urad'])
          .addBands(image.select(['SurfaceTemp', 'ST_CDIST'],
                                  ['min_SurfaceTemp', 'min_cloud_dist']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 
                                  'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
                                ['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 
                                'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp']))
          .addBands(image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 
                                  'Swir1', 'Swir2', 
                                  'SurfaceTemp'],
                                ['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 
                                'mean_Swir1', 'mean_Swir2', 
                                'mean_SurfaceTemp']))
          .addBands(image.select(['SurfaceTemp']))
          .updateMask(d.eq(3)) # only vegetated water
          .updateMask(hs.eq(1)) # only illuminated pixels
          .updateMask(f.eq(0))
          .updateMask(r.eq(1))
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 
            'med_temp_qa','med_atran', 'med_drad', 'med_emis',
            'med_emsd', 'med_trad', 'med_urad']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted()
      .forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), outputPrefix = 'mean_', sharedInputs = False)
    )
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def maximum_no_of_tasks(MaxNActive, waitingPeriod):
  """ Function to limit the number of tasks sent to Earth Engine at one time to avoid time out errors
  
  Args:
      MaxNActive: maximum number of tasks that can be active in Earth Engine at one time
      waitingPeriod: time to wait between checking if tasks are completed, in seconds
      
  Returns:
      None.
  """
  ##maintain a maximum number of active tasks
  ## initialize submitting jobs
  ts = list(ee.batch.Task.list())
  NActive = 0
  for task in ts:
     if ('RUNNING' in str(task) or 'READY' in str(task)):
         NActive += 1
  ## wait if the number of current active tasks reach the maximum number
  ## defined in MaxNActive
  while (NActive >= MaxNActive):
    time.sleep(waitingPeriod) # if reach or over maximum no. of active tasks, wait for 2min and check again
    ts = list(ee.batch.Task.list())
    NActive = 0
    for task in ts:
      if ('RUNNING' in str(task) or 'READY' in str(task)):
        NActive += 1
  return()


# get locations and yml from data folder
yml = read_csv('data_acquisition/in/yml.csv')

eeproj = yml['ee_proj'][0]
#initialize GEE
ee.Initialize(project = eeproj)

# get current tile
with open('data_acquisition/out/current_tile.txt', 'r') as file:
  tiles = file.read()

# get EE/Google settings from yml file
proj = yml['proj'][0]
proj_folder = yml['proj_folder'][0]

# get/save start date
yml_start = yml['start_date'][0]
yml_end = yml['end_date'][0]

# store run date for versioning
run_date = yml['run_date'][0]

if yml_end == 'today':
  yml_end = run_date

# gee processing settings
buffer = yml['site_buffer'][0]
cloud_filt = yml['cloud_filter'][0]
cloud_thresh = yml['cloud_thresh'][0]

try: 
  dswe = yml['DSWE_setting'][0].astype(str)
except AttributeError: 
  dswe = yml['DSWE_setting'][0]

# get extent info
extent = (yml['extent'][0]
  .split('+'))

if 'site' in extent:
  locations = read_csv('data_acquisition/in/locs.csv')
  # convert locations to an eeFeatureCollection
  locs_feature = csv_to_eeFeat(locations, yml['location_crs'][0])


if 'polygon' in extent:
  #if polygon is in extent, check for shapefile
  shapefile = yml['polygon'][0]
  # if shapefile provided by user 
  if shapefile == True:
    # load the shapefile into a Fiona object
    with fiona.open('data_acquisition/out/user_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  else: #otherwise use the NHDPlus file
    # load the shapefile into a Fiona object
    with fiona.open('data_acquisition/out/NHDPlus_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  # Create an ee.Feature for each shape
  features = [ee.Feature(shape, {}) for shape in shapes]
  # Create an ee.FeatureCollection from the ee.Features
  poly_feat = ee.FeatureCollection(features)


if 'polycenter' in extent:
  if yml['polygon'][0] == True:
    centers_csv = read_csv('data_acquisition/out/user_polygon_centers.csv')
    centers_csv = (centers_csv.rename(columns={'poi_latitude': 'Latitude', 
      'poi_longitude': 'Longitude',
      'r_id': 'id'}))
    # load the shapefile into a Fiona object
    centers = csv_to_eeFeat(centers_csv, 'EPSG:4326')
  else: #otherwise use the NHDPlus file
    centers_csv = read_csv('data_acquisition/out/NHDPlus_polygon_centers.csv')
    centers_csv = (centers_csv.rename(columns={'poi_latitude': 'Latitude', 
      'poi_longitude': 'Longitude',
      'r_id': 'id'}))
    centers = csv_to_eeFeat(centers_csv, 'EPSG:4326')
  # Create an ee.FeatureCollection from the ee.Features
  ee_centers = ee.FeatureCollection(centers)    

  

##############################################
##---- CREATING EE FEATURECOLLECTIONS   ----##
##############################################


wrs = (ee.FeatureCollection('projects/ee-ls-c2-srst/assets/WRS2_descending')
  .filterMetadata('PR', 'equals', tiles))

wrs_path = int(tiles[:3])
wrs_row = int(tiles[-3:])

#grab images and apply scaling factors
l7 = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end)
    .filterDate('1999-05-28', '2019-12-31') # for valid dates
    .filter(ee.Filter.eq('WRS_PATH', wrs_path))
    .filter(ee.Filter.eq('WRS_ROW', wrs_row)))
l5 = (ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end)
    .filter(ee.Filter.eq('WRS_PATH', wrs_path))
    .filter(ee.Filter.eq('WRS_ROW', wrs_row)))
l4 = (ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end)
    .filter(ee.Filter.eq('WRS_PATH', wrs_path))
    .filter(ee.Filter.eq('WRS_ROW', wrs_row)))
    
# merge collections by image processing groups
ls457 = ee.ImageCollection(l4.merge(l5).merge(l7))
    
# existing band names
bn457 = (['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 
  'QA_PIXEL', 'SR_CLOUD_QA', 'QA_RADSAT', 'ST_B6', 
  'ST_QA', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  
# new band names
bns457 = (['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
  'pixel_qa', 'cloud_qa', 'radsat_qa', 'SurfaceTemp', 
  'temp_qa', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  

#grab image stacks
l8 = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end)
    .filter(ee.Filter.eq('WRS_PATH', wrs_path))
    .filter(ee.Filter.eq('WRS_ROW', wrs_row)))
l9 = (ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end)
    .filter(ee.Filter.eq('WRS_PATH', wrs_path))
    .filter(ee.Filter.eq('WRS_ROW', wrs_row)))


# merge collections by image processing groups
ls89 = ee.ImageCollection(l8.merge(l9))
    
# existing band names
bn89 = (['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 
  'QA_PIXEL', 'SR_QA_AEROSOL', 'QA_RADSAT', 'ST_B10', 
  'ST_QA', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  
# new band names
bns89 = (['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
  'pixel_qa', 'aerosol_qa', 'radsat_qa', 'SurfaceTemp', 
  'temp_qa', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
 

##########################################
##---- LANDSAT 457 ACQUISITION      ----##
##########################################

## run the pull for LS457, looping through all extents from yml
for e in extent:
  
  geo = wrs.geometry()
  
  if e == 'site':
    ## get locs feature and buffer ##
    feat = (locs_feature
      .filterBounds(geo)
      .map(dp_buff))
  elif e == 'polygon':
    ## get the polygon stack ##
    feat = (poly_feat
      .filterBounds(geo))
  elif e == 'polycenter':
    ## get centers feature and buffer ##
    feat = (ee_centers
      .filterBounds(geo)
      .map(dp_buff))
  else: 
    print('Extent not identified. Check configuration file.')
  
  ## process 457 stack
  #snip the ls data by the geometry of the location points    
  locs_stack_ls457 = (ls457
    .filterBounds(feat.geometry()) 
    # apply fill mask and scaling factors
    .map(apply_fill_mask_457)
    .map(apply_scale_factors)
    .map(apply_realistic_mask_457)
    .map(apply_opac_mask))
  
  # rename bands for ease
  locs_stack_ls457 = locs_stack_ls457.select(bn457, bns457)
  
  # pull DSWE1 variations as configured
  if '1' in dswe:
    # pull DSWE1 and DSWE1 with algal mask if configured
    if '1a' in dswe:
      print('Starting Landsat 4, 5, 7 DSWE 1 acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_457_D1 = locs_stack_ls457.map(ref_pull_457_DSWE1).flatten()
      locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1 = proj+'_'+e+'_LS457_C2_SRST_DSWE1_'+str(tiles)+'_v'+run_date
      locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                              description = locs_srname_457_D1,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_457_D1.start()
      print('Completed Landsat 4, 5, 7 DSWE 1 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
      print('Starting Landsat 4, 5, 7 DSWE 1a acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_457_D1a = locs_stack_ls457.map(ref_pull_457_DSWE1a).flatten()
      locs_out_457_D1a = locs_out_457_D1a.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1a = proj+'_'+e+'_LS457_C2_SRST_DSWE1a_'+str(tiles)+'_v'+run_date
      locs_dataOut_457_D1a = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1a,
                                              description = locs_srname_457_D1a,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_457_D1a.start()
      print('Completed Landsat 4, 5, 7 DSWE 1a stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
    
    else: 
      print('Not configured to acquire DSWE 1a stack for Landsat 4, 5, 7 for ' + e + ' configuration')
      # and pull DSWE1
      print('Starting Landsat 4, 5, 7 DSWE1 acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_457_D1 = locs_stack_ls457.map(ref_pull_457_DSWE1).flatten()
      locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1 = proj+'_'+e+'_LS457_C2_SRST_DSWE1_'+str(tiles)+'_v'+run_date
      locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                              description = locs_srname_457_D1,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_457_D1.start()
      print('Completed Landsat 4, 5, 7 DSWE 1 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 1 or DSWE 1a stack for Landsat 4, 5, 7 for ' + e + ' configuration')
  
  # pull DSWE3 variants if configured
  if '3' in dswe:
    # pull DSWE3
    print('Starting Landsat 4, 5, 7 DSWE3 acquisition for ' + e + ' configuration at tile ' + str(tiles))
    locs_out_457_D3 = locs_stack_ls457.map(ref_pull_457_DSWE3).flatten()
    locs_out_457_D3 = locs_out_457_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D3 = proj+'_'+e+'_LS457_C2_SRST_DSWE3_'+str(tiles)+'_v'+run_date
    locs_dataOut_457_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D3,
                                            description = locs_srname_457_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_457_D3.start()
    print('Completed Landsat 4, 5, 7 DSWE 3 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 3 stack for Landsat 4, 5, 7 for ' + e + ' configuration')



#########################################
##---- LANDSAT 89 SITE ACQUISITION ----##
#########################################

for e in extent:
  
  geo = wrs.geometry()
  
  # use extent configuration to define feature for pull
  if e == 'site':
    ## get locs feature and buffer ##
    feat = (locs_feature
      .filterBounds(geo)
      .map(dp_buff))
  elif e == 'polygon':
    ## get the polygon stack ##
    feat = (poly_feat
      .filterBounds(geo))
  elif e == 'polycenter':
    ## get centers feature and buffer ##
    feat = (ee_centers
      .filterBounds(geo)
      .map(dp_buff))
  else: 
    print('Extent not identified. Check configuration file.')
  
  # snip the ls data by the geometry of the location points    
  locs_stack_ls89 = (ls89
    .filterBounds(feat.geometry()) 
    # apply fill mask and scaling factors
    .map(apply_fill_mask_89)
    .map(apply_scale_factors)
    .map(apply_realistic_mask_89)
    .map(apply_high_aero_mask))
  
  # rename bands for ease
  locs_stack_ls89 = locs_stack_ls89.select(bn89, bns89)
  
  if '1' in dswe:
    if '1a' in dswe:
      print('Starting Landsat 8, 9 DSWE1 acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_89_D1 = locs_stack_ls89.map(ref_pull_89_DSWE1).flatten()
      locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1 = proj+'_'+ e + '_LS89_C2_SRST_DSWE1_'+str(tiles)+'_v'+run_date
      locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                              description = locs_srname_89_D1,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_89_D1.start()
      print('Completed Landsat 8, 9 DSWE 1 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
      print('Starting Landsat 8, 9 DSWE 1a acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_89_D1a = locs_stack_ls89.map(ref_pull_89_DSWE1a).flatten()
      locs_out_89_D1a = locs_out_89_D1a.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1a = proj+'_'+e+'_LS89_C2_SRST_DSWE1a_'+str(tiles)+'_v'+run_date
      locs_dataOut_89_D1a = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1a,
                                              description = locs_srname_89_D1a,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_89_D1a.start()
      print('Completed Landsat 8, 9 DSWE 1a stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
    else:
      print('Not configured to acquire DSWE 1a stack for Landsat 8, 9 for ' + e + ' configuration')
      print('Starting Landsat 8, 9 DSWE1 acquisition for ' + e + ' configuration at tile ' + str(tiles))
      locs_out_89_D1 = locs_stack_ls89.map(ref_pull_89_DSWE1).flatten()
      locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1 = proj+'_'+e+'_LS89_C2_SRST_DSWE1_'+str(tiles)+'_v'+run_date
      locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                              description = locs_srname_89_D1,
                                              folder = proj_folder,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                              'med_emsd', 'med_trad', 'med_urad',
                                              'min_SurfaceTemp', 'min_cloud_dist',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'kurt_SurfaceTemp', 
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Check how many existing tasks are running and take a break of 120 secs if it's >25 
      maximum_no_of_tasks(10, 120)
      #Send next task.                                        
      locs_dataOut_89_D1.start()
      print('Completed Landsat 8, 9 DSWE 1 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 8, 9 for ' + e + ' configuration')
  
  if '3' in dswe:
    print('Starting Landsat 8, 9 DSWE3 acquisition for ' + e + ' configuration at tile ' + str(tiles))
    locs_out_89_D3 = locs_stack_ls89.map(ref_pull_89_DSWE3).flatten()
    locs_out_89_D3 = locs_out_89_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D3 = proj+'_'+e+'_LS89_C2_SRST_DSWE3_'+str(tiles)+'_v'+run_date
    locs_dataOut_89_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D3,
                                            description = locs_srname_89_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_89_D3.start()
    print('Completed Landsat 8, 9 DSWE 3 stack acquisitions for ' + e + ' configuration at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 3 stack for Landsat 8,9 for ' + e + ' configuration')


##############################################
##---- LANDSAT 457 METADATA ACQUISITION ----##
##############################################

print('Starting Landsat 4, 5, 7 metadata acquisition for tile ' +str(tiles))

## get metadata ##
meta_srname_457 = proj+'_metadata_LS457_C2_'+str(tiles)+'_v'+run_date
meta_dataOut_457 = (ee.batch.Export.table.toDrive(collection = ls457,
                                        description = meta_srname_457,
                                        folder = proj_folder,
                                        fileFormat = 'csv'))

#Check how many existing tasks are running and take a break of 120 secs if it's >25 
maximum_no_of_tasks(10, 120)
#Send next task.                                        
meta_dataOut_457.start()

print('Completed Landsat 4, 5, 7 metadata acquisition for tile ' + str(tiles))


#############################################
##---- LANDSAT 89 METADATA ACQUISITION ----##
#############################################

print('Starting Landsat 8, 9 metadata acquisition for tile ' +str(tiles))

## get metadata ##
meta_srname_89 = proj+'_metadata_LS89_C2_'+str(tiles)+'_v'+run_date
meta_dataOut_89 = (ee.batch.Export.table.toDrive(collection = ls89,
                                        description = meta_srname_89,
                                        folder = proj_folder,
                                        fileFormat = 'csv'))

#Check how many existing tasks are running and take a break of 120 secs if it's >25 
maximum_no_of_tasks(10, 120)
#Send next task.                                        
meta_dataOut_89.start()

print('completed Landsat 8, 9 metadata acquisition for tile ' + str(tiles))

