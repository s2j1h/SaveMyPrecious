#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SaveMyPrecious - Sauvegarde de fichiers
# Permet de sauvegarder en utilisant rsync + "hard link" pour l'incrémental + ssh
# Développé par J.RAIGNEAU - julien@raigneau.net - http://www.tifauve.net/SaveMyPrecious

#Licensed under the Apache License, Version 2.0 (the "License"); you may not 
#use this file except in compliance with the License. You may obtain a copy of the License at
#http://www.apache.org/licenses/LICENSE-2.0
#Unless required by applicable law or agreed to in writing, software 
#distributed under the License is distributed on an "AS IS" BASIS, WITHOUT 
#WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the 
#License for the specific language governing permissions and limitations under the License. 

import logging
import re
import os,sys
from time import strftime
import time
import datetime 
import pynotify

from configuration import Configuration

#pour l'icone dans la barre des tâches
import gtk
import pygtk
import threading
import time
import gobject

gobject.threads_init()

VERSION = "0.8 - the big Adventure"

class MyThread(threading.Thread):

     NB_ERREURS = 0
     def __init__(self):
        super(MyThread, self).__init__()

     #messages de notification à l'écran
     def notify(self,message,priority,notification):
     	if notification == True:
        	titleNotify = "SaveMyPrecious"
             	uriNotify = "file://" + os.path.join(sys.path[0], 'precious.png')
             	n = pynotify.Notification(titleNotify, message,uriNotify)
             	n.set_urgency(priority)
             	n.show()
 
     #Execute une commande distante et renvoi le résultat
     def execSSH(self,cmd):
         
         cmdSSH = "ssh -p %s -i %s %s@%s '%s'" % (self.myConfiguration.getSsh_port(),self.myConfiguration.getSsh_Key(),self.myConfiguration.getSsh_user(),self.myConfiguration.getSsh_destination(),cmd) 
         out = os.popen(cmdSSH).read()
         out = out.split("\n")
         return out

     def run(self):
      #####################################
      #début script
         #Activation logs
        logFile = os.path.join(sys.path[0],"precious.log")
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=logFile,
                    filemode='w')

        #Lecture fichier de conf
        logging.info('Ouverture fichier de configuration')
        self.myConfiguration = Configuration(os.path.join(sys.path[0],'precious.yaml'))

	#preparation libnotify
	if self.myConfiguration.getNotification() == True:
	    notification = True
	    pynotify.init("SaveMyPrecious - Sauvegarde de fichiers")
	else:
	    notification = False

	backupdir = strftime("%Y%m%d_%H%M%S") #nom du nouveau repertoire
	dateDebutBackup = strftime("%d/%m/%Y %H:%M:%S")
	logging.info("Début du backup: %s" % dateDebutBackup)
	self.notify("Début du backup: %s" % dateDebutBackup,pynotify.URGENCY_NORMAL,notification)

	#vérifications iniales
	#backupmasterDir est non nul
	if self.myConfiguration.getBackupmasterdir() is None:
	    logging.error("Le fichier de configuration n'est pas complet: pas de répertoire destination")
	    self.notify("Le fichier de configuration n'est pas complet: pas de répertoire destination. Le programme ne peut continuer, merci de voir le fichier de log %s" % logFile,pynotify.URGENCY_CRITICAL,notification)
	    self.NB_ERREURS = self.NB_ERREURS +1
	    exit(-1)
	if self.myConfiguration.getDirs2backup() == []:
	    logging.error("Le fichier de configuration n'est pas complet: pas de répertoire à sauvegarder")
	    self.notify("Le fichier de configuration n'est pas complet: pas de répertoire à sauvegarder. Le programme ne peut continuer, merci de voir le fichier de log %s" % logFile,pynotify.URGENCY_CRITICAL,notification)
	    self.NB_ERREURS = self.NB_ERREURS +1
	    exit(-1)
	#il y a au moins un répertoire à sauvegarder

	currentDir =  os.path.join(self.myConfiguration.getBackupmasterdir(),"current")

	#ouverture client ssh
	logging.info("Paramètres: %s %s %s %s" % (self.myConfiguration.getSsh_port(),self.myConfiguration.getSsh_destination(),self.myConfiguration.getSsh_user(),self.myConfiguration.getSsh_Key()))
	stdout= self.execSSH('ls -r1 %s' % self.myConfiguration.getBackupmasterdir())

	#print stdout

	#traitement retour premiere commande (ls -rl)
	dirs = []
	for line in stdout:
	    regexp = line.strip('\n')
	    if re.match(r"\d{8}_\d{6}",regexp) is not None:
		dirs.append(regexp)

	logging.info('Répertoires de sauvegarde actuellement sur le serveur: %s'% dirs)

	#Suppression repertoire le plus vieux 
	if len(dirs) == self.myConfiguration.getIterations():
	    oldbackupdir = dirs[-1]
	    logging.info('Dernier repertoire à effacer %s' % oldbackupdir)
	    self.execSSH('rm -rf %s/%s' % (self.myConfiguration.getBackupmasterdir(),oldbackupdir))

	#création du repertoire via cp -al
	if len(dirs) == 0:
	    logging.info('Premier backup...cela peut durer !')
	    self.execSSH( 'mkdir %s/%s;ln -s %s/%s/ %s/current' % (self.myConfiguration.getBackupmasterdir(),backupdir,self.myConfiguration.getBackupmasterdir(),backupdir,self.myConfiguration.getBackupmasterdir()))
	else:
	    lastbackupdir = dirs[0]
	    logging.info('Le répertoire %s servira de référence - taggué previous ' % lastbackupdir)
	    self.execSSH( 'cp -al %s/%s %s/%s;rm %s/current;ln -s %s/%s %s/current;' % (self.myConfiguration.getBackupmasterdir(),lastbackupdir,self.myConfiguration.getBackupmasterdir(),backupdir,self.myConfiguration.getBackupmasterdir(),self.myConfiguration.getBackupmasterdir(),backupdir,self.myConfiguration.getBackupmasterdir()))
	    self.execSSH( 'rm %s/previous;ln -s %s/%s %s/previous' % (self.myConfiguration.getBackupmasterdir(),self.myConfiguration.getBackupmasterdir(),lastbackupdir,self.myConfiguration.getBackupmasterdir()))


	#liste des fichiers/répertoire à exclure
	excludedDirs = ""
	for item in self.myConfiguration.getExcludedDirs():
	    if excludedDirs == "":
		excludedDirs = "--exclude="+item
	    else:
		excludedDirs = excludedDirs + " --exclude=" + item

	logging.info('Les patterns suivant seront exclus: %s'% excludedDirs)

	#backup via rsync
	for dir in self.myConfiguration.getDirs2backup():
	    logging.info('Synchronisation de %s...' % dir)
	    self.notify('Synchronisation de %s...' % dir,pynotify.URGENCY_NORMAL,notification)
	    error = os.system('nice -n 19 rsync -aRz --delete %s --delete-excluded -e "ssh -p %s -i %s" %s %s@%s:%s/%s' % (excludedDirs,self.myConfiguration.getSsh_port(),self.myConfiguration.getSsh_Key(),dir,self.myConfiguration.getSsh_user(),self.myConfiguration.getSsh_destination(),self.myConfiguration.getBackupmasterdir(),backupdir))
	    #print 'nice -n 19 rsync -az --delete %s --delete-excluded -e "ssh -p %s -i %s" %s %s@%s:%s/%s' % (excludedDirs,myConfiguration.getSsh_port(),myConfiguration.getSsh_Key(),dir,myConfiguration.getSsh_user(),myConfiguration.getSsh_destination(),myConfiguration.getBackupmasterdir(),backupdir)
	    if error <> 0:
		logging.error("La synchronisation de %s ne s'est pas déroulé correctement" % dir)
		self.notify("La synchronisation de %s ne s'est pas déroulé correctement" % dir,pynotify.URGENCY_CRITICAL,notification)
		self.NB_ERREURS = self.NB_ERREURS +1
		if error == 5888: #error de répertoire n'existant pas
		    logging.error("Le répertoire %s n'existe pas!" % dir)
		    self.notify("Le répertoire %s n'existe pas!" % dir,pynotify.URGENCY_CRITICAL,notification)
	    else:
	       logging.info("Synchronisation de %s s'est terminée avec succès" % dir) 
	    #print 'nice -n 19 rsync -az --delete %s --delete-excluded -e "ssh -p %s -i %s" %s %s@%s:%s/%s' % (excludedDirs,myConfiguration.getSsh_port(),myConfiguration.getSsh_Key(),dir,myConfiguration.getSsh_user(),myConfiguration.getSsh_destination(),myConfiguration.getBackupmasterdir(),backupdir)

	#Fin du backup
	dateFinBackup = strftime("%d/%m/%Y %H:%M:%S")
	if self.NB_ERREURS < 1:
	    msg = ""
	else:
	    if self.NB_ERREURS == 1:
		msg = "Une erreur a été trouvée. Merci de consulter le fichier de log pour obtenir plus d'information."
	    else:
		msg = "%s erreur(s) ont été trouvées. Merci de consulter le fichier de log pour obtenir plus d'information." % self.NB_ERREURS
		
	logging.info("Fin du backup: %s.\n%s" % (dateFinBackup,msg))
	error = os.system("scp -P %s -i %s \"%s\" %s@%s:%s" % (self.myConfiguration.getSsh_port(),self.myConfiguration.getSsh_Key(),logFile,self.myConfiguration.getSsh_user(),self.myConfiguration.getSsh_destination(),currentDir))
	if error <> 0:
		logging.error("Impossible de copier le fichier de log %s sur la cible" % logFile)
		self.notify("Backup terminé mais avec des erreurs, merci de consulter le fichier de log %s"%logFile,pynotify.URGENCY_NORMAL,notification)
	else:
	    self.notify("Fin du backup: %s \n\n%s" % (dateFinBackup,msg),pynotify.URGENCY_NORMAL,notification)
	gtk.main_quit()

class Precious:
    """
    Classe principale (initialise GUI)
    """
    def __init__(self):
        """
        Initialisation
        """
	
    def gtk_destroy(self, source=None, event=None):
        gtk.main_quit()
        
    def main(self):
	uriNotify = os.path.join(sys.path[0], 'precious.png')
	statusIcon = gtk.StatusIcon()
	statusIcon.set_from_file(uriNotify)
	statusIcon.set_tooltip("SaveMyPrecious %s" % VERSION)
	statusIcon.set_visible(True)
        t = MyThread()
        t.start()
        gtk.main()
        t.quit = True
        return 0

# we start the app like this...
if __name__ == '__main__':
    app = Precious()
    app.main()
