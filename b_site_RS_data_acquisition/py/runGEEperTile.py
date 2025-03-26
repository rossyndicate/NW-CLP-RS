#import modules
import ee
import time
# import fiona
from datetime import date, datetime
import os 
from pandas import read_csv


# get yml from data folder
yml = read_csv('b_site_RS_data_acquisition/run/yml.csv')

eeproj = yml['ee_proj'][0]
#initialize GEE
ee.Initialize(project = eeproj)

# get current tile
with open('b_site_RS_data_acquisition/run/current_tile.txt', 'r') as file:
  tiles = file.read()

# get EE/Google settings from yml file
proj = yml['proj'][0]
proj_folder = yml['proj_folder'][0]
run_date = yml['run_date'][0]

# create folder with version number
folder_version = proj_folder + "_v" + run_date

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

def csv_to_eeFeat(df, proj):
  """Function to create an eeFeature from the location data

  Args:
      df: point locations .csv file with Latitude and Longitude
      proj: CRS projection of the points

  Returns:
      ee.FeatureCollection of the points 
  """
  features=[]
  # Calculate start and end indices for the current chunk
  for i in range(len(df)):
    try:
      x,y = df.Longitude[i],df.Latitude[i]
      latlong = [x,y]
      loc_properties = {'system:index':str(df.id[i]), 'id':str(df.id[i])}
      g = ee.Geometry.Point(latlong, proj) 
      feature = ee.Feature(g, loc_properties)
      features.append(feature)
    except KeyError as e:
      print(f"KeyError at index {i}, skipping to next iteration")
      continue  # skip to the next iteration
  return ee.FeatureCollection(features)

if 'site' in extent:
  # create file name of location data
  locs_fn = os.path.join("b_site_RS_data_acquisition/out/locations/", ("locations_" + tiles + ".csv"))
  # read in locations file
  locations_subset = read_csv(locs_fn)
  # convert locations to an eeFeatureCollection
  locs_feature = csv_to_eeFeat(locations_subset, yml['location_crs'][0])


if 'polygon' in extent:
  #if polygon is in extent, check for shapefile
  shapefile = yml['polygon'][0]
  # if shapefile provided by user 
  if shapefile == True:
    # load the shapefile into a Fiona object
    with fiona.open('b_site_RS_data_acquisition/run/user_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  else: #otherwise use the NHDPlus file
    # load the shapefile into a Fiona object
    with fiona.open('b_site_RS_data_acquisition/run/NHDPlus_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  # Create an ee.Feature for each shape
  features = [ee.Feature(shape, {}) for shape in shapes]
  # Create an ee.FeatureCollection from the ee.Features
  poly_feat = ee.FeatureCollection(features)


if 'polycenter' in extent:
  if yml['polygon'][0] == True:
    centers_csv = read_csv('b_site_RS_data_acquisition/run/user_polygon_centers.csv')
    centers_csv = (centers_csv.rename(columns={'poi_latitude': 'Latitude', 
      'poi_longitude': 'Longitude',
      'r_id': 'id'}))
    # load the shapefile into a Fiona object
    centers = csv_to_eeFeat(centers_csv, 'EPSG:4326')
  else: #otherwise use the NHDPlus file
    centers_csv = read_csv('b_site_RS_data_acquisition/run/NHDPlus_polygon_centers.csv')
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
bn457 = (["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7", 
  "QA_PIXEL", "SR_ATMOS_OPACITY", "QA_RADSAT", "ST_B6"])
  
# new band names
bns457 = (["Blue", "Green", "Red", "Nir", "Swir1", "Swir2", 
  "pixel_qa", "opacity_qa", "radsat_qa", "SurfaceTemp"])
  

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
bn89 = (["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7", 
  "QA_PIXEL", "SR_QA_AEROSOL", "QA_RADSAT", "ST_B10"])
  
# new band names
bns89 = (["Aerosol", "Blue", "Green", "Red", "Nir", "Swir1", "Swir2",
  "pixel_qa", "aerosol_qa", "radsat_qa", "SurfaceTemp"])
 
 
#################################
# LOAD ALL THE CUSTOM FUNCTIONS #
#################################



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


def apply_rad_mask(image):
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
  satMask = satQA.eq(0)
  return image.updateMask(satMask)


def add_cf_mask(image):
  """Creates a binary band for contaminated or clear pixels
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with additional band called 'cfmask'
  """
  #grab just the pixel_qa info
  qa = image.select('pixel_qa')
  cloudqa = (qa.bitwiseAnd(1 << 1).rename('cfmask') #dialated clouds value 1
    # high aerosol for LS8/9 is taken care of in sr_aerosol function
    .where(qa.bitwiseAnd(1 << 3), ee.Image(2)) # clouds value 2
    .where(qa.bitwiseAnd(1 << 4), ee.Image(3)) # cloud shadows value 3
    .where(qa.bitwiseAnd(1 << 5), ee.Image(4))) # snow value 4
  return image.addBands(cloudqa)


### update these to use renamed bands
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
def add_realistic_mask_457(image):
  """ mask out unrealistic SR values (those less than -0.01) in Landsat 4, 5, 7
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image with a 1/0 mask for realistic values
  """
  b1_mask = image.select('Blue').gt(-0.01)
  b2_mask = image.select('Green').gt(-0.01)
  b3_mask = image.select('Red').gt(-0.01)
  b4_mask = image.select('Nir').gt(-0.01)
  b5_mask = image.select('Swir1').gt(-0.01)
  b7_mask = image.select('Swir2').gt(-0.01)
  realistic = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask()).rename('real')
  return image.addBands(realistic)


def add_realistic_mask_89(image):
  """ mask out unrealistic SR values (those less than -0.01) in Landsat 8, 9
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image with new band for realistic mask
  """
  b1_mask = image.select('Aerosol').gt(-0.01)
  b2_mask = image.select('Blue').gt(-0.01)
  b3_mask = image.select('Green').gt(-0.01)
  b4_mask = image.select('Red').gt(-0.01)
  b5_mask = image.select('Nir').gt(-0.01)
  b6_mask = image.select('Swir1').gt(-0.01)
  b7_mask = image.select('Swir2').gt(-0.01)
  realistic = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b6_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask()).rename('real')
  return image.addBands(realistic)


# This should be applied AFTER scaling factors
# Mask values greater than 0.2
def add_sun_glint_mask(image):
  """ mask out pixels likely affected by sun glint (those greater than 0.2) 
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image with a 1 (unlikely glint) / 0 (likely glint) mask for pixels in
      all bands but Aerosol
  """
  b1_mask = image.select('Blue').lt(0.2)
  b2_mask = image.select('Green').lt(0.2)
  b3_mask = image.select('Red').lt(0.2)
  b4_mask = image.select('Nir').lt(0.2)
  b5_mask = image.select('Swir1').lt(0.2)
  b7_mask = image.select('Swir2').lt(0.2)
  no_glint = (b1_mask.eq(1)
    .And(b2_mask.eq(1))
    .And(b3_mask.eq(1))
    .And(b4_mask.eq(1))
    .And(b5_mask.eq(1))
    .And(b7_mask.eq(1))
    .selfMask()).rename('no_glint')
  return image.addBands(no_glint)

# This should be applied AFTER scaling factors
# Flag IR values greater than 0.1
def add_ir_glint_flag(image):
  """ flags infrared bands (nir, swir) where pixels likely affected by sun glint 
      (those greater than or equal to 0.1) 
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image with a 1 (flagged for ir glint) / 0 (no flag for ir glint) 
      for pixels in all ir bands (nir, swir)
  """
  b4_flag = image.select('Nir').gte(0.1)
  b5_flag = image.select('Swir1').gte(0.1)
  b7_flag = image.select('Swir2').gte(0.1)
  ir_glint = (b4_flag.eq(1)
    .And(b5_flag.eq(1))
    .And(b7_flag.eq(1))
    .selfMask()).rename('ir_glint')
  return image.addBands(ir_glint)


# mask high opacity (>0.3 after scaling) pixels
def add_opac_mask(image):
  """ mask out instances where atmospheric opacity is greater than 0.3 in Landsat 
      5&7
  
  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      an ee.Image with an additional mask band where any pixels with SR_ATMOS_OPACITY 
      greater than 0.3 are set to a value of 0 in the 'opac' band
  """
  opac = image.select("opacity_qa").multiply(0.001).lt(0.3).rename('opac')
  return image.addBands(opac)


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


def add_sr_aero_mask(image):
  """Creates a binary maks for any pixels in Landsat 8 and 9 that have 'medium' 
  or 'high' aerosol QA flags from the SR_QA_AEROSOL band

  Args:
      image: ee.Image of an ee.ImageCollection

  Returns:
      ee.Image with additional band called 'medHighAero', where pixels are given a value of 1
      if the aerosol QA flag is medium or high and 0 otherwise
  """
  aerosolQA = image.select('aerosol_qa')
  # pull out mask out where aeorosol is med and high
  medHighAero = aerosolQA.bitwiseAnd(1 << 7)
  sr_aero_mask = medHighAero.eq(0).rename('aero')
  return image.addBands(sr_aero_mask)


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
   .And(swir1.lt(0.09))
   .And(nir.lt(0.15)) 
   .And(ndvi.lt(0.7)))
  t5 = (mndwi.gt(-0.5) #Partial Surface Water 2 thresholds
   .And(blue.lt(0.1))
   .And(swir1.lt(0.3))
   .And(swir2.lt(0.1))
   .And(nir.lt(0.25)))
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


def remove_geo(image):
  """ Funciton to remove the geometry from an ee.Image
  
  Args:
      image: ee.Image of an ee.ImageCollection
      
  Returns:
      ee.Image with the geometry removed
  """
  return image.setGeometry(None)


## Set up the reflectance pull
def ref_pull_457_DSWE1(image, feat):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1, high confidence
  water

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE is 1
  """
  # process image with cfmask
  # where the mask is > 1 (clouds and cloud shadow)
  # call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low opacity, realistic values, sun glint, ir glint
  opac = add_opac_mask(image).select('opac').eq(1).rename('low_opac')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  # calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  # calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  # apply dswe function
  d = DSWE(image).select('dswe')

  # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
    
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create masks for each band for <0 and <-0.01
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()

  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()

  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1)).selfMask()
  
  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                        'SurfaceTemp'],
                        ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                        'med_SurfaceTemp'])
            .addBands(image.select(['SurfaceTemp'],
                                    ['min_SurfaceTemp']))
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
            # mask the image for dswe
            .updateMask(dswe1) # high confidence water mask
            # add bands back in for QA (prior to masking of dswe/hs/f/r)
            .addBands(gt0) 
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(dswe1a)
            .addBands(opac.eq(0).selfMask().rename('high_opac'))
            .addBands(real.eq(0).selfMask().rename('unreal_val'))
            .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
            .addBands(ir_glint.eq(1).selfMask())
            .addBands(blue_zero)
            .addBands(blue_thresh)
            .addBands(green_zero)
            .addBands(green_thresh)
            .addBands(red_zero)
            .addBands(red_thresh)
            .addBands(nir_zero)
            .addBands(nir_thresh)
            .addBands(swir1_zero)
            .addBands(swir1_thresh)
            .addBands(swir2_zero)
            .addBands(swir2_thresh)
            .addBands(blue_glint)
            .addBands(green_glint)
            .addBands(red_glint)
            .addBands(nir_glint)
            .addBands(swir1_glint)
            .addBands(swir2_glint)
            .addBands(nir_ir_glint)
            .addBands(swir1_ir_glint)
            .addBands(swir2_ir_glint)
            .addBands(clouds) 
            .addBands(hs)
            .addBands(h)
            ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 
              'high_opac', 'unreal_val',
              'sun_glint', 'ir_glint',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


## Set up the reflectance pull
def ref_pull_457_DSWE1a(image, feat):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)
  or where the algal mask threshold is met

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1 or where
      the algal mask threshold is met
  """
  # process image with cfmask
  # where the mask is > 1 (clouds and cloud shadow)
  # call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low opacity, realistic values, sun glint, ir glint
  opac = add_opac_mask(image).select('opac').eq(1).rename('low_opac')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  # calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  # calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  
  # apply dswe function
  d = DSWE(image).select('dswe')
  
  # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
    
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create masks for each band for <0 and <-0.01
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  
  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()

  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()

  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
                        'SurfaceTemp'],
                        ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2',
                        'med_SurfaceTemp'])
            .addBands(image.select(['SurfaceTemp'],
                                    ['min_SurfaceTemp']))
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
            # mask the image
            .updateMask(dswe1a) # dswe1 with algal mask
            # add bands for summaries
            .addBands(gt0) 
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(dswe1a)
            .addBands(opac.eq(0).selfMask().rename('high_opac'))
            .addBands(real.eq(0).selfMask().rename('unreal_val'))
            .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
            .addBands(ir_glint.eq(1).selfMask())
            .addBands(blue_zero)
            .addBands(blue_thresh)
            .addBands(green_zero)
            .addBands(green_thresh)
            .addBands(red_zero)
            .addBands(red_thresh)
            .addBands(nir_zero)
            .addBands(nir_thresh)
            .addBands(swir1_zero)
            .addBands(swir1_thresh)
            .addBands(swir2_zero)
            .addBands(swir2_thresh)
            .addBands(blue_glint)
            .addBands(green_glint)
            .addBands(red_glint)
            .addBands(nir_glint)
            .addBands(swir1_glint)
            .addBands(swir2_glint)
            .addBands(nir_ir_glint)
            .addBands(swir1_ir_glint)
            .addBands(swir2_ir_glint)
            .addBands(clouds) 
            .addBands(hs)
            .addBands(h)
            ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 
              'high_opac', 'unreal_val',
              'sun_glint', 'ir_glint',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out

def ref_pull_457_DSWE3(image, feat):
  """ This function applies all functions to the Landsat 4-7 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 3 (high confidence
  vegetated pixel)

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 3
  """
  # process image with cfmask
  # where the mask is > 1 (clouds and cloud shadow)
  # call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low opacity, realistic values, sun glint, ir glint
  opac = add_opac_mask(image).select('opac').eq(1).rename('low_opac')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  #apply dswe function
  d = DSWE(image).select('dswe')
  
    # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
    
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, opac and real
    .updateMask(clouds.eq(0))
    .updateMask(opac.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  
  # create masks for each band for <0 and <-0.01
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()

  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()

  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(opac.eq(1)).updateMask(d.eq(3)).selfMask()
    
  pixOut = (image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
                      'SurfaceTemp'],
                      ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2',
                      'med_SurfaceTemp'])
          .addBands(image.select(['SurfaceTemp'],
                                  ['min_SurfaceTemp']))
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
          # mask the image
          .updateMask(dswe3) # vegetated water mask
          # add bands for summaries
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(opac.eq(0).selfMask().rename('high_opac'))
          .addBands(real.eq(0).selfMask().rename('unreal_val'))
          .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
          .addBands(ir_glint.eq(1).selfMask())
          .addBands(blue_zero)
          .addBands(blue_thresh)
          .addBands(green_zero)
          .addBands(green_thresh)
          .addBands(red_zero)
          .addBands(red_thresh)
          .addBands(nir_zero)
          .addBands(nir_thresh)
          .addBands(swir1_zero)
          .addBands(swir1_thresh)
          .addBands(swir2_zero)
          .addBands(swir2_thresh)
          .addBands(blue_glint)
          .addBands(green_glint)
          .addBands(red_glint)
          .addBands(nir_glint)
          .addBands(swir1_glint)
          .addBands(swir2_glint)
          .addBands(nir_ir_glint)
          .addBands(swir1_ir_glint)
          .addBands(swir2_ir_glint)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 
              'high_opac', 'unreal_val',
              'sun_glint', 'ir_glint',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE1(image, feat):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where DSWE is 1, high confidence water

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE is 1
  """
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low aerosol, realistic values, sun glint, ir glint
  aero = add_sr_aero_mask(image).select('aero').eq(0).rename('low_aero')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  # calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  # calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  # calculage DSWE
  d = DSWE(image).select('dswe')
  
  # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
    
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create masks for each band for <0 and <-0.01
  aero_zero = image.select('Aerosol').lt(0).rename('aero_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  aero_thresh = image.select('Aerosol').lt(-0.01).rename('aero_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()

  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()

  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1)).selfMask()

  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
                      'SurfaceTemp'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                      'med_SurfaceTemp'])
          .addBands(image.select(['SurfaceTemp'],
                                  ['min_SurfaceTemp']))
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
          # mask the image
          .updateMask(dswe1) # high confidence water mask
          # add bands back in for QA (prior to masking of dswe/hs/f/r)
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(aero.eq(0).selfMask().rename('high_aero'))
          .addBands(real.eq(0).selfMask().rename('unreal_val'))
          .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
          .addBands(ir_glint.eq(1).selfMask())
          .addBands(aero_zero)
          .addBands(aero_thresh)
          .addBands(blue_zero)
          .addBands(blue_thresh)
          .addBands(green_zero)
          .addBands(green_thresh)
          .addBands(red_zero)
          .addBands(red_thresh)
          .addBands(nir_zero)
          .addBands(nir_thresh)
          .addBands(swir1_zero)
          .addBands(swir1_thresh)
          .addBands(swir2_zero)
          .addBands(swir2_thresh)
          .addBands(blue_glint)
          .addBands(green_glint)
          .addBands(red_glint)
          .addBands(nir_glint)
          .addBands(swir1_glint)
          .addBands(swir2_glint)
          .addBands(nir_ir_glint)
          .addBands(swir1_ir_glint)
          .addBands(swir2_ir_glint)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 'high_aero', 'unreal_val',
              'sun_glint', 'ir_glint', 'aero_zero', 'aero_thresh',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
  
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE1a(image, feat):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 1 (high confidence water)
  or the algal threshold has been met

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 1 or the algal
      threshold has been met
  """
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low aerosol, realistic values, sun glint, ir glint
  aero = add_sr_aero_mask(image).select('aero').eq(0).rename('low_aero')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  # calculage DSWE
  d = DSWE(image).select('dswe')
  
  # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
    
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
    
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  
  # create masks for each band for <0 and <-0.01
  aero_zero = image.select('Aerosol').lt(0).rename('aero_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  aero_thresh = image.select('Aerosol').lt(-0.01).rename('aero_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  
  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()

  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(1).Or(alg.eq(1))).selfMask()
  
  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
                      'SurfaceTemp'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2',
                      'med_SurfaceTemp'])
          .addBands(image.select(['SurfaceTemp'],
                                  ['min_SurfaceTemp']))
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
          # mask the image
          .updateMask(dswe1a) # high confidence water + algal mask
          # add bands back in for QA (prior to masking of dswe/hs/f/r)
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(aero.eq(0).selfMask().rename('high_aero'))
          .addBands(real.eq(0).selfMask().rename('unreal_val'))
          .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
          .addBands(ir_glint.eq(1).selfMask())
          .addBands(aero_zero)
          .addBands(aero_thresh)
          .addBands(blue_zero)
          .addBands(blue_thresh)
          .addBands(green_zero)
          .addBands(green_thresh)
          .addBands(red_zero)
          .addBands(red_thresh)
          .addBands(nir_zero)
          .addBands(nir_thresh)
          .addBands(swir1_zero)
          .addBands(swir1_thresh)
          .addBands(swir2_zero)
          .addBands(swir2_thresh)
          .addBands(blue_glint)
          .addBands(green_glint)
          .addBands(red_glint)
          .addBands(nir_glint)
          .addBands(swir1_glint)
          .addBands(swir2_glint)
          .addBands(nir_ir_glint)
          .addBands(swir1_ir_glint)
          .addBands(swir2_ir_glint)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 'high_aero', 'unreal_val',
              'sun_glint', 'ir_glint', 'aero_zero', 'aero_thresh',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
  lsout = (pixOut.reduceRegions(feat, combinedReducer, 30))
  out = lsout.map(remove_geo)
  return out


def ref_pull_89_DSWE3(image, feat):
  """ This function applies all functions to the Landsat 8 and 9 ee.ImageCollection, extracting
  summary statistics for each geometry area where the DSWE value is 3 (high confidence vegetated
  pixels)

  Args:
      image: ee.Image of an ee.ImageCollection
      feat: ee.FeatureGeometry of the buffered locations

  Returns:
      summaries for band data within any given geometry area where the DSWE value is 3
  """
  # where the f mask is > 1 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = add_cf_mask(image).select('cfmask').gte(1).rename('clouds')
  # add mask FOR low aerosol, realistic values, sun glint, ir glint
  aero = add_sr_aero_mask(image).select('aero').eq(0).rename('low_aero')
  real = add_realistic_mask_457(image).select('real').eq(1).rename('is_real')
  no_glint = add_sun_glint_mask(image).select('no_glint').eq(1)
  ir_glint = add_ir_glint_flag(image).select('ir_glint').eq(1)
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  # calculate DSWE
  d = DSWE(image).select('dswe')
  
  # create additive masks for dswe>0 (water of any type)
  # hs = 1, fully illuminated pixels
  gt0 = (d.gt(0).rename('dswe_gt0')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  # create additive masks for dswe==1 (confident open water)
  # hs = 1, fully illuminated pixels
  dswe1 = (d.eq(1).rename('dswe1')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  # create additive masks for dswe==3 (confident vegetated water)
  # hs = 1, fully illuminated pixels
  dswe3 = (d.eq(3).rename('dswe3')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  # define dswe 1a where d is not 0 and red/green threshold met
  grn_alg_thrsh = image.select('Green').gt(0.05)
  red_alg_thrsh = image.select('Red').lt(0.04)
  alg = (d.gt(1).rename('algae')
    .And(grn_alg_thrsh.eq(1))
    .And(red_alg_thrsh.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    )
  # create additive mask for dswe1a: dswe = 1 or algal threshold met
  # hs = 1, fully illuminated pixels
  dswe1a = (d.eq(1)
    .Or(alg.eq(1))
    .rename('dswe1a')
    .updateMask(hs.eq(1))
    # add cloud, aero and real
    .updateMask(clouds.eq(0))
    .updateMask(aero.eq(1))
    .updateMask(real.eq(1))
    .updateMask(no_glint.eq(1))
    .selfMask()
    )
  
  # create masks for each band for <0 and <-0.01
  aero_zero = image.select('Aerosol').lt(0).rename('aero_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  aero_thresh = image.select('Aerosol').lt(-0.01).rename('aero_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  blue_zero = image.select('Blue').lt(0).rename('blue_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  blue_thresh = image.select('Blue').lt(-0.01).rename('blue_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  green_zero = image.select('Green').lt(0).rename('green_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  green_thresh = image.select('Green').lt(-0.01).rename('green_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  red_zero = image.select('Red').lt(0).rename('red_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  red_thresh = image.select('Red').lt(-0.01).rename('red_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_zero = image.select('Nir').lt(0).rename('nir_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_thresh = image.select('Nir').lt(-0.01).rename('nir_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_zero = image.select('Swir1').lt(0).rename('swir1_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_thresh = image.select('Swir1').lt(-0.01).rename('swir1_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_zero = image.select('Swir2').lt(0).rename('swir2_zero').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_thresh = image.select('Swir2').lt(-0.01).rename('swir2_thresh').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  
  # create masks for each band for >= 0.2
  blue_glint = image.select('Blue').gte(0.2).rename('blue_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  green_glint = image.select('Green').gte(0.2).rename('green_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  red_glint = image.select('Red').gte(0.2).rename('red_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  nir_glint = image.select('Nir').gte(0.2).rename('nir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_glint = image.select('Swir1').gte(0.2).rename('swir1_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_glint = image.select('Swir2').gte(0.2).rename('swir2_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  
  # create masks for ir bands >= 0.1
  nir_ir_glint = image.select('Nir').gte(0.1).rename('nir_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir1_ir_glint = image.select('Swir1').gte(0.1).rename('swir1_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()
  swir2_ir_glint = image.select('Swir2').gte(0.1).rename('swir2_ir_glint').updateMask(hs.eq(1)).updateMask(clouds.eq(0)).updateMask(aero.eq(1)).updateMask(d.eq(3)).selfMask()  
  
  #calculate hillshade
  h = calc_hill_shades(image, wrs.geometry()).select('hillShade')
  #calculate hillshadow
  hs = calc_hill_shadows(image, wrs.geometry()).select('hillShadow')
  pixOut = (image.select(['Aerosol', 'Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
                      'SurfaceTemp'],
                      ['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2',
                      'med_SurfaceTemp'])
          .addBands(image.select(['SurfaceTemp'],
                                  ['min_SurfaceTemp']))
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
          # mask image
          .updateMask(dswe3) # dswe3 mask
          # add bands back in for QA (prior to masking of dswe/hs/f/r)
          .addBands(gt0) 
          .addBands(dswe1)
          .addBands(dswe3)
          .addBands(dswe1a)
          .addBands(aero.eq(0).selfMask().rename('high_aero'))
          .addBands(real.eq(0).selfMask().rename('unreal_val'))
          .addBands(no_glint.eq(0).selfMask().rename('sun_glint'))
          .addBands(ir_glint.eq(1).selfMask())
          .addBands(aero_zero)
          .addBands(aero_thresh)
          .addBands(blue_zero)
          .addBands(blue_thresh)
          .addBands(green_zero)
          .addBands(green_thresh)
          .addBands(red_zero)
          .addBands(red_thresh)
          .addBands(nir_zero)
          .addBands(nir_thresh)
          .addBands(swir1_zero)
          .addBands(swir1_thresh)
          .addBands(swir2_zero)
          .addBands(swir2_thresh)
          .addBands(blue_glint)
          .addBands(green_glint)
          .addBands(red_glint)
          .addBands(nir_glint)
          .addBands(swir1_glint)
          .addBands(swir2_glint)
          .addBands(nir_ir_glint)
          .addBands(swir1_ir_glint)
          .addBands(swir2_ir_glint)
          .addBands(clouds) 
          .addBands(hs)
          .addBands(h)
          ) 
  
  combinedReducer = (ee.Reducer.median().unweighted()
      .forEachBand(pixOut.select(['med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 
            'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp']))
    .combine(ee.Reducer.min().unweighted()
      .forEachBand(pixOut.select(['min_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted()
      .forEachBand(pixOut.select(['sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp'])), 
      sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 
              'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.count().unweighted()
      .forEachBand(pixOut.select(['dswe_gt0', 'dswe1', 'dswe3', 'dswe1a', 'high_aero', 'unreal_val',
              'sun_glint', 'ir_glint', 'aero_zero', 'aero_thresh',
              'blue_zero', 'blue_thresh', 'green_zero', 'green_thresh', 'red_zero', 'red_thresh',
              'nir_zero', 'nir_thresh', 'swir1_zero', 'swir1_thresh', 'swir2_zero', 'swir2_thresh',
              'blue_glint', 'green_glint', 'red_glint', 'nir_glint', 'swir1_glint', 'swir2_glint',
              'nir_ir_glint', 'swir1_ir_glint', 'swir2_ir_glint'])), 
      outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['clouds', 'hillShadow'])), 
      outputPrefix = 'prop_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted()
      .forEachBand(pixOut.select(['hillShade'])), 
      outputPrefix = 'mean_', sharedInputs = False)
    )
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
    # if reach or over maximum no. of active tasks, wait for a certain amount 
    # of time ('waitingPeriod') and check again
    time.sleep(waitingPeriod) 
    ts = list(ee.batch.Task.list())
    NActive = 0
    for task in ts:
      if ('RUNNING' in str(task) or 'READY' in str(task)):
        NActive += 1
  return()



##########################################
##---- LANDSAT 457 ACQUISITION      ----##
##########################################


## run the pull for LS457, looping through all extents from yml
for e in extent:
  
  maximum_no_of_tasks(10, 120)

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
    .map(apply_scale_factors))
  
  # rename bands for ease
  locs_stack_ls457 = locs_stack_ls457.select(bn457, bns457)
  
  # apply masks that require above rename
  locs_stack_ls457 = (locs_stack_ls457
    .map(apply_rad_mask))
  
  # pull DSWE1 variations as configured
  if '1' in dswe:
    # pull DSWE1 and DSWE1 with algal mask if configured
    if '1a' in dswe:
      locs_out_457_D1 = locs_stack_ls457.map(lambda image: ref_pull_457_DSWE1(image, feat)).flatten()
      locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1 = proj + '_site_LS457_C2_SRST_DSWE1_' + str(tiles) + '_v' + run_date
      locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                              description = locs_srname_457_D1,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_opac', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 
                                              'pCount_swir1_glint', 'pCount_swir2_glint', 
                                              'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_457_D1.start()
      print('Task sent: Landsat 4, 5, 7 DSWE 1 acquisitions for site configuration at tile ' + str(tiles))
      locs_out_457_D1a = locs_stack_ls457.map(lambda image: ref_pull_457_DSWE1a(image, feat)).flatten()
      locs_out_457_D1a = locs_out_457_D1a.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1a = proj + '_site_LS457_C2_SRST_DSWE1a_' + str(tiles) + '_v' + run_date
      locs_dataOut_457_D1a = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1a,
                                              description = locs_srname_457_D1a,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_opac', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 
                                              'pCount_swir1_glint', 'pCount_swir2_glint', 
                                              'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_457_D1a.start()
      print('Task sent: Landsat 4, 5, 7 DSWE 1a acquisitions for site configuration at tile ' + str(tiles))
    
    else: 
      # only pull DSWE1
      locs_out_457_D1 = locs_stack_ls457.map(lambda image: ref_pull_457_DSWE1(image, feat)).flatten()
      locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_457_D1 = proj + '_site_LS457_C2_SRST_DSWE1_' + str(tiles) + '_v' + run_date
      locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                              description = locs_srname_457_D1,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_opac', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 
                                              'pCount_swir1_glint', 'pCount_swir2_glint', 
                                              'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_457_D1.start()
      print('Task sent: Landsat 4, 5, 7 DSWE 1 acquisitions for site configuration at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 1 or DSWE 1a stack for Landsat 4, 5, 7 for site configuration')
  
  # pull DSWE3 variants if configured
  if '3' in dswe:
    # pull DSWE3
    locs_out_457_D3 = locs_stack_ls457.map(lambda image: ref_pull_457_DSWE3(image, feat)).flatten()
    locs_out_457_D3 = locs_out_457_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D3 = proj + '_site_LS457_C2_SRST_DSWE3_' + str(tiles) + '_v' + run_date
    locs_dataOut_457_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D3,
                                            description = locs_srname_457_D3,
                                            folder = folder_version,
                                            fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_opac', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 
                                              'pCount_swir1_glint', 'pCount_swir2_glint', 
                                              'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Send next task.                                        
    locs_dataOut_457_D3.start()
    print('Task sent: Landsat 4, 5, 7 DSWE 3 acquisitions for site configuration at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 3 stack for Landsat 4, 5, 7 for site configuration')



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
      .map(apply_scale_factors))
      
  # rename bands for ease
  locs_stack_ls89 = locs_stack_ls89.select(bn89, bns89)
  
  # apply masks that require above rename
  locs_stack_ls89 = (locs_stack_ls89
    .map(apply_rad_mask))
  
  if '1' in dswe:
    if '1a' in dswe:
      locs_out_89_D1 = locs_stack_ls89.map(lambda image: ref_pull_89_DSWE1(image, feat)).flatten()
      locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1 = proj + '_site_LS89_C2_SRST_DSWE1_' + str(tiles) + '_v' + run_date
      locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                              description = locs_srname_89_D1,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_aero', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_aero_zero', 'pCount_aero_thresh',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 'pCount_swir1_glint',
                                              'pCount_swir2_glint', 'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_89_D1.start()
      print('Task sent: Landsat 8, 9 DSWE 1  acquisitions for site configuration at tile ' + str(tiles))
      
      locs_out_89_D1a = locs_stack_ls89.map(lambda image: ref_pull_89_DSWE1a(image, feat)).flatten()
      locs_out_89_D1a = locs_out_89_D1a.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1a = proj+'_site_LS89_C2_SRST_DSWE1a_' + str(tiles) + '_v' + run_date
      locs_dataOut_89_D1a = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1a,
                                              description = locs_srname_89_D1a,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_aero', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_aero_zero', 'pCount_aero_thresh',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 'pCount_swir1_glint',
                                              'pCount_swir2_glint', 'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_89_D1a.start()
      print('Task sent: Landsat 8, 9 DSWE 1a acquisitions for site configuration at tile ' + str(tiles))
      
    else:
      locs_out_89_D1 = locs_stack_ls89.map(lambda image: ref_pull_89_DSWE1(image, feat)).flatten()
      locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
      locs_srname_89_D1 = proj + '_site_LS89_C2_SRST_DSWE1_' + str(tiles) + '_v' + run_date
      locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                              description = locs_srname_89_D1,
                                              folder = folder_version,
                                              fileFormat = 'csv',
                                              selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_aero', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_aero_zero', 'pCount_aero_thresh',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 'pCount_swir1_glint',
                                              'pCount_swir2_glint', 'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
      #Send next task.                                        
      locs_dataOut_89_D1.start()
      print('Task sent: Landsat 8, 9 DSWE 1 acquisitions for site configuration at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 8, 9 for site configuration')
  
  if '3' in dswe:
    locs_out_89_D3 = locs_stack_ls89.map(lambda image: ref_pull_89_DSWE3(image, feat)).flatten()
    locs_out_89_D3 = locs_out_89_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D3 = proj + '_site_LS89_C2_SRST_DSWE3_' + str(tiles) + '_v' + run_date
    locs_dataOut_89_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D3,
                                            description = locs_srname_89_D3,
                                            folder = folder_version,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                              'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                              'med_SurfaceTemp', 'min_SurfaceTemp',
                                              'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                              'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                              'mean_SurfaceTemp',
                                              'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 'pCount_dswe1a',
                                              'pCount_high_aero', 'pCount_unreal_val', 'pCount_sun_glint', 'pCount_ir_glint',
                                              'pCount_aero_zero', 'pCount_aero_thresh',
                                              'pCount_blue_zero', 'pCount_blue_thresh', 'pCount_green_zero', 'pCount_green_thresh', 
                                              'pCount_red_zero', 'pCount_red_thresh', 'pCount_nir_zero', 'pCount_nir_thresh', 
                                              'pCount_swir1_zero', 'pCount_swir1_thresh', 'pCount_swir2_zero', 'pCount_swir2_thresh', 
                                              'pCount_blue_glint', 'pCount_green_glint', 'pCount_red_glint', 'pCount_nir_glint', 'pCount_swir1_glint',
                                              'pCount_swir2_glint', 'pCount_nir_ir_glint', 'pCount_swir1_ir_glint', 'pCount_swir2_ir_glint',
                                              'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Send next task.                                        
    locs_dataOut_89_D3.start()
    print('Task sent: Landsat 8, 9 DSWE 3 acquisitions for site configuration at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 3 stack for Landsat 8,9 for sites')



##############################################
##---- LANDSAT 457 METADATA ACQUISITION ----##
##############################################


## get metadata ##
meta_srname_457 = proj + '_metadata_LS457_C2_' + str(tiles) + '_v' + run_date
meta_dataOut_457 = (ee.batch.Export.table.toDrive(collection = ls457,
                                        description = meta_srname_457,
                                        folder = folder_version,
                                        fileFormat = 'csv'))

#Send next task.                                        
meta_dataOut_457.start()



#############################################
##---- LANDSAT 89 METADATA ACQUISITION ----##
#############################################

## get metadata ##
meta_srname_89 = proj + '_metadata_LS89_C2_' + str(tiles) + '_v' + run_date
meta_dataOut_89 = (ee.batch.Export.table.toDrive(collection = ls89,
                                        description = meta_srname_89,
                                        folder = folder_version,
                                        fileFormat = 'csv'))


#Send next task.                                        
meta_dataOut_89.start()

print("Task sent: metadata acquisition for tile " + str(tiles))
