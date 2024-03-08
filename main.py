from github import Github, InputGitTreeElement, Auth
from datetime import datetime, timezone
import argparse
import config
import mirror
import sys, os
import subprocess

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--manual", type=int, help="Manually mirror PRs from the specified repository without conditions."),
args = parser.parse_args()

try:
	if config.api_key:
		auth = Auth.Token(config.api_key)
		github_api = Github(auth=auth)
	else:
		print("No API key specified in config.")
		sys.exit()
except Exception as e:
	print(f"Error while logging into Github, double-check credentials or try again later. Error text: {e}")
	sys.exit()
try:
	print(f"Extracting the upstream repository.")
	upstream = github_api.get_repo(f"{config.upstream_owner}/{config.upstream_repo}")
except:
	print("Error while obtaining upstream repository info, check if owner and repo names were entered correctly.")
	sys.exit()
try:
	print(f"Extracting a downstream repository.")
	downstream = github_api.get_repo(f"{config.downstream_owner}/{config.downstream_repo}")
except:
	print("Error while obtaining downstream repository info, check if owner and repo names were entered correctly.")
	sys.exit()

if not os.path.isdir(config.local_repo_directory):
	print("Local clone of downstream repository not found, cloning.")
	try:
		subprocess.check_output(
			["git", "clone", f"https://github.com/{config.downstream_owner}/{config.downstream_repo}", f"{config.local_repo_directory}"])
		current_directory = os.getcwd()
		os.chdir(config.local_repo_directory)
		subprocess.check_output(["git", "remote", "add", "upstream", f"https://github.com/{config.upstream_owner}/{config.upstream_repo}"])
		subprocess.check_output(["git", "remote", "add", "downstream", f"https://github.com/{config.downstream_owner}/{config.downstream_repo}"])
		os.chdir(current_directory)
	except:
		print("An error occured during cloning.")
		sys.exit()

print("Extracting closed pull requests from the source repository.")
upstream_pulls_requests = upstream.get_pulls(state='closed', sort='created', direction='asc')
downstream_pulls_requests = downstream.get_pulls(sort='all', direction='asc')

if args.manual is not None:
	print(f"Manual extraction PR {args.manual}")
	#result = mirror.mirror_pr(upstream, downstream, args.manual)
	upstream_pull_request = upstream.get_pull(args.manual)
	downstream_pr_exist = False
	if downstream_pulls_requests.totalCount == 0:
		result = mirror.mirror_pr(upstream, downstream, args.manual)
		sys.exit()
	else:
		for downstream_pr in downstream_pulls_requests:
			if f"{config.mirror_pr_title_prefix}{upstream_pull_request.title} - {upstream_pull_request.number}" == downstream_pr.title:
				print(RED + f"Pull request #{args.manual} already exists in the target repository" + RESET)
				downstream_pr_exist = True
				sys.exit()
		if downstream_pr_exist != True:
			print(YELLOW + f"Create Pull-request #{args.manual} in the target repository" + RESET)
			result = mirror.mirror_pr(upstream, downstream, args.manual)
			sys.exit()

else:
	if config.end_date:
		print("Set the limit date of retrievable repositories.")
		end_date = config.end_date
		end_date_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
	else:
		print("There is no end date in the configuration.")
		sys.exit()

	if downstream_pulls_requests.totalCount == 0:
		for pull_request in upstream_pulls_requests:
			if pull_request.merged and pull_request.merged_at >= end_date_datetime:
				print(f"Create Pull-request #{pull_request.number} in the target repository")
				mirror.mirror_pr(upstream, downstream, pull_request.number)
		sys.exit()
	
	for pull_request in upstream_pulls_requests:
		if pull_request.merged and pull_request.merged_at >= end_date_datetime:
			print(f"Processing a combined pull request #{pull_request.number}")
			downstream_pr_exist = False	
			for downstream_pr in downstream_pulls_requests:
				if f"{config.mirror_pr_title_prefix}{pull_request.title} - {pull_request.number}" == downstream_pr.title:
					print(RED + f"Pull request #{pull_request.number} already exists in the target repository" + RESET)
					downstream_pr_exist = True
					break
			if downstream_pr_exist != True:
				print(YELLOW + f"Create Pull-request #{pull_request.number} in the target repository" + RESET)
				result = mirror.mirror_pr(upstream, downstream, pull_request.number)
