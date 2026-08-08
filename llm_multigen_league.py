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
		log_p1 = -np.log1p(np.exp(-diff))
		log_p0 = -np.log1p(np.exp( diff))
		nll = -np.sum(scores * log_p1 + (1 - scores) * log_p0)
		
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

document = '''\
Intro
0:00
Inflation inflation.
0:02
Every single metric is saying that
...
23:45
video next and get this video to 10,000
23:47
likes. Thanks.
'''

def make_candidates ():
	ar = [
		"{{[INPUT]}}<attachement name='original'>", document,
		"</attachment>Above is a transcript. Divide time ranges by topic and name subheadings. Insert brief summary under each subheading.{{[OUTPUT]}}"
	]
	with open('candidates.txt', 'w', encoding='utf-8', newline='\n') as f:
		for i in range(10):
			ans, done, ctx = generate(''.join(ar))
			f.write(repr(( ans, done, [] )))
			f.write('\n')

def make_matches ():
	def match (ans1, ans2):
		ar = [
			"{{[INPUT]}}<attachement name='original'>", document,
			"</attachment>Above is a transcript. Divide time ranges by topic and name subheadings. Insert brief summary under each subheading.{{[OUTPUT]}}",
			"{{[INPUT]}}",
			"Above is a transcript and two summaries A and B. Name the better summary and explain why. The most important quality of an excellent summary is presenting the core message that is unique to the video.",
			"<attachment name='Summary A'>", ans1, "</attachment>",
			"<attachment name='Summary B'>", ans2, "</attachment>",
			"{{[OUTPUT]}}"
		]
		ans, done, ctx = generate(''.join(ar))
		i1 = ans.find('Summary A')
		i2 = ans.find('Summary B')
		# assume winner is mentioned first. 1 if A wins
		if i1 < 0:
			if i2 < 0: return
			else: return 0
		else:
			if i2 < 0: return 1
			else: return 1 if i1 < i2 else 0
		
	with open('candidates.txt', 'r', encoding='utf-8', newline='\n') as f:
		cand = [ ans for ans, done, ctx in map(eval, f) ]
	with open('matches.txt', 'w', encoding='utf-8', newline='\n') as f:
		for i in range(10-1):
			for j in range(i+1, 10):
				f.write(repr(( i, j, match(cand[i], cand[j]) )))
				f.write('\n')

def test ():
	make_candidates()
	make_matches()
	from bradley_terry import calculate_ratings
	with open('matches.txt', 'r', encoding='utf-8', newline='\n') as f:
		scores = list(map(eval, f))
	ratings = [ (r, i) for i, r in enumerate(calculate_ratings(scores, 10)) ]
	ratings.sort(reverse=True)
	with open('candidates.txt', 'r', encoding='utf-8', newline='\n') as f:
		cand = [ ans for ans, done, ctx in map(eval, f) ]
	with open('o.txt', 'w', encoding='utf-8', newline='\n') as f:
		for r, i in ratings:
			print((round(float(r), 4), i), file=f)
			print(cand[i], file=f)

test()
