import json
import csv
import os
import sys

import re

# Remove various ways the files describe a metro area
namere = re.compile(' (Metro Area|Micro Area|PMSA|MSA|NECMA)$')

# Drop anything after hyphens to match major cities only
namere2 = re.compile('[/-][^,]*,')
namere3 = re.compile('-.*$')


def format_city_name(city_name):
	new_city_name = city_name
	new_city_name = namere.sub('',new_city_name)
	new_city_name = namere2.sub(',',new_city_name)
	new_city_name = namere3.sub('',new_city_name)
	new_city_name = new_city_name.replace('TX, AR','TX')
	new_city_name = new_city_name.replace('Urban Honolulu','Honolulu')
	return new_city_name

digitre = re.compile('\d+$')

	
def get_cities():
	cities = {}
	
	# Read in city codes and names from County Business Pattern data
	firstline = True
	with open('metadata/msa_county_reference12.txt','rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',', quotechar='"')
		for row in reader:
			if firstline:
				firstline = False
				continue
			
			city = {}
			city['code'] = row[0]
			city_name = format_city_name(row[1])
			city['name'] = city_name
			cities[city_name] = city
			
	# Add in recent population numbers
	f = open('metadata/metro-populations.txt','r')
	for line in f.readlines():
		lineparts = line.strip().split('\t')
		city_name = format_city_name(lineparts[0])
		if city_name in cities:
			cities[city_name]['population'] = int(lineparts[1])

	return cities

	
def get_industries():
	# Read in NAICS industry codes		
	industries = {}
	firstline = True
	with open('metadata/NAICS2012.txt','rb') as csvfile:
		reader = csv.reader(csvfile, delimiter=',', quotechar='"')
		for row in reader:
			if firstline:
				firstline = False
				continue
			
			industry = {}
			naics_code = row[0]
			naics_name = row[1]
				
			if naics_code.endswith('----') and naics_code.startswith('--') == False:
				industry['code'] = naics_code
				industry['name'] = naics_name
				industries[naics_name] = industry

	return industries
	
		
def populate_business_data(data, city_names, city_code_to_name, industry_names, industry_code_to_name):
	years = ['98','99','00','01','02','03','04','05','06','07','08','09','10','11','12','13']
	yearvals = [1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013]

	# Construct our shell data set, which we will then fill in with discovered values.
	# Allows us to zero out all instances where data is not present.

	obs_idx = {}
	id = 0
	for naics_name in industry_names:
		observation = {}
		observation['id'] = id
		observation['name'] = naics_name + ' (Establishments)'
		observation['timestamps'] = yearvals
		data['observations'].append(observation)
		obs_idx[observation['name']] = id

		id += 1
		
		observation = {}
		observation['id'] = id
		observation['name'] = naics_name + ' (Payroll)'
		observation['timestamps'] = yearvals
		data['observations'].append(observation)
		obs_idx[observation['name']] = id
		
		id += 1

	city_idx = {}
	id = 0

	for city in city_names:
		instance = {}
		instance['name'] = city
		observations = []
		
		for i in range(len(data['observations'])):
			observation = {}
			observation['id'] = i
			vals = []
			for j in range(len(yearvals)):
				vals.append(0)
			observation['values'] = vals
			observations.append(observation)
		
		instance['observations'] = observations
		
		data['instances'].append(instance)
		
		city_idx[city] = id
		id += 1

	for year in years:
		yearval = '20' + year
		if year.startswith('9'):
			yearval = '19' + year
		
		yearval = int(yearval)
		yearidx = years.index(year)
		
		# Read in file
		# Ignore all lines except those with two digit NAICS (e.g. 11----)
		firstline = True
		headers = None
		with open('cbp_data/cbp' + year + 'msa.txt', 'rb') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			for row in reader:
				if firstline:
					firstline = False
					headers = []
					for val in row:
						headers.append(val.lower())
					continue
				
				city_code = row[0]
				naics_code = row[1]
				
				if city_code in city_code_to_name and naics_code in industry_code_to_name:	
					city_name = city_code_to_name[city_code]
					naics_name = industry_code_to_name[naics_code]
					
					naics_payroll = naics_name + ' (Payroll)'
					naics_establishments = naics_name + ' (Establishments)'
					
					payroll = int(row[headers.index('ap')])
					establishments = int(row[headers.index('est')])
					
					data['instances'][city_idx[city_name]]['observations'][obs_idx[naics_payroll]]['values'][yearidx] = payroll
					data['instances'][city_idx[city_name]]['observations'][obs_idx[naics_establishments]]['values'][yearidx] = establishments

def populate_databook_data(data, city_idx):
	unparsed_names = set()
	for file in os.listdir('databooks'):
		if file.endswith('.txt'):
			firstLine = True
			metric_name = file.replace('.txt','')
			
			f = open('databooks/' + file,'r')
			for line in f.readlines():
				lineparts = line.strip().split('\t')
				if firstLine:
					lineparts.pop(0)
					timestamps = []
					if len(lineparts) > 1:
						lineparts.reverse()
						for sval in lineparts:
							timestamps.append(int(sval))
					else:
						timestamps.append(2010)
					
					observation = {}
					observation['id'] = len(data['observations'])
					observation['name'] = metric_name
					observation['timestamps'] = timestamps
					data['observations'].append(observation)
					firstLine = False
				else:	
					city_name = format_city_name(lineparts.pop(0))
					if city_name in city_idx:
						lineparts.reverse()
						observation = {}
						observation['id'] = len(data['observations'])-1
						observation['values'] = []
						for sval in lineparts:
							try:
								observation['values'].append(float(sval.replace(',','')))
							except ValueError:
								print 'Problem parsing ' + sval
								observation['values'].append(observation['values'][len(observation['values'])-1])
						data['instances'][city_idx[city_name]]['observations'].append(observation)
					else:
						unparsed_names.add(city_name)
	name_arr = list(unparsed_names)
	name_arr.sort()
	print 'Unable to find the following cities (likely suburbs of a larger metro area):'
	for name in name_arr:
		print name
					
def populate_crime_data(data, city_idx):
	years = ['97','98','99','01','02','03','04','05','06','07','08','09','10']
	yearvals = [1997,1998,1999,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010]

	# Determine what cities are covered in the crime dataset
	city_code_idx = {}
	f = open('fbi_data/msanecmaid.xls.txt','r')
	for line in f.readlines():
		lineparts = line.strip().split('\t')
		city_name = format_city_name(lineparts[1])
		if city_name in city_idx:
			city_code_idx[lineparts[0]] = city_name
		else:
			print 'City not in list: ' + city_name
		
	f.close()
	
	# Add observations for murder, robbery, assault, and burglary
	for crime in ['Crime - Murder','Crime - Robbery', 'Crime - Assault', 'Crime - Burglary']:
		observation = {}
		observation['id'] = len(data['observations'])
		observation['name'] = crime
		observation['timestamps'] = yearvals
		data['observations'].append(observation)
		print 'Added ' + crime + ' as Observation ID ' + str(len(data['observations'])-1)

		for city in city_code_idx.values():
			observation = {}
			observation['id'] = len(data['observations'])-1
			vals = []
			for j in range(len(yearvals)):
				vals.append(0)
			observation['values'] = vals
			data['instances'][city_idx[city]]['observations'].append(observation)
		
	for year in years:
		yearval = '20' + year
		if year.startswith('9'):
			yearval = '19' + year
		
		yearval = int(yearval)
		yearidx = years.index(year)
		
		# Read in file
		firstline = True
		headers = None
		f = open('fbi_data/tbl_msa_rates_' + year + '.xls.txt','r')
		for line in f.readlines():
			lineparts = line.strip().split('\t')
			if firstline:
				firstline = False
				headers = []
				for val in lineparts:
					headers.append(digitre.sub('',val.lower()))
				continue
			
			city_code = lineparts[0]
			
			if city_code in city_code_idx:	
				city_name = city_code_idx[city_code]
				if headers.index('mrmurd')>= len(lineparts):
					continue
					
				murder = float(lineparts[headers.index('mrmurd')])
				robbery = float(lineparts[headers.index('mrrobt')])
				assault = float(lineparts[headers.index('mrassa')])
				burglary = float(lineparts[headers.index('mrburg')])
				
				data['instances'][city_idx[city_name]]['observations'][len(data['instances'][city_idx[city_name]]['observations'])-4]['values'][yearidx] = murder
				data['instances'][city_idx[city_name]]['observations'][len(data['instances'][city_idx[city_name]]['observations'])-3]['values'][yearidx] = robbery
				data['instances'][city_idx[city_name]]['observations'][len(data['instances'][city_idx[city_name]]['observations'])-2]['values'][yearidx] = assault
				data['instances'][city_idx[city_name]]['observations'][len(data['instances'][city_idx[city_name]]['observations'])-1]['values'][yearidx] = burglary
	
# Get cities
cities = get_cities()
city_names = cities.keys()
city_names.sort()
city_code_to_name = {}
for city in cities:
	if 'code' in cities[city]:
		city_code_to_name[cities[city]['code']] = cities[city]['name']
city_idx = {}
for i in range(len(city_names)):
	city_idx[city_names[i]] = i
	
		
# Get industries
industries = get_industries()
industry_names = industries.keys()
industry_names.sort()
industry_code_to_name = {}
for industry in industries:
	industry_code_to_name[industries[industry]['code']] = industries[industry]['name']
	
data = {}
data['instances'] = []
data['observations'] = []

# Populate business data
populate_business_data(data, city_names, city_code_to_name, industry_names, industry_code_to_name)

# Populate databook data
populate_databook_data(data, city_idx)

# Populate crime data
populate_crime_data(data, city_idx)


print 'Instances: ' + str(len(data['instances']))
print 'Observations: ' + str(len(data['observations']))
f = open('us_cities_data.json','w')
f.write(json.dumps(data))
f.close()
				