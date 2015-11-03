#! /usr/bin/env python
# -*- coding: utf-8 -*-
# 2015.10.13 <varunasarman-at-gmail-dot-com>

# Similar task to the simon game used in Cornish, Smith & Kirby 2013, but focusing on sound.
# Script is partly based on "Simulate (a Simon clone)", Al Sweigart, al@inventwithpython.com

from __future__ import print_function
import random, sys, time, pygame, os
from shutil import copy2
from itertools import permutations
from pygame.locals import *
from os.path import expanduser
import csv, glob, contextlib, wave, re

#-------------------------------------------------------
# Set directories
#-------------------------------------------------------

# directory containing the script
# wd = expanduser("~/Dropbox/lana/MCK/esperimentuak/hch11_py/")
wd = os.getcwd()
os.chdir(wd)

# directory to write responses in
responsedir1 = "response/"

#-------------------------------------------------------
# Graphical globals
#-------------------------------------------------------

FPS = 30
WINDOWWIDTH = 640
WINDOWHEIGHT = 480
TIMEOUT = 4 # seconds before game over if no button is pushed.
beepms = 600 # ms to wait between sequence items while playback

#                R    G    B
WHITE        = (255, 255, 255)
BLACK        = (  0,   0,   0)
LIGHTGRAY    = (150, 150, 150)
MIDGRAY      = (100, 100, 100)
bgColor      = LIGHTGRAY

# Set of button i/o possible buttons
col1 = 1
col2 = 2
col3 = 3
possibs = [col1, col2, col3]

#-------------------------------------------------------
# Functions
#-------------------------------------------------------

# draw some text into an area of a surface
# automatically wraps words
# returns any text that didn't get blitted
# source: http://pygame.org/wiki/TextWrap
def drawText(surface, text, color, rect, font, aa=False, bkg=None):
    rect = Rect(rect)
    y = rect.top
    lineSpacing = -2
 
    # get the height of the font
    fontHeight = font.size("Tg")[1]
 
    while text:
        i = 1
 
        # determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break
 
        # determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1
 
        # if we've wrapped the text, then adjust the wrap to the last word      
        if i < len(text): 
            i = text.rfind(" ", 0, i) + 1
 
        # render the line and blit it to the surface
        if bkg:
            image = font.render(text[:i], 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(text[:i], aa, color)
 
        surface.blit(image, (rect.left, y))
        y += fontHeight + lineSpacing
 
        # remove the text we just blitted
        text = text[i:]
 
    return text

def terminate():
    pygame.quit()
    sys.exit()

def checkForQuit():
    for event in pygame.event.get(QUIT): # get all the QUIT events
        terminate() # terminate if any QUIT events are present
    for event in pygame.event.get(KEYUP): # get all the KEYUP events
        if event.key == K_ESCAPE:
            terminate() # terminate if the KEYUP event was for the Esc key
            print("Trying to quit")
        pygame.event.post(event) # put the other KEYUP event objects back

def clean(color):
    """ Clean screen with defined color.
    """
    DISPLAYSTRF.fill(color)
    pygame.display.flip()
    return

def jump(): 
    """ Start experiment by pressing a key.
    Exit by pressing escape.
    """
    global stayHere
    beg = 0
    while beg == 0:
        if pygame.event.peek():
            ev = pygame.event.peek()
            pygame.event.clear()
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE:
                    clean(bgColor)
                    beg = 1
                    stayHere = 0
                    break
                if ev.key == K_ESCAPE:
                    clean(bgColor)
                    terminate()
                if ev.key == K_BACKSPACE:
                    clean(bgColor)                    
                    stayHere = 1
                    return
        FPSCLOCK.tick(FPS)

def instr():
    """ Display instruction-type messages on screen.
    """    
    global testua
    clean(bgColor)
    
    textrect = DISPLAYSTRF.get_rect()
    margin = 150
    textrect.left = textrect.left + margin
    textrect.top = textrect.top + margin
    textrect.width = textrect.width - 750
        
    # create underline for first line of message
    # underline = '_'*len(testua[0])
    # testua = testua[:1] + [underline] + testua[1:]
    
    for i in range(0, len(testua)):
        messageRect = instrFont.render(testua[i], True, BLACK).get_rect()
        paragraphSep = ((messageRect[2]/(messageRect[3]*10))+1) * messageRect[3]
        parSep = ((paragraphSep / 70) + 1) * messageRect[3]
        drawText(DISPLAYSTRF, testua[i], BLACK, textrect, instrFont)
        textrect[1] = textrect[1] + parSep # 40
    
    pygame.display.flip()
    jump()
    pygame.time.wait(1000)
    return
    
def infodisp(notification, pausems):
    """ Display short notifications to participant.
    """
    infoSurf = instrFont.render(notification, 1, BLACK)
    infoRect = infoSurf.get_rect()
    infoRect.centerx = DISPLAYSTRF.get_rect().centerx
    infoRect.centery = DISPLAYSTRF.get_rect().centery + (WINDOWHEIGHT/2 - 15)
    
    DISPLAYSTRF.blit(infoSurf, infoRect)
    pygame.display.flip()
    pygame.time.wait(pausems)
    clean(bgColor)
    return
    
# Levenshtein distance algorithm implementation by
# http://hetland.org/
def levenshtein(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

def drawRec():
    """ Display a microphone symbol when waiting for participant's input
    """
    global screenRect
    screenRect = DISPLAYSTRF.get_rect()
    recIcon = pygame.image.load('stimuli/icons/mic1.png')
    iconRect = recIcon.get_rect()
    DISPLAYSTRF.blit(recIcon,(screenRect.width/2 - iconRect.width/2, screenRect.height/2 - iconRect.height/2))
    pygame.display.flip()

def stimulidef():
    """ Define stimuli files, corresponding labels,
    and stimulus-to-key mapping.
    """    
    global stimulidir, stimtxt, stimwav, keypermutation, syllableSet
    
    # define key-sound mapping based on subject number.
    # with 3 keys (3 sounds), 6 permutations are possible.
    keypermutationList = list(permutations([0,1,2]))
    # each subject sets a unique random generator
    keypermutation = list(random.sample(keypermutationList, 1)[0])
    # assign a different permutation to each of the first 6 subjects,
    # then restart the series
    # snumber2 = int(snumber)-1
    # keymap = snumber2 - 6*(snumber2//6)
    # keypermutation = list(keypermutationList[keymap])
    
    # new stimuli here!
    # directory to read stimuli from
    dir_coda1 = "stimuli/nld_coda1/"
    dir_onset1 = "stimuli/nld_onset1/"
    dir_onset2 = "stimuli/nld_onset2/"
    dir_3dim1 = "stimuli/nld_3dim1/"
    dir_3dim2 = "stimuli/nld_3dim2/"
    stim_dirs = [dir_coda1, dir_onset1, dir_onset2, dir_3dim1, dir_3dim2]
    
    stimulidir = stim_dirs[stim_set]
    
    # get list of sound stimuli
    stimwav = []
    for (dirname, dirs, files) in os.walk(stimulidir):
        for f in files:
            if f.endswith('.wav'):
                stimwav.append(f)
    stimwav = sorted(stimwav)
    stimwav = [ stimwav[i] for i in keypermutation]
    
    # new stimuli here!
    # set text cues to visualise sound stimuli
    lab_coda1 = ['ta', 'tan', 'ti', 'tin']
    lab_onset1 = ['di', 'ka', 'ni', 'ta']
    lab_onset2 = ['ka', 'ki', 'ta', 'ti']
    lab_3dim1 = ['ki', 'ta', 'tin']
    lab_3dim2 = ['ka', 'tan', 'ti']
    stim_labels = [lab_coda1, lab_onset1, lab_onset2, lab_3dim1, lab_3dim2]
    
    stimtxt = stim_labels[stim_set]
    stimtxt = sorted(stimtxt)
    stimtxt = [ stimtxt[i] for i in keypermutation]
    syllableSet = ', '.join(stimtxt)

def getrefsubj():
    """ Suject-related operations.
    Set reference subject (previous one by default).
    Set initial state of random generator using snumber.
    """
    global responsedir, snumber, refsubj
    
    responsedir = responsedir1 + phase + "/chain" + chain + "/"

    # get subject number for last existing subject response file
    # get list of existing response files
    prevResp = []
    for (dirname, dirs, files) in os.walk(responsedir):
        for f in files:
            if (f.endswith('_inout.txt')):
                prevResp.append(f)
    # extract subject numbers
    subjList = []
    for i in prevResp:
        isubj = re.search("ch" + chain + 's(.*)_', i)
        isubjN = int(isubj.group(1))
        subjList.append(isubjN)
    # define current snumber as lastSubject + 1
    snumber = str(max(subjList)+1)
    
    # set initial state of random generator, for reproductibility.
    # given that each chain restarts snumbers,
    # create unique snumber by adding chain info
    snumber3 = (int(chain)*100) + int(snumber)
    random.seed(snumber3)

    # define the reference subject, the output of which will be used as
    # the input for the current subject.
    # by default, if no other subject is defined, the previous
    # available subject will be used
    if refsubj == "":
        refsubj = str(int(snumber)-1)
    else:
        refsubj = refsubj
        
def stimfiles():
    """ Read the sequence of stimuli from the _inout.txt file
    from the reference subject (previous subject by default).
    """
    global trialList, trainList, outfileBase
    
    outfileBase =  "ch" + chain + "s"
    
    # read sequences from reference subject
    filename = responsedir + outfileBase + refsubj + "_inout.txt"
    with open(filename) as f:
        trials = list(tuple(rec) for rec in csv.reader(f, delimiter = ','))
    
    # for each sequence, get the block info.
    # only select those from the appropriate block.
    # sequences are read as strings; convert them to integers
    trialList = []
    for i in range(0, len(trials)):
        if 'block2' in trials[i][2]:
            trialList.append(map(int, trials[i][4]))

    # read training sequences
    trainingFile = responsedir1 + 'hch11_training.txt'    
    with open(trainingFile) as f:
        trainSeq = f.read().splitlines()

    trainList = []
    for tr in trainSeq:
        trainList.append(map(int, tr))
    trainList

def outfiles():
    """ Create output files for the current subject:
    in, out, inout.
    """
    global sfileOUT, sfileIN, sfileINOUT
    
    # create response files
    sfileOUT = open(responsedir + "longResp/" + outfileBase + snumber + '_out.txt', 'w')
    print('subjectID', 'block', 'seqID', 'itemID', 'button', 'relRT', file = sfileOUT, sep = ",")

    sfileIN = open(responsedir + "longResp/" + outfileBase + snumber + '_in.txt', 'w')
    print('subjectID', 'block', 'seqID', 'itemID', 'button', 'relRT', file = sfileIN, sep = ",")
    
    sfileINOUT = open(responsedir + outfileBase + snumber + '_inout.txt', 'w')    

    return

def questions1():
    """ Technical questions answered by experimenter.
    """
    global phase, stim_set, refsubj, chain
    
    phase = raw_input("\n\nPhase of experiment (test, pilot, chains): ")
    # stim_set = int(raw_input("Set of stimuli (3 = ki-tin-ta; 4 = ka-ti-tan): "))
    chain = raw_input("Diffusion chain number: ")
    refsubj = raw_input("Reference subject (leave empty if reference subject is previous subject): ")
    
    # phase = 'pilot'
    stim_set = 3
    # chain = '1'
    # refsubj = '0'    
    
    return    

def questions2():
    """ Ask the subject some background questions.
    """
    global testdate, sinfotxt

    slistfile = "hch11_subjectList.tsv"
        
    # if subjectList file doesn't exist, create and print headers; else open and append at the end
    if os.path.isfile(slistfile) == 0:
        slist = open(slistfile, 'a')
        print('date', 'phase', 'stimuliSet', 'chain', 'subjectID', 'keyPermutation', 'name', 'email', 'birthYear', 'gender', 'lefthanded', 'nativeLanguages', 'otherLanguages', 'musicInstruction', 'musicPractice', sep = '\t', file = slist)
    else:
        slist = open(slistfile, 'a')
    
    print("\n\nWelcome to the HCH 1.1 experiment.\nBefore starting, " +
    "we would like to ask you to fill in some background questions.\n" +
    "All personal details will remain confidential. \n\n" +
    "Your participant ID is: " + "ch" + chain + "s" + snumber + "\n" +
    "The reference ID is: " + refsubj + "\n\n")
    
    testdate = time.strftime("%Y%m%d_%H%M")
    
    if phase == "t":
        sname = "Some test name"
        semail = "some.random_name@provider.com"
        syear = "1901"
        sgender = "f"
        shand = "n"
        snative = "kuna, maniq"
        sother = "dyirbal, limburgs, bizkaiera"
        smusic = "1"
        smusic2 = "3"
    else:
        sname = raw_input ("Name and surname: ")
        semail = raw_input ("E-mail address: ")
        syear = raw_input ("Year of birth: ")
        sgender = raw_input ("Gender: f(emale), m(ale), o(ther): ")
        snative = raw_input("Which languages could you speak before the age of 5 (separated by commas if more than one): ")
        sother = raw_input("Which other languages can you speak now (separated by commas): ")
        shand = raw_input ("Are you left-handed (y/n)?: ")
        smusic = raw_input("How many years of music instruction have you had? ")
        smusic2 = raw_input("How many hours per week do you sing, play an instrument or dance? ")
    
    subjectInfo = [testdate, phase, stim_set, chain, snumber, syllableSet, sname, semail, syear,
          sgender, shand, snative, sother,
          smusic, smusic2]
    # convert each element to a string
    sinfotxt = []
    for i in subjectInfo: sinfotxt.append(str(i))
    # collapse list into string
    sinfotxt = '\t'.join(sinfotxt)
    
    #print(testdate, phase, stim_set, chain, snumber, str(keypermutation), sname, semail, syear,
    #      sgender, shand, snative, sother,
    #      smusic, smusic2, sep = '\t', file = slist)
    print(sinfotxt, sep = '\t', file = slist)
    
    slist.close()
    
    return

def training1():
    """ Training where subject can test the
    key-syllable mapping without constraints
    """
    global testua, stayHere, block, inpattern, outpattern, levdist, FPSCLOCK
    
    stayHere = 1
    
    block = "training1"
    
    testua = ["Welcome to the HCH 1.1 experiment.",
              
            "During the experiment, you will listen to sequences "+
            "of syllables " +
            "and try to reproduce them using the keyboard.",
            
            "There are three types of syllables, [" +
            syllableSet + "], " +
            "which match the [left, down, right] arrow keys.",

            "In the next screen, you can test the keys and check "+
            "whether you can hear the syllables alright.",
            
            "If you don't have any questions, " +
            "please press the spacebar."]
    
    instr()
    
    # Initialize some variables for a new game
    pattern = [] # stores the pattern of colors
    patternum = 0
    currentStep = 0 # the color the player must push next
    lastClickTime = 0 # timestamp of the player's last button push 
    outpattern = ""
    inpattern = ""
    levdist = ""
    patternEndTime = time.time()  

    while True: # main game loop
        
        drawRec()
        
        clickedButton = None
        for event in pygame.event.get(): # event handling loop
            if event.type == KEYDOWN:
                if event.key == K_LEFT:
                    clickedButton = col1
                if event.key == K_DOWN:
                    clickedButton = col2
                if event.key == K_RIGHT:
                    clickedButton = col3
                if event.key == K_ESCAPE:
                    terminate()
                if event.key == K_SPACE:
                    print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                    clean(bgColor)
                    stayHere = 0
                    return
                
        # wait for the player to enter buttons
        if (clickedButton):
            sounds[clickedButton-1].play()
            outpattern = outpattern + str(clickedButton)
            currentStep += 1
            lastClickTime = time.time()
            print(snumber, block, patternum+1, currentStep, clickedButton,
                  lastClickTime - patternEndTime, 
                  file = sfileOUT, sep = ",")
                  
        pygame.display.update()
        FPSCLOCK.tick(FPS)

def training2():
    global block, testua, stayHere
    
    block = 'training2'    
    
    stayHere = 1
    while stayHere == 1:
    
        testua = ["-- Training session --",
                  "",
                  "Now that you know how the keys work, you can try out some simple training sequences in the following screen.",
                  
                  "Please listen carefully while the computer plays the sequence of syllables. " +
                  "Once the sequence has ended, a microphone will show on the screen. " +
                  "You can then enter the sequence using the [left, down, right] arrow keys. " +
                  "Remember that they match the syllables " +
                  "[" + syllableSet + "]. ",

                  "Since this is a training session, if the wrong key is pressed, you will receive a warning " +
                  "and will have to reproduce the sequence from the beginning. " +
                  "Once the correct syllables are entered, the next sequence will play automatically.",

                  "To start, please press the spacebar."]
    
        playtrain(trainList)
        
        testua = ["Well done!", "",
                  "If you would like to go through this training session once more, " +
              "please press the [backspace] key; otherwise press the spacebar."]
        
        instr()

def block1():
    global block, testua
    
    block = 'block1'    
    
    testua = ["-- Block 1 --",
    "",
    "Is the task clear? Please ask the experimenter if you have any questions.",
    "",
    "During the experiment you will be asked to repeat two blocks of 30 sequences each. " +
    "They will be longer than the ones you just listened to. " +
    "But don't worry, even if you are not confident about the whole sequence, " +
    "try to reproduce the overall pattern as closely as you can. " +
    "Once you have entered a sequence, " +
    "just wait for a couple of seconds; a score will appear on the screen and the next sequence will be reproduced.",
    
    "Reminder: the order of the syllables is [" + syllableSet + "].",
    
    "To start, please press the spacebar."]
    
    playgame(trialList)
    
def block2():
    global block, testua
    
    block = 'block2'    
    
    testua = ["-- Block 2 --",
              "",
    "That was the end of block 1. " +
    "You can now take a break. " +
    "Once you are ready, please press the spacebar to continue with block 2."]
    
    playgame(trialList)

def endExp():
    global testua
    
    testua = ["That was it!",
    "Thank you very much for your help."]
    
    instr()

def handleEvents():
    """ handle events entered by user.
    """
    global clickedButton, stayHere
    
    clickedButton = None
    for event in pygame.event.get(): # event handling loop
        if event.type == KEYDOWN:
            if event.key == K_LEFT:
                clickedButton = col1
            if event.key == K_DOWN:
                clickedButton = col2
            if event.key == K_RIGHT:
                clickedButton = col3
            if event.key == K_ESCAPE:
                terminate()
            if event.key == K_SPACE:
                print(chain, snumber, block, inpattern, outpattern, levdist,
                  file = sfileINOUT, sep = ",")
                clean(bgColor)
                stayHere = 0
                return

def playtrain(stimuli):
    """ Subject is asked to reproduce patterns.
    Do not present new pattern until current one correctly answered.
    """
    global FPSCLOCK, levdist, patternum, stayHere
    
    instr()
    
    # Initialize some variables for a new game
    pattern = [] # stores the pattern of colors
    patternum = 0
    currentStep = 0 # the color the player must push next
    lastClickTime = 0 # timestamp of the player's last button push
    levdist = ""
    # when False, the pattern is playing.
    # when True, waiting for the player to click a colored button:
    waitingForInput = False

    while patternum < len(stimuli): # main game loop
    
        clickedButton = None
        for event in pygame.event.get(): # event handling loop
            if event.type == KEYDOWN:
                if event.key == K_LEFT:
                    clickedButton = col1
                if event.key == K_DOWN:
                    clickedButton = col2
                if event.key == K_RIGHT:
                    clickedButton = col3
                if event.key == K_ESCAPE:
                    terminate()
                if event.key == K_r:
                    waitingForInput = False
                if event.key == K_SPACE:
                    print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                    clean(bgColor)
                    stayHere = 0
                    return

        if not waitingForInput:
            # play the pattern
            # pygame.event.set_allowed(None)
            pygame.display.update()
            pygame.time.wait(1000)
            pattern = stimuli[patternum]
            outpattern = ""
            inpattern = ""
            patternEndTime = time.time()
            for button in pattern:
                sounds[button-1].play()
                lastClickTime = time.time()
                pygame.time.wait(beepms)
                print(snumber, block, patternum+1, currentStep, button,
                      lastClickTime - patternEndTime,
                      file = sfileIN, sep = ",")
                inpattern = inpattern + str(button)
            patternEndTime = time.time()
            waitingForInput = True
        else:
            drawRec()
            # wait for the player to enter buttons
            if (clickedButton and clickedButton == pattern[currentStep]):
                sounds[clickedButton-1].play()
                outpattern = outpattern + str(clickedButton)
                currentStep += 1
                lastClickTime = time.time()
                print(snumber, block, patternum+1, currentStep, clickedButton,
                      lastClickTime - patternEndTime, 
                      file = sfileOUT, sep = ",")
                if currentStep == len(pattern):
                    patternum += 1
                    currentStep = 0
                    print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                    waitingForInput = False
                    pygame.time.wait(200)
                    clean(bgColor)
                    # infodisp("Well done!", 0)
                
            elif (clickedButton and clickedButton != pattern[currentStep]):
                sounds[clickedButton-1].play()
                outpattern = outpattern + str(clickedButton)
                currentStep += 1
                lastClickTime = time.time()
                print(snumber, block, patternum+1, currentStep, clickedButton,
                      lastClickTime - patternEndTime, 
                      file = sfileOUT, sep = ",")
                print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                outpattern = ""
                currentStep = 0
                pygame.time.wait(200)
                infodisp("Please try again", 800)

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def playgame(stimuli):
    """ Subject is asked to reproduce patterns.
    Do not check whether subject's response is correct.
    """
    global FPSCLOCK, levdist, patternum
    
    instr()
    
    # Initialize some variables for a new game
    pattern = [] # stores the pattern of colors
    patternum = 0
    currentStep = 0 # the color the player must push next
    lastClickTime = 0 # timestamp of the player's last button push
    
    # randomise the sequences within the block
    random.shuffle(stimuli)
    
    # when False, the pattern is playing.
    # when True, waiting for the player to click a colored button:
    waitingForInput = False

    while patternum < len(stimuli): # main game loop
    
        clickedButton = None        
        for event in pygame.event.get(): # event handling loop
            if event.type == KEYDOWN:
                if event.key == K_LEFT:
                    clickedButton = col1
                if event.key == K_DOWN:
                    clickedButton = col2
                if event.key == K_RIGHT:
                    clickedButton = col3
                if event.key == K_ESCAPE:
                    terminate()
                if event.key == K_r: # replay the current sequence
                    waitingForInput = False
                if event.key == K_SPACE:
                    print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                    clean(bgColor)
                    return

        if not waitingForInput:
            # play the pattern
            pygame.display.update()
            pygame.time.wait(1000)
            pattern = stimuli[patternum]
            outpattern = ""
            inpattern = ""
            patternEndTime = time.time()
            for button in pattern:
                sounds[button-1].play()
                lastClickTime = time.time()
                pygame.time.wait(beepms)
                print(snumber, block, patternum+1, currentStep, button,
                      lastClickTime - patternEndTime,
                      file = sfileIN, sep = ",")
                inpattern = inpattern + str(button)
            patternEndTime = time.time()
            waitingForInput = True
        else:
            # wait for the player to enter buttons
            drawRec()
            if (clickedButton):
                sounds[clickedButton-1].play()
                outpattern = outpattern + str(clickedButton)
                currentStep += 1
                lastClickTime = time.time()
                print(snumber, block, patternum+1, currentStep, clickedButton,
                      lastClickTime - patternEndTime, 
                      file = sfileOUT, sep = ",")
                      
            # if entered sequence is too short, ask sequence at random later point    
            elif (5 > currentStep > 0 and time.time() - TIMEOUT > lastClickTime):
                levdist = None
                print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                # generate random future position for too-short sequence
                futurePosition = random.randint(patternum+1, len(stimuli)+1)
                # print('future position is: ' + str(futurePosition) + '; somewhere between ' + str(patternum+1) + ' and ' +  str(len(stimuli)+1))
                # repeat current sequence at random future position
                stimuli = stimuli[:futurePosition] + [stimuli[patternum]] + stimuli[futurePosition:]
                patternum += 1
                waitingForInput = False
                currentStep = 0
                clean(bgColor)
                infodisp("That was short!", 1000)
                
            # if entered sequence is long enough and time is out
            elif (currentStep != 0 and time.time() - TIMEOUT > lastClickTime):
                longpattern = inpattern
                if len(outpattern) > len(inpattern): longpattern = outpattern
                levdist = 100 * (1 - (float(levenshtein(outpattern, inpattern)) / len(longpattern)))
                levdist = int(levdist)
                print(chain, snumber, block, inpattern, outpattern, levdist,
                      file = sfileINOUT, sep = ",")
                patternum += 1
                waitingForInput = False
                currentStep = 0
                clean(bgColor)
                infodisp(str(levdist) + " % correct!", 1000)

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def backupResp():
    """ Make a backup copy of the response data
    by copying the 3 subject files (in, out, inout)
    to a unique folder.
    *A better alternative would be to save the response data
    in a *sql relational database.
    """

    # first, close the relevant files
    respFiles = [sfileOUT, sfileIN, sfileINOUT]
    for f in respFiles: f.close()
    
    # then create a unique backup folder
    bupath = "bu/responseBackup/" + phase + "_" + "ch" + chain + "s" + snumber + "_" + testdate
    os.makedirs(bupath)
    
    # then save files
    for f in respFiles: copy2(f.name, bupath)
    
    return

def backupInfo():
    """ Save backup of subject information.
    """
    
    slistfileBU = "bu/responseBackup/hch11_subjectList_bu.tsv"    
    
    # if subjectList file doesn't exist, create and print headers; else open and append at the end
    if os.path.isfile(slistfileBU) == 0:
        slistBU = open(slistfileBU, 'a')
        print('date', 'phase', 'stimuliSet', 'chain', 'subjectID', 'keyPermutation', 'name', 'email', 'birthYear', 'gender', 'lefthanded', 'nativeLanguages', 'otherLanguages', 'musicInstruction', 'musicPractice', sep = '\t', file = slistBU)
    else:
        slistBU = open(slistfileBU, 'a')

    print(sinfotxt, sep = '\t', file = slistBU)    
    slistBU.close()

def main():
    global FPSCLOCK, DISPLAYSTRF, sounds, instrFont, screenRect
    
    questions1()
    getrefsubj()
    stimfiles()
    outfiles()
    stimulidef()
    questions2()

    # audio on:
    # pre-setup mixer to avoid sound lag
    pygame.mixer.pre_init(frequency = 44100, size = 16, buffer = 2048, channels = 1)
    pygame.init()
    
    FPSCLOCK = pygame.time.Clock()
    
    DISPLAYSTRF = pygame.display.set_mode([0,0],FULLSCREEN | DOUBLEBUF)
    screenRect = DISPLAYSTRF.get_rect()
    DISPLAYSTRF = pygame.display.set_mode((screenRect.width, screenRect.height))
#    DISPLAYSTRF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('HCH 1.1')
    cueFont = pygame.font.SysFont('arial', 50)
    instrFont = pygame.font.SysFont('arial', 32)
    pygame.mouse.set_visible(False)
    
    # pre-load sound files to avoid sound lag
    sounds = []
    for i in stimwav:
        sounds.append(pygame.mixer.Sound(stimulidir + i))    
    
    training1()
    training2()
    block1()
    block2()
    backupResp()
    backupInfo()
    endExp()

if __name__ == '__main__':
    main()
