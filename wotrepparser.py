# World Of Tanks replay file parser/clanwar filter.
# Copyright (C) 20120817 Rasz_pl
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information please view the readme file.
#

import sys
import binascii
import array
import time
import hashlib
import random
import string,os
import struct
import threading
import json
from pprint import pprint
from datetime import datetime
import os
import shutil
import fnmatch, re
import wotdecoder
# most of those imports are redundand, im lazy like that


# Returns the list of .extension files in path directory. Omit skip file. Can be recursive.
def custom_listfiles(path, extension, recursive, skip = None):
  if recursive:
    files = []
    for root, subFolders, filename in os.walk(path):
      for f in filename:
        if f.endswith("."+extension) and f!=skip:
          files.append(os.path.join(root,f))
  else:
    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(path + os.path.sep + f) and f.endswith("."+extension) and f!=skip]
  return files



def main():

  verbose = False
  recursive = False
  rename = True
  moving = True
  source = os.getcwd()
  output = os.getcwd()
  skip = -1

# Parse arguments
  for argind, arg in enumerate(sys.argv[1:]):
    if argind == skip: pass
    elif arg == "-v" : verbose = True
    elif arg == "-r" : recursive = True
    elif arg == "-n" : rename = False
    elif arg == "-c" : moving = False
    elif arg == "-o" :
      if len(sys.argv) <= argind+2:
        sys.exit("\nUnspecified Output directory.")
      output = sys.argv[argind+2]
      skip = argind+1

      if not os.path.isdir(output):
        print("\nOutput directory: "+output+" doesnt exist. Creating.")
        try:
          os.makedirs(output)
        except:
          sys.exit("Cant create "+output)

    elif arg in ("-h", "-?") or arg.startswith("-") :
                    sys.exit("wotrepparser scans replay files and sorts them into categories (incomplete, result, complete, clanwar, error)."
                             "\nUsage:" \
                             "\n\nwotrepparser file_or_directory -o output_directory -v -r -n" \
                             "\n\n-o  Specify output directory. Default is current." \
                             "\n-v  Verbose, display every file processed." \
                             "\n-r  Recursive scan of all subdirectories." \
                             "\n-n  Dont rename files." \
                             "\n-c  Copy instead of moving.")
    elif source == os.getcwd():
      if not os.path.exists(arg):
        sys.exit("\n"+arg+" doesnt exist.")
      source = arg


  print ("\nSource:", source)
  print ("Output:", output)
  print ("Moving:", moving, "Rename:", rename, "Verbose:", verbose, "Recursive:", recursive, "\n")


  t1 = time.clock()

  if os.path.isfile(source):
    listdir = [source]
  else:
    listdir = custom_listfiles(source, "wotreplay", recursive, "temp.wotreplay")

#  listdir = custom_listfiles("G:\\World_of_Tanks\\replays\\clanwars\\", "wotreplay", False)
#  listdir += custom_listfiles("G:\\World_of_Tanks\\replays\\complete\\", "wotreplay", False)
#  listdir += custom_listfiles("G:\\World_of_Tanks\\replays\\incomplete\\", "wotreplay", False)
#  listdir = {"G:\\World_of_Tanks\\replays\\incomplete\\20121213_0553_usa-T110_39_crimea.wotreplay"}

  if not os.path.exists(output + os.path.sep + "clanwar"):
    os.makedirs(output + os.path.sep + "clanwar")
  if not os.path.exists(output + os.path.sep + "incomplete"):
    os.makedirs(output + os.path.sep + "incomplete")
  if not os.path.exists(output + os.path.sep + "result"):
    os.makedirs(output + os.path.sep + "result")
  if not os.path.exists(output + os.path.sep + "complete"):
    os.makedirs(output + os.path.sep + "complete")
  if not os.path.exists(output + os.path.sep + "error"):
    os.makedirs(output + os.path.sep + "error")

  errors = 0
  for files in listdir:
    while True:
      chunks, chunks_bitmask, processing = wotdecoder.replay(files,7) #7 means try to decode all three blocks (binary 111)

      if processing >=6: #decoder encountered an error
        dest_index = 5
        errors += 1
      else:
        date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
        dest = ["incomplete", "result", "complete", "complete", "clanwar", "error"]
        dest_index = processing-1

      if (processing == 3 and (len(chunks[0]['vehicles'])!=len(chunks[1][1]))) or \
         (processing == 4 and chunks[2]['common']['bonusType'] == 5): #cw

        clan_tag = ["", ""]
        dest_index = 4
        if rename:
          for playind, player in enumerate(chunks[1][1]):
            if playind == 0:
              first_tag = chunks[1][1][player]['clanAbbrev']
              clan_tag[chunks[1][1][player]['team'] - 1] = chunks[1][1][player]['clanAbbrev']
            elif first_tag != chunks[1][1][player]['clanAbbrev']:
              clan_tag[chunks[1][1][player]['team'] - 1] = chunks[1][1][player]['clanAbbrev']
              break

          winlose=("Loss","Win_")[chunks[1][0]['isWinner']==1]

          clan_tag[0] = clan_tag[0] +"_"*(5-len(clan_tag[0]))
          clan_tag[1] = clan_tag[1] +"_"*(5-len(clan_tag[1]))

# You can change cw filename format here.
          fileo = "cw"+date+"_"+clan_tag[0]+"_"+clan_tag[1]+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"

      else:
        if rename and (chunks_bitmask&2): #is second Json available? use it to determine win/loss
          winlose=("Loss","Win_")[chunks[1][0]['isWinner']==1]
          fileo = date+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"
        elif rename and (chunks_bitmask&4): #is pickle available? use it to determine win/loss
          winlose=("Loss","Win_")[chunks[2]['common']['winnerTeam']==chunks[2]['personal']['team']]
          fileo = date+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"
        else:
          fileo = os.path.basename(files)

#      print ("\n"+files, fileo)

      if moving:
        shutil.move(files, output + os.path.sep + dest[dest_index] + os.path.sep + fileo)
      else:
        shutil.copy(files, output + os.path.sep + dest[dest_index] + os.path.sep + fileo)
      if verbose:
        print ("\n",dest[dest_index], " -->", fileo)
        print (wotdecoder.status[processing])
      break


  t2 = time.clock()

  print ("\nProcessed "+str(len(listdir))+" files.", errors, "errors.")
  print  ("Took %0.3fms"  % ((t2-t1)*1000))

main()
