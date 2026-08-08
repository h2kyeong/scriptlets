def calculate_ratings (matches, num_candidates, l2_reg=1e-4):
	'''
	Bradley-Terry model for Maximum Likelihood Estimation (MLE)
	matches is a list of (ID 1, ID 2, 1 if #1 won)
	'''
	import numpy as np
	from scipy.optimize import minimize
	idx1 = np.array([m[0] for m in matches])
	idx2 = np.array([m[1] for m in matches])
	scores = np.array([m[2] for m in matches], dtype=float)
	
	def negative_log_likelihood (ratings):
		diff = ratings[idx1] - ratings[idx2]
		log_p1 = np.log1p(np.exp(-diff))
		log_p0 = np.log1p(np.exp( diff))
		nll = np.sum(scores * log_p1 + (1 - scores) * log_p0)
		
		# Add small L2 regularization to handle scale/translation invariance
		reg_penalty = l2_reg * np.sum(ratings**2)
		return nll + reg_penalty

	def gradient (ratings):
		diff = ratings[idx1] - ratings[idx2]
		prob = 1.0 / (1.0 + np.exp(-diff))
		errors = scores - prob
		
		grad = np.zeros_like(ratings)
		np.add.at(grad, idx1, -errors)
		np.add.at(grad, idx2, errors)
		
		return grad + 2 * l2_reg * ratings

	initial_ratings = np.zeros(num_candidates)
	res = minimize(
		fun=negative_log_likelihood,
		x0=initial_ratings,
		jac=gradient,
		method='L-BFGS-B'
	)
	return res.x - np.max(res.x)


import json

prompt_base = {"max_context_length": 32768, "max_length": 4096, "rep_pen": 1, "temperature": 1, "top_p": 0.95, "top_k": 64, "top_a": 0, "typical": 1, "tfs": 1, "rep_pen_range": 360, "rep_pen_slope": 0.7, "sampler_order": [6, 0, 1, 3, 4, 2, 5], "memory": "", "trim_stop": True, "genkey": "KCPP4606", "min_p": 0, "dynatemp_range": 0, "dynatemp_exponent": 1, "smoothing_factor": 0, "smoothing_curve": 1, "nsigma": 0, "banned_tokens": [], "render_special": False, "logprobs": False, "replace_instruct_placeholders": True, "presence_penalty": 0, "logit_bias": {}, "adaptive_target": -1, "adaptive_decay": 0.9, "stop_sequence": ["{{[INPUT]}}", "{{[OUTPUT]}}"], "use_default_badwordsids": False, "bypass_eos": False, "prompt": "{{[INPUT]}}guten tag!{{[OUTPUT]}}"}

def generate (prompt):
	from urllib.request import Request, urlopen
	data = dict(prompt_base)
	data['prompt']=prompt
	r = Request(
		'http://localhost:5001/api/generate',
		headers={"Content-Type": "application/json"},
		data=json.dumps(data).encode('utf-8')
	)
	ar = []
	ctx = None
	done = False
	for x in map( json.loads, urlopen(r).read().decode('utf-8').splitlines() ):
		if 'response' in x: ar.append(x['response'])
		if 'context' in x: ctx = x['context']
		if 'done' in x: done = done | x['done']
	return (''.join(ar), done, ctx)

def compare (ans1, ans2):
	ar = [
		"{{[INPUT]}}<attachement name='original'>", document,
		"</attachment>Above is a transcript. Divide time ranges by topic and name subheadings. Insert brief summary under each subheading.{{[OUTPUT]}}",
		"{{[INPUT]}}",
		"<attachment name='Summary A'>", ans1, "</attachment>",
		"<attachment name='Summary B'>", ans2, "</attachment>",
		"Above is a transcript and two summaries A and B. Name the better summary. The most important quality of an excellent summary is presenting the core message that is unique to the video. No explanation is required.",
		"{{[OUTPUT]}}"
	]
	ans, done, ctx = generate(''.join(ar))
	i1 = ans.find('Summary A')
	i2 = ans.find('Summary B')
	# assume winner is mentioned first. 1 if A wins
	if i1 < 0: return 0
	if i2 < 0: return 1
	return 1 if i1 < i2 else 0


def transcript_summary ():
	ar = [
		"{{[INPUT]}}<attachement name='original'>", document,
		"</attachment>Above is a transcript. Divide time ranges by topic and name subheadings. Insert brief summary under each subheading.{{[OUTPUT]}}"
	]
	cand = []
	for i in range(num_gen):
		print('generating', i)
		ans, done, ctx = generate(''.join(ar))
		cand.append(ans)
	
	scores = []
	for i in range(num_gen-1):
		print('comparing', i)
		for j in range(i+1, num_gen):
			for k in range(2):
				scores.append(( i, j, compare(cand[i], cand[j]) ))
	for i in range(num_gen-1, 1, -1):
		print('comparing back', i)
		for j in range(i-1, 0, -1):
			for k in range(2):
				scores.append(( i, j, compare(cand[i], cand[j]) ))
	
	ratings = [ (r, i) for i, r in enumerate(calculate_ratings(scores, num_gen)) ]
	ratings.sort(reverse=True)
	
	with open('o.txt', 'w', encoding='utf-8', newline='\n') as f:
		for r, i in ratings:
			print((round(float(r), 4), i), file=f)
			print(cand[i], file=f)
			f.write('\n'*2)

import sys

num_gen = 10

with open(sys.argv[1], 'r', encoding='utf-8', newline='\n') as f:
	document = f.read()

transcript_summary()
