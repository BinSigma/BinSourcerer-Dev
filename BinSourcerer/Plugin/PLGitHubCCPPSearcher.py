#!/usr/bin/env python
# -*-coding: utf8 -*-

########################################################################
# Copyright 2014 Concordia University
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
########################################################################
# This Python script is part of BinSourcerer, a framework
# for assembly to source code matching
#
# Status: Debug
#
########################################################################

import time
import random
import string
import os
import sys
import urllib

#-----------------------------------------------------------------------
# Configuration agent
# The two next function are needed so the configuration manager will be
# able to provide configuration for this module.
# configurationNeed is called first. If no config for this 
# utility exists, user is prompted for utility configuration. If
# configuration exists, previous configs will be used. In all cases,
# configuration step is ended when configurationProvision
# is called with a configuration list as arg.
#-----------------------------------------------------------------------
def configurationNeed():
    return None #This utility does not need configuration
            
def configurationProvision(utilityConfig=[]):
    pass #This utility does not need configuration

#----------------------------------------------------------------------
# Plugin type
# Since many plugins with diferent capabilities can be integrated
# to the framework, we need a general method to understand the
# use of each plugin in a unified way. The value returned by this method
# will allow the framework to call the right operations on the plugin.
#----------------------------------------------------------------------
def identifyPluginType():
    return ["searcher"] 
    
#-----------------------------------------------------------------------
# Plugin name
# This is used so the framework can give a name to a specific plugin
# The name will be used to visualy identify each plugins.
#-----------------------------------------------------------------------
def identifyPlugin():
    return ["GitHubCCPPSearcher", "GitHub (C/C++)"] #First item in list have to have the same name as main class name. Second item in list is visual name
       
#-----------------------------------------------------------------------
# GitHubSearcherCCPP
# This class implements GitHub online search capabilities
#-----------------------------------------------------------------------
class GitHubCCPPSearcher():

    def __init__(self, plMngr):
        self._manager = plMngr
        
        self.__repONL = """
        <h3>%s</h3>
        %s <br />
        <b>Elements : </b> <font color="SaddleBrown" face="Courier New,Courier, monospace">
        %s</font> <br />
        <b>Projects : </b> <font color="Green" face="Courier New,Courier, monospace">
        %s</font><br />""" 
        self.__repLNK = """
        <b>Source : </b> %s <br />"""
        
    #
    # This method is used to manage request timing. Local search engines
    # do not need wait time in between request. This method will be called
    # by the control manager when managing search or analysis requests.
    #
    def isLocal(self):
        return False
        
        
    #
    # Main search plugin function, returns HTML string
    # that can be used by the report manager.
    #
    def pluginSearch(self, searchList):
        #First, we only keep good search terms
        #searchList = self.filterSearchItems(searchList)
        #Now, select terms in order not to overflow the search query buffer
        searchQuery = self.selectSearchItems(searchList)
        if searchQuery == None:
            return None #Search not worth the time...
        #Out on the Internet to get results
        cResultsFile, cppResultsFile, cResults, cppResults = self.doSearch(searchQuery)
        #Parsing results and report HTML string generation
        searchQuery = urllib.unquote_plus(searchQuery)
        resultHTML = self.GenerateGitHubHtml(cResults, cResultsFile, "C", searchQuery)
        resultHTML += self.GenerateGitHubHtml(cppResults, cppResultsFile, "C++", searchQuery)
        return resultHTML
        
    #
    # This is used to filter search items. After this is called
    # only "good" search terms should be present inside the search
    # list items.
    #
    def filterSearchItems(self, searchList):
        filter = self._manager._core._UtMngr.call("SearchFilter", self._manager._core._UtMngr)
        return filter.sf_filter(searchList)
    
    #
    # Search items selection in order to prepare limit search.
    # WARNING, this returns a query string to be used inside a 
    # search!!!
    #
    def selectSearchItems(self, searchList):
        prepper = self._manager._core._UtMngr.call("SearchPrep", self._manager._core._UtMngr)
        return prepper.sp_prepareSearch(searchList, maxLength=128, prefixHexConst=True) #GitHub has 128 chars limits
    
    #
    # Search is sent to GitHub, this function
    # returns c and cpp on disk results + c and cpp parsed results
    #
    def doSearch(self, searchQuery):
        gitQuery = "https://github.com/search?ref=cmdform&type=Code&q=" + searchQuery
        
        webFetcher = self._manager._core._UtMngr.call("WebFetcher", self._manager._core._UtMngr)
        ressourcesAccessor = self._manager._core._UtMngr.call("RessourcesAccessor", self._manager._core._UtMngr)
        
        #GitHub can't search 2 languages at a time. Need to do 2 search...
        #First, we get C results
        cResultsFile = ressourcesAccessor.ra_saveToRessource(webFetcher.wf_fetchPage(gitQuery + "&l=C"))
        if cResultsFile == "":
            time.sleep(20)
            cResultsFile = ressourcesAccessor.ra_saveToRessource(webFetcher.wf_fetchPage(gitQuery + "&l=C"))
        
        #Do not rush on GitHub, it will throw you out!!!
        #Random number has been increased because GitHub seems to be
        #less permissive thant before...
        time.sleep(random.randint(4,7)) #Random is used to "humanize" our search pace...
        
        #Now, we get C++ results
        cppResultsFile =  ressourcesAccessor.ra_saveToRessource(webFetcher.wf_fetchPage(gitQuery + "&l=C%2B%2B"))
        if cppResultsFile == "":
            time.sleep(20)
            cppResultsFile =  ressourcesAccessor.ra_saveToRessource(webFetcher.wf_fetchPage(gitQuery + "&l=C%2B%2B"))
        
        return cResultsFile, cppResultsFile, (self.parseGitHubPage(cResultsFile)), (self.parseGitHubPage(cppResultsFile))

    #
    # This will parse the results files so they can later be used to generate
    # HTML for the report
    #
    def parseGitHubPage(self, inputFile):
        completeResult = []
        try:
            file = open(inputFile, "r+")
        except:
            print "Error while parsing file " + inputFile
            return ""
        while(1):
            line = file.readline()
            if line:
                if string.find(line, "<p class=\"title\">") >= 0:
                    #We got a search line
                    singleResult = []
                    singleResult.append(line)
                    singleResult.append(file.readline())
                    file.readline()
                    singleResult.append(file.readline())
                    singleResult.append(file.readline())
                    completeResult.append(singleResult)
                #print_debug(line)
            else:
                break
        file.close()
        #All results are now in completeResult list
        #We now have to parse those strings
        parsedResult = []
        for result in completeResult:
            partialResult = result[1:3]
            firstQuoteIndex = string.find(partialResult[0], "\"") + 1
            secondQuoteIndex = string.find(partialResult[0][firstQuoteIndex:], "\"")
            userProject = partialResult[0][firstQuoteIndex:secondQuoteIndex+firstQuoteIndex]
            firstQuoteIndex = string.find(partialResult[1], "\"") + 1
            secondQuoteIndex = string.find(partialResult[1][firstQuoteIndex:], "\"")
            fileUrl = partialResult[1][firstQuoteIndex:secondQuoteIndex+firstQuoteIndex]
            parsedResult.append((userProject, fileUrl))
        return parsedResult
        
    #
    # Final report HTML string preparation
    #
    def GenerateGitHubHtml(self, gitResults, resultPageGit, language, query):
        if len(gitResults) == 0:
            return ""
            
        htmlString = ""
        gitHubLink = ""
        if resultPageGit is not "":
            splitted = resultPageGit.split("\\") if (os.name == "nt" and sys.platform == "win32") else resultPageGit.split("/")
            gitHubLink += "<a href=\"" + splitted[len(splitted)-1] + "\">See Git Result Set("+language+")</a><br />"
        repositoriesString = ""
        
        for singleResult in gitResults:
            #Lets print repositories names
            if repositoriesString == "":
                repositoriesString += singleResult[0]
            else:
                repositoriesString += ", " + singleResult[0]
        htmlString += (self.__repONL % ("GitHub", gitHubLink, query, repositoriesString) )   
        for singleResult in gitResults:
            #Lets print files direct links
            htmlString += (self.__repLNK % self.getLink(singleResult[1].rsplit("/")[-1], "https://www.github.com"+singleResult[1]))
        
        return htmlString
    
    #
    # Helper method for GenerateOhlohHtml
    #
    def getLink(slef, label, url):
        return '<a href="%s">%s</a>' % (url, label)
        
#-----------------------------------------------------------------------
# __main__
# QA main for this module
#-----------------------------------------------------------------------
if __name__ == "__main__":

    searcher = GitHubSearcher(None)


   
