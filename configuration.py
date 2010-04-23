#!/usr/bin/env python
# -*- coding: utf8 -*-

import yaml
import sys

class Configuration(object):
    def __init__(self,fichier):
        try:
            confFile = file(fichier, 'r')    # 'document.yaml' contains a single YAML document.
            self.config = yaml.load(confFile)
            confFile.close()
        except IOError:
            print "le fichier %s n'existe pas ou est incorrect" % fichier
            sys.exit(-1)
        except:
            print "erreur lors de l'importation des données de configuration"
            sys.exit(-1)
            
            
    def getBackupmasterdir(self):
        return self.config['backupmasterdir']
    
    def getSsh_destination(self):
        if self.config['ssh_destination'] is None:
            return "luniversetaudela"
        else:
            return self.config['ssh_destination']    
    
    def getSsh_user(self):
        if self.config['ssh_user'] is None:
            return "anonymous"
        else:
            return self.config['ssh_user']    
    
    def getSsh_port(self):
        if self.config['ssh_port'] is None:
            return 22
        else:
            return self.config['ssh_port']    
    
    def getSsh_Key(self):
        if self.config['ssh_key'] is None:
            return "RIEN"
        else:
            return self.config['ssh_key']    
    
    def getDirs2backup(self):
         if self.config['dirs2backup'] is None:
            return []
         else:
            return self.config['dirs2backup']
    
    def getIterations(self):
        if self.config['iterations'] is None:
            return 10 #par défaut
        else:
            return self.config['iterations']
    
    def getExcludedDirs(self):
        if self.config['excludedDirs'] is None:
            return []
        else:
            return self.config['excludedDirs']

    
    def getNotification(self):
        if self.config['notification'] == True:
            return True
        else:
            return False
