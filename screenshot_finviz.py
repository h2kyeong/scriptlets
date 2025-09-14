#! /usr/bin/env python3

def symbols ():
	import csv
	# https://www.nasdaq.com/market-activity/stocks/screener
	with open("/path/to/nasdaq_screener.csv", encoding="utf-8", newline="") as f:
		for a in csv.reader(f):
			yield a[0]


import time
import os, glob
import subprocess

def create_driver ():
	from selenium import webdriver
	
	options = webdriver.ChromeOptions()
	options.binary_location="/path/to/chrome"
	options.page_load_strategy = 'none'
	
	from selenium.webdriver.chrome.service import Service
	driver = webdriver.Chrome(options=options, service=Service("/path/to/chromedriver"))
	return driver

def create_undetected_driver ():
	import undetected_chromedriver as webdriver
	options = webdriver.ChromeOptions()
	options.page_load_strategy = 'none'
	#options.add_argument(r'--no-sandbox')
	#options.add_argument(r'--user-data-dir=/home/redacted/.config/chromium')
	#options.add_argument(r'--profile-directory=Default')
	
	driver = webdriver.Chrome(options=options,
		browser_executable_path="/path/to/chrome",
		driver_executable_path="/path/to/chromedriver"
	)
	return driver

def main_sleep (*argv):
	global driver
	driver = create_driver()
	time.sleep(10000)

def main_do (*argv):
	global driver
	from selenium.webdriver.common.by import By
	from selenium.common.exceptions import NoSuchElementException
	driver = create_driver()
	
	for i,quote in enumerate(symbols()):
		driver.get(f"https://finviz.com/quote.ashx?t={quote}&p=w")
		while True:
			driver.set_window_size(1600, 1100)
			try:
				driver.find_element(By.TAG_NAME, 'canvas')
				driver.execute_script("window.stop();")
			except NoSuchElementException:
				time.sleep(1)
				continue
			break
		driver.save_screenshot(f"finviz/{i:04d}_{quote}.png")
		time.sleep(6)


if __name__ == '__main__':
	import sys
	globals()['main_'+sys.argv[1]](*sys.argv[2:])
