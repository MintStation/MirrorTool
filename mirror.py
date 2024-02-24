import os
import subprocess
import config
import sys


def clean_repo():
	print("Cleaning local repo.")
	subprocess.run(["git", "fetch", "--all"],
	               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.run(["git", "checkout", "master"],
	               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.run(["git", "reset", "--hard", "downstream/master"],
	               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.run(["git", "clean", "-f"],
	               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	print("Deleting branches.")
	for deletable_branch in [line.strip().decode() for line in subprocess.check_output(["git", "branch"]).splitlines() if line != b"* master"]:
		subprocess.run(["git", "branch", "-D", deletable_branch],
		               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mirror_pr(upstream, downstream, pr_id):
	print(f"Mirroring PR #{pr_id}.")
	current_directory = os.getcwd()
	try:
		os.chdir(config.local_repo_directory)
		original_pull = upstream.get_pull(pr_id)
		clean_repo()
		print("Switching to mirror branch.")
		subprocess.run(["git", "checkout", "-b", f"{config.mirror_branch_prefix}{pr_id}"],
		               )

		try:
			print("Cherry-picking merge commit.")
			cherry_out = subprocess.check_output(["git", "cherry-pick", "-m", "1",
                                         original_pull.merge_commit_sha], stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as e:
			cherry_out = str(e.output)

		try:
			cherry_out = cherry_out.decode()  # love python3
		except:
			pass

		if "mainline was specified but commit" in cherry_out:
			print("PR was merged via squash.")
			commits = original_pull.get_commits()
			subprocess.run(["git", "fetch", "--all"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			if original_pull.merge_commit_sha in [c.sha for c in commits]:
				for c in commits:
					subprocess.run(["git", "cherry-pick", "--no-commit", "-n", c.sha])
					subprocess.run(["git", "add", "-A", "."])
					subprocess.run(["git", "commit", "--no-edit", "-m", c.commit.message])
					subprocess.run(["git", "cherry-pick", "--continue"])
			else:
				subprocess.run(["git", "cherry-pick", "--no-commit", "-n",
                                    original_pull.merge_commit_sha])
				subprocess.run(["git", "add", "-A", "."])
				subprocess.run(["git", "commit", "--no-edit", "-m", original_pull.title])
				subprocess.run(["git", "cherry-pick", "--continue"])
		else:
			subprocess.run(["git", "add", "-A", "."])

		subprocess.run(["git", "commit", "--allow-empty", "--no-edit", "-m", original_pull.title],
		               )
		print("Pushing to downstream.")
		subprocess.run(["git", "push", "downstream",
                  f"{config.mirror_branch_prefix}{pr_id}"], )

		print("Creating pull request.")
		result = downstream.create_pull(title=f"{config.mirror_pr_title_prefix}{original_pull.title} - {pr_id}",
                                               body=f"Original PR: {original_pull.html_url}\n-----\n{original_pull.body.replace('@', '')}",
                                               base="master",
                                               head=f"{config.mirror_branch_prefix}{pr_id}",
                                               maintainer_can_modify=True)

		print(f"Pull request created: {result.title} (#{result.number})")
		set_label(pull_request, label_name, label_color)
		return result
	except:
		print("An error occured during mirroring.")
	finally:
		os.chdir(current_directory)

def remirror_pr(upstream, downstream, mirror_pr_id):
	print(f"Remirroring #{mirror_pr_id}.")
	current_directory = os.getcwd()
	try:
		os.chdir(config.local_repo_directory)
		mirror_pull = downstream.get_pull(mirror_pr_id)
		# Get original PR number from the "Original PR: " link
		original_pull = upstream.get_pull(
			int(mirror_pull.body.split("/")[6].split("\n")[0]))
		clean_repo()
		print("Switching to mirror branch.")
		subprocess.run(["git", "checkout", "-b", f"{config.mirror_branch_prefix}{original_pull.number}"],
		               )
		print("Cherry-picking merge commit.")
		subprocess.run(["git", "cherry-pick", "-m", "1", original_pull.merge_commit_sha],
		               )
		print("Force pushing to downstream.")
		subprocess.run(["git", "push", "--force", "downstream",
                  f"{config.mirror_branch_prefix}{original_pull.number}"], )
	except:
		print("An error occured during remirroring.")
	finally:
		os.chdir(current_directory)

"""
def set_label(repo, pull_request, label_name, label_color):
	try:
		pull_request.add_to_labels(label_name)
	except:
		try:
			repo.create_label(name=label_name, color=label_color)
			pull_request.add_to_labels(label_name)
		except Exception as e:
			print(f"Failed to assign a PR label. Error text: {e}")

def mirror_label(repo, upstream_pull_request, downstream_pull_request):
	for label in upstream_pull_request.get_labels():
		set_label(repo, downstream_pull_request, label.name, label.color)
"""