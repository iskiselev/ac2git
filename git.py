#!/usr/bin/python2

# ################################################################################################ #
# Git utility script                                                                               #
# Author: Lazar Sumar                                                                              #
# Date:   03/12/2014                                                                               #
#                                                                                                  #
# This script is a library that is intended to expose a Python API for the git commands and        #
# command result data structures.                                                                  #
# ################################################################################################ #

import sys
import os
import subprocess
import xml.etree.ElementTree as ElementTree
import datetime
import re

gitCmd = 'git'

class GitStatus(object):
    # Regular expressions used in fromgitoutput classmethod for parsing the different git lines.
    branchRe        = re.compile("^On branch (\\w)$")
    blankRe         = re.compile("^\\s*$")
    commentRe       = re.compile("^\\s+\\(.*\\)$")
    fileRe          = re.compile("^\\s+(new file|modified|deleted):\\s+(\\S+)\\s*$")
    untrackedFileRe = re.compile("^\\s+(\\S+)\\s*$")
        
    def __init__(self, branch=None, staged=[], changed=[], untracked=[]):
        self.branch    = branch
        self.staged    = staged
        self.changed   = changed
        self.untracked = untracked

    def __repr__(self):
        str  = "On branch {0}\n".format(self.branch)
        if self.staged is not None and len(self.staged) > 0:
            str += "Changes to be committed:\n\n"
            for file, status in self.staged:
                str += " {0}: {1}\n".format(status, file)
            str += "\n"
        if self.changed is not None and len(self.changed) > 0:
            str += "Changes not staged for commit:\n\n"
            for file, status in self.changed:
                str += " {0}: {1}\n".format(status, file)
            str += "\n"
        if self.untracked is not None and len(self.untracked) > 0:
            str += "Untracked files:\n\n"
            for file in self.untracked:
                str += " {0}\n".format(file[0])
            str += "\n"
        return str
    
    @classmethod
    def fromgitoutput(cls, gitOutput):
        lines = gitOutput.split('\n')
        # git status output example
        # On branch <branch name>
        # Changes to be committed:
        #   (use "git reset HEAD <file>..." to unstage)
        #  
        #  new file:   file1.ext
        #  modified:   file2.ext
        #  deleted:    file3.ext
        #  
        # Changes not staged for commit:
        #   (use git add <file>..." to update what will be committed)
        #   (use "git checkout -- <file>..." to discard changes in working directory)
        #  
        #  modified:    file2.ext
        #  deleted:     file4.ext
        #  
        # Untracked files:
        #   (use "git add <file>..." to include in what will be committed)
        #  
        #  file5.ext
        #  file6.ext
        
        # Parse the branch
        branchName    = None
        branchSpec    = lines.pop(0)
        branchReMatch = GitStatus.branchRe.match(branchSpec)
        if branchReMatch:
            branchName = branchReMatch.group(1)
        
        stagedFiles = []
        changedFiles = []
        untrackedFiles = []
        
        lastHeading = lines.pop(0)
        while len(lines) > 0:
            if lastHeading == "Changes to be committed:":
                # Find the first blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    nextLine = lines.pop(0)
                # Parse files until blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    fileMatch = GitStatus.fileRe.match(nextLine)
                    if not fileMatch:
                        raise Exception("Line [{0}] did not match [{1}]".format(nextLine, GitStatus.fileRe.pattern))
                    fileStatus = fileMatch.group(1)
                    fileName   = fileMatch.group(2)
                    stagedFiles.append((fileName, fileStatus))
                    
                    nextLine = lines.pop(0)
            elif lastHeading == "Changes not staged for commit:":
                # Find the first blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    nextLine = lines.pop(0)
                # Parse files until blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    fileMatch = GitStatus.fileRe.match(nextLine)
                    if not fileMatch:
                        raise Exception("Line [{0}] did not match [{1}]".format(nextLine, GitStatus.fileRe.pattern))
                    fileStatus = fileMatch.group(1)
                    fileName   = fileMatch.group(2)
                    changedFiles.append((fileName, fileStatus))
                    
                    nextLine = lines.pop(0)
            elif lastHeading == "Untracked files:":
                # Find the first blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    nextLine = lines.pop(0)
                # Parse files until blank line
                nextLine = lines.pop(0)
                while not GitStatus.blankRe.match(nextLine) and len(lines) > 0:
                    fileMatch = GitStatus.untrackedFileRe.match(nextLine)
                    if not fileMatch:
                        raise Exception("Line [{0}] did not match [{1}]".format(nextLine, GitStatus.untrackedFileRe.pattern))
                    fileName   = fileMatch.group(1)
                    untrackedFiles.append((fileName,))
                    
                    nextLine = lines.pop(0)
            
            if len(lines) > 0:
                lastHeading = lines.pop(0)
        
        return cls(branch=branchName, staged=stagedFiles, changed=changedFiles, untracked=untrackedFiles)

# GitBranchListItem is an object serialization of a single branch output when the git branch -vv
# command is run.
class GitBranchListItem(object):
    branchVVRe = re.compile("^(?P<iscurrent>\\*)?\\s+(?P<name>\\S+)\\s+(?P<hash>\\S+)\\s+(?:(?P<remote>\\[\\S+\\])\\s+)?(?P<comment>.*)$")
    def __init__(self, name, shortHash, remote, shortComment, isCurrent):
        self.name = name
        self.shortHash = shortHash
        self.remote = remote
        self.shortComment = shortComment
        self.isCurrent = isCurrent
    
    def __repr__(self):
        if self.isCurrent:
            str = "*"
        else:
            str = " "
        str += " {0} {1}".format(self.name, self.shortHash)
        if self.remote is not None:
            str += " {0}".format(self.remote)
        str += " {0}".format(self.shortComment)
        
        return str
        
    def __eq__(self, other):
        if type(other) == GitBranchListItem:
            return (self.name == other.name and self.shortHash == other.shortHash)
        raise Exception("Can't compare {0} with {1}".format(type(self), type(other)))
        
    @classmethod
    def fromgitbranchoutput(cls, outputLine):
        branchVVMatch = GitBranchListItem.branchVVRe.match(outputLine)
        if branchVVMatch is not None:
            name = branchVVMatch.group("name")
            shortHash = branchVVMatch.group("hash")
            comment = branchVVMatch.group("comment")
            remote =  branchVVMatch.group("remote")
            isCurrent = branchVVMatch.group("iscurrent")
            isCurrent = (isCurrent is not None)
            
            return cls(name=name, shortHash=shortHash, remote=remote, shortComment=comment, isCurrent=isCurrent)
        return None
    
class repo(object):
    def __init__(self, path):
        self.path = path
        self._cwdQueue = []
        
    def _pushd(self, newPath):
        self._cwdQueue.insert(0, os.getcwd())
        os.chdir(newPath)
    
    def _popd(self):
        os.chdir(self._cwdQueue.pop(0))
    
    def checkout(self):
        pass

    def branch(self):
        pass
    
    def branch_list(self):
        try:
            cmd = [ gitCmd, 'branch', '-vv' ]
            
            strCmd = ' '.join(cmd)
            self._pushd(self.path)
            output = subprocess.check_output(strCmd)
            self._popd()
        except:
            return None
        
        branchList = []
        outputLines = output.split('\n')
        for line in outputLines:
            if len(line.strip()) > 0:
                branchList.append(GitBranchListItem.fromgitbranchoutput(line))
        return branchList

    def status(self):
        try:
            cmd = [ gitCmd, 'status' ]
            
            strCmd = ' '.join(cmd)
            self._pushd(self.path)
            output = subprocess.check_output(strCmd)
            self._popd()
        except:
            return None
        
        return GitStatus.fromgitoutput(output)

def isRepo(path=None):
    if path is not None and os.path.isdir(path):
        if os.path.isdir(os.path.join(path, ".git")):
            return True
    return False

def init(isBare=False, path=None):
    try:
        cmd = [ gitCmd, 'init' ]
        if isBare:
            cmd.append('--bare')
        if path is not None:
            cmd.append(str(path))
        
        strCmd = ' '.join(cmd)
        output = subprocess.check_output(strCmd)
    except:
        return None
    return repo(path)

def open(path):
    if isRepo(path):
        return repo(path=path)
    return None

def delete(path=None):
    if path is None:
        path = os.getcwd()
    if IsRepo(path=path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        return True
    return False
