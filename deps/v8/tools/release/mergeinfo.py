#!/usr/bin/env python
# Copyright 2015 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# for py2/py3 compatibility
from __future__ import print_function

import argparse
import os
import sys
import re

from search_related_commits import git_execute

GIT_OPTION_HASH_ONLY = '--pretty=format:%H'
GIT_OPTION_NO_DIFF = '--quiet'
GIT_OPTION_ONELINE = '--oneline'

def describe_commit(git_working_dir, hash_to_search, one_line=False):
  if one_line:
    return git_execute(git_working_dir, ['show',
                                         GIT_OPTION_NO_DIFF,
                                         GIT_OPTION_ONELINE,
                                         hash_to_search]).strip()
  return git_execute(git_working_dir, ['show',
                                       GIT_OPTION_NO_DIFF,
                                       hash_to_search]).strip()


def get_followup_commits(git_working_dir, hash_to_search):
  cmd = ['log', '--grep=' + hash_to_search, GIT_OPTION_HASH_ONLY,
         'remotes/origin/queen'];
  return git_execute(git_working_dir, cmd).strip().splitlines()

def get_merge_commits(git_working_dir, hash_to_search):
  merges = get_related_commits_not_on_queen(git_working_dir, hash_to_search)
  false_merges = get_related_commits_not_on_queen(
    git_working_dir, 'Cr-Branched-From: ' + hash_to_search)
  false_merges = set(false_merges)
  return ([merge_commit for merge_commit in merges
      if merge_commit not in false_merges])

def get_related_commits_not_on_queen(git_working_dir, grep_command):
  commits = git_execute(git_working_dir, ['log',
                                          '--all',
                                          '--grep=' + grep_command,
                                          GIT_OPTION_ONELINE,
                                          '--decorate',
                                          '--not',
                                          'remotes/origin/queen',
                                          GIT_OPTION_HASH_ONLY])
  return commits.splitlines()

def get_branches_for_commit(git_working_dir, hash_to_search):
  branches = git_execute(git_working_dir, ['branch',
                                           '--contains',
                                           hash_to_search,
                                           '-a']).strip()
  branches = branches.splitlines()
  return map(str.strip, branches)

def is_lkgr(branches):
  return 'remotes/origin/lkgr' in branches

def get_first_canary(branches):
  canaries = ([currentBranch for currentBranch in branches if
    currentBranch.startswith('remotes/origin/chromium/')])
  canaries.sort()
  if len(canaries) == 0:
    return 'No Canary coverage'
  return canaries[0].split('/')[-1]

def get_first_v8_version(branches):
  version_re = re.compile("remotes/origin/[0-9]+\.[0-9]+\.[0-9]+")
  versions = filter(lambda branch: version_re.match(branch), branches)
  if len(versions) == 0:
    return "--"
  version = versions[0].split("/")[-1]
  return version

def print_analysis(git_working_dir, hash_to_search):
  print('1.) Searching for "' + hash_to_search + '"')
  print('=====================ORIGINAL COMMIT START===================')
  print(describe_commit(git_working_dir, hash_to_search))
  print('=====================ORIGINAL COMMIT END=====================')
  print('2.) General information:')
  branches = get_branches_for_commit(git_working_dir, hash_to_search)
  print('Is LKGR:         ' + str(is_lkgr(branches)))
  print('Is on Canary:    ' + str(get_first_canary(branches)))
  print('First V8 branch: ' + str(get_first_v8_version(branches)) + \
      ' (Might not be the rolled version)')
  print('3.) Found follow-up commits, reverts and ports:')
  followups = get_followup_commits(git_working_dir, hash_to_search)
  for followup in followups:
    print(describe_commit(git_working_dir, followup, True))

  print('4.) Found merges:')
  merges = get_merge_commits(git_working_dir, hash_to_search)
  for currentMerge in merges:
    print(describe_commit(git_working_dir, currentMerge, True))
    print('---Merged to:')
    mergeOutput = git_execute(git_working_dir, ['branch',
                                                '--contains',
                                                currentMerge,
                                                '-r']).strip()
    print(mergeOutput)
  print('Finished successfully')

if __name__ == '__main__':  # pragma: no cover
  parser = argparse.ArgumentParser('Tool to check where a git commit was'
 ' merged and reverted.')

  parser.add_argument('-g', '--git-dir', required=False, default='.',
                        help='The path to your git working directory.')

  parser.add_argument('hash',
                      nargs=1,
                      help='Hash of the commit to be searched.')

  args = sys.argv[1:]
  options = parser.parse_args(args)

  sys.exit(print_analysis(options.git_dir, options.hash[0]))
