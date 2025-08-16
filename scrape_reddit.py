#! /usr/bin/env python3

'''
Selenium-based Reddit Scraper
by h2kyeong, 2025. 8. 16.
released with MIT license terms
'''

def generic_insert (storage, item):
	for key in ('add','append','insert'):
		if hasattr(storage, key):
			return getattr(storage, key)(item)
	raise TypeError(storage)


import re

rx_remove_whitespace = re.compile(r'^\s*(.+?)\s*$')
rx_post_url = re.compile(r'/r/([^/]+)/comments/([^/]+)/')

def remove_whitespace (s):
	return rx_remove_whitespace.match(s).group(1)


from lxml import etree

def read_html_file (filename):
	with open(filename, encoding='utf-8') as f:
		parser = etree.HTMLParser(recover=True)
		parser.feed(f.read())
		root = parser.close()
	return root

def parse_article (el):
	ret = dict()
	for e in el.iter():
		if e.tag == 'shreddit-post':
			for k in ('permalink','post-title','score','comment-count','created-timestamp',):
				ret[k] = e.attrib.get(k)
		if e.tag == 'div' and 'class' in e.attrib and 'mb-xs' in e.attrib['class']:
			ret['body'] = ' '.join(( f.text or '' for f in e.iter() ))
			ret['body'] = re.sub(r'\s+',' ',ret['body'])
	return ret

def extract_post_links (storage, html):
	parser = etree.HTMLParser(recover=True)
	parser.feed(html)
	root = parser.close()
	
	for e in root.iter():
		if e.tag != 'article': continue
		generic_insert(storage, parse_article(e))


import time

def create_driver ():
	from selenium import webdriver
	from selenium.webdriver.chrome.service import Service
	from webdriver_manager.chrome import ChromeDriverManager

	options = webdriver.ChromeOptions()

	if HEADLESS:
		options.add_argument('--headless')
		options.add_argument('--no-sandbox')

	service = Service()
	return webdriver.Chrome(service=service, options=options)

def scroll_down (context, callback, iteration=5):
	from selenium.webdriver.common.by import By
	from selenium.webdriver.common.keys import Keys
	
	for _ in range(iteration):
		driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
		time.sleep(4)
		contents = driver.find_element(By.TAG_NAME, 'body').get_attribute('outerHTML')
		callback(context, contents)



HEADLESS = False
CHANNELS = ('stocks','investing','Economics','StockMarket','ValueInvesting',)

def main_top (*argv):
	import json
	global driver
	driver = create_driver()
	for sub in CHANNELS:
		driver.get(f'https://www.reddit.com/r/{sub}/new/')
		storage = list()
		dead = set()
		scroll_down(storage, callback=extract_post_links, iteration=20)
		with open(f'top_{sub}', 'w', encoding='utf-8') as f:
			for item in storage:
				key = item['permalink']
				if key in dead: continue
				print(json.dumps(item), file=f)
				dead.add(key)

def main_posts (*argv):
	import json, os
	global driver
	driver = create_driver()
	for sub in CHANNELS:
		with open(f'top_{sub}', encoding='utf-8') as f:
			posts = [json.loads(line) for line in f]
		for a in posts:
			m = rx_post_url.search(a['permalink'])
			driver.get('https://www.reddit.com' + a['permalink'])
			sub, id = m.groups()
			if not os.path.exists(sub):
				os.mkdir(sub)
			storage = []
			scroll_down(storage, callback=generic_insert, iteration=5)
			print([len(x) for x in storage])
			with open(f'{sub}/{id}.html', 'w', encoding='utf-8', errors='ignore') as f:
				f.write(storage[-1])


if __name__ == '__main__':
	import sys
	globals()['main_'+sys.argv[1]](*sys.argv[2:])
